# Standard Library
import os
import datetime
from datetime import time        
from datetime import date         
from datetime import datetime, timedelta
from django.utils import timezone

# Django Core & Utils
from django.db import models

# Django Auth & Models
from django.contrib.auth.models import User, AbstractBaseUser, BaseUserManager, PermissionsMixin

# Django Content Types
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation 

# ==================== EMPLOYEE MODEL ====================

class Employee(models.Model):
    # User relationship (optional)
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # Basic Information
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15)
    department = models.CharField(max_length=50)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    join_date = models.DateField(auto_now_add=True)
    
    # Employee ID (auto-generated)
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    # Profile Picture
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    
    # Position/Designation
    position = models.CharField(max_length=100, blank=True, default='Staff')
    
    # Personal Information
    date_of_birth = models.DateField(null=True, blank=True)
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    
    MARITAL_STATUS = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS, blank=True, null=True)
    
    blood_group = models.CharField(max_length=5, blank=True, null=True)
    nationality = models.CharField(max_length=50, blank=True, null=True, default='Pakistani')
    
    # Contact Information
    alternate_phone = models.CharField(max_length=15, blank=True, null=True)
    present_address = models.TextField(blank=True, null=True)
    permanent_address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True, null=True)
    
    # Bank Details
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    bank_branch = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    social_security = models.CharField(max_length=50, blank=True, null=True)
    
    # Work Information
    WORK_SHIFT = [
        ('morning', 'Morning (9 AM - 5 PM)'),
        ('evening', 'Evening (2 PM - 10 PM)'),
        ('night', 'Night (10 PM - 6 AM)'),
    ]
    work_shift = models.CharField(max_length=10, choices=WORK_SHIFT, default='morning', blank=True, null=True)
    
    WEEKLY_OFF = [
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
        ('monday', 'Monday'),
    ]
    weekly_off = models.CharField(max_length=10, choices=WEEKLY_OFF, default='sunday', blank=True, null=True)
    
    EMPLOYMENT_TYPE = [
        ('permanent', 'Permanent'),
        ('contract', 'Contract'),
        ('intern', 'Intern'),
        ('probation', 'Probation'),
        ('fulltime', 'Full Time'),
        ('parttime', 'Part Time'),
    ]
    employment_type = models.CharField(max_length=10, choices=EMPLOYMENT_TYPE, default='permanent', blank=True, null=True)
    
    EMPLOYEE_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
        ('terminated', 'Terminated'),
        ('onboarding', 'Onboarding'),
    ]
    status = models.CharField(max_length=10, choices=EMPLOYEE_STATUS, default='active', blank=True, null=True)
    
    # ========== NEW FIELDS FOR ATTENDANCE ==========
    shift_start_time = models.TimeField(default='09:00:00')  # ✅ 9:00 AM
    shift_end_time = models.TimeField(default='18:00:00')    # ✅ 6:00 PM
    grace_period_minutes = models.IntegerField(default=30)    # ✅ 30 min
    
    class Meta:
        db_table = 'account_employee'
    
    def save(self, *args, **kwargs):
        # Auto-generate employee_id if not provided
        if not self.employee_id:
            last_employee = Employee.objects.order_by('-id').first()
            if last_employee:
                self.employee_id = f"EMP{str(last_employee.id + 1).zfill(3)}"
            else:
                self.employee_id = "EMP001"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - {self.employee_id}"


# ==================== USER ROLE MODEL ====================
class UserRole(models.Model):
    """User roles for permissions"""
    ROLE_CHOICES = [
        ('employee', 'Employee'),
        ('admin', 'Admin'),
        ('ceo', 'CEO'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='role')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_roles'
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"


# ==================== ATTENDANCE MODEL ====================

class Attendance(models.Model):
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('on_leave', 'On Leave'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=date.today)
    
    # Check-in/Check-out as DateTime (not just Time)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    
    # ========== NEW FIELDS FOR TRACKING ==========
    is_late = models.BooleanField(default=False)
    late_minutes = models.IntegerField(default=0)
    is_half_day = models.BooleanField(default=False)
    total_working_hours = models.FloatField(default=0.0)  # in hours
    
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default='absent')
    notes = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'account_attendance'
        unique_together = ['employee', 'date']
        ordering = ['-date']
    
    def calculate_status(self):
        """Calculate attendance status based on check-in time"""
        if not self.check_in:
            self.status = 'absent'
            return
        
        # Convert date to datetime for comparison
        shift_start = datetime.combine(self.date, self.employee.shift_start_time)
        if timezone.is_naive(shift_start):
            shift_start = timezone.make_aware(shift_start)
        
        # Grace period ke saath compare
        grace_end = shift_start + timedelta(minutes=self.employee.grace_period_minutes)
        
        if self.check_in <= shift_start:
            self.is_late = False
            self.late_minutes = 0
            self.is_half_day = False
            self.status = 'present'
        elif self.check_in <= grace_end:
            self.is_late = True
            self.late_minutes = int((self.check_in - shift_start).total_seconds() / 60)
            self.is_half_day = False
            self.status = 'late'
        else:
            self.is_late = True
            self.late_minutes = int((self.check_in - shift_start).total_seconds() / 60)
            self.is_half_day = True
            self.status = 'half_day'
    
    def calculate_working_hours(self):
        """Calculate total working hours"""
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            # Break time subtract karo
            total_breaks = Break.objects.filter(
                attendance=self,
                end_time__isnull=False
            ).aggregate(
                total=models.Sum('duration_minutes')
            )['total'] or 0
            
            working_minutes = (delta.total_seconds() / 60) - total_breaks
            self.total_working_hours = round(working_minutes / 60, 2)
            self.save()
    
    def __str__(self):
        return f"{self.employee.name} - {self.date} - {self.status}"


# ==================== BREAK MODEL ====================

class Break(models.Model):
    BREAK_TYPES = [
        ('lunch', 'Lunch Break'),
        ('tea', 'Tea Break'),
        ('prayer', 'Prayer Break'),
        ('personal', 'Personal Break'),
        ('other', 'Other'),
    ]
    
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='breaks')
    break_type = models.CharField(max_length=10, choices=BREAK_TYPES)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    # ========== NEW FIELDS FOR EXCESSIVE BREAKS ==========
    duration_minutes = models.IntegerField(default=0)
    requires_reason = models.BooleanField(default=False)
    reason = models.TextField(blank=True, null=True)
    reason_submitted_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'account_break'
    
    def save(self, *args, **kwargs):
        # Calculate duration if end_time is set
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.duration_minutes = int(delta.total_seconds() / 60)
            
            # Check if break is excessive
            if self.break_type == 'tea' and self.duration_minutes > 15:
                self.requires_reason = True
            elif self.break_type == 'lunch' and self.duration_minutes > 60:
                self.requires_reason = True
            elif self.duration_minutes > 30:
                self.requires_reason = True
        
        super().save(*args, **kwargs)
    
    @property
    def duration(self):
        if self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return 0
    
    def __str__(self):
        return f"{self.get_break_type_display()} - {self.attendance.employee.name} - {self.attendance.date}"


# ==================== SALARY MODEL ====================

class Salary(models.Model):
    SALARY_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='salaries')
    month = models.DateField()  # First day of the month
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    house_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    conveyance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medical = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overtime = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=SALARY_STATUS, default='pending')
    payment_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'account_salary'
        unique_together = ['employee', 'month']
        ordering = ['-month']
    
    @property
    def net_salary(self):
        total = (self.basic_salary + self.house_rent + self.conveyance + 
                self.medical + self.bonus + self.overtime)
        deductions = self.deductions + self.tax
        return total - deductions
    
    def __str__(self):
        return f"{self.employee.name} - {self.month.strftime('%B %Y')}"


# ==================== DOCUMENT MODEL ====================

class Document(models.Model):
    DOCUMENT_TYPES = [
        ('cv', 'CV/Resume'),
        ('contract', 'Employment Contract'),
        ('id', 'ID Card'),
        ('degree', 'Educational Degree'),
        ('certificate', 'Certificate'),
        ('other', 'Other'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='employee_documents/')
    notes = models.TextField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'account_document'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.employee.name} - {self.title}"


# ==================== ADMIN MODEL ====================
class Admin(models.Model):
    ROLE_CHOICES = [
        ('hr', 'HR Manager'),
        ('ceo', 'Chief Executive Officer'),
        ('manager', 'Department Manager'),
        ('finance', 'Finance Manager'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, unique=True)
    department = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='hr')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'account_admin'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


# ==================== LEAVE REQUEST MODEL ====================

class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ('annual', 'Annual Leave'),
        ('sick', 'Sick Leave'),
        ('personal', 'Personal Leave'),
        ('unpaid', 'Unpaid Leave'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    review_notes = models.TextField(blank=True, null=True)
    review_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'account_leaves'
        ordering = ['-created_at']
    
    def days_count(self):
        return (self.end_date - self.start_date).days + 1
    
    def __str__(self):
        return f"{self.employee.name} - {self.leave_type} ({self.start_date} to {self.end_date})"


# ==================== TASK MANAGEMENT MODELS ====================

class TaskCategory(models.Model):
    """Task categories like Development, Design, HR, etc."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=20, default='#2563eb')  # For UI
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'account_task_category'
        verbose_name_plural = 'Task Categories'
    
    def __str__(self):
        return self.name


class Task(models.Model):
    """Main Task Model"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('on_hold', 'On Hold'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Task Details
    title = models.CharField(max_length=200)
    description = models.TextField()
    task_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    # Relationships
    created_by = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, related_name='created_tasks')
    assigned_to = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='tasks')
    category = models.ForeignKey(TaskCategory, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Dates
    created_date = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField()
    completed_date = models.DateTimeField(null=True, blank=True)
    
    # Status & Priority
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    
    # Progress
    progress_percentage = models.IntegerField(default=0)  # 0-100
    
    # Additional Info
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'account_tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['due_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.task_id:
            last_task = Task.objects.order_by('-id').first()
            if last_task:
                self.task_id = f"TSK{str(last_task.id + 1).zfill(4)}"
            else:
                self.task_id = "TSK0001"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.task_id} - {self.title}"
    
    @property
    def is_overdue(self):
        if self.due_date and self.status != 'completed':
            return date.today() > self.due_date
        return False
    
    @property
    def days_remaining(self):
        if self.due_date and self.status != 'completed':
            delta = self.due_date - date.today()
            return delta.days
        return None


class TaskComment(models.Model):
    """Comments/Notes on Tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'account_task_comments'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment on {self.task.task_id} by {self.user.username}"


class TaskAttachment(models.Model):
    """Files attached to tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'account_task_attachments'


class TaskHistory(models.Model):
    """Track all task changes"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)
    field_name = models.CharField(max_length=50, blank=True, null=True)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'account_task_history'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task.task_id} - {self.action} by {self.user}"


# ==================== TEAM MODEL ====================

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    team_leader = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='led_team'
    )
    members = models.ManyToManyField(User, related_name='teams', blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_teams'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'teams'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def member_count(self):
        return self.members.count()


# ==================== PROJECT MODEL ====================

class Project(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    project_code = models.CharField(max_length=20, unique=True, blank=True)
    
    # Dates
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status & Priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Budget
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Relationships
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='projects')
    team_leader = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='led_projects'
    )
    project_manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_projects'
    )
    members = models.ManyToManyField(User, related_name='projects', blank=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_projects'
    )
    
    class Meta:
        db_table = 'projects'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.project_code:
            last_project = Project.objects.order_by('-id').first()
            if last_project:
                self.project_code = f"PRJ{str(last_project.id + 1).zfill(4)}"
            else:
                self.project_code = "PRJ0001"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.project_code} - {self.title}"
    
    @property
    def progress(self):
        tasks = self.tasks.all()
        if tasks.exists():
            completed = tasks.filter(status='completed').count()
            return int((completed / tasks.count()) * 100)
        return 0
    
    @property
    def days_remaining(self):
        delta = self.end_date - timezone.now().date()
        return delta.days
    
    @property
    def task_stats(self):
        tasks = self.tasks.all()
        return {
            'total': tasks.count(),
            'todo': tasks.filter(status='todo').count(),
            'in_progress': tasks.filter(status='in_progress').count(),
            'review': tasks.filter(status='review').count(),
            'completed': tasks.filter(status='completed').count(),
        }


# ==================== PROJECT TASK MODEL ====================

class ProjectTask(models.Model):
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('blocked', 'Blocked'),
        ('handoff', 'Ready for Handoff'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    TASK_TYPE_CHOICES = [
        ('task', 'Task'),
        ('bug', 'Bug'),
        ('feature', 'Feature'),
        ('enhancement', 'Enhancement'),
        ('documentation', 'Documentation'),
        ('testing', 'Testing'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    task_code = models.CharField(max_length=20, unique=True, blank=True)
    
    task_type = models.CharField(
        max_length=20, 
        choices=TASK_TYPE_CHOICES, 
        default='task'
    )
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Status & Priority
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Progress
    progress = models.IntegerField(default=0, help_text="Progress percentage (0-100)")
    
    story_points = models.IntegerField(null=True, blank=True, help_text="Story points for agile estimation")
    
    # Relationships
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='project_tasks'
    )
    assigned_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_project_tasks'
    )
    
    # Handoff Feature
    handoff_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='handoff_tasks'
    )
    handoff_requested_at = models.DateTimeField(null=True, blank=True)
    handoff_completed_at = models.DateTimeField(null=True, blank=True)
    handoff_notes = models.TextField(blank=True)
    
    # Subtasks (Self-referential)
    parent_task = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subtasks'
    )
    
    depends_on = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        blank=True, 
        related_name='blocked_by'
    )
    
    # Time tracking
    estimated_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Tags/Labels
    tags = models.CharField(max_length=200, blank=True, help_text="Comma separated tags")
    
    class Meta:
        db_table = 'project_tasks'
        ordering = ['due_date', '-priority']
    
    def save(self, *args, **kwargs):
        if not self.task_code:
            last_task = ProjectTask.objects.order_by('-id').first()
            if last_task:
                self.task_code = f"PTSK{str(last_task.id + 1).zfill(4)}"
            else:
                self.task_code = "PTSK0001"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.task_code} - {self.title}"
    
    @property
    def is_overdue(self):
        return self.due_date < timezone.now().date() and self.status != 'completed'
    
    @property
    def blocked_by_tasks(self):
        return self.blocked_by.filter(status__in=['todo', 'in_progress', 'review'])


# ==================== TASK HANDOFF MODEL ====================

class TaskHandoff(models.Model):
    task = models.ForeignKey(ProjectTask, on_delete=models.CASCADE, related_name='handoffs')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='handoffs_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='handoffs_received')
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ], default='pending')
    notes = models.TextField(blank=True)
    response_notes = models.TextField(blank=True)
    
    class Meta:
        db_table = 'task_handoffs'
        ordering = ['-requested_at']


# ==================== COMMENT MODEL ====================

class Comment(models.Model):
    content = models.TextField()
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='replies'
    )
    
    mentions = models.ManyToManyField(User, related_name='mentioned_in_comments', blank=True)
    attachment = models.FileField(upload_to='comment_attachments/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'comments'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment by {self.user.username}"


# ==================== NOTIFICATION MODEL (Project) ====================

class Notification(models.Model):
    TYPE_CHOICES = [
        ('task_assigned', 'Task Assigned'),
        ('task_updated', 'Task Updated'),
        ('task_completed', 'Task Completed'),
        ('handoff_request', 'Handoff Request'),
        ('handoff_accepted', 'Handoff Accepted'),
        ('handoff_rejected', 'Handoff Rejected'),
        ('comment', 'New Comment'),
        ('mention', 'Mentioned in Comment'),
        ('project_created', 'New Project'),
        ('team_added', 'Added to Team'),
        ('deadline', 'Deadline Approaching'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_notifications')
    
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.CharField(max_length=255)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']


# ==================== ACTIVITY LOG MODEL ====================

class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('status_change', 'Status Changed'),
        ('assign', 'Assigned'),
        ('handoff', 'Handed Off'),
        ('complete', 'Completed'),
        ('comment', 'Commented'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'activity_logs'
        ordering = ['-created_at']


# ==================== PAYROLL MODELS ====================

class Payroll(models.Model):
    """Payroll generation for employees"""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_ceo', 'Pending CEO Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    
    # Payroll Details
    payroll_code = models.CharField(max_length=20, unique=True, blank=True)
    pay_period_start = models.DateField()
    pay_period_end = models.DateField()
    payment_date = models.DateField()
    
    # Generated by HR
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='generated_payrolls')
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # CEO Approval
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_payrolls')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True, null=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Totals
    total_gross_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_net_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    employee_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'payrolls'
        ordering = ['-pay_period_end']
    
    def save(self, *args, **kwargs):
        if not self.payroll_code:
            last_payroll = Payroll.objects.order_by('-id').first()
            if last_payroll:
                self.payroll_code = f"PRL{str(last_payroll.id + 1).zfill(4)}"
            else:
                self.payroll_code = "PRL0001"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.payroll_code} - {self.pay_period_start} to {self.pay_period_end}"


class PayrollEmployee(models.Model):
    """Individual employee payroll details"""
    
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='employees')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    
    # Salary Details
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    house_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    conveyance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    medical = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    overtime = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Attendance & Leave Impact
    working_days = models.IntegerField(default=0)
    present_days = models.IntegerField(default=0)
    absent_days = models.IntegerField(default=0)
    leave_days = models.IntegerField(default=0)
    
    # Deductions
    tax_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    loan_deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    other_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Totals
    gross_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Payment Status
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payroll_employees'
        unique_together = ['payroll', 'employee']
    
    def __str__(self):
        return f"{self.employee.name} - {self.payroll.payroll_code}"
    
    def calculate_net_pay(self):
        """Calculate net pay after deductions"""
        self.gross_pay = self.basic_salary + self.house_rent + self.conveyance + self.medical + self.bonus + self.overtime
        self.total_deductions = self.tax_deduction + self.loan_deduction + self.other_deductions
        self.net_pay = self.gross_pay - self.total_deductions
        return self.net_pay


class PayrollApproval(models.Model):
    """Approval workflow tracking"""
    
    payroll = models.ForeignKey(Payroll, on_delete=models.CASCADE, related_name='approvals')
    approved_by = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50)  # 'hr', 'ceo'
    status = models.CharField(max_length=20)  # 'approved', 'rejected'
    notes = models.TextField(blank=True, null=True)
    approved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payroll_approvals'
        ordering = ['-approved_at']



# CHAT MODELS STARTS FROM HERE

# ==================== CHAT/MESSAGING MODELS ====================

class ChatRequest(models.Model):
    """Chat approval requests (Employee → Employee)"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_requests_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_requests_received')
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Approval
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Rejection
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username}"


class ChatRoom(models.Model):
    """Chat room for conversations"""
    name = models.CharField(max_length=255, blank=True)
    participants = models.ManyToManyField(User, related_name='chat_rooms')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Link to request
    chat_request = models.OneToOneField(ChatRequest, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_monitored = models.BooleanField(default=False)
    monitored_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    
    class Meta:
        db_table = 'chat_rooms'
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.name or f"Room {self.id}"
    
    def get_other_participant(self, user):
        return self.participants.exclude(id=user.id).first()


class ChatMessage(models.Model):
    """Individual chat messages"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    content = models.TextField()
    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.username}"


class ChatNotification(models.Model):
    """Chat notifications"""
    TYPES = [
        ('new_request', 'New Request'),
        ('request_approved', 'Approved'),
        ('request_rejected', 'Rejected'),
        ('new_message', 'New Message'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_notifications')
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPES)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_notifications'
        ordering = ['-created_at']


