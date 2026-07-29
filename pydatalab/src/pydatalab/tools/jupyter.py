"""Built-in JupyterLab tool provider and JupyterHub launch code exchange."""

import hmac
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from flask import Blueprint, abort, jsonify, request

from pydatalab import __version__
from pydatalab.config import CONFIG

from .base import (
    ToolContext,
    ToolLaunchGrantIssuer,
    ToolLaunchResult,
    ToolMetadata,
    ToolProvider,
    ToolRouteAuth,
)
from .exchange import exchange_launch_code

JUPYTER_BLUEPRINT = Blueprint("jupyter-tool", __name__)


def _jupyter_public_url() -> str:
    settings = CONFIG.TOOLS.JUPYTER
    if settings.EXTERNAL_URL is not None:
        return str(settings.EXTERNAL_URL)
    if settings.PUBLIC_URL is not None:
        return str(settings.PUBLIC_URL)
    if CONFIG.APP_URL:
        return f"{CONFIG.APP_URL.rstrip('/')}/jupyter/"
    return "http://localhost:8000/jupyter/"


def _login_url(code: str) -> str:
    login_url = urljoin(
        f"{_jupyter_public_url().rstrip('/')}/",
        "hub/datalab-login",
    )
    parts = urlsplit(login_url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.append(("datalab_launch_code", code))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class JupyterToolProvider(ToolProvider):
    """Built-in standalone JupyterLab provider."""

    id = "jupyter"
    metadata = ToolMetadata(
        name="JupyterLab",
        description="Explore and analyse your datalab data programmatically in JupyterLab.",
        version=__version__,
        icon="book",
    )
    blueprint = JUPYTER_BLUEPRINT
    route_auth = ToolRouteAuth.SERVICE

    def is_available(self, context: ToolContext) -> bool:
        return CONFIG.TOOLS.JUPYTER.ENABLED

    def authenticate_service_request(self) -> bool:
        """Authenticate the configured JupyterHub client."""
        settings = CONFIG.TOOLS.JUPYTER
        authorization = request.authorization
        if authorization is None or authorization.type.lower() != "basic":
            return False

        configured_secret = settings.CLIENT_SECRET
        if configured_secret is None:
            return False

        supplied_id = authorization.username or ""
        supplied_secret = authorization.password or ""
        return hmac.compare_digest(
            supplied_id.encode("utf-8"),
            settings.CLIENT_ID.encode("utf-8"),
        ) and hmac.compare_digest(
            supplied_secret.encode("utf-8"),
            configured_secret.get_secret_value().encode("utf-8"),
        )

    def launch(
        self,
        context: ToolContext,
        grants: ToolLaunchGrantIssuer,
    ) -> ToolLaunchResult:
        settings = CONFIG.TOOLS.JUPYTER
        code = grants.issue(settings.CLIENT_ID)
        return ToolLaunchResult(url=_login_url(code))


@JUPYTER_BLUEPRINT.route("/exchange", methods=["POST"])
def exchange_jupyter_launch_code():
    """Exchange one launch code for a tool access token."""
    if not CONFIG.TOOLS.JUPYTER.ENABLED:
        abort(404)

    payload = request.get_json(silent=True) or {}
    code = payload.get("code")
    if not isinstance(code, str) or not code:
        return jsonify({"status": "error", "message": "A launch code is required"}), 400

    settings = CONFIG.TOOLS.JUPYTER
    exchange = exchange_launch_code(code, JupyterToolProvider.id, settings.CLIENT_ID)
    if exchange is None:
        return jsonify({"status": "error", "message": "Invalid or expired launch code"}), 400

    response = jsonify(
        {
            "user_id": exchange.context.user_id,
            "username": f"datalab-{exchange.context.user_id}",
            "display_name": exchange.context.display_name,
            "role": exchange.context.role,
            "group_ids": list(exchange.context.group_ids),
            "tool_access_token": exchange.tool_session.tool_access_token,
            "expires_at": exchange.tool_session.expires_at.isoformat(),
        }
    )
    response.headers["Cache-Control"] = "no-store"
    return response, 200
