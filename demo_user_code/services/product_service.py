"""Product service for e-commerce operations"""
import json
from typing import Dict, Any, Optional
from pathlib import Path

from models.product import Product
from services.catalog_sync import CatalogSync


class ProductService:
    """Service for product operations and return policy checks"""
    
    def __init__(self):
        self.catalog_sync = CatalogSync("https://external-catalog-api.com")
        self._load_product_data()
    
    def _load_product_data(self):
        """Load product data from data files"""
        data_path = Path(__file__).parent.parent.parent / "data"
        
        # Load current product state (after clearance updates)
        products_file = data_path / "products_after.jsonl"
        self.catalog_products = {}
        
        if products_file.exists():
            with open(products_file, 'r') as f:
                for line in f:
                    if line.strip():
                        product_data = json.loads(line)
                        # Add return policy based on clearance status
                        if product_data.get("is_clearance", False):
                            product_data["return_policy"] = "FINAL_SALE_NO_RETURNS"
                        else:
                            product_data["return_policy"] = "30_DAY_RETURN"
                        
                        self.catalog_products[product_data["sku"]] = product_data
    
    async def get_product(self, sku: str) -> Optional[Product]:
        """Get product with synced catalog data"""
        # This calls the buggy catalog sync
        synced_data = await self.catalog_sync.sync_product(sku)
        
        # Get full catalog data
        catalog_data = self.catalog_products.get(sku, {})
        
        # Merge synced data with catalog data
        # BUG: return_policy is missing from synced_data due to catalog sync bug
        product_data = {**catalog_data, **synced_data}
        
        return Product.from_catalog_data(product_data)
    
    async def check_return_eligibility(self, sku: str, order_id: str) -> Dict[str, Any]:
        """Check if a product can be returned - this is where the schema failure occurs"""
        product = await self.get_product(sku)
        
        if not product:
            return {
                "error": "Product not found",
                "sku": sku,
                "order_id": order_id
            }
        
        # Schema validation - expects return_policy field
        if not product.return_policy:
            # This triggers the schema validation failure!
            raise ValueError(f"Schema validation failed: return_policy missing for SKU {sku}")
        
        # Determine eligibility based on policy
        eligible = product.return_policy != "FINAL_SALE_NO_RETURNS"
        
        return {
            "sku": sku,
            "order_id": order_id,
            "eligible": eligible,
            "return_policy": product.return_policy,
            "reason": "Final sale item" if not eligible else "Standard return policy",
            "is_clearance": product.is_clearance
        } 