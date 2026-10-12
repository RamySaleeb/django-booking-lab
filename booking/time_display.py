"""Display-only conversion from canonical UTC slot identities."""

from datetime import datetime, time, timedelta, timezone
from functools import lru_cache
from importlib.resources import files
from zoneinfo import ZoneInfo

# Use the pinned package on every platform, regardless of host timezone data.
ZONES = tuple(sorted(set(files("tzdata").joinpath("zones").read_text().splitlines())))


def normalize_zone(value):
    return value if value in ZONES else "UTC"


@lru_cache(maxsize=64)
def get_zone(name):
    name = normalize_zone(name)
    with files("tzdata.zoneinfo").joinpath(*name.split("/")).open("rb") as source:
        return ZoneInfo.from_file(source, key=name)


def local_range(day, hour, zone_name):
    start = datetime.combine(day, time(hour), tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    zone = get_zone(zone_name)

    def label(instant):
        local = instant.astimezone(zone)
        offset = local.strftime("%z")
        return f"{local:%Y-%m-%d %H:%M} UTC{offset[:3]}:{offset[3:]}"

    return f"{label(start)} → {label(end)}"
