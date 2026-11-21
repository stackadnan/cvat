# SPDX-License-Identifier: MIT

from collections import Counter

from django.db.models import CharField, Count, Q, Value
from django.db.models.functions import Concat

from cvat.apps.engine.models import Job, LabeledImage, LabeledShape, LabeledTrack


def count_annotations_by_label(task_id: int, job_id: int | None = None) -> Counter[int]:
    """
    Returns {label_id: number of annotated objects} for a task, or for one of its jobs.

    One object is: an ungrouped shape, all shapes sharing a (job, frame, group),
    a track, or a tag. Skeleton points are part of their skeleton, so shapes and
    tracks with a parent are skipped. The three tables are counted by the database
    and sent back in a single UNION ALL query.
    """
    jobs = Job.objects.filter(segment__task_id=task_id)
    if job_id is not None:
        jobs = jobs.filter(id=job_id)

    ungrouped = Q(group__isnull=True) | Q(group=0)
    group_key = Concat("job_id", Value(":"), "frame", Value(":"), "group", output_field=CharField())

    shapes = (
        LabeledShape.objects.filter(job__in=jobs, parent__isnull=True)
        .values("label_id")
        .annotate(
            n=Count("id", filter=ungrouped)
            + Count(group_key, filter=Q(group__gt=0), distinct=True)
        )
    )
    tracks = (
        LabeledTrack.objects.filter(job__in=jobs, parent__isnull=True)
        .values("label_id")
        .annotate(n=Count("id"))
    )
    tags = LabeledImage.objects.filter(job__in=jobs).values("label_id").annotate(n=Count("id"))

    counts = Counter()
    for row in shapes.union(tracks, tags, all=True):
        counts[row["label_id"]] += row["n"]
    return counts
