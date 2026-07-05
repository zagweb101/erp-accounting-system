"""SQLAlchemy Inventory model re-export (already in product_model.py)."""
# Inventory is defined in product_model.py (InventoryEntryModel)
# This file is just for explicit module organization
from infrastructure.db.models.product_model import InventoryEntryModel

__all__ = ["InventoryEntryModel"]
