# Advanced Search

Advanced Search lets you filter any item list in datalab using structured, field-level conditions — no raw query strings required. It dynamically pulls the available fields and operators directly from the data model, so you never need to update the UI when a new field is added to the backend.

---

## Table of Contents

1. [For Users](#for-users)
   - [Opening the Panel](#opening-the-panel)
   - [Selecting an Item Type](#selecting-an-item-type)
   - [Adding Filter Rules](#adding-filter-rules)
   - [Combining Rules — AND / OR](#combining-rules--and--or)
   - [Nested Groups](#nested-groups)
   - [Sorting Results](#sorting-results)
   - [Live Preview Count](#live-preview-count)
   - [Running the Search](#running-the-search)
   - [Clearing Filters](#clearing-filters)
   - [Screenshots](#screenshots)
2. [For Developers](#for-developers)
   - [Architecture Overview](#architecture-overview)
   - [Component Tree](#component-tree)
   - [Mounting AdvancedQueryBuilder in a New View](#mounting-advancedquerybuilder-in-a-new-view)
   - [Backend: List Views and Item Types](#backend-list-views-and-item-types)
   - [How Dynamic Fields Are Discovered](#how-dynamic-fields-are-discovered)
   - [API Endpoints](#api-endpoints)
   - [Query Tree Format](#query-tree-format)
   - [Available Operators](#available-operators)
   - [Editor Components](#editor-components)
   - [Cursor-Based Pagination](#cursor-based-pagination)
   - [How to Add a New List View](#how-to-add-a-new-list-view)
   - [How to Add a New Item Type / Model](#how-to-add-a-new-item-type--model)
   - [Pinning Fields Manually per Model](#pinning-fields-manually-per-model)
   - [Customising Field Labels and Groups](#customising-field-labels-and-groups)
   - [Adding a New Operator](#adding-a-new-operator)
   - [Adding a Custom Editor Component](#adding-a-custom-editor-component)

---

## For Users

### Opening the Panel

Every item list page (Samples, Cells, Starting Materials, Equipment) has an **Advanced Search** button in the toolbar — it looks like a funnel icon. Click it to open the search panel as a modal dialog.

When filters are active, the button turns purple and shows a short summary of your current conditions. You can click the **×** on the button to clear all filters instantly without opening the panel.

> _[Screenshot: toolbar with the Advanced Search button highlighted]_

---

### Selecting an Item Type

At the top of the panel you will see radio buttons for each item type available in that view — for example **Sample** and **Cell** on the Samples page.

Choose the type you want to search across. The field list below updates automatically to show only the fields that belong to that type.

> **Note:** If you already have rules built and you switch types, datalab will warn you how many of those rules would become invalid and ask you to confirm before clearing them.

> _[Screenshot: type selector with Sample and Cell options]_

---

### Adding Filter Rules

Click **New Rule** to add a condition. Each rule has three parts:

| Part | What it does |
|---|---|
| **Field** | The data attribute you want to filter on (e.g. Name, Formula, Date) |
| **Operator** | How to match the value (e.g. *contains*, *equals*, *is set*, *before*) |
| **Value** | The value to compare against (not shown for operators like *is set*) |

The operator list changes depending on the field type:

- **Text fields** — `contains`, `equals`, `is set`, `is not set`
- **Number fields** — `greater than`, `less than`, `equals`, `is set`
- **Date fields** — `in range`, `before`, `after`, `is set`
- **Enum fields** (e.g. Status, Cell Format) — `is one of`, `equals`, `is set`
- **Constituent fields** (electrodes, electrolyte) — `contains`, `does not contain` with an item reference picker

To remove a rule, click the trash icon on the right of that row.

> _[Screenshot: a rule row with field "Name", operator "contains", value "LFP"]_

---

### Combining Rules — AND / OR

When you have two or more rules, an **AND / OR** toggle appears above them.

- **AND** — all conditions must be true (narrower results)
- **OR** — at least one condition must be true (broader results)

Click the toggle to switch between them. The combinator applies to every rule in that group.

> _[Screenshot: AND/OR toggle with two rules]_

---

### Nested Groups

Click **Add group** to create a sub-group of rules with its own AND / OR combinator. This lets you build more complex logic, for example:

```
(Name contains "LFP") AND (
    (Cell Format equals "coin") OR (Cell Format equals "pouch")
)
```

Groups can be nested up to a depth defined per view (up to 5 levels for item views). Remove a group with the **Remove group** link that appears inside it.

> _[Screenshot: two rules plus a nested group with its own OR combinator]_

---

### Sorting Results

The **Sort by** row at the top of the rule area lets you pick which field to sort results by. Only fields that support sorting appear in the dropdown. Click the **↓ Desc / ↑ Asc** button next to it to flip the direction.

If no sort is chosen, results default to newest first (by date).

> _[Screenshot: sort row with "Date" selected and descending arrow]_

---

### Live Preview Count

As you build or change your conditions, the footer of the panel shows a live count — for example **Found: 42 items** — without you having to click Search. This count updates automatically after a short pause (400 ms) every time you change a rule or switch types.

The count shows `200+ items` when the result set exceeds 200 (the preview limit).

If any rule is incomplete (missing a value), the preview pauses until the rule is valid.

> _[Screenshot: footer showing "Found: 17 items"]_

---

### Running the Search

Click **Search** in the bottom-right corner. datalab fetches all matching items (up to 2 000) and replaces the table content with the results. The Advanced Search button in the toolbar now shows a summary of the active filters.

The table works normally on the filtered results — you can still sort columns, select rows, export, etc.

> _[Screenshot: table showing search results with the active filter summary in the toolbar]_

---

### Clearing Filters

- Click the **×** on the Advanced Search button in the toolbar — clears all filters instantly and restores the full list.
- Or open the panel and click **Cancel** to close without applying changes.

---

### Screenshots

> _Add screenshots here before turning this into a presentation._

---

---

## For Developers

### Architecture Overview

Advanced Search is split cleanly between a Vue 3 frontend and a Flask/MongoDB backend. Neither side hard-codes field names or operators — everything is derived at runtime from Pydantic model schemas.

```
Browser                          Backend (Flask + MongoDB)
──────────────────────           ─────────────────────────────────────────
AdvancedQueryBuilder.vue         GET /query-capabilities   → is search enabled?
  │                              GET /query-types          → list of item types
  ├─ QueryGroup.vue              GET /query-schema         → fields + operators per type
  │    └─ QueryRule.vue          POST /query               → run query, returns items + cursor
  │         └─ <editor>.vue      GET /query-options/<src>  → autocomplete for constituent picker
  │
  └─ server_fetch_utils.js  →  wraps all five endpoints above
```

The full backend logic lives in:

```
pydatalab/src/pydatalab/routes/v0_1/query.py
```

The frontend components live in:

```
webapp/src/components/AdvancedQueryBuilder.vue   ← entry point
webapp/src/components/QueryGroup.vue
webapp/src/components/QueryRule.vue
webapp/src/components/queryEditors/             ← one file per editor type
```

---

### Component Tree

```
AdvancedQueryBuilder          Manages state: selected type, schema, rules, sort,
│                             preview, pagination. Emits query-results upward.
│
├─ QueryGroup                 Recursive. Renders a list of rules/sub-groups with
│   │                         an AND/OR combinator toggle. Handles add/remove/update.
│   └─ QueryRule              One filter row: field select → operator select → editor.
│        │                    Looks up available operators from the schema returned
│        │                    by the backend — never hard-codes them.
│        └─ <EditorComponent> Swapped in based on the operator's "editor" key:
│               TextEditor
│               NumberEditor
│               DatetimeEditor
│               DatetimeRangeEditor
│               StringListEditor
│               EnumEditor
│               ChemicalFormulaEditor
│               ConstituentSelectorEditor   (fetches item references from the server)
│               FallbackEditor              (catch-all for unknown editor types)
```

---

### Mounting AdvancedQueryBuilder in a New View

`AdvancedQueryBuilder` is a self-contained component. The parent page only needs to:

1. Pass a `listView` name (must match a key in `QUERY_VIEWS` on the backend).
2. Listen for the `query-results` event.

**Minimal example**

```vue
<template>
  <AdvancedQueryBuilder
    list-view="samples"
    @query-results="onResults"
  />
</template>

<script>
import AdvancedQueryBuilder from "@/components/AdvancedQueryBuilder.vue";

export default {
  components: { AdvancedQueryBuilder },
  methods: {
    onResults(items) {
      if (items === null) {
        // filters were cleared — restore the normal list
      } else {
        // items is the full collected array (up to 2 000 summary objects)
        this.rows = items;
      }
    },
  },
};
</script>
```

**With pre-loaded query config** (avoids one extra network round-trip)

If your page already fetches capabilities (e.g. `DynamicDataTable` does this automatically), pass the config object directly:

```vue
<AdvancedQueryBuilder
  list-view="samples"
  :query-options="advancedQueryConfig.options"
  @query-results="onResults"
/>
```

`queryOptions.options` comes from `GET /query-capabilities` and has this shape:

```json
{
  "queryRoute": "/query",
  "listViewName": "samples",
  "resource": "items",
  "item_types": [
    { "id": "samples", "label": "Sample", "queryable": true },
    { "id": "cells",   "label": "Cell",   "queryable": true }
  ]
}
```

**DynamicDataTable integration**

`DynamicDataTable` does all of this automatically via `DynamicDataTableButtons`. It calls `fetchAdvancedQueryConfig(dataType)` on mount, passes the result to `DynamicDataTableButtons`, which renders `AdvancedQueryBuilder` when `advancedQueryConfig.isEnabled` is true. No extra code is needed for views already backed by a registered list view.

---

### Backend: List Views and Item Types

The backend organises searchable data into **list views**, defined in `QUERY_VIEWS` at the top of `query.py`:

```python
QUERY_VIEWS: dict[str, dict] = {
    "samples": {
        "resource": "items",
        "collection": "items",
        "types": ["samples", "cells"],          # which item types live here
        "model_by_type": ITEM_MODELS,
        "view_contexts": ["samples"],            # frontend dataType strings that map here
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
    # equipment, collections, users, groups ...
}
```

`view_contexts` is the bridge between the frontend `dataType` prop and the backend view name. When `DynamicDataTable` calls `GET /query-capabilities?data_type=startingMaterials`, the backend finds the view whose `view_contexts` list contains that string.

---

### How Dynamic Fields Are Discovered

This is the core of what makes advanced search dynamic. When the frontend requests `GET /query-schema?list_view=samples&item_type=cells`, the backend:

1. Calls `model.schema(by_alias=False)` on the Pydantic model for that type (e.g. `Cell`).
2. Walks every property recursively via `_iter_schema_fields`, skipping internal fields listed in `_SKIP_FIELDS`.
3. Inspects each field's JSON Schema type/format to assign operators:
   - `"format": "date-time"` or field name contains `"date"` → date operators
   - `"type": "number"` or `"integer"` → numeric operators
   - `"type": "string"` → text operators
   - `$ref` pointing to an enum → enum operators
   - Known constituent array fields → constituent operators
4. Merges UI hints from `_FIELD_UI` (custom label, group, sortable flag, editor overrides).
5. Returns the complete field + operator list as JSON.

**Result:** add a field to a Pydantic model → it automatically appears in the advanced search UI the next time the schema endpoint is called. No frontend changes needed.

---

### API Endpoints

All endpoints are registered on the `QUERY` blueprint and mounted at `/api/v0.1/`.

---

#### `GET /query-capabilities`

Checks whether advanced search is enabled for a given frontend data type context.

| Parameter | Type | Description |
|---|---|---|
| `data_type` | string | The frontend `dataType` value (e.g. `"samples"`, `"startingMaterials"`) |

**Response**

```json
{
  "data_type": "samples",
  "advanced_query": {
    "isEnabled": true,
    "listViewName": "samples",
    "resource": "items",
    "queryRoute": "/query",
    "options": { "...": "..." },
    "capabilities": {
      "combinators": ["and", "or"],
      "allow_negation": false,
      "max_rules": 50,
      "max_depth": 5
    }
  },
  "views": ["...all views..."]
}
```

Returns `"advanced_query": null` when no view matches `data_type`.

---

#### `GET /query-types`

Returns the list of queryable item types for a list view.

| Parameter | Type | Description |
|---|---|---|
| `list_view` | string | e.g. `"samples"` |

**Response**

```json
{
  "list_view": "samples",
  "item_types": [
    { "id": "samples", "label": "Sample", "description": "...", "queryable": true },
    { "id": "cells",   "label": "Cell",   "description": "...", "queryable": true }
  ]
}
```

---

#### `GET /query-schema`

Returns all searchable fields and their operators for a specific item type.

| Parameter | Type | Description |
|---|---|---|
| `list_view` | string | e.g. `"samples"` |
| `item_type` | string (repeatable) | e.g. `"cells"` |

**Response (excerpt)**

```json
{
  "version": "1.0",
  "list_view": "samples",
  "fields": [
    {
      "id": "name",
      "label": "Name",
      "group": "Basic",
      "sortable": true,
      "operators": [
        { "id": "contains",   "label": "contains",   "value_required": true,  "editor": "text" },
        { "id": "eq",         "label": "equals",      "value_required": true,  "editor": "text" },
        { "id": "is_set",     "label": "is set",      "value_required": false },
        { "id": "is_not_set", "label": "is not set",  "value_required": false }
      ]
    },
    {
      "id": "cell_format",
      "label": "Cell Format",
      "group": "Cell",
      "sortable": true,
      "operators": [
        {
          "id": "in", "label": "is one of", "value_required": true,
          "editor": "enum",
          "value_schema": { "type": "array", "items": { "enum": ["coin","pouch","..."] } }
        }
      ]
    }
  ],
  "capabilities": { "combinators": ["and", "or"], "max_depth": 5 }
}
```

---

#### `POST /query`

Executes a query and returns one page of matching items with a cursor for the next page.

**Request body**

```json
{
  "list_view": "samples",
  "item_types": ["cells"],
  "where": {
    "kind": "group",
    "combinator": "and",
    "children": [
      { "kind": "rule", "field": "name", "operator": "contains", "value": "LFP" },
      { "kind": "rule", "field": "cell_format", "operator": "eq", "value": "coin" }
    ]
  },
  "sort": [{ "field": "date", "direction": "desc" }],
  "page": { "limit": 50, "cursor": "<opaque cursor string>" }
}
```

`where` can be omitted (returns all items of the given types).
`page.cursor` is omitted on the first request; pass the value from `next_cursor` to fetch the next page.

**Response**

```json
{
  "query": {
    "common_type": { "id": "cells", "label": "Cell" },
    "selected_item_types": ["cells"]
  },
  "items": [ { "item_id": "...", "name": "...", "_id": "...", "...": "..." } ],
  "page": { "limit": 50, "next_cursor": "<string or null>", "has_more": true }
}
```

Each item is a summary object (not the full document). Fields returned: `_id` (string), `item_id`, `name`, `chemform`, `type`, `date`, `refcode`, `status`, `characteristic_chemical_formula`, `nblocks`, `nfiles`, `blocks`, `creators`, `groups`, `collections`.

---

#### `GET /query-options/<source_id>`

Autocomplete endpoint for the constituent-selector editor. Currently the only valid `source_id` is `datalab:item-reference`.

| Parameter | Type | Description |
|---|---|---|
| `q` | string | Search string matched against name, item_id, refcode |
| `limit` | int | Max results (default 20, max 100) |
| `item_type` | string (repeatable) | Filter by item type |
| `cursor` | string | Pagination cursor |

---

### Query Tree Format

Every query sent to `POST /query` is a tree of `group` and `rule` nodes.

```
Node = Group | Rule

Group:
  kind:       "group"
  combinator: "and" | "or"
  children:   Node[]          ← can contain Rules and nested Groups

Rule:
  kind:     "rule"
  field:    string            ← field id from /query-schema
  operator: string            ← operator id from that field's operators list
  value:    any | undefined   ← omit when value_required is false
```

**Example — (name contains "LFP") AND ((format = coin) OR (format = pouch))**

```json
{
  "kind": "group",
  "combinator": "and",
  "children": [
    { "kind": "rule", "field": "name", "operator": "contains", "value": "LFP" },
    {
      "kind": "group",
      "combinator": "or",
      "children": [
        { "kind": "rule", "field": "cell_format", "operator": "eq", "value": "coin" },
        { "kind": "rule", "field": "cell_format", "operator": "eq", "value": "pouch" }
      ]
    }
  ]
}
```

---

### Available Operators

Operators are defined in the `OPERATORS` dict in `query.py`. Each compiles to a MongoDB filter fragment.

The table below shows both the **id** (the token sent in the API) and the **label** (the text shown to the user in the dropdown).

| `id` (sent to API) | `label` (shown in UI) | Value type | Editor |
|---|---|---|---|
| `contains` | contains | string | `text` |
| `eq` | equals | any | `text` |
| `is_set` | is set | — | — |
| `is_not_set` | is not set | — | — |
| `in` | is one of | array | `string-list` or `enum` |
| `gt` | greater than | number | `number` |
| `lt` | less than | number | `number` |
| `before` | before | datetime string | `datetime` |
| `after` | after | datetime string | `datetime` |
| `date_range` | in range | `[start, end]` | `datetime-range` |
| `has_constituent` | contains | item refcode/id | `constituent-selector` |
| `not_has_constituent` | does not contain | item refcode/id | `constituent-selector` |

When building a rule in the frontend, use the **id** as the `operator` field. The **label** is only for display. When defining a new operator in `query.py`, you set both independently.

---

### Editor Components

`QueryRule` maps the `editor` key from the operator definition to a Vue component via `editorMap`:

| `editor` key | Component | Used for |
|---|---|---|
| `text` | `TextEditor` | Plain string input |
| `number` | `NumberEditor` | Numeric input |
| `datetime` | `DatetimeEditor` | Single date/time picker |
| `datetime-range` | `DatetimeRangeEditor` | Start + end date pickers |
| `string-list` | `StringListEditor` | Comma-separated or tag-style list |
| `enum` | `EnumEditor` | Dropdown built from `value_schema.items.enum` |
| `chemical-formula` | `ChemicalFormulaEditor` | Plain text input for now (formula-aware editor is a TODO) |
| `constituent-selector` | `ConstituentSelectorEditor` | Async item search, fetches from `/query-options/` |
| _(anything else)_ | `FallbackEditor` | Plain text fallback |

---

### Cursor-Based Pagination

`POST /query` uses cursor pagination instead of offset pagination. This avoids the "skipping rows" problem that can occur when documents are inserted between page fetches.

**How the cursor is built**

The backend appends `("_id", 1)` to the sort spec as a tie-breaker, then fetches `limit + 1` documents. If the result has more than `limit` rows, the `_id` of the last returned document is base64-encoded into `next_cursor`:

```python
# backend: _encode_cursor / _decode_cursor
next_cursor = base64.urlsafe_b64encode(str(last_id).encode()).decode()
```

**How the cursor is applied on the next request**

When the client sends `page.cursor`, the backend decodes the `_id` and adds:

```json
{ "_id": { "$gt": "<decoded ObjectId>" } }
```

This is combined with the original `$match` filter via `$and`, so only documents with a greater `_id` are returned.

> **Known limitation:** The current cursor is based only on `_id`. Because `_id` is always appended to the sort as the last key, pagination stays consistent for most cases. However, for large datasets with a custom sort field that has many ties, some edge cases can produce unexpected ordering between pages. A composite cursor (encoding the sort field value alongside `_id`) would be more robust.

**Frontend behaviour**

`AdvancedQueryBuilder.submitQuery` loops automatically, collecting pages of 200 items each until `has_more` is false or 2 000 items are accumulated (safety cap). The full collected array is then emitted once via `query-results` and displayed in the table.

---

### How to Add a New List View

1. Add an entry to `QUERY_VIEWS` in `query.py`:

```python
QUERY_VIEWS["experiments"] = {
    "resource": "items",
    "collection": "items",
    "types": ["experiments"],
    "model_by_type": ITEM_MODELS,
    "view_contexts": ["experiments"],        # must match the frontend dataType prop
    "default_sort": [("date", -1)],
}
```

2. Register `Experiment` in `ITEM_MODELS` (see `pydatalab/models/__init__.py`).

3. The frontend picks this up automatically — no changes needed in Vue components.

---

### How to Add a New Item Type / Model

1. Create the Pydantic model class (e.g. `pydatalab/models/experiments.py`):

```python
from pydatalab.models.items import Item
from pydantic import Field

class Experiment(Item):
    """A model for representing an experiment."""

    type: str = Field("experiments", const="experiments", pattern="^experiments$")

    protocol: str | None
    temperature_c: float | None
```

2. Register it in `ITEM_MODELS` in `pydatalab/models/__init__.py`:

```python
from pydatalab.models.experiments import Experiment

ITEM_MODELS = {
    ...,
    "experiments": Experiment,
}
```

3. That is all. The schema endpoint will automatically discover `protocol` (text operators) and `temperature_c` (numeric operators) next time it is called.

---

### Pinning Fields Manually per Model

By default, every field that appears in the Pydantic schema and has a recognised type is shown in the advanced search UI. If you want to **restrict** the search to a specific subset of fields — or expose them in a specific order — add `query_options_list` to your model's schema extra config.

When `query_options_list` is present it **completely replaces** the auto-discovered field list for that model. See `_query_options_list` in `query.py` for the full specification.

The codebase uses **Pydantic v1**. Add a `Config` inner class with `schema_extra`:

```python
class Experiment(Item):
    """A model for representing an experiment."""

    type: str = Field("experiments", const="experiments", pattern="^experiments$")
    protocol: str | None
    temperature_c: float | None

    class Config:
        schema_extra = {
            "query_options_list": ["name", "item_id", "date", "temperature_c"]
        }
```

Only those four fields will appear in the advanced search panel for `Experiment` items.

**Advanced example — overriding label, operators, and editor**

Each entry in `query_options_list` can be a plain field-ID string or a dict that overrides specific properties:

```python
"query_options_list": [
    "name",
    "date",
    {
        "id": "temperature_c",
        "label": "Temperature (°C)",
        "operators": ["gt", "lt", "eq", "is_set"],
    },
    {
        "id": "chemform",
        "label": "Formula",
        "operators": ["eq", "contains"],
        "editor_override": {"eq": "chemical-formula"},
    },
]
```

Each entry is either:
- A **plain string** — field ID looked up in the auto-discovered registry; uses all its defaults.
- A **dict** — overrides any of `label`, `operators`, `editor_override`, `mongo_path`, `group`, `sortable`.

> **Important:** If any field ID in the list is invalid (typo or not present in the schema), the backend raises a `ValueError` at request time with a message listing the unknown entries and the available fields. This prevents the silent fallback to the full registry.

---

### Customising Field Labels and Groups

`_FIELD_UI` in `query.py` is a plain dict that maps field names to display metadata. It applies globally across all models that have that field.

```python
_FIELD_UI: dict[str, dict] = {
    "name":    {"label": "Name",    "group": "Basic",     "sortable": True},
    "chemform":{"label": "Formula", "group": "Chemistry", "sortable": True,
                "editor_override": {"eq": "chemical-formula", "contains": "text"}},
    # ...
}
```

| Key | Type | Effect |
|---|---|---|
| `label` | string | Human-readable column header in the UI |
| `group` | string | Groups fields in the dropdown (`Basic`, `Chemistry`, `Cell`, `Synthesis`, `Provenance`, `Other`) |
| `sortable` | bool | Whether the field appears in the Sort By dropdown |
| `editor_override` | dict | Maps operator `id` → editor key, overriding the default for that operator |

To add a new field to `_FIELD_UI`, simply add an entry. Fields not listed get a title-cased label and are placed in `Other`.

---

### Adding a New Operator

Operators are defined in the `OPERATORS` dict in `query.py`. Add an entry:

```python
OPERATORS["regex"] = {
    "label": "matches regex",
    "value_required": True,
    "editor": "text",
    "compile": lambda path, value: {
        path: {"$regex": str(value), "$options": "m"}
    },
}
```

> **Security note:** For operators like `contains` that treat user input as a **literal string**, always use `re.escape()` — the built-in `contains` operator already does this. For a dedicated `regex` operator the user is intentionally writing a pattern, so do **not** escape it — escaping would turn `^LFP.*` into `\^LFP\.\*` and break it. Instead, consider limiting regex complexity or restricting who can use this operator.

The keys each operator entry must have:

| Key | Required | Description |
|---|---|---|
| `label` | yes | Displayed in the operator dropdown |
| `value_required` | yes | If `False`, no editor is shown and `value` is ignored |
| `editor` | when `value_required` is `True` | Key into the frontend `editorMap` in `QueryRule.vue` |
| `compile` | yes | `(mongo_path, value) → dict` — produces the MongoDB filter fragment |
| `options_source` | no | For constituent-selector only: the source ID passed to `/query-options/<id>` |

After adding to `OPERATORS`, also add the operator `id` to the relevant field's `operator_ids` list — either via `_field_to_operators` logic, via `_FIELD_UI` `editor_override`, or via `query_options_list` on the model.

---

### Adding a Custom Editor Component

1. Create `webapp/src/components/queryEditors/MyEditor.vue`. The component must:
   - Accept a `modelValue` prop (the current value).
   - Accept a `valueSchema` prop (optional — the JSON Schema for allowed values, passed from the backend).
   - Emit `update:modelValue` when the value changes.

```vue
<template>
  <input
    :value="modelValue"
    type="text"
    class="form-control form-control-sm"
    @input="$emit('update:modelValue', $event.target.value)"
  />
</template>

<script>
export default {
  name: "MyEditor",
  props: {
    modelValue: { default: null },
    valueSchema: { type: Object, default: null },
  },
  emits: ["update:modelValue"],
};
</script>
```

2. Register it in `QueryRule.vue`:

```js
import MyEditor from "@/components/queryEditors/MyEditor.vue";

const editorMap = {
  // existing entries ...
  "my-editor": "MyEditor",
};

// and add MyEditor to the components: { ... } option
```

3. Reference it in an operator definition on the backend:

```python
OPERATORS["my_op"] = {
    "label": "my operator",
    "value_required": True,
    "editor": "my-editor",         # must match the key in editorMap
    "compile": lambda p, v: {p: v},
}
```
