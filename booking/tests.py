from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from uuid import uuid4
from django.db import IntegrityError, close_old_connections, transaction
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

    def test_full_room_day_disables_slots_and_race(self):
        for hour in range(9, 17):
            self.client.post("/reserve/", {**self.data, "hour": hour})

        response = self.client.get(
            "/", {"room": "focus", "day": str(self.day)}
        )

        self.assertEqual(response.context["free_count"], 0)
        self.assertIsNone(response.context["race_hour"])
        self.assertEqual(len(response.context["reservations"]), 8)
        self.assertTrue(all(slot["taken"] for slot in response.context["slots"]))
        self.assertContains(response, "0 open")
        self.assertEqual(
            response.content.decode().count('<button class="slot" disabled>'), 8
        )
        self.assertContains(response, 'id="race-button" disabled')

    def test_cancellation_reopens_exact_slot_and_race_targets_it(self):
        for hour in range(9, 17):
            self.client.post("/reserve/", {**self.data, "hour": hour})

        reservation = Reservation.objects.get(day=self.day, hour=12)
        self.assertEqual(
            self.client.post(reverse("cancel", args=[reservation.reference])).status_code,
            302,
        )

        response = self.client.get(
            "/", {"room": "focus", "day": str(self.day)}
        )
        slots = {slot["hour"]: slot for slot in response.context["slots"]}

        self.assertEqual(response.context["free_count"], 1)
        self.assertEqual(response.context["race_hour"], 12)
        self.assertFalse(slots[12]["taken"])
        self.assertTrue(all(slots[hour]["taken"] for hour in range(9, 17) if hour != 12))
        self.assertContains(response, "1 open")

    def test_full_room_does_not_block_other_room_day_or_visitor(self):
        for hour in range(9, 17):
            self.client.post("/reserve/", {**self.data, "hour": hour})

        other_day = available_days()[1]
        other = Client()
        other.get("/")

        for client, room, day in [
            (self.client, "meeting", self.day),
            (self.client, "focus", other_day),
            (other, "focus", self.day),
        ]:
            with self.subTest(room=room, day=day, client=client is other):
                response = client.get("/", {"room": room, "day": str(day)})
                self.assertEqual(response.context["free_count"], 8)
                self.assertEqual(response.context["race_hour"], 9)
                self.assertTrue(
                    all(not slot["taken"] for slot in response.context["slots"])
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
    def test_two_database_connections_only_create_one_reservation(self):
        barrier = Barrier(2)
        sandbox, day = uuid4(), available_days()[0]

        def compete():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return reserve_slot(sandbox, "focus", day, 9) is not None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: compete(), range(2)))
        self.assertEqual(sorted(outcomes), [False, True])
        self.assertEqual(Reservation.objects.count(), 1)
