# Web UI support for custom / plugin item types

## Overview

This work wires the frontend end-to-end for custom item types registered by out-of-tree plugins — types that the backend already serves but that the app previously had no way to display or edit. It introduces two rendering paths (automatic from annotations, or via a custom Vue panel shipped by the plugin), a plugin panel discovery CLI, and an in-repo example plugin that exercises both paths.

---

## Backend additions (`pydatalab/`)

### `/info/types` enrichment ([routes/v0_1/info.py](pydatalab/src/pydatalab/routes/v0_1/info.py))

The `/info/types` and `/info/types/<type>` endpoints now return `title`, `base_type`, `hidden_fields`, and `ui_color` alongside the JSON schema. `base_type` is resolved by walking the MRO against the built-in models so it works regardless of the plugin's inheritance depth.

### `datalab-collect-plugin-panels` CLI ([cli.py](pydatalab/src/pydatalab/cli.py))

New entry-point command that scans installed `pydatalab.item_types` packages, copies any `webapp/*.vue` files into `webapp/src/plugins/<package>/`, and generates `webapp/src/plugins/panels.generated.js` — an auto-generated map of `type_name → () => import(...)` factories. Convention: `heat_treatments` → `HeatTreatmentPanel.vue`. The generated file is gitignored; only the committed shim (`index.js`) is tracked.

---

## Frontend additions (`webapp/`)

### Dynamic type registry ([resources.js](webapp/src/resources.js))

- `itemTypes` is now `reactive({...})` so Vue computeds re-evaluate when plugin types register after startup.
- `registerDynamicItemType(type, { title, base_type, hidden_fields, ui_color })` adds a custom type into the shared registry, deriving the base information component from `BASE_TYPE_COMPONENTS`, computing a pastel badge color with `lightTint()`, and storing the custom panel factory from `PLUGIN_PANELS`.
- `prettifyType()` and `lightTint()` added as shared helpers.

### Schema loading ([server_fetch_utils.js](webapp/src/server_fetch_utils.js))

`loadItemSchemas()` (called once from `App.vue` on startup) now calls `registerDynamicItemType` for each type returned by `/info/types` before caching schemas. `createNewItem` prepends custom-type items to the samples list and returns `item_id`.

### `EditPage.vue` ([EditPage.vue](webapp/src/views/EditPage.vue))

- Falls back to the `itemType` string in the navbar if the registry entry isn't loaded yet.
- `informationComponent`: renders the built-in base component (e.g. `SampleInformation`) so standard fields (name, description, relationships…) always appear.
- `hasCustomPanel` / `resolvedCustomPanel`: if the type has a plugin-shipped panel factory, wraps it with `defineAsyncComponent`; otherwise falls back to `CustomFieldsPanel`.

### `CustomFieldsPanel.vue` ([CustomFieldsPanel.vue](webapp/src/components/custom/CustomFieldsPanel.vue)) — new

Annotation-driven renderer for custom type fields. Diffs the type schema against its base type schema and renders only the delta fields. Supports:

- Number + unit compound widget (`datalab_unit_field`)
- Inline item-reference selector / display (`datalab_ref_types`) via `ItemSelect` + `FormattedItemName`
- Enum dropdown, boolean checkbox, multiline textarea (`datalab_multiline`)
- Multi-card grouping by `datalab_section`; default card titled by `datalab_section_title`
- Fields marked `datalab_hidden` are excluded; non-scalar fields (arrays, objects) are left to custom panels.

### Plugin panel shim ([plugins/index.js](webapp/src/plugins/index.js)) — new

Stable committed shim that loads `panels.generated.js` only when present, exporting `PLUGIN_PANELS`. The generated file itself stays gitignored.

### Existing components updated

[CellInformation](webapp/src/components/CellInformation.vue),
[SampleInformation](webapp/src/components/SampleInformation.vue),
[CreateItemModal](webapp/src/components/CreateItemModal.vue),
[ItemSelect](webapp/src/components/ItemSelect.vue),
[FormattedItemStatus](webapp/src/components/FormattedItemStatus.vue),
[CompactConstituentTable](webapp/src/components/CompactConstituentTable.vue),
[EquipmentInformation](webapp/src/components/EquipmentInformation.vue),
[StartingMaterialInformation](webapp/src/components/StartingMaterialInformation.vue)

Updated to use `FormattedItemName` for all item-reference badges (type-colored, correct click/cmd-click behavior) and to surface `hiddenFields` from the registry.

---

## Example plugin (`pydatalab/plugins/example_item_plugin/`)

Three custom `Sample` subtypes registered via `pydatalab.item_types` entry points:

- **`ExampleSample`** — minimal; one number+unit field (`voltage`).
- **`AnnealingProtocol`** — annotation-only, no JavaScript. Two cards: an annealing schedule (peak temperature, ramp rate, dwell time, atmosphere) and an Equipment & Safety card (furnace reference, supervision flag, hazard notes). Fully rendered by `CustomFieldsPanel`.
- **`HeatTreatment`** — ships `HeatTreatmentPanel.vue`: references an `AnnealingProtocol` (a custom type), seeds its as-run schedule via "Populate from protocol" (unit normalization K→°C, h→min), draws a live SVG temperature profile, and shows a second characterization card with a mass-loss progress bar.

---

## Config / infra

- [docker-compose.yml](docker-compose.yml): `DATALAB_DB_NAME` variable substitution so the database name is configurable without editing the compose file.
- [.gitignore](.gitignore): un-ignores `example_item_plugin` specifically; all other `pydatalab/plugins/` entries (deployment-specific plugins) and generated `webapp/src/plugins/` files remain local-only.
- [.eslintignore](.eslintignore): excludes `pydatalab/` so the pre-commit eslint hook doesn't try to lint plugin Vue files that have no eslint config.
- [pydatalab/docs/plugins.md](pydatalab/docs/plugins.md): full plugin-author guide covering both rendering paths, all `json_schema_extra` annotations (field-level and `model_config`-level), the collect command, and the custom panel conventions.
