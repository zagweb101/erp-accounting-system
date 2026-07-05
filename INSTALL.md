# 📦 دليل التثبيت — ERP Accounting System v7.0

## المتطلبات

### للتطوير
- Python 3.11 أو أحدث
- pip (مدير حزم Python)
- Git (اختياري)

### للتشغيل (بدون Python)
- Windows 10/11 (64-bit) أو Linux أو macOS
- 4GB RAM (الحد الأدنى)
- 500MB مساحة فارغة

---

## التثبيت للتطوير

### 1. فك الضغط
```bash
unzip erp_accounting_v7.0.zip
cd erp_accounting
```

### 2. تثبيت المتطلبات
```bash
pip install -r requirements.txt
```

### 3. إعداد البيئة
```bash
cp .env.example .env
# عدّل ملف .env وأضف:
# - اسم شركتك
# - الرقم الضريبي
# - مفتاح OpenAI API (اختياري — للمساعد الذكي)
```

### 4. تهيئة قاعدة البيانات
```bash
python -m erp_accounting.main --seed
```

### 5. تشغيل التطبيق
```bash
python -m erp_accounting.main
```

### بيانات الدخول الافتراضية
- **اسم المستخدم**: `admin`
- **كلمة المرور**: `Admin@123`

⚠️ **غيّر كلمة المرور فور أول تسجيل دخول!**

---

## تثبيت OpenAI (للمساعد الذكي) — اختياري

### 1. احصل على مفتاح API
- اذهب إلى: https://platform.openai.com/api-keys
- أنشئ مفتاحًا جديدًا

### 2. أضف المفتاح في .env
```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
```

### 3. أعد تشغيل التطبيق
المساعد الذكي سيكون متاحًا في القائمة الجانبية.

---

## تثبيت OCR (لاستخراج بيانات الفواتير) — اختياري

### 1. ثبّت Tesseract OCR

**Windows:**
- حمّل من: https://github.com/UB-Mannheim/tesseract/wiki
- ثبّت مع دعم العربية

**Linux (Ubuntu):**
```bash
sudo apt install tesseract-ocr tesseract-ocr-ara
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

### 2. ثبّت Python package
```bash
pip install pytesseract Pillow
```

---

## تثبيت LLM محلي (بديل OpenAI) — اختياري

### 1. ثبّت Ollama
- اذهب إلى: https://ollama.ai
- حمّل وثبّت

### 2. حمّل نموذج
```bash
ollama pull llama3:8b
# أو نموذج أصغر:
ollama pull qwen:7b
```

### 3. أضف في .env
```env
LOCAL_LLM_MODEL=llama3:8b
OLLAMA_HOST=http://localhost:11434
```

---

## بناء التطبيق التنفيذي

### 1. ثبّت PyInstaller
```bash
pip install pyinstaller
```

### 2. ابنِ التطبيق
```bash
./build.sh
# أو يدويًا:
pyinstaller erp_accounting.spec --noconfirm
```

### 3. النتيجة
- المجلد: `dist/ERP_Accounting/`
- الملف التنفيذي: `dist/ERP_Accounting/ERP_Accounting.exe` (ويندوز)

### 4. التوزيع
- اضغط مجلد `dist/ERP_Accounting/` في ملف ZIP
- وزّعه على المستخدمين

---

## تشغيل الاختبارات

```bash
# كل الاختبارات
pytest

# مع تقرير التغطية
pytest --cov=erp_accounting --cov-report=html

# اختبارات محددة
pytest tests/unit/test_journal.py -v
```

---

## قاعدة البيانات

### النسخ الاحتياطي
- من التطبيق: الإعدادات → النسخ الاحتياطي → إنشاء نسخة
- يدويًا: انسخ ملف `erp_accounting.db`

### الترقية إلى PostgreSQL
1. عدّل `.env`:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/erp_accounting
```
2. ثبّت psycopg2:
```bash
pip install psycopg2-binary
```
3. شغّل migrations:
```bash
alembic upgrade head
```

---

## استكشاف الأخطاء

### المشكلة: التطبيق لا يبدأ
**الحل**: تأكد من تثبيت كل المتطلبات
```bash
pip install -r requirements.txt
```

### المشكلة: خطأ في قاعدة البيانات
**الحل**: أعد التهيئة
```bash
rm erp_accounting.db
python -m erp_accounting.main --seed
```

### المشكلة: المساعد الذكي لا يعمل
**الحل**: تأكد من مفتاح OpenAI في `.env`
```bash
cat .env | grep OPENAI
```

### المشكلة: الخطوط العربية لا تظهر
**الحل**: ثبّت خطوط Noto Sans Arabic
```bash
# Linux:
sudo apt install fonts-noto
# macOS:
brew install --cask font-noto-sans-arabic
```

---

## الدعم

- الوثائق: `AUDIT_REPORT_v3.md`
- الكود المصدري: https://github.com/your-repo
- البريد الإلكتروني: support@your-company.com

---

© 2026 ERP Accounting System. جميع الحقوق محفوظة.
