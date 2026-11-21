# SPDX-License-Identifier: MIT

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from cvat.apps.engine.models import Job, Task

from .counting import count_annotations_by_label
from .permissions import AnnotationCountsPermission
from .serializers import AnnotationCountsQuerySerializer, AnnotationCountsSerializer


class AnnotationCountsViewSet(viewsets.GenericViewSet):
    queryset = Task.objects.select_related("project", "organization")
    iam_permission_class = AnnotationCountsPermission
    filter_backends = []
    pagination_class = None

    @extend_schema(
        summary="Number of annotations per label in a task",
        parameters=[
            OpenApiParameter("job_id", int, description="Count only this job of the task"),
        ],
        responses=AnnotationCountsSerializer,
    )
    def retrieve(self, request, pk):
        task = self.get_object()

        query = AnnotationCountsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        job_id = query.validated_data.get("job_id")
        if job_id is not None and not Job.objects.filter(id=job_id, segment__task=task).exists():
            raise ValidationError({"job_id": f"Job {job_id} is not part of task {task.id}"})

        counts = count_annotations_by_label(task.id, job_id)
        labels = sorted(
            (
                {"id": label.id, "name": label.name, "color": label.color, "count": counts[label.id]}
                for label in task.get_labels()
            ),
            key=lambda label: (-label["count"], label["name"]),
        )

        return Response(
            AnnotationCountsSerializer(
                {
                    "task_id": task.id,
                    "job_id": job_id,
                    "total": sum(label["count"] for label in labels),
                    "labels": labels,
                }
            ).data
        )
