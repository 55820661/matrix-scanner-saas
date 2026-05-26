# Phase 2.5 — Server Provisioning & Remote Bootstrap

## 1. الغرض من هذه المرحلة

هذه المرحلة تُضاف رسميًا إلى خطة مشروع **Matrix Scanner SaaS** بين:

```text
Phase 2 — Scanner Runtime
Phase 3 — Baseline Scan
```

الهدف منها هو إنشاء موديول داخل لوحة الأدمن يسمح لـ **Matrix Admin** بتثبيت وتشغيل **Scanner Runtime** على سيرفر العميل عن بُعد، ثم تشغيل الفحص التأسيسي والفحص الأمني المبدئي تلقائيًا.

---

## 2. الفصل المعماري بين منصة SaaS والـ Scanner Runtime

### 2.1 منصة SaaS

الأجزاء التالية تكون مستضافة مركزيًا على سيرفر Matrix Clouds / WhatsApp SaaS Server:

```text
Admin Interface
Client Portal
Public Website / Landing Page
API Backend
Telegram Bot Backend
Diagnostic Agent
Admin Tool Builder Agent
Tool Registry
Plans / Subscriptions / Payments
Incident Reports
Audit Logs
```

### 2.2 Scanner Runtime

على سيرفر العميل يتم تثبيت الكود الصغير فقط:

```text
Scanner Runtime
```

المسار الافتراضي المعتمد للتثبيت:

```text
/opt/matrix_scanner
```

ويتم إنشاء المسارات التالية داخله:

```text
/opt/matrix_scanner/.venv
/opt/matrix_scanner/config.yaml
/opt/matrix_scanner/data/
/opt/matrix_scanner/logs/
```

---

## 3. Server Provisioning & Remote Bootstrap Module

## 3.1 الهدف

من داخل Admin، يقوم Matrix Admin بإدخال بيانات وصول مؤقتة للسيرفر، ثم يقوم النظام بتثبيت Scanner Runtime تلقائيًا.

العملية تشمل:

```text
الاتصال بالسيرفر
اكتشاف نظام التشغيل والبيئة
اكتشاف Python والمكتبات المطلوبة
تثبيت المتطلبات الناقصة عند الحاجة
إنشاء مجلد /opt/matrix_scanner
تنزيل أو نسخ Scanner Runtime
كتابة config
تسجيل السيرفر في SaaS
إنشاء systemd service
تشغيل الـ agent
اختبار heartbeat
تشغيل Baseline Scan
تشغيل Security Preflight Scan
تخزين النتائج داخل حساب العميل
حذف بيانات الدخول المؤقتة
```

---

## 4. قواعد الأمان

Remote Bootstrap حساس لأنه يتعامل مع SSH/root access، لذلك تُعتمد القواعد التالية:

```text
1. الأفضل استخدام SSH key مؤقت بدل password.
2. لو تم استخدام password، لا يتم تخزينه نهائيًا بعد انتهاء التثبيت.
3. أي credential يتم تخزينه مؤقتًا فقط encrypted.
4. بعد نجاح التثبيت، يتم حذف بيانات الدخول من النظام.
5. كل خطوة تُسجل في Audit Log.
6. لا يتم تنفيذ أي أمر shell حر من الإيجنت.
7. الإيجنت الداخلي يوجه workflow فقط، ولا يخترع أوامر.
8. التنفيذ يتم من خلال Bootstrap Tools ثابتة ومعتمدة.
9. Remote Bootstrap في MVP خاص بـ Matrix Admin فقط.
10. العميل لا يستخدم Remote Bootstrap بنفسه في MVP.
```

---

## 5. آلية العمل المقترحة

### 5.1 إنشاء السيرفر من Admin

Matrix Admin يفتح:

```text
Admin → Servers → Add Server
```

ويختار:

```text
Install Scanner Remotely
```

ثم يدخل:

```text
Account / Customer
Server name
IP / hostname
SSH port
SSH user
Authentication method: password أو private key
Expected privilege: root أو sudo
```

---

### 5.2 إنشاء Bootstrap Session

النظام ينشئ جلسة تثبيت باسم:

```text
Bootstrap Session
```

حالات الجلسة:

```text
pending
connecting
probing
dependency_check
awaiting_confirmation
installing
registering
starting_agent
verifying_heartbeat
running_baseline
running_security_preflight
completed
failed
cancelled
```

---

### 5.3 فحص الاتصال بالسيرفر

أداة ثابتة:

```text
ssh_connectivity_check
```

تتحقق من:

```text
إمكانية الاتصال
صحة بيانات الدخول
نوع اليوزر
صلاحيات root أو sudo
نوع الـ shell
زمن الاستجابة
```

---

### 5.4 اكتشاف البيئة

أدوات ثابتة:

```text
remote_os_probe
package_manager_detector
python_runtime_detector
systemd_detector
panel_detector
```

تكتشف:

```text
OS
kernel
architecture
package manager: yum / dnf / apt
Python versions
systemd availability
cPanel presence
Apache/Nginx presence
```

---

### 5.5 تجهيز المتطلبات

أدوات ثابتة:

```text
dependency_plan_builder
package_install_checker
python_venv_checker
```

النظام لا يثبت أي شيء إلا بعد معرفة المطلوب.

في MVP يمكن السماح بتثبيت الحد الأدنى فقط:

```text
python3
python3-venv
pip
git أو curl عند الحاجة
```

قبل التثبيت، يظهر لـ Matrix Admin ملخص:

```text
سيتم تثبيت:
- python3
- python3-venv
- pip

هل توافق؟
```

---

### 5.6 تثبيت Scanner Runtime

أدوات ثابتة:

```text
scanner_directory_prepare
scanner_code_deploy
scanner_config_write
scanner_venv_create
scanner_dependencies_install
```

المسار المعتمد:

```text
/opt/matrix_scanner
```

---

### 5.7 تسجيل السيرفر في SaaS

أداة ثابتة:

```text
agent_register
```

تربط السيرفر بالمنصة من خلال:

```text
server_id
agent_id
registration_token
account_id
public key أو access token
```

بعد التسجيل، يتم إلغاء صلاحية registration token.

---

### 5.8 إنشاء systemd service

أداة ثابتة:

```text
systemd_service_install
```

تنشئ خدمة:

```text
matrix-scanner-agent.service
```

وظيفتها:

```text
تشغيل agent polling
إرسال heartbeat
استقبال jobs
تنفيذ tools
```

ثم يتم تشغيل:

```text
systemd_service_enable
systemd_service_start
agent_heartbeat_verify
```

---

### 5.9 تشغيل Baseline Scan

بعد نجاح heartbeat، يتم تشغيل:

```text
baseline_scan_launcher
```

ويشمل:

```text
system identity
services discovery
panel detection
cPanel domain discovery
application discovery
Laravel discovery
log sources discovery
git metadata
baseline findings
```

---

### 5.10 تشغيل Security Preflight Scan

قبل إنهاء الجلسة، يتم تشغيل:

```text
security_preflight_scan
```

ويبحث read-only عن:

```text
APP_DEBUG=true
Debugbar exposed
.env risk
.git under web paths
SQL dumps under public_html
suspicious cron entries
hidden suspicious directories
world-writable risky paths
recent 5xx if logs exist
```

ثم يتم تخزين findings داخل حساب العميل.

---

### 5.11 Cleanup

في نهاية العملية، يتم تشغيل:

```text
bootstrap_cleanup
```

ويشمل:

```text
حذف credentials المؤقتة
إلغاء registration token
إغلاق Bootstrap Session
حفظ Bootstrap Report
تسجيل كل النتائج في Audit Log
```

---

## 6. Bootstrap Tools الأساسية

يتم إضافة تصنيف جديد ضمن Core Tools:

```text
Bootstrap / Provisioning Tools
```

الأدوات المقترحة:

```text
1. ssh_connectivity_check
2. remote_os_probe
3. privilege_check
4. package_manager_detector
5. python_runtime_detector
6. systemd_detector
7. panel_detector
8. dependency_plan_builder
9. package_install_checker
10. bootstrap_directory_prepare
11. scanner_code_deploy
12. scanner_config_write
13. scanner_venv_create
14. scanner_dependencies_install
15. agent_register
16. systemd_service_install
17. systemd_service_enable
18. systemd_service_start
19. agent_heartbeat_verify
20. baseline_scan_launcher
21. security_preflight_scan
22. bootstrap_cleanup
23. bootstrap_failure_report
```

---

## 7. الفرق بين Bootstrap Tools وDiagnostic Tools

### 7.1 Bootstrap Tools

```text
تستخدم أثناء تثبيت Scanner Runtime فقط.
هدفها تجهيز السيرفر وتشغيل agent.
بعضها قد يثبت مكتبات أو يكتب ملفات.
لا تظهر للعميل العادي.
تستخدم فقط بواسطة Matrix Admin.
```

### 7.2 Diagnostic Tools

```text
تستخدم بعد التثبيت.
Read-only في MVP.
متاحة حسب الباقة.
يستخدمها Diagnostic Agent.
تظهر نتائجها في Portal وTelegram.
```

---

## 8. مستوى الخطورة

تُضاف فئة risk جديدة:

```text
bootstrap_action
```

وتكون مقيدة بالشروط التالية:

```text
Matrix Admin only
Requires explicit confirmation
Requires active bootstrap session
Allowed only before agent is active
Fully audited
No free shell
No customer access in MVP
```

---

## 9. دور الإيجنت الداخلي في التثبيت

الإيجنت الداخلي يوجه العملية كـ workflow، وليس كمنفذ أوامر.

مثال:

```text
تم الاتصال بالسيرفر بنجاح.
النظام CentOS 7.
Python 3 غير متاح بالمسار المطلوب.
مدير الحزم yum متاح.
الخطوة التالية المقترحة: تثبيت Python runtime المطلوب.
هل توافق؟
```

بعد الموافقة، يقوم النظام بتشغيل Tool ثابتة مثل:

```text
install_python_runtime
```

وليس shell حر.

---

## 10. البيانات التي يتم تخزينها بعد التثبيت

يتم تخزين:

```text
Server record
Agent ID
Agent status
Installed version
Install method: remote_bootstrap
Install timestamp
OS info
Panel type
Services
Domains
Applications pending review
Baseline findings
Security findings
Bootstrap log
```

ولا يتم تخزين:

```text
SSH password
Private key raw
Root credentials
Secrets from .env
```

---

## 11. Managed Install و Self Install

### 11.1 Managed Install

من Admin بواسطة Matrix Admin:

```text
نحن ندخل access مؤقت ونثبت Scanner Runtime للعميل.
```

هذه الطريقة تدخل في MVP.

### 11.2 Self Install

من Portal، العميل يأخذ أمر التثبيت ويشغله بنفسه:

```bash
curl -s https://scanner.matrixclouds.net/install.sh | bash -s -- --token=xxxx
```

يتم تجهيز التصميم لها من البداية، لكن يمكن تأجيل تفعيلها الكامل بعد MVP.

---

## 12. الجداول المقترحة لهذه المرحلة

### bootstrap_sessions

```text
id
account_id
server_id
created_by
status
target_host
ssh_port
ssh_user
auth_method
started_at
finished_at
failure_reason
created_at
updated_at
```

### bootstrap_steps

```text
id
bootstrap_session_id
step_name
tool_name
status
started_at
finished_at
summary
error_message
structured_output
created_at
updated_at
```

### bootstrap_credentials

> تخزين مؤقت ومشفر فقط، ويتم حذفه بعد انتهاء الجلسة.

```text
id
bootstrap_session_id
credential_type
encrypted_payload
expires_at
destroyed_at
created_at
```

### agent_installations

```text
id
server_id
agent_id
install_method
install_path
agent_version
service_name
status
installed_at
last_verified_at
created_at
updated_at
```

---

## 13. القرار المعتمد

تم اعتماد الآتي:

```text
1. Admin / Portal / Public Website مستضافون على سيرفر Matrix Clouds / WhatsApp SaaS.
2. Scanner Runtime فقط يثبت على سيرفر العميل.
3. إضافة Phase 2.5 باسم Server Provisioning & Remote Bootstrap.
4. وجود موديول في Admin لتثبيت Scanner Runtime على سيرفر العميل عن بعد.
5. التثبيت يتم عبر Bootstrap Tools ثابتة، وليس shell حر.
6. الإيجنت الداخلي يوجه عملية التثبيت خطوة بخطوة.
7. Credentials تستخدم مؤقتًا فقط ولا تحفظ بعد التثبيت.
8. المسار الافتراضي للتثبيت هو /opt/matrix_scanner.
9. بعد التثبيت يتم تشغيل Baseline Scan تلقائيًا.
10. قبل إنهاء الجلسة يتم تشغيل Security Preflight Scan.
11. Remote Bootstrap في MVP خاص بـ Matrix Admin فقط.
12. Self Install للعميل يكون مجهزًا تصميميًا من البداية، ويمكن تفعيله لاحقًا.
```

---

## 14. الخلاصة

هذه المرحلة تجعل onboarding احترافيًا ومناسبًا للعملاء الذين لا يعرفون تثبيت أدوات على السيرفر.

القيمة الأساسية:

```text
Matrix Admin يستطيع من لوحة الأدمن تثبيت Scanner Runtime على سيرفر العميل،
تشغيله،
تسجيله،
تشغيل Baseline Scan،
واستخراج Security Findings،
دون تنفيذ أوامر حرة أو تخزين بيانات وصول دائمة.
```

هذه المرحلة تُعد جزءًا مهمًا من الـ MVP لأنها تجعل تسجيل السيرفر وتشغيل الفحص الأولي عملية منظمة وقابلة للتكرار.
