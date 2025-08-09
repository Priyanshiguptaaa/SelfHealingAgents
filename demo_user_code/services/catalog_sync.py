#!/usr/bin/env python3
"""Catalog synchronization service"""

from typing import Dict, Any

# Fields to sync from catalog
POLICY_FIELDS = ["price", "inventory", "category"]

class CatalogSync:
    def __init__(self, api_url: str):
        self.api_url = api_url
    
    async def sync_product(self, sku: str) -> Dict[str, Any]:
        """Sync a single product from catalog"""
        response = await self._fetch_product_data(sku)
        
        # Extract only the configured fields
        product_data = {}
        for field in POLICY_FIELDS:
            if field in response:
                product_data[field] = response[field]
        
        return product_data
    
    async def _fetch_product_data(self, sku: str) -> Dict[str, Any]:
        """Fetch product data from external catalog API"""
        # Simulate API call - this represents the external catalog
        catalog_data = {
            "SKU-1001": {
                "sku": "SKU-1001",
                "name": "Everyday Tee", 
                "category": "tops",
                "price": 18.0,
                "inventory": 25,
                "is_clearance": True,
                "return_policy": "FINAL_SALE_NO_RETURNS"
            },
            "SKU-1002": {
                "sku": "SKU-1002",
                "name": "Linen Pants",
                "category": "bottoms", 
                "price": 59.0,
                "inventory": 15,
                "is_clearance": False,
                "return_policy": "30_DAY_RETURN"
            },
            "SKU-1003": {
                "sku": "SKU-1003",
                "name": "Weekend Hoodie",
                "category": "tops",
                "price": 35.0, 
                "inventory": 8,
                "is_clearance": True,
                "return_policy": "FINAL_SALE_NO_RETURNS"
            }
        }
        
        return catalog_data.get(sku, {
            "sku": sku,
            "price": 29.99,
            "inventory": 100,
            "category": "electronics",
            "return_policy": "30_DAY_RETURN"
        }) 