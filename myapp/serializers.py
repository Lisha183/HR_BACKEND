from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone 
from .models import CustomUser, EmployeeProfile, LeaveRequest, Payroll, AttendanceRecord, Department, SelfAssessment, MeetingSlot 

User = get_user_model()
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name'] 

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=CustomUser.USER_ROLES, default='employee', required=False)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'role']

    def create(self, validated_data):
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=validated_data.get('role', 'employee'),
            is_approved=False
        )
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = CustomUser.objects.filter(username=username).first()

            if not user:
                raise serializers.ValidationError("Invalid credentials.")

            if not user.is_approved:
                raise serializers.ValidationError("Your account is pending approval by an administrator.")

            user = authenticate(request=self.context.get('request'), username=username, password=password)

            if not user:
                raise serializers.ValidationError("Invalid credentials.")
            
        else:
            raise serializers.ValidationError("Must include 'username' and 'password'.")

        return user


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'is_approved', 'is_staff', 'date_joined', 'last_login']
        read_only_fields = ['username', 'email', 'role', 'is_staff', 'date_joined', 'last_login']


class DepartmentSerializer(serializers.ModelSerializer):
  
    class Meta:
        model = Department
        fields = '__all__'

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Department name cannot be empty.")
        return value


class EmployeeProfileSerializer(serializers.ModelSerializer):

    user_username = serializers.ReadOnlyField(source='user.username')
    user_email = serializers.ReadOnlyField(source='user.email')
    department_name = serializers.ReadOnlyField(source='department.name', allow_null=True)

    username = serializers.CharField(write_only=True, required=False)  

    class Meta:
        model = EmployeeProfile
        fields = '__all__'
        read_only_fields = ['user']

    def validate(self, data):
        request = self.context.get('request')
        username = data.pop('username', None)

        if request.method == 'POST':  
            if not username:
                raise serializers.ValidationError({"username": "Username is required."})
            
            try:
                user = CustomUser.objects.get(username=username)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({"username": "User with this username does not exist."})

            if user.is_staff:
                raise serializers.ValidationError({"user": "Employee profiles cannot be assigned to admin users. Please select a regular (non-staff) user."})

            if EmployeeProfile.objects.filter(user=user).exists():
                raise serializers.ValidationError({    "user": "An employee profile already exists for this user."
})

            data['user'] = user 
        else:
            pass
        return data

class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_username = serializers.ReadOnlyField(source='employee.username')
    approved_by_username = serializers.ReadOnlyField(source='approved_by.username')

    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ['employee', 'requested_at', 'approved_by', 'approval_date', 'comments']


class PayrollSerializer(serializers.ModelSerializer):
    employee_username = serializers.ReadOnlyField(source='employee.username')

    class Meta:
        model = Payroll
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at' ]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    employee_username = serializers.ReadOnlyField(source='employee.username')

    class Meta:
        model = AttendanceRecord
        fields = '__all__'
        read_only_fields = ['employee', 'timestamp']


class UserApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'is_approved']
        read_only_fields = ['username', 'email', 'role']


class SelfAssessmentSerializer(serializers.ModelSerializer):
    employee_username = serializers.ReadOnlyField(source='employee.username')
    reviewed_by_username = serializers.ReadOnlyField(source='reviewed_by.username')

    class Meta:
        model = SelfAssessment
        fields = [
            'id', 'employee', 'employee_username', 'quarter_number', 'year',
            'employee_answers',
            'submitted_at', 'status',
            'hr_rating', 'hr_feedback', 'reviewed_by', 'reviewed_by_username', 'reviewed_at'
        ]
        read_only_fields = [
            'id', 'employee', 'employee_username', 'submitted_at',
            'reviewed_by', 'reviewed_by_username', 'reviewed_at'
        ]
        extra_kwargs = {
            'quarter_number': {'required': True, 'allow_null': False},
            'year': {'required': True, 'allow_null': False},
            'employee_answers': {'required': True, 'allow_null': False},
            'hr_rating': {'required': False, 'allow_null': True},
            'hr_feedback': {'required': False, 'allow_blank': True},
        }

    def validate(self, data):
        request_method = self.context['request'].method
        request_user = self.context['request'].user
        reviewed_by = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(),
        required=False,
        allow_null=True
    )

        if request_method == 'POST':
            if not request_user.is_authenticated or request_user.is_staff:
                raise serializers.ValidationError("Only authenticated employees can submit self-assessments.")

            employee = request_user
            quarter_number = data.get('quarter_number')
            year = data.get('year')

            if SelfAssessment.objects.filter(employee=employee, quarter_number=quarter_number, year=year).exists():
                raise serializers.ValidationError(
                    f"A self-assessment for Q{quarter_number} {year} already exists for this employee. You can only submit one per quarter/year."
                )

            employee_answers = data.get('employee_answers')
            if not isinstance(employee_answers, list) or not employee_answers:
                raise serializers.ValidationError({"employee_answers": "Employee answers must be a non-empty list."})

            for i, qa in enumerate(employee_answers):
                if not isinstance(qa, dict):
                    raise serializers.ValidationError({f"employee_answers[{i}]": "Each answer must be an object."})
                if 'question_id' not in qa or not qa['question_id']:
                    raise serializers.ValidationError({f"employee_answers[{i}]": "Missing 'question_id' in answer."})
                if 'rating' not in qa or not isinstance(qa['rating'], int) or not (1 <= qa['rating'] <= 5):
                    raise serializers.ValidationError({f"employee_answers[{i}]": "Rating must be an integer between 1 and 5."})
                

            if any(field in data for field in ['hr_rating', 'hr_feedback', 'status', 'reviewed_by', 'reviewed_at']):
                raise serializers.ValidationError("Employees cannot set HR review fields during submission.")

        if request_method in ['PUT', 'PATCH']:
            if not request_user.is_authenticated or not request_user.is_staff:
                raise serializers.ValidationError("Only authenticated admin users can update self-assessments.")
            
            
            

            instance = self.instance
            if not request_user.is_staff and 'employee_answers' in data:
                 raise serializers.ValidationError({"employee_answers": "Employees cannot modify their self-assessment after submission."})

            new_status = data.get('status', instance.status)
            if new_status == 'Completed':
                if (data.get('hr_rating') is None and instance.hr_rating is None) or \
                   (data.get('hr_feedback') is None and instance.hr_feedback is None or data.get('hr_feedback', '') == ''):
                    raise serializers.ValidationError({"hr_rating": "HR Rating and Feedback are required to mark as Completed."})
                
                if not data.get('reviewed_by') and not instance.reviewed_by:
                        data['reviewed_by'] = request_user


            elif instance.status == 'Completed' and new_status != 'Completed':
                if request_user.is_staff:
                    data['hr_rating'] = None
                    data['hr_feedback'] = None
                    data['reviewed_by'] = None
                    data['reviewed_at'] = None
                else:
                    raise serializers.ValidationError({"status": "Only admin users can revert a 'Completed' assessment status."})

        return data

    def update(self, instance, validated_data):
        request = self.context['request']
        
        if request.user.is_staff:
            if 'hr_rating' in validated_data or 'hr_feedback' in validated_data or validated_data.get('status') == 'Completed':
                instance.reviewed_by = request.user
                if validated_data.get('status') == 'Completed' and not instance.reviewed_at:
                    instance.reviewed_at = timezone.now()

        if 'status' in validated_data:
            instance.status = validated_data['status']

        if 'hr_rating' in validated_data:
            instance.hr_rating = validated_data['hr_rating']
        if 'hr_feedback' in validated_data:
            instance.hr_feedback = validated_data['hr_feedback']

        instance.save()
        return instance


class MeetingSlotSerializer(serializers.ModelSerializer):
    hr_reviewer_username = serializers.ReadOnlyField(source='hr_reviewer.username')
    booked_by_employee_username = serializers.ReadOnlyField(source='booked_by_employee.username', allow_null=True)
    self_assessment_id = serializers.ReadOnlyField(source='self_assessment.id')
    booked_employee_profile_id = serializers.SerializerMethodField()

    class Meta:
        model = MeetingSlot
        fields = [
            'id', 'hr_reviewer', 'hr_reviewer_username',
            'date', 'start_time', 'end_time',
            'is_booked', 'booked_by_employee', 'booked_by_employee_username',
            'self_assessment', 'self_assessment_id',
            'booked_employee_profile_id', 
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'hr_reviewer',
            'is_booked', 'booked_by_employee', 'booked_by_employee_username',
            'hr_reviewer_username', 'created_at', 'updated_at', 'self_assessment_id',
            'booked_employee_profile_id'
        ]
        extra_kwargs = {
            'self_assessment': {'required': False, 'allow_null': True}
        }

    def get_booked_employee_profile_id(self, obj):
        if obj.booked_by_employee:
            try:
                return obj.booked_by_employee.employee_profile.id
            except EmployeeProfile.DoesNotExist:
                return None
        return None

    def validate(self, data):
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("End time must be after start time.")


        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("End time must be after start time.")
        
        if self.context['request'].method == 'POST':
            current_date = timezone.localdate()
            current_time = timezone.localtime().time()

            if data.get('date') == current_date and start_time < current_time:
                raise serializers.ValidationError("Cannot create a meeting slot in the past for today's date.")
            if data.get('date') < current_date:
                raise serializers.ValidationError("Cannot create a meeting slot for a past date.")

        return data
