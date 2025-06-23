from datetime import timezone
from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from .models import CustomUser, EmployeeProfile, Payroll, LeaveRequest, AttendanceRecord, Department, SelfAssessment


User = get_user_model()

class NestedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'is_staff', 'is_active']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'role']

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data['role'],
            is_approved=True
        )
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data.get('username'), password=data.get('password'))
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Invalid username or password")
  

class EmployeeProfileSerializer(serializers.ModelSerializer):
    user = CustomUserSerializer(read_only=True)
    department_name = serializers.ReadOnlyField(source='department.name')
    class Meta:
        model = EmployeeProfile
        fields = [
            'id', 'user', 'full_name', 'phone_number', 'address', 'date_of_birth',
            'hire_date', 'job_title', 'salary', 'department', 'department_name'
        ]
        read_only_fields = ['id', 'department_name'] 
        extra_kwargs = {
            'user': {'required': False} 
        }


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_username = serializers.ReadOnlyField(source='employee.username')
    approved_by_username = serializers.ReadOnlyField(source='approved_by.username')

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = [
            'requested_at',
        ]
        extra_kwargs = {
            'employee': {'write_only': True, 'required': False}, 
            'approved_by': {'required': False},
            'approval_date': {'required': False},
            'comments': {'required': False},
            'status': {'required': False},
        }

    def update(self, instance, validated_data):
        request = self.context.get('request')

        if 'status' in validated_data:
            new_status = validated_data['status']
            if request and not request.user.is_staff:
                if new_status != 'Cancelled':
                    raise serializers.ValidationError(
                        {"status": "Employees can only set their leave request status to 'Cancelled'."}
                    )
                if instance.status not in ['Pending', 'Approved']:
                     raise serializers.ValidationError(
                        {"status": "Only pending or approved leave requests can be cancelled by an employee."}
                    )
                if new_status == 'Cancelled':
                    instance.approved_by = None
                    instance.approval_date = None
                    instance.comments = None

        if ('approved_by' in validated_data or 'approval_date' in validated_data or 'comments' in validated_data):
            if request and not request.user.is_staff:
                raise serializers.ValidationError({"approval_details": "Only admin users can set approval details."})

        return super().update(instance, validated_data)


    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError({"detail": "Authentication required to create leave requests."})
        if request.user.is_authenticated and not request.user.is_staff:
            validated_data['employee'] = request.user

        return super().create(validated_data)


class PayrollSerializer(serializers.ModelSerializer):
    employee_username = serializers.ReadOnlyField(source='employee.username') 

    class Meta:
        model = Payroll
        fields = [
            'id', 'employee', 'employee_username',
            'pay_period_start', 'pay_period_end',
            'gross_pay',
            'deductions',
            'net_pay',
            'payout_date'
        ]
        read_only_fields = ['net_pay', 'employee_username']
        extra_kwargs = {
            'employee': {'write_only': True, 'required': True}
        }

class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_username = serializers.ReadOnlyField(source='employee.username')

    class Meta:
        model = AttendanceRecord
        fields = [
            'id', 'employee', 'employee_username', 'timestamp', 'record_type'
        ]
        read_only_fields = ['timestamp', 'employee', 'employee_username']


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'

class SelfAssessmentSerializer(serializers.ModelSerializer):
    employee_username = serializers.ReadOnlyField(source='employee.username')
    reviewed_by_username = serializers.ReadOnlyField(source='reviewed_by.username')

    class Meta:
        model = SelfAssessment
        fields = [
            'id', 'employee', 'employee_username', 'quarter_number', 'year',
            'employee_rating', 'employee_comments', 'submitted_at', 'status',
            'hr_rating', 'hr_feedback', 'reviewed_by', 'reviewed_by_username', 'reviewed_at'
        ]
        read_only_fields = [
            'id', 'employee', 'employee_username', 'submitted_at',
            'reviewed_by', 'reviewed_by_username', 'reviewed_at', 'status' 
        ]
        extra_kwargs = {
            'employee_rating': {'required': True, 'allow_null': False},
            'employee_comments': {'required': True, 'allow_blank': False},
            'quarter_number': {'required': True, 'allow_null': False},
            'year': {'required': True, 'allow_null': False},

            'hr_rating': {'required': False, 'allow_null': True},
            'hr_feedback': {'required': False, 'allow_blank': True},
        }

    def validate(self, data):
        request_method = self.context['request'].method
        request_user = self.context['request'].user

        if request_method == 'POST':
            if not request_user.is_authenticated or request_user.is_staff:
                raise serializers.ValidationError("Only authenticated employees can submit self-assessments.")

            employee = request_user
            quarter_number = data.get('quarter_number')
            year = data.get('year')

            if SelfAssessment.objects.filter(employee=employee, quarter_number=quarter_number, year=year).exists():
                raise serializers.ValidationError(
                    f"A self-assessment for Q{quarter_number} {year} already exists for this employee."
                )

            if any(field in data for field in ['hr_rating', 'hr_feedback', 'status', 'reviewed_by', 'reviewed_at']):
                raise serializers.ValidationError("Employees cannot set HR review fields during submission.")

        if request_method in ['PUT', 'PATCH']:
            if not request_user.is_authenticated or not request_user.is_staff:
                raise serializers.ValidationError("Only authenticated admin users can update self-assessments.")

            instance = self.instance 

            if not request_user.is_staff and any(field in data for field in ['employee_rating', 'employee_comments', 'quarter_number', 'year']):
                raise serializers.ValidationError("Employees cannot modify their self-assessment after submission.")

            new_status = data.get('status', instance.status)
            if new_status == 'Completed':
                if data.get('hr_rating') is None and instance.hr_rating is None:
                    raise serializers.ValidationError({"hr_rating": "HR Rating is required to mark as Completed."})
                if not data.get('hr_feedback') and not instance.hr_feedback:
                    raise serializers.ValidationError({"hr_feedback": "HR Feedback is required to mark as Completed."})
            elif instance.status == 'Completed' and new_status != 'Completed':
                if request_user.is_staff:
                    instance.hr_rating = None
                    instance.hr_feedback = None
                    instance.reviewed_by = None
                    instance.reviewed_at = None
                else:
                    raise serializers.ValidationError({"status": "Only admin users can revert a 'Completed' assessment status."})


        return data

    def update(self, instance, validated_data):
        request = self.context['request']
        if request.user.is_staff and (
            'hr_rating' in validated_data or 'hr_feedback' in validated_data or
            validated_data.get('status') == 'Completed'
        ):
            instance.reviewed_by = request.user
            if validated_data.get('status') == 'Completed' and not instance.reviewed_at:
                instance.reviewed_at = timezone.now()

        new_status = validated_data.get('status')
        if new_status:
            instance.status = new_status
            if new_status == 'Completed' and (not instance.hr_rating or not instance.hr_feedback):
                raise serializers.ValidationError("HR rating and feedback are required to complete an assessment.")

        return super().update(instance, validated_data)


class UserApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'is_approved']
        read_only_fields = ['username', 'email', 'role']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']  