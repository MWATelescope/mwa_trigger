from rest_framework import serializers
from . import models

class VOEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.VOEvent
        fields = '__all__'