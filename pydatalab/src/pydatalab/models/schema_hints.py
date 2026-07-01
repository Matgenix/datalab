"""Typed definitions of the ``datalab_*`` ``json_schema_extra`` hints.

Item models tag fields and model config with ``datalab_*`` keys that the API and
web UI read back (summary projection, field rendering, grouping, ...). The models
below list the valid keys; :func:`validate_schema_hints` checks them at
registration, and ``invoke dev.generate-schemas`` exports them as JSON schemas.

Call sites keep writing plain dicts. The field names here match the literal keys,
and the attribute docstrings become the descriptions in the generated schema.
"""

from pydantic import ConfigDict, ValidationError

from pydatalab.models.utils import BaseModel


class DatalabUIFieldExtra(BaseModel):
    """UI rendering hints attached to a field via ``json_schema_extra={"datalab_ui": {...}}``."""

    model_config = ConfigDict(extra="forbid")

    include_field_in_summary: bool | None = None
    """Also show this field in list/summary views."""

    hidden: bool | None = None
    """Store but don't render this field (e.g. a companion unit field)."""

    multiline: bool | None = None
    """Render a string as a multi-line textarea."""

    section: str | None = None
    """Group fields sharing this section string into their own card."""

    ref_types: list[str] | None = None
    """Render an item-reference widget restricted to these item types."""

    unit_field: str | None = None
    """Companion field holding the unit; renders a value box + unit dropdown."""

    units: list[str] | None = None
    """Unit options for the dropdown (with ``unit_field``)."""

    default_unit: str | None = None
    """Default unit for the dropdown."""


class DatalabFieldExtra(BaseModel):
    """Datalab hints attached to a field via ``json_schema_extra``."""

    model_config = ConfigDict(extra="forbid")

    datalab_ui: DatalabUIFieldExtra | None = None
    """UI rendering hints consumed by the web app's custom-fields panel."""

    datalab_exclude_from_db: bool | None = None
    """Don't persist this field to the database (block models)."""

    datalab_exclude_from_load: bool | None = None
    """Don't populate this field when loading from the database (block models)."""


class DatalabUIModelExtra(BaseModel):
    """UI rendering hints attached to a model's config via
    ``model_config['json_schema_extra']['datalab_ui']``."""

    model_config = ConfigDict(extra="forbid")

    hidden_fields: list[str] | None = None
    """Inherited field names to hide from the UI for this item type."""

    color: str | None = None
    """Accent colour (CSS hex) used for this item type in the UI."""

    section_title: str | None = None
    """Title of the default custom-fields card."""


class DatalabModelExtra(BaseModel):
    """Datalab hints attached to a model via ``model_config['json_schema_extra']``."""

    model_config = ConfigDict(extra="forbid")

    datalab_ui: DatalabUIModelExtra | None = None
    """UI hints consumed by the web app for this item type as a whole."""

    datalab_base_type: str | None = None
    """Built-in type this derives from, when not inferable from the class hierarchy."""


def _datalab_hint_keys(extra: dict) -> dict:
    """Pick the ``datalab_*`` hint keys out of a raw ``json_schema_extra`` dict.

    Only ``datalab_*`` keys are returned, so legitimate standard JSON Schema keys
    (e.g. ``format``) declared in the same dict are left untouched.
    """
    return {k: v for k, v in extra.items() if k.startswith("datalab_")}


def validate_schema_hints(model: type[BaseModel]) -> None:
    """Validate the datalab ``json_schema_extra`` hints on ``model`` and its fields.

    Checks the model-level config extras against :class:`DatalabModelExtra` and
    each field's extras against :class:`DatalabFieldExtra`, raising ``ValueError``
    that names the offending type/field if an unknown or mistyped ``datalab_*``
    hint is found. Non-datalab keys are ignored.
    """
    name = getattr(model, "__name__", str(model))

    model_extra = model.model_config.get("json_schema_extra")
    if isinstance(model_extra, dict):
        try:
            DatalabModelExtra(**_datalab_hint_keys(model_extra))
        except ValidationError as exc:
            raise ValueError(f"Invalid datalab model schema hints on {name!r}: {exc}") from exc

    for field_name, field in model.model_fields.items():
        field_extra = field.json_schema_extra
        if not isinstance(field_extra, dict):
            continue
        try:
            DatalabFieldExtra(**_datalab_hint_keys(field_extra))
        except ValidationError as exc:
            raise ValueError(
                f"Invalid datalab schema hints on {name!r}.{field_name!r}: {exc}"
            ) from exc
