from __future__ import annotations

import json
from typing import Any

from ..models import acr_store


async def _is_admin(user: dict, config: dict) -> bool:
    if not config.get("admin_bypass", True):
        return False
    admin_roles = config.get("admin_roles", ["admin"])
    user_roles = user.get("roles", [])
    return bool(set(admin_roles) & set(user_roles))


async def resolve_user_attribute(user: dict, ref: str) -> Any:
    """Resolve a user attribute reference like 'user:user_id' or 'user:groups'."""
    if ref.startswith("user:"):
        attr = ref[5:]
        if attr == "user_id":
            return user["id"]
        if attr in ("username", "email", "full_name"):
            return user.get(attr)
        if attr in ("roles", "groups"):
            return user.get(attr, [])
        if attr.startswith("custom:"):
            custom_key = attr[7:]
            return user.get("custom_attributes", {}).get(custom_key)
    return ref


def build_operator_sql(field: str, operator: str, value: Any, param_idx: int) -> tuple[str, list]:
    """Build a SQL condition fragment and parameters."""
    if operator == "eq":
        return f"{field} = ${param_idx}", [value]
    elif operator == "ne":
        return f"{field} != ${param_idx}", [value]
    elif operator == "in":
        if isinstance(value, list) and value:
            placeholders = ", ".join(f"${param_idx + i}" for i in range(len(value)))
            return f"{field} IN ({placeholders})", list(value)
        return "FALSE", []
    elif operator == "not_in":
        if isinstance(value, list) and value:
            placeholders = ", ".join(f"${param_idx + i}" for i in range(len(value)))
            return f"{field} NOT IN ({placeholders})", list(value)
        return "TRUE", []
    elif operator == "intersects":
        if isinstance(value, list) and value:
            placeholders = ", ".join(f"${param_idx + i}" for i in range(len(value)))
            return f"{field} && ARRAY[{placeholders}]", list(value)
        return "FALSE", []
    elif operator == "contains":
        return f"${param_idx} = ANY({field})", [value]
    elif operator == "gt":
        return f"{field} > ${param_idx}", [value]
    elif operator == "gte":
        return f"{field} >= ${param_idx}", [value]
    elif operator == "lt":
        return f"{field} < ${param_idx}", [value]
    elif operator == "lte":
        return f"{field} <= ${param_idx}", [value]
    return "TRUE", []


async def get_row_level_condition(
    user: dict,
    resource_type: str,
    table_alias: str | None = None,
) -> tuple[str, list]:
    """Build a WHERE clause fragment for row-level security on a resource type.

    Returns (condition_sql, params) or ("TRUE", []) if no conditions apply.
    """
    config = await acr_store.get_acr_config()

    if not config.get("acr_enabled", False) and not config.get("row_level_security", False):
        return "TRUE", []

    if await _is_admin(user, config):
        return "TRUE", []

    rules = await acr_store.list_rules(resource_type)
    if not rules:
        return "TRUE", []

    # Resolve user attribute values
    conditions: list[str] = []
    params: list = []
    idx = 1

    for rule in rules:
        if not rule.get("enabled"):
            continue

        resolved_value = await resolve_user_attribute(user, rule["value"])

        field_ref = rule["field"]
        if table_alias:
            field_ref = f"{table_alias}.{field_ref}"

        cond, cond_params = build_operator_sql(field_ref, rule["operator"], resolved_value, idx)
        if cond not in ("TRUE", "FALSE"):
            idx += len(cond_params)
            params.extend(cond_params)
        conditions.append(cond)

    if not conditions:
        return "TRUE", []

    combined = " AND ".join(f"({c})" for c in conditions)
    return combined, params


async def get_user_injection_value(user: dict) -> str | None:
    """Get the user_id to inject into queries for userid_injection mode."""
    config = await acr_store.get_acr_config()
    if config.get("userid_injection", False):
        return user["id"]
    return None


async def get_user_acr_context(user: dict) -> dict:
    """Get the full ACR context for a user including all applicable rules."""
    config = await acr_store.get_acr_config()

    if await _is_admin(user, config):
        return {
            "acr_enabled": config.get("acr_enabled", False),
            "bypass": True,
            "admin": True,
        }

    context = {
        "acr_enabled": config.get("acr_enabled", False),
        "bypass": False,
        "admin": False,
        "row_level_security": config.get("row_level_security", False),
        "property_level_security": config.get("property_level_security", False),
        "userid_injection": config.get("userid_injection", False),
        "user_id": user["id"],
    }

    return context
