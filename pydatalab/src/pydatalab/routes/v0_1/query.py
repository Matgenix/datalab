"""Advanced-search query routes: compiles a query tree built by the frontend's
query builder into a mongo filter and runs it. Field/operator schema discovery
lives in :mod:`pydatalab.routes.v0_1.query_schema`.
"""

import base64
import re
import uuid

from bson import ObjectId
from flask import Blueprint, jsonify, request

from pydatalab.models import ITEM_MODELS
from pydatalab.mongo import flask_mongo
from pydatalab.permissions import active_users_or_get_only, get_default_permissions
from pydatalab.routes.v0_1.items import collections_lookup, creators_lookup, groups_lookup
from pydatalab.routes.v0_1.query_schema import (
    LIST_VIEWS,
    OPERATORS,
    _build_field_registry_for_view,
    _model_label,
    _query_type_entry,
    _view_capability,
    _view_matches_context,
)

QUERY = Blueprint("query", __name__)


@QUERY.before_request
@active_users_or_get_only
def _(): ...


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
    "_id": {"$toString": "$_id"},
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


@QUERY.route("/query-capabilities", methods=["GET"])
def get_query_capabilities():
    data_type = request.args.get("data_type")
    views = [
        {
            "view_contexts": view.get("view_contexts", []),
            **_view_capability(list_view, view),
        }
        for list_view, view in LIST_VIEWS.items()
    ]
    selected = next(
        (
            _view_capability(list_view, view)
            for list_view, view in LIST_VIEWS.items()
            if _view_matches_context(view, data_type)
        ),
        None,
    )

    return jsonify({"data_type": data_type, "advanced_query": selected, "views": views})


@QUERY.route("/query-types", methods=["GET"])
def get_item_types():
    list_view = request.args.get("list_view")
    if not list_view:
        return _error(400, "MISSING_PARAM", "list_view is required")
    view = LIST_VIEWS.get(list_view)
    if not view:
        return _error(404, "NOT_FOUND", f"Unknown list_view: {list_view!r}")
    if view.get("model_by_type"):
        types = view.get("types", [])
        item_types = [_query_type_entry(t, view["model_by_type"]) for t in types]
    elif view.get("model"):
        item_types = [_query_type_entry(list_view, {list_view: view["model"]})]
    else:
        item_types = []

    return jsonify({"list_view": list_view, "item_types": item_types})


@QUERY.route("/query-schema", methods=["GET"])
def get_query_schema():
    list_view = request.args.get("list_view")
    if not list_view:
        return _error(400, "MISSING_PARAM", "list_view is required")
    view = LIST_VIEWS.get(list_view)
    if not view:
        return _error(404, "NOT_FOUND", f"Unknown list_view: {list_view!r}")
    # determine selected types and model map for this view
    if view.get("model_by_type"):
        model_map = view["model_by_type"]
        selected_types = request.args.getlist("item_type") or [view.get("types", [])[0]]
        if not selected_types or selected_types[0] is None:
            return _error(400, "MISSING_PARAM", "item_type is required for this list_view")
        for t in selected_types:
            if t not in model_map:
                return _error(404, "NOT_FOUND", f"Unknown item type: {t!r}")
            if t not in view.get("types", []):
                return _error(422, "INVALID_TYPE", f"Type {t!r} is not in list_view {list_view!r}")
        field_registry = _build_field_registry_for_view(list_view, view, selected_types)
    elif view.get("model"):
        # single-model view; ignore item_type parameter
        model_map = {list_view: view["model"]}
        selected_types = [list_view]
        field_registry = _build_field_registry_for_view(list_view, view, selected_types)
    else:
        return _error(400, "INVALID_VIEW", "This list_view has no model information")

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
            if op_def.get("options_source"):
                entry["options_source"] = op_def["options_source"]
            operators.append(entry)
        fields.append(
            {
                "id": field_id,
                "label": fdef["label"],
                "group": fdef["group"],
                "sortable": fdef["sortable"],
                "groupable": fdef.get("groupable", False),
                "operators": operators,
            }
        )

    common_type_id = selected_types[0]
    model = model_map[common_type_id]
    common_label = model.schema(by_alias=False).get("title", common_type_id)

    return jsonify(
        {
            "version": "1.0",
            "list_view": list_view,
            "selected_item_types": [
                {"id": t, "label": _model_label(model_map.get(t), t)} for t in selected_types
            ],
            "common_type": {"id": common_type_id, "label": common_label},
            "capabilities": {
                "combinators": ["and", "or"],
                "allow_negation": False,
                "max_rules": 50,
                "max_in_values": 100,
                "max_depth": 5 if view.get("resource") == "items" else 0,
            },
            "fields": fields,
        }
    )


@QUERY.route("/query", methods=["POST"])
def run_query():
    body = request.get_json(silent=True)
    if not body:
        return _error(400, "MALFORMED_REQUEST", "Request body must be JSON")

    list_view = body.get("list_view")
    if not list_view or list_view not in LIST_VIEWS:
        return _error(400, "MISSING_PARAM", "list_view is required")

    view = LIST_VIEWS[list_view]
    # determine model map and selected types
    if view.get("model_by_type"):
        model_map = view["model_by_type"]
        item_types = body.get("item_types") or view.get("types", [])
        if not item_types:
            return _error(400, "MISSING_PARAM", "item_types must be a non-empty array")
        for t in item_types:
            if t not in model_map:
                return _error(404, "NOT_FOUND", f"Unknown item type: {t!r}")
            if t not in view.get("types", []):
                return _error(422, "INVALID_TYPE", f"Type {t!r} is not in list_view {list_view!r}")
        field_registry = _build_field_registry_for_view(list_view, view, item_types)
    elif view.get("model"):
        model_map = {list_view: view["model"]}
        item_types = [list_view]
        field_registry = _build_field_registry_for_view(list_view, view, item_types)
    else:
        return _error(400, "INVALID_VIEW", "This list_view has no model information")
    where = body.get("where", {"kind": "group", "combinator": "and", "children": []})

    try:
        compiled_filter = _compile_node(where, field_registry)
    except ValueError as exc:
        return _error(422, "INVALID_QUERY", str(exc))

    page_opts = body.get("page") or {}
    limit = min(int(page_opts.get("limit", 50)), 200)
    cursor = page_opts.get("cursor")

    if view.get("resource") == "items":
        match: dict = {"type": {"$in": item_types}}
    else:
        match = {}
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

    pipeline = [{"$match": match}, {"$sort": dict(mongo_sort)}, {"$limit": limit + 1}]
    if view.get("resource") == "items":
        pipeline.extend(
            [
                {"$lookup": creators_lookup()},
                {"$lookup": groups_lookup()},
                {"$lookup": collections_lookup()},
                {"$project": _SUMMARY_PROJECT},
            ]
        )

    raw = list(flask_mongo.db[view.get("collection")].aggregate(pipeline))
    has_more = len(raw) > limit
    items = raw[:limit]

    next_cursor = None
    if has_more and items:
        raw_id = items[-1].get("_id")
        if raw_id:
            last_id = ObjectId(raw_id) if isinstance(raw_id, str) else raw_id
            next_cursor = _encode_cursor(last_id)

    common_type_id = item_types[0]
    return jsonify(
        {
            "query": {
                "common_type": {
                    "id": common_type_id,
                    "label": model_map[common_type_id]
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
