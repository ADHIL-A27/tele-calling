# College Admission Telecalling CRM

A Django + SQLite CRM for managing student enquiries, telecaller assignment,
calling activity, follow-ups and the admission pipeline, with a claymorphism
design system (Bootstrap 5 + Tailwind CSS, isolated with a `tw-` prefix) and
HTMX for partial updates.

## Setup

```bash
python -m venv venv
venv/Scripts/activate        # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_call_outcomes
python manage.py createsuperuser
python manage.py runserver
```

Copy `.env.example` to `.env` (or set the equivalent environment variables)
to override `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`.

## Demo data

Generates a self-contained set of demo accounts and leads, clearly tagged
(`demo_` usernames, `[DEMO DATA]` remarks) so it never mixes with real
student records:

```bash
python manage.py seed_demo_data --leads 150
```

Demo accounts (password `DemoPass123!`): `demo_admin`, `demo_manager`,
`demo_caller1`-`demo_caller3`, `demo_counselor`.

## Scheduled maintenance

No Celery/Redis required. Run periodically via OS scheduler / cron:

```bash
python manage.py generate_followup_reminders
```

## Tests

```bash
python manage.py test tests
```

## Roles

Super Admin, College Admin, Telecalling Manager, Telecaller, Admission
Counselor — enforced via `apps.accounts.permissions` decorators/helpers and
Django Groups, with object-level checks restricting telecallers to their own
assigned leads.

## Apps

`accounts`, `dashboard`, `courses`, `leads`, `assignments`, `telecalling`,
`followups`, `admissions`, `reports`, `notifications`, `audit_logs` — each
under `apps/`, with templates under `templates/<app>/` and the shared
claymorphism design system under `static/css/` and `templates/components/`.
