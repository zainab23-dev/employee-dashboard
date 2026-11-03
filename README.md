
# Employee Dashboard System

A Django web application for managing employees, attendance, leave, tasks, projects, teams and payroll, with separate admin and employee dashboards.

## Features

- Role-based login (Admin / Employee)
- Employee management with profile pictures and documents
- Attendance tracking with breaks and half-days
- Leave requests and approval workflow
- Task management with categories, comments, attachments and history
- Project, team and milestone management with task hand-offs and notifications
- Payroll generation, approval and employee payslips

## Tech Stack

- Python 3.13, Django 6.0
- MySQL (local development) / any `DATABASE_URL` database (production)
- WhiteNoise for static files, Gunicorn for serving
- Deployed on Render

## Run locally

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv venv
venv\Scripts\activate          # Windows  (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
```

### 2. Create the database in MySQL Workbench

Connect to your local server and run:

```sql
CREATE DATABASE db_employee CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Configure environment variables

```bash
copy .env.example .env         # macOS/Linux: cp .env.example .env
```

Edit `.env` and set `DB_PASSWORD` (your MySQL root password) and the optional `ADMIN_*` values.

### 4. Migrate and create the admin user

```bash
python manage.py migrate
python manage.py create_admin
python manage.py runserver
```

Open http://127.0.0.1:8000/ and log in with the `ADMIN_USERNAME` / `ADMIN_PASSWORD` you set.

## Deploy on Render

Render does not offer managed MySQL, so choose one database option:

- **Easiest:** create a free **Render PostgreSQL** database and use its *Internal Database URL*.
- **Keep MySQL:** use a hosted MySQL service (e.g. Aiven, TiDB Cloud, Railway) and use a URL like `mysql://user:password@host:port/db_employee`. Some providers require SSL; check their docs.

Steps:

1. Push this repo to GitHub.
2. In Render: **New > Blueprint** (uses `render.yaml`), or **New > Web Service** with:
   - Build command: `./build.sh`
   - Start command: `gunicorn config.wsgi:application`
3. Add environment variables: `DATABASE_URL`, `SECRET_KEY`, `DEBUG=False`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`.
4. Deploy. `build.sh` installs dependencies, collects static files, runs migrations and creates the admin user.

> **Note:** Render's free tier has an ephemeral filesystem, so uploaded files (profile pictures, documents, attachments) are lost on redeploy. For persistent uploads, add a Render Disk or use cloud storage such as S3/Cloudinary.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` locally, `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hosts (Render's hostname is added automatically) |
| `DATABASE_URL` | Production database URL (overrides the `DB_*` variables) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Local MySQL settings |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL` | Used by `create_admin` |

## Project structure

```
account/     Main app: models, views, urls, management commands
config/      Django project settings and WSGI/ASGI
templates/   HTML templates (admin, employee, payroll, project)
static/      CSS
media/       User uploads (not tracked by git)
```




