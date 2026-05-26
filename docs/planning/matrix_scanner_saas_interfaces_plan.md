# Matrix Scanner SaaS — Application Interfaces Plan

## 1. مقدمة

يعتمد مشروع **Matrix Scanner SaaS** على ثلاث واجهات رئيسية:

```text
Admin = إدارة المنصة نفسها من Matrix Clouds
Portal = واجهة العميل لإدارة حسابه وسيرفراته وتطبيقاته
Chat / Telegram = واجهة التشغيل السريعة للتشخيص والتنبيهات
```

كل واجهة لها وظيفة واضحة، مع مشاركة نفس الـ backend، ونفس نظام الصلاحيات، ونفس Audit Log.

---

# 2. Admin Interface — لوحة إدارة Matrix Scanner

هذه الواجهة خاصة بـ **Matrix Admin** فقط، وليست للعميل.

## 2.1 إدارة الحسابات / العملاء

الوظائف:

```text
عرض كل الحسابات
إنشاء حساب جديد
تعطيل / تفعيل حساب
تغيير الخطة
عرض حالة الاشتراك
عرض الاستخدام
```

مثال:

```text
Account: ABC Company
Plan: Pro
Servers: 3 / 5
Applications: 14 / 20
Status: Active
```

---

## 2.2 إدارة المستخدمين

الوظائف:

```text
عرض مستخدمي كل حساب
إضافة Owner
تغيير دور مستخدم
تعطيل مستخدم
فك / إعادة ربط Telegram ID
```

الأدوار:

```text
Owner
Operator
Viewer
Matrix Admin
```

---

## 2.3 إدارة السيرفرات

الوظائف:

```text
عرض جميع السيرفرات المسجلة
حالة كل agent
آخر heartbeat
آخر baseline scan
نوع السيرفر
عدد التطبيقات المكتشفة
عدد findings المفتوحة
```

مثال:

```text
Server: Matrix Clouds Production
Agent: Online
Panel: cPanel
Apps: 26
Critical Findings: 2
Last Seen: 1 min ago
```

---

## 2.4 إدارة التطبيقات المكتشفة

الوظائف:

```text
عرض كل التطبيقات المكتشفة عبر baseline
فلترة Laravel / WordPress / Unknown
عرض التطبيقات Pending Review
تعديل التصنيف لو الاكتشاف غير دقيق
ربط التطبيق بحساب/سيرفر
```

ملاحظة: اعتماد التطبيق النهائي يفضل أن يكون في Portal للعميل، إلا إذا كان Matrix Admin يدير الحساب نيابة عنه.

---

## 2.5 إدارة الباقات Dynamic Plans

هذه واجهة أساسية بناءً على قرار جعل الباقات ديناميكية.

الوظائف:

```text
إنشاء باقة
تحديد السعر
تحديد عدد السيرفرات
تحديد عدد التطبيقات
تحديد عدد المستخدمين
تحديد عدد جلسات التشخيص
تحديد مدة retention
تحديد الأدوات المتاحة داخل الباقة
تفعيل / تعطيل الباقة
```

مثال:

```text
Plan: Pro
Price: 99 USD/month
Servers: 5
Apps: 20
Tools: Core + Laravel Advanced
Telegram Groups: Enabled
```

---

## 2.6 إدارة الاشتراكات

الوظائف:

```text
إنشاء اشتراك لحساب
تغيير خطة الحساب
تجديد الاشتراك
إيقاف الاشتراك
تحديد فترة تجريبية
تعديل current period
عرض حالة الدفع
```

حالات الاشتراك:

```text
trial
active
past_due
suspended
cancelled
expired
```

---

## 2.7 إدارة المدفوعات

في MVP، الدفع يمكن أن يكون manual/offline.

الوظائف:

```text
تسجيل دفعة يدوية
إصدار رقم فاتورة
تحديد طريقة الدفع
ربط الدفعة باشتراك
عرض سجل المدفوعات
```

لاحقًا يمكن إضافة payment gateway.

---

## 2.8 Tool Registry

هذه من أهم واجهات الأدمن.

الوظائف:

```text
عرض Core Tools
عرض Custom Tools
إنشاء Tool Definition
تعديل Tool Definition
تفعيل / تعطيل Tool
عرض version history
ربط tool بالباقات
ربط tool بأنواع سيرفرات أو تطبيقات
```

---

## 2.9 Admin Tool Builder Agent

واجهة داخل الأدمن تساعد Matrix Admin على إنشاء أدوات جديدة.

مثال طلب:

```text
عايز أداة تفحص هل Debugbar مكشوف على Laravel app
```

الإيجنت يقترح:

```text
Tool Template: http_response_checker
Params: domain + fixed path
Risk: read_only
Expected safe: 404/403
Critical: 200
```

في MVP:

```text
Matrix Admin فقط يستخدمها
الأداة تبدأ Draft / Pending Review
لا تتفعل تلقائيًا
```

---

## 2.10 Policy Management

الوظائف:

```text
إدارة allowed paths العامة
إدارة blocked paths
إدارة max runtime
إدارة max output size
إدارة secret redaction patterns
إدارة risk levels
```

في MVP، لا نحتاج واجهة متقدمة جدًا، لكن نحتاج صفحة عرض وتعديل محدود.

---

## 2.11 Incident Reports العامة

الوظائف:

```text
عرض كل incidents عبر كل العملاء
فلترة حسب severity
فلترة حسب account/server/app
عرض آخر findings
عرض الجلسات الفاشلة
عرض tool runs المرفوضة بالـ policy
```

هذه الواجهة مهمة للدعم الداخلي.

---

## 2.12 Audit Logs

واجهة Audit Logs إلزامية من البداية.

تسجل:

```text
كل login
كل server added
كل baseline scan
كل tool run
كل agent decision
كل approval
كل policy rejection
كل plan/subscription/payment change
```

---

# 3. Portal Interface — بوابة العميل

هذه واجهة العميل نفسه، وتشمل أدوار:

```text
Owner
Operator
Viewer
```

---

## 3.1 Dashboard رئيسي

يعرض ملخص الحساب:

```text
عدد السيرفرات
عدد التطبيقات
حالة Agents
Critical Findings
آخر Incidents
استهلاك الباقة
آخر تنبيهات
```

مثال:

```text
Servers: 3 / 5
Applications: 14 / 20
Open Critical Findings: 2
Diagnostic Sessions Used: 18 / 50
Agent Offline: 0
```

---

## 3.2 Servers

العميل يقدر:

```text
إضافة سيرفر جديد
مشاهدة أمر التثبيت
عرض حالة السيرفر
عرض آخر heartbeat
إعادة تشغيل baseline scan يدويًا
عرض baseline summary
عرض الخدمات المكتشفة
```

صفحة السيرفر تعرض:

```text
OS
Panel type
CPU/RAM/Disk
Services
Domains
Applications
Log sources
Findings
```

---

## 3.3 Add Server Flow

الخطوات:

```text
1. اسم السيرفر
2. اختيار نوعه لو معروف أو Auto-detect
3. توليد install command
4. انتظار agent registration
5. تشغيل baseline scan
6. عرض النتائج
```

---

## 3.4 Applications

التطبيقات المكتشفة تظهر في Portal.

الحالات:

```text
Pending Review
Approved
Ignored
Archived
```

العميل يراجع:

```text
اسم التطبيق
الدومين
المسار
نوع التطبيق
Laravel version
PHP version
APP_ENV
APP_DEBUG
Log sources
```

ويقرر:

```text
Approve
Rename
Ignore
Archive
```

---

## 3.5 Baseline Findings

صفحة تعرض كل findings المكتشفة:

```text
Critical
High
Medium
Info
```

مع status:

```text
open
acknowledged
resolved
ignored
```

مثال:

```text
CRITICAL: APP_DEBUG=true on Mazadat
HIGH: SQL dump files under web path
MEDIUM: Bot scan detected
```

---

## 3.6 Diagnostic Sessions

العميل يقدر يبدأ جلسة تشخيص من Portal.

الاختيارات الأولى:

```text
Slowness
500 Error
Security Scan
Laravel Production Audit
Custom Question
```

بعدها يختار:

```text
Server
Application
Time window
```

ثم يبدأ Agent.

---

## 3.7 Incident Reports

عرض التقارير السابقة:

```text
التاريخ
السيرفر
التطبيق
نوع المشكلة
السبب المرجح
الحالة
```

داخل التقرير:

```text
Executive Summary
Timeline
Tools executed
Findings
Recommendations
Technical details
```

في MVP، يمكن عرض تقرير مختصر فقط مع حفظ التفاصيل.

---

## 3.8 Tool Runs History

يمكن أن تكون داخل التقرير أو صفحة منفصلة.

تعرض:

```text
الأداة
الوقت
المستخدم
النتيجة
status
مدة التنفيذ
هل حصل policy rejection
```

---

## 3.9 Telegram Settings

العميل يربط Telegram.

الوظائف:

```text
ربط مستخدم Telegram
ربط Group للتنبيهات
اختيار أنواع التنبيهات
اختيار هل read-only sessions auto-approved
```

في MVP:

```text
Private chat للتشخيص
Group للتنبيهات والملخصات فقط
```

---

## 3.10 Users & Roles

Owner فقط يقدر:

```text
دعوة مستخدم
تغيير role
تعطيل مستخدم
عرض آخر نشاط
```

الأدوار:

```text
Owner
Operator
Viewer
```

---

## 3.11 Subscription & Usage

العميل يرى:

```text
الباقة الحالية
تاريخ البداية والنهاية
عدد السيرفرات المستخدمة
عدد التطبيقات المستخدمة
عدد جلسات التشخيص المستخدمة
مدة الاحتفاظ بالتقارير
```

في MVP لا نحتاج دفع إلكتروني، لكن نعرض حالة الاشتراك.

---

# 4. Chat Interface — Telegram

هذه واجهة التشغيل السريعة، وليست بديلًا كاملًا للـ Portal.

---

## 4.1 ربط المستخدم

أول مرة:

```text
/start
```

البوت يطلب ربط الحساب عبر كود من Portal أو رابط آمن.

بعد الربط يعرف:

```text
user
account
role
allowed servers
```

---

## 4.2 القائمة الرئيسية

```text
My Servers
My Applications
Start Diagnosis
Recent Incidents
Open Findings
Reports
Help
```

---

## 4.3 اختيار السيرفر

```text
Matrix Clouds Production
Invi Server
WhatsApp SaaS Server
```

بعد اختيار السيرفر:

```text
Server Summary
Applications
Baseline Findings
Start Diagnosis
Recent Incidents
```

---

## 4.4 اختيار التطبيق

```text
Mazadat
WhatsApp SaaS
Main Website
```

بعد اختيار التطبيق:

```text
Start Diagnosis
Laravel Production Audit
Recent 5xx
Latest Findings
App Baseline
```

---

## 4.5 بدء جلسة تشخيص

أنواع جاهزة:

```text
Slowness
500 Error
Security Scan
Laravel Production Audit
```

أو رسالة طبيعية:

```text
افحص بطء مزادات آخر ٦ ساعات
```

---

## 4.6 سير جلسة التشخيص

البوت يرسل:

```text
سأبدأ بفحص موارد السيرفر خلال آخر ٦ ساعات لاستبعاد ضغط CPU أو Disk I/O.
```

بعد موافقة بداية الجلسة:

```text
read-only tools auto-approved
```

ثم يرسل notes:

```text
لا يظهر ضغط CPU أو Disk I/O. الخطوة التالية تحليل Apache logs.
```

ثم:

```text
تم اكتشاف APP_DEBUG=true وDebugbar exposed.
```

ثم التقرير النهائي.

---

## 4.7 أزرار الجلسة

```text
Stop
Show Details
Final Report
Run Next
```

في MVP مع auto-approval، زر Run Next قد لا يكون مطلوبًا إلا لو الحساب اختار manual mode لاحقًا.

---

## 4.8 التنبيهات في Groups

الجروب يستقبل:

```text
Agent offline
Critical baseline finding
Repeated recent 5xx
APP_DEBUG=true newly detected
Debugbar exposed
Suspicious cron detected
```

قاعدة مهمة:

```text
لا تنبيه على findings قديمة إلا لو أصبحت active حديثًا.
```

---

# 5. Dashboard عام للمنتج / Public Website

هذه ليست من الواجهات الثلاث الأساسية، لكنها مهمة تجاريًا لاحقًا.

في MVP يمكن أن يكون صفحة بسيطة:

```text
Landing page
Pricing
Login
Contact
Docs
Install guide
```

لكن لا تعطى أولوية قبل Admin/Portal/Telegram.

---

# 6. تقسيم الوظائف حسب الواجهة

| الوظيفة | Admin | Portal | Telegram |
|---|---:|---:|---:|
| إنشاء الحسابات | نعم | لا | لا |
| إدارة الباقات | نعم | لا | لا |
| إدارة الاشتراكات | نعم | عرض فقط | لا |
| تسجيل المدفوعات | نعم | عرض فقط | لا |
| إضافة سيرفر | نعم/نيابة | نعم | لا في البداية |
| عرض السيرفرات | نعم | نعم | نعم |
| Baseline Scan | نعم | نعم | ملخص فقط |
| مراجعة التطبيقات المكتشفة | نعم | نعم | لا أو محدود |
| Tool Registry | نعم | لا | لا |
| Tool Builder Agent | نعم | لا | لا |
| Diagnostic Sessions | نعم | نعم | نعم |
| Incident Reports | نعم | نعم | نعم مختصر |
| Audit Logs | نعم كامل | محدود | لا |
| Telegram Settings | نعم | نعم | من البوت جزئيًا |
| Alerts | مراقبة عامة | إعدادات | استقبال |

---

# 7. أولويات التنفيذ للواجهات

## 7.1 Admin MVP

```text
Accounts
Users
Servers
Plans
Subscriptions
Tool Registry
Audit Logs
Incidents
```

## 7.2 Portal MVP

```text
Dashboard
Servers
Applications Pending Review
Baseline Summary
Findings
Diagnostic Sessions
Reports
Telegram Settings
Subscription Usage
```

## 7.3 Telegram MVP

```text
Link account
List servers
List apps
Start diagnosis
Show agent notes
Show final report
Receive alerts
```

---

# 8. ترتيب التنفيذ المقترح

الأفضل التنفيذ بهذا الترتيب:

```text
1. Admin basic
2. Portal basic
3. Server registration + baseline display
4. Telegram linking
5. Diagnostic session from Portal
6. Diagnostic session from Telegram
7. Tool Builder Agent
```

السبب: يجب أن يكون عندنا Admin/Portal يعرفان الحسابات والسيرفرات قبل أن يعمل Telegram بذكاء.

---

# 9. الخلاصة

تقسيم الواجهات المعتمد:

```text
Admin = إدارة المنصة والمنتج والأدوات والباقات
Portal = إدارة العميل لسيرفراته وتطبيقاته وتشخيصاته
Telegram = تشغيل سريع وتنبيهات وجلسات تشخيص موجهة
```

الثلاثة يجب أن يستخدموا:

```text
نفس الـ backend
نفس الصلاحيات
نفس audit log
نفس policy engine
نفس tool registry
```
