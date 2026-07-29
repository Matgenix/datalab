"""Shared authentication helpers for tool launches and provider routes."""

from ipaddress import ip_address
from urllib.parse import urlsplit

from flask import request

from pydatalab.config import CONFIG


def _normalized_origin(value: str) -> tuple[str, str, int] | None:
    """Normalize an HTTP origin for strict comparisons."""
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme.lower() not in {"http", "https"}
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
        ):
            return None
        port = parsed.port
    except ValueError:
        return None

    scheme = parsed.scheme.lower()
    if port is None:
        port = 443 if scheme == "https" else 80
    return scheme, parsed.hostname.rstrip(".").lower(), port


def _is_loopback_origin(origin: tuple[str, str, int] | None) -> bool:
    if origin is None:
        return False
    hostname = origin[1]
    if hostname == "localhost" or hostname.endswith(".localhost"):
        return True
    try:
        return ip_address(hostname).is_loopback
    except ValueError:
        return False


def request_origin_is_allowed(*, require_origin: bool = False) -> bool:
    """Return whether the request origin is trusted by this datalab deployment."""
    supplied_origin = request.headers.get("Origin")
    if supplied_origin is None:
        return not require_origin

    origin = _normalized_origin(supplied_origin)
    request_origin = _normalized_origin(request.host_url)
    allowed_origins = {request_origin}
    if CONFIG.APP_URL:
        allowed_origins.add(_normalized_origin(str(CONFIG.APP_URL)))

    if origin is not None and origin in allowed_origins:
        return True

    # The development frontend and API commonly use separate localhost ports.
    return _is_loopback_origin(origin) and _is_loopback_origin(request_origin)
