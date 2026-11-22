# SPDX-License-Identifier: MIT

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from cvat.apps.engine.models import Job

from .live_updates import publish_task_changed


@receiver(post_save, sender=Job, dispatch_uid="annotation_counts_job_touched")
def notify_annotations_changed(sender, instance: Job, update_fields=None, **kwargs):
    # Annotations are written with bulk_create, so there is no signal for them.
    # But every save that changes annotations ends with Job.touch(), which saves
    # only updated_date (dataset_manager/task.py, _set_updated_date).
    if update_fields is None or set(update_fields) != {"updated_date"}:
        return

    task_id = instance.segment.task_id
    # publish after commit, otherwise the page could re-fetch the old counts
    transaction.on_commit(lambda: publish_task_changed(task_id))
