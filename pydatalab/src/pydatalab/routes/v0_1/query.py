import base64
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from flask import Blueprint, jsonify, request

from pydatalab.models import ITEM_MODELS
from pydatalab.mongo import flask_mongo
from pydatalab.permissions import active_users_or_get_only, get_default_permissions
from pydatalab.routes.v0_1.items import collections_lookup, creators_lookup, groups_lookup

QUERY = Blueprint("query", __name__)


@QUERY.before_request
@active_users_or_get_only
def _(): ...


LIST_VIEWS: dict[str, dict] = {
    "samples": {"types": ["samples", "cells"]},
    "starting_materials": {"types": ["starting_materials"]},
    "equipment": {"types": ["equipment"]},
}

_SKIP_FIELDS: set[str] = {
    "type",
    "immutable_id",
    "last_modified",
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
    "synthesis_constituents",
    "positive_electrode",
    "negative_electrode",
    "electrolyte",
}

_FIELD_UI: dict[str, dict] = {
    "name": {"label": "Name", "group": "Basic", "sortable": True},
    "item_id": {"label": "Item ID", "group": "Basic", "sortable": True},
    "refcode": {"label": "Refcode", "group": "Basic", "sortable": True},
    "description": {"label": "Description", "group": "Basic", "sortable": False},
    "date": {"label": "Date", "group": "Basic", "sortable": True},
    "status": {"label": "Status", "group": "Basic", "sortable": True},
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
    "cell_format": {"label": "Cell format", "group": "Cell", "sortable": True},
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
    "supplier": {"label": "Supplier", "group": "Provenance", "sortable": True},
    "location": {"label": "Location", "group": "Provenance", "sortable": True},
    "manufacturer": {"label": "Manufacturer", "group": "Provenance", "sortable": True},
    "serial_numbers": {"label": "Serial numbers", "group": "Provenance", "sortable": False},
    "contact": {"label": "Contact", "group": "Provenance", "sortable": False},
    "barcode": {"label": "Barcode", "group": "Provenance", "sortable": False},
    "chemical_purity": {"label": "Chemical purity", "group": "Chemistry", "sortable": False},
    "synthesis_description": {
        "label": "Synthesis description",
        "group": "Synthesis",
        "sortable": False,
    },
    "date_opened": {"label": "Date opened", "group": "Provenance", "sortable": True},
}

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


def _resolve_ref(ref: str, definitions: dict) -> dict:
    name = ref.split("/")[-1]
    return definitions.get(name, {})


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


def _build_field_registry(type_id: str) -> dict[str, dict]:
    model = ITEM_MODELS[type_id]
    schema = model.schema(by_alias=False)
    definitions = schema.get("definitions", {})
    properties = schema.get("properties", {})

    registry: dict[str, dict] = {}
    for field_name, field_def in properties.items():
        if field_name in _SKIP_FIELDS:
            continue

        operator_ids, editor_override, value_schema_override = _field_to_operators(
            field_def, definitions, field_name
        )
        if not operator_ids:
            continue

        ui = _FIELD_UI.get(field_name, {})
        label = ui.get("label") or field_name.replace("_", " ").title()
        group = ui.get("group", "Other")
        sortable = ui.get("sortable", field_def.get("type") in ("string", "number", "integer"))

        registry[field_name] = {
            "mongo_path": field_name,
            "label": label,
            "group": group,
            "sortable": sortable,
            "operator_ids": operator_ids,
            "editor_override": editor_override,
            "value_schema_override": value_schema_override,
        }

    return registry


def _get_field_registry(selected_types: list[str]) -> dict[str, dict]:
    registries = [_build_field_registry(t) for t in selected_types]
    common_ids = set(registries[0].keys())
    for r in registries[1:]:
        common_ids &= set(r.keys())
    return {fid: registries[0][fid] for fid in common_ids}


def _compile_rule(rule: dict, field_registry: dict) -> dict:
    field_id = rule.get("field")
    op_id = rule.get("operator")
    value = rule.get("value")

    field_def = field_registry.get(field_id)
    if not field_def:
        raise ValueError(f"Unknown field: {field_id!r}")
    if op_id not in field_def["operator_ids"]:
        raise ValueError(f"Operator {op_id!r} not valid for field {field_id!r}")

    op_def = OPERATORS.get(op_id or "")
    if not op_def:
        raise ValueError(f"Unknown operator: {op_id!r}")
    if op_def["value_required"] and value is None:
        raise ValueError(f"Operator {op_id!r} on field {field_id!r} requires a value")

    try:
        return op_def["compile"](field_def["mongo_path"], value)
    except Exception as exc:
        raise ValueError(f"Invalid value for {field_id!r}/{op_id!r}: {exc}") from exc


def _compile_node(node: dict, field_registry: dict, depth: int = 0) -> dict:
    if depth > 5:
        raise ValueError("Query too deeply nested (max depth 5)")
    kind = node.get("kind")
    if kind == "rule":
        return _compile_rule(node, field_registry)
    if kind == "group":
        children = [_compile_node(c, field_registry, depth + 1) for c in node.get("children", [])]
        children = [c for c in children if c]
        if not children:
            return {}
        if len(children) == 1:
            return children[0]
        return {"$and" if node.get("combinator", "and") == "and" else "$or": children}
    raise ValueError(f"Unknown node kind: {kind!r}")


def _encode_cursor(oid: ObjectId) -> str:
    return base64.urlsafe_b64encode(str(oid).encode()).decode()


def _decode_cursor(s: str) -> ObjectId:
    return ObjectId(base64.urlsafe_b64decode(s.encode()).decode())


def _error(status: int, code: str, message: str, details: list | None = None):
    return jsonify(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or [],
                "request_id": str(uuid.uuid4())[:8],
            }
        }
    ), status


_SUMMARY_PROJECT = {
    "_id": 0,
    "item_id": 1,
    "name": 1,
    "chemform": 1,
    "type": 1,
    "date": 1,
    "refcode": 1,
    "status": 1,
    "characteristic_chemical_formula": 1,
    "nblocks": {"$size": "$display_order"},
    "nfiles": {"$size": "$file_ObjectIds"},
    "blocks": {
        "$map": {
            "input": {"$objectToArray": {"$ifNull": ["$blocks_obj", {}]}},
            "as": "b",
            "in": {"blocktype": "$$b.v.blocktype", "title": "$$b.v.title"},
        }
    },
    "creators": {"display_name": 1, "gravatar_hash": 1},
    "groups": {"display_name": 1, "group_id": 1},
    "collections": {"collection_id": 1, "title": 1},
}


@QUERY.route("/item-types", methods=["GET"])
def get_item_types():
    list_view = request.args.get("list_view")
    if not list_view:
        return _error(400, "MISSING_PARAM", "list_view is required")
    view = LIST_VIEWS.get(list_view)
    if not view:
        return _error(404, "NOT_FOUND", f"Unknown list_view: {list_view!r}")

    from pydatalab.models import ITEM_MODELS as _IM

    result = []
    for type_id in view["types"]:
        model = _IM.get(type_id)
        schema = model.schema(by_alias=False) if model else {}
        label = schema.get("title", type_id.replace("_", " ").title())
        description = schema.get("description") or ""
        mro_names = [c.__name__ for c in model.__mro__] if model else []
        parent_type = None
        for t, m in _IM.items():
            if t != type_id and m.__name__ in mro_names[1:]:
                parent_type = t
                break

        result.append(
            {
                "id": type_id,
                "label": label,
                "description": description,
                "parent_type": parent_type,
                "queryable": True,
            }
        )

    return jsonify({"list_view": list_view, "item_types": result})


@QUERY.route("/item-query-schema", methods=["GET"])
def get_query_schema():
    list_view = request.args.get("list_view")
    if not list_view:
        return _error(400, "MISSING_PARAM", "list_view is required")
    view = LIST_VIEWS.get(list_view)
    if not view:
        return _error(404, "NOT_FOUND", f"Unknown list_view: {list_view!r}")

    selected_types = request.args.getlist("item_type") or [view["types"][0]]
    for t in selected_types:
        if t not in ITEM_MODELS:
            return _error(404, "NOT_FOUND", f"Unknown item type: {t!r}")
        if t not in view["types"]:
            return _error(422, "INVALID_TYPE", f"Type {t!r} is not in list_view {list_view!r}")

    field_registry = _get_field_registry(selected_types)

    fields = []
    _group_order = {
        "Basic": 0,
        "Chemistry": 1,
        "Cell": 2,
        "Synthesis": 3,
        "Provenance": 4,
        "Other": 9,
    }
    for field_id, fdef in sorted(
        field_registry.items(), key=lambda x: (_group_order.get(x[1]["group"], 9), x[0])
    ):
        eo = fdef.get("editor_override", {})
        vs_override = fdef.get("value_schema_override", {})
        operators = []
        for op_id in fdef["operator_ids"]:
            op_def = OPERATORS[op_id]
            entry: dict = {
                "id": op_id,
                "label": op_def["label"],
                "value_required": op_def["value_required"],
            }
            if op_def.get("editor") or op_id in eo:
                entry["editor"] = eo.get(op_id, op_def.get("editor", "text"))
            if op_id in vs_override:
                entry["value_schema"] = vs_override[op_id]
            operators.append(entry)
        fields.append(
            {
                "id": field_id,
                "label": fdef["label"],
                "group": fdef["group"],
                "sortable": fdef["sortable"],
                "operators": operators,
            }
        )

    common_type_id = selected_types[0]
    model = ITEM_MODELS[common_type_id]
    common_label = model.schema(by_alias=False).get("title", common_type_id)

    return jsonify(
        {
            "version": "1.0",
            "list_view": list_view,
            "selected_item_types": [
                {"id": t, "label": ITEM_MODELS[t].schema(by_alias=False).get("title", t)}
                for t in selected_types
            ],
            "common_type": {"id": common_type_id, "label": common_label},
            "capabilities": {
                "combinators": ["and", "or"],
                "allow_negation": False,
                "max_depth": 5,
                "max_rules": 50,
                "max_in_values": 100,
            },
            "fields": fields,
        }
    )


@QUERY.route("/item-query", methods=["POST"])
def run_query():
    body = request.get_json(silent=True)
    if not body:
        return _error(400, "MALFORMED_REQUEST", "Request body must be JSON")

    list_view = body.get("list_view")
    if not list_view or list_view not in LIST_VIEWS:
        return _error(400, "MISSING_PARAM", "list_view is required")

    view = LIST_VIEWS[list_view]
    item_types = body.get("item_types")
    if not item_types or not isinstance(item_types, list):
        return _error(400, "MISSING_PARAM", "item_types must be a non-empty array")

    for t in item_types:
        if t not in ITEM_MODELS:
            return _error(404, "NOT_FOUND", f"Unknown item type: {t!r}")
        if t not in view["types"]:
            return _error(422, "INVALID_TYPE", f"Type {t!r} is not in list_view {list_view!r}")

    field_registry = _get_field_registry(item_types)
    where = body.get("where", {"kind": "group", "combinator": "and", "children": []})

    try:
        compiled_filter = _compile_node(where, field_registry)
    except ValueError as exc:
        return _error(422, "INVALID_QUERY", str(exc))

    page_opts = body.get("page") or {}
    limit = min(int(page_opts.get("limit", 50)), 200)
    cursor = page_opts.get("cursor")

    match: dict = {"type": {"$in": item_types}}
    match.update(get_default_permissions(user_only=False, inherit_from_collections=False))
    if compiled_filter:
        match = {"$and": [match, compiled_filter]}

    if cursor:
        try:
            cursor_clause = {"_id": {"$gt": _decode_cursor(cursor)}}
            match = (
                {"$and": [match, cursor_clause]}
                if "$and" not in match
                else {**match, "$and": match["$and"] + [cursor_clause]}
            )
        except Exception:
            return _error(400, "INVALID_CURSOR", "Cursor is invalid")

    sort_spec = body.get("sort") or [{"field": "date", "direction": "desc"}]
    mongo_sort: list[tuple] = []
    for s in sort_spec:
        f = s.get("field")
        direction = -1 if s.get("direction", "desc") == "desc" else 1
        if (
            f
            and f in field_registry
            and field_registry[f].get("mongo_path")
            and field_registry[f]["sortable"]
        ):
            mongo_sort.append((field_registry[f]["mongo_path"], direction))
    mongo_sort = mongo_sort or [("date", -1)]
    mongo_sort.append(("_id", 1))

    pipeline = [
        {"$match": match},
        {"$sort": dict(mongo_sort)},
        {"$limit": limit + 1},
        {"$lookup": creators_lookup()},
        {"$lookup": groups_lookup()},
        {"$lookup": collections_lookup()},
        {"$project": _SUMMARY_PROJECT},
    ]

    raw = list(flask_mongo.db.items.aggregate(pipeline))
    has_more = len(raw) > limit
    items = raw[:limit]

    next_cursor = None
    if has_more and items:
        last_doc = list(
            flask_mongo.db.items.find({"refcode": items[-1]["refcode"]}, {"_id": 1}).limit(1)
        )
        if last_doc:
            next_cursor = _encode_cursor(last_doc[0]["_id"])

    common_type_id = item_types[0]
    return jsonify(
        {
            "query": {
                "common_type": {
                    "id": common_type_id,
                    "label": ITEM_MODELS[common_type_id]
                    .schema(by_alias=False)
                    .get("title", common_type_id),
                },
                "selected_item_types": item_types,
            },
            "items": items,
            "page": {"limit": limit, "next_cursor": next_cursor, "has_more": has_more},
        }
    )


@QUERY.route("/query-options/<source_id>", methods=["GET"])
def get_query_options(source_id: str):
    if source_id != "datalab:item-reference":
        return _error(404, "NOT_FOUND", f"Unknown options source: {source_id!r}")

    q = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 20)), 100)
    item_types = request.args.getlist("item_type") or list(ITEM_MODELS.keys())

    match: dict = {"type": {"$in": item_types}}
    match.update(get_default_permissions(user_only=False, inherit_from_collections=False))
    if q:
        escaped = re.escape(q)
        match["$or"] = [
            {"name": {"$regex": escaped, "$options": "i"}},
            {"item_id": {"$regex": escaped, "$options": "i"}},
            {"refcode": {"$regex": escaped, "$options": "i"}},
        ]

    cursor_str = request.args.get("cursor")
    if cursor_str:
        try:
            match["_id"] = {"$gt": _decode_cursor(cursor_str)}
        except Exception:
            return _error(400, "INVALID_CURSOR", "Cursor is invalid")

    docs = list(
        flask_mongo.db.items.find(
            match, {"_id": 1, "item_id": 1, "name": 1, "refcode": 1, "type": 1, "chemform": 1}
        )
        .sort("_id", 1)
        .limit(limit + 1)
    )

    has_more = len(docs) > limit
    docs = docs[:limit]

    options = [
        {
            "value": d.get("refcode") or d["item_id"],
            "label": f"{d.get('name') or d['item_id']} — {d.get('refcode') or d['item_id']}",
            "metadata": {
                "item_id": d["item_id"],
                "refcode": d.get("refcode"),
                "name": d.get("name"),
                "chemform": d.get("chemform"),
                "type": {
                    "id": d["type"],
                    "label": ITEM_MODELS.get(d["type"], type("", (), {"schema": lambda **_: {}})())
                    .schema(by_alias=False)
                    .get("title", d["type"]),
                },
            },
        }
        for d in docs
    ]

    return jsonify(
        {
            "options": options,
            "next_cursor": _encode_cursor(docs[-1]["_id"]) if has_more and docs else None,
            "has_more": has_more,
        }
    )
