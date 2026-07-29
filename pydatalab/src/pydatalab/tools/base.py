# This file was edited with the assistance of an AI model and requires human review from the contributor.
"""Stable public interfaces for datalab tool providers."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Literal, Protocol, Union
from urllib.parse import urlsplit

from flask import Blueprint
from pydantic import AnyHttpUrl, BaseModel, Field, StrictInt, root_validator, validator

TOOL_ENTRYPOINT_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
TOOL_ACTION_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


class ItemTableSelectionAction(BaseModel):
    """A tool action offered for selected rows in configured item tables."""

    kind: Literal["item-table-selection"] = "item-table-selection"
    id: str
    label: str
    tables: tuple[Literal["samples", "inventory", "equipment", "collection-items"], ...]
    min_items: StrictInt = 1
    max_items: StrictInt = 100

    @validator("id")
    def id_is_lowercase_slug(cls, value):
        if not TOOL_ACTION_ID_PATTERN.fullmatch(value):
            raise ValueError("Tool action IDs must be lowercase hyphenated slugs")
        return value

    @validator("label")
    def label_is_non_empty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Tool action labels must not be empty")
        return value

    @validator("tables")
    def tables_are_non_empty_and_unique(cls, value):
        if not value:
            raise ValueError("Tool actions must declare at least one table")
        if len(value) != len(set(value)):
            raise ValueError("Tool action tables must not contain duplicates")
        return value

    @root_validator
    def selection_limits_are_valid(cls, values):
        minimum = values.get("min_items")
        maximum = values.get("max_items")
        if minimum is not None and maximum is not None:
            if minimum < 1 or maximum > 100 or minimum > maximum:
                raise ValueError(
                    "Tool action limits must satisfy 1 <= min_items <= max_items <= 100"
                )
        return values

    class Config:
        allow_mutation = False
        extra = "forbid"


class ToolRouteAuth(str, Enum):
    """Authentication policy applied to every route in a provider blueprint."""

    BROWSER = "browser"
    SERVICE = "service"


class ToolOpenMode(str, Enum):
    """Browser navigation requested when a user opens a tool."""

    SAME_TAB = "same_tab"
    NEW_TAB = "new_tab"


class BaseToolUI(BaseModel):
    """Shared configuration for a tool's user interface."""

    open_mode: ToolOpenMode

    class Config:
        allow_mutation = False
        extra = "forbid"


class StandaloneToolUI(BaseToolUI):
    """A tool UI that runs outside the datalab web application."""

    kind: Literal["standalone"] = "standalone"
    open_mode: ToolOpenMode = ToolOpenMode.NEW_TAB


class InAppToolUI(BaseToolUI):
    """A trusted frontend bundle mounted inside the datalab web application."""

    kind: Literal["in_app"] = "in_app"
    open_mode: ToolOpenMode = ToolOpenMode.SAME_TAB
    entrypoint: str
    sdk_version: StrictInt

    @validator("sdk_version")
    def sdk_version_is_positive(cls, value):
        if value < 1:
            raise ValueError("In-app tools must declare a positive SDK version")
        return value

    @validator("entrypoint")
    def entrypoint_is_namespaced_relative_path(cls, value):
        parsed = urlsplit(value)
        segments = value.split("/")
        if (
            value != value.strip()
            or value.startswith("/")
            or "\\" in value
            or "%" in value
            or parsed.scheme
            or parsed.netloc
            or parsed.query
            or parsed.fragment
            or any(not TOOL_ENTRYPOINT_SEGMENT_PATTERN.fullmatch(segment) for segment in segments)
            or not segments[-1].endswith(".js")
        ):
            raise ValueError(
                "In-app tool entrypoints must be canonical relative JavaScript paths below the "
                "provider namespace"
            )
        return value


ToolUI = Union[StandaloneToolUI, InAppToolUI]


class ToolMetadata(BaseModel):
    """User-facing metadata returned by the tool catalog."""

    name: str
    description: str
    version: str | None = None
    icon: str = "laptop-code"
    ui: ToolUI = Field(default_factory=StandaloneToolUI, discriminator="kind")
    launch_actions: tuple[ItemTableSelectionAction, ...] = ()

    @validator("launch_actions")
    def launch_action_ids_are_unique(cls, value):
        action_ids = [action.id for action in value]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("Tool action IDs must be unique within a provider")
        return value

    class Config:
        allow_mutation = False
        extra = "forbid"


class ToolLaunchResult(BaseModel):
    """Runtime data returned by a provider after preparing a tool launch."""

    url: AnyHttpUrl | None = None

    class Config:
        allow_mutation = False
        extra = "forbid"


@dataclass(frozen=True)
class ToolContext:
    """Restricted, immutable current-user data passed to trusted providers."""

    user_id: str
    display_name: str | None
    role: str
    group_ids: tuple[str, ...]


class ToolLaunchGrantIssuer(Protocol):
    """Capability offered to a provider for issuing current-user tool launch grants."""

    def issue(self, client_id: str, lifetime_seconds: int = 60) -> str:
        """Create and return a raw, single-use launch code."""


class ToolProvider(ABC):
    """Base class implemented by built-in and installed tool providers."""

    id: ClassVar[str]
    metadata: ClassVar[ToolMetadata]
    blueprint: ClassVar[Blueprint | None] = None
    route_auth: ClassVar[ToolRouteAuth] = ToolRouteAuth.BROWSER

    def is_available(self, context: ToolContext) -> bool:
        """Return whether this provider is catalogued and launchable for ``context``."""
        return True

    def authenticate_service_request(self) -> bool:
        """Authenticate one request when ``route_auth`` is ``SERVICE``.

        Service-authenticated providers must override this method. Browser
        authentication is supplied by the tool framework.
        """
        return False

    @abstractmethod
    def launch(
        self,
        context: ToolContext,
        grants: ToolLaunchGrantIssuer,
    ) -> ToolLaunchResult:
        """Prepare and return a launch for ``context``."""
