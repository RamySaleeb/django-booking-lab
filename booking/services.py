from datetime import timedelta, timezone as datetime_timezone
from django.db import IntegrityError, transaction
from django.utils import timezone
from .models import Reservation

ROOMS = {
    "focus": {
        "name": "Focus room",
        "description": "A quiet space for deep work.",
        "capacity": "1–2 people",
        "number": "01",
    },
    "meeting": {
        "name": "Meeting room",
        "description": "Bring your next idea to the table.",
        "capacity": "Up to 6 people",
        "number": "02",
    },
    "creative": {
        "name": "Creative studio",
        "description": "Make room for something new.",
        "capacity": "Up to 4 people",
        "number": "03",
    },
}


def available_days():
    today = timezone.now().astimezone(datetime_timezone.utc).date()
    return [today + timedelta(days=i) for i in range(1, 8)]


def reserve_slot(sandbox, room, day, hour):
    """Validate first; the database, not an availability read, arbitrates races."""
    if room not in ROOMS or day not in available_days() or hour not in range(9, 17):
        raise ValueError(
            "Choose a listed room and a future slot within the next seven days."
        )
    try:
        with transaction.atomic():
            return Reservation.objects.create(
                sandbox=sandbox, room=room, day=day, hour=hour
            )
    except IntegrityError:
        # A savepoint has rolled back before checking the expected conflict.
        if Reservation.objects.filter(
            sandbox=sandbox, room=room, day=day, hour=hour
        ).exists():
            return None
        raise
