; ═════════════════════════════════════════════════════
; ERP Accounting System — Inno Setup Installer Script
; ═════════════════════════════════════════════════════
; ينشئ مثبّت احترافي (Setup.exe) للتوزيع التجاري
;
; الاستخدام:
;   1. ثبّت Inno Setup: https://jrsoftware.org/isdl.php
;   2. شغّل build.sh أولاً لإنشاء dist/ERP_Accounting/
;   3. افتح هذا الملف في Inno Setup Compiler
;   4. اضغط Ctrl+F9 للبناء
;   5. النتيجة: installer_output/ERP_Accounting_Setup.exe
; ═════════════════════════════════════════════════════

[Setup]
AppName=ERP Accounting System
AppVersion=10.0.0
AppPublisher=Your Company
AppPublisherURL=https://your-company.com
AppSupportURL=https://your-company.com/support
AppComments=نظام ERP محاسبي متكامل يعتمد القيد المزدوج

; مسار التثبيت الافتراضي
DefaultDirName={pf}\ERP_Accounting
DefaultGroupName=ERP Accounting

; لا_require إدخال معلومات المستخدم
DisableProgramGroupPage=yes
PrivilegesRequired=admin

; الإخراج
OutputDir=installer_output
OutputBaseFilename=ERP_Accounting_Setup_v10
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64

; الواجهة
WizardStyle=modern
ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage

; الأيقونة (أضف ملف .ico في مجلد المشروع)
; SetupIconFile=app_icon.ico

; إلغاء التثبيت
UninstallDisplayIcon={app}\ERP_Accounting.exe

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "إنشاء اختصار على سطح المكتب"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
Name: "quicklaunchicon"; Description: "إنشاء اختصار في شريط المهام"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
; كل ملفات التطبيق
Source: "dist\ERP_Accounting\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

; ملف .env.example (يُنسخ إن لم يوجد)
Source: ".env.example"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
; اختصار في قائمة ابدأ
Name: "{group}\ERP Accounting"; Filename: "{app}\ERP_Accounting.exe"

; اختصار على سطح المكتب (اختياري)
Name: "{commondesktop}\ERP Accounting"; Filename: "{app}\ERP_Accounting.exe"; Tasks: desktopicon

; اختصار في شريط المهام (اختياري)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar\ERP Accounting"; Filename: "{app}\ERP_Accounting.exe"; Tasks: quicklaunchicon

[Run]
; تشغيل التطبيق بعد التثبيت
Filename: "{app}\ERP_Accounting.exe"; Description: "تشغيل ERP Accounting الآن"; Flags: nowait postinstall skipifsilent

; فتح ملف .env للتعديل
Filename: "notepad.exe"; Parameters: "{app}\.env"; Description: "تعديل الإعدادات"; Flags: postinstall nowait skipifsilent unchecked

[UninstallDelete]
; حذف قاعدة البيانات عند إلغاء التثبيت (اختياري)
; Type: files; Name: "{app}\erp_accounting.db"
; Type: filesandordirs; Name: "{app}\backups"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

function NeedRestart(): Boolean;
begin
  Result := False;
end;
