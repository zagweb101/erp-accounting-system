"""
اختبارات إضافية لرفع تغطية product_use_cases.py (من 54% إلى 80%+)
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infrastructure.db.session import session_scope
from infrastructure.db.models.user_model import UserModel
from infrastructure.db.seed import seed_admin_user, seed_chart_of_accounts

from adapters.repositories.sql_alchemy.user_repository import SqlAlchemyUserRepository
from adapters.repositories.sql_alchemy.product_repository import (
    SqlAlchemyProductRepository, SqlAlchemyInventoryRepository,
)
from use_cases.products.product_use_cases import (
    CreateProductUseCase, CreateProductRequest,
    UpdateProductUseCase, UpdateProductRequest,
    DeleteProductUseCase, GetProductUseCase,
    ListProductsUseCase, SearchProductsUseCase,
    GetProductBalanceUseCase, ListInventoryEntriesUseCase,
    GetLowStockProductsUseCase, AdjustInventoryUseCase,
)
from domain.entities.user import User, UserStatus
from domain.value_objects.value_objects import UserRole
from domain.exceptions.exceptions import (
    PermissionDeniedException, ValidationException,
)


@pytest.fixture
def repo():
    return SqlAlchemyProductRepository()


@pytest.fixture
def inventory_repo():
    return SqlAlchemyInventoryRepository()


@pytest.fixture
def admin_user():
    from sqlalchemy import select
    with session_scope() as s:
        m = s.execute(select(UserModel).where(UserModel.username == "admin")).scalar_one()
        return User(
            id=m.id, username=m.username, email=m.email, password_hash=m.password_hash,
            full_name=m.full_name, role=UserRole(m.role), status=UserStatus(m.status),
        )


class TestCreateProductValidation:
    """اختبارات التحقق من صحة بيانات المنتج."""

    @pytest.mark.asyncio
    async def test_create_product_empty_sku_fails(self, repo, admin_user):
        """SKU فارغ يفشل."""
        uc = CreateProductUseCase(repo)
        with pytest.raises(ValidationException, match="is required"):
            await uc.execute(
                CreateProductRequest(sku="", name="Test"),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_product_empty_name_fails(self, repo, admin_user):
        """اسم فارغ يفشل."""
        uc = CreateProductUseCase(repo)
        with pytest.raises(ValidationException, match="is required"):
            await uc.execute(
                CreateProductRequest(sku=f"P-{uuid4().hex[:8]}", name=""),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_product_negative_cost_fails(self, repo, admin_user):
        """سعر تكلفة سالب يفشل."""
        uc = CreateProductUseCase(repo)
        with pytest.raises(ValidationException, match="negative"):
            await uc.execute(
                CreateProductRequest(
                    sku=f"P-{uuid4().hex[:8]}", name="Test",
                    cost_price=Decimal("-100"),
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_product_negative_sale_price_fails(self, repo, admin_user):
        """سعر بيع سالب يفشل."""
        uc = CreateProductUseCase(repo)
        with pytest.raises(ValidationException, match="negative"):
            await uc.execute(
                CreateProductRequest(
                    sku=f"P-{uuid4().hex[:8]}", name="Test",
                    sale_price=Decimal("-50"),
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_product_invalid_tax_rate_fails(self, repo, admin_user):
        """نسبة ضريبة غير صالحة (أكبر من 100) تفشل."""
        uc = CreateProductUseCase(repo)
        with pytest.raises(ValidationException, match="0-100"):
            await uc.execute(
                CreateProductRequest(
                    sku=f"P-{uuid4().hex[:8]}", name="Test",
                    tax_rate=Decimal("150"),
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_product_negative_tax_rate_fails(self, repo, admin_user):
        """نسبة ضريبة سالبة تفشل."""
        uc = CreateProductUseCase(repo)
        with pytest.raises(ValidationException, match="0-100"):
            await uc.execute(
                CreateProductRequest(
                    sku=f"P-{uuid4().hex[:8]}", name="Test",
                    tax_rate=Decimal("-10"),
                ),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_create_product_duplicate_sku_fails(self, repo, admin_user):
        """SKU مكرر يفشل."""
        uc = CreateProductUseCase(repo)
        sku = f"DUP-{uuid4().hex[:8]}"
        await uc.execute(
            CreateProductRequest(sku=sku, name="Product 1"),
            current_user=admin_user,
        )
        with pytest.raises(ValidationException, match="already exists"):
            await uc.execute(
                CreateProductRequest(sku=sku, name="Product 2"),
                current_user=admin_user,
            )


class TestCreateProductPermissions:
    """اختبارات صلاحيات إنشاء المنتجات."""

    @pytest.mark.asyncio
    async def test_owner_cannot_create_product(self, repo, admin_user):
        """صاحب الشركة لا يمكنه إنشاء منتجات."""
        from use_cases.auth.auth_use_cases import CreateUserUseCase, CreateUserRequest
        create_user_uc = CreateUserUseCase(SqlAlchemyUserRepository())
        owner = await create_user_uc.execute(
            CreateUserRequest(
                username=f"owner_prod_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"op_{uuid4().hex[:8]}@test.com",
                full_name="Owner",
                role=UserRole.COMPANY_OWNER,
            ),
            current_user=admin_user,
        )
        uc = CreateProductUseCase(repo)
        with pytest.raises(PermissionDeniedException):
            await uc.execute(
                CreateProductRequest(sku=f"P-{uuid4().hex[:8]}", name="Test"),
                current_user=owner,
            )

    @pytest.mark.asyncio
    async def test_inventory_clerk_can_create_product(self, repo, admin_user):
        """موظف المخزون يمكنه إنشاء منتجات."""
        from use_cases.auth.auth_use_cases import CreateUserUseCase, CreateUserRequest
        create_user_uc = CreateUserUseCase(SqlAlchemyUserRepository())
        clerk = await create_user_uc.execute(
            CreateUserRequest(
                username=f"clerk_prod_{uuid4().hex[:8]}",
                password="Pass@123",
                email=f"cp_{uuid4().hex[:8]}@test.com",
                full_name="Clerk",
                role=UserRole.INVENTORY_CLERK,
            ),
            current_user=admin_user,
        )
        uc = CreateProductUseCase(repo)
        product = await uc.execute(
            CreateProductRequest(sku=f"P-CLK-{uuid4().hex[:8]}", name="By Clerk"),
            current_user=clerk,
        )
        assert product.name == "By Clerk"


class TestUpdateProduct:
    """اختبارات تحديث المنتجات."""

    @pytest.mark.asyncio
    async def test_update_product_name(self, repo, admin_user):
        """تحديث اسم المنتج."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"UPD-{uuid4().hex[:8]}", name="Original"),
            current_user=admin_user,
        )
        update_uc = UpdateProductUseCase(repo)
        updated = await update_uc.execute(
            UpdateProductRequest(product_id=product.id, name="Updated"),
            current_user=admin_user,
        )
        assert updated.name == "Updated"

    @pytest.mark.asyncio
    async def test_update_product_prices(self, repo, admin_user):
        """تحديث الأسعار."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(
                sku=f"PRC-{uuid4().hex[:8]}", name="Test",
                cost_price=Decimal("100"), sale_price=Decimal("150"),
            ),
            current_user=admin_user,
        )
        update_uc = UpdateProductUseCase(repo)
        updated = await update_uc.execute(
            UpdateProductRequest(
                product_id=product.id,
                cost_price=Decimal("120"),
                sale_price=Decimal("180"),
            ),
            current_user=admin_user,
        )
        assert updated.cost_price == Decimal("120")
        assert updated.sale_price == Decimal("180")

    @pytest.mark.asyncio
    async def test_update_product_negative_price_fails(self, repo, admin_user):
        """سعر سالب يفشل."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"NEG-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )
        update_uc = UpdateProductUseCase(repo)
        with pytest.raises(ValidationException, match="negative"):
            await update_uc.execute(
                UpdateProductRequest(product_id=product.id, cost_price=Decimal("-50")),
                current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_update_product_empty_name_fails(self, repo, admin_user):
        """اسم فارغ يفشل."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"EN-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )
        update_uc = UpdateProductUseCase(repo)
        with pytest.raises(ValidationException, match="cannot be empty"):
            await update_uc.execute(
                UpdateProductRequest(product_id=product.id, name=""),
                current_user=admin_user,
            )


class TestDeleteProduct:
    """اختبارات حذف المنتجات."""

    @pytest.mark.asyncio
    async def test_delete_product_success(self, repo, admin_user):
        """حذف منتج ينجح (soft delete)."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"DEL-{uuid4().hex[:8]}", name="To Delete"),
            current_user=admin_user,
        )
        delete_uc = DeleteProductUseCase(repo)
        result = await delete_uc.execute(product.id, current_user=admin_user)
        assert result is True
        # Verify soft delete
        fetched = await repo.get_by_id(product.id)
        assert fetched.is_active is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_product(self, repo, admin_user):
        """حذف منتج غير موجود يفشل."""
        delete_uc = DeleteProductUseCase(repo)
        from domain.exceptions.exceptions import ProductNotFoundException
        with pytest.raises(ProductNotFoundException):
            await delete_uc.execute(uuid4(), current_user=admin_user)


class TestGetAndListProducts:
    """اختبارات الحصول على وسرد المنتجات."""

    @pytest.mark.asyncio
    async def test_get_product_success(self, repo, admin_user):
        """الحصول على منتج موجود."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"GET-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )
        get_uc = GetProductUseCase(repo)
        fetched = await get_uc.execute(product.id, current_user=admin_user)
        assert fetched.id == product.id

    @pytest.mark.asyncio
    async def test_get_product_not_found(self, repo, admin_user):
        """الحصول على منتج غير موجود يفشل."""
        get_uc = GetProductUseCase(repo)
        from domain.exceptions.exceptions import ProductNotFoundException
        with pytest.raises(ProductNotFoundException):
            await get_uc.execute(uuid4(), current_user=admin_user)

    @pytest.mark.asyncio
    async def test_list_products(self, repo, admin_user):
        """سرد المنتجات."""
        create_uc = CreateProductUseCase(repo)
        for i in range(3):
            await create_uc.execute(
                CreateProductRequest(sku=f"LST-{i}-{uuid4().hex[:8]}", name=f"Product {i}"),
                current_user=admin_user,
            )
        list_uc = ListProductsUseCase(repo)
        products = await list_uc.execute(current_user=admin_user)
        assert len(products) >= 3

    @pytest.mark.asyncio
    async def test_search_products_short_query(self, repo, admin_user):
        """بحث بكلمة قصيرة يُعيد قائمة فارغة."""
        search_uc = SearchProductsUseCase(repo)
        results = await search_uc.execute("a", current_user=admin_user)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_products_success(self, repo, admin_user):
        """بحث ناجح."""
        create_uc = CreateProductUseCase(repo)
        await create_uc.execute(
            CreateProductRequest(sku=f"SRCH-{uuid4().hex[:8]}", name="لابتوب Dell"),
            current_user=admin_user,
        )
        search_uc = SearchProductsUseCase(repo)
        results = await search_uc.execute("Dell", current_user=admin_user)
        assert len(results) >= 1
        assert any("Dell" in p.name for p in results)


class TestInventoryUseCases:
    """اختبارات حالات استخدام المخزون."""

    @pytest.mark.asyncio
    async def test_get_balance_zero_initially(self, repo, inventory_repo, admin_user):
        """الرصيد الابتدائي صفر."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"BAL-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )
        get_balance_uc = GetProductBalanceUseCase(inventory_repo)
        balance = await get_balance_uc.execute(product.id, current_user=admin_user)
        assert balance == 0.0

    @pytest.mark.asyncio
    async def test_adjust_inventory_in(self, repo, inventory_repo, admin_user):
        """تسوية مخزون (وارد)."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"ADJ-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )
        adjust_uc = AdjustInventoryUseCase(repo, inventory_repo)
        entry = await adjust_uc.execute(
            product.id, Decimal("100"), "initial stock", current_user=admin_user,
        )
        assert entry.quantity_in == Decimal("100")

        # Verify balance
        get_balance_uc = GetProductBalanceUseCase(inventory_repo)
        balance = await get_balance_uc.execute(product.id, current_user=admin_user)
        assert balance == 100.0

    @pytest.mark.asyncio
    async def test_adjust_inventory_out(self, repo, inventory_repo, admin_user):
        """تسوية مخزون (صادر)."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"OUT-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )
        adjust_uc = AdjustInventoryUseCase(repo, inventory_repo)
        # Add 100 first
        await adjust_uc.execute(product.id, Decimal("100"), "initial", current_user=admin_user)
        # Remove 30
        entry = await adjust_uc.execute(product.id, Decimal("70"), "sale", current_user=admin_user)
        assert entry.quantity_out == Decimal("30")

        # Verify balance
        get_balance_uc = GetProductBalanceUseCase(inventory_repo)
        balance = await get_balance_uc.execute(product.id, current_user=admin_user)
        assert balance == 70.0

    @pytest.mark.asyncio
    async def test_adjust_inventory_negative_fails(self, repo, inventory_repo, admin_user):
        """تسوية لكمية سالبة تفشل."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"NEG-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )
        adjust_uc = AdjustInventoryUseCase(repo, inventory_repo)
        with pytest.raises(ValidationException, match="negative"):
            await adjust_uc.execute(
                product.id, Decimal("-10"), "test", current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_adjust_inventory_no_reason_fails(self, repo, inventory_repo, admin_user):
        """تسوية بدون سبب تفشل."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"NRS-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )
        adjust_uc = AdjustInventoryUseCase(repo, inventory_repo)
        with pytest.raises(ValidationException, match="is required"):
            await adjust_uc.execute(
                product.id, Decimal("50"), "", current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_adjust_inventory_no_change_fails(self, repo, inventory_repo, admin_user):
        """تسوية لنفس الكمية تفشل (لا تغيير)."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"NC-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )
        adjust_uc = AdjustInventoryUseCase(repo, inventory_repo)
        with pytest.raises(ValidationException, match="no change"):
            await adjust_uc.execute(
                product.id, Decimal("0"), "no change", current_user=admin_user,
            )

    @pytest.mark.asyncio
    async def test_list_inventory_entries(self, repo, inventory_repo, admin_user):
        """سرد حركات المخزون."""
        create_uc = CreateProductUseCase(repo)
        product = await create_uc.execute(
            CreateProductRequest(sku=f"LIE-{uuid4().hex[:8]}", name="Test"),
            current_user=admin_user,
        )
        adjust_uc = AdjustInventoryUseCase(repo, inventory_repo)
        await adjust_uc.execute(product.id, Decimal("50"), "first", current_user=admin_user)
        await adjust_uc.execute(product.id, Decimal("30"), "second", current_user=admin_user)

        list_uc = ListInventoryEntriesUseCase(inventory_repo)
        entries = await list_uc.execute(product.id, current_user=admin_user)
        assert len(entries) >= 2

    @pytest.mark.asyncio
    async def test_get_low_stock_products(self, repo, inventory_repo, admin_user):
        """الحصول على منتجات تحت الحد الأدنى."""
        create_uc = CreateProductUseCase(repo)
        # Create product with min_stock_level = 10, but no inventory
        await create_uc.execute(
            CreateProductRequest(
                sku=f"LOW-{uuid4().hex[:8]}", name="Low Stock Product",
                min_stock_level=Decimal("10"),
            ),
            current_user=admin_user,
        )
        get_low_uc = GetLowStockProductsUseCase(inventory_repo)
        low_products = await get_low_uc.execute(current_user=admin_user)
        # Should return at least 1 product (our new one)
        assert len(low_products) >= 1
        # Each item is (product, balance) tuple
        # Product may be ProductModel or Product entity - check name attribute
        for item in low_products:
            product = item[0] if isinstance(item, tuple) else item
            assert hasattr(product, "name")


class TestProductBarcode:
    """اختبارات الباركود."""

    @pytest.mark.asyncio
    async def test_get_by_barcode(self, repo, admin_user):
        """الحصول على منتج بالباركود."""
        create_uc = CreateProductUseCase(repo)
        barcode = f"BC{uuid4().hex[:10]}"
        await create_uc.execute(
            CreateProductRequest(
                sku=f"BC-{uuid4().hex[:8]}", name="Test",
                barcode=barcode,
            ),
            current_user=admin_user,
        )
        product = await repo.get_by_barcode(barcode)
        assert product is not None
        assert product.barcode == barcode

    @pytest.mark.asyncio
    async def test_get_by_nonexistent_barcode(self, repo):
        """باركود غير موجود يُعيد None."""
        result = await repo.get_by_barcode("NONEXISTENT_BARCODE_XYZ")
        assert result is None
