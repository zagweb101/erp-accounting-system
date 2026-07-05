"""
Product & Inventory Use Cases
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
from uuid import UUID

from domain.entities.product import InventoryEntry, Product
from domain.exceptions.exceptions import (
    InsufficientStockException,
    PermissionDeniedException,
    ValidationException,
)
from domain.value_objects.value_objects import Permission
from use_cases.repositories.interfaces import IInventoryRepository, IProductRepository


# ============================================================
# Product DTOs
# ============================================================
@dataclass
class CreateProductRequest:
    sku: str
    name: str
    name_en: str = ""
    barcode: str = ""
    description: str = ""
    category: str = ""
    unit: str = "piece"
    cost_price: Decimal = Decimal("0")
    sale_price: Decimal = Decimal("0")
    tax_rate: Decimal = Decimal("15")
    min_stock_level: Decimal = Decimal("0")


@dataclass
class UpdateProductRequest:
    product_id: UUID
    name: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    cost_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    tax_rate: Optional[Decimal] = None
    min_stock_level: Optional[Decimal] = None


# ============================================================
# Product Use Cases
# ============================================================
class CreateProductUseCase:
    def __init__(self, product_repo: IProductRepository) -> None:
        self._repo = product_repo

    async def execute(self, request: CreateProductRequest, current_user) -> Product:
        if not current_user.has_permission(Permission.PRODUCT_CREATE):
            raise PermissionDeniedException("product.create")
        if not request.sku:
            raise ValidationException("sku", "is required")
        if not request.name:
            raise ValidationException("name", "is required")
        if request.cost_price < 0:
            raise ValidationException("cost_price", "cannot be negative")
        if request.sale_price < 0:
            raise ValidationException("sale_price", "cannot be negative")
        if not (0 <= request.tax_rate <= 100):
            raise ValidationException("tax_rate", "must be 0-100")

        existing = await self._repo.get_by_sku(request.sku)
        if existing is not None:
            raise ValidationException("sku", f"already exists: {request.sku}")

        product = Product(
            sku=request.sku,
            barcode=request.barcode,
            name=request.name,
            name_en=request.name_en,
            description=request.description,
            category=request.category,
            unit=request.unit,
            cost_price=request.cost_price,
            sale_price=request.sale_price,
            tax_rate=request.tax_rate,
            min_stock_level=request.min_stock_level,
            is_active=True,
        )
        return await self._repo.save(product)


class UpdateProductUseCase:
    def __init__(self, product_repo: IProductRepository) -> None:
        self._repo = product_repo

    async def execute(self, request: UpdateProductRequest, current_user) -> Product:
        if not current_user.has_permission(Permission.PRODUCT_UPDATE):
            raise PermissionDeniedException("product.update")

        from domain.exceptions.exceptions import ProductNotFoundException
        product = await self._repo.get_by_id(request.product_id)
        if product is None:
            raise ProductNotFoundException(str(request.product_id))  # type: ignore

        if request.name is not None:
            if not request.name:
                raise ValidationException("name", "cannot be empty")
            product.name = request.name
        if request.barcode is not None:
            product.barcode = request.barcode
        if request.description is not None:
            product.description = request.description
        if request.category is not None:
            product.category = request.category
        if request.cost_price is not None:
            if request.cost_price < 0:
                raise ValidationException("cost_price", "cannot be negative")
            product.cost_price = request.cost_price
        if request.sale_price is not None:
            if request.sale_price < 0:
                raise ValidationException("sale_price", "cannot be negative")
            product.sale_price = request.sale_price
        if request.tax_rate is not None:
            if not (0 <= request.tax_rate <= 100):
                raise ValidationException("tax_rate", "must be 0-100")
            product.tax_rate = request.tax_rate
        if request.min_stock_level is not None:
            product.min_stock_level = request.min_stock_level

        from datetime import datetime
        product.updated_at = datetime.now()
        return await self._repo.save(product)


class DeleteProductUseCase:
    def __init__(self, product_repo: IProductRepository) -> None:
        self._repo = product_repo

    async def execute(self, product_id: UUID, current_user) -> bool:
        if not current_user.has_permission(Permission.PRODUCT_DELETE):
            raise PermissionDeniedException("product.delete")
        from domain.exceptions.exceptions import ProductNotFoundException
        product = await self._repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundException(str(product_id))  # type: ignore
        product.is_active = False
        from datetime import datetime
        product.updated_at = datetime.now()
        await self._repo.save(product)
        return True


class GetProductUseCase:
    def __init__(self, product_repo: IProductRepository) -> None:
        self._repo = product_repo

    async def execute(self, product_id: UUID, current_user) -> Product:
        if not current_user.has_permission(Permission.PRODUCT_VIEW):
            raise PermissionDeniedException("product.view")
        from domain.exceptions.exceptions import ProductNotFoundException
        product = await self._repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundException(str(product_id))  # type: ignore
        return product


class ListProductsUseCase:
    def __init__(self, product_repo: IProductRepository) -> None:
        self._repo = product_repo

    async def execute(self, current_user, skip: int = 0, limit: int = 100) -> list[Product]:
        if not current_user.has_permission(Permission.PRODUCT_VIEW):
            raise PermissionDeniedException("product.view")
        return await self._repo.list_all(skip=skip, limit=limit)


class SearchProductsUseCase:
    def __init__(self, product_repo: IProductRepository) -> None:
        self._repo = product_repo

    async def execute(self, query: str, current_user, limit: int = 10) -> list[Product]:
        if not current_user.has_permission(Permission.PRODUCT_VIEW):
            raise PermissionDeniedException("product.view")
        if not query or len(query) < 2:
            return []
        return await self._repo.search(query, limit=limit)


# ============================================================
# Inventory Use Cases
# ============================================================
class GetProductBalanceUseCase:
    """الحصول على رصيد مخزون منتج."""

    def __init__(self, inventory_repo: IInventoryRepository) -> None:
        self._repo = inventory_repo

    async def execute(self, product_id: UUID, current_user) -> float:
        if not current_user.has_permission(Permission.PRODUCT_VIEW):
            raise PermissionDeniedException("product.view")
        return await self._repo.get_balance(product_id)


class ListInventoryEntriesUseCase:
    """عرض سجل حركة مخزون منتج."""

    def __init__(self, inventory_repo: IInventoryRepository) -> None:
        self._repo = inventory_repo

    async def execute(
        self, product_id: UUID, current_user, skip: int = 0, limit: int = 100
    ) -> list[InventoryEntry]:
        if not current_user.has_permission(Permission.PRODUCT_VIEW):
            raise PermissionDeniedException("product.view")
        return await self._repo.list_entries(product_id, skip=skip, limit=limit)


class GetLowStockProductsUseCase:
    """المنتجات تحت الحد الأدنى - للتنبيهات."""

    def __init__(self, inventory_repo: IInventoryRepository) -> None:
        self._repo = inventory_repo

    async def execute(self, current_user) -> list[tuple]:
        if not current_user.has_permission(Permission.PRODUCT_VIEW):
            raise PermissionDeniedException("product.view")
        return await self._repo.get_low_stock_products()


class AdjustInventoryUseCase:
    """تسوية مخزون (يدوي - لجرد أو تالف)."""

    def __init__(
        self,
        product_repo: IProductRepository,
        inventory_repo: IInventoryRepository,
    ) -> None:
        self._product_repo = product_repo
        self._inventory_repo = inventory_repo

    async def execute(
        self,
        product_id: UUID,
        new_quantity: Decimal,
        reason: str,
        current_user,
    ) -> InventoryEntry:
        if not current_user.has_permission(Permission.PRODUCT_UPDATE):
            raise PermissionDeniedException("product.update")
        if new_quantity < 0:
            raise ValidationException("new_quantity", "cannot be negative")
        if not reason:
            raise ValidationException("reason", "is required for inventory adjustment")

        from domain.exceptions.exceptions import ProductNotFoundException
        product = await self._product_repo.get_by_id(product_id)
        if product is None:
            raise ProductNotFoundException(str(product_id))  # type: ignore

        current_balance = await self._inventory_repo.get_balance(product_id)
        current_balance_dec = Decimal(str(current_balance))
        diff = new_quantity - current_balance_dec

        if diff > 0:
            entry = InventoryEntry(
                product_id=product_id,
                quantity_in=diff,
                reference_type="adjustment",
                unit_cost=product.cost_price,
                balance_after=new_quantity,
                created_by=current_user.id,
            )
        elif diff < 0:
            entry = InventoryEntry(
                product_id=product_id,
                quantity_out=abs(diff),
                reference_type="adjustment",
                unit_cost=product.cost_price,
                balance_after=new_quantity,
                created_by=current_user.id,
            )
        else:
            raise ValidationException("new_quantity", "no change needed")
        return await self._inventory_repo.add_entry(entry)
