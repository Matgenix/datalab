# Plugins

## Overview

Plugins are independently installable Python packages that extend datalab
without requiring changes to the core repository. They are discovered when the
API starts through standard Python package entry points.

Plugins can be public or private. Public plugins may use the
[`datalab-plugin` topic on GitHub](https://github.com/topics/datalab-plugin);
there is no formal plugin registry at present.

datalab currently supports:

- **Data block plugins**, which add parsers and visualisations for data attached
  to items.
- **Tool plugins**, which add [in-app or standalone tools](tools.md).

Other extension points, such as custom item types and ingestion hooks, are
possible future additions; see the [roadmap](roadmap.md).

!!! warning "Only install plugins you trust"
    A plugin runs inside the datalab API process with the same privileges as
    the server. An in-app tool plugin also runs JavaScript inside each signed-in
    user's datalab page.

    The deployment administrator is responsible for reviewing and trusting the
    plugin's source, dependencies, compiled frontend assets, maintainers, and
    update process. Framework validation catches accidental incompatibilities;
    it does not isolate deliberately malicious installed code.

## Writing a Data Block plugin

A Data Block plugin registers one or more
[`DataBlock`](blocks/index.md) classes through the
`pydatalab.apps.plugins` entry-point group. Data blocks parse files attached to
an item and provide the corresponding data representation and visualisation.

Start from the
[datalab app plugin template](https://github.com/datalab-org/datalab-app-plugin-template).
The template contains the package metadata, a minimal block implementation,
tests, and installation instructions.

The [Data Blocks documentation](blocks/index.md) explains the block lifecycle,
events, rendering, and asynchronous processing in more detail.

## Writing a Tool plugin

A Tool plugin registers a provider through the `pydatalab.tools` entry-point
group. Start from the Copier template:

```shell
uvx copier copy https://github.com/Matgenix/datalab-tool-plugin-template \
  ../my-datalab-tool
```

The template repository is hosted at
[Matgenix/datalab-tool-plugin-template](https://github.com/Matgenix/datalab-tool-plugin-template).

The template asks for the tool name, its stable ID, its Python distribution
name, the UI type, and whether it opens in the same browser tab or a new one.
For an in-app tool it can also generate an optional selected-items table
action. It derives the Python package and provider class names automatically.

### Provider contract and discovery

The package exposes a zero-argument `ToolProvider` subclass:

```toml
[project.entry-points."pydatalab.tools"]
example-tool = "example_tool.provider:ExampleToolProvider"
```

The entry-point name must match the provider's lowercase, hyphenated `id`. The
provider declares immutable `ToolMetadata` and may implement:

- `launch(context, grants)`, which returns `None` for an in-app tool or an
  HTTP(S) URL for a standalone tool;
- `is_available(context)`, which controls whether the current user can see and
  launch the tool; and
- a Flask `Blueprint` containing provider-owned routes.

datalab discovers providers once at API startup. A provider that fails to load
is logged and skipped without preventing the server from starting. Duplicate
IDs are rejected. Installing or removing a plugin therefore requires an API
restart. An administrator can disable an installed provider by adding its ID to
`TOOLS.DISABLED`.

Provider blueprints are the only supported way for a plugin to add routes to
datalab. The framework mounts them below
`/tools/plugins/<tool-id>/` for every supported API alias and automatically
authenticates every route:

- the default browser policy requires an active datalab browser session and
  validates the origin of non-safe requests;
- the service policy is for machine-to-machine integrations and requires the
  provider to implement `authenticate_service_request()`.

Automatic route authentication determines who may enter a route. It does not
automatically filter arbitrary database queries. Plugins should retrieve data
through the normal datalab API or explicitly use permission-aware datalab
services for server-side processing.

The route ownership boundary is:

| Interface | Authentication | Data permissions |
|---|---|---|
| Core catalog and launch endpoints | datalab | Current user and provider availability |
| Provider callbacks such as `launch()` and `is_available()` | Called by protected core routes; they are not routes themselves | Restricted provider context |
| Routes in `ToolProvider.blueprint` | Provider's browser or service policy, applied by datalab | Normal API calls or explicit permission-aware server queries |
| Routes on an external tool service | External service | Calls to the datalab API with a temporary tool access token |

Directly registering routes on the Flask app or modifying core blueprints is
unsupported and bypasses the tool framework's guarantees.

The canonical API endpoints are:

- `GET /v0.1/info/tools` for the current-user catalog;
- `POST /v0.1/tools/<tool-id>/launch` to launch either UI type; and
- `/v0.1/tools/plugins/<tool-id>/...` for provider-owned routes.

### In-app tools

An in-app tool renders below the normal datalab navigation:

```python
metadata = ToolMetadata(
    name="Example analysis",
    description="Analyse data without leaving datalab.",
    ui=InAppToolUI(),
)
```

The provider serves one compiled frontend entrypoint from its blueprint. The
bundle registers its component synchronously:

```javascript
window.datalabToolSdk.register(ToolView);
```

The versioned frontend SDK supplies the host runtime, authenticated API helpers,
navigation helpers, selected datalab components, and the standard dialog
service. An in-app tool should use these supported interfaces rather than the
webapp's private store or internal source paths.

The template's Vite project builds one classic JavaScript bundle, externalising
the frontend runtime supplied by datalab. Build it before packaging the Python
distribution:

```shell
cd frontend
yarn install
yarn build
```

Commit and review the dependency lockfile and compiled bundle. Loading a bundle
into the webapp is an administrator trust decision, not a browser sandbox.

### Selected-items table actions

An in-app tool may add an action to selected-items menus:

```python
metadata = ToolMetadata(
    name="Example comparison",
    description="Compare selected items.",
    ui=InAppToolUI(),
    launch_actions=(
        ItemTableSelectionAction(
            id="compare-selected",
            label="Compare selected",
            tables=("samples", "inventory", "collection-items"),
            min_items=2,
            max_items=20,
        ),
    ),
)
```

The supported table identifiers are `samples`, `inventory`, `equipment`, and
`collection-items`. Selection limits must satisfy
`1 <= min_items <= max_items <= 100`.

When the user chooses the action, datalab opens the normal tool host with
ordered, deduplicated item refcodes:

```text
/tools/example-comparison?action=compare-selected&items=test%3AABC&items=test%3ADEF
```

The frontend reads them through the SDK:

```javascript
const { actionId, itemRefcodes } = sdk.selection.current();
```

Only immutable refcodes are passed—not item names, blocks, database IDs, or
complete table rows. Query parameters are untrusted input, so the plugin must
load current item data through permission-aware API routes.

The
[datalab item comparison tool](https://github.com/Matgenix/datalab-item-comparison-tool)
demonstrates this integration for Samples, Inventory, and items within a
collection.

### Standalone tools

A standalone tool owns its user interface and normally opens separately:

```python
metadata = ToolMetadata(
    name="Example tool",
    description="A separate application.",
    ui=StandaloneToolUI(),
)

def launch(self, context, grants):
    code = grants.issue("example-tool")
    return f"https://tool.example/#datalab_launch_code={code}"
```

The launch code is short-lived, single-use, and bound to the user, tool, and
client. A successful exchange atomically consumes it and returns a temporary
tool access token. The standalone application uses that token only with normal
datalab API endpoints, which apply the current user's permissions.

Keep launch codes in URL fragments rather than query parameters where possible,
remove them from the address bar immediately, and never put the resulting tool
access token in URLs, persistent browser storage, notebooks, files, analytics,
or logs. Tool access tokens must not be confused with users' permanent datalab
API keys.

A separately hosted application is outside datalab's automatic route
protection. Its administrator owns its authentication, isolation, storage, and
data-retention policy. If it requires a callback hosted by datalab, the
installed provider must expose that callback through a service-authenticated
provider blueprint.

### Tool plugin development tutorials

The tutorials build two deliberately small plugins:

- [Developing a standalone Tool plugin](plugin-development/standalone-tool-plugin.md),
  accompanied by the
  [standalone example repository](https://github.com/Matgenix/datalab-standalone-tool-plugin-example),
  opens in a new tab and displays the signed-in user's accessible sample count.
- [Developing an in-app Tool plugin](plugin-development/in-app-tool-plugin.md),
  accompanied by the
  [in-app example repository](https://github.com/Matgenix/datalab-in-app-tool-plugin-example),
  renders inside datalab and displays the same small piece of API-backed data.

Start with the
[plugin development tutorial overview](plugin-development/index.md) for a
side-by-side explanation of discovery and current-user access.

## Installing plugins

Plugins are declared in a `plugins.toml` file at the repository root, alongside
`pydatalab/` and `webapp/`. The format mirrors the relevant parts of
`pyproject.toml`; its JSON Schema is stored at
`pydatalab/schemas/plugin_config.json`.

```toml
# plugins.toml
dependencies = [
    "datalab-app-plugin-insitu",
    "my-local-plugin",
]

[tool.uv.sources]
# Pin a Git dependency to a specific revision.
datalab-app-plugin-insitu = { git = "https://github.com/datalab-org/datalab-app-plugin-insitu.git", rev = "v0.4.1" }

# Or install a local checkout; paths are relative to plugins.toml.
my-local-plugin = { path = "../my-local-plugin", editable = true }
```

Install datalab together with the declared plugins:

```shell
cd pydatalab
uv run invoke dev.install
```

This task:

1. merges `plugins.toml` into a copy of `pyproject.toml` under `build/`;
2. regenerates `build/uv.lock` so plugin versions are locked with the core
   dependencies; and
3. synchronises the resulting environment.

Pass `--no-dev` to omit development dependencies. If no `plugins.toml` exists,
the task installs the base project, so it is safe to run unconditionally.

To return to the locked core dependencies without plugins:

```shell
uv sync --all-extras --dev
```

The production API Docker image uses the same installation task. A root
`plugins.toml` is therefore picked up during the image build, allowing plugins
to be included without modifying the Dockerfile. The
[datalab Ansible deployment](https://github.com/datalab-org/datalab-ansible-terraform)
can use the same file.
