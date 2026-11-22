# SPDX-License-Identifier: MIT

from django.apps import AppConfig


class TestConfig(AppConfig):
    name = "cvat.apps.test"
    verbose_name = "Annotation analytics"

    def ready(self):
        from . import signals  # noqa: F401
