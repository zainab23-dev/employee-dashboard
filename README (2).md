# Employee Dashboard

A role-based **HR and employee operations management system** built with Django. The platform brings employee records, attendance, leave requests, tasks, projects, teams, and payroll workflows together in one application, with dedicated dashboards for HR, the CEO, and employees.

<p align="left">
  <a href="https://employee-dashboard-snfl.onrender.com/"><strong>Live Demo</strong></a>
  ·
  <a href="https://github.com/zainab23-dev/employee-dashboard"><strong>Source Code</strong></a>
</p>

---

## Table of Contents

- [Live Demo](#live-demo)
- [Demo Login](#demo-login)
- [Project Overview](#project-overview)
- [Features](#features)
- [Roles and Workflows](#roles-and-workflows)
- [Screenshots](#screenshots)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Run Locally](#run-locally)
- [Environment Configuration](#environment-configuration)
- [Application Routes](#application-routes)
- [Deployment on Render](#deployment-on-render)
- [Known Limitations](#known-limitations)
- [Future Improvements](#future-improvements)
- [Contributors](#contributors)

---

## Live Demo

**Application:** <https://employee-dashboard-snfl.onrender.com/>

The live application can be used to explore the employee experience. Sign in with the demo account below.

## Demo Login

Use these credentials to access the **Employee** dashboard:

| Field | Demo credential |
| --- | --- |
| **Username** | `john` |
| **Password** | `emp123` |
| **Login page** | <https://employee-dashboard-snfl.onrender.com/> |
| **Employee dashboard** | `/employee/dashboard/` |

> **Demo account notice:** This is a shared public demo account. Information and changes may be visible to other visitors. Please do not enter personal or confidential information, change account credentials, or delete shared records. Admin and CEO passwords are not published in this README.

---

## Project Overview

The Employee Dashboard is designed to simplify routine workplace operations through three role-based areas:

- **HR / Admin:** manages employee records, attendance, leave requests, tasks, projects, teams, and payroll preparation.
- **CEO:** reviews company-level information and approves or rejects payroll submitted by HR.
- **Employee:** records attendance, manages breaks, follows assigned tasks, participates in project work, requests leave, and views payslips.

The application centralizes these activities and provides a defined approval process for payroll.

## Features

| Module | Capabilities |
| --- | --- |
| **Role-Based Access** | Separate dashboards and permissions for HR, the CEO, and employees. |
| **Employee Management** | Create, view, edit, and remove employee records; filter by department, employment type, and status; upload profile photos and documents. |
| **Attendance Tracking** | Clock in and out, record breaks and reasons, detect late arrivals and half-days, flag excessive breaks, and export attendance data to CSV. |
| **Leave Management** | Submit leave requests, view leave history, and let HR accept or reject requests using status, type, and department filters. |
| **Task Management** | Assign tasks with categories, priorities, due dates, and assignees; update progress; add comments; and review task activity history. |
| **Projects and Teams** | Organize work into projects, manage project tasks, create teams, assign team leaders, and hand off tasks between members through a response workflow. |
| **Payroll Management** | Generate payroll runs, adjust salary components, submit payroll for CEO approval, and let employees view their payslip history. |
| **Notifications and Activity Log** | In-app notifications for assignments, handoffs, and status changes, alongside a system-wide activity log. |

## Roles and Workflows

| Role | Main responsibilities |
| --- | --- |
| **Admin (HR)** | Manages employee information and attendance, assigns tasks, reviews leave requests, manages projects and teams, and prepares payroll for CEO approval. |
| **CEO** | Provides company-level oversight and approves or rejects payroll submitted by HR. |
| **Employee** | Tracks attendance and breaks, follows assigned tasks, comments on task work, requests leave, and views payslips. |

### Payroll approval workflow

```text
HR generates payroll
        ↓
HR submits payroll for approval
        ↓
CEO reviews the payroll
        ↓
CEO approves or rejects the payroll
        ↓
Approved payslips become available to employees
```

## Screenshots

The following screenshots illustrate the main areas of the application. Image paths are relative to the repository root.

### Employee dashboard

| Employee dashboard | Leave request |
| --- | --- |
| ![Employee dashboard](Pictures/emp_dashboard.png) | ![Leave request](Pictures/emp_leave.png) |
| **Leave history** | **My tasks** |
| ![Leave history](Pictures/emp_leave_history.png) | ![My tasks](Pictures/emp_my_task.png) |
| **Task detail** | **Project detail** |
| ![Task detail](Pictures/emp_task_detail_1.png) | ![Project detail](Pictures/emp_project_details.png) |
| **Projects** | **Payslips** |
| ![Projects](Pictures/emp_project.png) | ![Payslips](Pictures/emp_pay_slip.png) |

### HR / Admin dashboard

| Admin dashboard | Attendance |
| --- | --- |
| ![Admin dashboard](Pictures/Admin%20dashboard.png) | ![Attendance](Pictures/Admin%20Attendance.png) |
| **Employee management** | **Leave requests** |
| ![Employee management](Pictures/Admin%20emp%20management.png) | ![Leave requests](Pictures/Admin%20Leave%20Req.png) |
| **Payroll management** | **Payroll details** |
| ![Payroll management](Pictures/payroll_admin_1.png) | ![Payroll details](Pictures/Admin%20Payroll%202.png) |
| **Projects** | **Teams** |
| ![Projects](Pictures/Admin%20Project.png) | ![Teams](Pictures/Admin_Team_1.png) |
| **Task management** | |
| ![Task management](Pictures/Admin%20Task.png) | |

### CEO dashboard

| CEO payroll dashboard | Leave approval record |
| --- | --- |
| ![CEO payroll dashboard](Pictures/ceo_payroll_dashboard_1.png) | ![CEO leave detail](Pictures/ceo_leave_detail.png) |

## Technology Stack

| Area | Technology |
| --- | --- |
| **Programming language** | Python 3.13 |
| **Backend framework** | Django 6.0 |
| **Local database** | MySQL, using PyMySQL |
| **Production database** | PostgreSQL or MySQL, configured through `DATABASE_URL` |
| **Frontend** | Django Templates, custom CSS, JavaScript |
| **Image processing** | Pillow |
| **Static file serving** | WhiteNoise |
| **Application server** | Gunicorn |
| **Configuration** | `python-dotenv`, `dj-database-url` |
| **UI assets** | Inter (Google Fonts), Font Awesome 6.0.0, Chart.js |
| **Hosting** | Render |

## Project Structure

```text
employee-dashboard/
├── account/                  # Main application
│   ├── models.py             # Employees, attendance, leave, tasks, projects, teams, payroll
│   ├── views.py              # Dashboard and application request handling
│   ├── urls.py               # Application URL routing
│   ├── signals.py            # Notifications and activity logging
│   └── management/commands/  # Custom management commands
│       └── create_admin.py   # Provisions configured demo accounts
├── config/                   # Django settings, root URLs, WSGI/ASGI entry points
├── templates/                # Admin, CEO, employee, payroll, and project templates
├── static/css/               # Stylesheets
├── Pictures/                 # README screenshots
├── media/                    # User uploads (not tracked by Git)
├── build.sh                  # Render build script
├── render.yaml               # Render Blueprint configuration
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variable template
```

## Run Locally

### Prerequisites

- Python 3.13
- MySQL Server
- Git

### 1. Clone the repository

```bash
git clone https://github.com/zainab23-dev/employee-dashboard.git
cd employee-dashboard
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
```

**Windows (Command Prompt):**

```bat
venv\Scripts\activate
```

**macOS / Linux:**

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the MySQL database

Run this in your MySQL client:

```sql
CREATE DATABASE db_employee
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 5. Configure environment variables

Create your local `.env` file from the example:

**Windows (Command Prompt):**

```bat
copy .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

Open `.env` and configure the database connection and account settings. Use a unique Django `SECRET_KEY` and strong passwords for local accounts.

### 6. Apply migrations and create configured accounts

```bash
python manage.py migrate
python manage.py create_admin
```

The `create_admin` management command provisions the demo accounts using the account environment variables configured in `.env`.

### 7. Start the development server

```bash
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in your browser and sign in with an account configured for your local environment.

## Environment Configuration

Use `.env.example` as the configuration template. The main supported variables are:

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret key. Set a long, unique value in production. |
| `DEBUG` | Set to `True` for local development and `False` in production. |
| `ALLOWED_HOSTS` | Comma-separated list of permitted hostnames. The Render hostname is added automatically by the project configuration. |
| `DATABASE_URL` | Production database connection URL. When set, it takes precedence over the individual `DB_*` variables. |
| `DB_NAME` | Local MySQL database name. |
| `DB_USER` | Local MySQL username. |
| `DB_PASSWORD` | Local MySQL password. |
| `DB_HOST` | Local MySQL host. |
| `DB_PORT` | Local MySQL port. |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL` | Credentials and email for the HR account created by `create_admin`. |
| `CEO_USERNAME`, `CEO_PASSWORD`, `CEO_EMAIL` | Credentials and email for the CEO account. |
| `EMPLOYEE_USERNAME`, `EMPLOYEE_PASSWORD`, `EMPLOYEE_EMAIL`, `EMPLOYEE_NAME` | Credentials and display name for the sample employee. |

**Security:** Never commit `.env` or publish production secrets, database URLs, or privileged account passwords in source control, screenshots, or documentation. Use environment variables for deployment secrets.

## Application Routes

| Route | Purpose |
| --- | --- |
| `/` | Login page |
| `/dashboard/` | Redirects users to the dashboard for their role |
| `/admin-dashboard/` | HR overview |
| `/ceo/dashboard/` | CEO overview and payroll approvals |
| `/employee/dashboard/` | Employee overview, clock-in, and breaks |
| `/employee-management/` | Employee directory |
| `/admin/attendance/` | Attendance management |
| `/admin/leaves/` | Leave request review |
| `/admin/tasks/` | Task assignment and reporting |
| `/admin/projects/dashboard/` | Project management |
| `/admin/teams/` | Team management |
| `/payrolls/` | Payroll generation and management |
| `/ceo/payrolls/` | CEO payroll review |
| `/employee/tasks/` | Employee task list |
| `/employee/projects/` | Employee project list |
| `/admin/` | Django administration site |

## Deployment on Render

The application is configured for deployment on Render using `render.yaml` and `build.sh`.

### Database options

- **Render PostgreSQL (recommended):** create a PostgreSQL database and configure its Internal Database URL as `DATABASE_URL` for the web service.
- **Hosted MySQL:** use an external MySQL provider and configure its connection URL through `DATABASE_URL`. Check the provider's SSL requirements.

### Deployment steps

1. Push the project repository to GitHub.
2. In Render, choose **New → Blueprint** to use `render.yaml`, or create a **Web Service** manually.
3. For a manual web service, use the following commands:

   **Build command**
   ```bash
   ./build.sh
   ```

   **Start command**
   ```bash
   gunicorn config.wsgi:application
   ```

4. Add the required environment variables, including `DATABASE_URL`, `SECRET_KEY`, `DEBUG=False`, and the account configuration variables.
5. Deploy the service and review the Render logs for build or startup errors.

> **File storage note:** Render's free-tier filesystem is ephemeral. Uploaded profile photos, documents, and attachments may be lost when the service is redeployed. Use a persistent disk or an external storage service such as Amazon S3 or Cloudinary when persistent uploads are required.

## Known Limitations

- The chat module between employees and managers is not yet complete.
- Uploaded files require persistent or external storage for reliable retention across deployments.
- Automated test coverage for attendance, leave, and payroll workflows is still needed.

## Future Improvements

- Complete and improve the employee–manager chat module.
- Integrate persistent cloud storage for uploaded files.
- Add automated tests for attendance, leave, and payroll workflows.
- Add email notifications for leave decisions and payroll approvals.
- Add CSV and Excel export options for payroll reports.

## Contributors

**Zainab Asif and Nimra Manzoor**

GitHub: [@zainab23-dev](https://github.com/zainab23-dev)

Developed as a portfolio project. Feedback and contributions are welcome.
