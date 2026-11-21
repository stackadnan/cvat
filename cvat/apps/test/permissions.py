# SPDX-License-Identifier: MIT

from cvat.apps.engine.models import Task
from cvat.apps.engine.permissions import TaskPermission


class AnnotationCountsPermission:
    """
    Seeing the counts of a task needs the same right as seeing the task itself,
    so the decision is left to CVAT's own task "view" rule in OPA.
    """

    @classmethod
    def create(cls, request, view, obj: Task | None, iam_context):
        if obj is None:
            return []
        return [TaskPermission.create_scope_view(request, obj)]
