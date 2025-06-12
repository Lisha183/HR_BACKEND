from rest_framework import serializers
from .models import EmployeeProfile

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfile
        fields = '__all__'
