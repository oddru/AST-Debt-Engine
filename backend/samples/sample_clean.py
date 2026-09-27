"""Clean, modular Python sample demonstrating high maintainability and low complexity."""

from typing import List, Dict


def calculate_discount(price: float, rate: float) -> float:
    """Calculates discounted price cleanly."""
    if rate <= 0.0:
        return price
    return round(price * (1.0 - rate), 2)


def filter_active_users(users: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Filters active user records with straightforward comprehension."""
    return [u for u in users if u.get("status") == "active"]


def format_user_summary(user_id: str, email: str) -> str:
    """Formats brief user string representation."""
    return f"User[{user_id}] <{email}>"
