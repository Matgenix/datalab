"""Current-user catalog and launch routes for tools."""

import json

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user
from pydantic import AnyHttpUrl, parse_obj_as

from pydatalab.logger import LOGGER
from pydatalab.login import is_browser_session_user
from pydatalab.models.people import AccountStatus
from pydatalab.permissions import active_users_or_get_only
from pydatalab.tools.auth import request_origin_is_allowed
from pydatalab.tools.base import (
    StandaloneToolUI,
    ToolContext,
)
from pydatalab.tools.grants import BoundToolLaunchGrantIssuer
from pydatalab.tools.registry import TOOL_REGISTRY_EXTENSION, ToolRegistry

from .info import Attributes, Data, JSONAPIResponse, Meta

TOOLS = Blueprint("tools", __name__)


def _active_tool_context() -> ToolContext | None:
    if not current_user.is_authenticated or current_user.account_status != AccountStatus.ACTIVE:
        return None

    groups = current_user.groups or []
    return ToolContext(
        user_id=str(current_user.person.immutable_id),
        display_name=current_user.display_name,
        role=current_user.role.value,
        group_ids=tuple(str(group.immutable_id) for group in groups),
    )


def _registry() -> ToolRegistry:
    return current_app.extensions[TOOL_REGISTRY_EXTENSION]


@TOOLS.route("/info/tools", methods=["GET"])
@active_users_or_get_only
def list_tools():
    """List tools enabled and available to the active current user."""
    context = _active_tool_context()
    if context is None:
        return jsonify({"error": "Unauthorized"}), 401

    response = JSONAPIResponse(
        data=[
            Data(
                id=provider.id,
                type="tool",
                attributes=Attributes(**provider.metadata.dict()),
            )
            for provider in _registry().available_for(context)
        ],
        meta=Meta(query=request.query_string),
    )
    catalog_response = jsonify(json.loads(response.json()))
    catalog_response.headers["Cache-Control"] = "private, no-store"
    return catalog_response, 200


@TOOLS.route("/tools/<string:tool_id>/launch", methods=["POST"])
@active_users_or_get_only
def launch_tool(tool_id: str):
    """Prepare a tool launch for the active current user."""
    if not current_user.is_authenticated or not is_browser_session_user(current_user):
        return jsonify({"status": "error", "message": "A browser session is required"}), 403

    if not request_origin_is_allowed():
        return jsonify({"status": "error", "message": "Untrusted request origin"}), 403

    context = _active_tool_context()
    if context is None:
        return jsonify({"error": "Unauthorized"}), 401

    provider = _registry().available_provider(tool_id, context)
    if provider is None:
        return jsonify({"status": "error", "message": "Tool not found or unavailable"}), 404

    issuer = BoundToolLaunchGrantIssuer(tool_id=tool_id, user_id=context.user_id)
    try:
        result = provider.launch(context, issuer)
        launch_data = {}
        if isinstance(provider.metadata.ui, StandaloneToolUI):
            if not isinstance(result, str):
                raise TypeError("Standalone tool launches must return an HTTP(S) URL")
            launch_data["url"] = str(parse_obj_as(AnyHttpUrl, result))
        elif result is not None:
            raise TypeError("In-app tool launches must return None")
    except Exception:
        LOGGER.exception("Unable to launch tool provider %r", tool_id)
        return jsonify({"status": "error", "message": "Unable to launch tool"}), 503

    response = jsonify(launch_data)
    response.headers["Cache-Control"] = "no-store"
    return response, 200
