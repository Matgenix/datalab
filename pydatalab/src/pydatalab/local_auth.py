"""Small file-backed local credentials for testing-only login."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError
from werkzeug.security import check_password_hash, generate_password_hash

from pydatalab.config import CONFIG
from pydatalab.models.utils import HumanReadableIdentifier

LOCAL_AUTH_FILENAME = ".local_auth_credentials.json"


def local_auth_credentials_path() -> Path:
    return Path(CONFIG.FILE_DIRECTORY) / LOCAL_AUTH_FILENAME


def load_local_credentials() -> dict:
    path = local_auth_credentials_path()
    if not path.is_file():
        return {}

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}

    return data if isinstance(data, dict) else {}


def save_local_credentials(credentials: dict) -> None:
    path = local_auth_credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(credentials, indent=2, sort_keys=True) + "\n")
    os.replace(tmp_path, path)


def set_local_credential(username: str, user_id: str, password: str) -> None:
    username = str(HumanReadableIdentifier(username))
    credentials = load_local_credentials()
    credentials[username] = {
        "user_id": str(user_id),
        "password_hash": generate_password_hash(password),
    }
    save_local_credentials(credentials)


def verify_local_credential(username: str, password: str) -> str | None:
    try:
        username = str(HumanReadableIdentifier(username))
    except (ValueError, ValidationError):
        return None

    credential = load_local_credentials().get(username)
    if not credential:
        return None

    password_hash = credential.get("password_hash")
    if not password_hash or not check_password_hash(password_hash, password):
        return None

    return credential.get("user_id")
