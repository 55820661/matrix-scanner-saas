# Matrix Scanner SaaS

Matrix Scanner SaaS is a Django-based platform for read-only diagnostics of customer servers, initially focused on cPanel/WHM, Laravel, Apache/EasyApache, PHP, MySQL/MariaDB, and traditional `public_html` production environments.

The current repository state is planning and scaffolding. Implementation should follow:

- [PLANS.md](PLANS.md)
- [docs/DECISIONS.md](docs/DECISIONS.md)
- [docs/PROJECT-STRUCTURE.md](docs/PROJECT-STRUCTURE.md)
- [docs/SECURITY-MODEL.md](docs/SECURITY-MODEL.md)
- [docs/IMPLEMENTATION-CHECKLIST.md](docs/IMPLEMENTATION-CHECKLIST.md)

## MVP Rule

Read-only first. No free shell commands, no remediation, no file edits, no service restarts, and no secrets in storage, reports, AI prompts, or Telegram.
