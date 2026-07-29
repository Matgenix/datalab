"""Public server-side exchange service for remote tool providers."""

from dataclasses import dataclass

from pydatalab.login import get_by_id
from pydatalab.models.people import AccountStatus

from .base import ToolContext
from .grants import (
    DEFAULT_TOOL_SESSION_LIFETIME_SECONDS,
    MAX_TOOL_SESSION_LIFETIME_SECONDS,
    DelegatedToolSession,
    consume_launch_code,
    create_delegated_tool_session,
)


@dataclass(frozen=True)
class ToolLaunchExchange:
    """Tool context and delegated tool session produced by a launch code exchange."""

    context: ToolContext
    tool_session: DelegatedToolSession


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
