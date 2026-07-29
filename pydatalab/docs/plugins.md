# Plugins

**Terms used:** [*Data block*](tools-glossary.md#data-block), [*In-app tool*](tools-glossary.md#in-app-tool), [*Standalone tool*](tools-glossary.md#standalone-tool).

*datalab*'s plugin system is under active development, as is this documentation page.
It currently supports custom application *data blocks*, *standalone tools*, and
*in-app tools*. See [Tools](tools.md).

*datalab* supports plugins that extend the server with new functionality.
Some self-declared plugins can be found via the [`datalab-plugin` topic on GitHub](https://github.com/topics/datalab-plugin), in lieu of a formal registry at this time.
Plugins can also be kept private and installed from e.g., a private git repository, or a local path on the host, using the same installation described below.

!!! warning "Only install plugins you trust"
    Plugins are installed into the same Python environment as the *datalab*
    server and run with full server privileges. *In-app tool* plugins also run
    JavaScript inside each signed-in user's datalab page. The deployment
    administrator is responsible for reviewing and trusting the plugin's
    source, dependencies, distributed frontend bundles, maintainer, and update
    process. datalab's plugin validation is not a security sandbox.

## What a plugin is

**Terms used:** [*Authentication*](tools-glossary.md#authentication), [*Data block*](tools-glossary.md#data-block), [*Item*](tools-glossary.md#item), [*Standalone tool*](tools-glossary.md#standalone-tool).

A *datalab* plugin is a Python package discovered at server startup through one of these Python entry-point groups:

- `pydatalab.apps.plugins` registers [data block](blocks/index.md) classes. *Data blocks* ingest files attached to an *item* and render a view of the parsed data.
- `pydatalab.tools` registers *standalone tools* that open separately and trusted
  *in-app tools* that render within the webapp. See [Tools](tools.md) for their
  lifecycle, trust boundary, and *authentication* model.

Custom *item* types and ingestion hooks remain future work; see the [roadmap](roadmap.md).

## Writing a plugin

**Terms used:** [*Authentication*](tools-glossary.md#authentication), [*Copier*](tools-glossary.md#copier), [*Data block*](tools-glossary.md#data-block), [*In-app tool*](tools-glossary.md#in-app-tool), [*Route authentication*](tools-glossary.md#route-authentication), [*Table-selection tool action*](tools-glossary.md#table-selection-tool-action), [*Tool launch grant*](tools-glossary.md#tool-launch-grant), [*Tool plugin*](tools-glossary.md#tool-plugin).

For a *data block*, start from the [datalab-app-plugin-template](https://github.com/datalab-org/datalab-app-plugin-template).
For either a standalone or an *in-app tool*, use the *Copier* template shipped in
this repository:

```shell
uvx copier copy templates/datalab-tool-plugin-template ../my-datalab-tool
```

The template asks which UI kind and open mode the tool should use. The standalone variant
contains a separate page and current-user access through a single-use
*tool launch grant*. The in-app variant contains an automatically protected blueprint, a Vue
single-file component, and a Vite build that targets datalab's frontend SDK.
It can also declare an optional *table-selection tool action* without adding
plugin-specific code to datalab's item tables.
datalab applies one *authentication* policy to every route in a provider's
declared blueprint. Object-level permissions still come from normal API calls
or explicit permission-aware server queries; *route authentication* alone does
not filter arbitrary database access.
See [Writing a tool plugin](tools.md#writing-a-tool-plugin) for the provider contract.
The [tool plugin tutorials](tools-tutorials/index.md) walk through two minimal
Hello World examples: one standalone new-tab tool and one *in-app tool*.

## Installing plugins

**Terms used:** [*plugins.toml*](tools-glossary.md#plugins-toml), [*Role*](tools-glossary.md#role).

Plugins are declared in a `plugins.toml` file at the root of the repository (alongside `pydatalab/` and `webapp/`).
The format mirrors the relevant fragments of `pyproject.toml`, and a generated JSON Schema describing the expected structure is checked in at `pydatalab/schemas/plugin_config.json`:

```toml
# plugins.toml (at the repository root)
dependencies = [
    "datalab-app-plugin-insitu",
    "my-local-plugin",
]

[tool.uv.sources]
# Pin to a specific git ref:
datalab-app-plugin-insitu = { git = "https://github.com/datalab-org/datalab-app-plugin-insitu.git", rev = "v0.4.1" }
# Or point at a local checkout (paths are resolved relative to plugins.toml itself):
my-local-plugin = { path = "../my-local-plugin", editable = true }
```

To install *datalab* together with the declared plugins:

```shell
cd pydatalab
uv run invoke dev.install
```

This task:

1. Merges `plugins.toml` into a copy of `pyproject.toml` under `./build/` (as a `plugins` optional-dependency group, plus any `[tool.uv.sources]` entries).
2. Regenerates `./build/uv.lock` so plugin versions are locked alongside the core deps.
3. Runs `uv sync --all-extras --active --project ./build` to install everything into the currently active *datalab* virtual environment.

Pass `--no-dev` to skip dev dependencies (used by the production Docker build).

If no `plugins.toml` is present, the task falls back to installing the base `pyproject.toml` — so it is safe to run unconditionally.

To revert to the locked core dependencies without any plugins, run:

```shell
uv sync --all-extras --dev
```

The same `invoke dev.install` task is used by the production Docker image (`.docker/server/Dockerfile`): a `plugins.toml` at the repository root is picked up automatically at build time, so plugins can be baked into a custom image without modifying the Dockerfile itself.
It will also be invoked from the [*datalab* Ansible role](https://github.com/datalab-org/datalab-ansible-terraform) to provision plugins on a deployed server when a `plugins.toml` is provided; see the *role* documentation for details.
