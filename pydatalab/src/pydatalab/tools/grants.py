"""Single-use tool launch grants and delegated tool sessions."""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha512

from bson import ObjectId
from bson.errors import InvalidId
from flask import current_app, has_app_context
from pymongo.errors import DuplicateKeyError

from pydatalab.mongo import flask_mongo

from .base import ToolLaunchGrantIssuer

DEFAULT_LAUNCH_LIFETIME_SECONDS = 60
DEFAULT_TOOL_SESSION_LIFETIME_SECONDS = 24 * 60 * 60
MAX_LAUNCH_LIFETIME_SECONDS = 10 * 60
MAX_TOOL_SESSION_LIFETIME_SECONDS = DEFAULT_TOOL_SESSION_LIFETIME_SECONDS


def _hash_secret(value: str) -> str:
    return sha512(value.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass(frozen=True)
class DelegatedToolSession:
    """Tool access token returned once for a delegated tool session."""

    tool_access_token: str
    expires_at: datetime


@dataclass(frozen=True)
class BoundToolLaunchGrantIssuer(ToolLaunchGrantIssuer):
    """Tool launch grant capability bound to one provider and current user."""

    tool_id: str
    user_id: str

    def issue(
        self,
        client_id: str,
        lifetime_seconds: int = DEFAULT_LAUNCH_LIFETIME_SECONDS,
    ) -> str:
        """Create a hashed, expiring tool launch grant and return its raw code."""
        if not client_id.strip():
            raise ValueError("Launch-grant client ID must not be empty")
        if not 1 <= lifetime_seconds <= MAX_LAUNCH_LIFETIME_SECONDS:
            raise ValueError(
                f"Tool launch grants must expire within {MAX_LAUNCH_LIFETIME_SECONDS} seconds"
            )

        created_at = _now()
        expires_at = created_at + timedelta(seconds=lifetime_seconds)
        for _ in range(3):
            code = secrets.token_urlsafe(32)
            try:
                flask_mongo.db.tool_launch_grants.insert_one(
                    {
                        "code_hash": _hash_secret(code),
                        "user_id": ObjectId(self.user_id),
                        "tool_id": self.tool_id,
                        "client_id": client_id,
                        "created_at": created_at,
                        "expires_at": expires_at,
                    }
                )
                return code
            except DuplicateKeyError:
                continue

        raise RuntimeError("Unable to create a unique tool launch grant")


def consume_launch_code(
    code: str,
    tool_id: str,
    client_id: str,
    expected_user_id: str | None = None,
) -> str | None:
    """Atomically consume a matching unexpired launch code and return its user ID."""
    if not code or not tool_id or not client_id:
        return None

    query: dict[str, object] = {
        "code_hash": _hash_secret(code),
        "tool_id": tool_id,
        "client_id": client_id,
        "expires_at": {"$gt": _now()},
    }
    if expected_user_id is not None:
        try:
            query["user_id"] = ObjectId(expected_user_id)
        except (InvalidId, TypeError):
            return None

    grant = flask_mongo.db.tool_launch_grants.find_one_and_delete(query)
    if grant is None:
        return None
    return str(grant["user_id"])


def create_delegated_tool_session(
    user_id: str,
    tool_id: str,
    client_id: str,
    lifetime_seconds: int = DEFAULT_TOOL_SESSION_LIFETIME_SECONDS,
) -> DelegatedToolSession:
    """Issue a tool access token for one delegated tool session."""
    if not 1 <= lifetime_seconds <= MAX_TOOL_SESSION_LIFETIME_SECONDS:
        raise ValueError(
            "Delegated tool sessions must expire within "
            f"{MAX_TOOL_SESSION_LIFETIME_SECONDS} seconds"
        )

    created_at = _now()
    expires_at = created_at + timedelta(seconds=lifetime_seconds)
    for _ in range(3):
        tool_access_token = secrets.token_urlsafe(48)
        try:
            flask_mongo.db.tool_sessions.insert_one(
                {
                    "token_hash": _hash_secret(tool_access_token),
                    "user_id": ObjectId(user_id),
                    "tool_id": tool_id,
                    "client_id": client_id,
                    "created_at": created_at,
                    "expires_at": expires_at,
                }
            )
            return DelegatedToolSession(
                tool_access_token=tool_access_token,
                expires_at=expires_at,
            )
        except DuplicateKeyError:
            continue

    raise RuntimeError("Unable to create a unique delegated tool session")


def get_tool_access_token_user_id(tool_access_token: str) -> str | None:
    """Return the user bound to an unexpired tool access token."""
    session = flask_mongo.db.tool_sessions.find_one(
        {
            "token_hash": _hash_secret(tool_access_token),
            "expires_at": {"$gt": _now()},
        },
        projection={"user_id": 1, "tool_id": 1},
    )
    if session is None:
        return None
    tool_id = session.get("tool_id")
    if not isinstance(tool_id, str) or not has_app_context():
        return None

    from .registry import TOOL_REGISTRY_EXTENSION, ToolRegistry

    registry = current_app.extensions.get(TOOL_REGISTRY_EXTENSION)
    if not isinstance(registry, ToolRegistry) or not registry.is_enabled(tool_id):
        return None
    return str(session["user_id"])
