# Matrix Scanner SaaS Diagnostics Skill

## Purpose
Use this skill when implementing read-only scanners for Linux, cPanel/WHM, Apache/EasyApache, PHP/PHP-FPM, MySQL/MariaDB, Laravel, WordPress classification, and log sources.

## General Scanner Rules
- Scanners collect facts only. They do not send alerts, write reports, or execute fixes.
- Scanner output should be structured JSON suitable for AgentJob results, ToolRun storage, BaselineScan processing, and findings.
- Each scanner should identify:
  - status.
  - evidence.
  - warnings.
  - permission or availability limitations.
- A scanner failure should become a partial result, not a process crash.
- Scanner output must pass secret redaction before storage or display.
- Scanner output must pass secret redaction before AI prompts or Telegram delivery.
- Do not expose raw `.env` values; read only explicit safe keys.
- Baseline Scan implementation starts after the Tool Registry and Policy Engine foundation.

## System Health
Collect:
- CPU percentage.
- RAM usage.
- disk usage.
- load average.
- uptime.
- swap usage.

Prefer Python libraries such as `psutil` once dependencies are introduced.

## Services
Check configured services:
- httpd/apache.
- nginx where present.
- php-fpm.
- mysql/mariadb.
- redis, crond, supervisor, exim, dovecot, docker, and pm2 when present.
- additional config-defined services.

Use read-only status checks. Do not restart, reload, enable, disable, or modify services.

## cPanel and Domains
Read cPanel metadata from known read-only paths such as `/var/cpanel/userdata/*` when accessible.

Collect:
- cPanel user.
- main domains, addon domains, and subdomains.
- document roots.
- PHP version per domain when available.
- SSL aliases and IP binding when available.

Do not change cPanel data, Apache configuration, DNS, SSL, or user files.

## Apache and Nginx Logs
Read configured log paths:
- access log.
- error log.

Summarize:
- recent errors.
- common status codes.
- spikes in 499, 500, 502, and 504.
- frequent failing endpoints.

Avoid returning large raw log blocks.

## PHP-FPM
Collect when available:
- service status.
- pool config values such as `pm.max_children`.
- process counts.
- memory usage.
- signs of `max_children` pressure.

Do not edit pool config.

## MySQL
Read-only checks only:
- service status.
- `max_connections`.
- `Threads_running`.
- `Slow_queries`.
- `innodb_buffer_pool_size`.
- processlist summary.

Do not change schema, indexes, variables, or logs in MVP.

## Laravel
Inspect configured Laravel project path:
- `storage/logs/laravel.log`.
- safe `.env` keys needed for diagnostics only, such as `APP_ENV`, `APP_DEBUG`, `LOG_CHANNEL`, `LOG_LEVEL`, `QUEUE_CONNECTION`, `CACHE_DRIVER`, and `SESSION_DRIVER`.
- queue and scheduler indicators when safely available.
- failed jobs if accessible.

Never expose full `.env` contents.
Never store full `.env` contents.

## Application Discovery
Classify applications conservatively:
- Laravel when `artisan`, `composer.json`, `bootstrap/`, `storage/`, and `routes/` signals match.
- WordPress when standard WordPress files are present.
- Static/Unknown when signals are incomplete.

All discovered applications should enter Pending Review before being treated as approved customer assets.
