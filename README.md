# 📊 ERP Accounting System v8.0

نظام ERP محاسبي مكتبي احترافي يعتمد القيد المزدوج، مبني بـ Python + PySide6 وفقًا لـ Clean Architecture.

## ✨ المميزات الرئيسية

### 🏗️ المعمارية
- **Clean Architecture**: 4 طبقات منفصلة (Domain, Use Cases, Adapters, Infrastructure)
- **0 مخالفات معمارية**: Use Cases لا تستورد من Infrastructure
- **Unit of Work**: معاملات ذرية للعمليات المعقدة
- **Dependency Injection**: Repository pattern قابل للاستبدال

### 💼 الوحدات الوظيفية (12 وحدة)
- ✅ المصادقة + RBAC (5 أدوار، 25+ صلاحية)
- ✅ العملاء والموردون (CRUD كامل)
- ✅ المنتجات والمخزون (حركة + تنبيهات + تسوية)
- ✅ الفواتير (بيع/شراء + قيود تلقائية)
- ✅ المرتجعات (بيع/شراء + قيود عكسية)
- ✅ المصروفات والإيرادات اليدوية
- ✅ التقارير (ميزان المراجعة + المركز المالي + الدخل + كشف حساب)
- ✅ النسخ الاحتياطي والاستعادة (مشفّر)
- ✅ الإعدادات العامة

### 🤖 الذكاء الاصطناعي
- **AI Agent**: مساعد ذكي بـ Function Calling
- **OpenAI Provider**: جاهز لـ GPT-4o / GPT-4o-mini
- **Local LLM**: جاهز لـ Llama عبر Ollama
- **Human-in-the-Loop**: تأكيد المستخدم قبل كل تنفيذ
- **AI Audit Log**: سجل كامل لكل تفاعل
- **OCR**: استخراج بيانات الفواتير من الصور

### 🎨 التصميم (Soft UI)
- **Claymorphism**: عناصر طينية بظلال منتفخة
- **Soft UI (Neumorphism)**: ظلال داخلية وخارجية ناعمة
- **Organic UI**: أشكال منحنية وألوان طبيعية
- **Auto-Applier**: يطبّق Soft UI على كل الشاشات تلقائيًا
- **رسوم بيانية**: BarChart + DonutChart + LineChart
- **Toast Notifications**: إشعارات منبثقة ناعمة
- **RTL كامل**: دعم العربية من اليمين لليسار

### 🔒 الأمان
- **bcrypt** (cost=12) لكلمات المرور
- **RBAC** كامل (5 أدوار)
- **Audit Log** (append-only) لكل عملية حساسة
- **قفل الحساب** بعد 5 محاولات فاشلة
- **0 SQL Injection** (100% ORM)
- **0 XSS** (Qt widgets)

## 🚀 التشغيل السريع

```bash
# 1. تثبيت المتطلبات
pip install -r requirements.txt

# 2. إعداد البيئة
cp .env.example .env
# أضف مفاتيحك في .env

# 3. تهيئة قاعدة البيانات
python -m erp_accounting.main --seed

# 4. تشغيل التطبيق
python -m erp_accounting.main
```

### بيانات الدخول الافتراضية
- **اسم المستخدم**: `admin`
- **كلمة المرور**: `Admin@123`

## 📦 بناء التطبيق التنفيذي

### Windows
```bash
build.bat
```

### Linux/macOS
```bash
chmod +x build.sh
./build.sh
```

### إنشاء مثبت احترافي (Inno Setup)
1. ثبّت [Inno Setup](https://jrsoftware.org/isdl.php)
2. افتح `installer.iss` في Inno Setup Compiler
3. اضغط Compile

## 🧪 الاختبارات

```bash
# كل الاختبارات
pytest

# مع التغطية
pytest --cov=erp_accounting --cov-report=html
```

## 📁 بنية المشروع

```
erp_accounting/
├── domain/                 # طبقة الكيانات (مستقلة)
├── use_cases/              # طبقة منطق الأعمال
├── adapters/               # طبقة التكييف (SQLAlchemy)
├── infrastructure/         # طبقة الأطر (UI, DB, Services)
│   ├── ui/theme/           # Soft UI Design System
│   ├── ui/widgets/         # مكونات ناعمة + رسوم بيانية
│   ├── ui/windows/         # 11 شاشة كاملة
│   └── services/           # AI, OCR, PDF, Backup, Audit
├── tests/                  # 300+ اختبار
├── alembic/                # Database migrations
├── build.sh / build.bat    # Build scripts
├── installer.iss           # Inno Setup installer
├── .env.example            # Environment template
├── INSTALL.md              # دليل التثبيت الكامل
└── AUDIT_REPORT_v3.md      # تقرير المراجعة
```

## 🛠️ التقنيات

| التقنية | الاستخدام |
|---------|---------|
| Python 3.11+ | اللغة الأساسية |
| PySide6 (Qt 6) | واجهات المستخدم |
| SQLAlchemy 2.0 | ORM |
| SQLite / PostgreSQL | قاعدة البيانات |
| ReportLab | تصدير PDF |
| openpyxl | استيراد/تصدير Excel |
| bcrypt | تشفير كلمات المرور |
| Alembic | إدارة migrations |
| PyInstaller | بناء التطبيق التنفيذي |

## 📊 إحصائيات المشروع

- **118 ملف Python**
- **22,000+ سطر كود**
- **300+ اختبار ناجح**
- **11 شاشة UI كاملة**
- **0 مخالفات Clean Architecture**

## 📄 الترخيص

Proprietary © 2026

## 📖 الوثائق

- [دليل التثبيت](INSTALL.md)
- [تقرير المراجعة](AUDIT_REPORT_v3.md)
- [سجل التغييرات](CHANGELOG.md)
