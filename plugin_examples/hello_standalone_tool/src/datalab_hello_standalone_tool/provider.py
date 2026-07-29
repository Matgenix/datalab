"""Provider for the standalone Hello World datalab tool."""

from flask import Blueprint, jsonify, request
from flask_login import current_user

from pydatalab.tools import (
    StandaloneToolUI,
    ToolContext,
    ToolLaunchGrantIssuer,
    ToolMetadata,
    ToolProvider,
    exchange_launch_code,
)

TOOL_ID = "hello-standalone"
TOOL_BLUEPRINT = Blueprint(
    "datalab_hello_standalone_tool",
    __name__,
    static_folder="static",
    static_url_path="",
)


@TOOL_BLUEPRINT.post("/exchange")
def exchange():
    """Exchange this user's launch code for a tool access token."""
    payload = request.get_json(silent=True) or {}
    code = payload.get("code")
    if not isinstance(code, str) or not code:
        return jsonify({"error": "A launch code is required"}), 400

    result = exchange_launch_code(
        code,
        TOOL_ID,
        TOOL_ID,
        expected_user_id=str(current_user.person.immutable_id),
    )
    if result is None:
        return jsonify({"error": "Invalid or expired launch code"}), 400

    response = jsonify({"tool_access_token": result.tool_session.tool_access_token})
    response.headers["Cache-Control"] = "no-store"
    return response, 200


class HelloStandaloneToolProvider(ToolProvider):
    """Expose a minimal standalone tool through datalab's tool catalog."""

    id = TOOL_ID
    metadata = ToolMetadata(
        name="Hello standalone",
        description="Open a new tab and call datalab with a tool access token.",
        version="0.1.0",
        icon="external-link-alt",
        ui=StandaloneToolUI(),
    )
    blueprint = TOOL_BLUEPRINT

    def launch(
        self,
        context: ToolContext,
        grants: ToolLaunchGrantIssuer,
    ) -> str:
        """Issue a single-use tool launch grant and return the standalone page URL."""
        del context
        code = grants.issue(TOOL_ID)
        api_prefix = request.path.rsplit("/tools/", maxsplit=1)[0]
        plugin_path = f"{api_prefix}/tools/plugins/{self.id}/"
        base_url = f"{request.host_url.rstrip('/')}{plugin_path}"
        return f"{base_url}index.html#datalab_launch_code={code}"
