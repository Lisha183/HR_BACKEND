from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from rest_framework import viewsets
from .models import EmployeeProfile
from .serializers import EmployeeSerializer

@api_view(['GET'])
def home_view(request):
    return Response({'message': 'Welcome to the HR System API!'})

@api_view(['POST'])
def register(request):
    form = CustomUserCreationForm(request.data)
    if form.is_valid():
        user = form.save()
        login(request, user) 
        return Response({'message': 'User registered successfully.'}, status=status.HTTP_201_CREATED)
    return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = EmployeeProfile.objects.all()
    serializer_class = EmployeeSerializer
