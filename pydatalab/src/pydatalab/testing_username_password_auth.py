"""Small file-backed credentials for testing-only username/password login."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError
from werkzeug.security import check_password_hash, generate_password_hash

from pydatalab.config import CONFIG
from pydatalab.models.utils import HumanReadableIdentifier

TESTING_USERNAME_PASSWORD_AUTH_FILENAME = ".testing_username_password_credentials.json"  # noqa: S105


def testing_username_password_credentials_path() -> Path:
    return Path(CONFIG.FILE_DIRECTORY) / TESTING_USERNAME_PASSWORD_AUTH_FILENAME


def load_testing_username_password_credentials() -> dict:
    path = testing_username_password_credentials_path()
    if not path.is_file():
        return {}

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {}

    return data if isinstance(data, dict) else {}


def save_testing_username_password_credentials(credentials: dict) -> None:
    path = testing_username_password_credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(credentials, indent=2, sort_keys=True) + "\n")
    os.replace(tmp_path, path)


def set_testing_username_password_credential(username: str, user_id: str, password: str) -> None:
    username = str(HumanReadableIdentifier(username))
    credentials = load_testing_username_password_credentials()
    credentials[username] = {
        "user_id": str(user_id),
        "password_hash": generate_password_hash(password),
    }
    save_testing_username_password_credentials(credentials)


def verify_testing_username_password_credential(username: str, password: str) -> str | None:
    try:
        username = str(HumanReadableIdentifier(username))
    except (ValueError, ValidationError):
        return None

    credential = load_testing_username_password_credentials().get(username)
    if not credential:
        return None

    password_hash = credential.get("password_hash")
    if not password_hash or not check_password_hash(password_hash, password):
        return None

    return credential.get("user_id")
