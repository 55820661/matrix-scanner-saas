# Deployment Notes

Deployment is not part of Sprint 1, but the project should be structured with production deployment in mind.

Expected services later:
- `scanner-platform-web.service`
- `scanner-platform-celery.service`
- `scanner-platform-celerybeat.service` when scheduled jobs are introduced
- PostgreSQL
- Redis
- Nginx
- Gunicorn

Required production controls:
- `DEBUG=false`
- Environment variables for secrets.
- HTTPS.
- Database backups.
- Log rotation.
- Separate logs for web, Celery, bootstrap, and agent API events.
- Error monitoring.

Do not commit real environment files or secrets.
