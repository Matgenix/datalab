"""Provider for the in-app Hello World datalab tool."""

from pathlib import Path

from flask import Blueprint, send_from_directory

from pydatalab.tools import (
    InAppToolUI,
    ToolMetadata,
    ToolProvider,
)

TOOL_BLUEPRINT = Blueprint("datalab_hello_in_app_tool", __name__)
TOOL_ID = "hello-in-app"
FRONTEND_DIRECTORY = Path(__file__).parent / "static" / "frontend"


@TOOL_BLUEPRINT.get("/frontend/tool.js")
def frontend_entrypoint():
    """Serve the compiled in-app Hello World bundle."""
    response = send_from_directory(FRONTEND_DIRECTORY, "tool.js")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


class HelloInAppToolProvider(ToolProvider):
    """Expose a minimal in-app tool through datalab's tool catalog."""

    id = TOOL_ID
    metadata = ToolMetadata(
        name="Hello in-app",
        description="Print one datalab-backed message inside the web app.",
        version="0.1.0",
        icon="laptop-code",
        ui=InAppToolUI(),
    )
    blueprint = TOOL_BLUEPRINT
