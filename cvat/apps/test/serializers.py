# SPDX-License-Identifier: MIT

from rest_framework import serializers


class LabelCountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    color = serializers.CharField()
    count = serializers.IntegerField()


class AnnotationCountsSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    job_id = serializers.IntegerField(allow_null=True)
    total = serializers.IntegerField()
    labels = LabelCountSerializer(many=True)


class AnnotationCountsQuerySerializer(serializers.Serializer):
    job_id = serializers.IntegerField(required=False, min_value=1)
