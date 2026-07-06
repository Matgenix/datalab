def test_query_schema_supports_multiple_list_views(client):
    cases = {
        "samples": ("samples", "chemform"),
        "equipment": ("equipment", "manufacturer"),
        "starting_materials": ("starting_materials", "CAS"),
    }

    for list_view, (item_type, expected_field) in cases.items():
        response = client.get(f"/query-schema?list_view={list_view}&item_type={item_type}")
        assert response.status_code == 200
        field_ids = {field["id"] for field in response.json["fields"]}
        assert expected_field in field_ids


def test_query_execution_across_list_views(
    client,
    insert_default_sample,
    insert_default_equipment,
    insert_default_starting_material,
):
    cases = [
        ("samples", "samples", "name", "other_sample", insert_default_sample.item_id),
        (
            "equipment",
            "equipment",
            "manufacturer",
            "science inc.",
            insert_default_equipment.item_id,
        ),
        (
            "starting_materials",
            "starting_materials",
            "chemform",
            "Na2CO3",
            insert_default_starting_material.item_id,
        ),
    ]

    for list_view, item_type, field, value, item_id in cases:
        response = client.post(
            "/query",
            json={
                "list_view": list_view,
                "item_types": [item_type],
                "where": {
                    "kind": "group",
                    "combinator": "and",
                    "children": [
                        {"kind": "rule", "field": field, "operator": "eq", "value": value}
                    ],
                },
            },
        )
        assert response.status_code == 200
        assert item_id in {item["item_id"] for item in response.json["items"]}


def test_query_execution_for_collections(client, database, default_collection):
    database.collections.insert_one(default_collection.dict(exclude_unset=False))
    try:
        response = client.post(
            "/query",
            json={
                "list_view": "collections",
                "where": {
                    "kind": "group",
                    "combinator": "and",
                    "children": [
                        {"kind": "rule", "field": "title", "operator": "contains", "value": "My"}
                    ],
                },
            },
        )
        assert response.status_code == 200
        assert default_collection.collection_id in {
            item["collection_id"] for item in response.json["items"]
        }
    finally:
        database.collections.delete_one({"collection_id": default_collection.collection_id})


def test_invalid_list_view_returns_error(client):
    response = client.get("/query-schema?list_view=missing")
    assert response.status_code == 404

    response = client.post("/query", json={"list_view": "missing", "where": {}})
    assert response.status_code in (400, 404)


def test_malformed_query_does_not_500(client):
    response = client.post(
        "/query",
        json={
            "list_view": "samples",
            "item_types": ["samples"],
            "where": {"kind": "rule", "field": "name", "operator": "contains"},
        },
    )
    assert response.status_code == 422
