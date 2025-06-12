from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EmployeeViewSet

router = DefaultRouter()
router.register(r'employees', EmployeeViewSet)

from . import views
from django.contrib.auth.views import LoginView


urlpatterns = [
    path('', views.home_view, name='home'),
    path('register/', views.register, name='register'),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('myapp/', include(router.urls)),

]
