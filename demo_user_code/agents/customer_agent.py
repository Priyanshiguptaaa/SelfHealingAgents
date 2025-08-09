"""Customer agent that simulates customer actions in the e-commerce system"""
import asyncio
import random
from datetime import datetime
from typing import Dict, Any

from agents.catalog_agent import catalog_agent


class CustomerAgent:
    """Autonomous agent that simulates customer behavior and actions"""
    
    def __init__(self):
        self.active = False
        self.customer_sessions = {}
    
    async def start(self):
        """Start the customer agent"""
        self.active = True
        print("👤 Customer Agent started - simulating customer behavior")
    
    async def stop(self):
        """Stop the customer agent"""
        self.active = False
        print("👤 Customer Agent stopped")
    
    async def simulate_return_request(self, sku: str, order_id: str) -> Dict[str, Any]:
        """Customer agent initiates a return request"""
        print(f"👤 Customer requesting return for {sku}, order {order_id}")
        
        try:
            # Customer agent calls the catalog agent
            result = await catalog_agent.process_return_request(sku, order_id)
            
            if result["status"] == "success":
                if result["eligible"]:
                    print(f"👤 Customer happy: Return approved for {sku}")
                else:
                    print(f"👤 Customer informed: {result['reason']} for {sku}")
            
            return result
            
        except Exception as e:
            # Customer experiences an error - this triggers the healing
            print(f"👤 Customer frustrated: Return system failed - {e}")
            return {
                "status": "error",
                "error": str(e),
                "sku": sku,
                "order_id": order_id,
                "customer_impact": "Unable to process return request"
            }
    
    async def simulate_customer_journey(self):
        """Simulate a realistic customer journey"""
        if not self.active:
            return
        
        # Simulate different customer scenarios
        scenarios = [
            {"sku": "SKU-1001", "order_id": "ORD-001", "type": "clearance_return"},
            {"sku": "SKU-1002", "order_id": "ORD-002", "type": "regular_return"},
            {"sku": "SKU-1003", "order_id": "ORD-003", "type": "clearance_return"},
        ]
        
        scenario = random.choice(scenarios)
        print(f"👤 Customer journey: {scenario['type']}")
        
        # Add realistic delay
        await asyncio.sleep(random.uniform(1, 3))
        
        return await self.simulate_return_request(
            scenario["sku"], 
            scenario["order_id"]
        )


# Global customer agent instance  
customer_agent = CustomerAgent() 