# 🖥️ دليل تثبيت نظام ERP المحاسبي على سطح المكتب

## المتطلبات الأساسية

### 1. تثبيت Python 3.11+

**Windows:**
1. اذهب إلى: https://www.python.org/downloads/
2. حمّل Python 3.11 أو أحدث
3. **مهم جدًا**: عند التثبيت، فعّل خيار `Add Python to PATH`

**التحقق من التثبيت:**
```bash
python --version
# يجب أن يظهر: Python 3.11.x أو أحدث
```

---

## الطريقة الأولى: التشغيل المباشر (للمطورين)

### 1. فك الضغط
```bash
unzip erp_accounting_v10.0.zip
cd erp_accounting
```

### 2. تثبيت المكتبات
```bash
pip install -r requirements.txt
```

### 3. إعداد البيئة
```bash
cp .env.example .env
```
افتح ملف `.env` بأي محرر نصوص وعدّل:
```env
COMPANY_NAME=اسم شركتك
COMPANY_TAX_NUMBER=رقمك الضريبي
COMPANY_PHONE=هاتفك
# لإضافة الذكاء الاصطناعي (اختياري):
# OPENAI_API_KEY=sk-your-key-here
```

### 4. تهيئة قاعدة البيانات
```bash
python -m erp_accounting.main --seed
```

### 5. تشغيل التطبيق
```bash
python -m erp_accounting.main
```

### بيانات الدخول
- **اسم المستخدم**: `admin`
- **كلمة المرور**: `Admin@123`

⚠️ **غيّر كلمة المرور فور أول تسجيل دخول!**

---

## الطريقة الثانية: إنشاء اختصار على سطح المكتب (Windows)

### 1. إنشاء ملف اختصار
بعد تثبيت المتطلبات وتشغيل التطبيق مرة واحدة، أنشئ ملف `.bat`:

**الخطوات:**
1. افتح **المفكرة (Notepad)**
2. اكتب الكود التالي (عدّل المسار حسب مكان المشروع):
```bat
@echo off
cd /d "C:\path\to\erp_accounting"
python -m erp_accounting.main
pause
```
3. احفظ الملف باسم `ERP_Accounting.bat` على سطح المكتب

### 2. تغيير الأيقونة (اختياري)
1. اضغط يمين على الملف `.bat` → **إنشاء اختصار**
2. اضغط يمين على الاختصار → **خصائص**
3. اضغط **تغيير الأيقونة**
4. اختر أيقونة مناسبة

---

## الطريقة الثالثة: بناء ملف تنفيذي .exe (للتوزيع)

هذه الطريقة تنشئ ملف `.exe` يعمل بدون تثبيت Python.

### 1. تثبيت PyInstaller
```bash
pip install pyinstaller
```

### 2. بناء التطبيق
```bash
cd erp_accounting
./build.sh
```
أو يدويًا:
```bash
pyinstaller erp_accounting.spec --noconfirm
```

### 3. النتيجة
- المجلد: `dist/ERP_Accounting/`
- الملف التنفيذي: `dist/ERP_Accounting/ERP_Accounting.exe`

### 4. التثبيت على سطح المكتب
1. انسخ مجلد `dist/ERP_Accounting/` بالكامل
2. الصقه في: `C:\Program Files\ERP_Accounting\`
3. أنشئ اختصار لـ `ERP_Accounting.exe` على سطح المكتب
4. شغّل التطبيق من الاختصار

---

## الطريقة الرابعة: إنشاء مثبّت احترافي (Inno Setup)

لإنشاء مثبّت مثل البرامج الاحترافية (Setup.exe):

### 1. تثبيت Inno Setup
- حمّل من: https://jrsoftware.org/isdl.php
- ثبّت على ويندوز

### 2. إنشاء سكريبت التثبيت
أنشئ ملف `installer.iss` في مجلد المشروع:

```iss
[Setup]
AppName=ERP Accounting System
AppVersion=10.0
AppPublisher=Your Company
DefaultDirName={pf}\ERP_Accounting
DefaultGroupName=ERP Accounting
OutputDir=installer_output
OutputBaseFilename=ERP_Accounting_Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Files]
Source: "dist\ERP_Accounting\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\ERP Accounting"; Filename: "{app}\ERP_Accounting.exe"
Name: "{commondesktop}\ERP Accounting"; Filename: "{app}\ERP_Accounting.exe"

[Run]
Filename: "{app}\ERP_Accounting.exe"; Description: "تشغيل ERP Accounting"; Flags: nowait postinstall skipifsilent
```

### 3. بناء المثبّت
1. افتح Inno Setup Compiler
2. افتح ملف `installer.iss`
3. اضغط **Compile** (Ctrl+F9)
4. النتيجة: `installer_output/ERP_Accounting_Setup.exe`

### 4. التوزيع
- وزّع `ERP_Accounting_Setup.exe` للعملاء
- العميل يشغّله → التطبيق يُثبّت تلقائيًا مع اختصار على سطح المكتب

---

## تثبيت المتطلبات الاختيارية

### تفعيل المساعد الذكي (AI)
1. احصل على مفتاح OpenAI API من: https://platform.openai.com/api-keys
2. أضف في `.env`:
```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

### تفعيل OCR (استخراج بيانات الفواتير من الصور)

**Windows:**
1. حمّل Tesseract من: https://github.com/UB-Mannheim/tesseract/wiki
2. ثبّت مع تفعيل دعم العربية
3. ثبّت Python package:
```bash
pip install pytesseract Pillow
```

### تفعيل دعم الخطوط العربية
```bash
# ثبّت خطوط Noto Sans Arabic (مهم للواجهة العربية)
# Windows: حمّل من Google Fonts
# Linux: sudo apt install fonts-noto
```

---

## استكشاف الأخطاء

### المشكلة: التطبيق لا يبدأ
```bash
# تحقق من Python
python --version

# أعد تثبيت المتطلبات
pip install -r requirements.txt --force-reinstall
```

### المشكلة: خطأ في قاعدة البيانات
```bash
# احذف قاعدة البيانات وأعد التهيئة
del erp_accounting.db  # Windows
rm erp_accounting.db   # Linux/Mac

python -m erp_accounting.main --seed
```

### المشكلة: الخطوط العربية لا تظهر
```bash
# ثبّت خطوط Noto
pip install fonttools
# أو حمّل الخطوط يدويًا من Google Fonts
```

### المشكلة: المساعد الذكي لا يعمل
- تأكد من مفتاح OpenAI في `.env`
- تأكد من اتصال الإنترنت
- تحقق من رصيد OpenAI

---

## ملخص سريع

| الطريقة | المناسبة لـ | المدة |
|---------|-------------|-------|
| تشغيل مباشر | المطورين | 5 دقائق |
| ملف .bat | الاستخدام اليومي | 10 دقائق |
| ملف .exe | التوزيع المحدود | 15 دقيقة |
| مثبّت Inno Setup | التوزيع التجاري | 30 دقيقة |

---

## الدعم

- **دليل التثبيت الكامل**: `INSTALL.md`
- **تقرير الـ Audit**: `AUDIT_FINAL_v4.md`
- **ملف المتطلبات**: `requirements.txt`
- **قالب الإعدادات**: `.env.example`

© 2026 ERP Accounting System v10.0
