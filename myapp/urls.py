from django.urls import path
from .views import (
    csrf_test,
    RegisterView,
    LoginView,
    LogoutView,
    current_user_details,
    EmployeeProfileList,
    EmployeeProfileDetail,
    EmployeeLeaveRequestListCreateView,
    EmployeeLeaveRequestDetailView,
    AdminLeaveRequestListView,
    AdminLeaveRequestDetailView,
    AdminPayrollListCreate,
    AdminPayrollDetail,
    EmployeePayrollList,
    EmployeePayrollDetail,
    AttendanceListCreateView,
    AdminAttendanceListView,
    AdminUserApprovalListView,
    AdminUserApprovalDetailView,
    DepartmentListCreateView,
    DepartmentDetailView,
    EmployeeSelfAssessmentListCreateView,
    AdminSelfAssessmentListView,
    AdminSelfAssessmentDetailView,

)

urlpatterns = [
    path('csrf/', csrf_test, name='csrf_test'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('user/me/', current_user_details, name='current_user_details'),

    path('employee-profiles/', EmployeeProfileList.as_view(), name='employee-profile-list'),
    path('employee-profiles/<int:pk>/', EmployeeProfileDetail.as_view(), name='employee-profile-detail'),

    path('employee/leave-requests/', EmployeeLeaveRequestListCreateView.as_view(), name='employee-leave-request-list-create'),
    path('employee/leave-requests/<int:pk>/', EmployeeLeaveRequestDetailView.as_view(), name='employee-leave-request-detail'),
    path('admin/leave-requests/', AdminLeaveRequestListView.as_view(), name='admin-leave-request-list'),
    path('admin/leave-requests/<int:pk>/', AdminLeaveRequestDetailView.as_view(), name='admin-leave-request-detail'),

    path('admin/payroll/', AdminPayrollListCreate.as_view(), name='admin-payroll-list-create'),
    path('admin/payroll/<int:pk>/', AdminPayrollDetail.as_view(), name='admin-payroll-detail'),
    path('employee/payslips/', EmployeePayrollList.as_view(), name='employee-payslip-list'),
    path('employee/payslips/<int:pk>/', EmployeePayrollDetail.as_view(), name='employee-payslip-detail'),

    path('attendance/', AttendanceListCreateView.as_view(), name='attendance-list-create'),
    path('admin/attendance/', AdminAttendanceListView.as_view(), name='admin-attendance-list'),

    path('admin/users/pending-approval/', AdminUserApprovalListView.as_view(), name='admin-user-pending-approval-list'),
    path('admin/users/<int:pk>/approve/', AdminUserApprovalDetailView.as_view(), name='admin-user-approve'),

    path('admin/departments/', DepartmentListCreateView.as_view(), name='department-list-create'),
    path('admin/departments/<int:pk>/', DepartmentDetailView.as_view(), name='department-detail'),

    path('employee/self-assessments/', EmployeeSelfAssessmentListCreateView.as_view(), name='employee-self-assessment-list-create'),
    path('admin/self-assessments/', AdminSelfAssessmentListView.as_view(), name='admin-self-assessment-list'),
    path('admin/self-assessments/<int:pk>/', AdminSelfAssessmentDetailView.as_view(), name='admin-self-assessment-detail'),



]
