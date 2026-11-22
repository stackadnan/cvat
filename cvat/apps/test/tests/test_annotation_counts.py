# SPDX-License-Identifier: MIT

from unittest import mock

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from cvat.apps.engine.models import (
    Job,
    Label,
    LabeledImage,
    LabeledShape,
    LabeledTrack,
    Segment,
    Task,
)
from cvat.apps.engine.tests.utils import ForceLogin
from cvat.apps.iam.models import User
from cvat.apps.test.counting import count_annotations_by_label


def make_user(username: str, group: str = "user") -> User:
    user = User.objects.create_user(username=username, password="pass-" + username)
    user.groups.add(Group.objects.get_or_create(name=group)[0])
    return user


class AnnotationCountsTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = make_user("owner")
        cls.stranger = make_user("stranger")

        cls.task = Task.objects.create(name="counts", owner=cls.owner, segment_size=10)
        cls.job_a = cls._make_job(cls.task, 0, 9)
        cls.job_b = cls._make_job(cls.task, 10, 19)

        cls.cat = Label.objects.create(task=cls.task, name="cat")
        cls.dog = Label.objects.create(task=cls.task, name="dog")
        cls.empty = Label.objects.create(task=cls.task, name="empty")
        cls.skeleton = Label.objects.create(task=cls.task, name="person", type="skeleton")
        cls.nose = Label.objects.create(task=cls.task, name="nose", parent=cls.skeleton)

        def shape(job, label, frame, group=0, parent=None):
            return LabeledShape.objects.create(
                job=job, label=label, frame=frame, group=group, parent=parent,
                type="polygon", points=[0, 0, 1, 1, 2, 0],
            )

        # job A: 2 plain cats, 1 cat split in 3 parts (one object), 1 dog track, 1 dog tag
        shape(cls.job_a, cls.cat, 0)
        shape(cls.job_a, cls.cat, 1)
        for _ in range(3):
            shape(cls.job_a, cls.cat, 2, group=5)
        LabeledTrack.objects.create(job=cls.job_a, label=cls.dog, frame=0, group=0)
        LabeledImage.objects.create(job=cls.job_a, label=cls.dog, frame=3, group=0)

        # job B: same group number 5 on another frame is another object,
        # and one skeleton whose point must not be counted on its own
        shape(cls.job_b, cls.cat, 10, group=5)
        shape(cls.job_b, cls.cat, 10, group=5)
        root = shape(cls.job_b, cls.skeleton, 11)
        shape(cls.job_b, cls.nose, 11, parent=root)

    @staticmethod
    def _make_job(task, start, stop):
        segment = Segment.objects.create(task=task, start_frame=start, stop_frame=stop)
        return Job.objects.create(segment=segment)

    def _get(self, user, path):
        with ForceLogin(user, self.client):
            return self.client.get(path)

    def test_counts_objects_not_shapes(self):
        counts = count_annotations_by_label(self.task.id)

        self.assertEqual(counts[self.cat.id], 4)
        self.assertEqual(counts[self.dog.id], 2)
        self.assertEqual(counts[self.skeleton.id], 1)
        self.assertEqual(counts[self.nose.id], 0)

    def test_job_filter_splits_task_total(self):
        job_a = count_annotations_by_label(self.task.id, self.job_a.id)
        job_b = count_annotations_by_label(self.task.id, self.job_b.id)

        self.assertEqual(job_a, {self.cat.id: 3, self.dog.id: 2})
        self.assertEqual(job_b, {self.cat.id: 1, self.skeleton.id: 1})
        self.assertEqual(job_a + job_b, count_annotations_by_label(self.task.id))

    def test_endpoint_lists_every_label_sorted_by_count(self):
        response = self._get(self.owner, f"/api/annotation-counts/{self.task.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["total"], 7)
        self.assertIsNone(data["job_id"])
        self.assertEqual(
            [(label["name"], label["count"]) for label in data["labels"]],
            [("cat", 4), ("dog", 2), ("person", 1), ("empty", 0)],
        )

    def test_endpoint_job_filter(self):
        response = self._get(self.owner, f"/api/annotation-counts/{self.task.id}?job_id={self.job_b.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total"], 2)

    def test_job_of_another_task_is_rejected(self):
        other_task = Task.objects.create(name="other", owner=self.owner, segment_size=10)
        other_job = self._make_job(other_task, 0, 9)

        response = self._get(self.owner, f"/api/annotation-counts/{self.task.id}?job_id={other_job.id}")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_login_is_rejected(self):
        response = self.client.get(f"/api/annotation-counts/{self.task.id}")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_access_to_task_is_rejected(self):
        response = self._get(self.stranger, f"/api/annotation-counts/{self.task.id}")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LiveUpdatesSignalTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        owner = make_user("owner")
        cls.task = Task.objects.create(name="live", owner=owner, segment_size=10)
        segment = Segment.objects.create(task=cls.task, start_frame=0, stop_frame=9)
        cls.job = Job.objects.create(segment=segment)

    @mock.patch("cvat.apps.test.signals.publish_task_changed")
    def test_annotation_save_publishes_after_commit(self, publish):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            self.job.touch()  # what dataset_manager does after saving annotations
            publish.assert_not_called()

        self.assertEqual(len(callbacks), 1)
        publish.assert_called_once_with(self.task.id)

    @mock.patch("cvat.apps.test.signals.publish_task_changed")
    def test_other_job_saves_are_ignored(self, publish):
        with self.captureOnCommitCallbacks(execute=True):
            self.job.save()
            self.job.save(update_fields=["state"])

        publish.assert_not_called()
