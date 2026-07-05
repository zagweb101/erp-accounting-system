# Changelog — سجل التغييرات

جميع التغييرات الجوهرية في كل إصدار.

## [v8.0.0] — 2026-07-05

### Added
- ✅ Windows build script (`build.bat`) — بناء التطبيق التنفيذي على ويندوز
- ✅ Inno Setup installer script (`installer.iss`) — مثبت ويندوز احترافي
- ✅ تطبيق Soft UI على **كل الشاشات** (9 نوافذ)
- ✅ Soft UI Auto-Applier (`soft_auto.py`) — يطبّق Soft UI تلقائيًا
- ✅ رسوم بيانية: BarChart + DonutChart + LineChart
- ✅ Toast Notifications ناعمة (4 أنواع)
- ✅ Dashboard حقيقي بـ KPI cards + رسوم بيانية
- ✅ OpenAI LLM Provider (جاهز للمفتاح)
- ✅ Local LLM Provider (Ollama / Llama)
- ✅ OCR Service (Tesseract — استخراج بيانات الفواتير)
- ✅ AI Chat UI (واجهة محادثة مع المساعد الذكي)
- ✅ `.env.example` template كامل
- ✅ `INSTALL.md` دليل تثبيت شامل
- ✅ `CHANGELOG.md` سجل تغييرات
- ✅ Alembic migrations
- ✅ PyInstaller spec file
- ✅ LoadingOverlay widget

### Changed
- 🔄 Login Window مُعاد تصميمها بـ Soft UI + Organic UI
- 🔄 Main Window Sidebar بألوان Soft UI ناعمة
- 🔄 كل الألوان تحوّلت من مشبعة إلى ماضيلية (soft palette)
- 🔄 كل الزوايا تحوّلت من 6-8px إلى 12-20px (أكثر نعومة)

### Fixed
- ✅ 0 مخالفات Clean Architecture (كانت 3 في v3.0)
- ✅ `datetime.utcnow()` deprecated (0 متبقي)
- ✅ `balance_after` calculation في الفواتير
- ✅ Race condition في `next_invoice_no`
- ✅ Test isolation (كل اختبار في DB منفصل)

---

## [v7.0.0] — 2026-07-05

### Added
- ✅ رسوم بيانية (BarChart, DonutChart, LineChart)
- ✅ Soft UI Auto-Applier لكل الشاشات
- ✅ `build.sh` — Build script للينكس/ماك
- ✅ `INSTALL.md` — دليل التثبيت الكامل

---

## [v6.0.0] — 2026-07-05

### Added
- ✅ Dashboard حقيقي مدمج في Main Window
- ✅ Login Window v2 (Soft UI + Organic gradient)
- ✅ Soft UI Helper للشاشات الموجودة
- ✅ `.env.example` template

### Changed
- 🔄 Main Window Sidebar بألوان Soft UI
- 🔄 كل الألوان في Main Window تحوّلت لـ Soft UI

---

## [v5.0.0] — 2026-07-05

### Added
- ✅ OpenAI LLM Provider (`openai_provider.py`)
- ✅ Local LLM Provider (Ollama)
- ✅ OCR Service (`ocr_service.py`)
- ✅ Login Window v2 (Soft UI كامل)
- ✅ Dashboard حقيقي بـ KPI cards + Gradient cards
- ✅ Toast Notification system (`toast.py`)

---

## [v4.0.0] — 2026-07-05

### Added
- ✅ **Soft UI Design System** كامل (`soft_ui.py`)
  - Claymorphism + Soft UI + Organic UI
  - لوحة ألوان ماضيلية (Soft Palette)
  - QSS شامل لكل عناصر Qt
- ✅ مكونات UI مخصصة (`soft_components.py`)
  - SoftCard, KPICard, GradientCard
  - ChatBubble, SoftSidebar, SoftSearchBar
- ✅ AI Chat UI (`ai_chat_window.py`)
  - فقاعات محادثة ناعمة
  - إجراءات سريعة + لوحة تأكيد
  - مؤشر كتابة + سجل محادثة
- ✅ LoadingOverlay widget
- ✅ Alembic migrations setup
- ✅ PyInstaller spec file

---

## [v3.1.0] — 2026-07-05

### Added
- ✅ إكمال هجرة ReportRepository (0 مخالفات Clean Architecture)
- ✅ اختبارات UI logic (28 اختبار)
- ✅ اختبارات invoice_use_cases (14 اختبار)
- ✅ LoadingOverlay widget
- ✅ docstrings محسّنة

### Fixed
- ✅ `get_low_stock_products` DetachedInstanceError

---

## [v3.0.0] — 2026-07-05

### Added
- ✅ شاشة الموردين كاملة (CRUD + بحث)
- ✅ شاشة القيود المحاسبية (جدول + قيد يدوي + قلب)
- ✅ شاشة المصروفات والإيرادات
- ✅ شاشة النسخ الاحتياطي (إنشاء + استعادة + حذف)
- ✅ شاشة الإعدادات (4 تبويبات)
- ✅ AI Agent Service foundation
  - LLMProvider interface (pluggable)
  - MockLLMProvider للاختبار
  - AIFunction definitions
  - AIAuditLogger
  - Human-in-the-Loop
  - RBAC integration
- ✅ 19 اختبار للـ AI Agent

---

## [v2.5.0] — 2026-07-05

### Added
- ✅ ReportRepository (فصل الاستعلامات المعقدة)
- ✅ docstrings للدوال العامة
- ✅ استبدال try/except: pass بـ توثيق

### Fixed
- ✅ Clean Architecture violation في reports_use_cases (3 imports → 0)

---

## [v2.4.0] — 2026-07-05

### Added
- ✅ Unit of Work pattern
- ✅ Session-aware repository methods
- ✅ 102 اختبار جديد (user_repository, auth_use_cases, services, suppliers)
- ✅ Test isolation (كل اختبار في DB منفصل)

### Fixed
- ✅ backup_service يقرأ `DATABASE_URL` ديناميكيًا
- ✅ session.py يقرأ الإعدادات ديناميكيًا

---

## [v2.3.0] — 2026-07-05 (System Audit)

### Added
- ✅ AuditLog model + AuditService
- ✅ 25 اختبار أمني وتحديثي
- ✅ AUDIT_REPORT.md (تقرير شامل)

### Fixed
- ✅ `balance_after` calculation في الفواتير
- ✅ Race condition في `next_invoice_no`
- ✅ `datetime.utcnow()` deprecated (42 موقع → 0)

---

## [v2.2.0] — 2026-07-05

### Added
- ✅ شاشة المنتجات كاملة (CRUD + مخزون + تسوية + تنبيهات)
- ✅ شاشة الفواتير كاملة (جدول + إنشاء + PDF + إلغاء)
- ✅ شاشة التقارير كاملة (4 تقارير + PDF)
- ✅ وحدة المرتجعات (بيع/شراء + قيود عكسية)
- ✅ وحدة المصروفات والإيرادات

---

## [v2.1.0] — 2026-07-05

### Added
- ✅ شاشة العملاء كاملة (CRUD + بحث)
- ✅ خدمة PDF (فواتير + ميزان مراجعة + ميزانية)
- ✅ خدمة النسخ الاحتياطي (إنشاء + استعادة)
- ✅ 27 اختبار جديد

---

## [v2.0.0] — 2026-07-05

### Added
- ✅ تحويل النظام من محاسبي إلى ERP متكامل
- ✅ وحدة العملاء (CRUD كامل)
- ✅ وحدة الموردين (CRUD كامل)
- ✅ وحدة المنتجات والمخزون
- ✅ وحدة الفواتير (بيع/شراء + قيود تلقائية)
- ✅ وحدة التقارير (ميزان + ميزانية + دخل + كشف حساب)
- ✅ تصدير PDF
- ✅ النسخ الاحتياطي والاستعادة
- ✅ دليل حسابات SOCPA (43 حساب)
- ✅ 36 قصة مستخدم

---

## [v1.0.0] — 2026-07-05

### Added
- ✅ بنية Clean Architecture كاملة (4 طبقات)
- ✅ Domain: User, Account, JournalEntry, Customer, Supplier, Product
- ✅ Use Cases: Login, CreateUser, ChangePassword, CreateJournalEntry, PostJournalEntry
- ✅ Adapters: SqlAlchemy repositories (User, Account, Journal)
- ✅ Infrastructure: Settings, DB session, 7 SQLAlchemy models, Login Window, Main Window
- ✅ محرك القيد المزدوج كامل
- ✅ Auth + RBAC (5 أدوار، 25+ صلاحية)
- ✅ دليل حسابات SOCPA (43 حساب)
- ✅ 58 اختبار ناجح

---

## PRD (وثيقة المتطلبات)

- ✅ PRD v2.0 شاملة (120 صفحة، 261 عنوان، 8 مخططات بصرية)
