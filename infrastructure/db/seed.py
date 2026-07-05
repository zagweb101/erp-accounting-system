"""
Seed data - بيانات افتراضية أولية

يُنشئ:
- مستخدم admin افتراضي (admin / Admin@123)
- دليل حسابات SOCPA القياسي
"""
from __future__ import annotations

import asyncio
from decimal import Decimal
from uuid import uuid4

from domain.entities.account import Account
from domain.entities.user import User, UserStatus
from domain.value_objects.value_objects import AccountCode, AccountType, UserRole
from infrastructure.db.session import init_db, session_scope
from infrastructure.db.models.user_model import UserModel
from infrastructure.db.models.account_model import AccountModel
from use_cases.auth.auth_use_cases import PasswordHasher


# ============================================================
# Default admin user
# ============================================================
DEFAULT_ADMIN = {
    "username": "admin",
    "password": "Admin@123",
    "email": "admin@company.com",
    "full_name": "مدير النظام",
    "role": UserRole.ADMIN,
}


# ============================================================
# Default Chart of Accounts (SOCPA-aligned)
# ============================================================
DEFAULT_ACCOUNTS = [
    # (code, name, name_en, type, parent_code, is_posting)
    # Level 1: Main categories
    ("1", "الأصول", "Assets", "ASSET", None, False),
    ("2", "الخصوم", "Liabilities", "LIABILITY", None, False),
    ("3", "حقوق الملكية", "Equity", "EQUITY", None, False),
    ("4", "الإيرادات", "Revenue", "REVENUE", None, False),
    ("5", "المصروفات", "Expenses", "EXPENSE", None, False),

    # Level 2: Asset subcategories
    ("11", "الأصول المتداولة", "Current Assets", "ASSET", "1", False),
    ("12", "الأصول الثابتة", "Fixed Assets", "ASSET", "1", False),

    # Level 3: Asset detail accounts
    ("1101", "الصندوق", "Cash on Hand", "ASSET", "11", True),
    ("1102", "البنك - الحساب الجاري", "Bank - Current Account", "ASSET", "11", True),
    ("1103", "ذمم العملاء", "Accounts Receivable", "ASSET", "11", True),
    ("1104", "المخزون", "Inventory", "ASSET", "11", True),
    ("1105", "ضريبة القيمة المضافة - المدخلات", "VAT Input", "ASSET", "11", True),
    ("1201", "أراضٍ", "Land", "ASSET", "12", True),
    ("1202", "مباني", "Buildings", "ASSET", "12", True),
    ("1203", "سيارات", "Vehicles", "ASSET", "12", True),
    ("1204", "أجهزة ومعدات", "Equipment", "ASSET", "12", True),

    # Level 2: Liability subcategories
    ("21", "الخصوم المتداولة", "Current Liabilities", "LIABILITY", "2", False),
    ("22", "الخصوم طويلة الأجل", "Long-term Liabilities", "LIABILITY", "2", False),

    # Level 3: Liability detail accounts
    ("2101", "ذمم الموردين", "Accounts Payable", "LIABILITY", "21", True),
    ("2102", "ضريبة القيمة المضافة - المستحقة", "VAT Output", "LIABILITY", "21", True),
    ("2103", "رواتب مستحقة", "Salaries Payable", "LIABILITY", "21", True),
    ("2201", "قروض طويلة الأجل", "Long-term Loans", "LIABILITY", "22", True),

    # Level 2: Equity
    ("31", "رأس المال", "Capital", "EQUITY", "3", False),
    ("32", "الأرباح المحتجزة", "Retained Earnings", "EQUITY", "3", False),

    # Level 3: Equity detail
    ("3101", "رأس المال المدفوع", "Paid-in Capital", "EQUITY", "31", True),
    ("3102", "الأرباح المحتجزة", "Retained Earnings", "EQUITY", "32", True),

    # Level 2: Revenue
    ("41", "إيرادات التشغيل", "Operating Revenue", "REVENUE", "4", False),
    ("42", "إيرادات أخرى", "Other Revenue", "REVENUE", "4", False),

    # Level 3: Revenue detail
    ("4101", "إيرادات المبيعات", "Sales Revenue", "REVENUE", "41", True),
    ("4102", "إيرادات الخدمات", "Service Revenue", "REVENUE", "41", True),
    ("4201", "إيرادات الفوائد", "Interest Income", "REVENUE", "42", True),
    ("4202", "أرباح بيع أصول ثابتة", "Gain on Asset Sale", "REVENUE", "42", True),

    # Level 2: Expenses
    ("51", "تكلفة المبيعات", "Cost of Goods Sold", "EXPENSE", "5", False),
    ("52", "المصروفات الإدارية", "Administrative Expenses", "EXPENSE", "5", False),
    ("53", "المصروفات التشغيلية", "Operating Expenses", "EXPENSE", "5", False),

    # Level 3: Expense detail
    ("5101", "تكلفة البضاعة المباعة", "COGS", "EXPENSE", "51", True),
    ("5201", "رواتب وأجور", "Salaries & Wages", "EXPENSE", "52", True),
    ("5202", "إيجار", "Rent Expense", "EXPENSE", "52", True),
    ("5203", "كهرباء وماء", "Utilities", "EXPENSE", "52", True),
    ("5204", "مصروفات إدارية", "Admin Expenses", "EXPENSE", "52", True),
    ("5301", "مصروفات تسويق", "Marketing", "EXPENSE", "53", True),
    ("5302", "مصروفات صيانة", "Maintenance", "EXPENSE", "53", True),
    ("5303", "مصروفات شحن", "Shipping", "EXPENSE", "53", True),
]


def seed_admin_user() -> None:
    """إنشاء مستخدم admin افتراضي إن لم يوجد."""
    from sqlalchemy import select

    with session_scope() as session:
        # Check if admin already exists
        existing = session.execute(
            select(UserModel).where(UserModel.username == DEFAULT_ADMIN["username"])
        ).scalar_one_or_none()
        if existing is not None:
            print(f"  → Admin user already exists: {DEFAULT_ADMIN['username']}")
            return

        # Create admin
        admin = UserModel(
            id=str(uuid4()),
            username=DEFAULT_ADMIN["username"],
            email=DEFAULT_ADMIN["email"],
            password_hash=PasswordHasher.hash(DEFAULT_ADMIN["password"]),
            full_name=DEFAULT_ADMIN["full_name"],
            role=DEFAULT_ADMIN["role"].value,
            status=UserStatus.ACTIVE.value,
        )
        session.add(admin)
        print(f"  ✓ Created default admin: {DEFAULT_ADMIN['username']} / {DEFAULT_ADMIN['password']}")


def seed_chart_of_accounts() -> None:
    """إنشاء دليل الحسابات الافتراضي."""
    from sqlalchemy import select

    with session_scope() as session:
        # Check if any accounts exist
        existing_count = session.execute(select(AccountModel)).scalars().first()
        if existing_count is not None:
            print("  → Chart of accounts already exists, skipping")
            return

        # Build a code→id mapping
        code_to_id: dict[str, str] = {}

        # First pass: create all accounts (without parent_id)
        for code, name, name_en, acc_type, parent_code, is_posting in DEFAULT_ACCOUNTS:
            account_id = str(uuid4())
            code_to_id[code] = account_id
            account = AccountModel(
                id=account_id,
                code=code,
                name=name,
                name_en=name_en,
                account_type=acc_type,
                parent_id=None,  # Will update in second pass
                is_active=True,
                is_posting_account=is_posting,
                description="",
            )
            session.add(account)

        session.flush()

        # Second pass: update parent_id
        for code, name, name_en, acc_type, parent_code, is_posting in DEFAULT_ACCOUNTS:
            if parent_code and parent_code in code_to_id:
                account = session.execute(
                    select(AccountModel).where(AccountModel.code == code)
                ).scalar_one()
                account.parent_id = code_to_id[parent_code]

        print(f"  ✓ Created {len(DEFAULT_ACCOUNTS)} default accounts (SOCPA-aligned)")


def seed_all() -> None:
    """تشغيل كل عمليات الـ seed."""
    print("\n🌱 Seeding initial data...")
    init_db()
    seed_admin_user()
    seed_chart_of_accounts()
    print("✓ Seeding complete.\n")


if __name__ == "__main__":
    seed_all()
