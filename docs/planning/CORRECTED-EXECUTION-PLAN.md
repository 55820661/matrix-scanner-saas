# خطة تنفيذية مصححة - Matrix Scanner SaaS

هذه الوثيقة هي الخطة التنفيذية العملية المبنية على `docs/planning/ROADMAP-CORRECTION.md` وعلى الوضع الحالي للكود بعد اكتمال MVP وPhase 2 حتى ingestion. الهدف هو تحويل المشروع من منصة scanner تجمع بيانات إلى منتج تشخيص ذكي يقوده AI واحد داخل Admin Chatbot، ثم فتح نفس العقل لاحقا من Telegram.

تصحيح مهم لمفهوم الأدوات: في المرحلة الحالية، الأداة ليست بالضرورة runtime handler مستقل داخل كود الـ Agent. الأساس العملي المفضل هو أن تكون الأداة `command_template` أو `script_template` read-only محفوظة داخل Tool Registry، ويتولى SaaS التحقق من السياسات والصلاحيات قبل أن ينفذها Runtime/Agent كـ safe restricted command executor. Runtime handlers تبقى خيارا متقدما لاحقا فقط عند الحاجة.

## 1. القاعدة التنفيذية

- يوجد AI واحد فقط: `Admin AI Chatbot`.
- لا يتم إنشاء AI مستقل للتشخيص أو التقارير أو بناء الأدوات.
- `DiagnosticSession` الحالي يستخدم كبنية workflow/قرارات، وليس كعقل مستقل.
- `Tool Builder` الحالي يستخدم كمسار منظم داخل نفس الشات.
- Telegram لاحقا واجهة لنفس الشات ونفس السياسات، وليس backend مستقل.
- كل التنفيذ يظل read-only في هذه المرحلة.
- لا shell حر، لا remediation، لا destructive/write actions.
- كل تشغيل أداة يجب أن يمر عبر `ToolDefinition -> ToolPolicy -> PlanTool -> ToolRun -> AgentJob`.
- كل سياق للـ AI يجب أن يكون redacted, summarized, capped.
- أدوات المرحلة الحالية يجب أن تكون command templates أو script templates منظمة ومقيدة، لا أوامر حرة.
- runtime handlers لا تكون الأساس الافتراضي لكل أداة، بل خيار متقدم لاحقا.

## 2. الوضع الحالي المختصر

الحالة الموثقة في 2026-06-20:

- المسار المصحح من C1 إلى C9 مكتمل.
- Remote Bootstrap يثبت Runtime/Agent الحقيقي ويدعم registration وheartbeat وpolling وتنفيذ AgentJob وإرجاع النتائج.
- Safe Context Builder وAdmin Internal Chat وPortal Customer Chat وTool Orchestrator منفذة.
- Runtime يدعم `command_template` الآمن بأسلوب argv-only، مع بقاء `script_template` مؤجلا.
- Tool Builder متاح في Admin Internal Chat فقط، ولا يوجد في Portal.
- Portal يستخدم الأدوات المعتمدة فقط ويوفر تقارير customer-safe بنمط self-service.
- تقارير الشات تستخدم redaction وreadable summaries ولا تعرض raw ToolRun/AgentJob output.
- C10-A نُفذ يدويا على Matrix/Siyaq كـ internal pilot أولي ناجح. عمل Portal Chat وSafe Context و`services_status` ومسار `ToolRun -> AgentJob` وعودة safe summary والتقارير دون ظهور raw logs أو raw `.env` أو raw execution output.
- مشكلة عرض dict/list في التقارير التي ظهرت أثناء C10-A أُصلحت لاحقا.
- C10.5 فصل مسؤوليات Portal Customer Chat عن Staff-only Admin Internal Chat، وC10.5-B أكمل تحسين واجهة وتنقل Internal Chat.
- C10-B Laravel/Apache/Innvii Pilot مؤجل حاليا.
- Live AI لم ينفذ بعد. المسار المقترح التالي هو C10.6 داخل Admin Internal Chat فقط.
- Telegram C11 وTelegram Pilot C12 لم يبدآ، وليسا المهمة الفورية التالية.

## 3. المراحل التنفيذية المعتمدة

| Sprint | الاسم | حالة التنفيذ |
|---|---|---|
| C1 | Current State and Documentation Alignment | مكتمل |
| C1.5 | Remote Bootstrap Runtime Completion | مكتمل |
| C2 | Safe Context Builder MVP | مكتمل |
| C3 | Admin Chat Data Model and Read-only UI | مكتمل |
| C4 | Deterministic Chat Responder | مكتمل |
| C5 | Tool Orchestrator MVP | مكتمل |
| C6 | Safe Command Execution Runtime | مكتمل |
| C7 | Tool Builder from Chat | مكتمل، ثم قُصر على Admin Internal Chat في C10.5 |
| C8 | First Laravel/Apache Tool Cycle | مكتمل باستخدام `apache_5xx_summary` |
| C9 | Reports from Chat | مكتمل |
| C10-A | Internal Pilot on Matrix/Siyaq | مكتمل يدويا وناجح كـ pilot أولي |
| C10.5 | Split Admin and Portal Chat Responsibilities | مكتمل |
| C10.5-B | Admin Internal Chat UX and Navigation Fix | مكتمل |
| C10.5-C | Current State Reconciliation | مكتمل |
| C10-B | Laravel/Apache/Innvii Pilot | مؤجل |
| C10.6-Pre | Safe Context Hard Cap and Live AI Readiness | مكتمل، دون Live AI |
| C10.6 | Live Admin AI Chatbot MVP | الخطوة المقترحة التالية، غير منفذة |
| C11 | Telegram Interface to Same Chat | لم يبدأ |
| C12 | Telegram Pilot | لم يبدأ |

## 4. المرحلة 0 - Current State Lock

### الهدف

تثبيت نقطة البداية قبل أي بناء جديد.

### لماذا مطلوبة

المشروع وصل لحالة تشغيلية جيدة، وأي بناء AI/Chat فوقه يجب ألا يكسر baseline أو runtime أو ingestion.

### التنفيذ

- تأكيد آخر commit محلي وremote.
- تأكيد أن working tree نظيف أو توثيق الملفات المفتوحة.
- تشغيل:
  - `python manage.py check`
  - `python manage.py makemigrations --check --dry-run`
  - `python manage.py test --noinput`
- توثيق آخر server smoke:
  - baseline profile.
  - scan summary.
  - services/domains/apps/log sources counts.
- مراجعة migrations الحالية بدون squash.

### ملفات محتملة

- `LOG.md`
- `docs/CURRENT-TASKS.md`
- `docs/planning/CORRECTED-EXECUTION-PLAN.md`
- ربما `docs/operations/RELEASE-CHECKLIST.md`

### نماذج متأثرة

لا يوجد.

### اختبارات

لا اختبارات جديدة إلا إذا ظهر regression.

### Manual Smoke

- Admin login.
- Portal login.
- baseline `debian_nginx_opt`.
- latest report.
- agent heartbeat.

### مخاطر

منخفضة.

### الأولوية

يجب تنفيذها قبل أي مرحلة أخرى.

## 4.5 المرحلة 0.5 - Remote Bootstrap Runtime Completion

### الهدف

استكمال مسار `Remote Bootstrap Foundation` الموجود حاليا بحيث لا يثبت bundle بسيطا للتسجيل والـ heartbeat فقط، بل يثبت ويشغل Agent Runtime الحقيقي المتوافق مع SaaS الحالي.

### الوضع الحالي

Remote Bootstrap foundation موجود بالفعل وليس مجرد فكرة. الموجود حاليا يشمل:

- `BootstrapSession`.
- `BootstrapStep`.
- `BootstrapCredential`.
- `AgentInstallation`.
- Paramiko SSH adapter.
- encrypted temporary credentials.
- credential TTL.
- cleanup بعد success/failure/expiry.
- fixed install command templates.
- runtime config upload.
- systemd service install/start.
- heartbeat verification.
- Admin action.
- tests بالـ mocks.

لكن الـ bootstrap bundle الحالي ما زال من نوع `sprint3-bootstrap-runtime`، ويقوم أساسا بـ registration + heartbeat فقط. لا يحتوي هذا bundle على job polling أو ToolRun/AgentJob execution الكامل.

### لماذا مطلوبة

قبل الاعتماد على Remote Bootstrap لتثبيت runtime على سيرفرات داخلية أو سيرفرات عملاء، يجب أن يكون ما يتم تثبيته هو Runtime/Agent الحقيقي القادر على:

- registration أو استخدام registration token.
- heartbeat.
- polling.
- استقبال AgentJob.
- تنفيذ jobs المعتمدة.
- job result submission.
- استخدام config متوافق مع SaaS الحالي.
- العمل كـ systemd service مستقرة.

### نطاق التنفيذ لاحقا

- عدم هدم Remote Bootstrap الموجود.
- إعادة استخدام models/services/admin/tests الحالية.
- تحديث `runtime_bundle` أو install flow ليستخدم Agent Runtime الحقيقي الحالي بدل bootstrap demo runtime.
- التأكد أن systemd service يشير إلى runtime الصحيح.
- التأكد أن config الناتج متوافق مع runtime الحالي.
- إبقاء bootstrap نفسه لا ينشئ `AgentJob` أو `BaselineScan` أثناء التثبيت.
- الحفاظ على cleanup للـ credentials بعد success/failure/expiry.
- إضافة smoke checklist لتجربة تثبيت حقيقية على VM أو سيرفر داخلي.

### ممنوع في هذه المرحلة

- لا Portal customer bootstrap.
- لا raw shell جديد.
- لا arbitrary commands.
- لا تغيير فلسفة الأدوات إلى runtime handlers.
- لا remediation أو write/destructive actions.
- لا توسيع UI خارج Admin action الحالية إلا إذا كان ضروريا جدا.

### اختبارات مطلوبة لاحقا

- install flow ينتج config صحيح ومتوافق مع runtime الحالي.
- systemd service يشير إلى runtime الصحيح.
- runtime المثبت يستطيع التسجيل وإرسال heartbeat.
- runtime المثبت يستطيع polling وتنفيذ AgentJob معتمد ثم submit result.
- bootstrap لا ينشئ AgentJob أو Baseline أثناء التثبيت.
- credentials cleanup بعد success/failure/expiry.
- رفض raw/arbitrary commands مستمر.

### Manual Smoke

- Matrix Admin ينشئ bootstrap session من Django Admin ببيانات SSH مؤقتة.
- تشغيل bootstrap على VM أو سيرفر داخلي.
- التحقق من وجود `/opt/matrix_scanner/config.json`.
- التحقق من `matrix-scanner-agent.service`.
- التحقق من heartbeat في SaaS.
- إنشاء ToolRun/Baseline لاحقا والتأكد أن runtime المثبت يقوم بالـ polling والتنفيذ.
- التحقق من تنظيف credentials.

### مخاطر

متوسطة إلى عالية بسبب SSH وsystemd وتثبيت runtime على سيرفر فعلي. يجب تنفيذها كسبرنت مستقل ومحدود، مع إبقاء الأوامر ثابتة ومراجعة redaction/cleanup.

### الأولوية

تأتي مباشرة بعد تثبيت الوضع الحالي وقبل الاعتماد على Remote Bootstrap كوسيلة تثبيت runtime للأدوات أو للـ pilot.

## 5. المرحلة 1 - Architecture Cleanup

### الهدف

توحيد المصطلحات والوثائق حول مفهوم AI واحد فقط.

### التنفيذ

- اعتماد `ROADMAP-CORRECTION.md` كوثيقة مرجعية.
- مراجعة docs القديمة التي توحي بوجود:
  - Diagnostic AI مستقل.
  - Report AI مستقل.
  - Tool Builder AI مستقل.
- تعديل اللغة إلى:
  - Admin AI Chatbot.
  - Tool Orchestrator.
  - Tool Builder Workflow.
  - Reports from Chat.
  - Telegram Interface for the same AI.

### ملفات محتملة

- `PLANS.md`
- `README.md`
- `docs/planning/matrix_scanner_saas_mvp_plan.md`
- `docs/planning/matrix_scanner_saas_execution_plan.md`
- `docs/planning/matrix_scanner_saas_interfaces_plan.md`
- `docs/PROJECT-STRUCTURE.md`
- `docs/TEST-PLAN.md`

### نماذج متأثرة

لا يوجد.

### اختبارات

لا يوجد.

### مخاطر

منخفضة. الخطر الوحيد هو تغيير وثائق بطريقة تلغي قرارات صحيحة؛ يجب أن يكون التعديل مصطلحي وتنظيمي فقط.

### الأولوية

يجب إتمامها قبل تصميم Admin Chat.

## 6. المرحلة 2 - Safe Context Builder

### الهدف

إنشاء طبقة واحدة مسؤولة عن بناء السياق الآمن الذي يقرأه Admin AI Chatbot.

### لماذا مطلوبة

بدونها سيضطر الشات أو الـ AI إلى قراءة مخرجات خام أو نماذج كثيرة مباشرة، وهذا يرفع خطر تسريب أسرار أو prompt injection أو context bloat.

### نطاق التنفيذ

إنشاء service لا يستدعي AI ولا يشغل أدوات. فقط يبني JSON آمن.

### المخرجات المطلوبة

```json
{
  "account_summary": {},
  "server_summary": {},
  "baseline_summary": {},
  "applications_summary": [],
  "services_summary": [],
  "domains_summary": [],
  "log_sources_summary": [],
  "findings_summary": [],
  "reports_summary": [],
  "knowledge_summary": [],
  "available_tools": [],
  "recent_tool_runs": [],
  "risk_summary": {}
}
```

### مصادر آمنة

- `Server` safe fields فقط.
- آخر `BaselineScan.summary`.
- `Application`: name, framework, path, domain, review_status, safe metadata.
- `DiscoveredService`: name, status, safe metadata.
- `DiscoveredDomain`: domain, document_root, owner, safe metadata.
- `LogSource`: path, type, exists, size metadata فقط.
- `Finding`: title, severity, status, evidence_summary.
- `Report`: title, type, summary_redacted.
- `KnowledgeEntry`: approved/internal-safe/customer-visible حسب المستخدم.
- `ToolDefinition` المتاحة عبر ToolPolicy/PlanTool.
- `ToolRun`: status, tool key/name, timestamps, redacted summary فقط.

### ممنوع

- `AgentJob.result` raw.
- `ToolRun.result_redacted` كامل بدون تلخيص.
- raw logs.
- raw `.env`.
- credentials/tokens/private keys.
- bootstrap stdout/stderr.
- prompts خام من المستخدم بدون redaction.

### ملفات محتملة

- `apps/ai_context/services.py` أو `apps/diagnostics/context.py`
- إذا لم نرغب في app جديد: `apps/diagnostics/context_builder.py`
- `tests/unit/test_safe_context_builder.py`
- Admin/Portal imports لاحقا.

### نماذج متأثرة

لا migrations مبدئيا.

### اختبارات مطلوبة

- context is account-scoped.
- cross-account server denied.
- viewer/operator/owner visibility differences.
- no raw AgentJob result.
- no raw ToolRun output.
- secrets redacted.
- output capped.
- available tools respect ToolPolicy/PlanTool.
- latest baseline/report/finding summaries included.

### Manual Smoke

- Build context for Matrix/Siyaaq server.
- Confirm counts match latest baseline.
- Confirm no raw long outputs.

### مخاطر

متوسطة بسبب حساسية البيانات. يجب تنفيذها قبل أي AI provider.

## 7. المرحلة 3 - Admin Chat MVP

### الهدف

إنشاء واجهة محادثة داخلية محفوظة، لكنها في أول نسخة لا تشغل أدوات ولا تستخدم Telegram.

### نطاق MVP

- شات داخل Portal أو Admin.
- ربط conversation بالمستخدم والحساب والسيرفر والتطبيق اختياريا.
- تخزين الرسائل redacted.
- استخدام Safe Context للردود.
- في أول خطوة يمكن استخدام deterministic/mock responder أو provider disabled mode.

### نماذج مقترحة

`AdminChatSession`

- account
- user
- server nullable
- application nullable
- status: `open`, `archived`
- title_redacted
- context_snapshot_redacted
- last_message_at

`AdminChatMessage`

- session
- sender_type: `user`, `assistant`, `system`
- body_redacted
- metadata_redacted
- created_at

`AdminChatDecision`

- session
- decision_type: `answer`, `tool_suggestion`, `tool_request`, `report_request`, `tool_build_request`
- input_context_redacted
- output_json_redacted
- reasoning_summary

### ملفات محتملة

- `apps/ai_chat/models.py` أو داخل `apps/diagnostics`
- `apps/ai_chat/services.py`
- `apps/ai_chat/admin.py`
- `apps/portal/views.py`
- `templates/portal/admin_chat_*.html`
- tests under `tests/unit/test_admin_chat.py`

### قرار معماري

يفضل إنشاء app جديد `apps/ai_chat` لأن الشات سيكون مركزيا فوق diagnostics/tools/reports، وليس جزءا من diagnostics فقط.

### اختبارات

- owner/operator can create chat.
- viewer read-only or blocked from active chat حسب القرار.
- staff without account cannot use Portal chat.
- account scoping.
- selected server/application ownership checks.
- message redaction.
- no ToolRun/AgentJob created in Chat MVP.

### Manual Smoke

- افتح Portal.
- اختر server.
- افتح chat.
- اسأل عن الحالة.
- تحقق أن الرد يعتمد على Safe Context ولا يشغل أدوات.

### مخاطر

متوسطة: UI + permissions + redaction.

## 8. المرحلة 4 - Tool Orchestrator MVP

### الهدف

تمكين الشات من اقتراح وتشغيل أدوات موجودة فقط عبر السياسات الحالية.

### نطاق التنفيذ

- لا free-form tool execution.
- لا arbitrary params.
- الأدوات المسموحة تأتي من Safe Context `available_tools`.
- C5 يشغل فقط الأدوات الموجودة حاليا والتي لها مسار تنفيذ آمن بالفعل، مثل runtime handlers الحالية أو أي مسارات آمنة موجودة ومفعلة عبر ToolPolicy.
- C5 لا يعني السماح بتشغيل `command_template` أو `script_template` قبل وجود Runtime آمن لها.
- تشغيل أدوات من نوع `command_template` أو `script_template` يبدأ فقط بعد تنفيذ C6، أو يتم دمج جزء من C5/C6 إذا قررنا أننا نحتاج command templates مبكرا.
- أول نسخة يمكن أن تكون deterministic intent routing بدون LLM.
- لاحقا AI يخرج JSON action proposal، والخدمة تتحقق منه.

### Orchestrator Actions

```text
answer_from_context
suggest_tool
request_tool_approval
run_approved_tool
summarize_tool_result
stop
```

### Workflow

1. المستخدم يسأل.
2. Orchestrator يحدد هل يحتاج أداة.
3. يعرض الأداة وسبب الاختيار.
4. يطلب approval.
5. بعد approval ينشئ `ToolRun` عبر `create_tool_run_job`.
6. ينتظر النتيجة.
7. يلخص النتيجة داخل الشات.

### ملفات محتملة

- `apps/ai_chat/orchestrator.py`
- `apps/ai_chat/services.py`
- `apps/tools/services.py` reuse only.
- `apps/portal/views.py`
- `templates/portal/admin_chat_detail.html`
- tests.

### نماذج محتملة

إضافة:

- `AdminChatToolRequest`
  - session
  - message
  - tool_definition
  - params_redacted
  - status: `suggested`, `approved`, `queued`, `succeeded`, `failed`, `cancelled`
  - tool_run nullable
  - approved_by
  - approved_at

### اختبارات

- cannot run tool not in available tools.
- ToolPolicy denial blocks before AgentJob.
- PlanTool denial blocks.
- viewer cannot approve.
- owner/operator can approve.
- no direct AgentJob creation.
- result summary does not include raw output.
- audit entries created.

### Manual Smoke

- Ask chat to check services.
- Approve `systemd_services_discovery` or safe enabled tool.
- Confirm ToolRun/AgentJob created.
- Runtime executes.
- Chat shows safe summary.

### مخاطر

عالية نسبيا لأنها أول نقطة تربط AI/chat بالتنفيذ. يجب أن تكون deterministic ومقفولة في البداية.

### العلاقة مع C6

Tool Orchestrator في C5 مسؤول عن orchestration والapproval واحترام ToolPolicy/PlanTool. لكنه لا يضيف قدرة تنفيذ عامة للأوامر المحفوظة. لذلك:

- C5 يمكنه تشغيل الأدوات الحالية التي تعمل فعلا عبر runtime handlers أو المسارات الآمنة الموجودة.
- C5 لا يشغل command templates/script templates قبل وجود Runtime آمن لها.
- C6 هو السبرنت الذي يضيف التنفيذ الآمن للأوامر المحفوظة كـ command templates/script templates.
- بعد C6 فقط يمكن لـ Tool Builder من الشات اقتراح command templates قابلة للتشغيل لاحقا.

## 9. المرحلة 5 - Safe Command Execution Runtime

### الهدف

تحويل Runtime/Agent من مجموعة handlers فقط إلى منفذ أوامر آمن ومقيد يستطيع تنفيذ command templates المعتمدة من Tool Registry، مع إبقاء runtime handlers كخيار متقدم لاحقا.

### التنفيذ المقترح

- إضافة نوع أداة مفضل للمرحلة الحالية: `command_template`.
- دعم typed parameters مع bounds واضحة.
- بناء argv ثابت أو مقيد من template مع validation، بدون shell حر.
- تطبيق timeout وmax output.
- إعادة نتيجة منظمة:
  - `stdout_redacted`
  - `stderr_redacted`
  - `exit_code`
  - `execution_time_ms`
  - `truncated`
- منع الأوامر الخطرة:
  - delete/remove/write/edit.
  - restart/reload/service actions.
  - package install/update.
  - network exfiltration.
  - secrets/private key access.
  - pipes أو redirects خطرة غير مبررة.
- الاحتفاظ بإمكانية runtime capabilities:
  - agent version.
  - supported execution modes: `command_template`, `script_template`, `runtime_handler`.
  - supported handler keys للأدوات المتقدمة الموجودة.

### نماذج محتملة

قد نضيف حقولا على `ToolTemplate` أو `ToolDefinition`:

- `execution_type`: `command_template`, `script_template`, `runtime_handler`
- `command_template_redacted`
- `allowed_parameters`
- `blocked_tokens`
- `expected_output_format`

وقد نضيف:

`ScannerAgent.capabilities_redacted`

أو نموذج:

`AgentRuntimeCapability`

- agent
- handler_key
- handler_version
- last_seen_at
- metadata_redacted

### ملفات محتملة

- `apps/servers/models.py`
- `apps/agent_api/views.py` أو مكان agent endpoints الحالي.
- `scanner_runtime/prototype.py`
- runtime handler modules.
- tests.

### اختبارات

- command templates لا تقبل shell حر.
- params يتم التحقق منها قبل بناء الأمر.
- dangerous tokens rejected.
- timeout/output cap enforced.
- stdout/stderr redacted.
- runtime handler tools الحالية لا تنكسر.
- heartbeat/capabilities لا تحتوي أسرار.
- ToolRun لا ينشأ إلا بعد ToolPolicy/PlanTool.

### Manual Smoke

- تشغيل command template بسيط read-only مثل `tail -n {{lines}} /var/log/nginx/error.log` في بيئة pilot وبـ lines bounded.
- التأكد من عدم وجود raw secrets.
- التأكد أن الأوامر غير المصرح بها ترفض قبل التنفيذ.

### مخاطر

عالية نسبيا لأنها تضيف طبقة تنفيذ عامة. يجب تنفيذها بحذر وباختبارات صارمة، وربما تبدأ بـ allowlist ضيق جدا.

## 10. المرحلة 6 - Tool Builder داخل الشات

### الهدف

ربط Tool Builder الموجود بمحادثة Admin AI Chatbot، بحيث ينتج في الأساس command templates أو script templates read-only، وليس runtime handlers افتراضيا.

### التنفيذ

- من داخل الشات، إذا طلب المستخدم أداة جديدة:
  - يبحث الشات في الأدوات الحالية.
  - إن لم تكف، ينشئ `ToolBuildRequest`.
  - يولد `ToolBuildProposal` deterministic في البداية.
  - يقترح command template مع typed inputs وtimeout/output/redaction.
  - يربط الطلب بالجلسة.
  - لا ينشئ runtime handler إلا إذا قرر Matrix Admin لاحقا أن الأداة متقدمة وتحتاج code.
  - لا يفعّل الأداة.

### ملفات محتملة

- `apps/ai_chat/tool_builder_flow.py`
- `apps/tools/services.py` reuse.
- `apps/tools/models.py` ربما add FK اختياري من ToolBuildRequest إلى chat session إذا احتجنا.

### نماذج محتملة

إما:

- إضافة `source_chat_session` nullable إلى `ToolBuildRequest`.

أو بدون migration:

- تخزين reference في `validation_summary`.

الأفضل لاحقا FK واضح إذا صار flow أساسي.

### اختبارات

- chat-created request stores redacted description.
- rejects write/destructive/remediation requests.
- existing tool suggested before new proposal.
- no ToolDefinition enabled.
- no ToolRun/AgentJob.
- proposal validates command template safety.

### Manual Smoke

- اطلب من الشات أداة Laravel Log Health.
- يتحول الطلب إلى ToolBuildRequest/Proposal.
- Admin يراجعها في Django Admin.

### مخاطر

متوسطة. يجب إبقاء التنفيذ metadata-only.

## 11. المرحلة 7 - أول دورة أداة كاملة

### الهدف

إثبات المسار الكامل بأداة واحدة تخدم الخطة التجارية الأصلية وتعمل كـ command template آمن إن أمكن، لا كـ runtime handler إلا عند الضرورة.

### الأداة الموصى بها أولا

الأداة الأولى المفضلة يجب أن تكون أقل حساسية من `.env`، مثل:

- `laravel_log_health`
- أو `apache_5xx_summary`

السبب:

- تثبت دورة command template أو safe tool execution بأقل تعرض للـ secrets.
- يمكن ضبطها بمدخلات محدودة مثل عدد الأسطر أو نافذة زمنية bounded.
- تختبر redaction وoutput caps وapproval flow وsafe summary.
- لا تتطلب قراءة raw `.env` في أول إثبات للمسار الكامل.

### أدوات مؤجلة بعد إثبات المسار

- `laravel_env_sanity`
- `supervisor_summary`
- `queue_workers_summary`

`laravel_env_sanity` مهمة تجاريا، لكنها تتعامل مع `.env` ومخاطرها أعلى. لذلك لا تكون أول أداة كاملة افتراضيا. يتم الانتقال إليها لاحقا فقط بعد إثبات:

- command templates.
- redaction.
- output caps.
- approval flow.
- safe summary.
- عدم عرض raw data.

### التنفيذ

1. الشات يناقش الحاجة للأداة.
2. ينشئ ToolBuildRequest/Proposal.
3. المقترح يحدد command template آمن ومدخلات typed.
4. يتم validation على read-only/safety/redaction/output caps.
5. يضاف ToolDefinition contract.
6. تفعيل pilot plan فقط بعد المراجعة.
7. تشغيل من الشات عبر ToolRun/AgentJob.
8. تلخيص النتيجة.

إذا ثبت أن الأداة تحتاج parsing معقد أو filesystem traversal منظم، يمكن لاحقا تنفيذها كـ runtime handler متقدم، لكن هذا ليس الافتراض الأول.

### ملفات محتملة

- `apps/tools/setup.py`
- command/script template seed أو proposal conversion حسب قرار التنفيذ.
- ربما runtime command-template support من C6.
- runtime handler متقدم فقط إذا ثبت أن command template لا يكفي.
- migration seed إذا احتجنا.
- `apps/servers/baseline_profiles.py` لاحقا.
- tests.

### اختبارات

- no raw logs.
- no raw `.env`.
- no raw stack traces.
- bounded params.
- output caps.
- safe redaction.
- approval required.
- ToolPolicy/PlanTool enforced.
- if later `laravel_env_sanity` is implemented: only allowlisted keys.
- secrets never stored.
- symlink/path escape rejected.
- tool rejects params or only typed allowlisted params.

### Manual Smoke

- على سيرفر Laravel/Apache/cPanel داخلي.
- تشغيل tool مباشرة عبر AgentJob.
- فحص ToolRun result.
- فحص الشات summary.

### مخاطر

متوسطة إذا بدأنا بـ `laravel_log_health` أو `apache_5xx_summary` مع عدم عرض raw logs. تصبح عالية عند الانتقال لاحقا إلى `laravel_env_sanity` بسبب `.env`، ويجب تنفيذها بعد ضبط القيود الأمنية.

## 12. المرحلة 8 - Reports من نفس الشات

### الهدف

تمكين الشات من إنشاء تقرير تقني ومبسط من نفس السياق والأدوات.

### التنفيذ

- استخدام models الحالية:
  - `Report`
  - `ReportSection`
  - `Recommendation`
- إضافة report template service:
  - technical report.
  - customer summary.
- ربط report request بالchat session.
- قبل الحفظ، يعرض draft للمراجعة.

### نماذج محتملة

قد نضيف:

`AdminChatReportDraft`

- session
- report_type
- title_redacted
- sections_redacted
- status: `draft`, `approved`, `converted`, `rejected`
- converted_report nullable

أو نستخدم `Report` مباشرة كـ generated بعد approval. الأفضل draft model لو AI live.

### اختبارات

- no raw ToolRun output.
- no raw AgentJob output.
- no raw logs/env.
- recommendations advisory only.
- report account scoping.
- technical/customer summaries differ but safe.

### Manual Smoke

- اطلب من الشات تقرير عن سيرفر.
- راجع draft.
- احفظ report.
- افتحه من Portal/Admin.

### مخاطر

متوسطة. Reports foundation آمن نسبيا، لكن AI text generation يحتاج guardrails.

## 13. المرحلة 9 - Internal Pilot

### الهدف

اختبار المسار الداخلي قبل Telegram.

### البيئات

- Matrix/Siyaaq: Debian/Nginx/Opt/Django/PostgreSQL.
- Innvii أو بديل: Laravel/Apache/cPanel/PHP/MySQL/Supervisor.
- Laravel/Nginx إذا متاح.

### سيناريوهات الاختبار

- اسأل الشات عن حالة السيرفر.
- اطلب تشخيص 500.
- اطلب تشخيص Laravel production audit.
- شغل أداة read-only.
- اطلب تقرير تقني.
- اطلب تقرير مبسط.
- اطلب raw logs وتأكد من الرفض.
- اطلب إجراء خطير وتأكد من الرفض.

### معيار النجاح

- الشات مفيد بدون raw data.
- كل tool runs عبر ToolPolicy.
- لا تسريب أسرار.
- runtime مستقر.
- التقارير مفهومة.

## 14. المرحلة 10 - Telegram Interface

### الهدف

فتح نفس Admin AI Chatbot من Telegram بدون منطق مستقل.

### شرط البدء

لا تبدأ هذه المرحلة قبل نجاح المرحلة 9.

### التنفيذ

- Telegram message -> Chat session/message.
- يستخدم نفس Safe Context Builder.
- يستخدم نفس Orchestrator.
- يستخدم نفس approvals.
- private chat فقط.
- groups summaries only.

### أوامر أولية

- `/start`
- `/help`
- `/servers`
- `/select_server`
- `/status`
- `/diagnose`
- `/report`
- `/cancel`

### اختبارات

- revoked/expired links denied.
- cross-account callback denied.
- viewer cannot run tools.
- group diagnostics blocked.
- raw logs refused.
- no direct AgentJob.

## 15. المرحلة 11 - Telegram Pilot

### الهدف

اختبار داخلي محدود قبل أي تعميم.

### التنفيذ

- مستخدم داخلي واحد أو اثنان.
- سيرفر واحد فقط في البداية.
- أدوات read-only محدودة.
- logging/audit كامل.
- مراجعة كل الردود.

### معيار النجاح

- نفس AI ونفس السياسات.
- لا تسريب بيانات.
- تجربة مفهومة على mobile.
- لا التفاف على Portal/Admin permissions.

## 16. خطة السبرنتات المقترحة

### Sprint C1 - Current State and Documentation Alignment

Objective:
- تثبيت الوضع الحالي وتحديث docs لتتبع المعمارية المصححة.

Implement:
- تحديث docs فقط.
- لا code.

Tests:
- `git diff --check`.

Must happen now:
- نعم.

### Sprint C1.5 - Remote Bootstrap Runtime Completion

Objective:
- استكمال Remote Bootstrap بحيث يثبت Agent Runtime الحقيقي المتوافق مع SaaS الحالي، وليس bundle التسجيل والـ heartbeat فقط.

Implement:
- إعادة استخدام Bootstrap models/services/admin/tests الحالية.
- تحديث runtime bundle أو install flow.
- إنتاج config صحيح.
- systemd service يشير إلى runtime الصحيح.
- smoke checklist لتثبيت حقيقي على VM أو سيرفر داخلي.

Do not implement:
- Portal customer bootstrap.
- raw shell.
- arbitrary commands.
- تغيير فلسفة الأدوات إلى runtime handlers.

Must happen before relying on bootstrap-installed runtime:
- نعم.

### Sprint C2 - Safe Context Builder MVP

Objective:
- بناء service آمن ينتج JSON context.

Implement:
- context builder.
- tests.
- Admin helper/read-only preview إن لزم.

Models:
- لا migrations مبدئيا.

Must happen before AI:
- نعم.

### Sprint C3 - Admin Chat Data Model and Read-only UI

Objective:
- إنشاء جلسات ورسائل الشات بدون tool execution.

Models:
- `AdminChatSession`
- `AdminChatMessage`
- ربما `AdminChatDecision`

Migrations:
- نعم.

Must happen before Tool Orchestrator:
- نعم.

### Sprint C4 - Deterministic Chat Responder

Objective:
- ردود مبنية على Safe Context بدون LLM live.

Implement:
- service يرد على status/summary/findings/reports.
- لا ToolRun.

Must happen before live AI:
- نعم.

### Sprint C5 - Tool Orchestrator MVP

Objective:
- تشغيل أدوات موجودة من الشات بعد approval.
- C5 يستخدم فقط أدوات لها مسار تنفيذ آمن موجود بالفعل.
- لا تشغيل `command_template` أو `script_template` قبل C6.

Models:
- `AdminChatToolRequest` غالبا.

Migrations:
- غالبا نعم.

Must happen before Telegram:
- نعم.

### Sprint C6 - Safe Command Execution Runtime

Objective:
- تمكين Runtime/Agent من تنفيذ command templates المعتمدة بأمان.
- هذه هي المرحلة التي تسمح لاحقا بتشغيل `command_template` و`script_template` المقترحة أو المعتمدة.

Models:
- likely changes to ToolDefinition/ToolTemplate execution metadata.

Can defer:
- لا يفضل تأجيله إذا كان Tool Builder من الشات سيقترح أدوات جديدة كـ command templates.

### Sprint C7 - Tool Builder from Chat

Objective:
- تحويل طلب أداة من الشات إلى ToolBuildRequest/Proposal.

Implement:
- integration فقط.
- command-template proposal أولا.
- runtime handler proposal فقط كخيار متقدم إذا قرر Matrix Admin أن command template لا يكفي.

### Sprint C8 - First Laravel/Apache Tool Cycle

Objective:
- إثبات أول أداة تجارية من الشات end-to-end.

Recommended tool:
- `laravel_log_health` أو `apache_5xx_summary`.

Deferred first-sensitive tool:
- `laravel_env_sanity` بعد إثبات redaction/output caps/approval/safe summary وعدم عرض raw data.

### Sprint C9 - Reports from Chat

Objective:
- إنشاء تقارير تقنية ومبسطة من نفس الشات.

### Sprint C10 - Internal Pilot

Objective:
- اختبار شامل داخلي على بيئتين.

Current reconciliation:
- C10-A نُفذ يدويا على Matrix/Siyaq ونجح كـ internal pilot أولي.
- C10-B Laravel/Apache/Innvii لم ينفذ ومؤجل حاليا.

### Sprint C10.5 - Chat Responsibility Split

Status:
- مكتمل، بما في ذلك C10.5-B لتحسين UX والتنقل في Admin Internal Chat.
- Portal Customer Chat لا يحتوي Tool Builder، وAdmin Internal Chat ما زال staff-only.

### Sprint C10.5-C - Current State Reconciliation

Objective:
- توثيق الحالة الفعلية فقط قبل أي تطوير جديد.

### Sprint C10.6 - Live Admin AI Chatbot MVP

Status:
- غير منفذ، وهو المسار المقترح التالي قبل Telegram ما لم يصدر قرار عكسي.
- يبدأ داخل Admin Internal Chat فقط، وليس Portal أو Telegram.

Prerequisite completed:
- C10.6-Pre يفرض hard byte cap فعليا على Safe Context ويجهز payload منفصلة allowlisted مع redaction ثانية وتعليمات واضحة بأن بيانات السياق غير موثوقة ولا تنفذ أدوات أو أوامر.
- لا تتضمن payload الخام logs أو `.env` أو ToolRun/AgentJob output، ولم يضف هذا الشرط أي Live AI أو ChatKit أو execution path.

### Sprint C11 - Telegram Interface to Same Chat

Objective:
- Telegram كواجهة لنفس chat/orchestrator.

Status:
- لم يبدأ، وليس المهمة الفورية التالية حاليا.

### Sprint C12 - Telegram Pilot

Objective:
- pilot داخلي محدود وآمن.

Status:
- لم يبدأ.

## 17. ما لا يجب تنفيذه الآن

- لا live LLM ضمن C10.5-C؛ C10.6 هو Sprint مستقل مقترح ويحتاج نطاقا واعتمادا واضحين.
- لا Telegram AI قبل نجاح Internal Pilot.
- لا remediation.
- لا write/destructive tools.
- لا shell حر.
- لا تنفيذ command template غير معتمد.
- لا customer-created tools.
- لا report AI مستقل.
- لا diagnostic AI مستقل.
- لا Tool Builder AI مستقل.
- لا raw logs أو raw `.env`.
- لا direct AgentJob من Telegram أو من الشات.

## 18. أول Sprint موصى به بعد اعتماد هذه الوثيقة

الأول المقترح:

```text
Sprint C1 - Current State and Documentation Alignment
```

لكن إذا كانت الوثائق كافية وتم اعتماد هذه الوثيقة، نبدأ مباشرة بـ:

```text
Sprint C1.5 - Remote Bootstrap Runtime Completion
```

هذا هو أول sprint برمجي حقيقي موصى به إذا كنا سنعتمد على Remote Bootstrap لتثبيت Runtime/Agent في pilot أو على سيرفرات جديدة. بعده يأتي:

```text
Sprint C2 - Safe Context Builder MVP
```

لأنه شرط أمان قبل Admin Chat وAI وTelegram. أما تنفيذ command-template runtime العام فيأتي بعد Safe Context وAdmin Chat الأساسي، وقبل السماح للشات باقتراح وتشغيل أدوات جديدة.

## 19. معيار الجاهزية للانتقال إلى Telegram

لا نبدأ Telegram Interface إلا بعد تحقق التالي:

- Safe Context Builder آمن ومختبر.
- Admin Chat يعمل داخليا.
- Tool Orchestrator يشغل أدوات عبر ToolPolicy فقط.
- نتائج الأدوات تلخص ولا تعرض raw output.
- Tool Builder من الشات لا يفعل أدوات تلقائيا.
- تقرير من الشات يتم حفظه بأمان.
- Pilot داخلي ناجح على Debian/Nginx وLaravel/Apache أو بديل واقعي.
- اختبارات cross-account وviewer denial وsecret redaction ناجحة.

## 20. الخلاصة

المسار المنفذ أثبت الطبقة الداخلية الموحدة. التسلسل المقترح من الحالة الحالية هو:

```text
C10.5-C Current State Reconciliation -> C10.6 Live Admin AI Chatbot MVP -> later pilot decision -> Telegram C11 -> Telegram Pilot C12
```

يظل C10-B Laravel/Apache/Innvii مؤجلا. Live AI وTelegram لم ينفذا بعد، وأي انتقال إليهما يظل خاضعا لنطاق Sprint واعتماد مستقلين.
