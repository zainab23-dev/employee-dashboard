# standard library
import json
import logging
from functools import wraps
import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from urllib import request

# django core & extensions
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models, transaction
from django.db.models import (
    Avg, Count, ExpressionWrapper, F, IntegerField, Max, Q, Sum
)
from django.db.models.functions import Extract
from django.http import Http404, HttpResponse, JsonResponse
from django.template import Context, Template
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie

# local models & utils
from .models import (
    ActivityLog, Admin, Attendance, Break, Comment, Employee, LeaveRequest, 
    Notification, Payroll, PayrollApproval, PayrollEmployee, Project, 
    ProjectTask, Task, TaskAttachment, TaskCategory, TaskComment, 
    TaskHandoff, TaskHistory, Team, UserRole ,ChatRoom, ChatMessage, ChatRequest, ChatNotification,
)



# ==================== CHAT HELPER FUNCTIONS ====================

def get_user_role(user):
    """Get user role from UserRole model"""
    try:
        return user.role.role
    except:
        return 'employee'

def can_chat_directly(sender, recipient):
    """Check if users can chat directly without approval"""
    sender_role = get_user_role(sender)
    recipient_role = get_user_role(recipient)
    
    # Admin/CEO can chat with anyone
    if sender_role in ['admin', 'ceo']:
        return True
    
    # Employee can chat with Admin/CEO directly
    if recipient_role in ['admin', 'ceo']:
        return True
    
    # Check if room already exists
    from .models import ChatRoom
    return ChatRoom.objects.filter(
        participants=sender, is_active=True
    ).filter(participants=recipient).exists()

def create_chat_notification(user, message, type, link=''):
    """Create chat notification"""
    from .models import ChatNotification
    ChatNotification.objects.create(
        user=user,
        message=message,
        type=type,
        link=link
    )


    
# ==================== LOGIN / AUTH VIEWS ====================
def login_view(request):
    """Handle user login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            
            # Check if user is admin (has Admin record)
            admin = Admin.objects.filter(user=user).first()
            if admin:
                if admin.role == 'ceo':
                    return redirect('ceo_dashboard')  # CEO ka alag dashboard
                else:
                    return redirect('admin_dashboard')  # Admin/HR ka dashboard
            
            # Check if user is employee
            try:
                employee = Employee.objects.get(email=user.email)
                return redirect('employee_dashboard')
            except Employee.DoesNotExist:
                return redirect('employee_dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')

@login_required
def logout_view(request):
    """Handle user logout"""
    logout(request)
    return redirect('login')


@login_required
def ceo_dashboard(request):
    """CEO Dashboard"""
    if not is_ceo(request.user):
        messages.error(request, 'Access denied. CEO only.')
        return redirect('admin_dashboard')
    
    # Statistics
    total_employees = Employee.objects.count()
    total_payrolls = Payroll.objects.count()
    pending_approvals = Payroll.objects.filter(status='pending_ceo').count()
    
    # Recent payrolls pending approval
    pending_payrolls = Payroll.objects.filter(status='pending_ceo')[:5]
    
    context = {
        'user': request.user,
        'admin': Admin.objects.get(user=request.user),
        'total_employees': total_employees,
        'total_payrolls': total_payrolls,
        'pending_approvals': pending_approvals,
        'pending_payrolls': pending_payrolls,
        'current_date': datetime.now().strftime("%B %d, %Y"),
    }
    return render(request, 'ceo_dashboard.html', context)


# ==================== DASHBOARD VIEWS ====================

@login_required
def employee_dashboard(request):
    """Employee dashboard view"""
    now = timezone.now()
    try:
        employee = Employee.objects.get(email=request.user.email)
        # Use the same attendance date as the clock-in and clock-out views.
        attendance = Attendance.objects.filter(
            employee=employee, date=now.date()
        ).first()
        active_break = None
        if attendance and attendance.check_in and not attendance.check_out:
            active_break = Break.objects.filter(
                attendance=attendance, end_time__isnull=True
            ).first()

        context = {
            'user': request.user,
            'employee': employee,
            'attendance': attendance,
            'active_break': active_break,
            'now': now,
            'current_date': datetime.now().strftime("%B %d, %Y"),
            'tasks_count': 8,
            'completed_tasks': 3,
            'pending_tasks': 5,
            'projects': [
                {'name': 'Website Redesign', 'progress': 75},
                {'name': 'Mobile App', 'progress': 45},
            ],
            'team_members': [
                {'name': 'John Doe', 'role': 'Developer', 'initials': 'JD'},
                {'name': 'Alice Smith', 'role': 'Designer', 'initials': 'AS'},
                {'name': 'Robert Johnson', 'role': 'Manager', 'initials': 'RJ'},
            ]
        }
    except Employee.DoesNotExist:
        context = {
            'user': request.user,
            'employee': None,
            'attendance': None,
            'active_break': None,
            'now': now,
            'current_date': datetime.now().strftime("%B %d, %Y"),
            'message': 'Employee profile not found',
            'tasks_count': 0,
            'projects': [],
            'team_members': []
        }
    
    return render(request, 'employee_dashboard.html', context)

@login_required
def admin_dashboard(request):
    """Admin dashboard view"""
    
    # Check if user is superuser or staff first
    if request.user.is_superuser or request.user.is_staff:
        # Superuser ke liye Admin record exist na bhi kare to bhi allow karo
        try:
            admin = Admin.objects.get(user=request.user)
        except Admin.DoesNotExist:
            # Agar Admin record nahi hai to temporary admin object banao
            admin = None
            messages.warning(request, 'Admin record not found. Some features may be limited.')
    else:
        # Agar na superuser hai na staff, to access deny
        messages.error(request, 'Access denied. Admin only.')
        return redirect('employee_dashboard')
    
    employees = Employee.objects.all()
    admins = Admin.objects.select_related('user').all()
    show_admin_link = request.user.is_staff or request.user.is_superuser
    
    context = {
        'user': request.user,
        'admin': admin,
        'employees': employees,
        'admins': admins,
        'total_employees': employees.count(),
        'total_admins': admins.count(),
        'show_admin_link': show_admin_link,
        'is_staff': request.user.is_staff,
        'is_superuser': request.user.is_superuser,
        'current_date': datetime.now().strftime("%B %d, %Y"),
    }
    
    return render(request, 'admin_dashboard.html', context)

# ==================== EMPLOYEE MANAGEMENT ====================

@login_required
def employee_management(request):
    """Employee management page"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('employee_dashboard')
    
    employees = Employee.objects.all()
    print("========== EMPLOYEE MANAGEMENT ==========")
    print("Employees queryset:", employees)
    print("Total employees:", employees.count())
    for emp in employees:
        print(f"ID: {emp.id}, Name: {emp.name}, Email: {emp.email}")
    print("=========================================")
    
    context = {
        'user': request.user,
        'admin': admin,
        'employees': employees,
        'total_employees': employees.count(),
        'current_date': datetime.now().strftime("%B %d, %Y"),
    }
    
    return render(request, 'employee_management.html', context)


@login_required
def employee_detail(request, employee_id):
    """Employee detail page with all information"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('employee_dashboard')
    
    employee = get_object_or_404(Employee, id=employee_id)
    
    # Get current month for display
    current_month = datetime.now().strftime("%B %Y")
    
    # These will be populated when you create the models
    # For now, using empty lists to avoid template errors
    attendances = []
    today_breaks = []
    salaries = []
    documents = []
    
    context = {
        'user': request.user,
        'admin': admin,
        'employee': employee,
        'attendances': attendances,
        'today_breaks': today_breaks,
        'salaries': salaries,
        'documents': documents,
        'current_month': current_month,
    }
    return render(request, 'employee_detail.html', context)

# ==================== EMPLOYEE API ENDPOINTS ====================

@login_required
def get_employee(request, employee_id):
    """Get employee data as JSON"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    try:
        employee = Employee.objects.get(id=employee_id)
        data = {
            'id': employee.id,
            'name': employee.name,
            'email': employee.email,
            'phone': employee.phone,
            'department': employee.department,
            'salary': str(employee.salary),
        }
        return JsonResponse({'success': True, 'employee': data})
    except Employee.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee not found'})

@login_required
def add_employee(request):
    """Add new employee"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            if Employee.objects.filter(email=data.get('email')).exists():
                return JsonResponse({'success': False, 'error': 'Employee with this email already exists'})
            
            employee = Employee.objects.create(
                name=data.get('name'),
                email=data.get('email'),
                phone=data.get('phone'),
                department=data.get('department'),
                salary=data.get('salary', 0),
            )
            
            # Create user account for employee
            username = data.get('email').split('@')[0]
            if not User.objects.filter(username=username).exists():
                User.objects.create_user(
                    username=username,
                    password='default123',
                    email=data.get('email')
                )
            
            return JsonResponse({'success': True, 'message': 'Employee added successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
def update_employee(request, employee_id):
    """Update employee information - Supports all fields"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(id=employee_id)
            
            # Parse JSON data
            if request.body:
                data = json.loads(request.body)
            else:
                data = request.POST
            
            print(f"Updating employee {employee_id} with data:", data)  # Debug
            
            # Update all fields that exist in the model
            fields_to_update = [
                'name', 'email', 'phone', 'alternate_phone', 'department', 
                'position', 'salary', 'date_of_birth', 'gender', 
                'marital_status', 'blood_group', 'nationality', 
                'present_address', 'permanent_address', 'city', 'postal_code',
                'emergency_contact_name', 'emergency_contact_phone', 
                'emergency_contact_relation', 'work_shift', 'weekly_off',
                'employment_type', 'status', 'bank_name', 'bank_account',
                'bank_branch', 'tax_id', 'social_security'
            ]
            
            for field in fields_to_update:
                if field in data and data[field] is not None and data[field] != '':
                    # Special handling for salary field
                    if field == 'salary':
                        try:
                            setattr(employee, field, float(data[field]))
                        except (ValueError, TypeError):
                            pass
                    else:
                        setattr(employee, field, data[field])
            
            # Check email uniqueness if changed
            new_email = data.get('email')
            if new_email and new_email != employee.email:
                if Employee.objects.filter(email=new_email).exists():
                    return JsonResponse({
                        'success': False, 
                        'error': 'Email already exists'
                    })
                employee.email = new_email
                
                # Update associated user email
                try:
                    user = User.objects.get(email=employee.email)
                    user.email = new_email
                    user.save()
                except User.DoesNotExist:
                    pass
            
            employee.save()
            print(f"Employee {employee_id} updated successfully")  # Debug
            
            return JsonResponse({
                'success': True, 
                'message': 'Employee updated successfully'
            })
            
        except Employee.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': 'Employee not found'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False, 
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            print(f"Error updating employee: {str(e)}")  # Debug
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False, 
        'error': 'Invalid request method'
    }, status=405)

@login_required
def delete_employee(request, employee_id):
    """Delete employee"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(id=employee_id)
            
            # Delete associated user if exists
            try:
                user = User.objects.get(email=employee.email)
                user.delete()
            except User.DoesNotExist:
                pass
            
            employee.delete()
            
            return JsonResponse({'success': True, 'message': 'Employee deleted successfully'})
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# ==================== PHOTO UPLOAD ====================

@login_required
def upload_employee_photo(request, employee_id):
    """Upload profile picture for employee"""
    if request.method == 'POST' and request.FILES.get('photo'):
        try:
            employee = get_object_or_404(Employee, id=employee_id)
            
            # Delete old photo if exists
            if employee.profile_picture:
                if os.path.isfile(employee.profile_picture.path):
                    os.remove(employee.profile_picture.path)
            
            # Save new photo
            employee.profile_picture = request.FILES['photo']
            employee.save()
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'No photo uploaded'})

# ==================== LEAVE MANAGEMENT ====================


@login_required
def apply_leave(request):
    """Employee apply for leave"""
    try:
        employee = Employee.objects.get(email=request.user.email)
    except Employee.DoesNotExist:
        messages.error(request, 'Employee profile not found.')
        return redirect('employee_dashboard')
    
    if request.method == 'POST':
        leave_type = request.POST.get('leave_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason')
        notes = request.POST.get('notes', '')
        alt_phone = request.POST.get('alt_phone', '')
        alt_email = request.POST.get('alt_email', '')
        handover_to = request.POST.get('handover_to', '')
        handover_notes = request.POST.get('handover_notes', '')
        
        if not all([leave_type, start_date, end_date, reason]):
            messages.error(request, 'All fields are required.')
            return redirect('apply_leave.html')
        
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        if start > end:
            messages.error(request, 'Start date cannot be after end date.')
            return redirect('apply_leave.html')
        
        if start < timezone.now().date():
            messages.error(request, 'Start date cannot be in the past.')
            return redirect('apply_leave.html')
        
        LeaveRequest.objects.create(
            employee=employee,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            reason=reason,
            notes=notes,
            status='pending'
        )
        
        messages.success(request, 'Leave request submitted successfully!')
        return redirect('leave_success')
    
    context = { 
        'employee': employee,
        'today': timezone.now().date().isoformat(),
    }
    return render(request, 'apply_leave.html', context)


@login_required
def leave_success(request):
    """Show leave request success page with details"""
    try:
        employee = Employee.objects.get(email=request.user.email)
        # Get the most recent pending leave request
        latest_leave = LeaveRequest.objects.filter(
            employee=employee, 
            status='pending'
        ).order_by('-created_at').first()
        
        context = {
            'employee': employee,
            'leave': latest_leave
        }
        return render(request, 'leave_success.html', context)
    except Employee.DoesNotExist:
        return redirect('employee_dashboard')

@staff_member_required
def approve_leave(request, leave_id):
    """Approve leave request with notes"""
    if request.method == 'POST':
        leave = get_object_or_404(LeaveRequest, id=leave_id)
        
        if leave.status != 'pending':
            return JsonResponse({
                'success': False,
                'error': f'This request is already {leave.status}'
            })
        
        data = json.loads(request.body)
        
        leave.status = 'approved'
        leave.review_notes = data.get('notes', '')
        leave.reviewed_by = request.user
        leave.review_date = timezone.now()
        leave.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Leave request approved'
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@staff_member_required
def reject_leave(request, leave_id):
    """Reject leave request with reason"""
    if request.method == 'POST':
        leave = get_object_or_404(LeaveRequest, id=leave_id)
        data = json.loads(request.body)
        remarks = data.get('remarks', '')
        
        if leave.status != 'pending':
            return JsonResponse({
                'success': False,
                'error': f'This request is already {leave.status}'
            })
        
        if not remarks:
            return JsonResponse({
                'success': False,
                'error': 'Please provide a reason for rejection'
            })
        
        leave.status = 'rejected'
        leave.review_notes = remarks
        leave.reviewed_by = request.user
        leave.review_date = timezone.now()
        leave.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Leave request rejected'
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@staff_member_required
def leave_detail(request, leave_id):
    """Get leave request details as JSON"""
    leave = get_object_or_404(LeaveRequest, id=leave_id)
    
    data = {
        'id': leave.id,
        'employee_name': leave.employee.name,
        'employee_email': leave.employee.email,
        'leave_type': leave.get_leave_type_display(),
        'start_date': leave.start_date.strftime('%d %B %Y'),
        'end_date': leave.end_date.strftime('%d %B %Y'),
        'days': leave.days_count(),
        'reason': leave.reason,
        'notes': leave.notes or '',
        'applied_on': leave.created_at.strftime('%d %B %Y, %I:%M %p'),
        'status': leave.status,
        'remarks': leave.review_notes,
        'approved_by': leave.reviewed_by.get_full_name() if leave.reviewed_by else None,
        'approved_at': leave.review_date.strftime('%d %B %Y, %I:%M %p') if leave.review_date else None,
    }
    
    return JsonResponse(data)


@staff_member_required
def leave_requests(request):
    """Admin view to manage all leave requests"""
    status = request.GET.get('status', '')
    leave_type = request.GET.get('type', '')
    department = request.GET.get('department', '')
    
    leaves = LeaveRequest.objects.all().order_by('-created_at')
    
    if status:
        leaves = leaves.filter(status=status)
    if leave_type:
        leaves = leaves.filter(leave_type=leave_type)
    if department:
        leaves = leaves.filter(employee__department=department)
    
    context = {
        'leaves': leaves,
        'pending_requests': LeaveRequest.objects.filter(status='pending').count(),
        'approved_requests': LeaveRequest.objects.filter(status='approved').count(),
        'rejected_requests': LeaveRequest.objects.filter(status='rejected').count(),
        'total_requests': LeaveRequest.objects.count(),
        'current_status': status,
        'current_type': leave_type,
    }
    
    return render(request, 'leave_requests.html', context)

@login_required
def leave_history(request):
    """Employee leave history page"""
    try:
        employee = Employee.objects.get(email=request.user.email)
    except Employee.DoesNotExist:
        messages.error(request, 'Employee profile not found.')
        return redirect('employee_dashboard')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    leave_type = request.GET.get('type', '')
    year = request.GET.get('year', '')
    
    # Base queryset
    leaves = LeaveRequest.objects.filter(employee=employee).order_by('-created_at')
    
    # Apply filters
    if status:
        leaves = leaves.filter(status=status)
    if leave_type:
        leaves = leaves.filter(leave_type=leave_type)
    if year:
        leaves = leaves.filter(start_date__year=year)
    
    # Calculate leave balances
    annual_total = 15
    sick_total = 10
    personal_total = 5
    
    current_year = timezone.now().year
    
    # Calculate used leaves
    annual_used = 0
    for leave in LeaveRequest.objects.filter(
        employee=employee,
        leave_type='annual',
        status='approved',
        start_date__year=current_year
    ):
        annual_used += leave.days_count()
    
    sick_used = 0
    for leave in LeaveRequest.objects.filter(
        employee=employee,
        leave_type='sick',
        status='approved',
        start_date__year=current_year
    ):
        sick_used += leave.days_count()
    
    personal_used = 0
    for leave in LeaveRequest.objects.filter(
        employee=employee,
        leave_type='personal',
        status='approved',
        start_date__year=current_year
    ):
        personal_used += leave.days_count()
    
    unpaid_used = LeaveRequest.objects.filter(
        employee=employee,
        leave_type='unpaid',
        status='approved',
        start_date__year=current_year
    ).count()
    
    # Statistics
    total_leaves = leaves.count()
    pending_count = leaves.filter(status='pending').count()
    approved_count = leaves.filter(status='approved').count()
    rejected_count = leaves.filter(status='rejected').count()
    
    # Get available years for filter
    years = LeaveRequest.objects.filter(
        employee=employee
    ).dates('start_date', 'year').values_list('start_date__year', flat=True).distinct()
    
    context = {
        'employee': employee,
        'leaves': leaves,
        'annual_balance': max(0, annual_total - annual_used),
        'annual_used': annual_used,
        'sick_balance': max(0, sick_total - sick_used),
        'sick_used': sick_used,
        'personal_balance': max(0, personal_total - personal_used),
        'personal_used': personal_used,
        'unpaid_balance': '∞',
        'unpaid_used': unpaid_used,
        'total_leaves': total_leaves,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'years': years,
        'current_status': status,
        'current_type': leave_type,
        'current_year': year,
    }
    return render(request, 'leave_history.html', context)



# ==================== TEST VIEW ====================

@csrf_protect
def test_csrf(request):
    """Test CSRF token"""
    if request.method == 'POST':
        return HttpResponse("POST Success!")
    
    html = """
    <form method="post">
        {% csrf_token %}
        <input type="text" name="test">
        <button type="submit">Submit</button>
    </form>
    """
    t = Template(html)
    c = Context({})
    return HttpResponse(t.render(c))





    #admin attendance /hr 

# ==================== ATTENDANCE & BREAK VIEWS ====================

@login_required
def clock_in(request):
    """Clock In functionality"""
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(email=request.user.email)
            now = timezone.now()
            today = now.date()
            
            # Check if already checked in
            attendance, created = Attendance.objects.get_or_create(
                employee=employee,
                date=today,
                defaults={'check_in': now}
            )
            
            if attendance.check_out:
                messages.warning(request, 'You have already clocked out today!')
            elif not created and attendance.check_in:
                messages.warning(request, 'You have already clocked in today!')
            else:
                # Existing records (for example, marked absent) also need a check-in.
                attendance.check_in = now
                # Calculate if late or half day
                attendance.calculate_status()
                attendance.save()
                
                if attendance.is_half_day:
                    messages.warning(request, f'⚠️ You are {attendance.late_minutes} minutes late. This will be marked as HALF DAY.')
                elif attendance.is_late:
                    messages.info(request, f'⚠️ You are {attendance.late_minutes} minutes late.')
                else:
                    messages.success(request, '✅ Clocked in successfully!')
            
        except Employee.DoesNotExist:
            messages.error(request, 'Employee record not found!')
    
    return redirect('employee_dashboard')

@login_required
def clock_out(request):
    """Clock Out functionality"""
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(email=request.user.email)
            today = timezone.now().date()
            
            try:
                attendance = Attendance.objects.get(employee=employee, date=today)
                
                if not attendance.check_in:
                    messages.error(request, 'Please clock in before clocking out!')
                elif attendance.check_out:
                    messages.warning(request, 'You have already clocked out today!')
                else:
                    # Close any active breaks
                    active_breaks = Break.objects.filter(
                        attendance=attendance, 
                        end_time__isnull=True
                    )
                    for brk in active_breaks:
                        brk.end_time = timezone.now()
                        brk.save()
                    
                    attendance.check_out = timezone.now()
                    attendance.calculate_working_hours()
                    attendance.save()
                    
                    messages.success(request, f'✅ Clocked out! Total hours: {attendance.total_working_hours} hrs')
            
            except Attendance.DoesNotExist:
                messages.error(request, 'No clock-in record found for today!')
        
        except Employee.DoesNotExist:
            messages.error(request, 'Employee record not found!')
    
    return redirect('employee_dashboard')

@login_required
def start_break(request):
    """Start a break"""
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(email=request.user.email)
            today = timezone.now().date()
            
            try:
                attendance = Attendance.objects.get(employee=employee, date=today)

                if not attendance.check_in:
                    messages.error(request, 'Please clock in first!')
                    return redirect('employee_dashboard')
                if attendance.check_out:
                    messages.warning(request, 'You have already clocked out today!')
                    return redirect('employee_dashboard')
                
                # Check if already on break
                active_break = Break.objects.filter(
                    attendance=attendance, 
                    end_time__isnull=True
                ).first()
                
                if active_break:
                    messages.warning(request, 'You are already on a break!')
                else:
                    break_type = request.POST.get('break_type', 'tea')
                    
                    new_break = Break.objects.create(
                        attendance=attendance,
                        start_time=timezone.now(),
                        break_type=break_type
                    )
                    
                    messages.success(request, f'☕ Break started at {new_break.start_time.strftime("%I:%M %p")}')
            
            except Attendance.DoesNotExist:
                messages.error(request, 'Please clock in first!')
        
        except Employee.DoesNotExist:
            messages.error(request, 'Employee record not found!')
    
    return redirect('employee_dashboard')

@login_required
def end_break(request):
    """End break - check if reason required"""
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(email=request.user.email)
            today = timezone.now().date()
            
            attendance = Attendance.objects.get(employee=employee, date=today)
            active_break = Break.objects.filter(
                attendance=attendance, 
                end_time__isnull=True
            ).first()
            
            if not active_break:
                messages.error(request, 'No active break found!')
                return redirect('employee_dashboard')
            
            # Calculate duration
            duration = (timezone.now() - active_break.start_time).total_seconds() / 60
            
            # Check if reason is required (excessive break)
            requires_reason = False
            if active_break.break_type == 'tea' and duration > 15:
                requires_reason = True
            elif active_break.break_type == 'lunch' and duration > 60:
                requires_reason = True
            elif duration > 30:
                requires_reason = True
            
            if requires_reason:
                # Store break info in session for reason page
                request.session['pending_break_id'] = active_break.id
                return redirect('break_reason')
            else:
                # End break directly
                active_break.end_time = timezone.now()
                active_break.save()
                attendance.calculate_working_hours()
                
                messages.success(request, f'✅ Break ended. Duration: {int(duration)} minutes')
        
        except (Employee.DoesNotExist, Attendance.DoesNotExist):
            messages.error(request, 'Error ending break')
    
    return redirect('employee_dashboard')

@login_required
def break_reason(request):
    """Page for submitting break reason"""
    try:
        employee = Employee.objects.get(email=request.user.email)
        
        # Get pending break from session
        break_id = request.session.get('pending_break_id')
        if not break_id:
            messages.error(request, 'No pending break found')
            return redirect('employee_dashboard')
        
        active_break = get_object_or_404(Break, id=break_id, end_time__isnull=True)
        
        if request.method == 'POST':
            reason = request.POST.get('reason')
            if not reason:
                messages.error(request, 'Please provide a reason')
            else:
                # End break with reason
                active_break.end_time = timezone.now()
                active_break.reason = reason
                active_break.reason_submitted_at = timezone.now()
                active_break.requires_reason = True
                active_break.save()
                
                # Update attendance
                active_break.attendance.calculate_working_hours()
                
                # Clear session
                del request.session['pending_break_id']
                
                duration = active_break.duration_minutes
                messages.success(request, f'✅ Break ended. Duration: {duration} minutes')
                return redirect('employee_dashboard')
        
        # Calculate current duration
        duration = (timezone.now() - active_break.start_time).total_seconds() / 60
        
        context = {
            'break_obj': active_break,
            'duration': int(duration),
            'break_type_display': active_break.get_break_type_display(),
        }
        return render(request, 'break_reason.html', context)
    
    except Employee.DoesNotExist:
        messages.error(request, 'Employee not found')
        return redirect('employee_dashboard')

@staff_member_required
def admin_attendance(request):
    """HR Admin attendance dashboard"""
    # Get filter date from request
    filter_date = request.GET.get('date')
    if filter_date:
        try:
            filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
        except ValueError:
            filter_date = timezone.now().date()
    else:
        filter_date = timezone.now().date()
    
    # Get all attendances for the date
    attendances = Attendance.objects.filter(date=filter_date).select_related('employee')
    
    # Get today's leaves
    today_leaves = LeaveRequest.objects.filter(
        start_date__lte=filter_date,
        end_date__gte=filter_date,
        status='approved'
    ).select_related('employee')
    
    # Get absent employees (active employees with no attendance)
    active_employees = Employee.objects.filter(status='active')
    present_employee_ids = attendances.values_list('employee_id', flat=True)
    absent_employees = active_employees.exclude(id__in=present_employee_ids)
    
    # Get excessive breaks
    excessive_breaks = Break.objects.filter(
        attendance__date=filter_date,
        requires_reason=True
    ).select_related('attendance__employee')
    
    # Statistics
    total_present = attendances.count()
    total_late = attendances.filter(is_late=True).count()
    half_days = attendances.filter(is_half_day=True).count()
    on_break = Break.objects.filter(
        attendance__date=filter_date,
        end_time__isnull=True
    ).count()
    
    context = {
        'filter_date': filter_date,
        'attendances': attendances,
        'today_leaves': today_leaves,
        'absent_employees': absent_employees,
        'excessive_breaks': excessive_breaks,
        'total_present': total_present,
        'total_late': total_late,
        'half_days': half_days,
        'on_break': on_break,
        'excessive_breaks_count': excessive_breaks.count(),
        'pending_requests': LeaveRequest.objects.filter(status='pending').count(),
    }
    
    return render(request, 'admin_attendance.html', context)

@staff_member_required
def get_attendance_detail(request, attendance_id):
    """Get attendance details as JSON"""
    try:
        attendance = Attendance.objects.get(id=attendance_id)
        breaks = attendance.breaks.all()
        
        breaks_data = []
        for brk in breaks:
            breaks_data.append({
                'id': brk.id,
                'break_type': brk.break_type,
                'break_type_display': brk.get_break_type_display(),
                'start_time': brk.start_time.strftime('%I:%M %p'),
                'end_time': brk.end_time.strftime('%I:%M %p') if brk.end_time else None,
                'duration_minutes': brk.duration_minutes,
                'requires_reason': brk.requires_reason,
                'reason': brk.reason,
            })
        
        data = {
            'success': True,
            'attendance': {
                'id': attendance.id,
                'employee': {
                    'name': attendance.employee.name,
                    'department': attendance.employee.department,
                    'position': attendance.employee.position,
                },
                'check_in': attendance.check_in.strftime('%I:%M %p') if attendance.check_in else None,
                'check_out': attendance.check_out.strftime('%I:%M %p') if attendance.check_out else None,
                'status': attendance.status,
                'status_display': attendance.get_status_display(),
                'late_minutes': attendance.late_minutes,
                'is_half_day': attendance.is_half_day,
                'total_working_hours': attendance.total_working_hours,
            },
            'breaks': breaks_data,
        }
        return JsonResponse(data)
    except Attendance.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Attendance not found'})

@staff_member_required
def get_break_detail(request, break_id):
    """Get break details as JSON"""
    try:
        brk = Break.objects.get(id=break_id)
        data = {
            'success': True,
            'break': {
                'id': brk.id,
                'employee': brk.attendance.employee.name,
                'break_type': brk.get_break_type_display(),
                'start_time': brk.start_time.strftime('%I:%M %p, %d %B %Y'),
                'end_time': brk.end_time.strftime('%I:%M %p, %d %B %Y') if brk.end_time else None,
                'duration_minutes': brk.duration_minutes,
                'requires_reason': brk.requires_reason,
                'reason': brk.reason,
                'reason_submitted_at': brk.reason_submitted_at.strftime('%I:%M %p, %d %B %Y') if brk.reason_submitted_at else None,
            }
        }
        return JsonResponse(data)
    except Break.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Break not found'})

@staff_member_required
def mark_absent(request, employee_id):
    """Mark employee as absent for today"""
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(id=employee_id)
            today = timezone.now().date()
            
            attendance, created = Attendance.objects.get_or_create(
                employee=employee,
                date=today,
                defaults={
                    'status': 'absent',
                    'check_in': None,
                    'check_out': None,
                }
            )
            
            if not created:
                attendance.status = 'absent'
                attendance.save()
            
            return JsonResponse({'success': True, 'message': 'Marked as absent'})
        except Employee.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Employee not found'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@staff_member_required
def export_attendance(request):
    """Export attendance report as CSV"""
    import csv
    from django.http import HttpResponse
    
    filter_date = request.GET.get('date')
    if filter_date:
        filter_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
    else:
        filter_date = timezone.now().date()
    
    attendances = Attendance.objects.filter(date=filter_date).select_related('employee')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance_{filter_date}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Employee', 'Department', 'Check In', 'Check Out', 'Status', 'Late Minutes', 'Half Day', 'Total Hours'])
    
    for att in attendances:
        writer.writerow([
            att.employee.name,
            att.employee.department,
            att.check_in.strftime('%I:%M %p') if att.check_in else '-',
            att.check_out.strftime('%I:%M %p') if att.check_out else '-',
            att.get_status_display(),
            att.late_minutes if att.late_minutes else '-',
            'Yes' if att.is_half_day else 'No',
            f"{att.total_working_hours} hrs" if att.total_working_hours else '-',
        ])
    
    return response
@staff_member_required
def update_attendance_api(request, attendance_id):
    """API endpoint to update attendance record from edit modal"""
    if request.method == 'POST':
        try:
            attendance = get_object_or_404(Attendance, id=attendance_id)
            
            # Get data from request
            check_in_str = request.POST.get('check_in')
            check_out_str = request.POST.get('check_out')
            status = request.POST.get('status')
            is_half_day = request.POST.get('is_half_day') == 'on'
            
            # Update check in time
            if check_in_str:
                check_in_time = datetime.datetime.strptime(check_in_str, '%H:%M').time()
                attendance.check_in = check_in_time
                
                # Calculate late minutes (standard check-in is 9:00 AM)
                standard_check_in = datetime.time(9, 0)
                check_in_dt = datetime.datetime.combine(datetime.date.today(), check_in_time)
                standard_dt = datetime.datetime.combine(datetime.date.today(), standard_check_in)
                
                if check_in_dt > standard_dt:
                    late_seconds = (check_in_dt - standard_dt).total_seconds()
                    attendance.late_minutes = int(late_seconds // 60)
                    attendance.is_late = True
                else:
                    attendance.late_minutes = 0
                    attendance.is_late = False
            
            # Update check out time
            if check_out_str:
                check_out_time = datetime.datetime.strptime(check_out_str, '%H:%M').time()
                attendance.check_out = check_out_time
            
            # Update status
            if status:
                attendance.status = status
            
            # Update half day flag
            attendance.is_half_day = is_half_day
            
            # Recalculate total working hours
            if attendance.check_in and attendance.check_out:
                check_in = datetime.datetime.combine(datetime.date.today(), attendance.check_in)
                check_out = datetime.datetime.combine(datetime.date.today(), attendance.check_out)
                working_seconds = (check_out - check_in).total_seconds()
                attendance.total_working_hours = round(working_seconds / 3600, 1)
            
            attendance.save()
            
            return JsonResponse({'success': True, 'message': 'Attendance updated successfully'})
            
        except Attendance.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Attendance record not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


#task management views
# ==================== TASK MANAGEMENT VIEWS ====================

@login_required
def task_dashboard(request):
    """Main task dashboard - different views for admin/employee"""
    try:
        # Check if user is admin
        admin = Admin.objects.get(user=request.user)
        return redirect('admin_tasks')
    except Admin.DoesNotExist:
        return redirect('employee_tasks')


# ==================== ADMIN TASK VIEWS ====================

@staff_member_required
def admin_tasks(request):
    """Admin task management dashboard"""
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Access denied.')
        return redirect('employee_dashboard')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')
    employee_id = request.GET.get('employee', '')
    category_id = request.GET.get('category', '')
    
    # Base queryset
    tasks = Task.objects.all().select_related('assigned_to', 'category')
    
    # Apply filters
    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)
    if employee_id:
        tasks = tasks.filter(assigned_to_id=employee_id)
    if category_id:
        tasks = tasks.filter(category_id=category_id)
    
    # Statistics
    total_tasks = Task.objects.count()
    pending_tasks = Task.objects.filter(status='pending').count()
    in_progress_tasks = Task.objects.filter(status='in_progress').count()
    completed_tasks = Task.objects.filter(status='completed').count()
    overdue_tasks = Task.objects.filter(due_date__lt=date.today()).exclude(status='completed').count()
    
    context = {
        'admin': admin,
        'tasks': tasks,
        'employees': Employee.objects.filter(status='active'),
        'categories': TaskCategory.objects.all(),
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'current_status': status,
        'current_priority': priority,
        'current_employee': employee_id,
        'current_category': category_id,
    }
    return render(request, 'admin_tasks.html', context)


@staff_member_required
def create_task(request):
    """Create new task and assign to employee"""
    if request.method == 'POST':
        try:
            admin = Admin.objects.get(user=request.user)
            
            title = request.POST.get('title')
            description = request.POST.get('description')
            assigned_to_id = request.POST.get('assigned_to')
            category_id = request.POST.get('category')
            priority = request.POST.get('priority', 'medium')
            due_date = request.POST.get('due_date')
            estimated_hours = request.POST.get('estimated_hours')
            
            # Validate
            if not all([title, description, assigned_to_id, due_date]):
                return JsonResponse({'success': False, 'error': 'All fields are required'})
            
            # Get employee
            try:
                employee = Employee.objects.get(id=assigned_to_id)
            except Employee.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Employee not found'})
            
            # Create task
            task = Task.objects.create(
                title=title,
                description=description,
                created_by=admin,
                assigned_to=employee,
                category_id=category_id if category_id else None,
                priority=priority,
                due_date=due_date,
                estimated_hours=estimated_hours if estimated_hours else None,
                status='pending'
            )
            
            # Create history entry
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                action='Created',
                comment=f'Task created by {request.user.username}'
            )
            
            return JsonResponse({
                'success': True, 
                'message': 'Task created successfully',
                'task_id': task.id
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request - return form data
    employees = Employee.objects.filter(status='active')
    categories = TaskCategory.objects.all()
    
    context = {
        'employees': employees,
        'categories': categories,
    }
    return render(request, 'create_task_modal.html', context)


# ==================== FIXED TASK DETAIL VIEW ====================
# This view allows BOTH admin and assigned employee to view task details

def task_detail(request, task_id):
    """View task details - accessible to both admin and assigned employee"""
    task = get_object_or_404(Task.objects.select_related(
        'assigned_to', 'created_by', 'category'
    ), id=task_id)
    
    # Check if user is admin
    try:
        admin = Admin.objects.get(user=request.user)
        is_admin = True
    except Admin.DoesNotExist:
        is_admin = False
    
    # Check if user is the assigned employee
    try:
        employee = Employee.objects.get(email=request.user.email)
        is_assigned_employee = (employee.id == task.assigned_to.id)
    except Employee.DoesNotExist:
        is_assigned_employee = False
    
    # If not admin and not assigned employee, deny access
    if not is_admin and not is_assigned_employee:
        messages.error(request, 'You do not have permission to view this task.')
        return redirect('employee_tasks')
    
    comments = TaskComment.objects.filter(task=task).select_related('user')
    history = TaskHistory.objects.filter(task=task).select_related('user')
    attachments = TaskAttachment.objects.filter(task=task)
    
    # Use different templates for admin and employee
    if is_admin:
        template = 'task_detail.html'  # Admin ke liye alag template
    else:
        template = 'employee_task_detail.html'  # Employee ke liye alag template
    
    context = {
        'task': task,
        'comments': comments,
        'history': history,
        'attachments': attachments,
        'is_admin': is_admin,
        'is_employee': is_assigned_employee,
    }
    return render(request, template, context)


@staff_member_required
def update_task(request, task_id):
    """Update task details"""
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        
        # Track changes
        changes = []
        fields = ['title', 'description', 'assigned_to', 'category', 
                  'priority', 'status', 'due_date', 'estimated_hours']
        
        for field in fields:
            old_value = getattr(task, field)
            new_value = request.POST.get(field)
            
            if field == 'assigned_to':
                new_value = request.POST.get('assigned_to')
                try:
                    new_employee = Employee.objects.get(id=new_value) if new_value else None
                    if new_employee and task.assigned_to != new_employee:
                        changes.append({
                            'field': 'assigned_to',
                            'old': task.assigned_to.name if task.assigned_to else None,
                            'new': new_employee.name
                        })
                        task.assigned_to = new_employee
                except:
                    pass
            elif field == 'category':
                new_value = request.POST.get('category')
                try:
                    new_category = TaskCategory.objects.get(id=new_value) if new_value else None
                    if task.category != new_category:
                        changes.append({
                            'field': 'category',
                            'old': task.category.name if task.category else None,
                            'new': new_category.name if new_category else None
                        })
                        task.category = new_category
                except:
                    task.category = None
            elif field == 'status' and str(old_value) != str(new_value):
                changes.append({
                    'field': 'status',
                    'old': task.get_status_display(),
                    'new': dict(Task.STATUS_CHOICES).get(new_value, new_value)
                })
                setattr(task, field, new_value)
                
                # If completed, set completed date
                if new_value == 'completed' and not task.completed_date:
                    task.completed_date = timezone.now()
            elif str(old_value) != str(new_value):
                changes.append({
                    'field': field,
                    'old': old_value,
                    'new': new_value
                })
                setattr(task, field, new_value)
        
        task.save()
        
        # Record history
        for change in changes:
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                action='Updated',
                field_name=change['field'],
                old_value=str(change['old']),
                new_value=str(change['new'])
            )
        
        messages.success(request, 'Task updated successfully')
        return redirect('task_detail', task_id=task.id)
    
    employees = Employee.objects.filter(status='active')
    categories = TaskCategory.objects.all()
    context = {
        'task': task,
        'employees': employees,
        'categories': categories,
    }
    return render(request, 'edit_task_modal.html', context)


@staff_member_required
def delete_task(request, task_id):
    """Delete task"""
    if request.method == 'POST':
        task = get_object_or_404(Task, id=task_id)
        task.delete()
        return JsonResponse({'success': True, 'message': 'Task deleted successfully'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@staff_member_required
def task_reports(request):
    """Generate task reports"""
    # Date range filter
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    tasks = Task.objects.all()
    
    if start_date:
        tasks = tasks.filter(created_date__date__gte=start_date)
    if end_date:
        tasks = tasks.filter(created_date__date__lte=end_date)
    
    # Statistics by employee
    employee_stats = []
    for employee in Employee.objects.filter(status='active'):
        emp_tasks = tasks.filter(assigned_to=employee)
        employee_stats.append({
            'employee': employee,
            'total': emp_tasks.count(),
            'completed': emp_tasks.filter(status='completed').count(),
            'pending': emp_tasks.filter(status='pending').count(),
            'in_progress': emp_tasks.filter(status='in_progress').count(),
            'overdue': emp_tasks.filter(due_date__lt=date.today()).exclude(status='completed').count()
        })
    
    # Statistics by status
    status_stats = {
        'pending': tasks.filter(status='pending').count(),
        'in_progress': tasks.filter(status='in_progress').count(),
        'completed': tasks.filter(status='completed').count(),
        'on_hold': tasks.filter(status='on_hold').count(),
        'cancelled': tasks.filter(status='cancelled').count(),
    }
    
    # Statistics by priority
    priority_stats = {
        'low': tasks.filter(priority='low').count(),
        'medium': tasks.filter(priority='medium').count(),
        'high': tasks.filter(priority='high').count(),
        'urgent': tasks.filter(priority='urgent').count(),
    }
    
    context = {
        'employee_stats': employee_stats,
        'status_stats': status_stats,
        'priority_stats': priority_stats,
        'total_tasks': tasks.count(),
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'task_reports.html', context)


# ==================== EMPLOYEE TASK VIEWS ====================

@login_required
def employee_tasks(request):
    """Employee view for their tasks"""
    try:
        employee = Employee.objects.get(email=request.user.email)
    except Employee.DoesNotExist:
        messages.error(request, 'Employee record not found')
        return redirect('employee_dashboard')
    
    # Filter tasks
    status = request.GET.get('status', '')
    
    tasks = Task.objects.filter(assigned_to=employee).select_related('category')
    
    if status:
        tasks = tasks.filter(status=status)
    
    # Statistics
    total_tasks = tasks.count()
    pending_tasks = tasks.filter(status='pending').count()
    in_progress_tasks = tasks.filter(status='in_progress').count()
    completed_tasks = tasks.filter(status='completed').count()
    overdue_tasks = tasks.filter(due_date__lt=date.today()).exclude(status='completed').count()
    
    context = {
        'employee': employee,
        'tasks': tasks,
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'overdue_tasks': overdue_tasks,
        'current_status': status,
    }
    return render(request, 'employee_tasks.html', context)


@login_required
def update_task_status(request, task_id):
    """Employee updates task status"""
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(email=request.user.email)
            task = get_object_or_404(Task, id=task_id, assigned_to=employee)
            
            new_status = request.POST.get('status')
            comment = request.POST.get('comment', '')
            progress = request.POST.get('progress')
            
            if not new_status:
                return JsonResponse({'success': False, 'error': 'Status required'})
            
            old_status = task.status
            task.status = new_status
            task.progress_percentage = int(progress) if progress else task.progress_percentage
            
            if new_status == 'completed':
                task.completed_date = timezone.now()
                task.progress_percentage = 100
            
            task.save()
            
            # Add comment if provided
            if comment:
                TaskComment.objects.create(
                    task=task,
                    user=request.user,
                    comment=comment
                )
            
            # Record history
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                action='Status Changed',
                field_name='status',
                old_value=dict(Task.STATUS_CHOICES).get(old_status, old_status),
                new_value=dict(Task.STATUS_CHOICES).get(new_status, new_status),
                comment=comment
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Task status updated',
                'new_status': new_status,
                'progress': task.progress_percentage
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def add_task_comment(request, task_id):
    """Add comment to task"""
    if request.method == 'POST':
        try:
            employee = Employee.objects.get(email=request.user.email)
            task = get_object_or_404(Task, id=task_id, assigned_to=employee)
            
            comment_text = request.POST.get('comment')
            
            if not comment_text:
                return JsonResponse({'success': False, 'error': 'Comment required'})
            
            comment = TaskComment.objects.create(
                task=task,
                user=request.user,
                comment=comment_text
            )
            
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'text': comment.comment,
                    'user': request.user.username,
                    'time': comment.created_at.strftime('%b %d, %Y %I:%M %p')
                }
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# ==================== TASK CATEGORY MANAGEMENT ====================

@staff_member_required
def manage_categories(request):
    """Manage task categories"""
    categories = TaskCategory.objects.all()
    return render(request, 'task_categories.html', {'categories': categories})


@staff_member_required
def add_category(request):
    """Add new task category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        color = request.POST.get('color', '#2563eb')
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Name required'})
        
        category = TaskCategory.objects.create(
            name=name,
            description=description,
            color=color
        )
        
        return JsonResponse({
            'success': True,
            'category': {
                'id': category.id,
                'name': category.name,
                'color': category.color
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@staff_member_required
def delete_category(request, category_id):
    """Delete task category"""
    if request.method == 'POST':
        category = get_object_or_404(TaskCategory, id=category_id)
        category.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})



#admin task dashboard with enhanced features


@staff_member_required
def admin_task_dashboard(request):
    """Comprehensive admin task dashboard with analytics"""
    from datetime import timedelta
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        messages.error(request, 'Access denied.')
        return redirect('employee_dashboard')
    
    # Get filter parameters
    employee_id = request.GET.get('employee')
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    sort = request.GET.get('sort', 'due_date')
    
    # Base queryset
    tasks = Task.objects.all().select_related('assigned_to', 'category')
    
    # Apply filters
    if employee_id:
        tasks = tasks.filter(assigned_to_id=employee_id)
    if status:
        tasks = tasks.filter(status=status)
    if priority:
        tasks = tasks.filter(priority=priority)
    
    # Apply sorting
    tasks = tasks.order_by(sort)
    
    # Statistics
    total_tasks = Task.objects.count()
    pending_tasks = Task.objects.filter(status='pending').count()
    in_progress_tasks = Task.objects.filter(status='in_progress').count()
    completed_tasks = Task.objects.filter(status='completed').count()
    active_tasks = total_tasks - completed_tasks
    
    # Overdue tasks
    overdue_tasks = Task.objects.filter(
        due_date__lt=date.today()
    ).exclude(
        status='completed'
    ).select_related('assigned_to')
    
    # Add days overdue as a new attribute (not using property name)
    overdue_tasks_list = []
    for task in overdue_tasks:
        task.overdue_days = (date.today() - task.due_date).days  # ✅ Different name
        overdue_tasks_list.append(task)
    
    # Upcoming tasks (next 7 days)
    upcoming_tasks = Task.objects.filter(
        due_date__gte=date.today(),
        due_date__lte=date.today() + timedelta(days=7)
    ).exclude(
        status='completed'
    ).select_related('assigned_to').order_by('due_date')
    
    # Add days remaining as a new attribute (not using property name)
    upcoming_tasks_list = []
    for task in upcoming_tasks:
        task.remaining_days = (task.due_date - date.today()).days  # ✅ Different name
        upcoming_tasks_list.append(task)
    
    # Task distribution by employee
    employees = Employee.objects.filter(status='active')
    employee_names = []
    employee_task_counts = []
    
    for emp in employees:
        employee_names.append(emp.name.split()[0])
        employee_task_counts.append(Task.objects.filter(assigned_to=emp).count())
    
    # Convert to JSON safe format
    import json
    employee_names_json = json.dumps(employee_names)
    employee_task_counts_json = json.dumps(employee_task_counts)
    
    context = {
        'admin': admin,
        'tasks': tasks,
        'employees': employees,
        'total_tasks': total_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'active_tasks': active_tasks,
        'overdue_tasks': overdue_tasks_list,
        'overdue_tasks_count': overdue_tasks.count(),
        'upcoming_tasks': upcoming_tasks_list,
        'employee_names': employee_names_json,
        'employee_task_counts': employee_task_counts_json,
    }
    return render(request, 'admin_task_dashboard.html', context)




#admin edit task m

@staff_member_required
def update_task(request, task_id):
    """Update task details"""
    task = get_object_or_404(Task, id=task_id)  # ✅ Sabse pehle task define karo
    
    if request.method == 'POST':
        # Track changes
        changes = []
        fields = ['title', 'description', 'assigned_to', 'category', 
                  'priority', 'status', 'due_date', 'estimated_hours']
        
        for field in fields:
            old_value = getattr(task, field)
            new_value = request.POST.get(field)
            
            if field == 'assigned_to':
                new_value = request.POST.get('assigned_to')
                try:
                    new_employee = Employee.objects.get(id=new_value) if new_value else None
                    if new_employee and task.assigned_to != new_employee:
                        changes.append({
                            'field': 'assigned_to',
                            'old': task.assigned_to.name if task.assigned_to else None,
                            'new': new_employee.name
                        })
                        task.assigned_to = new_employee
                except:
                    pass
            elif field == 'category':
                new_value = request.POST.get('category')
                try:
                    new_category = TaskCategory.objects.get(id=new_value) if new_value else None
                    if task.category != new_category:
                        changes.append({
                            'field': 'category',
                            'old': task.category.name if task.category else None,
                            'new': new_category.name if new_category else None
                        })
                        task.category = new_category
                except:
                    task.category = None
            elif field == 'status' and str(old_value) != str(new_value):
                changes.append({
                    'field': 'status',
                    'old': task.get_status_display(),
                    'new': dict(Task.STATUS_CHOICES).get(new_value, new_value)
                })
                setattr(task, field, new_value)
                
                # If completed, set completed date
                if new_value == 'completed' and not task.completed_date:
                    task.completed_date = timezone.now()
            elif str(old_value) != str(new_value):
                changes.append({
                    'field': field,
                    'old': old_value,
                    'new': new_value
                })
                setattr(task, field, new_value)
        
        task.save()
        
        # Record history
        for change in changes:
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                action='Updated',
                field_name=change['field'],
                old_value=str(change['old']),
                new_value=str(change['new'])
            )
        
        messages.success(request, 'Task updated successfully')
        return redirect('task_detail', task_id=task.id)
    
    # ✅ GET request ke liye - edit form show karo
    employees = Employee.objects.filter(status='active')
    categories = TaskCategory.objects.all()
    context = {
        'task': task,  # ✅ task yahan define hai
        'employees': employees,
        'categories': categories,
    }
    return render(request, 'edit_task_modal.html', context)


# ==================== HELPER FUNCTION ====================

def is_super_admin(user):
    """Check if user is super admin via Admin model"""
    try:
        admin = Admin.objects.get(user=user)
        return True
    except Admin.DoesNotExist:
        return False


def is_admin(user):
    """Check if user is Admin (any role)"""
    try:
        admin = Admin.objects.get(user=user)
        return True
    except Admin.DoesNotExist:
        return False

def is_ceo(user):
    """Check if user is CEO"""
    try:
        admin = Admin.objects.get(user=user)
        return admin.role == 'ceo'
    except Admin.DoesNotExist:
        return False

def is_hr(user):
    """Check if user is HR"""
    try:
        admin = Admin.objects.get(user=user)
        return admin.role == 'hr'
    except Admin.DoesNotExist:
        return False
    


#Project Management views starts from here====



# ==================== HELPER FUNCTIONS ====================

def is_admin_or_leader(user, project):
    """Check if user is admin, project leader, or team leader"""
    return (
        user.is_superuser or 
        user == project.team_leader or 
        user == project.project_manager
    )

def has_project_access(user, project):
    """Check if user has access to project"""
    return (
        user.is_superuser or
        user == project.team_leader or
        user == project.project_manager or
        user in project.members.all()
    )

def log_activity(user, action, content_object, details=""):
    """Helper function to create activity log"""
    ActivityLog.objects.create(
        user=user,
        action=action,
        content_object=content_object,
        details=details
    )

def create_notification(recipient, sender, notification_type, message, content_object, link=""):
    """Helper function to create notification"""
    Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notification_type=notification_type,
        message=message,
        content_object=content_object,
        link=link
    )



# ==================== DASHBOARD VIEWS ====================

@staff_member_required
def admin_project_dashboard(request):
    """Admin main project management dashboard"""
    # Get statistics
    total_projects = Project.objects.count()
    total_teams = Team.objects.count()
    total_tasks = ProjectTask.objects.count()
    pending_handoffs = TaskHandoff.objects.filter(status='pending').count()
    
    # Recent projects (last 6)
    recent_projects = Project.objects.all().order_by('-created_at')[:6]
    
    # Recent activities
    recent_activities = ActivityLog.objects.all().select_related('user')[:10]
    
    # Pending handoffs list
    pending_handoffs_list = TaskHandoff.objects.filter(
        status='pending'
    ).select_related('task', 'from_user', 'to_user')[:5]
    
    context = {
        'total_projects': total_projects,
        'total_teams': total_teams,
        'total_tasks': total_tasks,
        'pending_handoffs': pending_handoffs,
        'recent_projects': recent_projects,
        'recent_activities': recent_activities,
        'pending_handoffs_list': pending_handoffs_list,
    }
    return render(request, 'project/admin_project_dashboard.html', context)


@login_required
def employee_project_dashboard(request):
    """Employee main project management dashboard"""
    user = request.user
    
    # Get user's projects
    my_projects = Project.objects.filter(
        Q(members=user) | Q(team_leader=user) | Q(project_manager=user)
    ).distinct()
    
    # Get user's tasks
    my_tasks = ProjectTask.objects.filter(assigned_to=user)
    
    # Statistics
    my_projects_count = my_projects.count()
    my_tasks_count = my_tasks.count()
    in_progress_count = my_tasks.filter(status='in_progress').count()
    completed_tasks_count = my_tasks.filter(status='completed').count()
    
    # Recent tasks (last 5)
    my_recent_tasks = my_tasks.order_by('-updated_at')[:5]
    
    # Pending handoffs for this user
    pending_handoffs = TaskHandoff.objects.filter(
        to_user=user,
        status='pending'
    ).select_related('task', 'from_user')[:5]
    
    # Recent comments in user's projects
    project_ids = my_projects.values_list('id', flat=True)
    content_type = ContentType.objects.get_for_model(Project)
    recent_comments = Comment.objects.filter(
        content_type=content_type,
        object_id__in=project_ids
    ).select_related('user')[:5]
    
    context = {
        'my_projects': my_projects[:6],
        'my_projects_count': my_projects_count,
        'my_tasks_count': my_tasks_count,
        'in_progress_count': in_progress_count,
        'completed_tasks_count': completed_tasks_count,
        'my_recent_tasks': my_recent_tasks,
        'pending_handoffs': pending_handoffs,
        'recent_comments': recent_comments,
    }
    return render(request, 'project/employee_project_dashboard.html', context)


# ==================== ADMIN/TEAM LEADER VIEWS ====================

@staff_member_required
def admin_project_list(request):
    """Admin view - List all projects"""
    projects = Project.objects.all().select_related('team', 'team_leader', 'project_manager')
    
    # Filters
    status = request.GET.get('status')
    priority = request.GET.get('priority')
    team_id = request.GET.get('team')
    
    if status:
        projects = projects.filter(status=status)
    if priority:
        projects = projects.filter(priority=priority)
    if team_id:
        projects = projects.filter(team_id=team_id)
    
    # Search
    search = request.GET.get('search')
    if search:
        projects = projects.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) |
            Q(project_code__icontains=search)
        )
    
    context = {
        'projects': projects,
        'total_projects': projects.count(),
        'active_projects': projects.filter(status='active').count(),
        'completed_projects': projects.filter(status='completed').count(),
        'planning_projects': projects.filter(status='planning').count(),
        'on_hold_projects': projects.filter(status='on_hold').count(),
        'cancelled_projects': projects.filter(status='cancelled').count(),
    }
    return render(request, 'project/admin_project_list.html', context)


@staff_member_required
def admin_project_detail(request, project_code):
    """Admin view - Project details"""
    project = get_object_or_404(Project, project_code=project_code)
    
    # Get tasks
    tasks = ProjectTask.objects.filter(project=project).select_related(
        'assigned_to', 'assigned_by', 'parent_task'
    )
    
    # Task counts by status
    task_stats = {
        'todo': tasks.filter(status='todo').count(),
        'in_progress': tasks.filter(status='in_progress').count(),
        'review': tasks.filter(status='review').count(),
        'completed': tasks.filter(status='completed').count(),
        'blocked': tasks.filter(status='blocked').count(),
        'handoff': tasks.filter(status='handoff').count(),
        'total': tasks.count(),
    }
    
    # Get tasks by priority
    priority_stats = {
        'low': tasks.filter(priority='low').count(),
        'medium': tasks.filter(priority='medium').count(),
        'high': tasks.filter(priority='high').count(),
        'urgent': tasks.filter(priority='urgent').count(),
    }
    
    # Get comments
    content_type = ContentType.objects.get_for_model(project)
    comments = Comment.objects.filter(
        content_type=content_type,
        object_id=project.id,
        parent__isnull=True
    ).select_related('user').prefetch_related('replies__user', 'mentions')
    
    # Get activity logs
    activity_logs = ActivityLog.objects.filter(
        content_type=ContentType.objects.get_for_model(project),
        object_id=project.id
    ).select_related('user')[:20]
    
    # Team members with task counts
    team_members = project.members.all().annotate(
        task_count=Count('project_tasks', filter=Q(project_tasks__project=project)),
        completed_tasks=Count('project_tasks', filter=Q(project_tasks__project=project, project_tasks__status='completed'))
    )
    
    context = {
        'project': project,
        'tasks': tasks,
        'todo_tasks': tasks.filter(status='todo'),
        'in_progress_tasks': tasks.filter(status='in_progress'),
        'review_tasks': tasks.filter(status='review'),
        'completed_tasks': tasks.filter(status='completed'),
        'blocked_tasks': tasks.filter(status='blocked'),
        'handoff_tasks': tasks.filter(status='handoff'),
        'task_stats': task_stats,
        'priority_stats': priority_stats,
        'comments': comments,
        'activity_logs': activity_logs,
        'team_members': team_members,
        'content_type_id': content_type.id,
        'progress': project.progress,
        'days_remaining': project.days_remaining,
    }
    return render(request, 'project/admin_project_detail.html', context)


@staff_member_required
def admin_create_project(request):
    """Admin view - Create new project"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        team_id = request.POST.get('team')
        priority = request.POST.get('priority', 'medium')
        budget = request.POST.get('budget')
        project_leader_id = request.POST.get('project_leader')
        project_manager_id = request.POST.get('project_manager')
        
        # Validate dates
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid date format')
            return redirect('admin_create_project')
        
        if start > end:
            messages.error(request, 'Start date cannot be after end date')
            return redirect('admin_create_project')
        
        # Get team
        team = get_object_or_404(Team, id=team_id)
        
        # Get project leader
        project_leader = get_object_or_404(User, id=project_leader_id)
        
        # Get project manager (optional)
        project_manager = None
        if project_manager_id:
            project_manager = get_object_or_404(User, id=project_manager_id)
        
        # Create project
        project = Project.objects.create(
            title=title,
            description=description,
            start_date=start,
            end_date=end,
            team=team,
            team_leader=project_leader,
            project_manager=project_manager,
            priority=priority,
            created_by=request.user,
            budget=budget if budget else None,
        )
        
        # Add selected team members
        selected_members = request.POST.getlist('selected_members')
        if selected_members:
            members_to_add = User.objects.filter(id__in=selected_members)
            project.members.set(members_to_add)
        else:
            # Add all team members by default
            project.members.set(team.members.all())
        
        # Add project leader to members if not already
        if project_leader not in project.members.all():
            project.members.add(project_leader)
        
        # Add project manager to members if exists and not already
        if project_manager and project_manager not in project.members.all():
            project.members.add(project_manager)
        
        # Create activity log
        log_activity(request.user, 'create', project, f'Project created by {request.user.username}')
        
        # Notify team members
        for member in project.members.all():
            if member != request.user:
                create_notification(
                    recipient=member,
                    sender=request.user,
                    notification_type='project_created',
                    message=f'New project "{title}" has been created',
                    content_object=project,
                    link=f'/admin/projects/{project.project_code}/'
                )
        
        messages.success(request, f'Project "{title}" created successfully')
        return redirect('admin_project_detail', project_code=project.project_code)
    
    # GET request
    teams = Team.objects.all()
    employees = User.objects.filter(is_active=True)
    
    context = {
        'teams': teams,
        'employees': employees,
    }
    return render(request, 'project/admin_project_create.html', context)


@staff_member_required
def admin_update_project(request, project_code):
    """Admin view - Update project"""
    project = get_object_or_404(Project, project_code=project_code)
    
    if request.method == 'POST':
        project.title = request.POST.get('title')
        project.description = request.POST.get('description')
        project.status = request.POST.get('status')
        project.priority = request.POST.get('priority')
        project.budget = request.POST.get('budget') or None
        
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if start_date:
            project.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            project.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        project.save()
        
        # Update members
        selected_members = request.POST.getlist('members')
        if selected_members:
            project.members.set(selected_members)
        
        log_activity(request.user, 'update', project, f'Project updated by {request.user.username}')
        messages.success(request, 'Project updated successfully')
        return redirect('admin_project_detail', project_code=project.project_code)
    
    # GET request
    teams = Team.objects.all()
    employees = User.objects.filter(is_active=True)
    
    context = {
        'project': project,
        'teams': teams,
        'employees': employees,
    }
    return render(request, 'project/admin_project_update.html', context)


@staff_member_required
def admin_create_task(request, project_code):
    """Admin/Leader view - Create task"""
    project = get_object_or_404(Project, project_code=project_code)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        assigned_to_id = request.POST.get('assigned_to')
        due_date = request.POST.get('due_date')
        priority = request.POST.get('priority', 'medium')
        task_type = request.POST.get('task_type', 'task')
        story_points = request.POST.get('story_points')
        estimated_hours = request.POST.get('estimated_hours')
        tags = request.POST.get('tags', '')
        parent_task_id = request.POST.get('parent_task')
        
        task = ProjectTask.objects.create(
            title=title,
            description=description,
            project=project,
            assigned_to_id=assigned_to_id,
            assigned_by=request.user,
            due_date=due_date,
            priority=priority,
            task_type=task_type,
            story_points=story_points if story_points else None,
            estimated_hours=estimated_hours if estimated_hours else None,
            tags=tags,
            status='todo'
        )
        
        # Set parent task if provided
        if parent_task_id:
            parent_task = get_object_or_404(ProjectTask, id=parent_task_id)
            task.parent_task = parent_task
            task.save()
        
        # Create notification for assigned user - FIX HERE
        if assigned_to_id and int(assigned_to_id) != request.user.id:
            # CHANGE 'recipient_id' TO 'recipient'
            recipient_user = User.objects.get(id=assigned_to_id)
            create_notification(
                recipient=recipient_user,  # ← YAHAN CHANGE
                sender=request.user,
                notification_type='task_assigned',
                message=f'New task "{title}" assigned to you in project {project.title}',
                content_object=task,
                link=f'/admin/tasks/{task.task_code}/'
            )
        
        # Create activity log
        log_activity(request.user, 'create', task, f'Task created by {request.user.username}')
        
        messages.success(request, f'Task "{title}" created')
        return redirect('admin_project_detail', project_code=project_code)
    
    # GET request
    members = project.members.all()
    employees = User.objects.filter(is_active=True)
    parent_tasks = ProjectTask.objects.filter(project=project, parent_task__isnull=True)
    
    context = {
        'project': project,
        'members': members,
        'employees': employees,
        'parent_tasks': parent_tasks,
    }
    return render(request, 'project/admin_task_create.html', context)

@staff_member_required
def admin_task_detail(request, task_code):
    """Admin view - Task details"""
    task = get_object_or_404(ProjectTask, task_code=task_code)
    project = task.project
    
    # Get comments
    content_type = ContentType.objects.get_for_model(task)
    comments = Comment.objects.filter(
        content_type=content_type,
        object_id=task.id,
        parent__isnull=True
    ).select_related('user').prefetch_related('replies__user', 'mentions')
    
    # Get handoff history
    handoffs = TaskHandoff.objects.filter(task=task).select_related('from_user', 'to_user')
    
    # Get activity logs
    activity_logs = ActivityLog.objects.filter(
        content_type=content_type,
        object_id=task.id
    ).select_related('user')[:20]
    
    # Get available members for handoff
    available_members = project.members.exclude(id=task.assigned_to.id if task.assigned_to else None)
    
    # # Get task history
    # task_history = TaskHistory.objects.filter(task=task).select_related('user')[:10]
    
    context = {
        'task': task,
        'project': project,
        'comments': comments,
        'handoffs': handoffs,
        'activity_logs': activity_logs,
        # 'task_history': task_history,
        'content_type_id': content_type.id,
        'available_members': available_members,
        'subtasks': task.subtasks.all(),
        'blocked_by': task.blocked_by_tasks,
        'depends_on': task.depends_on.all(),
    }
    return render(request, 'project/admin_task_detail.html', context)


@staff_member_required
def admin_update_task(request, task_code):
    """Admin view - Update task"""
    task = get_object_or_404(ProjectTask, task_code=task_code)
    
    if request.method == 'POST':
        old_status = task.status
        old_assigned = task.assigned_to
        
        task.title = request.POST.get('title')
        task.description = request.POST.get('description')
        task.status = request.POST.get('status')
        task.priority = request.POST.get('priority')
        task.task_type = request.POST.get('task_type')
        task.progress = request.POST.get('progress', 0)
        task.story_points = request.POST.get('story_points') or None
        task.estimated_hours = request.POST.get('estimated_hours') or None
        task.actual_hours = request.POST.get('actual_hours') or None
        task.tags = request.POST.get('tags', '')
        
        due_date = request.POST.get('due_date')
        if due_date:
            task.due_date = due_date
        
        assigned_to_id = request.POST.get('assigned_to')
        if assigned_to_id:
            task.assigned_to_id = assigned_to_id
        
        task.save()
        
        # Log changes
        changes = []
        if old_status != task.status:
            changes.append(f"status: {old_status} → {task.status}")
        if old_assigned != task.assigned_to:
            changes.append(f"assigned to: {task.assigned_to}")
        
        if changes:
            log_activity(request.user, 'update', task, f"Task updated: {', '.join(changes)}")
        
        messages.success(request, 'Task updated successfully')
        return redirect('admin_task_detail', task_code=task.task_code)
    
    # GET request
    project = task.project
    members = project.members.all()
    
    context = {
        'task': task,
        'project': project,
        'members': members,
    }
    return render(request, 'project/admin_task_update.html', context)


# ==================== EMPLOYEE VIEWS ====================

@login_required
def employee_projects(request):
    """Employee view - Show assigned projects"""
    user = request.user
    
    # Projects where user is member or leader
    assigned_projects = Project.objects.filter(members=user)
    led_projects = Project.objects.filter(team_leader=user)
    managed_projects = Project.objects.filter(project_manager=user)
    
    # Combine and remove duplicates
    projects = (assigned_projects | led_projects | managed_projects).distinct()
    
    # Get tasks assigned to user
    my_tasks = ProjectTask.objects.filter(assigned_to=user).select_related('project')
    
    # Overdue tasks
    today = timezone.now().date()
    overdue_tasks = my_tasks.filter(
        due_date__lt=today
    ).exclude(status='completed')
    
    # Tasks due today
    due_today = my_tasks.filter(
        due_date=today
    ).exclude(status='completed')
    
    # Tasks due this week
    week_end = today + timedelta(days=7)
    due_this_week = my_tasks.filter(
        due_date__range=[today, week_end]
    ).exclude(status='completed')
    
    context = {
        'projects': projects,
        'my_tasks': my_tasks,
        'overdue_tasks': overdue_tasks,
        'due_today': due_today,
        'due_this_week': due_this_week,
        'total_projects': projects.count(),
        'total_tasks': my_tasks.count(),
        'pending_tasks': my_tasks.exclude(status='completed').count(),
        'completed_tasks': my_tasks.filter(status='completed').count(),
    }
    return render(request, 'project/employee_projects.html', context)


@login_required
def employee_project_detail(request, project_code):
    """Employee view - Project details"""
    project = get_object_or_404(Project, project_code=project_code)
    
    # Check access
    if not has_project_access(request.user, project):
        messages.error(request, 'Access denied')
        return redirect('employee_projects')
    
    # Get tasks based on role
    if request.user == project.team_leader or request.user == project.project_manager or request.user.is_superuser:
        # Leaders see all tasks
        tasks = ProjectTask.objects.filter(project=project).select_related('assigned_to')
        my_tasks = tasks.filter(assigned_to=request.user)
    else:
        # Regular members see only their tasks
        my_tasks = ProjectTask.objects.filter(project=project, assigned_to=request.user)
        tasks = my_tasks
    
    # Task counts by status
    task_stats = {
        'todo': my_tasks.filter(status='todo').count(),
        'in_progress': my_tasks.filter(status='in_progress').count(),
        'review': my_tasks.filter(status='review').count(),
        'completed': my_tasks.filter(status='completed').count(),
        'blocked': my_tasks.filter(status='blocked').count(),
        'total': my_tasks.count(),
    }
    
    # Get comments
    content_type = ContentType.objects.get_for_model(project)
    comments = Comment.objects.filter(
        content_type=content_type,
        object_id=project.id,
        parent__isnull=True
    ).select_related('user').prefetch_related('replies__user', 'mentions')
    
    # Team members
    team_members = project.members.all()
    
    context = {
        'project': project,
        'tasks': tasks,
        'my_tasks': my_tasks,
        'task_stats': task_stats,
        'comments': comments,
        'content_type_id': content_type.id,
        'team_members': team_members,
        'is_leader': request.user == project.team_leader,
        'is_manager': request.user == project.project_manager,
        'progress': project.progress,
        'days_remaining': project.days_remaining,
    }
    return render(request, 'project/employee_project_detail.html', context)


@login_required
def employee_task_detail(request, task_code):
    """Employee view - Task details with update options"""
    task = get_object_or_404(ProjectTask, task_code=task_code)
    project = task.project
    
    # Check access
    if not (request.user == task.assigned_to or has_project_access(request.user, project)):
        messages.error(request, 'You do not have permission to view this task')
        return redirect('employee_projects')
    
    # Get comments
    content_type = ContentType.objects.get_for_model(task)
    comments = Comment.objects.filter(
        content_type=content_type,
        object_id=task.id,
        parent__isnull=True
    ).select_related('user').prefetch_related('replies__user', 'mentions')
    
    # Get available members for handoff
    available_members = project.members.exclude(id=request.user.id)
    
    # Check if handoff is pending
    pending_handoff = TaskHandoff.objects.filter(
        task=task,
        status='pending'
    ).first()
    
    # Get task history
    # task_history = TaskHistory.objects.filter(task=task).select_related('user')[:10]
    
    context = {
        'task': task,
        'project': project,
        'comments': comments,
        # 'task_history': task_history,
        'content_type_id': content_type.id,
        'available_members': available_members,
        'pending_handoff': pending_handoff,
        'subtasks': task.subtasks.all(),
        'blocked_by': task.blocked_by_tasks,
        'depends_on': task.depends_on.all(),
        'is_assigned': request.user == task.assigned_to,
        'can_edit': request.user == task.assigned_to or request.user == project.team_leader,
    }
    return render(request, 'project/employee_task_detail.html', context)


@login_required
def employee_update_task_status(request, task_code):
    """Employee view - Update task status"""
    if request.method == 'POST':
        task = get_object_or_404(ProjectTask, task_code=task_code)
        
        if request.user != task.assigned_to:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        new_status = request.POST.get('status')
        old_status = task.status
        
        if new_status and new_status != old_status:
            task.status = new_status
            
            if new_status == 'in_progress' and not task.started_at:
                task.started_at = timezone.now()
            elif new_status == 'completed':
                task.completed_at = timezone.now()
                task.progress = 100
            
            task.save()
            
            # Create task history
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                field='status',
                old_value=old_status,
                new_value=new_status
            )
            
            # Notify project leaders
            if new_status == 'completed':
                if task.project.team_leader and task.project.team_leader != request.user:
                    create_notification(
                        recipient=task.project.team_leader,
                        sender=request.user,
                        notification_type='task_completed',
                        message=f'Task {task.task_code} completed',
                        content_object=task,
                        link=f'/admin/tasks/{task.task_code}/'
                    )
            
            return JsonResponse({
                'success': True,
                'status': task.status,
                'status_display': task.get_status_display()
            })
        
        return JsonResponse({'success': False, 'error': 'No changes made'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def employee_discussion(request, project_code):
    """Employee view - Project discussion page"""
    project = get_object_or_404(Project, project_code=project_code)
    
    # Check access
    if not has_project_access(request.user, project):
        messages.error(request, 'Access denied')
        return redirect('employee_projects')
    
    # Get all comments
    content_type = ContentType.objects.get_for_model(project)
    comments = Comment.objects.filter(
        content_type=content_type,
        object_id=project.id,
        parent__isnull=True
    ).select_related('user').prefetch_related(
        'replies__user', 'replies__mentions', 'mentions'
    ).order_by('-created_at')
    
    context = {
        'project': project,
        'comments': comments,
        'content_type_id': content_type.id,
        'team_members': project.members.all(),
    }
    return render(request, 'project/employee_discussion.html', context)


# ==================== TASK HANDOFF VIEWS ====================

@login_required
def request_task_handoff(request, task_code):
    """Request to handoff task to another member"""
    if request.method == 'POST':
        task = get_object_or_404(ProjectTask, task_code=task_code)
        
        # Check if user is assigned to this task
        if request.user != task.assigned_to:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        to_user_id = request.POST.get('to_user')
        notes = request.POST.get('notes', '')
        
        to_user = get_object_or_404(User, id=to_user_id)
        
        # Check if handoff already pending
        existing_handoff = TaskHandoff.objects.filter(
            task=task,
            status='pending'
        ).exists()
        
        if existing_handoff:
            return JsonResponse({'success': False, 'error': 'Handoff already pending for this task'})
        
        # Create handoff record
        handoff = TaskHandoff.objects.create(
            task=task,
            from_user=request.user,
            to_user=to_user,
            notes=notes,
            status='pending'
        )
        
        # Update task
        task.status = 'handoff'
        task.handoff_to = to_user
        task.handoff_requested_at = timezone.now()
        task.handoff_notes = notes
        task.save()
        
        # Create task history
        TaskHistory.objects.create(
            task=task,
            user=request.user,
            field='handoff',
            old_value=str(task.assigned_to),
            new_value=str(to_user)
        )
        
        # Create notification
        create_notification(
            recipient=to_user,
            sender=request.user,
            notification_type='handoff_request',
            message=f'{request.user.username} handed off task {task.task_code} to you',
            content_object=task,
            link=f'/employee/tasks/{task.task_code}/'
        )
        
        # Create activity log
        log_activity(request.user, 'handoff', task, f'Task handed off to {to_user.username}')
        
        return JsonResponse({'success': True, 'message': 'Handoff requested'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def respond_to_handoff(request, handoff_id):
    """Accept or reject task handoff"""
    if request.method == 'POST':
        handoff = get_object_or_404(TaskHandoff, id=handoff_id, to_user=request.user)
        
        action = request.POST.get('action')
        response_notes = request.POST.get('notes', '')
        
        if action == 'accept':
            # Update handoff
            handoff.status = 'accepted'
            handoff.responded_at = timezone.now()
            handoff.response_notes = response_notes
            handoff.save()
            
            # Update task
            task = handoff.task
            old_assigned = task.assigned_to
            task.assigned_to = request.user
            task.handoff_completed_at = timezone.now()
            task.status = 'todo'
            task.save()
            
            # Create task history
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                field='assigned_to',
                old_value=str(old_assigned),
                new_value=str(request.user)
            )
            
            # Create notification
            create_notification(
                recipient=handoff.from_user,
                sender=request.user,
                notification_type='handoff_accepted',
                message=f'{request.user.username} accepted task {task.task_code} handoff',
                content_object=task,
                link=f'/employee/tasks/{task.task_code}/'
            )
            
            # Create activity log
            log_activity(request.user, 'handoff', task, f'Task handoff accepted from {handoff.from_user.username}')
            
        elif action == 'reject':
            handoff.status = 'rejected'
            handoff.responded_at = timezone.now()
            handoff.response_notes = response_notes
            handoff.save()
            
            # Update task
            task = handoff.task
            task.handoff_to = None
            task.handoff_requested_at = None
            task.status = 'in_progress'
            task.save()
            
            # Create notification
            create_notification(
                recipient=handoff.from_user,
                sender=request.user,
                notification_type='handoff_rejected',
                message=f'{request.user.username} rejected task {task.task_code} handoff: {response_notes}',
                content_object=task,
                link=f'/employee/tasks/{task.task_code}/'
            )
            
            # Create activity log
            log_activity(request.user, 'handoff', task, f'Task handoff rejected from {handoff.from_user.username}')
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})



@login_required
def handoff_management(request):
    """Complete handoff management page"""
    return render(request, 'project/handoff_management.html')

@login_required
def check_handoff_alerts(request):
    """API endpoint to check handoff alerts"""
    # Tasks handed off to me
    pending_handoffs = TaskHandoff.objects.filter(
        to_user=request.user,
        status='pending'
    ).select_related('task', 'from_user', 'task__project')
    
    # Tasks ready for handoff (assigned to me and marked handoff)
    my_handoffs = ProjectTask.objects.filter(
        assigned_to=request.user,
        status='handoff'
    ).select_related('handoff_to', 'project')
    
    data = {
        'pending_handoffs': [
            {
                'id': h.id,
                'task_code': h.task.task_code,
                'task_title': h.task.title,
                'from_user': h.from_user.username,
                'from_user_id': h.from_user.id,
                'project_code': h.task.project.project_code,
                'project_title': h.task.project.title,
                'requested_at': h.requested_at.strftime('%Y-%m-%d %H:%M'),
                'notes': h.notes
            }
            for h in pending_handoffs
        ],
        'my_handoffs': [
            {
                'task_code': t.task_code,
                'task_title': t.title,
                'handoff_to': t.handoff_to.username if t.handoff_to else 'Unknown',
                'handoff_to_id': t.handoff_to.id if t.handoff_to else None,
                'project_code': t.project.project_code,
                'handoff_notes': t.handoff_notes
            }
            for t in my_handoffs
        ]
    }
    
    return JsonResponse(data)


# ==================== COMMENT VIEWS ====================

@login_required
def add_comment(request):
    """Add comment to project or task"""
    if request.method == 'POST':
        content = request.POST.get('content')
        content_type_id = request.POST.get('content_type')
        object_id = request.POST.get('object_id')
        parent_id = request.POST.get('parent')
        mentions = request.POST.getlist('mentions')
        
        if not content:
            return JsonResponse({'success': False, 'error': 'Comment content required'})
        
        # Get content type and object
        content_type = get_object_or_404(ContentType, id=content_type_id)
        content_object = content_type.get_object_for_this_type(id=object_id)
        
        # Check permission
        if isinstance(content_object, Project):
            if not has_project_access(request.user, content_object):
                return JsonResponse({'success': False, 'error': 'Permission denied'})
        elif isinstance(content_object, ProjectTask):
            project = content_object.project
            if not (request.user == content_object.assigned_to or has_project_access(request.user, project)):
                return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        # Create comment
        comment = Comment.objects.create(
            content=content,
            content_type=content_type,
            object_id=object_id,
            user=request.user,
            parent_id=parent_id
        )
        
        # Add mentions
        if mentions:
            comment.mentions.set(mentions)
            
            # Create notifications for mentions
            for user_id in mentions:
                if int(user_id) != request.user.id:  # Don't notify yourself
                    create_notification(
                        recipient_id=user_id,
                        sender=request.user,
                        notification_type='mention',
                        message=f'{request.user.username} mentioned you in a comment',
                        content_object=content_object,
                        link=f'#comment-{comment.id}'
                    )
        
        # Handle attachment
        if 'attachment' in request.FILES:
            comment.attachment = request.FILES['attachment']
            comment.save()
        
        # Create activity log
        log_activity(request.user, 'comment', content_object, f'Comment added by {request.user.username}')
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'content': comment.content,
                'user': request.user.username,
                'user_id': request.user.id,
                'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'attachment_url': comment.attachment.url if comment.attachment else None,
                'attachment_name': comment.attachment.name.split('/')[-1] if comment.attachment else None,
            }
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@login_required
def delete_comment(request, comment_id):
    """Delete a comment"""
    if request.method == 'POST':
        comment = get_object_or_404(Comment, id=comment_id)
        
        # Check permission
        if comment.user != request.user and not request.user.is_superuser:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        comment.delete()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# ==================== TASK PROGRESS UPDATE ====================

@login_required
def update_task_progress(request, task_code):
    """Update task progress"""
    if request.method == 'POST':
        task = get_object_or_404(ProjectTask, task_code=task_code)
        
        # Check permission
        if request.user != task.assigned_to and request.user != task.project.team_leader:
            return JsonResponse({'success': False, 'error': 'Permission denied'})
        
        progress = request.POST.get('progress')
        status = request.POST.get('status')
        actual_hours = request.POST.get('actual_hours')
        
        old_status = task.status
        old_progress = task.progress
        
        if progress:
            task.progress = int(progress)
        
        if status and status != task.status:
            task.status = status
            
            if status == 'in_progress' and not task.started_at:
                task.started_at = timezone.now()
            elif status == 'completed':
                task.completed_at = timezone.now()
                task.progress = 100
                
                # Create notification for project leader and manager
                recipients = []
                if task.project.team_leader and task.project.team_leader != request.user:
                    recipients.append(task.project.team_leader)
                if task.project.project_manager and task.project.project_manager != request.user:
                    recipients.append(task.project.project_manager)
                
                for recipient in recipients:
                    create_notification(
                        recipient=recipient,
                        sender=request.user,
                        notification_type='task_completed',
                        message=f'Task {task.task_code} completed by {request.user.username}',
                        content_object=task,
                        link=f'/admin/tasks/{task.task_code}/'
                    )
        
        if actual_hours:
            task.actual_hours = actual_hours
        
        task.save()
        
        # Create task history for changes
        if status and status != old_status:
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                field='status',
                old_value=old_status,
                new_value=status
            )
        
        if progress and int(progress) != old_progress:
            TaskHistory.objects.create(
                task=task,
                user=request.user,
                field='progress',
                old_value=str(old_progress),
                new_value=progress
            )
        
        return JsonResponse({
            'success': True,
            'progress': task.progress,
            'status': task.status,
            'status_display': task.get_status_display(),
            'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M') if task.completed_at else None
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


# ==================== NOTIFICATION VIEWS ====================

@login_required
def get_notifications(request):
    """Get user notifications"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender')[:20]
    
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'id': n.id,
                'message': n.message,
                'type': n.notification_type,
                'type_display': n.get_notification_type_display(),
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
                'created_at_human': (timezone.now() - n.created_at).total_seconds() // 3600,
                'is_read': n.is_read,
                'link': n.link
            }
            for n in notifications
        ]
    }
    
    return JsonResponse(data)


@login_required
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


# ==================== TEAM VIEWS ====================

@staff_member_required
def team_list(request):
    """List all teams"""
    teams = Team.objects.all().annotate(
        projects_count=Count('projects'),
        members_count=Count('members')
    ).select_related('team_leader')
    
    context = {
        'teams': teams,
    }
    return render(request, 'project/admin_team_list.html', context)


@staff_member_required
def create_team(request):
    """Create new team"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')
        team_leader_id = request.POST.get('team_leader')
        member_ids = request.POST.getlist('members')
        
        if Team.objects.filter(name=name).exists():
            messages.error(request, 'Team name already exists')
            return redirect('create_team')
        
        team = Team.objects.create(
            name=name,
            description=description,
            created_by=request.user
        )
        
        # Add team leader
        if team_leader_id:
            leader = get_object_or_404(User, id=team_leader_id)
            team.team_leader = leader
            team.members.add(leader)
        
        # Add other members
        if member_ids:
            members = User.objects.filter(id__in=member_ids)
            team.members.add(*members)
        
        team.save()
        
        # Notify team members
        for member in team.members.all():
            if member != request.user:
                create_notification(
                    recipient=member,
                    sender=request.user,
                    notification_type='team_added',
                    message=f'You have been added to team "{name}"',
                    content_object=team,
                    link=f'/admin/teams/{team.id}/'
                )
        
        messages.success(request, 'Team created successfully')
        return redirect('team_list')
    
    # GET request
    users = User.objects.filter(is_active=True)
    context = {'users': users}
    return render(request, 'project/admin_team_create.html', context)

@staff_member_required
def team_detail(request, team_id):
    """View team details"""
    team = get_object_or_404(Team, id=team_id)
    projects = team.projects.all()
    members = team.members.all()
    
    # Get ALL active employees from the system (yeh line IMPORTANT hai)
    all_employees = User.objects.filter(is_active=True).order_by('username')
    
    # Member task stats
    for member in members:
        member.task_count = ProjectTask.objects.filter(
            assigned_to=member,
            project__in=projects
        ).count()
        member.completed_tasks = ProjectTask.objects.filter(
            assigned_to=member,
            project__in=projects,
            status='completed'
        ).count()
    
    context = {
        'team': team,
        'projects': projects,
        'members': members,
        'all_employees': all_employees,  # ← YEH LINE IMPORTANT HAI
        'member_count': team.member_count(),
        'active_projects': projects.filter(status='active').count(),
        'completed_projects': projects.filter(status='completed').count(),
    }
    return render(request, 'project/admin_team_detail.html', context)


@staff_member_required
def update_team(request, team_id):
    """Update team details"""
    team = get_object_or_404(Team, id=team_id)
    
    if request.method == 'POST':
        team.name = request.POST.get('name')
        team.description = request.POST.get('description')
        
        team_leader_id = request.POST.get('team_leader')
        if team_leader_id:
            new_leader = get_object_or_404(User, id=team_leader_id)
            team.team_leader = new_leader
            # Ensure leader is in members
            if new_leader not in team.members.all():
                team.members.add(new_leader)
        
        team.save()
        
        messages.success(request, 'Team updated successfully')
        return redirect('team_detail', team_id=team.id)
    
    return redirect('team_detail', team_id=team.id)


@staff_member_required
def delete_team(request, team_id):
    """Delete team"""
    team = get_object_or_404(Team, id=team_id)
    
    # Check if team has projects
    if team.projects.exists():
        messages.error(request, 'Cannot delete team with active projects')
        return redirect('team_detail', team_id=team.id)
    
    team.delete()
    messages.success(request, 'Team deleted successfully')
    return redirect('team_list')


@staff_member_required
def add_team_members(request, team_id):
    """Add members to team"""
    team = get_object_or_404(Team, id=team_id)
    
    if request.method == 'POST':
        member_ids = request.POST.getlist('members')
        if member_ids:
            members = User.objects.filter(id__in=member_ids)
            team.members.add(*members)
            
            # Create notifications (optional)
            for member in members:
                Notification.objects.create(
                    recipient=member,
                    sender=request.user,
                    notification_type='team_added',
                    message=f'You have been added to team "{team.name}"',
                    content_object=team,
                    link=f'/admin/teams/{team.id}/'
                )
            
            messages.success(request, f'{len(members)} members added to team')
        else:
            messages.warning(request, 'No members selected')
    
    return redirect('team_detail', team_id=team.id)


@staff_member_required
def remove_team_member(request, team_id, member_id):
    """Remove member from team"""
    if request.method == 'POST':
        team = get_object_or_404(Team, id=team_id)
        member = get_object_or_404(User, id=member_id)
        
        # Can't remove team leader
        if member == team.team_leader:
            return JsonResponse({'success': False, 'error': 'Cannot remove team leader'})
        
        team.members.remove(member)
        
        # Create notification
        create_notification(
            recipient=member,
            sender=request.user,
            notification_type='team_updated',
            message=f'You have been removed from team "{team.name}"',
            content_object=team
        )
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@staff_member_required
def make_team_leader(request, team_id, member_id):
    """Make a member team leader"""
    if request.method == 'POST':
        team = get_object_or_404(Team, id=team_id)
        member = get_object_or_404(User, id=member_id)
        
        # Ensure member is in team
        if member not in team.members.all():
            team.members.add(member)
        
        team.team_leader = member
        team.save()
        
        # Create notification
        create_notification(
            recipient=member,
            sender=request.user,
            notification_type='team_updated',
            message=f'You are now the leader of team "{team.name}"',
            content_object=team,
            link=f'/admin/teams/{team.id}/'
        )
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})


@staff_member_required
def team_detail(request, team_id):
    """View team details"""
    team = get_object_or_404(Team, id=team_id)
    projects = team.projects.all()
    members = team.members.all()
    
    # Get ALL active employees from the system (for adding members)
    all_employees = User.objects.filter(is_active=True).order_by('username')
    
    # Member task stats
    for member in members:
        member.task_count = ProjectTask.objects.filter(
            assigned_to=member,
            project__in=projects
        ).count()
        member.completed_tasks = ProjectTask.objects.filter(
            assigned_to=member,
            project__in=projects,
            status='completed'
        ).count()
    
    context = {
        'team': team,
        'projects': projects,
        'members': members,
        'all_employees': all_employees,  # Add this line for all employees
        'member_count': team.member_count(),
        'active_projects': projects.filter(status='active').count(),
        'completed_projects': projects.filter(status='completed').count(),
    }
    return render(request, 'project/admin_team_detail.html', context)



@staff_member_required
def update_team(request, team_id):
    """Update team details"""
    team = get_object_or_404(Team, id=team_id)
    
    if request.method == 'POST':
        team.name = request.POST.get('name')
        team.description = request.POST.get('description')
        
        team_leader_id = request.POST.get('team_leader')
        if team_leader_id:
            new_leader = get_object_or_404(User, id=team_leader_id)
            team.team_leader = new_leader
            # Ensure leader is in members
            if new_leader not in team.members.all():
                team.members.add(new_leader)
        
        team.save()
        
        messages.success(request, 'Team updated successfully')
        return redirect('team_detail', team_id=team.id)
    
    return redirect('team_detail', team_id=team.id)







# ==================== PAYROLL MANAGEMENT (HR/ADMIN) ====================

@staff_member_required
def payroll_list(request):
    """List all payrolls with filters"""
    if not is_super_admin(request.user):
        messages.error(request, 'Access denied')
        return redirect('employee_dashboard')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    month = request.GET.get('month', '')
    
    payrolls = Payroll.objects.all().order_by('-pay_period_end')
    
    if status:
        payrolls = payrolls.filter(status=status)
    if month:
        payrolls = payrolls.filter(pay_period_start__year=month[:4], pay_period_start__month=month[5:7])
    
    # Statistics
    stats = {
        'total_payrolls': payrolls.count(),
        'pending_approval': payrolls.filter(status='pending_ceo').count(),
        'approved': payrolls.filter(status='approved').count(),
        'paid': payrolls.filter(status='paid').count(),
    }
    
    context = {
        'payrolls': payrolls,
        'stats': stats,
        'current_status': status,
        'current_month': month,
    }
    return render(request, 'payroll/payroll_list.html', context)


@staff_member_required
def generate_payroll(request):
    """Generate new payroll"""
    if not is_super_admin(request.user):
        messages.error(request, 'Access denied')
        return redirect('employee_dashboard')
    
    if request.method == 'POST':
        pay_period_start = request.POST.get('pay_period_start')
        pay_period_end = request.POST.get('pay_period_end')
        payment_date = request.POST.get('payment_date')
        
        # Validate dates
        start = datetime.strptime(pay_period_start, '%Y-%m-%d').date()
        end = datetime.strptime(pay_period_end, '%Y-%m-%d').date()
        
        if start > end:
            messages.error(request, 'Start date cannot be after end date')
            return redirect('generate_payroll')
        
        # Check if payroll already exists for this period
        if Payroll.objects.filter(pay_period_start=start, pay_period_end=end).exists():
            messages.error(request, 'Payroll already exists for this period')
            return redirect('payroll_list')
        
        # Create payroll
        payroll = Payroll.objects.create(
            pay_period_start=start,
            pay_period_end=end,
            payment_date=payment_date,
            generated_by=request.user,
            status='draft'
        )
        
        return redirect('add_payroll_employees', payroll_id=payroll.id)
    
    # Default dates (last month)
    today = date.today()
    first_day = date(today.year, today.month, 1)
    last_day = date(today.year, today.month, 1) - timedelta(days=1)
    last_month = last_day.replace(day=1)
    
    context = {
        'default_start': last_month.strftime('%Y-%m-%d'),
        'default_end': last_day.strftime('%Y-%m-%d'),
        'default_payment': today.strftime('%Y-%m-%d'),
    }
    return render(request, 'payroll/generate_payroll.html', context)

@staff_member_required
def add_payroll_employees(request, payroll_id):
    """Add employees to payroll and calculate salaries"""
    payroll = get_object_or_404(Payroll, id=payroll_id)
    
    if not is_super_admin(request.user):
        messages.error(request, 'Access denied')
        return redirect('employee_dashboard')
    
    if request.method == 'POST':
        selected_employees = request.POST.getlist('employees')
        
        if not selected_employees:
            messages.error(request, 'Please select at least one employee')
            return redirect('add_payroll_employees', payroll_id=payroll.id)
        
        total_gross = 0
        total_deductions = 0
        employee_count = 0
        
        for emp_id in selected_employees:
            employee = get_object_or_404(Employee, id=emp_id)
            
            # Get attendance for this period
            attendances = Attendance.objects.filter(
                employee=employee,
                date__gte=payroll.pay_period_start,
                date__lte=payroll.pay_period_end
            )
            
            # Calculate working days
            total_days = (payroll.pay_period_end - payroll.pay_period_start).days + 1
            present_days = attendances.filter(status='present').count()
            absent_days = attendances.filter(status='absent').count()
            leave_days = attendances.filter(status='on_leave').count()
            
            # ✅ FIXED LINES - Decimal calculations
            from decimal import Decimal
            
            if employee.salary:
                daily_rate = employee.salary / Decimal(total_days)
                basic_salary = daily_rate * Decimal(present_days)
                
                # Default calculations
                house_rent = basic_salary * Decimal('0.3')  # 30% of basic
                tax_deduction = basic_salary * Decimal('0.05')  # 5% tax
            else:
                basic_salary = Decimal('0')
                house_rent = Decimal('0')
                tax_deduction = Decimal('0')
            
            gross = basic_salary + house_rent
            net = gross - tax_deduction
            
            PayrollEmployee.objects.create(
                payroll=payroll,
                employee=employee,
                basic_salary=basic_salary,
                house_rent=house_rent,
                tax_deduction=tax_deduction,
                working_days=total_days,
                present_days=present_days,
                absent_days=absent_days,
                leave_days=leave_days,
                gross_pay=gross,
                total_deductions=tax_deduction,
                net_pay=net
            )
            
            total_gross += gross
            total_deductions += tax_deduction
            employee_count += 1
        
        # Update payroll totals
        payroll.total_gross_pay = total_gross
        payroll.total_deductions = total_deductions
        payroll.total_net_pay = total_gross - total_deductions
        payroll.employee_count = employee_count
        payroll.save()
        
        messages.success(request, f'Payroll generated for {employee_count} employees')
        return redirect('payroll_detail', payroll_id=payroll.id)
    
    # GET request - show employee selection
    employees = Employee.objects.filter(status='active')
    
    context = {
        'payroll': payroll,
        'employees': employees,
    }
    return render(request, 'payroll/add_employees.html', context)


@staff_member_required
def payroll_detail(request, payroll_id):
    """View payroll details"""
    payroll = get_object_or_404(Payroll, id=payroll_id)
    
    if not (is_super_admin(request.user) or request.user == payroll.generated_by):
        messages.error(request, 'Access denied')
        return redirect('payroll_list')
    
    # Get all employees in this payroll
    payroll_employees = PayrollEmployee.objects.filter(payroll=payroll).select_related('employee')
    
    context = {
        'payroll': payroll,
        'payroll_employees': payroll_employees,
        'can_edit': payroll.status == 'draft',
        'can_submit': payroll.status == 'draft',
    }
    return render(request, 'payroll/payroll_detail.html', context)


@staff_member_required
def submit_payroll_for_approval(request, payroll_id):
    """Submit payroll to CEO for approval"""
    payroll = get_object_or_404(Payroll, id=payroll_id)
    
    if not is_super_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if payroll.status != 'draft':
        return JsonResponse({'success': False, 'error': 'Payroll is not in draft status'})
    
    # Update status
    payroll.status = 'pending_ceo'
    payroll.save()
    
    # Create approval record
    PayrollApproval.objects.create(
        payroll=payroll,
        approved_by=request.user,
        role='hr',
        status='submitted',
        notes='Submitted for CEO approval'
    )
    
    # Notify CEO (you can implement notification system)
    
    return JsonResponse({'success': True, 'message': 'Payroll submitted for CEO approval'})

@staff_member_required
def edit_payroll_employee(request, payroll_employee_id):
    """Edit individual employee payroll details"""
    payroll_emp = get_object_or_404(PayrollEmployee, id=payroll_employee_id)
    
    if not is_super_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if payroll_emp.payroll.status != 'draft':
        return JsonResponse({'success': False, 'error': 'Cannot edit approved payroll'})
    
    if request.method == 'POST':
        try:
            # Get form data with proper Decimal conversion
            from decimal import Decimal
            
            payroll_emp.basic_salary = Decimal(request.POST.get('basic_salary', 0))
            payroll_emp.house_rent = Decimal(request.POST.get('house_rent', 0))
            payroll_emp.conveyance = Decimal(request.POST.get('conveyance', 0))
            payroll_emp.medical = Decimal(request.POST.get('medical', 0))
            payroll_emp.bonus = Decimal(request.POST.get('bonus', 0))
            payroll_emp.overtime = Decimal(request.POST.get('overtime', 0))
            payroll_emp.tax_deduction = Decimal(request.POST.get('tax_deduction', 0))
            payroll_emp.loan_deduction = Decimal(request.POST.get('loan_deduction', 0))
            payroll_emp.other_deductions = Decimal(request.POST.get('other_deductions', 0))
            
            # Calculate gross pay
            allowances = payroll_emp.house_rent + payroll_emp.conveyance + payroll_emp.medical + payroll_emp.bonus + payroll_emp.overtime
            payroll_emp.gross_pay = payroll_emp.basic_salary + allowances
            
            # Calculate total deductions
            payroll_emp.total_deductions = payroll_emp.tax_deduction + payroll_emp.loan_deduction + payroll_emp.other_deductions
            
            # Calculate net pay
            payroll_emp.net_pay = payroll_emp.gross_pay - payroll_emp.total_deductions
            
            # Save changes
            payroll_emp.save()
            
            # Update payroll totals
            payroll = payroll_emp.payroll
            employees = PayrollEmployee.objects.filter(payroll=payroll)
            
            from django.db.models import Sum
            payroll.total_gross_pay = employees.aggregate(Sum('gross_pay'))['gross_pay__sum'] or 0
            payroll.total_deductions = employees.aggregate(Sum('total_deductions'))['total_deductions__sum'] or 0
            payroll.total_net_pay = payroll.total_gross_pay - payroll.total_deductions
            payroll.save()
            
            # Return updated data
            return JsonResponse({
                'success': True,
                'message': 'Employee payroll updated successfully',
                'basic_salary': float(payroll_emp.basic_salary),
                'house_rent': float(payroll_emp.house_rent),
                'conveyance': float(payroll_emp.conveyance),
                'medical': float(payroll_emp.medical),
                'bonus': float(payroll_emp.bonus),
                'overtime': float(payroll_emp.overtime),
                'tax_deduction': float(payroll_emp.tax_deduction),
                'loan_deduction': float(payroll_emp.loan_deduction),
                'other_deductions': float(payroll_emp.other_deductions),
                'total_deductions': float(payroll_emp.total_deductions),
                'net_pay': float(payroll_emp.net_pay)
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})



# ==================== CEO APPROVAL VIEWS ====================

@login_required
def ceo_payroll_dashboard(request):
    """CEO dashboard for payroll approvals"""
    # Check if user is CEO (you need to define this based on your role system)
    # For now, checking super_admin
    if not is_super_admin(request.user):
        messages.error(request, 'Access denied')
        return redirect('employee_dashboard')
    
    # Pending approvals
    pending_payrolls = Payroll.objects.filter(status='pending_ceo').order_by('-generated_at')
    
    # Recent approvals
    recent_approvals = Payroll.objects.filter(
        Q(status='approved') | Q(status='rejected')
    ).order_by('-approved_at')[:10]
    
    # Statistics
    stats = {
        'pending': pending_payrolls.count(),
        'approved_this_month': Payroll.objects.filter(
            status='approved',
            approved_at__month=date.today().month
        ).count(),
        'total_paid': Payroll.objects.filter(status='paid').count(),
    }
    
    context = {
        'pending_payrolls': pending_payrolls,
        'recent_approvals': recent_approvals,
        'stats': stats,
    }
    return render(request, 'payroll/ceo_dashboard.html', context)


@login_required
def ceo_payroll_detail(request, payroll_id):
    """CEO view payroll details for approval"""
    payroll = get_object_or_404(Payroll, id=payroll_id)
    
    if not is_super_admin(request.user):
        messages.error(request, 'Access denied')
        return redirect('employee_dashboard')
    
    payroll_employees = PayrollEmployee.objects.filter(payroll=payroll).select_related('employee')
    
    context = {
        'payroll': payroll,
        'payroll_employees': payroll_employees,
        'is_ceo': True,
    }
    return render(request, 'payroll/ceo_payroll_detail.html', context)


@login_required
def approve_payroll(request, payroll_id):
    """CEO approves payroll"""
    payroll = get_object_or_404(Payroll, id=payroll_id)
    
    if not is_super_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if payroll.status != 'pending_ceo':
        return JsonResponse({'success': False, 'error': 'Payroll is not pending approval'})
    
    notes = request.POST.get('notes', '')
    
    # Update payroll
    payroll.status = 'approved'
    payroll.approved_by = request.user
    payroll.approved_at = timezone.now()
    payroll.approval_notes = notes
    payroll.save()
    
    # Create approval record
    PayrollApproval.objects.create(
        payroll=payroll,
        approved_by=request.user,
        role='ceo',
        status='approved',
        notes=notes
    )
    
    # Notify HR (you can implement notification)
    
    return JsonResponse({'success': True, 'message': 'Payroll approved successfully'})


@login_required
def reject_payroll(request, payroll_id):
    """CEO rejects payroll"""
    payroll = get_object_or_404(Payroll, id=payroll_id)
    
    if not is_super_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if payroll.status != 'pending_ceo':
        return JsonResponse({'success': False, 'error': 'Payroll is not pending approval'})
    
    notes = request.POST.get('notes', '')
    
    if not notes:
        return JsonResponse({'success': False, 'error': 'Rejection reason required'})
    
    # Update payroll
    payroll.status = 'rejected'
    payroll.approval_notes = notes
    payroll.save()
    
    # Create approval record
    PayrollApproval.objects.create(
        payroll=payroll,
        approved_by=request.user,
        role='ceo',
        status='rejected',
        notes=notes
    )
    
    return JsonResponse({'success': True, 'message': 'Payroll rejected'})


@staff_member_required
def get_payroll_employee(request, payroll_employee_id):
    """Get payroll employee data for editing"""
    payroll_emp = get_object_or_404(PayrollEmployee, id=payroll_employee_id)
    
    if not is_super_admin(request.user):
        return JsonResponse({'success': False, 'error': 'Permission denied'})
    
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'id': payroll_emp.id,
            'basic_salary': float(payroll_emp.basic_salary),
            'house_rent': float(payroll_emp.house_rent),
            'conveyance': float(payroll_emp.conveyance),
            'medical': float(payroll_emp.medical),
            'bonus': float(payroll_emp.bonus),
            'overtime': float(payroll_emp.overtime),
            'tax_deduction': float(payroll_emp.tax_deduction),
            'loan_deduction': float(payroll_emp.loan_deduction),
            'other_deductions': float(payroll_emp.other_deductions),
            'total_deductions': float(payroll_emp.total_deductions),
            'net_pay': float(payroll_emp.net_pay),
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})




# ==================== EMPLOYEE PAYROLL VIEWS ====================

@login_required
def employee_payrolls(request):
    """Employee view their payslips"""
    try:
        employee = Employee.objects.get(email=request.user.email)
    except Employee.DoesNotExist:
        messages.error(request, 'Employee record not found')
        return redirect('employee_dashboard')
    
    # Get payrolls where employee is included and approved
    payroll_employees = PayrollEmployee.objects.filter(
        employee=employee,
        payroll__status='approved'
    ).select_related('payroll').order_by('-payroll__pay_period_end')
    
    context = {
        'employee': employee,
        'payroll_employees': payroll_employees,
    }
    return render(request, 'payroll/employee_payrolls.html', context)


@login_required
def employee_payslip(request, payroll_employee_id):
    """View and print individual payslip"""
    payroll_emp = get_object_or_404(
        PayrollEmployee.objects.select_related('employee', 'payroll'),
        id=payroll_employee_id
    )
    
    # Check if employee owns this payslip
    if payroll_emp.employee.email != request.user.email:
        messages.error(request, 'Access denied')
        return redirect('employee_payrolls')
    
    # Only show approved payrolls
    if payroll_emp.payroll.status != 'approved':
        messages.error(request, 'Payslip not available')
        return redirect('employee_payrolls')
    
    # Calculate earnings breakdown
    earnings = {
        'Basic Salary': payroll_emp.basic_salary,
        'House Rent': payroll_emp.house_rent,
        'Conveyance': payroll_emp.conveyance,
        'Medical': payroll_emp.medical,
        'Bonus': payroll_emp.bonus,
        'Overtime': payroll_emp.overtime,
    }
    
    deductions = {
        'Tax': payroll_emp.tax_deduction,
        'Loan': payroll_emp.loan_deduction,
        'Other': payroll_emp.other_deductions,
    }
    
    context = {
        'payroll_emp': payroll_emp,
        'payroll': payroll_emp.payroll,
        'employee': payroll_emp.employee,
        'earnings': earnings,
        'deductions': deductions,
    }
    return render(request, 'payroll/employee_payslip.html', context)


@login_required
def download_payslip_pdf(request, payroll_employee_id):
    """Generate and download payslip as PDF"""
    # Similar to employee_payslip but returns PDF
    # You'll need to install reportlab or weasyprint
    pass






