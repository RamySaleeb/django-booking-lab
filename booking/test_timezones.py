from datetime import date, datetime, timezone
from unittest.mock import patch
from django.test import SimpleTestCase, TestCase
from django.utils import timezone as django_timezone
from .models import Reservation
from .services import available_days
from .time_display import local_range, normalize_zone


class TimeDisplayTests(SimpleTestCase):
    def test_spring_forward_skips_nonexistent_hour(self):
        self.assertEqual(
            local_range(date(2024, 3, 10), 9, "America/Los_Angeles"),
            "2024-03-10 01:00 UTC-08:00 → 2024-03-10 03:00 UTC-07:00",
        )

    def test_fall_back_repeated_hour_has_distinct_offsets(self):
        self.assertEqual(
            local_range(date(2024, 11, 3), 8, "America/Los_Angeles"),
            "2024-11-03 01:00 UTC-07:00 → 2024-11-03 01:00 UTC-08:00",
        )

    def test_fractional_offset(self):
        self.assertEqual(
            local_range(date(2024, 1, 1), 9, "Asia/Kolkata"),
            "2024-01-01 14:30 UTC+05:30 → 2024-01-01 15:30 UTC+05:30",
        )

    def test_both_calendar_rollovers(self):
        self.assertEqual(
            local_range(date(2024, 1, 1), 9, "Pacific/Honolulu"),
            "2023-12-31 23:00 UTC-10:00 → 2024-01-01 00:00 UTC-10:00",
        )
        self.assertEqual(
            local_range(date(2024, 1, 1), 16, "Pacific/Kiritimati"),
            "2024-01-02 06:00 UTC+14:00 → 2024-01-02 07:00 UTC+14:00",
        )

    def test_unknown_zone_falls_back_to_utc(self):
        for value in [None, "", "not/a-zone", "../../etc/passwd"]:
            self.assertEqual(normalize_zone(value), "UTC")
            self.assertEqual(
                local_range(date(2024, 1, 1), 9, value),
                "2024-01-01 09:00 UTC+00:00 → 2024-01-01 10:00 UTC+00:00",
            )

    def test_booking_window_uses_utc_today_even_with_active_local_zone(self):
        with patch(
            "booking.services.timezone.now",
            return_value=datetime(2024, 1, 1, 23, 30, tzinfo=timezone.utc),
        ):
            with django_timezone.override("Pacific/Kiritimati"):
                days = available_days()
        self.assertEqual(days[0], date(2024, 1, 2))
        self.assertEqual(days[-1], date(2024, 1, 8))
        self.assertEqual(len(days), 7)


class TimezoneBookingTests(TestCase):
    def test_display_choice_preserves_identity_conflict_and_cancel(self):
        day = available_days()[0]
        response = self.client.get("/", {"timezone": "Pacific/Kiritimati"})
        self.assertContains(response, "Showing Pacific/Kiritimati")
        self.assertContains(response, local_range(day, 9, "Pacific/Kiritimati"))
        data = {
            "room": "focus",
            "day": str(day),
            "hour": 9,
            "timezone": "Pacific/Kiritimati",
        }
        response = self.client.post("/reserve/", data, follow=True)
        self.assertContains(response, "Showing Pacific/Kiritimati")
        reservation = Reservation.objects.get()
        self.assertEqual((reservation.day, reservation.hour), (day, 9))
        self.assertEqual(
            self.client.post(
                "/reserve/",
                {**data, "timezone": "America/Los_Angeles"},
                HTTP_ACCEPT="application/json",
            ).status_code,
            409,
        )
        response = self.client.post(
            f"/cancel/{reservation.reference}/",
            {"timezone": "Pacific/Kiritimati"},
            follow=True,
        )
        self.assertContains(response, "Showing Pacific/Kiritimati")
        self.assertEqual(Reservation.objects.count(), 0)

    def test_invalid_zone_and_local_date_cannot_expand_window(self):
        response = self.client.get("/", {"timezone": "bad-zone"})
        self.assertContains(response, "Showing UTC")
        with patch(
            "booking.services.timezone.now",
            return_value=datetime(2024, 1, 1, 23, 30, tzinfo=timezone.utc),
        ):
            response = self.client.post(
                "/reserve/",
                {
                    "room": "focus",
                    "day": "2024-01-09",
                    "hour": 9,
                    "timezone": "Pacific/Kiritimati",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Reservation.objects.count(), 0)
