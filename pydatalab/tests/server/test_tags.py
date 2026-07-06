"""Tests for the tags routes (CRUD, search, usable-scope and authoring guards).

These exercise only the tags collection and its routes; items are not involved
yet (that comes with the `HasTags` mixin in a later step).
"""

import pytest
from bson import ObjectId


@pytest.fixture(autouse=True)
def _isolate_tags(database, group_id):
    """Isolate each test.

    The test database is only dropped per-module, so the `tags` collection (and
    any `managers` we set on the demo group) would otherwise leak between tests.
    Reset both before and after each test to avoid cross-test clashes.
    """
    database.tags.delete_many({})
    database.groups.update_one({"_id": group_id}, {"$set": {"managers": []}})
    yield
    database.tags.delete_many({})
    database.groups.update_one({"_id": group_id}, {"$set": {"managers": []}})


def _create_tag(client, name, description=None, **ownership):
    """Helper to PUT a tag and return the (response, data) pair."""
    data = {"name": name}
    if description is not None:
        data["description"] = description
    data.update(ownership)
    response = client.put("/tags", json={"data": data})
    return response


def test_create_personal_tag_and_list(client, user_id):
    """A normal user can create a personal tag and see it in their listing."""
    response = _create_tag(client, "test_tag", "This is an example")
    assert response.status_code == 201, response.json
    tag = response.json["data"]
    assert tag["type"] == "tags"
    assert tag["name"] == "test_tag"
    # Ownership is coerced to the creating user.
    assert tag["creator_ids"] == [str(user_id)]
    assert tag["immutable_id"]

    response = client.get("/tags")
    assert response.status_code == 200
    names = {t["name"] for t in response.json["data"]}
    assert "test_tag" in names


def test_duplicate_personal_tag_rejected(client):
    """A user cannot create two tags with the same name."""
    assert _create_tag(client, "duplicate-tag").status_code == 201
    response = _create_tag(client, "duplicate-tag")
    assert response.status_code == 409, response.json


def test_uniqueness_is_scope_based(
    client, another_client, admin_client, database, group_id, user_id
):
    """Names are unique within a scope, but the same name is allowed across scopes."""
    # Global names are unique among global tags.
    assert _create_tag(admin_client, "scoped", creator_ids=[]).status_code == 201
    assert _create_tag(admin_client, "scoped", creator_ids=[]).status_code == 409

    # A personal tag may reuse a global name (different scope).
    assert _create_tag(client, "scoped").status_code == 201
    # ...but not twice for the same user.
    assert _create_tag(client, "scoped").status_code == 409
    # A different user may also have their own personal "scoped".
    assert _create_tag(another_client, "scoped").status_code == 201

    # Group names are unique within the group, regardless of creator.
    database.groups.update_one({"_id": group_id}, {"$set": {"managers": [user_id]}})
    assert _create_tag(client, "group-scoped", group_ids=[str(group_id)]).status_code == 201
    # An admin cannot create another tag with the same name in the same group.
    assert _create_tag(admin_client, "group-scoped", group_ids=[str(group_id)]).status_code == 409


def test_global_tag_requires_admin(client, admin_client):
    """Only an admin may create a global tag (empty creator_ids)."""
    response = _create_tag(client, "global-from-user", creator_ids=[])
    assert response.status_code == 403, response.json

    response = _create_tag(admin_client, "global-from-admin", creator_ids=[])
    assert response.status_code == 201, response.json
    assert response.json["data"]["creator_ids"] == []


def test_group_tag_requires_manager(client, admin_client, database, group_id, user_id):
    """Group tags require admin or a manager of the named group."""
    # The isolation fixture guarantees the demo user starts as a non-manager.
    response = _create_tag(client, "group-no-manager", group_ids=[str(group_id)])
    assert response.status_code == 403, response.json

    # An admin can always create a group tag.
    response = _create_tag(admin_client, "group-from-admin", group_ids=[str(group_id)])
    assert response.status_code == 201, response.json
    assert response.json["data"]["group_ids"] == [str(group_id)]

    # Once the user manages the group, they may create a group tag too.
    database.groups.update_one({"_id": group_id}, {"$set": {"managers": [user_id]}})
    response = _create_tag(client, "group-from-manager", group_ids=[str(group_id)])
    assert response.status_code == 201, response.json
    assert response.json["data"]["group_ids"] == [str(group_id)]


def test_usable_scope_visibility(client, another_client, admin_client):
    """Users see global + their own tags, but not other users' private tags."""
    assert _create_tag(client, "user-private").status_code == 201
    assert _create_tag(admin_client, "everyone-global", creator_ids=[]).status_code == 201

    # The other user sees the global tag but not the first user's private tag.
    response = another_client.get("/tags")
    assert response.status_code == 200
    names = {t["name"] for t in response.json["data"]}
    assert "everyone-global" in names
    assert "user-private" not in names


def test_search_tags(client, another_client, admin_client, database, group_id, user_id):
    """Free-text search returns reference-shaped results with per-user scope and color."""
    assert (
        _create_tag(admin_client, "searchable-global", creator_ids=[], color="#f1c40f").status_code
        == 201
    )
    assert _create_tag(client, "searchable-private").status_code == 201
    # A group-shared tag, created by a manager of the demo group.
    database.groups.update_one({"_id": group_id}, {"$set": {"managers": [user_id]}})
    assert _create_tag(client, "searchable-group", group_ids=[str(group_id)]).status_code == 201

    response = client.get("/search-tags", query_string={"query": "searchable"})
    assert response.status_code == 200, response.json
    results = {r["name"]: r for r in response.json["data"]}
    assert {"searchable-global", "searchable-private", "searchable-group"} <= set(results)
    for result in response.json["data"]:
        assert result["type"] == "tags"
        assert result["immutable_id"]

    # `scope` reflects why the current user can see each tag, and `color` is returned.
    assert results["searchable-global"]["scope"] == "global"
    assert results["searchable-private"]["scope"] == "owner"
    assert results["searchable-group"]["scope"] == "owner"  # the creator
    assert results["searchable-global"]["color"] == "#f1c40f"

    # Another member of the group sees the group tag with 'group' scope (not the creator).
    response = another_client.get("/search-tags", query_string={"query": "searchable-group"})
    group_results = {r["name"]: r for r in response.json["data"]}
    assert group_results["searchable-group"]["scope"] == "group"

    # The empty-query case is rejected.
    assert client.get("/search-tags", query_string={"query": ""}).status_code == 400

    # An admin is treated like a normal user on GET unless super-user mode
    # (`?sudo=1`) is requested: by default they do NOT see another user's
    # private tag, but they do with sudo. This matches items/collections.
    response = admin_client.get("/search-tags", query_string={"query": "searchable"})
    assert response.status_code == 200
    names = {r["name"] for r in response.json["data"]}
    assert "searchable-global" in names
    assert "searchable-private" not in names

    response = admin_client.get("/search-tags", query_string={"query": "searchable", "sudo": "1"})
    assert response.status_code == 200
    names = {r["name"] for r in response.json["data"]}
    assert {"searchable-global", "searchable-private"} <= names


def test_admin_can_globalize_tag_via_permissions(client, another_client, admin_client):
    """An admin can make a personal tag global by setting an empty creators list."""
    tag_id = _create_tag(client, "to-globalize").json["data"]["immutable_id"]

    # Before: a second user cannot see the personal tag.
    names = {t["name"] for t in another_client.get("/tags").json["data"]}
    assert "to-globalize" not in names

    # Omitting both creators and groups is a no-op error.
    assert admin_client.patch(f"/tags/{tag_id}/permissions", json={}).status_code == 400

    # An explicit empty creators list makes the tag global.
    response = admin_client.patch(f"/tags/{tag_id}/permissions", json={"creators": []})
    assert response.status_code == 200, response.json

    # After: the second user now sees it, with no owner.
    everyone = {t["name"]: t for t in another_client.get("/tags").json["data"]}
    assert "to-globalize" in everyone
    assert everyone["to-globalize"]["creator_ids"] == []


def test_patch_tag(client):
    """A user can rename / re-describe their own tag, but not collide with an existing name."""
    tag_id = _create_tag(client, "patchable", "first").json["data"]["immutable_id"]
    assert _create_tag(client, "patchable-other").status_code == 201

    response = client.patch(f"/tags/{tag_id}", json={"data": {"description": "updated"}})
    assert response.status_code == 200, response.json

    response = client.get("/tags")
    patched = next(t for t in response.json["data"] if t["immutable_id"] == tag_id)
    assert patched["description"] == "updated"

    # Renaming onto an existing name in the same scope is rejected.
    response = client.patch(f"/tags/{tag_id}", json={"data": {"name": "patchable-other"}})
    assert response.status_code == 409, response.json

    # An invalid ID is a 400.
    assert client.patch("/tags/not-an-object-id", json={"data": {"name": "x"}}).status_code == 400


def test_delete_tag(client, another_client):
    """Only the owner (or an admin) can delete a tag."""
    tag_id = _create_tag(client, "deletable").json["data"]["immutable_id"]

    # Another user cannot delete it.
    assert another_client.delete(f"/tags/{tag_id}").status_code == 401

    # The owner can.
    assert client.delete(f"/tags/{tag_id}").status_code == 200

    response = client.get("/tags")
    names = {t["name"] for t in response.json["data"]}
    assert "deletable" not in names


def test_get_tags_editable_hint(client, another_client, admin_client, database, group_id, user_id):
    """`GET /tags` reports whether the current user may edit/delete each tag."""
    own_id = _create_tag(client, "editable-own").json["data"]["immutable_id"]
    global_id = _create_tag(admin_client, "editable-global", creator_ids=[]).json["data"][
        "immutable_id"
    ]

    # The owner may edit their own tag, but not a global one (admin-only).
    by_id = {t["immutable_id"]: t for t in client.get("/tags").json["data"]}
    assert by_id[own_id]["editable"] is True
    assert by_id[global_id]["editable"] is False

    # An admin may edit everything they can see, including the global tag.
    admin_by_id = {t["immutable_id"]: t for t in admin_client.get("/tags").json["data"]}
    assert admin_by_id[global_id]["editable"] is True

    # A group member who is not the creator cannot edit a group tag.
    database.groups.update_one({"_id": group_id}, {"$set": {"managers": [user_id]}})
    group_id_tag = _create_tag(client, "editable-group", group_ids=[str(group_id)]).json["data"][
        "immutable_id"
    ]
    other_by_id = {t["immutable_id"]: t for t in another_client.get("/tags").json["data"]}
    assert other_by_id[group_id_tag]["editable"] is False


def test_item_tag_resolution(client, admin_client, database):
    """Tag references on an item are resolved (and refreshed) on read; deleted tags drop out.

    Also covers the route-level round-trip of the mixed `tags` field (reference + string).
    """
    # A global tag (with a color), so the normal user can use it.
    tag_id = _create_tag(admin_client, "test-resolve-tag", creator_ids=[], color="#abcdef").json[
        "data"
    ]["immutable_id"]

    # Apply it to a sample alongside a custom string, with a deliberately stale inlined name.
    assert (
        client.post("/new-sample/", json={"type": "samples", "item_id": "tag-resolve"}).status_code
        == 201
    )
    save = client.post(
        "/save-item/",
        json={
            "item_id": "tag-resolve",
            "data": {
                "tags": [
                    {"type": "tags", "immutable_id": tag_id, "name": "stale name"},
                    "test-custom-string",
                ]
            },
        },
    )
    assert save.status_code == 200, save.json

    # The stored item keeps only the minimal `{type, immutable_id}` reference —
    # display fields (name/description/color) are not persisted.
    stored = database.items.find_one({"item_id": "tag-resolve"})
    assert [t for t in stored["tags"] if isinstance(t, dict)] == [
        {"type": "tags", "immutable_id": ObjectId(tag_id)}
    ]
    assert "test-custom-string" in stored["tags"]

    def _get_tags():
        resp = client.get("/get-item-data/tag-resolve")
        assert resp.status_code == 200, resp.json
        return resp.json["item_data"]["tags"]

    tags = _get_tags()
    refs = [t for t in tags if isinstance(t, dict)]
    strings = [t for t in tags if isinstance(t, str)]
    # The custom string passes through; the reference resolves to the *current*
    # name, not the stale stored one.
    assert strings == ["test-custom-string"]
    assert len(refs) == 1
    assert refs[0]["immutable_id"] == tag_id
    assert refs[0]["name"] == "test-resolve-tag"
    # The tag's color is inlined on the resolved reference.
    assert refs[0]["color"] == "#abcdef"

    # Renaming the tag is reflected on the next read.
    assert (
        admin_client.patch(
            f"/tags/{tag_id}", json={"data": {"name": "test-resolve-renamed"}}
        ).status_code
        == 200
    )
    refs = [t for t in _get_tags() if isinstance(t, dict)]
    assert refs[0]["name"] == "test-resolve-renamed"

    # A dangling reference (e.g. one surviving in a restored version) is dropped on read.
    database.items.update_one(
        {"item_id": "tag-resolve"},
        {"$push": {"tags": {"type": "tags", "immutable_id": ObjectId()}}},
    )
    tags = _get_tags()
    refs = [t for t in tags if isinstance(t, dict)]
    assert [t for t in tags if isinstance(t, str)] == ["test-custom-string"]
    assert len(refs) == 1
    assert refs[0]["immutable_id"] == tag_id

    # Deleting the tag removes the reference (the custom string survives).
    assert admin_client.delete(f"/tags/{tag_id}").status_code == 200
    assert _get_tags() == ["test-custom-string"]


def test_tags_stripped_on_creation(client, admin_client, database):
    """Tags provided directly at item creation are stored as minimal references too."""
    tag_id = _create_tag(admin_client, "test-create-tag", creator_ids=[], color="#abcdef").json[
        "data"
    ]["immutable_id"]

    response = client.post(
        "/new-sample/",
        json={
            "type": "samples",
            "item_id": "tag-on-create",
            "tags": [
                {"type": "tags", "immutable_id": tag_id, "name": "stale", "color": "#abcdef"},
                "create-custom",
            ],
        },
    )
    assert response.status_code == 201, response.json

    stored = database.items.find_one({"item_id": "tag-on-create"})
    assert [t for t in stored["tags"] if isinstance(t, dict)] == [
        {"type": "tags", "immutable_id": ObjectId(tag_id)}
    ]
    assert "create-custom" in stored["tags"]
