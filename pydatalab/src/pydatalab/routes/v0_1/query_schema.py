"""Schema introspection for the advanced-search query builder.

Builds, per queryable type, the registry of fields and operators that
:mod:`pydatalab.routes.v0_1.query` exposes through ``/query-schema`` and uses to
validate and compile incoming query rules. Kept separate from the route handlers
and the rule compiler so that "what can be queried" stays independent of "how a
query request is served".
"""

import re
from datetime import datetime, timezone
from typing import Any

from pydatalab.models import ITEM_MODELS
from pydatalab.models.collections import Collection
from pydatalab.models.people import Group, Person

QUERY_VIEWS: dict[str, dict] = {
    "samples": {
        "resource": "items",
        "collection": "items",
        "types": ["samples", "cells"],
        "model_by_type": ITEM_MODELS,
        "view_contexts": ["samples"],
        "default_sort": [("date", -1)],
    },
    "starting_materials": {
        "resource": "items",
        "collection": "items",
        "types": ["starting_materials"],
        "model_by_type": ITEM_MODELS,
        "view_contexts": ["startingMaterials", "starting_materials"],
        "default_sort": [("date", -1)],
    },
    "equipment": {
        "resource": "items",
        "collection": "items",
        "types": ["equipment"],
        "model_by_type": ITEM_MODELS,
        "view_contexts": ["equipment"],
        "default_sort": [("date", -1)],
    },
    "collections": {
        "resource": "collections",
        "collection": "collections",
        "types": ["collections"],
        "model_by_type": {"collections": Collection},
        "view_contexts": ["collections"],
        "default_sort": [("_id", -1)],
    },
    "users": {
        "resource": "users",
        "collection": "users",
        "model": Person,
        "view_contexts": ["users"],
        "default_sort": [("display_name", 1)],
    },
    "groups": {
        "resource": "groups",
        "collection": "groups",
        "model": Group,
        "view_contexts": ["groups"],
        "default_sort": [("display_name", 1)],
    },
}
LIST_VIEWS = QUERY_VIEWS

_SKIP_FIELDS: set[str] = {
    "type",
    "immutable_id",
    "creator_ids",
    "group_ids",
    "blocks_obj",
    "display_order",
    "file_ObjectIds",
    "revision",
    "revisions",
    "version",
    "relationships",
    "files",
    "collections",
    "creators",
    "groups",
}

_FIELD_UI: dict[str, dict] = {
    "name": {"label": "Name", "group": "Basic", "sortable": True},
    "item_id": {"label": "Item ID", "group": "Basic", "sortable": True},
    "refcode": {"label": "Refcode", "group": "Basic", "sortable": True},
    "description": {"label": "Description", "group": "Basic", "sortable": False},
    "date": {"label": "Date", "group": "Basic", "sortable": True},
    "status": {"label": "Status", "group": "Basic", "sortable": True, "groupable": True},
    "chemform": {
        "label": "Formula",
        "group": "Chemistry",
        "sortable": True,
        "editor_override": {"eq": "chemical-formula", "contains": "text"},
    },
    "characteristic_chemical_formula": {
        "label": "Active material formula",
        "group": "Chemistry",
        "sortable": True,
        "editor_override": {"eq": "chemical-formula"},
    },
    "smiles": {"label": "SMILES", "group": "Chemistry", "sortable": False},
    "inchi_key": {"label": "InChI key", "group": "Chemistry", "sortable": False},
    "inchi": {"label": "InChI", "group": "Chemistry", "sortable": False},
    "GHS_codes": {"label": "GHS hazard codes", "group": "Chemistry", "sortable": False},
    "CAS": {"label": "CAS number", "group": "Chemistry", "sortable": False},
    "molar_mass": {"label": "Molar mass (g/mol)", "group": "Chemistry", "sortable": True},
    "characteristic_mass": {
        "label": "Characteristic mass (mg)",
        "group": "Chemistry",
        "sortable": True,
    },
    "characteristic_molar_mass": {
        "label": "Characteristic molar mass",
        "group": "Chemistry",
        "sortable": True,
    },
    "cell_format": {"label": "Cell format", "group": "Cell", "sortable": True, "groupable": True},
    "cell_format_description": {
        "label": "Cell format description",
        "group": "Cell",
        "sortable": False,
    },
    "cell_preparation_description": {
        "label": "Cell preparation",
        "group": "Cell",
        "sortable": False,
    },
    "supplier": {"label": "Supplier", "group": "Provenance", "sortable": True, "groupable": True},
    "location": {"label": "Location", "group": "Provenance", "sortable": True, "groupable": True},
    "manufacturer": {
        "label": "Manufacturer",
        "group": "Provenance",
        "sortable": True,
        "groupable": True,
    },
    "serial_numbers": {"label": "Serial numbers", "group": "Provenance", "sortable": False},
    "contact": {"label": "Contact", "group": "Provenance", "sortable": False},
    "barcode": {"label": "Barcode", "group": "Provenance", "sortable": False},
    "chemical_purity": {"label": "Chemical purity", "group": "Chemistry", "sortable": False},
    "synthesis_description": {
        "label": "Synthesis description",
        "group": "Synthesis",
        "sortable": False,
    },
    "synthesis_constituents": {
        "label": "Synthesis constituent",
        "group": "Synthesis",
        "sortable": False,
    },
    "date_opened": {"label": "Date opened", "group": "Provenance", "sortable": True},
    "last_modified": {"label": "Last modified", "group": "Basic", "sortable": True},
    "active_ion_charge": {"label": "Active ion charge", "group": "Cell", "sortable": True},
    "positive_electrode": {
        "label": "Positive electrode constituent",
        "group": "Cell",
        "sortable": False,
    },
    "negative_electrode": {
        "label": "Negative electrode constituent",
        "group": "Cell",
        "sortable": False,
    },
    "electrolyte": {"label": "Electrolyte constituent", "group": "Cell", "sortable": False},
}


def _parse_dt(s: str) -> datetime:
    s = str(s).rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {s!r}")


def _compile_date_range(path: str, value: Any) -> dict:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("date_range requires [start, end]")
    return {path: {"$gte": _parse_dt(value[0]), "$lte": _parse_dt(value[1])}}


# Per-operator UI metadata (label/editor) alongside the mongo query it compiles to.
# The "compile" lambdas are what `query._compile_rule` actually calls; the rest is
# what `/query-schema` reports to the frontend so it knows what to render.
OPERATORS: dict[str, dict] = {
    "contains": {
        "label": "contains",
        "value_required": True,
        "editor": "text",
        "compile": lambda p, v: {p: {"$regex": re.escape(str(v)), "$options": "i"}},
    },
    "eq": {
        "label": "equals",
        "value_required": True,
        "editor": "text",
        "compile": lambda p, v: {p: v},
    },
    "is_set": {
        "label": "is set",
        "value_required": False,
        "compile": lambda p, v: {p: {"$exists": True, "$nin": [None, ""]}},
    },
    "is_not_set": {
        "label": "is not set",
        "value_required": False,
        "compile": lambda p, v: {"$or": [{p: {"$exists": False}}, {p: None}, {p: ""}]},
    },
    "in": {
        "label": "is one of",
        "value_required": True,
        "editor": "string-list",
        "compile": lambda p, v: {p: {"$in": list(v) if not isinstance(v, list) else v}},
    },
    "gt": {
        "label": "greater than",
        "value_required": True,
        "editor": "number",
        "compile": lambda p, v: {p: {"$gt": v}},
    },
    "lt": {
        "label": "less than",
        "value_required": True,
        "editor": "number",
        "compile": lambda p, v: {p: {"$lt": v}},
    },
    "before": {
        "label": "before",
        "value_required": True,
        "editor": "datetime",
        "compile": lambda p, v: {p: {"$lt": _parse_dt(v)}},
    },
    "after": {
        "label": "after",
        "value_required": True,
        "editor": "datetime",
        "compile": lambda p, v: {p: {"$gt": _parse_dt(v)}},
    },
    "date_range": {
        "label": "in range",
        "value_required": True,
        "editor": "datetime-range",
        "compile": lambda p, v: _compile_date_range(p, v),
    },
    "has_constituent": {
        "label": "contains",
        "value_required": True,
        "editor": "constituent-selector",
        "options_source": "datalab:item-reference",
        "compile": lambda p, v: {
            p: {
                "$elemMatch": {
                    "$or": [
                        {"item.refcode": str(v)},
                        {"item.item_id": str(v)},
                    ]
                }
            }
        },
    },
    "not_has_constituent": {
        "label": "does not contain",
        "value_required": True,
        "editor": "constituent-selector",
        "options_source": "datalab:item-reference",
        "compile": lambda p, v: {
            "$nor": [
                {
                    p: {
                        "$elemMatch": {
                            "$or": [
                                {"item.refcode": str(v)},
                                {"item.item_id": str(v)},
                            ]
                        }
                    }
                }
            ]
        },
    },
}


def _resolve_ref(ref: str, definitions: dict) -> dict:
    name = ref.split("/")[-1]
    return definitions.get(name, {})


def _resolve_schema_node(field_def: dict, definitions: dict) -> dict:
    for candidate in (field_def, *field_def.get("allOf", []), *field_def.get("anyOf", [])):
        ref = candidate.get("$ref", "")
        if ref:
            return _resolve_ref(ref, definitions)
    return field_def


def _json_schema_extra(model: type) -> dict:
    config = getattr(model, "Config", None)
    schema_extra = getattr(config, "schema_extra", {}) if config else {}
    if isinstance(schema_extra, dict):
        return schema_extra

    model_config = getattr(model, "model_config", {})
    if isinstance(model_config, dict):
        return model_config.get("json_schema_extra", {}) or {}

    return {}


def _query_options_list(model: type) -> list | None:
    """Return the explicit query field list for *model*, or ``None`` to use auto-discovery.

    To pin specific fields for a model in the advanced-search UI, add a ``Config``
    class with ``query_options_list`` to that model.  When present it **replaces**
    the automatically derived field registry entirely::

        class Config:
            schema_extra = {
                "query_options_list": [
                    "name",
                    "item_id",
                    "date",
                    {"id": "chemform", "operators": ["eq", "contains"], "label": "Formula"},
                ]
            }

    Each entry is either a plain field-ID string (looks up defaults from the registry)
    or a dict accepted by :func:`_normalise_query_option` (overrides label/operators/path).
    """
    extra = _json_schema_extra(model)
    options = extra.get("query_options_list")
    return options if isinstance(options, list) else None


def _field_to_operators(
    field_def: dict, definitions: dict, field_name: str
) -> tuple[list[str], dict, dict]:
    """Returns (operator_ids, editor_override_per_op, value_schema_override_per_op)."""
    fmt = field_def.get("format", "")
    ftype = field_def.get("type", "")

    ref = ""
    for candidate in (field_def, *field_def.get("allOf", []), *field_def.get("anyOf", [])):
        ref = candidate.get("$ref", "")
        if ref:
            break

    if ref:
        resolved = _resolve_ref(ref, definitions)
        enum_values = resolved.get("enum")
        if enum_values:
            vs = {"enum": enum_values}
            vs_array = {"type": "array", "items": vs}
            ui = _FIELD_UI.get(field_name, {})
            eo = ui.get("editor_override", {"in": "enum", "eq": "enum"})
            if "in" not in eo:
                eo["in"] = "enum"
            if "eq" not in eo:
                eo["eq"] = "enum"
            return ["in", "eq", "is_set"], eo, {"in": vs_array, "eq": vs}

    if fmt == "date-time" or (ftype == "string" and "date" in field_name):
        eo = {"date_range": "datetime-range", "before": "datetime", "after": "datetime"}
        return ["date_range", "before", "after", "is_set"], eo, {}

    if ftype in ("number", "integer"):
        return ["gt", "lt", "eq", "is_set"], {}, {}

    if ftype == "string":
        ui = _FIELD_UI.get(field_name, {})
        eo = dict(ui.get("editor_override", {}))
        return ["contains", "eq", "is_set", "is_not_set"], eo, {}

    return [], {}, {}


def _iter_schema_fields(
    properties: dict, definitions: dict, prefix: str = "", depth: int = 0
) -> list[tuple[str, dict]]:
    fields: list[tuple[str, dict]] = []
    for field_name, field_def in properties.items():
        path = f"{prefix}.{field_name}" if prefix else field_name
        if not prefix and field_name in _SKIP_FIELDS:
            continue

        resolved = _resolve_schema_node(field_def, definitions)
        node = resolved or field_def
        nested_properties = node.get("properties")
        array_items = node.get("items", {})
        array_node = _resolve_schema_node(array_items, definitions) if array_items else {}

        if node.get("type") == "array" and array_node.get("properties") and depth < 3:
            fields.extend(
                _iter_schema_fields(array_node["properties"], definitions, path, depth + 1)
            )
            continue

        if nested_properties and depth < 3:
            fields.extend(_iter_schema_fields(nested_properties, definitions, path, depth + 1))
            continue

        fields.append((path, field_def))

    return fields


def _normalise_query_option(
    option: str | dict, registry: dict[str, dict]
) -> tuple[str, dict] | None:
    if isinstance(option, str):
        return (option, registry[option]) if option in registry else None

    if not isinstance(option, dict):
        return None

    field_id = option.get("id") or option.get("field") or option.get("path")
    if not field_id:
        return None

    base = dict(registry.get(field_id, {}))
    operator_ids = (
        option.get("operators")
        or base.get("operator_ids")
        or [
            "contains",
            "eq",
            "is_set",
        ]
    )
    operator_ids = [op_id for op_id in operator_ids if op_id in OPERATORS]
    if not operator_ids:
        return None

    base.update(
        {
            "mongo_path": option.get("mongo_path")
            or option.get("path")
            or base.get("mongo_path", field_id),
            "label": option.get("label") or base.get("label", field_id.replace("_", " ").title()),
            "group": option.get("group") or base.get("group", "Other"),
            "sortable": option.get("sortable", base.get("sortable", False)),
            "groupable": option.get("groupable", base.get("groupable", False)),
            "operator_ids": operator_ids,
            "editor_override": option.get("editor_override") or base.get("editor_override", {}),
            "value_schema_override": option.get("value_schema_override")
            or base.get("value_schema_override", {}),
        }
    )
    if "subfields" in option:
        base["subfields"] = option["subfields"]

    return field_id, base


def _build_model_field_registry(model: Any, type_id: str) -> dict[str, dict]:
    try:
        schema = model.schema(by_alias=False)
        definitions = schema.get("definitions", {})
        properties = schema.get("properties", {})
    except Exception:
        definitions = {}
        properties = {}

    registry: dict[str, dict] = {}
    for field_name, field_def in _iter_schema_fields(properties, definitions):
        operator_ids, editor_override, value_schema_override = _field_to_operators(
            field_def, definitions, field_name
        )
        if not operator_ids:
            continue

        ui = _FIELD_UI.get(field_name, {})
        label = ui.get("label") or field_name.replace("_", " ").title()
        group = ui.get("group", "Other")
        sortable = ui.get("sortable", field_def.get("type") in ("string", "number", "integer"))
        groupable = ui.get("groupable", False)

        registry[field_name] = {
            "mongo_path": field_name,
            "label": label,
            "group": group,
            "sortable": sortable,
            "groupable": groupable,
            "operator_ids": operator_ids,
            "editor_override": editor_override,
            "value_schema_override": value_schema_override,
        }

    _constituent_fields = {
        "synthesis_constituents": ("Synthesis constituent", "Synthesis"),
        "positive_electrode": ("Positive electrode constituent", "Cell"),
        "negative_electrode": ("Negative electrode constituent", "Cell"),
        "electrolyte": ("Electrolyte constituent", "Cell"),
    }
    for cf_name, (cf_label, cf_group) in _constituent_fields.items():
        if cf_name in properties:
            registry[cf_name] = {
                "mongo_path": cf_name,
                "label": cf_label,
                "group": cf_group,
                "sortable": False,
                "groupable": False,
                "operator_ids": ["has_constituent", "not_has_constituent"],
                "editor_override": {},
                "value_schema_override": {},
            }

    explicit_options = _query_options_list(model)
    if explicit_options:
        explicit_registry: dict[str, dict] = {}
        invalid: list[str] = []
        for option in explicit_options:
            normalised = _normalise_query_option(option, registry)
            if normalised:
                field_id, field_config = normalised
                explicit_registry[field_id] = field_config
            else:
                label = option if isinstance(option, str) else repr(option)
                invalid.append(label)
        if invalid:
            raise ValueError(
                f"{model.__name__}.Config.schema_extra['query_options_list'] contains invalid "
                f"entries: {invalid}. Available fields: {sorted(registry)}"
            )
        if not explicit_registry:
            raise ValueError(
                f"{model.__name__}.Config.schema_extra['query_options_list'] is set but "
                f"produced no valid fields"
            )
        registry = explicit_registry

    return registry


def _build_field_registry(type_id: str) -> dict[str, dict]:
    return _build_model_field_registry(ITEM_MODELS[type_id], type_id)


def _get_field_registry(
    selected_types: list[str], model_by_type: dict | None = None
) -> dict[str, dict]:
    models = model_by_type or ITEM_MODELS
    registries = [_build_model_field_registry(models[t], t) for t in selected_types]
    common_ids = set(registries[0].keys())
    for r in registries[1:]:
        common_ids &= set(r.keys())
    return {fid: registries[0][fid] for fid in common_ids}


def _build_field_registry_for_view(
    list_view: str, view: dict, selected_types: list[str] | None = None
) -> dict[str, dict]:
    if view.get("model"):
        # single-model view
        return _build_model_field_registry(view["model"], list_view)

    model_by_type = view.get("model_by_type") or ITEM_MODELS
    types = selected_types or view.get("types") or list(model_by_type.keys())
    return _get_field_registry(types, model_by_type)


def _query_type_entry(type_id: str, model_by_type: dict) -> dict:
    model = model_by_type.get(type_id)
    schema = model.schema(by_alias=False) if model else {}
    label = schema.get("title", type_id.replace("_", " ").title())
    description = schema.get("description") or ""
    mro_names = [c.__name__ for c in model.__mro__] if model else []
    parent_type = None
    for t, m in model_by_type.items():
        if t != type_id and m.__name__ in mro_names[1:]:
            parent_type = t
            break

    return {
        "id": type_id,
        "label": label,
        "description": description,
        "parent_type": parent_type,
        "queryable": bool(model and _build_model_field_registry(model, type_id)),
    }


def _model_label(model: Any | None, fallback: str) -> str:
    if not model:
        return fallback
    try:
        return model.schema(by_alias=False).get("title", fallback)
    except Exception:
        return fallback


def _view_capability(list_view: str, view: dict) -> dict:
    if view.get("model_by_type"):
        query_types = [
            _query_type_entry(type_id, view["model_by_type"]) for type_id in view.get("types", [])
        ]
    elif view.get("model"):
        # single model view
        query_types = [_query_type_entry(list_view, {list_view: view["model"]})]
    else:
        query_types = []

    capabilities = {
        "combinators": ["and", "or"],
        "allow_negation": False,
        "max_rules": 50,
        "max_in_values": 100,
        "max_depth": 5 if view.get("resource") == "items" else 0,
    }

    return {
        "isEnabled": any(t["queryable"] for t in query_types),
        "listViewName": list_view,
        "resource": view["resource"],
        "queryRoute": "/query",
        "options": {
            "queryRoute": "/query",
            "listViewName": list_view,
            "resource": view["resource"],
            "query_types": query_types,
            "item_types": query_types,
        },
        "capabilities": capabilities,
    }


def _view_matches_context(view: dict, data_type: str | None) -> bool:
    return bool(data_type and data_type in view.get("view_contexts", []))
