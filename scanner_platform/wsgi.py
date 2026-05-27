"""WSGI config for scanner_platform."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scanner_platform.settings")

application = get_wsgi_application()
