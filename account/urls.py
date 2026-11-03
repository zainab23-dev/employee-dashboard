from django.urls import path
from . import views

urlpatterns = [
    # ==================== AUTHENTICATION ====================
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ==================== DASHBOARDS ====================
    path('dashboard/', views.employee_dashboard, name='dashboard'),  # Main dashboard
    path('employee/dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('ceo/dashboard/', views.ceo_dashboard, name='ceo_dashboard'),
    
    # ==================== EMPLOYEE ATTENDANCE & BREAKS ====================
    path('employee/clock-in/', views.clock_in, name='clock_in'),
    path('employee/clock-out/', views.clock_out, name='clock_out'),
    path('employee/break/start/', views.start_break, name='start_break'),
    path('employee/break/end/', views.end_break, name='end_break'),
    path('employee/break/reason/', views.break_reason, name='break_reason'),
    
    # ==================== EMPLOYEE MANAGEMENT ====================
    path('employee-management/', views.employee_management, name='employee_management'),
    path('employee/<int:employee_id>/', views.employee_detail, name='employee_detail'),
    path('api/employee/<int:employee_id>/upload-photo/', views.upload_employee_photo, name='upload_employee_photo'),
    
    # API endpoints for employee CRUD
    path('api/employee/<int:employee_id>/', views.get_employee, name='get_employee'),
    path('api/employee/add/', views.add_employee, name='add_employee'),
    path('api/employee/update/<int:employee_id>/', views.update_employee, name='update_employee'),
    path('api/employee/delete/<int:employee_id>/', views.delete_employee, name='delete_employee'),
    
    
    # ==================== LEAVE MANAGEMENT ====================
    path('employee/apply-leave/', views.apply_leave, name='apply_leave'),
    path('employee/leave-success/', views.leave_success, name='leave_success'),
    path('employee/leave-history/', views.leave_history, name='leave_history'),
    path('admin/leaves/', views.leave_requests, name='leave_requests'),
    path('admin/leaves/<int:leave_id>/approve/', views.approve_leave, name='approve_leave'),
    path('admin/leaves/<int:leave_id>/reject/', views.reject_leave, name='reject_leave'),
    path('admin/leaves/<int:leave_id>/detail/', views.leave_detail, name='leave_detail'),
    
    # ==================== ATTENDANCE MANAGEMENT ====================
    path('admin/attendance/', views.admin_attendance, name='admin_attendance'),
    path('api/attendance/mark-absent/<int:employee_id>/', views.mark_absent, name='mark_absent'),
    path('api/attendance/<int:attendance_id>/update/', views.update_attendance_api, name='update_attendance_api'),
    
    
    # ==================== TASK MANAGEMENT ====================
    path('tasks/', views.task_dashboard, name='task_dashboard'),
    
    # Admin Task URLs
    path('admin/tasks/', views.admin_tasks, name='admin_tasks'),
    path('admin/tasks/create/', views.create_task, name='create_task'),
    path('admin/tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('admin/tasks/<int:task_id>/update/', views.update_task, name='update_task'),
    path('admin/tasks/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('admin/tasks/reports/', views.task_reports, name='task_reports'),
    path('admin/tasks/dashboard/', views.admin_task_dashboard, name='admin_task_dashboard'),
    
    # Employee Task URLs
    path('employee/tasks/', views.employee_tasks, name='employee_tasks'),
    path('employee/tasks/<int:task_id>/status/', views.update_task_status, name='update_task_status'),
    path('employee/tasks/<int:task_id>/comment/', views.add_task_comment, name='add_task_comment'),
    path('employee/tasks/<int:task_id>/', views.task_detail, name='employee_task_detail'),
    
    # Category Management
    path('admin/categories/', views.manage_categories, name='manage_categories'),
    path('admin/categories/add/', views.add_category, name='add_category'),
    path('admin/categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    
    # ==================== PROJECT MANAGEMENT ====================
    # Admin/Team Leader URLs
    path('admin/projects/dashboard/', views.admin_project_dashboard, name='admin_project_dashboard'),
    path('admin/projects/create/', views.admin_create_project, name='admin_create_project'),
    path('admin/projects/', views.admin_project_list, name='admin_project_list'),
    path('admin/projects/<str:project_code>/', views.admin_project_detail, name='admin_project_detail'),
    
    # Project Task URLs
    path('admin/projects/<str:project_code>/tasks/create/', views.admin_create_task, name='admin_create_task'),
    path('admin/tasks/<str:task_code>/', views.admin_task_detail, name='admin_task_detail'),
    
    # Team URLs - Complete CRUD
    path('admin/teams/', views.team_list, name='team_list'),
    path('admin/teams/create/', views.create_team, name='create_team'),
    path('admin/teams/<int:team_id>/', views.team_detail, name='team_detail'),
    path('admin/teams/<int:team_id>/update/', views.update_team, name='update_team'),
    path('admin/teams/<int:team_id>/delete/', views.delete_team, name='delete_team'),
    path('admin/teams/<int:team_id>/add-members/', views.add_team_members, name='add_team_members'),
    path('admin/teams/<int:team_id>/remove-member/<int:member_id>/', views.remove_team_member, name='remove_team_member'),
    path('admin/teams/<int:team_id>/make-leader/<int:member_id>/', views.make_team_leader, name='make_team_leader'),
    
    # Employee Project URLs
    path('employee/projects/dashboard/', views.employee_project_dashboard, name='employee_project_dashboard'),
    path('employee/projects/', views.employee_projects, name='employee_projects'),
    path('employee/projects/<str:project_code>/discussion/', views.employee_discussion, name='employee_discussion'),
    path('employee/projects/<str:project_code>/', views.employee_project_detail, name='employee_project_detail'),
    path('employee/tasks/<str:task_code>/', views.employee_task_detail, name='employee_task_detail'),
    
    # ==================== TASK HANDOFF ====================
    path('handoffs/', views.handoff_management, name='handoff_management'),
    path('tasks/<str:task_code>/handoff/', views.request_task_handoff, name='request_task_handoff'),
    path('handoffs/<int:handoff_id>/respond/', views.respond_to_handoff, name='respond_to_handoff'),
    path('handoffs/alerts/', views.check_handoff_alerts, name='handoff_alerts'),
    
    # ==================== COMMENTS ====================
    path('comments/add/', views.add_comment, name='add_comment'),
    path('comments/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    
    # ==================== TASK PROGRESS ====================
    path('tasks/<str:task_code>/progress/', views.update_task_progress, name='update_task_progress'),
    path('tasks/<str:task_code>/status/', views.employee_update_task_status, name='employee_update_task_status'),
    
    # ==================== NOTIFICATIONS ====================
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # ==================== PAYROLL ====================
    # HR/Admin
    path('payrolls/', views.payroll_list, name='payroll_list'),
    path('payrolls/generate/', views.generate_payroll, name='generate_payroll'),
    path('payrolls/<int:payroll_id>/', views.payroll_detail, name='payroll_detail'),
    path('payrolls/<int:payroll_id>/add-employees/', views.add_payroll_employees, name='add_payroll_employees'),
    path('payrolls/<int:payroll_id>/submit/', views.submit_payroll_for_approval, name='submit_payroll_for_approval'),
    path('payrolls/employee/<int:payroll_employee_id>/edit/', views.edit_payroll_employee, name='edit_payroll_employee'),
    path('payrolls/employee/<int:payroll_employee_id>/get/', views.get_payroll_employee, name='get_payroll_employee'),
path('payrolls/employee/<int:payroll_employee_id>/edit/', views.edit_payroll_employee, name='edit_payroll_employee'),
    
    # CEO Payroll
    path('ceo/payrolls/', views.ceo_payroll_dashboard, name='ceo_payroll_dashboard'),
    path('ceo/payrolls/<int:payroll_id>/', views.ceo_payroll_detail, name='ceo_payroll_detail'),
    path('ceo/payrolls/<int:payroll_id>/approve/', views.approve_payroll, name='approve_payroll'),
    path('ceo/payrolls/<int:payroll_id>/reject/', views.reject_payroll, name='reject_payroll'),
    
    # Employee Payroll
    path('employee/payrolls/', views.employee_payrolls, name='employee_payrolls'),
    path('employee/payrolls/<int:payroll_employee_id>/', views.employee_payslip, name='employee_payslip'),
    path('employee/payrolls/<int:payroll_employee_id>/download/', views.download_payslip_pdf, name='download_payslip'),




     # ==================== CHAT URLS ====================
    # TODO: chat views (chat_dashboard, chat_room, ...) are missing from views.py.
    
    # Main Chat
    # [DISABLED - chat views missing from views.py] path('chat/', views.chat_dashboard, name='chat_dashboard'),
    # [DISABLED - chat views missing from views.py] path('chat/room/<int:room_id>/', views.chat_room, name='chat_room'),
    
    # Messages
    # [DISABLED - chat views missing from views.py] path('chat/room/<int:room_id>/send/', views.chat_send_message, name='chat_send_message'),
    # [DISABLED - chat views missing from views.py] path('chat/room/<int:room_id>/poll/', views.chat_poll_messages, name='chat_poll_messages'),
    
    # Users
    # [DISABLED - chat views missing from views.py] path('chat/search/', views.chat_search_users, name='chat_search_users'),
    
    # Requests
    # [DISABLED - chat views missing from views.py] path('chat/request/send/', views.chat_send_request, name='chat_send_request'),
    # [DISABLED - chat views missing from views.py] path('chat/requests/', views.chat_requests_list, name='chat_requests'),
    # [DISABLED - chat views missing from views.py] path('chat/request/<int:request_id>/approve/', views.chat_approve_request, name='chat_approve_request'),
    # [DISABLED - chat views missing from views.py] path('chat/request/<int:request_id>/reject/', views.chat_reject_request, name='chat_reject_request'),
    
    # Monitor
    # [DISABLED - chat views missing from views.py] path('chat/monitor/', views.chat_monitor_dashboard, name='chat_monitor'),
    # [DISABLED - chat views missing from views.py] path('chat/monitor/room/<int:room_id>/', views.chat_monitor_room, name='chat_monitor_room'),

    # Notifications
    # [DISABLED - chat views missing from views.py] path('chat/notifications/', views.chat_get_notifications, name='chat_notifications'),
    # [DISABLED - chat views missing from views.py] path('chat/notification/<int:note_id>/read/', views.chat_mark_notification_read, name='chat_mark_read'),

    
]