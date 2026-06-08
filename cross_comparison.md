# Cross-Sample Comparison Feature

## Context

Users need to compare data from multiple samples side by side — both metadata (synthesis conditions, date, formula) and analytical data blocks (XRD patterns, NMR spectra, etc.). Today the only workaround is the in-block "Comparison Files" selector (visible in CycleBlock), which is clunky: it operates on raw files rather than processed blocks, buries comparison inside a single sample's page, and makes the two samples asymmetric. This feature adds a first-class `/compare` page and, separately, an overlay endpoint that merges multiple blocks' data into a single Bokeh plot server-side.

Multi-item comparison is explicitly listed in the datalab roadmap. This implementation contributes it to core.

## Data Flow (How It Works Today for One XRD Block)

```
MongoDB: { file_id, wavelength, block_id, blocktype: "xrd" }  ← config only, no plot
GridFS:  actual .xrdml file bytes

1. Browser  → GET /get-item-data/{item_id}
             ← full item doc with blocks_obj (config only, no bokeh_plot_data)

2. Browser  → POST /update-block/  { block_data: { file_id, wavelength, block_id } }
             ← Backend:
                  XRDBlock.from_web(block_data)
                  get_file_info_by_id(file_id)  → file path on disk
                  XRDBlock.load_pattern(path, wavelength)  → pandas DataFrame
                  selectable_axes_plot([df])  → Bokeh figure
                  bokeh.embed.json_item(figure)  → JSON blob (100–500 KB)
             ← { new_block_data: { bokeh_plot_data: { ... } } }

3. Frontend stores JSON in Vuex → BokehPlot.vue → Bokeh.embed.embed_item() → DOM
```

For comparison, we intercept at step 2: instead of one block generating one figure,
a new endpoint loads N blocks' DataFrames and calls `selectable_axes_plot([df_A, df_B, ...])`.
Both `XRDBlock.load_pattern()` (classmethod) and `selectable_axes_plot()` (already handles list of DataFrames)
exist and require no changes.

## Implementation Plan

### Phase 1 — Metadata table + side-by-side block view (no backend changes)

**Goal:** Ship something immediately useful. Fetch N samples in parallel, show metadata
side-by-side, render each block's existing `bokeh_plot_data` in a grid.

New files:
- `webapp/src/views/ComparisonPage.vue`

Minimal edits to existing files:
- `webapp/src/router/index.js` — add `/compare` route + lazy import (~6 lines)
- `webapp/src/components/DynamicDataTableButtons.vue` — add "Compare selected" button to the selected-items dropdown, emits `compare-selected-items` (~15 lines)
- `webapp/src/components/DynamicDataTable.vue` — handle `compare-selected-items` emit → `$router.push('/compare?ids=...')` (~5 lines)

**ComparisonPage layout:**
```
/compare?ids=A,B,C                                    [+ Add sample]

┌─ Metadata ──────────────────────────────────────────────────────┐
│              Sample A      Sample B      Sample C               │
│ Name         ...           ...           ...                     │
│ Date         ...           ...           ...                     │
│ Formula      ...           ...           ...                     │
│ Description  ...           ...           ...                     │
└─────────────────────────────────────────────────────────────────┘

┌─ Block Comparison ──────────────────────────────────────────────┐
│ Block type: [XRD ▼]    Mode: [Side-by-side ●  Overlay ○]       │
│                                                                  │
│  [Sample A – XRD plot]   [Sample B – XRD plot]                  │
└─────────────────────────────────────────────────────────────────┘
```

Data fetching: `Promise.all(ids.map(id => getItemData(id)))` — reuses existing
`server_fetch_utils.js` function, stores results in Vuex `all_item_data` (already supports
multiple items keyed by `item_id`).

Block type selector: derived from intersection of block types present across all selected samples.

Side-by-side mode: renders each block's existing `bokeh_plot_data` via the existing
`<BokehBlock>` / `<BokehPlot>` components with a read-only prop.

---

### Phase 2 — Overlay endpoint (new backend file, one line in existing registry)

**Goal:** Merge N blocks' data into a single overlaid Bokeh plot, server-side.

New files:
- `pydatalab/src/pydatalab/routes/v0_1/comparison.py` — new Flask Blueprint `COMPARISON`

Minimal edits to existing files:
- `pydatalab/src/pydatalab/routes/v0_1/__init__.py` — add `from .comparison import COMPARISON` + add `COMPARISON` to `BLUEPRINTS` tuple (2 lines)

**Endpoint:**
```
POST /blocks/compare/
Body:
{
  "blocks": [
    {"item_id": "sample-A", "block_id": "abc123"},
    {"item_id": "sample-B", "block_id": "def456"}
  ],
  "normalization": "max" | "none",   // default: "max"
  "offset": 0.2                      // y-stagger between series, default: 0
}
Response: { "bokeh_plot_data": { ... } }
```

**Endpoint logic (no existing files touched):**
```python
# comparison.py
from pydatalab.apps.xrd.blocks import XRDBlock
from pydatalab.bokeh_plots import selectable_axes_plot, DATALAB_BOKEH_THEME
from pydatalab.file_utils import get_file_info_by_id
from pydatalab.mongo import flask_mongo
import bokeh

COMPARISON_LOADERS = {
    "xrd": lambda cfg: XRDBlock.load_pattern(
        get_file_info_by_id(cfg["file_id"])["location"],
        cfg.get("wavelength")
    ),
    # future: "nmr": ..., "cycle": ..., "uvvis": ...
}

@COMPARISON.route("/blocks/compare/", methods=["POST"])
def compare_blocks():
    blocks_refs = request.json["blocks"]   # [{item_id, block_id}, ...]
    normalization = request.json.get("normalization", "max")
    offset = float(request.json.get("offset", 0.0))

    # Load block configs + determine blocktype
    block_configs = [
        flask_mongo.db.items.find_one(
            {"item_id": r["item_id"]}, {f"blocks_obj.{r['block_id']}": 1}
        )["blocks_obj"][r["block_id"]]
        for r in blocks_refs
    ]

    blocktype = block_configs[0]["blocktype"]
    if blocktype not in COMPARISON_LOADERS:
        return jsonify({"status": "error", "message": f"{blocktype} not yet supported for overlay"}), 400

    loader = COMPARISON_LOADERS[blocktype]
    dfs = []
    labels = []
    for cfg, ref in zip(block_configs, blocks_refs):
        df, _, _ = loader(cfg)
        if normalization == "max":
            df["intensity"] = df["intensity"] / df["intensity"].max()
        if offset:
            df["intensity"] += len(dfs) * offset
        dfs.append(df)
        labels.append(ref["item_id"])

    fig = selectable_axes_plot(dfs, ...)
    return jsonify({"bokeh_plot_data": bokeh.embed.json_item(fig, theme=DATALAB_BOKEH_THEME)})
```

**Frontend changes for overlay mode** (in `ComparisonPage.vue`, no new files needed):
- Mode toggle: Side-by-side / Overlay radio button
- Overlay mode calls `POST /blocks/compare/` with selected blocks
- Normalization dropdown + offset slider feed into the request body
- Response `bokeh_plot_data` rendered via existing `<BokehPlot>` component

---

### Phase 3 — Additional entry points (small, incremental)

- `webapp/src/views/EditPage.vue` — "Compare with..." button that opens a sample-picker
  modal and navigates to `/compare?ids=currentId,pickedId`
- Collection page — "Compare items" action on `CollectionPage.vue`
- (Future) comparison basket — localStorage-based, browse and add

---

## Files touched summary

| File | Change | Lines |
|------|--------|-------|
| `webapp/src/router/index.js` | Add `/compare` route | ~6 |
| `webapp/src/components/DynamicDataTableButtons.vue` | "Compare selected" button | ~15 |
| `webapp/src/components/DynamicDataTable.vue` | Handle compare emit | ~5 |
| `pydatalab/src/pydatalab/routes/v0_1/__init__.py` | Import + register COMPARISON | 2 |

New files:
- `webapp/src/views/ComparisonPage.vue`
- `pydatalab/src/pydatalab/routes/v0_1/comparison.py`

Per-block additions (Phase 2+, only when adding a new block type to overlay):
- Add entry to `COMPARISON_LOADERS` dict in `comparison.py` — no block file touched for XRD
- For NMR/Cycling/UVVis: expose a `get_dataframe_for_comparison()` classmethod in each block, add to registry

---

## Key reused functions (no changes needed)

- `XRDBlock.load_pattern(path, wavelength)` — [apps/xrd/blocks.py](pydatalab/src/pydatalab/apps/xrd/blocks.py) — already a classmethod returning `(df, y_options, peak_data)`
- `selectable_axes_plot(dfs, ...)` — [pydatalab/bokeh_plots.py](pydatalab/src/pydatalab/bokeh_plots.py) — already accepts a list of DataFrames with automatic coloring (Dark2 palette) and shared axis selector (2θ / Q / d-spacing)
- `getItemData(item_id)` — [server_fetch_utils.js](webapp/src/server_fetch_utils.js) — already fetches full item + blocks into Vuex
- `<BokehPlot>` component — [BokehPlot.vue](webapp/src/components/BokehPlot.vue) — renders any Bokeh JSON blob

---

## URL design

- `/compare?ids=sample-A,sample-B,sample-C` — shareable, bookmarkable
- Limit: 5 samples max (UX constraint, enforced in `ComparisonPage.vue`)
- History: recent comparisons stored in `localStorage` (no DB changes needed)

---

## Verification

**Backend:**
```bash
# Unit test the comparison endpoint
pytest pydatalab/tests/server/test_comparison.py

# Manual smoke test
curl -X POST http://localhost:5001/blocks/compare/ \
  -H "Content-Type: application/json" \
  -d '{"blocks": [{"item_id": "A", "block_id": "x"}, {"item_id": "B", "block_id": "y"}], "normalization": "max"}'
# → should return {"bokeh_plot_data": {...}}
```

**Frontend:**
1. Multi-select 2 samples in Samples list → "Compare selected" button appears
2. Navigate to `/compare?ids=A,B` → metadata table renders correctly
3. Select XRD block type → side-by-side plots appear
4. Switch to Overlay → single merged Bokeh plot appears with 2 colored series
5. Bokeh axis selector (2θ / Q / d-spacing) works across all series simultaneously

---
---

# Follow-up Plan — Plugin-Extensible Overlay + Spectral-Block Rollout

> Status: planned (not yet implemented). The sections above describe the shipped first draft;
> this section describes the next iteration that makes overlay a block-declared capability and
> rolls it out to the spectral blocks.

## Context

Overlay is currently **hardcoded for XRD only** — a central `COMPARISON_SPECS` dict + XRD loaders in
`routes/v0_1/comparison.py`, and a hardcoded `OVERLAY_SUPPORTED` set in `ComparisonPage.vue`. So
**plugin blocks can never gain overlay**, and every new core block needs core edits.

This change: (1) **refactors** overlay into a capability each block declares on itself (discovered by
introspection, surfaced to the frontend via `/info/blocks`), uniform for core *and* plugin blocks;
(2) **rolls out** the capability to the 6 spectral blocks whose data is naturally 1D x/y:
**XRD, Raman, FTIR, NMR, UV-Vis, EIS**.

Side-by-side already works for every block (renders the block's own `bokeh_plot_data`) and is **not
changed**. Complex/2D/bespoke blocks (in-situ plugin, echem dual-axis, MassSpec gridplot, media,
chat, comment, tabular) simply don't implement the hook → overlay disabled, side-by-side only.

## Locked design decisions

1. **Capability on the block class** (instance method), discovered by introspecting `BLOCK_TYPES` — no central registry.
2. **Strictly same-type** overlay (sidesteps axis-compatibility; same class ⇒ identical column names).
3. **Data-only contract with a 1D reduction**: the block returns labeled dataframe(s) + axis hints; the endpoint always renders via `selectable_axes_plot` in per-sample-color mode. Blocks return the meaningful *comparable reduction*, not their native bespoke plot.
4. **Opt-in, never mandatory**: the hook has a base default (`return None`); a block that does nothing is automatically side-by-side only.

## The contract

In `pydatalab/src/pydatalab/blocks/base.py` (stable import location for plugins):

```python
@dataclass
class ComparisonData:
    series: list[tuple[str | None, pd.DataFrame]]  # (sublabel, df); multi-curve stays first-class
    x_options: list[str]      # selectable x columns (data-dependent labels OK, e.g. Raman unit)
    x_default: str
    y_default: str
    y_options: list[str] | None = None

class DataBlock:
    def get_comparison_data(self) -> "ComparisonData | None":
        """Override to support overlay. Reuse the block's own loaders. Default: unsupported."""
        return None

    @classmethod
    def supports_comparison(cls) -> bool:
        return cls.get_comparison_data is not DataBlock.get_comparison_data
```

Instance method, invoked after `from_web(cfg)`, so each block reuses its existing loaders and saved
state (`self.data`).

## Changes

### Backend — framework

1. **`blocks/base.py`** — add `ComparisonData`, the `get_comparison_data()` hook (default `None`), and `supports_comparison()`.
2. **`routes/v0_1/comparison.py`** — make generic: remove the `XRDBlock` import, `COMPARISON_SPECS`, and the XRD loaders. Flow: validate ≥2 refs; load each block config with `get_default_permissions(user_only=False)`; require a single blocktype; `cls = BLOCK_TYPES[blocktype]`, reject if `not cls.supports_comparison()`; for each ref `block = cls.from_web(cfg); data = block.get_comparison_data()`; collect `data.series` into the labelled dict (keep base-label/sublabel/unique-label logic); render via `selectable_axes_plot(labelled_dfs, x_options=data.x_options, ...)`.
3. **`routes/v0_1/info.py`** — add `"supports_overlay": block.supports_comparison()` to `/info/blocks` attributes (one line).

### Backend — per-block `get_comparison_data` (the rollout)

Pattern: reuse the block's existing parser/loader, build the df(s), return `ComparisonData`. The no-`file_id`/multi-file case mirrors the block's own behavior (XRD's "all compatible attached files"); most others are single-file.

- **`apps/xrd/blocks.py`** (XRDBlock) — implement hook; **relocate** the file-resolution + load loop from `comparison.py` into the block. Reuse `load_pattern`. Axes `[2θ, Q, d]` / `normalized intensity`.
- **`apps/raman/blocks.py`** (RamanBlock) — reuse `load()`; axes `[wavenumber (unit)]` / `normalized intensity`. (Also fix the `@classmethod load` that uses `self` → `cls`.)
- **`apps/ftir/__init__.py`** (FTIRBlock) — reuse `parse_ftir_asp/parse_ftir_txt`; axes `Wavenumber (cm⁻¹)` / `Absorbance`.
- **`apps/nmr/blocks.py`** (NMRBlock) — reuse `load_nmr_data` then deserialize to a df; axes `[ppm/hz]` / `normalized intensity`.
- **`apps/uvvis/__init__.py`** (UVVisBlock) — reuse `parse_uvvis_txt` + reference-absorbance; axes `Wavelength` / `Absorbance`.
- **`apps/eis/__init__.py`** (EISBlock) — reuse the EIS parsers; Nyquist axes `Re(Z) [Ω]` / `-Im(Z) [Ω]` (per-point frequency coloring dropped in overlay — acceptable).

### Frontend

4. **`webapp/src/views/ComparisonPage.vue`** — delete the hardcoded `OVERLAY_SUPPORTED` set; make `overlaySupported()` read `this.$store.state.blocksInfos[this.selectedBlockType]?.attributes?.supports_overlay`.

### Tests

5. **`pydatalab/tests/server/test_comparison.py`** — keep existing XRD tests. Add: (a) `/info/blocks` reports `supports_overlay` true for the 6 rolled-out types, false for a non-overlay type; (b) a parametrized overlay smoke test for raman + one more (reuse `example_data_dir` fixtures); (c) keep the no-`file_id` XRD regression test.

## Per-block effort survey (basis for the rollout scope)

| Block | Renderer | Reusable loader | Reduction (x / y) | Effort |
|-------|----------|-----------------|-------------------|--------|
| XRD | selectable_axes_plot | `load_pattern` (classmethod) | 2θ / normalized intensity | TRIVIAL |
| Raman | selectable_axes_plot | `load()` | wavenumber / normalized intensity | TRIVIAL |
| FTIR | selectable_axes_plot | `parse_ftir_asp/txt` | wavenumber / absorbance | TRIVIAL |
| NMR | selectable_axes_plot | `load_nmr_data` (instance, serialized) | ppm / normalized intensity | EASY |
| UV-Vis | selectable_axes_plot | `parse_uvvis_txt` + ref | wavelength / absorbance | EASY |
| EIS | selectable_axes_plot | parsers in utils | Re(Z) / -Im(Z) | EASY |
| CV | selectable_axes_plot | parsers + `_split_by_cycle` | potential / current | MEDIUM (deferred) |
| echem/Cycle | bespoke `double_axes_echem_plot` | `_load()` → `cycle_summary_df` | cycle # / capacity | MEDIUM (deferred) |
| MassSpec/TGA | per-species gridplot | `parse_mt_mass_spec_ascii` | — | OPT-OUT |
| Chat / Comment / Media / NotSupported | none / b64 image | — | — | OPT-OUT |
| Tabular | selectable_axes_plot | `load` | generic (no default x/y) | OPT-OUT |

**This iteration's scope: the 6 TRIVIAL+EASY spectral blocks.** CV and echem are deferred (MEDIUM); the rest opt out.

## Plugin author outcome

Implement `get_comparison_data` in the plugin block class (returning `ComparisonData`) and register
via the existing `pydatalab.apps.plugins` entry point — overlay then works with **no core or webapp
changes**. Complex plugins do nothing and stay side-by-side only. Overlay for plugins needs **no
webapp-plugin-component system** (rendering is generic Bokeh). Aligns with the planned
blocks-extraction-to-own-collection work: only where the endpoint sources `cfg` changes later; the
hook contract is unaffected.

## Verification

```bash
cd pydatalab && uv run pytest tests/server/test_comparison.py
curl -s localhost:5001/info/blocks | python -c "import json,sys; print({d['id']: d['attributes'].get('supports_overlay') for d in json.load(sys.stdin)['data']})"
# → xrd/raman/ftir/nmr/uv-vis/eis: True ; comment/ms/media/chat/cycle/cv/tabular: False
```
Manual: `/compare` with two samples of a rolled-out type → Overlay enabled & renders; a non-overlay
type → Overlay disabled with tooltip, side-by-side still works.

## Out of scope (future, incremental)

- MEDIUM blocks: CV (flatten dict-of-cycles) and echem/Cycle (expose `cycle_summary_df`) — later, one at a time.
- OPT-OUT blocks stay side-by-side only.
- Cross-type overlay on shared axes (e.g. Raman + FTIR on wavenumber) — same-type only for now.
