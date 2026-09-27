"""Legacy code sample demonstrating high complexity, deep nesting, parameter bloat, dead code, and duplicate subtrees."""

from typing import Any, Dict, List, Optional


# 1. Parameter Bloat: 7 parameters (> 5 threshold)
def process_order_transaction(
    user_id: str,
    order_id: str,
    amount: float,
    currency: str,
    tax_rate: float,
    discount_code: str,
    apply_shipping_fee: bool,
) -> Dict[str, Any]:
    """Processes financial order transaction with excessive parameters."""
    total = amount * (1.0 + tax_rate)
    return {"order_id": order_id, "user_id": user_id, "total": total}


# 2. High Cyclomatic Complexity (v(G) > 10) & 3. Deep Nesting (> 4 levels)
def evaluate_customer_tier(customer: Dict[str, Any], purchase_history: List[Dict[str, Any]]) -> str:
    """Complex nested business logic for evaluating customer loyalty tier."""
    tier = "Bronze"

    if customer.get("is_active"):
        if customer.get("is_verified"):
            for order in purchase_history:
                if order.get("status") == "COMPLETED":
                    # Level 5 nesting: If -> If -> For -> If -> If
                    if order.get("amount", 0) > 1000:
                        tier = "Platinum"
                    elif order.get("amount", 0) > 500:
                        tier = "Gold"
                    else:
                        tier = "Silver"
                elif order.get("status") == "PENDING":
                    if order.get("amount", 0) > 200:
                        tier = "Silver"
                elif order.get("status") == "REFUNDED":
                    tier = "Bronze"
    elif customer.get("is_vip"):
        tier = "VIP"
    else:
        tier = "Standard"

    return tier


# 4. Dead Code / Unreachable Subtree
def calculate_shipping_estimator(distance: float, weight: float) -> float:
    """Calculates shipping estimate, followed by unreachable dead statements."""
    base_rate = 5.0
    if distance > 100:
        return base_rate + (distance * 0.1) + (weight * 0.5)
    else:
        return base_rate + (weight * 0.2)

    # UNREACHABLE DEAD CODE:
    debug_log = "Shipping estimate calculation finished"
    unused_cache_ttl = 3600
    print(debug_log)


# 5. Duplicate Subtrees: Identical structural validation blocks
def validate_shipping_payload(payload: Dict[str, Any]) -> bool:
    if "destination" in payload:
        target_dest = payload["destination"]
        if isinstance(target_dest, dict) and "zip_code" in target_dest:
            if len(str(target_dest["zip_code"])) == 5:
                return True
    return False


def validate_billing_payload(payload: Dict[str, Any]) -> bool:
    # Isomorphic AST duplicate clone of validate_shipping_payload
    if "destination" in payload:
        target_dest = payload["destination"]
        if isinstance(target_dest, dict) and "zip_code" in target_dest:
            if len(str(target_dest["zip_code"])) == 5:
                return True
    return False
