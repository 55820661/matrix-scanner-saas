# Matrix Scanner SaaS MVP Plan

## 1. تعريف المشروع

**Matrix Scanner SaaS** هو منصة SaaS لتشخيص ومراقبة السيرفرات والتطبيقات، موجهة في نسختها الأولى إلى السيرفرات التقليدية التي تديرها شركات البرمجيات أو الأفراد، خصوصًا بيئات:

- cPanel / WHM
- Laravel applications
- Apache / EasyApache
- PHP / MySQL
- public_html structure
- Apache domlogs
- Laravel logs
- Git-based deployments
- Supervisor / Queue workers عند وجودها

المنتج لا يبدأ كمجرد أداة CLI، بل كمنصة SaaS من أول يوم، تحتوي على حسابات عملاء، مستخدمين، سيرفرات، تطبيقات، باقات، اشتراكات، أدوات تشخيص، جلسات تشخيص، تقارير، وتنبيهات.

---

## 2. الفكرة الأساسية

الفكرة تعتمد على ثلاث طبقات رئيسية:

```text
1. SaaS Platform
   لإدارة الحسابات، المستخدمين، السيرفرات، التطبيقات، الباقات، الاشتراكات، التقارير، والصلاحيات.

2. Scanner Runtime
   برنامج صغير وآمن يتم تثبيته على سيرفر العميل، ويعمل كـ systemd service، وينفذ أدوات محددة فقط.

3. Diagnostic Agent
   مساعد تشخيص خارجي يختار أدوات الفحص المناسبة، يحلل النتائج، يرسل ملاحظات للمستخدم، ويصدر تقريرًا مختصرًا.
```

المبدأ الأساسي:

```text
Agent يفكر ويقترح.
Scanner Runtime ينفذ فقط أدوات معتمدة.
Policy Engine يمنع أي تنفيذ غير آمن.
المستخدم يرى ملاحظات واضحة وتقريرًا نهائيًا.
```

---

## 3. القرارات المعتمدة

### 3.1 SaaS من أول يوم

تم اعتماد أن المنتج يبدأ كـ SaaS وليس كأداة داخلية ثم يتم تحويلها لاحقًا.

هذا يعني أن الهيكل يجب أن يحتوي من البداية على:

```text
Accounts
Users
Roles
Servers
Applications
Plans
Subscriptions
Payments
Usage Tracking
Audit Logs
```

---

### 3.2 العملاء المستهدفون

النسخة الأولى تستهدف:

```text
شركات أو أفراد لديهم سيرفر أو أكثر.
```

نوعية السيرفرات الأولى:

```text
cPanel / WHM
Laravel
Apache
PHP / MySQL
public_html
سيرفرات production تقليدية
```

---

### 3.3 الأدوار

الأدوار المعتمدة في MVP:

```text
Owner
Operator
Viewer
```

#### Owner

يمتلك الحساب ويدير السيرفرات والمستخدمين والاشتراك، ويملك الصلاحيات الأعلى.

#### Operator

يشغل جلسات التشخيص ويقرأ النتائج، ضمن حدود الصلاحيات المعتمدة.

#### Viewer

يشاهد التقارير والتنبيهات فقط.

---

### 3.4 التطبيقات

التطبيقات لا تُضاف يدويًا فقط، بل يتم اكتشافها تلقائيًا من خلال Baseline Scan.

بعد الاكتشاف تدخل التطبيقات بحالة:

```text
Pending Review
```

ثم يقوم المستخدم أو الـ Owner بمراجعتها وتسميتها واعتمادها.

---

### 3.5 MVP Read-only

أول نسخة تكون Read-only فقط.

ممنوع في MVP:

```text
تعديل ملفات
إعادة تشغيل خدمات
حذف ملفات
تغيير صلاحيات
block IP
git pull
composer install/update
patch code
تعديل .env
```

---

## 4. هيكل SaaS الأساسي

### 4.1 Account

يمثل العميل، سواء شركة أو فرد.

الحقول المقترحة:

```text
id
name
type: company / individual
status
current_subscription_id
created_at
updated_at
```

---

### 4.2 Users

كل Account يمكن أن يحتوي على أكثر من مستخدم.

الحقول المقترحة:

```text
id
account_id
name
email
password
role: owner / operator / viewer
telegram_id
status
created_at
updated_at
```

---

### 4.3 Servers

كل Server يتبع Account واحد فقط.

الحقول المقترحة:

```text
id
account_id
name
hostname
public_ip
os
kernel
panel_type
agent_status
last_seen_at
created_at
updated_at
```

---

### 4.4 Applications

كل Application يتبع Server واحد.

الحقول المقترحة:

```text
id
account_id
server_id
domain_id
name
domain
path
framework
framework_version
php_version
environment
debug_enabled
review_status
status
created_at
updated_at
```

---

### 4.5 Audit Logs

Audit Log إلزامي من أول نسخة.

يسجل:

```text
من نفذ؟
ماذا نفذ؟
على أي حساب؟
على أي سيرفر؟
على أي تطبيق؟
متى؟
ما النتيجة؟
```

---

## 5. Scanner Runtime

### 5.1 الهدف

Scanner Runtime هو برنامج صغير يتم تثبيته على سيرفر العميل.

وظائفه:

```text
تسجيل السيرفر في المنصة.
إرسال heartbeat دوري.
استقبال jobs من المنصة بطريقة polling.
تنفيذ أدوات محددة فقط.
إرجاع النتائج structured JSON.
رفض أي أداة أو معامل غير مسموح.
```

---

### 5.2 طريقة الاتصال

تم اعتماد أن الاتصال في MVP يكون:

```text
Polling من السيرفر إلى SaaS
```

وليس من SaaS إلى السيرفر.

السبب:

```text
لا يحتاج فتح ports.
يعمل خلف firewall.
أنسب لسيرفرات cPanel/WHM.
أبسط أمنيًا في البداية.
```

---

### 5.3 التشغيل

Runtime يكون في البداية:

```text
Python package
systemd service
```

مثال:

```text
matrix-scanner-agent.service
```

---

### 5.4 Job Model

كل تنفيذ يتم كـ Job من المنصة.

حالات الـ Job:

```text
pending
running
succeeded
failed
rejected_by_policy
timeout
```

---

## 6. Baseline Scan

### 6.1 الهدف

عند تسجيل السيرفر لأول مرة، يتم تشغيل فحص تأسيسي تلقائي يبني بصمة تشغيلية للسيرفر.

هذه البصمة تصبح مرجعًا لكل التشخيصات اللاحقة.

---

### 6.2 أدوات Baseline الأساسية

```text
system_identity
panel_detector
services_scanner
web_server_scanner
cpanel_domain_scanner
application_discovery
log_sources_discovery
security_baseline
git_metadata_scanner
```

---

### 6.3 المعلومات التي يتم جمعها

#### System Identity

```text
hostname
public IP
OS
kernel
timezone
uptime
CPU count
RAM
disk layout
```

#### Panel Detection

```text
cPanel / WHM
Plain Linux
Plesk لاحقًا
Forge لاحقًا
Docker لاحقًا
```

#### Services Discovery

```text
httpd
nginx
mysql / mariadb
php-fpm
supervisord
redis
crond
exim
dovecot
docker
pm2
```

#### cPanel Domain Discovery

من:

```text
/var/cpanel/userdata/*
```

يتم اكتشاف:

```text
cPanel user
main domains
addon domains
subdomains
document roots
PHP version per domain
SSL aliases
IP binding
```

#### Application Discovery

في MVP يتم التركيز على:

```text
Laravel
WordPress
Static/Unknown
```

Laravel يكتشف من وجود:

```text
artisan
composer.json
.env
bootstrap/
storage/
routes/
```

#### Laravel Baseline

```text
Laravel version
APP_ENV
APP_DEBUG
DEBUGBAR_ENABLED
LOG_CHANNEL
LOG_LEVEL
QUEUE_CONNECTION
CACHE_DRIVER
SESSION_DRIVER
storage/logs path
```

مع منع عرض الأسرار.

---

### 6.4 Baseline Findings

يتم إنشاء Findings بدرجات:

```text
Info
Medium
High
Critical
```

أمثلة:

```text
CRITICAL: APP_DEBUG=true
HIGH: Debugbar exposed
HIGH: Laravel document root points to project root instead of /public
MEDIUM: SQL dump files under web path
INFO: Git working tree dirty
```

---

## 7. Tool Registry / التطوير الجاف

### 7.1 المفهوم

التطوير الجاف يعني:

```text
الكود الأساسي ثابت.
الأدوات ديناميكية.
تعريفات الأدوات محفوظة في قاعدة البيانات.
التنفيذ يتم عبر Tool Templates آمنة.
```

---

### 7.2 Core Tools

أدوات تأتي مع النظام من البداية، لكنها أيضًا مسجلة في Tool Registry.

أمثلة:

```text
system_identity
services_status
cpanel_domain_scanner
laravel_env_reader
apache_access_summary
laravel_exception_summary
http_response_checker
git_metadata_reader
```

---

### 7.3 Custom Tools

أدوات يتم إضافتها لاحقًا من لوحة الأدمن عبر Admin Tool Builder Agent.

أمثلة:

```text
debugbar_exposure_check
laravel_5xx_correlation
bot_scan_detector
sql_dump_under_webroot_check
custom_log_pattern_detector
```

---

### 7.4 Tool Template vs Tool Definition

#### Tool Template

قالب تنفيذي آمن موجود في الكود.

مثال:

```text
apache_log_analyzer
```

#### Tool Definition

تعريف أداة محفوظ في قاعدة البيانات ويستخدم Template معين.

مثال:

```text
Apache 5xx Summary Last 6 Hours
```

---

### 7.5 قواعد Tool Registry

```text
لا توجد أدوات shell حرة.
كل Custom Tool يجب أن يستخدم Tool Template معروف.
كل Tool لها version.
كل Tool لها lifecycle.
كل Tool Run يسجل في Audit Log.
كل output يمر من secret redaction.
```

---

## 8. Policy Engine

### 8.1 الهدف

Policy Engine هو طبقة الحماية التي تمنع أي تنفيذ غير آمن.

---

### 8.2 أنواع السياسات

#### Tool Risk Policy

```text
read_only
low_risk_action
sensitive_action
forbidden
```

في MVP يستخدم فقط:

```text
read_only
```

#### Path Policy

المسارات لا تُقبل إلا إذا كانت:

```text
مكتشفة في baseline
أو ضمن allowed paths
```

#### Parameter Policy

كل parameter يكون typed ومحدود.

أمثلة:

```text
domain: valid hostname
since_hours: 1 إلى 168
status_filter: 4xx / 5xx / all
```

ممنوع:

```text
command
shell
script
raw_query
```

#### Output Redaction

يتم حجب الأسرار مثل:

```text
APP_KEY
DB_PASSWORD
MAIL_PASSWORD
API_KEY
TOKEN
SECRET
PRIVATE KEY
Authorization
Bearer
```

وتستبدل بـ:

```text
[REDACTED]
```

#### Tenant Isolation

مستخدم من Account معين لا يرى ولا يشغل أدوات على سيرفر أو تطبيق تابع لحساب آخر.

---

## 9. Diagnostic Agent الخارجي

### 9.1 الدور

Diagnostic Agent هو العقل التشخيصي.

وظائفه:

```text
يفهم طلب المستخدم.
يحدد السيرفر والتطبيق والفترة.
يقرأ baseline.
يرى الأدوات المسموحة.
يختار الخطوة التالية.
يحلل نتيجة كل أداة.
يعطي note قصيرة للمستخدم.
ينتج تقريرًا نهائيًا.
```

---

### 9.2 السيناريوهات في MVP

```text
slowness
500 errors
security scan
Laravel production audit
```

---

### 9.3 حدود الإيجنت

```text
لا ينفذ أوامر مباشرة.
لا يخترع أدوات.
لا يرى أدوات غير مسموحة.
لا يرى أسرار.
لا يتجاوز policy.
لا يعمل remediation في MVP.
```

---

### 9.4 الحد الأقصى للجلسة

مبدئيًا:

```text
10 tool runs لكل diagnostic session
```

---

## 10. Telegram Bot / Guided Workflow

### 10.1 الدور

Telegram هو واجهة التشغيل الأولى في MVP بجانب Dashboard بسيط.

---

### 10.2 Private Chat

يستخدم لـ:

```text
بدء جلسات التشخيص
عرض الملاحظات
الموافقات
التقرير النهائي
```

---

### 10.3 Groups

تستخدم في MVP لـ:

```text
alerts
summary reports
team visibility
```

ولا تستخدم في البداية للموافقات الحساسة أو التفاصيل الطويلة.

---

### 10.4 Approval

في MVP:

```text
read-only tools تكون auto-approved داخل الجلسة بعد موافقة بداية الجلسة.
```

لاحقًا يمكن تفعيل:

```text
manual approval لكل خطوة
```

---

## 11. Admin Tool Builder Agent

### 11.1 الهدف

مساعد داخلي في لوحة الأدمن يساعد Matrix Admin على إنشاء Tool Definitions جديدة بدون تعديل الكود.

---

### 11.2 حدود الدور

```text
لا ينفذ أدوات.
لا يكتب shell commands.
لا يفعّل الأدوات مباشرة.
لا يرى أسرار العملاء.
```

---

### 11.3 Lifecycle للأدوات

```text
Draft
Pending Review
Approved
Enabled
Disabled
Deprecated
```

الأداة لا تظهر للإيجنت الخارجي إلا إذا كانت:

```text
Approved + Enabled
```

---

### 11.4 صلاحيات MVP

في MVP:

```text
Matrix Admin فقط ينشئ ويعتمد الأدوات.
العملاء لا ينشئون أدوات.
```

---

## 12. Incident Reports & Knowledge Base

### 12.1 الهدف

كل Diagnostic Session ينتج Incident Report محفوظ.

---

### 12.2 ما يتم حفظه

```text
Session metadata
Timeline
Tool runs
Agent notes
Findings
Final summary
Developer notes عند الحاجة
```

---

### 12.3 Findings

كل Finding له:

```text
severity
category
status: open / acknowledged / resolved / ignored
first_seen_at
last_seen_at
source_tool
affected_server
affected_application
```

---

### 12.4 Alerts

قاعدة مهمة:

```text
لا يتم إرسال alert إلا إذا كان finding جديدًا أو active حديثًا.
```

الأخطاء القديمة تظهر في التقارير فقط.

---

## 13. Dynamic Plans / Subscriptions / Payments

### 13.1 القرار

لا توجد باقات ثابتة في الكود.

الأدمن ينشئ الباقات من لوحة التحكم ويحدد:

```text
السعر
العملة
دورة الدفع
عدد السيرفرات
عدد التطبيقات
عدد المستخدمين
عدد جلسات التشخيص
مدة حفظ التقارير
الميزات
الأدوات المتاحة
```

---

### 13.2 Plans Module

يمثل تعريف الباقة.

حقول مقترحة:

```text
id
name
description
price
currency
billing_cycle
max_servers
max_applications
max_users
max_diagnostic_sessions_per_month
retention_days
is_active
created_at
updated_at
```

---

### 13.3 Plan Features

```text
plan_id
feature_key
enabled
value
```

أمثلة:

```text
telegram_group_alerts_enabled
technical_reports_enabled
custom_tools_enabled
diagnostic_agent_enabled
```

---

### 13.4 Plan Tools

```text
plan_id
tool_id
enabled
monthly_limit optional
```

---

### 13.5 Subscriptions Module

يربط Account بباقة معينة.

حقول مقترحة:

```text
account_id
plan_id
status
start_date
end_date
current_period_start
current_period_end
trial_ends_at
auto_renew
cancelled_at
```

---

### 13.6 Payments Module

منفصل عن الاشتراكات.

في MVP يمكن أن يكون الدفع:

```text
manual / offline
```

ثم لاحقًا يتم دعم بوابات دفع.

---

### 13.7 Usage Tracking

يدخل من البداية.

يتتبع:

```text
servers_count
applications_count
users_count
diagnostic_sessions_used
tool_runs_used
alerts_sent
reports_generated
```

---

## 14. Low-risk Actions

ليست ضمن MVP الأول.

أمثلة مستقبلية:

```text
php artisan optimize:clear
clear cache
rotate huge logs
test endpoint
disable debugbar after approval
```

شروطها المستقبلية:

```text
backup
approval
audit log
rollback note
verification
```

---

## 15. Advanced / Sensitive Actions

ليست ضمن MVP.

أمثلة:

```text
restart service
block IP
edit .env
move SQL files
fix permissions
patch code
```

لا تُدرس إلا بعد ثبات النظام ونجاح read-only MVP.

---

## 16. MVP Scope

### يدخل في MVP

```text
SaaS accounts
Users and roles
Dynamic plans structure
Subscriptions structure
Usage tracking
Server registration
Python Scanner Runtime
Polling jobs
Baseline Scan
Application auto-discovery
Core Tool Registry
Policy Engine
Read-only tools
Diagnostic Agent
Telegram guided workflow
Incident Reports
Audit Logs
Admin Tool Builder Agent بشكل محدود
```

---

### لا يدخل في MVP

```text
تعديل ملفات
إعادة تشغيل خدمات
block IP
patch code
advanced remediation
full payment gateway
Enterprise features
custom customer-built tools
sensitive actions
```

---

## 17. أول Core Tool Templates

الاقتراح الأولي:

```text
system_info_reader
service_status_reader
cpanel_domain_reader
laravel_env_reader
apache_log_analyzer
laravel_log_analyzer
http_response_checker
file_presence_checker
git_metadata_reader
webroot_risk_checker
```

---

## 18. أول Secondary Tools

عدد محدود في MVP:

```text
debugbar_exposure_check
laravel_5xx_correlation
sql_dump_under_webroot_check
bot_scan_detector
```

---

## 19. التسلسل التشغيلي الكامل

```text
1. العميل ينشئ Account.
2. Owner يضيف Server.
3. النظام يعطيه install command.
4. Scanner Runtime يتثبت ويسجل السيرفر.
5. Baseline Scan يعمل تلقائيًا.
6. يتم اكتشاف الدومينات والتطبيقات والخدمات.
7. التطبيقات تدخل Pending Review.
8. المستخدم يعتمد التطبيقات المهمة.
9. يبدأ Diagnostic Session من Telegram أو Dashboard.
10. Diagnostic Agent يختار الأدوات المناسبة.
11. Scanner Runtime ينفذ tools read-only.
12. النتائج ترجع structured JSON.
13. الإيجنت يعطي notes بعد كل خطوة.
14. في النهاية يصدر Incident Report مختصر.
15. Findings تحفظ وتدخل Knowledge Base.
```

---

## 20. القرارات التقنية التي تحتاج نقاش لاحق

```text
1. هل SaaS Platform يبنى بـ Laravel أم Django؟
2. شكل قاعدة البيانات النهائي.
3. طريقة تثبيت Scanner Runtime.
4. طريقة توقيع الاتصال بين Runtime والمنصة.
5. AI provider: OpenAI فقط أم configurable؟
6. استضافة منصة SaaS نفسها.
7. شكل Dashboard الأولي.
8. شكل Telegram linking flow.
9. شكل Prompt Compiler للإيجنت الخارجي.
10. طريقة إدارة الأسرار والتوكنات.
```

---

## 21. الخلاصة

Matrix Scanner SaaS ليس مجرد أداة فحص، بل منصة تشخيص موجهة تعتمد على:

```text
SaaS Core
Scanner Runtime
Baseline Scan
Dynamic Tool Registry
Policy Engine
Diagnostic Agent
Telegram Workflow
Incident Reports
Usage-based Plans
```

القيمة الأساسية للمنتج:

```text
تشخيص عملي وسريع وآمن لسيرفرات cPanel/Laravel/Apache التقليدية.
```

التميّز:

```text
ليس منافسًا مباشرًا لـ Datadog أو New Relic.
بل منتج متخصص في واقع السيرفرات التي تديرها شركات البرمجيات الصغيرة والمتوسطة.
```

أول نسخة يجب أن تكون:

```text
Read-only
آمنة
محدودة الأدوات
لكن مبنية من البداية كـ SaaS قابل للتوسع.
```
