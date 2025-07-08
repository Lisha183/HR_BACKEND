from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import JSONField
from decimal import Decimal


class CustomUser(AbstractUser):
    USER_ROLES = (
        ('admin', 'Admin'),
        ('employee', 'Employee'),
    )
    role = models.CharField(
        max_length=20,
        choices=USER_ROLES,
        default='employee',
        help_text="User's role in the system (Admin or Employee)."
    )
    is_approved = models.BooleanField(
        default=False,
        help_text="Designates whether this user's account is approved by an admin."
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

class Department(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Name of the department (e.g., HR, Engineering)"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Brief description of the department's function."
    )

    class Meta:
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        ordering = ['name']

    def __str__(self):
        return self.name

class EmployeeProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='employee_profile',
        help_text='The associated user account for this employee profile.'
    )
    full_name = models.CharField(
        max_length=255,
        help_text='Full name of the employee.'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Employee's phone number."
    )
    address = models.TextField(
        blank=True,
        null=True,
        help_text="Employee's residential address."
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        help_text="Employee's date of birth."
    )
    hire_date = models.DateField(
        default=timezone.now,
        help_text='Date when the employee was hired.'
    )
    job_title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Employee's job title."
    )
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Employee's monthly or annual salary."
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
        help_text='The department the employee belongs to.'
    )

    class Meta:
        verbose_name = "Employee Profile"
        verbose_name_plural = "Employee Profiles"
        ordering = ['full_name'] 

    def __str__(self):
        return self.full_name

class LeaveRequest(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
    )

    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='leave_requests',
        help_text='The employee who submitted the leave request.'
    )
    leave_type = models.CharField(
        max_length=50,
        help_text='Type of leave (e.g., Sick, Vacation, Personal).'
    )
    start_date = models.DateField(
        help_text='Start date of the leave.'
    )
    end_date = models.DateField(
        help_text='End date of the leave.'
    )
    reason = models.TextField(
        help_text='Reason for the leave request.'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending',
        help_text='Current status of the leave request.'
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp when the leave request was submitted.'
    )
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leave_requests',
        help_text='Admin user who approved/rejected the request.'
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when the leave request was approved/rejected.'
    )
    comments = models.TextField(
        blank=True,
        null=True,
        help_text='Comments from the approver/reviewer.'
    )

    class Meta:
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"
        ordering = ['-requested_at'] 

    def __str__(self):
        return f"Leave Request for {self.employee.username} ({self.start_date} to {self.end_date}) - {self.status}"

class Payroll(models.Model):
    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='payroll_records',
        help_text='The employee associated with this payroll record.'
    )
    pay_period_start = models.DateField(
        help_text='Start date of the pay period.'
    
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    social_security_deduction = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=0.00,
    help_text='Social security deduction for the period.'
)

    tax_deduction = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=0.00,  
    help_text='Tax deduction for the period.'
)

    pay_period_end = models.DateField(
        help_text='End date of the pay period.'
    )
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, help_text='Basic salary of the employee.')

    gross_pay = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Gross pay for the period.'
    )
  

    bonuses = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Bonuses for the pay period.'
    )
    allowances = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=0.00,
    help_text='Allowances for the period.'
)
    deductions = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text='Total deductions for the period.'
    )
    net_pay = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Net pay after deductions.'
    )
    payout_date = models.DateField(
        help_text='Date the payroll was paid out.'
    )
  


    class Meta:
        verbose_name = "Payroll Record"
        verbose_name_plural = "Payroll Records"
        ordering = ['-pay_period_end'] 

    def __str__(self):
        return f"Payroll for {self.employee.username} ({self.pay_period_start} to {self.pay_period_end})"

class AttendanceRecord(models.Model):
    RECORD_TYPE_CHOICES = (
        ('clock_in', 'Clock In'),
        ('clock_out', 'Clock Out'),
    )

    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text='The employee associated with this attendance record.'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp of the attendance event.'
    )
    record_type = models.CharField(
        max_length=10,
        choices=RECORD_TYPE_CHOICES,
        help_text='Type of attendance record (Clock In or Clock Out).'
    )

    class Meta:
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        ordering = ['-timestamp'] 

    def __str__(self):
        return f"{self.employee.username} - {self.record_type} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class SelfAssessment(models.Model):
    QUARTER_CHOICES = (
        (1, 'Q1'),
        (2, 'Q2'),
        (3, 'Q3'),
        (4, 'Q4'),
    )
    
    STATUS_CHOICES = (
        ('Pending HR Review', 'Pending HR Review'),
        ('Completed', 'Completed'),
    )

    RATING_CHOICES = [
        (1, '1 - Needs Improvement'),
        (2, '2 - Developing'),
        (3, '3 - Meets Expectations'),
        (4, '4 - Exceeds Expectations'),
        (5, '5 - Outstanding'),
    ]

    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='self_assessments',
        help_text='The employee who submitted this self-assessment.'
    )
    quarter_number = models.IntegerField(
        choices=QUARTER_CHOICES,
        help_text='The quarter number for this assessment (1-4).'
    )
    year = models.IntegerField(
        help_text='The year for this assessment (e.g., 2025).'
    )
    employee_answers = JSONField(
        default=list, 
        help_text='JSON array of employee self-assessment answers. Each object must have question_id and rating.'
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Timestamp when the employee submitted the self-assessment.'
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Pending HR Review',
        help_text='Current status of the self-assessment review process.'
    )

    hr_rating = models.IntegerField(
        choices=RATING_CHOICES,
        null=True,
        blank=True,
        help_text='HR’s rating for the employee’s performance.'
    )
    hr_feedback = models.TextField(
        null=True,
        blank=True,
        help_text='HR’s feedback on the employee’s performance.'
    )
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_reviewed_assessments',
        help_text='The HR user who reviewed this assessment.'
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when the HR review was completed.'
    )

    class Meta:
        verbose_name = "Self-Assessment & HR Review"
        verbose_name_plural = "Self-Assessments & HR Reviews"
        unique_together = ('employee', 'quarter_number', 'year')
        ordering = ['-year', '-quarter_number', 'employee__username']

    def __str__(self):
        return f"{self.employee.username} - Q{self.quarter_number} {self.year} ({self.status})"

    def save(self, *args, **kwargs):
        if self.hr_rating is not None and self.hr_feedback and self.status == 'Completed' and not self.reviewed_at:
            self.reviewed_at = timezone.now()
        super().save(*args, **kwargs)


class MeetingSlot(models.Model):

    hr_reviewer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='scheduled_meetings',
                                   limit_choices_to={'is_staff': True}, 
                                   help_text="The HR/Admin user who scheduled this meeting slot.")
    
    date = models.DateField(help_text="Date of the meeting slot.")
    start_time = models.TimeField(help_text="Start time of the meeting slot.")
    end_time = models.TimeField(help_text="End time of the meeting slot.")
    
    is_booked = models.BooleanField(default=False,
                                    help_text="Indicates if the slot has been booked by an employee.")
    booked_by_employee = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='booked_meeting_slots',
                                           limit_choices_to={'role': 'employee'}, 
                                           help_text="The employee who booked this meeting slot (if booked).")
    
    self_assessment = models.OneToOneField(SelfAssessment, on_delete=models.SET_NULL, null=True, blank=True,
                                           related_name='meeting_slot',
                                           help_text="The self-assessment this meeting is for (optional).")

    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the slot was created.")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the slot was last updated.")

    class Meta:
        verbose_name = "Meeting Slot"
        verbose_name_plural = "Meeting Slots"
        ordering = ['date', 'start_time'] 
        unique_together = ('hr_reviewer', 'date', 'start_time')

    def __str__(self):
        status_str = "Booked" if self.is_booked else "Available"
        employee_str = f" by {self.booked_by_employee.username}" if self.booked_by_employee else ""
        return f"{self.date} {self.start_time}-{self.end_time} ({status_str}{employee_str})"

