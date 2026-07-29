"""Single-use tool launch grants and delegated tool sessions."""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha512

from bson import ObjectId
from bson.errors import InvalidId
from flask import current_app, has_app_context

from pydatalab.login import get_by_id
from pydatalab.models.people import AccountStatus
from pydatalab.mongo import flask_mongo

from .base import ToolContext, ToolLaunchGrantIssuer

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
class ToolLaunchExchange:
    """Tool context and delegated tool session produced by a launch code exchange."""

    context: ToolContext
    tool_session: DelegatedToolSession


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
        code = secrets.token_urlsafe(32)
        flask_mongo.db.tool_launch_grants.insert_one(
            {
                "_id": _hash_secret(code),
                "user_id": ObjectId(self.user_id),
                "tool_id": self.tool_id,
                "client_id": client_id,
                "created_at": created_at,
                "expires_at": created_at + timedelta(seconds=lifetime_seconds),
            }
        )
        return code


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
        "_id": _hash_secret(code),
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
    tool_access_token = secrets.token_urlsafe(48)
    flask_mongo.db.tool_sessions.insert_one(
        {
            "_id": _hash_secret(tool_access_token),
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


def get_tool_access_token_user_id(tool_access_token: str) -> str | None:
    """Return the user bound to an unexpired tool access token."""
    session = flask_mongo.db.tool_sessions.find_one(
        {
            "_id": _hash_secret(tool_access_token),
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


def exchange_launch_code(
    code: str,
    tool_id: str,
    client_id: str,
    tool_session_lifetime_seconds: int = DEFAULT_TOOL_SESSION_LIFETIME_SECONDS,
    expected_user_id: str | None = None,
) -> ToolLaunchExchange | None:
    """Consume a launch code and issue a delegated tool session for an active user.

    A provider-owned exchange route must authenticate its remote client before
    calling this function. Browser-authenticated routes should pass the current
    immutable user ID as ``expected_user_id`` so another user's code is never
    consumed.
    """
    if not 1 <= tool_session_lifetime_seconds <= MAX_TOOL_SESSION_LIFETIME_SECONDS:
        raise ValueError(
            "Delegated tool sessions must expire within "
            f"{MAX_TOOL_SESSION_LIFETIME_SECONDS} seconds"
        )

    user_id = consume_launch_code(
        code,
        tool_id,
        client_id,
        expected_user_id=expected_user_id,
    )
    if user_id is None:
        return None

    user = get_by_id(user_id)
    if user is None or user.account_status != AccountStatus.ACTIVE:
        return None

    groups = user.groups or []
    context = ToolContext(
        user_id=user_id,
        display_name=user.display_name,
        role=user.role.value,
        group_ids=tuple(str(group.immutable_id) for group in groups),
    )
    tool_session = create_delegated_tool_session(
        user_id=user_id,
        tool_id=tool_id,
        client_id=client_id,
        lifetime_seconds=tool_session_lifetime_seconds,
    )
    return ToolLaunchExchange(context=context, tool_session=tool_session)
