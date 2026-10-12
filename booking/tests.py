from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4
from django.db import IntegrityError, connections, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from .models import Reservation
from .services import available_days, reserve_slot


class BookingTests(TestCase):
    def setUp(self):
        self.client.get("/")
        self.day = available_days()[0]
        self.data = {"room": "focus", "day": str(self.day), "hour": 9}

    def test_booking_and_duplicate(self):
        self.assertEqual(
            self.client.post(
                "/reserve/", self.data, HTTP_ACCEPT="application/json"
            ).status_code,
            201,
        )
        self.assertEqual(
            self.client.post(
                "/reserve/", self.data, HTTP_ACCEPT="application/json"
            ).status_code,
            409,
        )
        self.assertEqual(Reservation.objects.count(), 1)

    def test_database_constraint_independent_of_service(self):
        fields = dict(sandbox=uuid4(), room="focus", day=self.day, hour=9)
        Reservation.objects.create(**fields)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Reservation.objects.create(**fields)

    def test_visitor_isolation(self):
        other = Client()
        other.get("/")
        for client in [self.client, other]:
            self.assertEqual(
                client.post(
                    "/reserve/", self.data, HTTP_ACCEPT="application/json"
                ).status_code,
                201,
            )
        self.assertEqual(Reservation.objects.count(), 2)
        self.assertEqual(len(self.client.get("/").context["reservations"]), 1)

    def test_cancellation_reopens_slot(self):
        self.client.post("/reserve/", self.data)
        reservation = Reservation.objects.get()
        self.assertEqual(
            self.client.post(
                reverse("cancel", args=[reservation.reference])
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                "/reserve/", self.data, HTTP_ACCEPT="application/json"
            ).status_code,
            201,
        )

    def test_other_visitor_cannot_cancel(self):
        self.client.post("/reserve/", self.data)
        other = Client()
        other.get("/")
        response = other.post(
            reverse("cancel", args=[Reservation.objects.get().reference])
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(Reservation.objects.count(), 1)

    def test_invalid_slots_rejected(self):
        for field, value in [
            ("room", "unknown"),
            ("hour", 8),
            ("hour", 17),
            ("hour", "oops"),
            ("day", "invalid"),
            ("day", str(self.day - timedelta(days=1))),
            ("day", str(self.day + timedelta(days=7))),
        ]:
            with self.subTest(field=field, value=value):
                data = {**self.data, field: value}
                self.assertEqual(self.client.post("/reserve/", data).status_code, 400)
        self.assertEqual(Reservation.objects.count(), 0)

    def test_mutations_require_post(self):
        self.assertEqual(self.client.get("/reserve/").status_code, 405)
        self.assertEqual(
            self.client.get(reverse("cancel", args=[uuid4()])).status_code, 405
        )

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.get("/")
        self.assertEqual(client.post("/reserve/", self.data).status_code, 403)
        self.assertEqual(
            client.post(
                "/reserve/",
                self.data,
                HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
            ).status_code,
            302,
        )

    def test_missing_sandbox_rejected(self):
        self.assertEqual(Client().post("/reserve/", self.data).status_code, 400)

    def test_date_and_room_query_fallbacks(self):
        response = self.client.get("/?day=not-a-date&room=unknown")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["room"], "focus")
        self.assertEqual(response.context["selected_day"], self.day)

    def test_standard_form_flow_without_javascript(self):
        response = self.client.post("/reserve/", self.data, follow=True)
        self.assertContains(response, "Reserved. Your room is ready")
        self.assertEqual(response.context["free_count"], 7)
        self.assertContains(response, "Cancel reservation")

    def test_health(self):
        self.assertEqual(self.client.get("/health/").json(), {"status": "ok"})


class ConcurrentBookingTests(TransactionTestCase):
    def compete(self, sandboxes):
        # Open both physical connections before releasing the workers. A sleep
        # does not prove that two independent sessions reached the starting gate.
        barrier = Barrier(2, timeout=10)
        day = available_days()[0]

        def reserve(sandbox):
            connection = connections["default"]
            connection.close()
            try:
                connection.ensure_connection()
                if connection.vendor == "postgresql":
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT pg_backend_pid()")
                        identity = cursor.fetchone()[0]
                else:
                    identity = id(connection.connection)
                barrier.wait()
                accepted = reserve_slot(sandbox, "focus", day, 9) is not None
                return identity, accepted
            finally:
                # close_old_connections() need not close a healthy connection.
                # Explicitly release each thread's connection, even on failure.
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(reserve, sandbox) for sandbox in sandboxes]
            results = [future.result(timeout=30) for future in futures]
        self.assertEqual(len({identity for identity, _ in results}), 2)
        return [accepted for _, accepted in results]

    def test_two_database_connections_only_create_one_reservation(self):
        sandbox = uuid4()
        self.assertEqual(sorted(self.compete([sandbox, sandbox])), [False, True])
        self.assertEqual(Reservation.objects.count(), 1)
        reservation = Reservation.objects.get()
        self.assertEqual(reservation.sandbox, sandbox)
        self.assertEqual((reservation.room, reservation.hour), ("focus", 9))

    def test_distinct_sandboxes_can_concurrently_reserve_same_slot(self):
        sandboxes = [uuid4(), uuid4()]
        self.assertEqual(self.compete(sandboxes), [True, True])
        self.assertEqual(Reservation.objects.count(), 2)
        self.assertSetEqual(set(Reservation.objects.values_list("sandbox", flat=True)), set(sandboxes))
