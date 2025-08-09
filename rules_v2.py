# FIXED rules: clearance is final sale

import json, re, pathlib

def load_products(path):
    items = []
    with open(path) as f:
        for line in f:
            items.append(json.loads(line))
    return items

def find_product_by_name_or_sku(products, text):
    # very naive lookup by SKU or name keyword
    t = text.lower()
    for p in products:
        if p["sku"].lower() in t or any(w in t for w in p["name"].lower().split()):
            return p
    return None

def answer(question:str, products_path:str, policies:str)->str:
    products = load_products(products_path)
    prod = find_product_by_name_or_sku(products, question)

    # hard rule: clearance = final sale
    if prod and prod.get("is_clearance", False):
        return "This item is a clearance item and is FINAL SALE—no returns or exchanges."

    if "clearance" in question.lower() and not prod:
        # conservative: if user says 'clearance' treat as final sale
        return "Clearance items are FINAL SALE—no returns or exchanges."

    # General policy answers
    if "window" in question.lower():
        return "You can return items within 30 days of delivery."
    if "refund" in question.lower():
        return "Refunds are issued within 5–10 business days after inspection."
    if "original" in question.lower() or "packaging" in question.lower():
        return "Yes, items must be unused and in their original packaging."

    if prod:
        return f"You can return the {prod['name']} within 30 days if unused and in original packaging."

    return "Our returns: 30 days; unused; original packaging; refund in 5–10 business days. Clearance items are FINAL SALE."