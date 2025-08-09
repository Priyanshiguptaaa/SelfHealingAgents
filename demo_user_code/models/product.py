"""Product models for the e-commerce system"""
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Product:
    """E-commerce product model"""
    sku: str
    name: str
    category: str
    price: float
    inventory: int
    is_clearance: bool = False
    return_policy: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "sku": self.sku,
            "name": self.name,
            "category": self.category,
            "price": self.price,
            "inventory": self.inventory,
            "is_clearance": self.is_clearance,
            "return_policy": self.return_policy
        }
    
    @classmethod
    def from_catalog_data(cls, data: Dict[str, Any]) -> 'Product':
        """Create product from external catalog data"""
        return cls(
            sku=data.get("sku", ""),
            name=data.get("name", ""),
            category=data.get("category", ""),
            price=data.get("price", 0.0),
            inventory=data.get("inventory", 0),
            is_clearance=data.get("is_clearance", False),
            return_policy=data.get("return_policy")
        ) 