# 🏢 Employee Dashboard

**A Django-based HR and operations platform for managing employees, attendance, leave, tasks, projects, teams, and payroll, with role-based dashboards for HR, the CEO, and employees.**

The system consolidates everyday workplace operations into one application. HR manages employee records, attendance, leave, and payroll generation. The CEO reviews and approves payroll. Employees clock in, request leave, follow assigned tasks, and collaborate through comments.

**Live website:** [employee-dashboard-snfl.onrender.com](https://employee-dashboard-snfl.onrender.com/)
**Source code:** [github.com/zainab23-dev/employee-dashboard](https://github.com/zainab23-dev/employee-dashboard)

---

---

## ✨ Key Features

| Feature | Description |
| --- | --- |
| **Role-Based Access** | Separate dashboards and permissions for HR (admin), the CEO, and employees. |
| **Employee Management** | Create, view, edit, and remove employee records. Filter by department, employment type, and status. Upload profile photos and documents. |
| **Attendance Tracking** | Clock-in and clock-out, break tracking with reasons, late-arrival and half-day detection, excessive-break alerts, and CSV export. |
| **Leave Management** | Employees submit leave requests and view their history. HR accepts or rejects requests, with filters by status, type, and department. |
| **Task Management** | HR assigns tasks with categories, priorities, due dates, and assignees. Employees follow their assigned tasks, update progress, and comment on them. Full activity history is kept for each task. |
| **Projects and Teams** | Organize work into projects with task boards. Build teams, assign team leaders, and hand off tasks between members with a response workflow. |
| **Payroll** | HR generates payroll runs, adjusts salary components, and submits them for CEO approval. The CEO approves or rejects each run. Employees view their payslip history. |
| **Notifications and Activity Log** | In-app notifications for assignments, handoffs, and status changes, plus a system-wide activity log. |

---

## 🧠 Authority and Workflow

| Role | Responsibilities |
| --- | --- |
| **Admin (HR)** | Manages employees and attendance. Assigns tasks. Accepts or rejects leave requests. Generates payroll and submits it for CEO approval. |
| **CEO** | Holds the highest authority. Approves or rejects payroll submitted by HR. Has company-level oversight through the CEO dashboard. |
| **Employee** | Follows assigned tasks and comments on them, in both the task section and the project task section. Clocks in and out, takes breaks, requests leave, and views payslips. |

**Payroll workflow:** HR generates a payroll run → HR submits it for approval → the CEO approves or rejects it → approved payslips become available to employees.

---

## ⚙️ Tech Stack

| Layer | Technology |
| --- | --- |
| Language | Python 3.13 |
| Framework | Django 6.0 |
| Database (local) | MySQL, via PyMySQL |
| Database (production) | PostgreSQL or MySQL, configured through `DATABASE_URL` |
| Image processing | Pillow |
| Static files | WhiteNoise |
| Application server | Gunicorn |
| Configuration | python-dotenv, dj-database-url |
| Frontend | Django Templates, custom CSS, JavaScript |
| UI assets | Inter (Google Fonts), Font Awesome 6.0.0, Chart.js |
| Hosting | Render |

---

## 🗄️ Project Structure

```
employee-dashboard/
├── account/                 Main application
│   ├── models.py            Employees, attendance, leave, tasks, projects, teams, payroll
│   ├── views.py             Request handling for every dashboard
│   ├── urls.py              URL routing
│   ├── signals.py           Notifications and activity logging
│   └── management/commands/ create_admin: provisions demo accounts from environment variables
├── config/                  Project settings, root URLs, WSGI/ASGI entry points
├── templates/               HTML templates (admin, CEO, employee, payroll, project)
├── static/css/              Stylesheets
├── Pictures/                Screenshots used in this README
├── media/                   User uploads (not tracked by git)
├── build.sh                 Build script used by Render
├── render.yaml              Render Blueprint configuration
├── requirements.txt         Python dependencies
└── .env.example             Template for local environment variables
```

---

## 🚀 Getting Started

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/zainab23-dev/employee-dashboard.git
cd employee-dashboard
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create the database

```sql
CREATE DATABASE db_employee CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 4. Configure environment variables

```bash
cp .env.example .env            # Windows: copy .env.example .env
```

Open `.env` and set `DB_PASSWORD` and the demo account values. Never commit `.env`.

### 5. Apply migrations, create accounts, and run

```bash
python manage.py migrate
python manage.py create_admin
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in with the credentials you configured.

---

## 🔧 Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `SECRET_KEY` | Yes (production) | Django secret key. Use a long, random value. |
| `DEBUG` | Yes | `True` for local development, `False` in production. |
| `ALLOWED_HOSTS` | Yes | Comma-separated hostnames. The Render hostname is added automatically. |
| `DATABASE_URL` | Production | Full database connection string. Overrides the `DB_*` variables. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Local development | MySQL connection settings. |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL` | Optional | Credentials for the HR account created by `create_admin`. |
| `CEO_USERNAME`, `CEO_PASSWORD`, `CEO_EMAIL` | Optional | Credentials for the CEO account. |
| `EMPLOYEE_USERNAME`, `EMPLOYEE_PASSWORD`, `EMPLOYEE_EMAIL`, `EMPLOYEE_NAME` | Optional | Credentials and display name for a sample employee. |

---

## 🌐 Application Routes

| URL | Purpose |
| --- | --- |
| `/` | Login |
| `/dashboard/` | Role-based redirect to the correct dashboard |
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
| `/admin/` | Django admin |

---

## ☁️ Deploying to Render

Render does not offer managed MySQL, so choose one database option:

- **Render PostgreSQL (recommended):** create a free PostgreSQL instance and use its *Internal Database URL* as `DATABASE_URL`.
- **Hosted MySQL:** use a provider such as Aiven, TiDB Cloud, or Railway, with a URL in the form `mysql://user:password@host:port/db_employee`. Some providers require SSL.

**Steps:**

1. Push the repository to GitHub.
2. In Render, select **New > Blueprint** (uses `render.yaml`), or **New > Web Service** with:
   - Build command: `./build.sh`
   - Start command: `gunicorn config.wsgi:application`
3. Add environment variables: `DATABASE_URL`, `SECRET_KEY`, `DEBUG=False`, and the account variables above.
4. Deploy. `build.sh` installs dependencies, collects static files, applies migrations, and creates the configured accounts.

> **Note:** Render's free tier has an ephemeral filesystem. Uploaded files (profile photos, documents, attachments) are lost on redeploy. For persistent storage, attach a Render Disk or use cloud storage such as S3 or Cloudinary.

---

## ⚠️ Known Limitations

- **Chat is not yet available.** The chat models exist, but the chat views are not implemented, so the chat routes are disabled.
- **Uploads are not persistent** on the free hosting tier.
- **Automated tests are not yet written.** `account/tests.py` is currently a placeholder.

---

## 🔭 Future Scope

- Complete the chat module between employees and managers
- Move file uploads to persistent cloud storage
- Add automated tests for attendance, leave, and payroll workflows
- Email notifications for leave decisions and payroll approvals
- CSV and Excel export for payroll reports

---

## 👩‍💻 Author

**Zainab Asif & Nimra Manzoor**

GitHub: [@zainab23-dev](https://github.com/zainab23-dev)

*Developed as a portfolio project. Feedback and contributions are welcome.*
