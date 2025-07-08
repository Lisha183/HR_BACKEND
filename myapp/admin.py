from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, EmployeeProfile, LeaveRequest, Payroll, AttendanceRecord, Department,MeetingSlot
from django.utils import timezone

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'is_approved')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'is_approved')}),
    )
    list_display = ('username', 'email', 'role', 'is_approved', 'is_staff', 'is_active')
    list_filter = ('role', 'is_approved', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'role')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)
    list_filter = ('name',) 

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'job_title', 'department', 'hire_date', 'salary') 
    search_fields = ('full_name', 'user__username', 'job_title', 'department__name')
    list_filter = ('department', 'job_title', 'hire_date')
    raw_id_fields = ('user',) 


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status', 'requested_at', 'approved_by')
    list_filter = ('status', 'leave_type', 'requested_at', 'approved_by')
    search_fields = ('employee__username', 'reason')
    raw_id_fields = ('employee', 'approved_by')
    actions = ['approve_leave_requests', 'reject_leave_requests']

    def approve_leave_requests(self, request, queryset):
        for obj in queryset:
            if obj.status == 'Pending':
                obj.status = 'Approved'
                obj.approved_by = request.user
                obj.approval_date = timezone.now()
                obj.save()
        self.message_user(request, "Selected leave requests have been approved.")
    approve_leave_requests.short_description = "Approve selected leave requests"

    def reject_leave_requests(self, request, queryset):
        for obj in queryset:
            if obj.status == 'Pending':
                obj.status = 'Rejected'
                obj.approved_by = request.user
                obj.approval_date = timezone.now()
                obj.save()
        self.message_user(request, "Selected leave requests have been rejected.")
    reject_leave_requests.short_description = "Reject selected leave requests"


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('employee', 'pay_period_start', 'pay_period_end', 'gross_pay', 'net_pay', 'payout_date')
    list_filter = ('pay_period_start', 'payout_date')
    search_fields = ('employee__username',)
    raw_id_fields = ('employee',)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('employee', 'timestamp', 'record_type')
    list_filter = ('record_type', 'timestamp')
    search_fields = ('employee__username',)
    raw_id_fields = ('employee',)


@admin.register(MeetingSlot)
class MeetingSlotAdmin(admin.ModelAdmin):
    list_display = ('date', 'start_time', 'end_time', 'hr_reviewer', 'is_booked', 'booked_by_employee', 'self_assessment', 'created_at')
    list_filter = ('is_booked', 'date', 'hr_reviewer', 'booked_by_employee')
    search_fields = ('hr_reviewer__username', 'booked_by_employee__username', 'self_assessment__employee__username')
    raw_id_fields = ('hr_reviewer', 'booked_by_employee', 'self_assessment') 
    readonly_fields = ('created_at', 'updated_at') 