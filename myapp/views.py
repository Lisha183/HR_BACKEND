from django.contrib.auth import login, logout, authenticate, get_user_model
from django.middleware.csrf import get_token
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission, IsAdminUser
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import CustomUser, EmployeeProfile, LeaveRequest, Payroll, AttendanceRecord, Department, SelfAssessment,  MeetingSlot
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    LeaveRequestSerializer,
    EmployeeProfileSerializer,
    PayrollSerializer,
    AttendanceRecordSerializer,
    CustomUserSerializer,
    UserApprovalSerializer,
    DepartmentSerializer,
    SelfAssessmentSerializer,
    MeetingSlotSerializer, 
    UserSerializer
)
from .permissions import IsOwnerOrAdmin, IsEmployeeUser
from django.db import models 
from django.db.models import Q 
from .utils import send_meeting_notification_email 


User = get_user_model()
@ensure_csrf_cookie
def csrf_test(request):
    return JsonResponse({"detail": "CSRF cookie set"})

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("REGISTRATION ERRORS:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            login(request, user)
            get_token(request)
            role = 'admin' if user.is_staff else user.role
            return Response({'id': user.id, 'username': user.username, 'role': role}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            logout(request)
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"detail": f"Logout failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)



from rest_framework.decorators import api_view, permission_classes 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_details(request):
    serializer = CustomUserSerializer(request.user)
    return Response(serializer.data)


class DepartmentListCreateView(generics.ListCreateAPIView):
    queryset = Department.objects.all().order_by('id')
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminUser]

class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdminUser]



class EmployeeProfileList(generics.ListCreateAPIView):
    queryset = EmployeeProfile.objects.all().select_related('user', 'department').order_by('full_name', 'id')
    serializer_class = EmployeeProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_staff or getattr(self.request.user, "is_hr", False):
            return EmployeeProfile.objects.all().select_related('user', 'department').order_by('full_name', 'id')
        elif self.request.user.is_authenticated:
            return EmployeeProfile.objects.filter(user=self.request.user).select_related('user', 'department').order_by('full_name', 'id')
        return EmployeeProfile.objects.none()

    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            raise PermissionDenied("Only admins can create employee profiles.")

        username = self.request.data.get('username')
        if not username:
            raise ValidationError({"username": "Username is required to create an employee profile."})

        try:
            target_user = CustomUser.objects.get(username=username)
        except CustomUser.DoesNotExist:
            raise ValidationError({"username": "User with this username does not exist."})
        serializer.save(user=target_user)

class EmployeeProfileDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = EmployeeProfile.objects.all().select_related('user', 'department')
    serializer_class = EmployeeProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]

    def get_object(self):
        queryset = self.get_queryset()
        pk = self.kwargs.get('pk')

        obj = generics.get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(self.request, obj)
        return obj

class EmployeeLeaveRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeaveRequest.objects.filter(employee=self.request.user).order_by('-requested_at').select_related('employee', 'approved_by')

    def perform_create(self, serializer):
        print(f"DEBUG Backend - User: {self.request.user.username}, ID: {self.request.user.id}, is_authenticated: {self.request.user.is_authenticated}, is_staff: {self.request.user.is_staff}")

        if self.request.user.is_staff:
             raise PermissionDenied("Admins cannot submit leave requests via this endpoint for themselves. Please use admin interface or a dedicated admin endpoint.")
        
        serializer.save(employee=self.request.user, status='Pending')


class EmployeeLeaveRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveRequest.objects.all().select_related('employee', 'approved_by')
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsOwnerOrAdmin]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not request.user.is_staff:
            if 'status' in request.data:
                if request.data['status'] != 'Cancelled' or instance.status not in ['Pending', 'Approved']:
                    return Response(
                        {"detail": "Employees can only change their own pending/approved requests to 'Cancelled'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if request.data['status'] == 'Cancelled':
                    instance.approved_by = None
                    instance.approval_date = None
                    instance.comments = None
            
            forbidden_fields = ['approved_by', 'approval_date', 'comments']
            if any(field in request.data for field in forbidden_fields):
                 return Response(
                    {"detail": "Employees cannot modify approval-related fields."},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return super().update(request, *args, **kwargs)


class AdminLeaveRequestListView(generics.ListAPIView):
    queryset = LeaveRequest.objects.all().order_by('-requested_at').select_related('employee', 'approved_by')
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAdminUser]


class AdminLeaveRequestDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LeaveRequest.objects.all().select_related('employee', 'approved_by')
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAdminUser]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data.get('status', instance.status)
        current_status = instance.status

        if new_status in ['Approved', 'Rejected']:
            if current_status == 'Pending' or \
               (current_status in ['Approved', 'Rejected'] and new_status != current_status):
                serializer.validated_data['approved_by'] = request.user
                serializer.validated_data['approval_date'] = timezone.now()
        elif new_status == 'Cancelled':
            if current_status != 'Cancelled':
                serializer.validated_data['approved_by'] = request.user
                serializer.validated_data['approval_date'] = timezone.now()
        elif new_status == 'Pending':
            if current_status != 'Pending':
                serializer.validated_data['approved_by'] = None
                serializer.validated_data['approval_date'] = None
        
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()

class AdminPayrollListCreate(generics.ListCreateAPIView):
    queryset = Payroll.objects.all().select_related('employee')
    serializer_class = PayrollSerializer
    permission_classes = [IsAdminUser]


class AdminPayrollDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Payroll.objects.all().select_related('employee')
    serializer_class = PayrollSerializer
    permission_classes = [IsAdminUser]


class EmployeePayrollList(generics.ListAPIView):
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payroll.objects.filter(employee=self.request.user).order_by('-pay_period_start').select_related('employee')


class EmployeePayrollDetail(generics.RetrieveAPIView):
    serializer_class = PayrollSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payroll.objects.filter(employee=self.request.user).select_related('employee')

    def get_object(self):
        queryset = self.get_queryset()
        obj = generics.get_object_or_404(queryset, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

class AttendanceListCreateView(generics.ListCreateAPIView):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AttendanceRecord.objects.filter(employee=self.request.user).order_by('-timestamp').select_related('employee')

    def perform_create(self, serializer):
        user = self.request.user
        record_type = serializer.validated_data.get('record_type')

        if user.is_staff:
            raise PermissionDenied("Admins cannot use this endpoint for attendance. Please use the admin interface.")
        
        last_record = AttendanceRecord.objects.filter(employee=user).order_by('-timestamp').first()

        if record_type == 'clock_in':
            if last_record and last_record.record_type == 'clock_in' and timezone.now().date() == last_record.timestamp.date():
                raise ValidationError({"detail": "You are already clocked in today."})
        elif record_type == 'clock_out':
            if not last_record or last_record.record_type == 'clock_out' or timezone.now().date() != last_record.timestamp.date():
                raise ValidationError({"detail": "You are already clocked out or have not clocked in today."})
        else:
            raise ValidationError({"detail": "Invalid record_type provided."})

        serializer.save(employee=user)


class AdminAttendanceListView(generics.ListAPIView):
    queryset = AttendanceRecord.objects.all().select_related('employee').order_by('-timestamp')
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAdminUser]


    def get_queryset(self):
        queryset = super().get_queryset()
        
        employee_username = self.request.query_params.get('employee_username', None)
        if employee_username:
            queryset = queryset.filter(employee__username__icontains=employee_username)

        start_date_str = self.request.query_params.get('start_date', None)
        end_date_str = self.request.query_params.get('end_date', None)

        if start_date_str:
            try:
                start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(timestamp__date__gte=start_date)
            except ValueError:
                raise ValidationError({"start_date": "Invalid date format. UseYYYY-MM-DD."})
        
        if end_date_str:
            try:
                end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(timestamp__date__lte=end_date)
            except ValueError:
                raise ValidationError({"end_date": "Invalid date format. UseYYYY-MM-DD."})
        
        return queryset


class AdminUserApprovalListView(generics.ListAPIView):
    queryset = CustomUser.objects.filter(is_approved=False, role='employee')
    serializer_class = UserApprovalSerializer
    permission_classes = [IsAdminUser]


class AdminUserApprovalDetailView(generics.RetrieveUpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserApprovalSerializer
    permission_classes = [IsAdminUser]

    def patch(self, request, *args, **kwargs):
        allowed_fields = {'is_approved'}
        if not set(request.data.keys()).issubset(allowed_fields):
            return Response(
                {"detail": f"Only {list(allowed_fields)} field(s) can be updated via this endpoint."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.partial_update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        allowed_fields = {'is_approved'}
        if set(request.data.keys()) != allowed_fields:
            return Response(
                {"detail": f"For PUT, only {list(allowed_fields)} field(s) must be provided. Prefer PATCH for partial updates."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return self.update(request, *args, **kwargs)


class EmployeeSelfAssessmentListCreateView(generics.ListCreateAPIView):
    serializer_class = SelfAssessmentSerializer
    permission_classes = [IsEmployeeUser] 

    def get_queryset(self):
        return SelfAssessment.objects.filter(employee=self.request.user).order_by('-year', '-quarter_number')

    def perform_create(self, serializer):
        
        quarter_number = serializer.validated_data.get('quarter_number')
        year = serializer.validated_data.get('year')

        if SelfAssessment.objects.filter(employee=self.request.user, quarter_number=quarter_number, year=year).exists():
            raise ValidationError(
                {"detail": f"A self-assessment for Q{quarter_number} {year} already exists for you. You can only submit one per quarter/year."}
            )

     
        serializer.save(employee=self.request.user, status='Pending HR Review')



class AdminSelfAssessmentListView(generics.ListAPIView):
    serializer_class = SelfAssessmentSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = SelfAssessment.objects.all().select_related('employee', 'reviewed_by').order_by(
            '-year', '-quarter_number', 'employee__username'
        )

        employee_username = self.request.query_params.get('employee_username')
        quarter_number = self.request.query_params.get('quarter_number')
        year = self.request.query_params.get('year')
        status = self.request.query_params.get('status')

        if employee_username:
            queryset = queryset.filter(employee__username__icontains=employee_username)

        if quarter_number:
            queryset = queryset.filter(quarter_number=quarter_number)

        if year:
            queryset = queryset.filter(year=year)

        if status:
            queryset = queryset.filter(status=status)

        return queryset



class AdminSelfAssessmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SelfAssessment.objects.all().select_related('employee', 'reviewed_by')
    serializer_class = SelfAssessmentSerializer
    permission_classes = [IsAdminUser]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        print("Validated data for update:", serializer.validated_data)

        if request.user.is_staff:
            if 'hr_rating' in serializer.validated_data or \
               'hr_feedback' in serializer.validated_data or \
               serializer.validated_data.get('status') == 'Completed':

                instance.reviewed_by = request.user
                if serializer.validated_data.get('status') == 'Completed' and not instance.reviewed_at:
                    instance.reviewed_at = timezone.now()
                    

        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)

        print(f"Instance before save - status: {instance.status}, hr_rating: {instance.hr_rating}, hr_feedback: {instance.hr_feedback}")

        instance.save()

        serializer = self.get_serializer(instance)

        return Response(serializer.data)

class EmployeeUserListView(generics.ListAPIView):
    queryset = CustomUser.objects.filter(role='employee').order_by('username')
    serializer_class = CustomUserSerializer 
    permission_classes = [IsAdminUser]





class MeetingSlotListCreateView(generics.ListCreateAPIView):

    queryset = MeetingSlot.objects.all().select_related('hr_reviewer', 'booked_by_employee', 'self_assessment')
    serializer_class = MeetingSlotSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):

        if not self.request.user.is_staff:
            raise PermissionDenied("Only HR/Admin users can create meeting slots.")

        self_assessment_id = serializer.validated_data.get('self_assessment')
        if self_assessment_id:
            if MeetingSlot.objects.filter(self_assessment=self_assessment_id).exists():
                raise ValidationError({"self_assessment": "A meeting slot for this self-assessment already exists."})

        serializer.save(hr_reviewer=self.request.user)


class MeetingSlotDetailView(generics.RetrieveUpdateDestroyAPIView):
  
    queryset = MeetingSlot.objects.all().select_related('hr_reviewer', 'booked_by_employee', 'self_assessment')
    serializer_class = MeetingSlotSerializer
    permission_classes = [IsAdminUser] 

    def perform_update(self, serializer):

        instance = self.get_object()
        is_booked_before = instance.is_booked
        is_booked_after = serializer.validated_data.get('is_booked', is_booked_before)

        if not self.request.user.is_staff:

            if is_booked_before and not is_booked_after and instance.booked_by_employee == self.request.user:
                 raise PermissionDenied("Employees cannot unbook slots through this admin endpoint.")

        if is_booked_before and not is_booked_after and self.request.user.is_staff:
            serializer.validated_data['booked_by_employee'] = None
            serializer.validated_data['is_booked'] = False

        serializer.save()


class EmployeeMeetingSlotListView(generics.ListAPIView):

    queryset = MeetingSlot.objects.filter(is_booked=False).select_related('hr_reviewer').order_by('date', 'start_time')
    serializer_class = MeetingSlotSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        queryset = super().get_queryset()

        hr_username = self.request.query_params.get('hr_username', None)
        if hr_username:
            queryset = queryset.filter(hr_reviewer__username__icontains=hr_username)

        self_assessment_id = self.request.query_params.get('self_assessment_id', None)
        if self_assessment_id:
            try:
                queryset = queryset.filter(self_assessment_id=int(self_assessment_id))
            except ValueError:
                raise ValidationError({"self_assessment_id": "Invalid self_assessment_id. Must be an integer."})

        current_datetime = timezone.now()
        queryset = queryset.filter(date__gte=current_datetime.date()).filter(
            models.Q(date=current_datetime.date(), start_time__gte=current_datetime.time()) | models.Q(date__gt=current_datetime.date())
        )

        return queryset

class EmployeeMyBookingsListView(generics.ListAPIView):

    serializer_class = MeetingSlotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_authenticated or self.request.user.is_staff:
          
            return MeetingSlot.objects.none() 

        queryset = MeetingSlot.objects.filter(
            is_booked=True,
            booked_by_employee=self.request.user
        ).select_related('hr_reviewer', 'self_assessment').order_by('-date', '-start_time') 
        current_datetime = timezone.now()
        queryset = queryset.filter(
            Q(date__gt=current_datetime.date()) |
            Q(date=current_datetime.date(), start_time__gte=current_datetime.time())
        )
        return queryset

class BookMeetingSlotView(generics.UpdateAPIView):

    queryset = MeetingSlot.objects.all()
    serializer_class = MeetingSlotSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        queryset = self.get_queryset()
        obj = generics.get_object_or_404(queryset, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if request.user.is_staff:
            raise PermissionDenied("Admin users cannot book slots through this endpoint.")

        if instance.is_booked:
            return Response({"detail": "This slot is already booked."}, status=status.HTTP_400_BAD_REQUEST)

        current_datetime = timezone.now()
        slot_datetime = timezone.make_aware(timezone.datetime.combine(instance.date, instance.start_time))
        if slot_datetime < current_datetime:
            return Response({"detail": "Cannot book a meeting slot in the past."}, status=status.HTTP_400_BAD_REQUEST)

        if instance.booked_by_employee == request.user:
            return Response({"detail": "You have already booked this slot."}, status=status.HTTP_200_OK)

        if not SelfAssessment.objects.filter(employee=request.user).exists():
            return Response(
                {"detail": "You must have at least one self-assessment submitted to book a meeting slot.", "type": "info"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if instance.self_assessment:
            if instance.self_assessment.employee != request.user:
                raise PermissionDenied(
                    "This meeting slot is for a specific self-assessment that is not yours. You can only book slots linked to your own self-assessments."
                )

        instance.is_booked = True
        instance.booked_by_employee = request.user
        instance.save()

        send_meeting_notification_email(instance, request.user, 'booked')


        serializer = self.get_serializer(instance) 
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return Response({"detail": "PUT method not allowed for booking. Use PATCH."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


class UnbookMeetingSlotView(generics.UpdateAPIView):

    queryset = MeetingSlot.objects.all()
    serializer_class = MeetingSlotSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        queryset = self.get_queryset()
        obj = generics.get_object_or_404(queryset, pk=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if request.user.is_staff:
            raise PermissionDenied("Admin users cannot unbook slots through this endpoint. They manage via MeetingSlotDetailView.")

        if not instance.is_booked:
            return Response({"detail": "This slot is not currently booked."}, status=status.HTTP_400_BAD_REQUEST)

        if instance.booked_by_employee != request.user:
            return Response({"detail": "You can only unbook slots that you have booked."}, status=status.HTTP_403_FORBIDDEN)

        current_datetime = timezone.now()
        slot_datetime = timezone.make_aware(timezone.datetime.combine(instance.date, instance.start_time))
        if slot_datetime < current_datetime:
            return Response({"detail": "Cannot unbook a meeting slot that is in the past."}, status=status.HTTP_400_BAD_REQUEST)

        instance.is_booked = False
        instance.booked_by_employee = None
        instance.save()

        send_meeting_notification_email(instance, request.user, 'unbooked') 


        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return Response({"detail": "PUT method not allowed for unbooking. Use PATCH."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

class EmployeeProfileByUsernameView(generics.RetrieveAPIView):
    serializer_class = EmployeeProfileSerializer

    def get_queryset(self):
        return EmployeeProfile.objects.select_related('user')

    def get_object(self):
        username = self.kwargs['username']
        return self.get_queryset().get(user__username=username)

class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.all() 
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
   
        return User.objects.all()


class HRUserListView(generics.ListAPIView):
   
    queryset = User.objects.filter(is_staff=True).order_by('username') 
    serializer_class = UserSerializer 
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
    
        return super().get_queryset()



class DepartmentList(generics.ListAPIView):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

class LeaveRequestList(generics.ListAPIView):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveRequestSerializer


class EmployeeProfileMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = EmployeeProfile.objects.select_related('user', 'department').get(user=request.user)
            serializer = EmployeeProfileSerializer(profile)
            return Response(serializer.data)
        except EmployeeProfile.DoesNotExist:
            return Response({"detail": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)