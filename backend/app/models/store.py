from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..database import get_pool


async def _ensure_tables() -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                username        TEXT UNIQUE NOT NULL,
                password_hash   TEXT NOT NULL,
                email           TEXT,
                full_name       TEXT,
                is_active       BOOLEAN DEFAULT TRUE,
                is_superuser    BOOLEAN DEFAULT FALSE,
                roles           JSONB DEFAULT '["developer"]',
                groups          JSONB DEFAULT '[]',
                custom_attributes JSONB DEFAULT '{}',
                created_at      TIMESTAMPTZ DEFAULT now(),
                updated_at      TIMESTAMPTZ DEFAULT now(),
                last_login      TIMESTAMPTZ
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                name        TEXT PRIMARY KEY,
                display_name TEXT,
                description TEXT,
                permissions JSONB DEFAULT '[]'
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                name         TEXT PRIMARY KEY,
                display_name TEXT,
                description  TEXT,
                parent_group TEXT REFERENCES groups(name) ON DELETE SET NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS token_blacklist (
                jti       TEXT PRIMARY KEY,
                user_id   UUID REFERENCES users(id) ON DELETE CASCADE,
                expires_at TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name         TEXT NOT NULL,
                key_hash     TEXT UNIQUE NOT NULL,
                key_prefix   TEXT NOT NULL,
                is_active    BOOLEAN DEFAULT TRUE,
                scopes       JSONB DEFAULT '[]',
                created_by   UUID REFERENCES users(id) ON DELETE CASCADE,
                last_used_at TIMESTAMPTZ,
                expires_at   TIMESTAMPTZ,
                created_at   TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS personal_access_tokens (
                id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                name         TEXT NOT NULL,
                token_hash   TEXT UNIQUE NOT NULL,
                token_prefix TEXT NOT NULL,
                is_active    BOOLEAN DEFAULT TRUE,
                scopes       JSONB DEFAULT '[]',
                user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
                last_used_at TIMESTAMPTZ,
                expires_at   TIMESTAMPTZ,
                created_at   TIMESTAMPTZ DEFAULT now()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key        TEXT PRIMARY KEY,
                value      JSONB NOT NULL DEFAULT 'null',
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """)
        # Seed default roles
        for role, disp in [("admin", "管理员"), ("developer", "开发者"), ("viewer", "观察者")]:
            await conn.execute(
                "INSERT INTO roles (name, display_name) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                role, disp,
            )
        # Seed default groups
        for grp, disp, parent in [
            ("admins", "管理员组", None),
            ("developers", "开发者组", None),
            ("viewers", "观察者组", None),
        ]:
            await conn.execute(
                "INSERT INTO groups (name, display_name, parent_group) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
                grp, disp, parent,
            )
        # Seed default admin user (admin / admin123)
        from ..core.security import hash_password
        existing = await conn.fetchval("SELECT id FROM users WHERE username = 'admin'")
        if not existing:
            await conn.execute(
                """INSERT INTO users (username, password_hash, email, full_name, is_superuser, roles, groups)
                   VALUES ($1, $2, $3, $4, TRUE, '["admin"]', '["admins"]')""",
                "admin", hash_password("admin123"), "admin@ontology.local", "系统管理员",
            )


# ── Users ─────────────────────────────────────────────────

async def get_user_by_username(username: str) -> dict | None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE username = $1", username)
    return _row_to_user(row) if row else None


async def get_user_by_id(user_id: str) -> dict | None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    return _row_to_user(row) if row else None


async def create_user(data: dict) -> dict:
    await _ensure_tables()
    from ..core.security import hash_password

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO users (username, password_hash, email, full_name, is_superuser, roles, groups)
               VALUES ($1, $2, $3, $4, $5, $6, $7)
               RETURNING *""",
            data["username"], hash_password(data["password"]),
            data.get("email"), data.get("full_name"),
            data.get("is_superuser", False),
            data.get("roles", ["developer"]), data.get("groups", []),
        )
    return _row_to_user(row)


async def update_user(user_id: str, data: dict) -> dict | None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        setters: list[str] = []
        vals: list[Any] = []
        idx = 1
        field_map = {
            "email": "email", "full_name": "full_name",
            "is_active": "is_active", "is_superuser": "is_superuser",
            "roles": "roles", "groups": "groups", "custom_attributes": "custom_attributes",
        }
        for py_key, col in field_map.items():
            if py_key in data:
                setters.append(f"{col} = ${idx}")
                vals.append(data[py_key])
                idx += 1
        if not setters:
            return await get_user_by_id(user_id)
        setters.append(f"updated_at = ${idx}")
        vals.append(datetime.now(UTC))
        idx += 1
        vals.append(user_id)
        sql = f"UPDATE users SET {', '.join(setters)} WHERE id = ${idx} RETURNING *"
        row = await conn.fetchrow(sql, *vals)
    return _row_to_user(row) if row else None


async def list_users(page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT count(*) FROM users")
        rows = await conn.fetch(
            "SELECT * FROM users ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            page_size, (page - 1) * page_size,
        )
    return [_row_to_user(r) for r in rows], total


async def delete_user(user_id: str) -> bool:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
    return result == "DELETE 1"


async def update_last_login(user_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET last_login = now() WHERE id = $1", user_id)


# ── Roles ─────────────────────────────────────────────────

async def list_roles() -> list[dict]:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM roles ORDER BY name")
    return [_row_to_dict(r) for r in rows]


async def create_role(name: str, display_name: str = "", description: str = "", permissions: list = None) -> dict:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO roles (name, display_name, description, permissions)
               VALUES ($1, $2, $3, $4) ON CONFLICT (name) DO UPDATE
               SET display_name = $2, description = $3, permissions = $4 RETURNING *""",
            name, display_name, description, permissions or [],
        )
    return _row_to_dict(row)


async def update_role(name: str, data: dict) -> dict | None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE roles SET display_name = COALESCE($2, display_name),
               description = COALESCE($3, description),
               permissions = COALESCE($4, permissions)
               WHERE name = $1 RETURNING *""",
            name, data.get("display_name"), data.get("description"), data.get("permissions"),
        )
    return _row_to_dict(row) if row else None


async def delete_role(name: str) -> bool:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM roles WHERE name = $1", name)
    return result == "DELETE 1"


# ── Groups ────────────────────────────────────────────────

async def list_groups() -> list[dict]:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM groups ORDER BY name")
    return [_row_to_dict(r) for r in rows]


async def create_group(name: str, display_name: str = "", description: str = "", parent_group: str | None = None) -> dict:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO groups (name, display_name, description, parent_group)
               VALUES ($1, $2, $3, $4) ON CONFLICT (name) DO UPDATE
               SET display_name = $2, description = $3, parent_group = $4 RETURNING *""",
            name, display_name, description, parent_group,
        )
    return _row_to_dict(row)


async def update_group(name: str, data: dict) -> dict | None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """UPDATE groups SET display_name = COALESCE($2, display_name),
               description = COALESCE($3, description),
               parent_group = $4
               WHERE name = $1 RETURNING *""",
            name, data.get("display_name"), data.get("description"), data.get("parent_group"),
        )
    return _row_to_dict(row) if row else None


async def delete_group(name: str) -> bool:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM groups WHERE name = $1", name)
    return result == "DELETE 1"


# ── Token Blacklist ───────────────────────────────────────

async def blacklist_token(jti: str, user_id: str, expires_at: datetime) -> None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO token_blacklist (jti, user_id, expires_at) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            jti, user_id, expires_at,
        )


async def is_token_blacklisted(jti: str) -> bool:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT 1 FROM token_blacklist WHERE jti = $1", jti)
    return row is not None


# ── Helpers ───────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    import json
    from uuid import UUID
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, UUID):
            d[k] = str(v)
        elif isinstance(v, str) and (k in ("roles", "groups", "permissions", "custom_attributes")):
            try:
                d[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                pass
    if "created_at" in d and d["created_at"]:
        d["created_at"] = d["created_at"].isoformat()
    if "updated_at" in d and d["updated_at"]:
        d["updated_at"] = d["updated_at"].isoformat()
    if "last_login" in d and d["last_login"]:
        d["last_login"] = d["last_login"].isoformat()
    return d


def _row_to_user(row) -> dict:
    d = _row_to_dict(row)
    d["password_hash"] = str(row["password_hash"])
    return d


# ── API Keys ───────────────────────────────────────────────

async def create_api_key(user_id: str, name: str, key_hash: str, key_prefix: str, scopes: list, expires_at: datetime | None) -> dict:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO api_keys (name, key_hash, key_prefix, scopes, created_by, expires_at)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
            name, key_hash, key_prefix, scopes, user_id, expires_at,
        )
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "key_prefix": row["key_prefix"],
        "is_active": row["is_active"],
        "scopes": row["scopes"],
        "created_by": str(row["created_by"]),
        "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
        "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


async def list_api_keys(user_id: str) -> list[dict]:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM api_keys WHERE created_by = $1 ORDER BY created_at DESC", user_id,
        )
    return [_api_key_row(r) for r in rows]


async def list_all_api_keys(page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT count(*) FROM api_keys")
        rows = await conn.fetch(
            "SELECT * FROM api_keys ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            page_size, (page - 1) * page_size,
        )
    return [_api_key_row(r) for r in rows], total


async def revoke_api_key(key_id: str, user_id: str | None = None) -> bool:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id:
            result = await conn.execute(
                "DELETE FROM api_keys WHERE id = $1 AND created_by = $2", key_id, user_id,
            )
        else:
            result = await conn.execute("DELETE FROM api_keys WHERE id = $1", key_id)
    return result == "DELETE 1"


async def get_api_key_by_hash(key_hash: str) -> dict | None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM api_keys WHERE key_hash = $1", key_hash)
    return _api_key_row(row) if row else None


async def touch_api_key(key_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE api_keys SET last_used_at = now() WHERE id = $1", key_id)


# ── Personal Access Tokens ─────────────────────────────────

async def create_personal_token(user_id: str, name: str, token_hash: str, token_prefix: str, scopes: list, expires_at: datetime | None) -> dict:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO personal_access_tokens (name, token_hash, token_prefix, scopes, user_id, expires_at)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING *""",
            name, token_hash, token_prefix, scopes, user_id, expires_at,
        )
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "token_prefix": row["token_prefix"],
        "is_active": row["is_active"],
        "scopes": row["scopes"],
        "user_id": str(row["user_id"]),
        "last_used_at": row["last_used_at"].isoformat() if row["last_used_at"] else None,
        "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


async def list_personal_tokens(user_id: str) -> list[dict]:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM personal_access_tokens WHERE user_id = $1 ORDER BY created_at DESC", user_id,
        )
    return [_pat_row(r) for r in rows]


async def list_all_personal_tokens(page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT count(*) FROM personal_access_tokens")
        rows = await conn.fetch(
            "SELECT * FROM personal_access_tokens ORDER BY created_at DESC LIMIT $1 OFFSET $2",
            page_size, (page - 1) * page_size,
        )
    return [_pat_row(r) for r in rows], total


async def revoke_personal_token(token_id: str, user_id: str | None = None) -> bool:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id:
            result = await conn.execute(
                "DELETE FROM personal_access_tokens WHERE id = $1 AND user_id = $2", token_id, user_id,
            )
        else:
            result = await conn.execute("DELETE FROM personal_access_tokens WHERE id = $1", token_id)
    return result == "DELETE 1"


async def revoke_all_user_tokens(user_id: str) -> int:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM personal_access_tokens WHERE user_id = $1", user_id,
        )
    return int(result.split()[-1]) if result.startswith("DELETE") else 0


async def get_personal_token_by_hash(token_hash: str) -> dict | None:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM personal_access_tokens WHERE token_hash = $1", token_hash)
    return _pat_row(row) if row else None


async def touch_personal_token(token_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE personal_access_tokens SET last_used_at = now() WHERE id = $1", token_id)


# ── Helpers ────────────────────────────────────────────────

def _api_key_row(row) -> dict:
    import json
    d = dict(row)
    d["id"] = str(d["id"])
    d["created_by"] = str(d["created_by"])
    if "scopes" in d and isinstance(d["scopes"], str):
        try:
            d["scopes"] = json.loads(d["scopes"])
        except (json.JSONDecodeError, TypeError):
            d["scopes"] = []
    for ts in ("last_used_at", "expires_at", "created_at"):
        if ts in d and d[ts]:
            d[ts] = d[ts].isoformat()
    d.pop("key_hash", None)
    return d


# ── System Config ────────────────────────────────────────

async def get_all_system_config() -> dict[str, Any]:
    await _ensure_tables()
    import json
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT key, value FROM system_config ORDER BY key")
    result = {}
    for r in rows:
        v = r["value"]
        if isinstance(v, str):
            try:
                result[r["key"]] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                result[r["key"]] = v
        else:
            result[r["key"]] = v
    return result


async def get_system_config_item(key: str) -> dict | None:
    await _ensure_tables()
    import json
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT key, value, updated_at FROM system_config WHERE key = $1", key)
    if not row:
        return None
    v = row["value"]
    if isinstance(v, str):
        try:
            v = json.loads(v)
        except (json.JSONDecodeError, TypeError):
            pass
    return {"key": row["key"], "value": v, "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None}


async def set_system_config_items(items: dict[str, Any]) -> dict[str, Any]:
    await _ensure_tables()
    import json
    pool = await get_pool()
    async with pool.acquire() as conn:
        for key, value in items.items():
            await conn.execute(
                """INSERT INTO system_config (key, value, updated_at)
                   VALUES ($1, $2::jsonb, now())
                   ON CONFLICT (key) DO UPDATE SET value = $2::jsonb, updated_at = now()""",
                key, json.dumps(value),
            )
    return await get_all_system_config()


async def update_system_config_item(key: str, value: Any) -> dict | None:
    await _ensure_tables()
    import json
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO system_config (key, value, updated_at)
               VALUES ($1, $2::jsonb, now())
               ON CONFLICT (key) DO UPDATE SET value = $2::jsonb, updated_at = now()
               RETURNING key, value, updated_at""",
            key, json.dumps(value),
        )
    if not row:
        return None
    return {"key": row["key"], "value": row["value"], "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None}


async def delete_system_config_item(key: str) -> bool:
    await _ensure_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM system_config WHERE key = $1", key)
    return result == "DELETE 1"


def _pat_row(row) -> dict:
    import json
    d = dict(row)
    d["id"] = str(d["id"])
    d["user_id"] = str(d["user_id"])
    if "scopes" in d and isinstance(d["scopes"], str):
        try:
            d["scopes"] = json.loads(d["scopes"])
        except (json.JSONDecodeError, TypeError):
            d["scopes"] = []
    for ts in ("last_used_at", "expires_at", "created_at"):
        if ts in d and d[ts]:
            d[ts] = d[ts].isoformat()
    d.pop("token_hash", None)
    return d
