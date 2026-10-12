import uuid
from django.db import models


class Reservation(models.Model):
    reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    sandbox = models.UUIDField(db_index=True)
    room = models.CharField(max_length=20)
    day = models.DateField()
    hour = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["day", "hour", "room"]
        constraints = [
            models.UniqueConstraint(
                fields=["sandbox", "room", "day", "hour"],
                name="one_reservation_per_slot",
            ),
            models.CheckConstraint(
                condition=models.Q(hour__gte=9, hour__lte=16), name="business_hours"
            ),
            models.CheckConstraint(
                condition=models.Q(room__in=["focus", "meeting", "creative"]),
                name="known_room",
            ),
        ]
