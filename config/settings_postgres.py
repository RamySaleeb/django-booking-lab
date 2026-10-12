"""Opt-in settings for disposable PostgreSQL verification, never the live default."""
import os

from .settings import *  # noqa: F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["PGDATABASE"],
        "USER": os.environ["PGUSER"],
        "PASSWORD": os.environ["PGPASSWORD"],
        "HOST": os.environ["PGHOST"],
        "PORT": os.environ.get("PGPORT", "5432"),
        "CONN_MAX_AGE": 0,
        "OPTIONS": {
            "connect_timeout": 5,
            "options": "-c statement_timeout=15000 -c lock_timeout=10000",
        },
    }
}
