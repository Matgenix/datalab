import datetime
import json

from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, jsonify, request
from flask_login import current_user
from pydantic import ValidationError

from pydatalab.config import CONFIG
from pydatalab.logger import LOGGER, logged_route
from pydatalab.models.tags import Tag
from pydatalab.models.utils import UserRole
from pydatalab.mongo import (
    TAGS_FTS_FIELDS,
    build_search_pipeline,
    flask_mongo,
    insert_pydantic_model_fork_safe,
)
from pydatalab.permissions import (
    PUBLIC_USER_ID,
    active_users_or_get_only,
    get_default_permissions,
)
from pydatalab.routes.v0_1.items import creators_lookup, groups_lookup

TAGS = Blueprint("tags", __name__)


@TAGS.before_request
@active_users_or_get_only
def _(): ...


def _parse_object_id(raw: str) -> ObjectId | None:
    """Parse a string into an ObjectId, returning None if it is not valid."""
    try:
        return ObjectId(raw)
    except (InvalidId, TypeError):
        return None


def _name_conflict_exists(
    name: str,
    creator_ids: list[ObjectId],
    group_ids: list[ObjectId],
    exclude_id: ObjectId | None = None,
) -> bool:
    """Whether a tag with `name` already exists in the same uniqueness scope.

    The scope is determined by the tag's audience:
        - group-shared (`group_ids` set): names are unique within each shared
          group, regardless of who created the tag;
        - personal (`creator_ids` set, no groups): names are unique among the
          owner's own tags;
        - global (no owner): names are unique among global tags.

    Same-named tags in *different* scopes are allowed; `immutable_id` is the
    unique identifier.
    """
    query: dict = {"name": name}
    if exclude_id is not None:
        query["_id"] = {"$ne": exclude_id}

    if group_ids:
        query["group_ids"] = {"$in": list(group_ids)}
    elif creator_ids:
        query["creator_ids"] = {"$in": list(creator_ids)}
    else:
        query["creator_ids"] = []

    return flask_mongo.db.tags.find_one(query, {"_id": 1}) is not None


def _authorize_tag_ownership(
    creator_ids: list[ObjectId], group_ids: list[ObjectId]
) -> tuple | None:
    """Check whether the current user is allowed to author a tag with the given ownership.

    Returns `None` if allowed, otherwise a Flask `(response, status)` error tuple.

    Policy (see plan "Who may create/edit privileged tags"):
        - Admins may author any tag.
        - Global tags (empty `creator_ids`) require admin.
        - Group tags (`group_ids` set) require admin or a manager of *every* named group.
        - Personal tags are allowed for any authenticated user.
    """
    # In testing mode without a logged-in user, auth is disabled globally.
    if CONFIG.TESTING and not current_user.is_authenticated:
        return None

    if current_user.is_authenticated and current_user.role == UserRole.ADMIN:
        return None

    if not creator_ids:
        return (
            jsonify(
                status="error",
                message="Only administrators can create global tags.",
            ),
            403,
        )

    if group_ids:
        managed_count = flask_mongo.db.groups.count_documents(
            {"_id": {"$in": group_ids}, "managers": current_user.person.immutable_id}
        )
        if managed_count != len(set(group_ids)):
            return (
                jsonify(
                    status="error",
                    message="You must be a manager of every group a tag is shared with.",
                ),
                403,
            )

    return None


def _tag_scope(creator_ids: list[ObjectId], group_ids: list[ObjectId]) -> str:
    """Classify why the current user can see a tag: 'global', 'owner', or 'group'.

    'other' is only reachable by an admin in super-user mode viewing a tag that is
    neither global, owned, nor shared with one of their groups.
    """
    if not creator_ids or PUBLIC_USER_ID in creator_ids:
        return "global"
    if current_user.is_authenticated and current_user.person is not None:
        if current_user.person.immutable_id in creator_ids:
            return "owner"
        user_group_ids = {group.immutable_id for group in (current_user.person.groups or [])}
        if user_group_ids.intersection(group_ids):
            return "group"
    return "other"


def _tag_editable(creator_ids: list[ObjectId]) -> bool:
    """Whether the current user may edit/delete a tag with the given owners.

    Only the tag's creators, or an admin can edit. Global tags (empty
    `creator_ids`) are editable by admins
    only. This is a transient, per-request hint and is never persisted.
    """
    # In testing mode without a logged-in user, auth is disabled globally.
    if CONFIG.TESTING and not current_user.is_authenticated:
        return True
    if current_user.is_authenticated and current_user.role == UserRole.ADMIN:
        return True
    if current_user.is_authenticated and current_user.person is not None:
        return current_user.person.immutable_id in creator_ids
    return False


@TAGS.route("/tags", methods=["GET"])
def get_tags():
    """Return all tags usable by the current user (global + own + group-shared).

    Each tag also carries a per-request `editable` hint derived from the current
    user (whether they may edit/delete it); it is never persisted.
    """
    tags = flask_mongo.db.tags.aggregate(
        [
            {"$match": get_default_permissions(user_only=False)},
            {"$lookup": creators_lookup()},
            {"$lookup": groups_lookup()},
            {"$sort": {"_id": -1}},
        ]
    )

    data = []
    for doc in tags:
        tag = Tag(**doc).model_dump(mode="json")
        tag["editable"] = _tag_editable(doc.get("creator_ids") or [])
        data.append(tag)

    return jsonify({"status": "success", "data": data})


@TAGS.route("/search-tags", methods=["GET"])
@TAGS.route("/search/tags", methods=["GET"])
def search_tags():
    """Perform a free-text search over the tags usable by the current user.

    GET parameters:
        query: String with the search terms.
        nresults: Maximum number of results (default 100).

    Returns:
        A list of `{type, immutable_id, name, description, color, scope}` dictionaries
        in order of descending match score, suitable for use as tag references. `scope`
        is one of 'global'/'owner'/'group' (see `_tag_scope`); `creator_ids`/`group_ids`
        are used only to derive it and are not returned.
    """
    query = request.args.get("query", type=str)
    nresults = request.args.get("nresults", default=100, type=int)

    if not query:
        return jsonify({"status": "error", "message": "No query provided."}), 400

    permissions = get_default_permissions(user_only=False)
    pipeline = build_search_pipeline(query, TAGS_FTS_FIELDS, permissions)
    pipeline.append({"$limit": nresults})
    pipeline.append(
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "description": 1,
                "color": 1,
                "creator_ids": 1,
                "group_ids": 1,
            }
        }
    )

    data = [
        {
            "type": "tags",
            "immutable_id": str(doc["_id"]),
            "name": doc.get("name"),
            "description": doc.get("description"),
            "color": doc.get("color"),
            "scope": _tag_scope(doc.get("creator_ids") or [], doc.get("group_ids") or []),
        }
        for doc in flask_mongo.db.tags.aggregate(pipeline)
    ]

    return jsonify({"status": "success", "data": data}), 200


@TAGS.route("/tags", methods=["PUT"])
def create_tag():
    request_json = request.get_json()
    data = request_json.get("data", {})

    if not current_user.is_authenticated and not CONFIG.TESTING:
        return (
            jsonify(
                status="error",
                message="Unable to create a tag without user authentication.",
            ),
            401,
        )

    name = data.get("name")
    if not name:
        return jsonify(status="error", message="A tag name is required."), 400

    # Resolve the requested ownership: an explicit (possibly empty) `creator_ids`
    # signals global/assigned ownership; otherwise the tag is personal to the caller.
    if "creator_ids" in data:
        creator_ids = [ObjectId(c) for c in data["creator_ids"]]
    elif current_user.is_authenticated:
        creator_ids = [current_user.person.immutable_id]
    else:
        # Only reachable under CONFIG.TESTING
        creator_ids = [PUBLIC_USER_ID]
    group_ids = [ObjectId(g) for g in data.get("group_ids", [])]

    auth_error = _authorize_tag_ownership(creator_ids, group_ids)
    if auth_error is not None:
        return auth_error

    # Enforce name uniqueness within this tag's scope (global / personal / group).
    if _name_conflict_exists(name, creator_ids, group_ids):
        return (
            jsonify(
                status="error",
                message=f"A tag named {name!r} already exists in this scope.",
            ),
            409,  # 409: Conflict
        )

    try:
        tag = Tag(
            name=name,
            description=data.get("description"),
            color=data.get("color"),
            creator_ids=creator_ids,
            group_ids=group_ids,
            last_modified=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )
    except ValidationError as error:
        return (
            jsonify(status="error", message="Unable to create the tag.", output=str(error)),
            400,
        )

    tag.immutable_id = insert_pydantic_model_fork_safe(tag, "tags")

    return jsonify({"status": "success", "data": json.loads(tag.model_dump_json())}), 201


@TAGS.route("/tags/<tag_id>", methods=["PATCH"])
@logged_route
def save_tag(tag_id):
    object_id = _parse_object_id(tag_id)
    if object_id is None:
        return jsonify(status="error", message=f"Invalid tag ID {tag_id!r}."), 400

    request_json = request.get_json()
    updated_data = request_json.get("data")

    if not updated_data:
        return (
            jsonify(status="error", message="No data provided to update the tag with."),
            204,  # 204: No content
        )

    # Ownership and identity are not editable through this endpoint.
    for key in ("_id", "immutable_id", "type", "creators", "creator_ids", "groups", "group_ids"):
        updated_data.pop(key, None)

    updated_data["last_modified"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    tag = flask_mongo.db.tags.find_one(
        {"_id": object_id, **get_default_permissions(user_only=True)}
    )

    if not tag:
        return (
            jsonify(
                status="error",
                message=f"Unable to find a tag with appropriate permissions and ID {tag_id!r}.",
            ),
            400,
        )

    # Keep names unique within the tag's scope on rename.
    if "name" in updated_data and _name_conflict_exists(
        updated_data["name"],
        tag.get("creator_ids", []),
        tag.get("group_ids", []),
        exclude_id=object_id,
    ):
        return (
            jsonify(
                status="error",
                message=f"A tag named {updated_data['name']!r} already exists in this scope.",
            ),
            409,
        )

    tag.update(updated_data)

    try:
        tag = Tag(**tag).model_dump(exclude={"immutable_id", "creators", "groups"})
    except ValidationError as exc:
        return (
            jsonify(
                status="error",
                message=f"Unable to update tag {tag_id!r} with new data {updated_data}.",
                output=str(exc),
            ),
            400,
        )

    result = flask_mongo.db.tags.update_one({"_id": object_id}, {"$set": tag})

    if result.modified_count != 1:
        return (
            jsonify(
                status="error",
                message=f"Unable to update tag {tag_id!r}.",
                output=result.raw_result,
            ),
            400,
        )

    return jsonify(status="success"), 200


@TAGS.route("/tags/<tag_id>/permissions", methods=["PATCH"])
def update_tag_permissions(tag_id: str):
    """Update the owners/groups of a tag, subject to the tag-authoring policy."""
    object_id = _parse_object_id(tag_id)
    if object_id is None:
        return jsonify(status="error", message=f"Invalid tag ID {tag_id!r}."), 400

    request_json = request.get_json()

    current_tag = flask_mongo.db.tags.find_one(
        {"_id": object_id, **get_default_permissions(user_only=True)},
        {"_id": 1, "name": 1, "creator_ids": 1, "group_ids": 1},
    )

    if not current_tag:
        return (
            jsonify(status="error", message=f"No valid tag found with the given ID {tag_id!r}."),
            401,
        )

    # Contract: a field is only changed when present and non-null. An explicit
    # empty list *clears* that scope (e.g. `creators: []` makes the tag global),
    # whereas omitting the field (or sending null) leaves it unchanged.
    creators_requested = request_json.get("creators") is not None
    groups_requested = request_json.get("groups") is not None

    if not creators_requested and not groups_requested:
        return (
            jsonify(status="error", message="No valid creator or group IDs found in the request."),
            400,
        )

    creator_ids = [
        ObjectId(creator["immutable_id"])
        for creator in (request_json.get("creators") or [])
        if creator.get("immutable_id") is not None
    ]
    group_ids = [
        ObjectId(group["immutable_id"])
        for group in (request_json.get("groups") or [])
        if group.get("immutable_id") is not None
    ]

    if creator_ids:
        found = flask_mongo.db.users.count_documents({"_id": {"$in": creator_ids}})
        if found != len(set(creator_ids)):
            return (
                jsonify(status="error", message="One or more creator IDs not found."),
                400,
            )

    if group_ids:
        found = flask_mongo.db.groups.count_documents({"_id": {"$in": group_ids}})
        if found != len(set(group_ids)):
            return (
                jsonify(status="error", message="One or more group IDs not found."),
                400,
            )

    # The authoring policy applies to the resulting ownership scope.
    new_creator_ids = creator_ids if creators_requested else current_tag.get("creator_ids", [])
    new_group_ids = group_ids if groups_requested else current_tag.get("group_ids", [])
    auth_error = _authorize_tag_ownership(new_creator_ids, new_group_ids)
    if auth_error is not None:
        return auth_error

    # Changing scope must not collide with an existing name in the new scope.
    if _name_conflict_exists(
        current_tag["name"], new_creator_ids, new_group_ids, exclude_id=object_id
    ):
        return (
            jsonify(
                status="error",
                message=f"A tag named {current_tag['name']!r} already exists in the new scope.",
            ),
            409,
        )

    set_op = {}
    if creators_requested:
        set_op["creator_ids"] = creator_ids
    if groups_requested:
        set_op["group_ids"] = group_ids

    LOGGER.debug("Updating tag %s permissions with set op: %s", tag_id, set_op)

    result = flask_mongo.db.tags.update_one(
        {"_id": object_id, **get_default_permissions(user_only=True)},
        {"$set": set_op},
    )

    if result.matched_count != 1:
        return (
            jsonify(
                status="error",
                message="Failed to update permissions: tag not found or insufficient permissions.",
            ),
            400,
        )

    return jsonify(status="success"), 200


@TAGS.route("/tags/<tag_id>", methods=["DELETE"])
def delete_tag(tag_id: str):
    object_id = _parse_object_id(tag_id)
    if object_id is None:
        return jsonify(status="error", message=f"Invalid tag ID {tag_id!r}."), 400

    result = flask_mongo.db.tags.delete_one(
        {"_id": object_id, **get_default_permissions(user_only=True, deleting=True)}
    )

    if result.deleted_count != 1:
        return (
            jsonify(
                status="error",
                message=f"Authorization required to delete tag with ID {tag_id!r}.",
            ),
            401,
        )

    # Best-effort cleanup: drop references to the deleted tag from items' `tags`
    # arrays. Like collection deletion, this is an ownership-agnostic raw update
    # that does NOT go through the item save route, so it neither bumps
    # `last_modified` nor creates a new item version.
    #
    # This hardcodes `items` as `HasTags` collection. Extend it if `HasTags` is
    # applied to other entities. Note that references are not deleted from item_versions
    # so a reference to a deleted tag can survive there.
    flask_mongo.db.items.update_many(
        {"tags": {"$elemMatch": {"immutable_id": object_id, "type": "tags"}}},
        {"$pull": {"tags": {"immutable_id": object_id, "type": "tags"}}},
    )

    return jsonify(status="success"), 200
