"""Provider for the standalone Hello World datalab tool."""

from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, jsonify, request, send_from_directory
from flask_login import current_user

from pydatalab.tools import (
    StandaloneToolUI,
    ToolLaunchGrantIssuer,
    ToolLaunchResult,
    ToolMetadata,
    ToolProvider,
    exchange_launch_code,
)

TOOL_BLUEPRINT = Blueprint("datalab_hello_standalone_tool", __name__)
TOOL_ID = "hello-standalone"
CLIENT_ID = TOOL_ID
STATIC_DIRECTORY = Path(__file__).parent / "static"


@TOOL_BLUEPRINT.get("/")
def index():
    """Serve the standalone Hello World page."""
    response = send_from_directory(STATIC_DIRECTORY, "index.html")
    response.headers["Cache-Control"] = "no-store"
    return response


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
        CLIENT_ID,
        expected_user_id=str(current_user.person.immutable_id),
    )
    if result is None:
        return jsonify({"error": "Invalid or expired launch code"}), 400

    response = jsonify(
        {
            "current_user": {
                "display_name": result.context.display_name,
                "role": result.context.role,
            },
            "tool_access_token": result.tool_session.tool_access_token,
        }
    )
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
        ui=StandaloneToolUI(open_mode="new_tab"),
    )
    blueprint = TOOL_BLUEPRINT

    def launch(
        self,
        context,
        grants: ToolLaunchGrantIssuer,
    ) -> ToolLaunchResult:
        """Issue a single-use tool launch grant and return the standalone page URL."""
        del context
        code = grants.issue(CLIENT_ID)
        api_prefix = request.path.rsplit("/tools/", maxsplit=1)[0]
        plugin_path = f"{api_prefix}/tools/plugins/{self.id}/"
        base_url = f"{request.host_url.rstrip('/')}{plugin_path}"
        url = f"{base_url}#datalab_launch_code={quote(code, safe='')}"
        return ToolLaunchResult(url=url)
