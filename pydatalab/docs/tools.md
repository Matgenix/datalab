<!-- This file was edited with the assistance of an AI model and requires human review from the contributor. -->
# Tools

**Terms used:** [*Browser session*](tools-glossary.md#browser-session), [*In-app tool*](tools-glossary.md#in-app-tool), [*Item*](tools-glossary.md#item), [*Open mode*](tools-glossary.md#open-mode), [*Standalone tool*](tools-glossary.md#standalone-tool), [*Tool access token*](tools-glossary.md#tool-access-token), [*Tool launch grant*](tools-glossary.md#tool-launch-grant), [*Tool plugin*](tools-glossary.md#tool-plugin), [*Tool provider*](tools-glossary.md#tool-provider).

Tools are optional applications that work with data across *datalab*, rather than a visualisation attached to one *item*.
An authenticated user sees the tools available to them in the **Tools** navigation dropdown or on the full **Tools** page.
For a hands-on introduction, start with the
[standalone and in-app Hello World tutorials](tools-tutorials/index.md).

*Tool providers* have two UI choices:

| UI kind | Default open mode | Use it when |
|---|---|---|
| `standalone` | `new_tab` | The tool is a separate application or working environment, such as JupyterLab |
| `in_app` | `same_tab` | The tool should render below datalab's normal navigation and deliberately integrate with the web application |

A *standalone tool* owns its page and normally authenticates through a
single-use *tool launch grant*. An *in-app tool* is an administrator-trusted frontend bundle
served from the plugin's datalab API namespace. datalab mounts it at
`/tools/<tool-id>` without an iframe and supplies a small, versioned frontend
SDK. Either UI kind may set `open_mode` to `same_tab` or `new_tab`; this controls
browser navigation and is independent of where the UI runs.

!!! danger "Deployment administrators own the plugin trust decision"
    Installing a *tool plugin* authorizes its Python package to execute inside
    the datalab API process. Installing an in-app tool additionally authorizes its
    JavaScript to execute inside the authenticated datalab web application.
    That code can act with the signed-in user's *browser session* and can display,
    send, or modify any data that the user is allowed to access. datalab
    validates the provider namespace and SDK contract, but it cannot make
    malicious installed code safe. Administrators must review the source,
    provenance, dependencies, build artifacts, and update policy of every
    plugin before enabling it.
    For a separately hosted *standalone tool*, this trust decision also covers
    the remote operator and backend, where *tool access tokens* are delivered,
    and the service's data retention and deletion policies.

## How a tool interacts with datalab

**Terms used:** [*Authentication*](tools-glossary.md#authentication), [*Authorization*](tools-glossary.md#authorization), [*Browser session*](tools-glossary.md#browser-session), [*Current user*](tools-glossary.md#current-user), [*Current-user permissions*](tools-glossary.md#current-user-permissions), [*External tool server*](tools-glossary.md#external-tool-server), [*Group ID*](tools-glossary.md#group-id), [*In-app tool*](tools-glossary.md#in-app-tool), [*Item*](tools-glossary.md#item), [*Launch code*](tools-glossary.md#launch-code), [*Launch endpoint*](tools-glossary.md#launch-endpoint), [*Permanent API key*](tools-glossary.md#permanent-api-key), [*Provider callback*](tools-glossary.md#provider-callback), [*Role*](tools-glossary.md#role), [*Route authentication*](tools-glossary.md#route-authentication), [*Standalone tool*](tools-glossary.md#standalone-tool), [*Tool access token*](tools-glossary.md#tool-access-token), [*Tool launch grant*](tools-glossary.md#tool-launch-grant), [*Tool provider*](tools-glossary.md#tool-provider).

A *tool provider* is trusted Python code loaded into the API process.
At launch time it receives an immutable `ToolContext` containing only the *current user*'s stable ID, display name, *role*, and *group IDs*.
Providers should use this public context instead of importing datalab database internals.
This interface is data minimization, not a security sandbox: an installed Python package has the same process privileges as the API and must be trusted by the deployment administrator.

Standalone and *in-app tools* use different current-user access paths:

- A standalone provider calls `grants.issue(client_id)` during launch and
  passes the resulting short-lived code to its isolated UI or remote backend.
  An authenticated exchange endpoint consumes that code and returns a
  *tool access token*.
- An *in-app tool* is already running inside the authenticated datalab web
  application. It uses the SDK's API methods, which send the existing browser
  session and therefore apply the user's normal, current permissions. It does
  not mint or expose a *tool access token*.

*Launch codes* are single-use, bound to a user, tool, and client, stored only as
hashes, and must never be treated as *permanent API keys*. Successful
exchange atomically removes the *tool launch grant*, so it cannot be reused even
before its expiry.

datalab automatically authenticates every route in a provider's declared
Flask blueprint. One policy applies to the entire blueprint:

- `ToolRouteAuth.BROWSER`, the default, requires an active datalab browser
  session. Non-safe requests also require a trusted browser origin.
- `ToolRouteAuth.SERVICE` invokes the provider's
  `authenticate_service_request()` hook for machine-to-machine integrations.
  The framework rejects service providers that do not implement the hook.

This *route authentication* determines who may enter a route; it does not add
*item* filters to arbitrary plugin code. *In-app tools* should use
`DatalabToolSDK.api`, and *standalone tools* should use their *tool access token*
against normal datalab API endpoints. Those endpoints apply the existing
*current-user permissions*. A custom backend route that queries MongoDB directly
must explicitly use permission-aware datalab services or
`get_default_permissions()`.

The supported route ownership boundary is:

| Code or route | *Authentication* owner | Data *authorization* |
|---|---|---|
| Core catalog and *launch endpoints* | datalab core | *Current user* and provider availability |
| *Provider callbacks* such as `launch()` and `is_available()` | Called behind core endpoints; they are not HTTP routes | Restricted `ToolContext` |
| Routes in `ToolProvider.blueprint` | datalab applies the declared provider policy automatically | Normal API calls or explicit permission-aware backend queries |
| Routes on an *external tool server* | External operator | API calls made with a *tool access token* |
| Plugin routes added directly to the Flask app | Unsupported; bypasses the tool framework | No framework guarantee |

The `is_available()` method controls catalog and launch visibility only.
Plugins must add datalab-hosted routes exclusively through their declared
blueprint. Direct `app.add_url_rule()` calls or mutation of core blueprints are
unsupported. Because plugins are trusted in-process Python, this is an
enforced framework contract rather than a sandbox against malicious code.

*Tool access tokens* are accepted through the normal `DATALAB-API-KEY` header, so existing API clients and permission checks continue to work.
The API reloads the associated user on each request; account deactivation and *role* or group changes therefore take effect without restarting the tool.
datalab rejects *tool access tokens* from permanent-key rotation, login and
account mutation, administrator routes, and browser-only tool launch routes.
Tools must not call `/get-api-key/`, which rotates the user's *permanent API key*.

### HTTP API

**Terms used:** [*Authentication*](tools-glossary.md#authentication), [*Launch code*](tools-glossary.md#launch-code).

The canonical versioned endpoints are:

- `GET /v0.1/info/tools` for the current-user catalog;
- `POST /v0.1/tools/<tool-id>/launch` for either UI kind; and
- `/v0.1/tools/plugins/<tool-id>/...` for optional provider-owned routes.

The existing unversioned and full-version aliases are registered in the same
way as other datalab blueprints. datalab applies the provider's *authentication*
policy identically to every alias.
The built-in Jupyter integration exchanges its Basic-authenticated *launch code*
at `POST /v0.1/tools/plugins/jupyter/exchange`.

## Built-in JupyterLab

**Terms used:** [*Current-user snapshot*](tools-glossary.md#current-user-snapshot), [*Forced-login handler*](tools-glossary.md#forced-login-handler), [*Hub*](tools-glossary.md#hub), [*IPython startup file*](tools-glossary.md#ipython-startup-file), [*JupyterHub*](tools-glossary.md#jupyterhub), [*Kernel banner*](tools-glossary.md#kernel-banner), [*Launch code*](tools-glossary.md#launch-code), [*Launch code exchange*](tools-glossary.md#launch-code-exchange), [*New-notebook banner*](tools-glossary.md#new-notebook-banner), [*Notebook save hook*](tools-glossary.md#notebook-save-hook), [*Permanent API key*](tools-glossary.md#permanent-api-key), [*Preloaded datalab client*](tools-glossary.md#preloaded-datalab-client), [*Tool access token*](tools-glossary.md#tool-access-token).

JupyterLab is the first built-in provider and is disabled by default.
It can target either the *JupyterHub* shipped with the Docker Compose deployment or an independently managed, datalab-compatible *JupyterHub*:

- `TOOLS.JUPYTER.ENABLED=false` hides the tool.
- `ENABLED=true` with no `EXTERNAL_URL` selects the co-deployed *Hub*.
- `ENABLED=true` with `EXTERNAL_URL` set launches that external *Hub* and does not require a local *Hub* replica.

Both arrangements use the same *launch code exchange* and *tool access token*.
The integration's dedicated *forced-login handler* consumes a fresh code on each
launch, including when the browser already has a *JupyterHub* cookie from an
earlier datalab session.
New datalab users are created dynamically in *JupyterHub* on first launch, so the *Hub* does not require a restart or a pre-provisioned user list.
The notebook environment exposes a *preloaded datalab client* and a
*current-user snapshot* without exposing the user's *permanent API key*.

Every Python notebook and Jupyter console kernel receives:

```python
datalab       # authenticated datalab_api.DatalabClient
current_user  # launch-time identity, role, and group snapshot
```

The integration installs these names through an *IPython startup file*. They
are available without running an import cell and are deliberately visible to
`%who` and `%whos`. A *kernel banner* reports them when the frontend displays
kernel startup information.

A Jupyter Server *notebook save hook* places a short *new-notebook banner* in
each newly created blank notebook. The single-user bootstrap installs its HTML
template at `~/.local/share/datalab-jupyterhub/banner.html`, and the hook copies
that template into a non-editable but deletable Markdown cell. The banner
explains the two names but contains no user details, API URL, or credential.
Existing notebooks and non-empty notebooks imported into JupyterLab are not
changed. The managed JupyterLab configuration keeps the editor hidden for all
read-only Markdown cells; ordinary editable Markdown cells are unaffected.

See [Server configuration](config.md#tools) for settings.

## Deploying JupyterHub

**Terms used:** [*Authentication*](tools-glossary.md#authentication), [*Client ID*](tools-glossary.md#client-id), [*Client secret*](tools-glossary.md#client-secret), [*Current-user snapshot*](tools-glossary.md#current-user-snapshot), [*datalab API URL*](tools-glossary.md#datalab-api-url), [*Delegated tool session*](tools-glossary.md#delegated-tool-session), [*DockerSpawner*](tools-glossary.md#dockerspawner), [*External JupyterHub*](tools-glossary.md#external-jupyterhub), [*Hub*](tools-glossary.md#hub), [*JupyterHub*](tools-glossary.md#jupyterhub), [*Launch code*](tools-glossary.md#launch-code), [*Notebook container*](tools-glossary.md#notebook-container), [*Permanent API key*](tools-glossary.md#permanent-api-key), [*Reverse proxy*](tools-glossary.md#reverse-proxy), [*Tool access token*](tools-glossary.md#tool-access-token), [*WebSocket*](tools-glossary.md#websocket).

### Activation and Compose profile

**Terms used:** [*Hub*](tools-glossary.md#hub), [*JupyterHub*](tools-glossary.md#jupyterhub), [*Notebook container*](tools-glossary.md#notebook-container).

Jupyter has one user-facing switch and an optional external target.
The optional local *Hub* is selected with the `jupyterhub` Compose profile:

| `ENABLED` | `EXTERNAL_URL` | Compose profiles | Tools behavior |
|---|---|---|---|
| `false` | unset or set | `dev` or `prod` | Disabled |
| `true` | unset | `dev jupyterhub` or `prod jupyterhub` | Compose-managed *Hub* |
| `true` | set | `dev` or `prod` | External *Hub* |

Set the variables in the shell or the deployment `.env`, then use the
normal Compose arguments:

```shell
docker compose --profile prod --profile jupyterhub up --build --wait
docker compose --profile dev --profile jupyterhub up --build --wait
```

The *JupyterHub* service has the fixed profile `jupyterhub`; there are no generated
profiles such as `prod-external`.
The production and development profiles are alternatives and are not intended
to run simultaneously.
The managed *Hub* service reads `.docker/jupyterhub/.env` through its Compose
`env_file`. Keep the shared `PYDATALAB_TOOLS__JUPYTER__CLIENT_ID`,
`PYDATALAB_TOOLS__JUPYTER__CLIENT_SECRET`, and
`PYDATALAB_TOOLS__JUPYTER__PUBLIC_URL` values in sync with `pydatalab/.env`.
The *Hub* is an administrator-trusted service with Docker-spawning access; spawned
*notebook containers* do not receive this file and are given only their
current-user runtime variables.
Docker Compose does not use service `env_file` values for host-side
interpolation such as published ports; customize those values from the shell
only when needed.
Outside Compose, enabling Jupyter without `EXTERNAL_URL` does not start a
process: the deployer must run a compatible *Hub* at the configured public URL.

Conditional logic does not run in the container entrypoint.
An entrypoint no-op would still create an exited or dummy service, interact
poorly with restart policies, and make `docker compose up --wait` misleading.
When a local replica exists, its entrypoint always starts a real *JupyterHub* and
its healthcheck represents the real service.

Docker Compose 2.20 or newer is required for the optional
`depends_on.required: false` relationship used with the optional *Hub* profile.
*JupyterHub* has optional healthy dependencies on both `api` and `api-dev`.
Both API services receive the same public tool settings and use the common
tool-network alias `datalab-api`, so only the API selected by the active profile
needs to be running.

### Local URL and reverse proxy

**Terms used:** [*Hub*](tools-glossary.md#hub), [*Launch code*](tools-glossary.md#launch-code), [*Reverse proxy*](tools-glossary.md#reverse-proxy), [*WebSocket*](tools-glossary.md#websocket).

The Compose *Hub* binds to `127.0.0.1:8000` by default. Because this is a
host-side Compose interpolation setting, customize the address and port from
the shell with `PYDATALAB_JUPYTERHUB_BIND_ADDRESS` and
`PYDATALAB_JUPYTERHUB_PORT` if needed.
For loopback development, the browser URL can therefore be
`http://localhost:8000/jupyter/`.

In production, set `PYDATALAB_APP_URL` to the canonical frontend URL and route
its `/jupyter/` path to the *Hub*, or set
`PYDATALAB_TOOLS__JUPYTER__PUBLIC_URL` to another browser-facing HTTPS base URL.
The proxy must:

- preserve the `/jupyter/` prefix and forwarded host/protocol information;
- proxy normal HTTP requests to *Hub* port 8000;
- support *WebSocket* upgrades and long-lived connections, including per-user
  kernel channel paths below `/jupyter/user/`;
- use timeouts appropriate for interactive kernels;
- omit or redact the `datalab_launch_code` query value from proxy access logs; and
- terminate TLS for every non-loopback deployment.

The *Hub* also redacts the *launch code* from its own handler log and marks the
redirect `no-referrer`.

`PUBLIC_URL` changes the co-deployed *Hub*'s browser URL and base path.
`EXTERNAL_URL` instead selects a separately administered *Hub* and suppresses the
local replica.

### Network, socket, and storage boundaries

**Terms used:** [*Authentication*](tools-glossary.md#authentication), [*Client secret*](tools-glossary.md#client-secret), [*Current-user snapshot*](tools-glossary.md#current-user-snapshot), [*DockerSpawner*](tools-glossary.md#dockerspawner), [*Hub*](tools-glossary.md#hub), [*JupyterHub*](tools-glossary.md#jupyterhub), [*Tool access token*](tools-glossary.md#tool-access-token).

Use a dedicated Docker network shared only by the API, *JupyterHub*, and spawned
user servers.
Give both production and development APIs the alias `datalab-api`, so
the *Hub* and notebooks use `http://datalab-api:5001` independently of the active
profile.
Keep MongoDB off this tools network: notebook processes must not be able to
bypass the datalab API and its current-user permission checks.
The API may join both the database backend network and the tools network.

*DockerSpawner* needs the Docker socket to create per-user containers.
Possession of that socket is effectively host-root access, so only the
administrator-trusted *Hub* receives it.
User servers must receive no Docker socket, MongoDB credentials or network,
Flask secrets, host filesystem mounts, or shared *client secret*.
They receive only their own *tool access token*, *current-user snapshot*,
API URL, and persistent work volume.

The managed defaults are:

- 2 CPU cores and 4 GiB memory per user server;
- shutdown after one hour of inactivity;
- a maximum server age of 24 hours; and
- a named work volume keyed by the Compose project and stable Jupyter username
  derived from the immutable datalab user ID.

The *Hub* database, cookie secret, and encrypted *authentication* state live in the
separate `datalab-jupyterhub-data` volume.
Stopping or upgrading the *Hub* removes disposable user containers but preserves
their named work volumes.
Deployment administrators should add host-level storage quotas and a documented
volume-retention/removal policy appropriate to their environment.

### External JupyterHub

**Terms used:** [*Client ID*](tools-glossary.md#client-id), [*Client secret*](tools-glossary.md#client-secret), [*datalab API URL*](tools-glossary.md#datalab-api-url), [*Delegated tool session*](tools-glossary.md#delegated-tool-session), [*DockerSpawner*](tools-glossary.md#dockerspawner), [*External JupyterHub*](tools-glossary.md#external-jupyterhub), [*Hub*](tools-glossary.md#hub), [*JupyterHub*](tools-glossary.md#jupyterhub), [*Permanent API key*](tools-glossary.md#permanent-api-key), [*Tool access token*](tools-glossary.md#tool-access-token).

With `ENABLED=true` and `EXTERNAL_URL` set, the datalab API returns that *Hub*'s
login URL. Do not include the `jupyterhub` Compose profile in that deployment.
The external administrator owns TLS, proxying, availability, upgrades,
spawning, resource limits, culling, and per-user persistent storage.

Install the compatible `datalab-jupyterhub` integration package in the *Hub* and
configure its `DatalabAuthenticator` with:

- a server-reachable *datalab API URL*;
- the same *client ID* and 32-character-or-longer *client secret* configured in
  datalab;
- persistent encrypted `auth_state`, with a persistent
  `JUPYTERHUB_CRYPT_KEY`; and
- dynamic user creation rather than a pre-provisioned user list.

The single-user image must contain `datalab-api` and the integration bootstrap.
Use `datalab-jupyter-singleuser` as the spawner command to install the
*IPython startup file* and create the welcome notebook before JupyterLab starts.
Installing the integration package also enables its Jupyter Server
*notebook save hook*, which supplies the *new-notebook banner*.
The spawner may be *DockerSpawner*, KubeSpawner, or another implementation, but
it must isolate each user's storage and inject only that user's *delegated tool
session* state.

*tool access tokens* last at most 24 hours.
Keep external user servers within that lifetime and require the user to launch
again after expiry; do not replace the *tool access token* with a permanent
API key.

## Writing a tool plugin

**Terms used:** [*API alias*](tools-glossary.md#api-alias), [*Copier*](tools-glossary.md#copier), [*Launch code*](tools-glossary.md#launch-code), [*Launch code exchange*](tools-glossary.md#launch-code-exchange), [*Permanent API key*](tools-glossary.md#permanent-api-key), [*plugins.toml*](tools-glossary.md#plugins-toml), [*Provider ID*](tools-glossary.md#provider-id), [*Standalone tool*](tools-glossary.md#standalone-tool), [*Table-selection tool action*](tools-glossary.md#table-selection-tool-action), [*Tool access token*](tools-glossary.md#tool-access-token), [*Tool launch action*](tools-glossary.md#tool-launch-action), [*Tool plugin*](tools-glossary.md#tool-plugin).

Generate a package from the in-repository *Copier* template:

```shell
uvx copier copy templates/datalab-tool-plugin-template ../my-datalab-tool
```

*Copier* asks for the UI kind:

- `standalone` generates a protected standalone page, *launch code exchange*,
  and API example using a *tool access token*; and
- `in-app` generates a protected in-app provider plus a small Vite project
  containing `ToolView.vue`, SDK registration, and prefixed CSS.

For an in-app plugin, *Copier* can optionally add one
*table-selection tool action*. When enabled, it asks for the action label,
supported tables, and selection bounds. When disabled, no selection-specific
metadata or frontend code is generated.

Only files for the selected variant are emitted. The UI kind and *open mode*
are recorded as `tool_ui_kind` and `tool_open_mode` in
`.copier-answers.yml`, so later *Copier* updates retain both choices.

The package registers a zero-argument `ToolProvider` subclass:

```toml
[project.entry-points."pydatalab.tools"]
example-tool = "example_tool:ExampleToolProvider"
```

The entry-point name must equal the provider's lowercase, hyphenated `id`.
The provider declares immutable `ToolMetadata` and implements
`launch(context, grants)`. It may override `is_available(context)` when it
needs per-user catalog visibility; the default makes the tool available.
It may expose a Flask `Blueprint`; datalab mounts that blueprint below `/tools/plugins/<tool-id>/` for every supported *API alias*.
Providers are discovered once at API startup, so installing or removing one requires an API restart.
A broken or duplicate third-party provider is logged and skipped without preventing the server from starting.
Blueprint routes use `ToolRouteAuth.BROWSER` by default, so generated plugins
do not repeat browser-user or origin decorators. A provider exposing only
machine-to-machine routes declares `ToolRouteAuth.SERVICE` and implements
`authenticate_service_request()`. Mixed policies within one blueprint are not
supported.

Install the generated package through the same root `plugins.toml` mechanism used by data-block plugins; see [Plugins](plugins.md#installing-plugins).
Deployment administrators can disable an installed provider without uninstalling it by adding its ID to `TOOLS.DISABLED`.
For small end-to-end examples, follow the
[standalone Hello World](tools-tutorials/standalone-hello-world.md) and
[in-app Hello World](tools-tutorials/in-app-hello-world.md) tutorials.

### Optional table-selection action

**Terms used:** [*Copier*](tools-glossary.md#copier), [*Item refcode*](tools-glossary.md#item-refcode), [*Permission-aware API*](tools-glossary.md#permission-aware-api), [*Python entry point*](tools-glossary.md#python-entry-point), [*Selected-items dropdown*](tools-glossary.md#selected-items-dropdown), [*Selection query parameters*](tools-glossary.md#selection-query-parameters), [*Stable table identifier*](tools-glossary.md#stable-table-identifier), [*Table-selection tool action*](tools-glossary.md#table-selection-tool-action), [*Tool catalog*](tools-glossary.md#tool-catalog), [*Tool frontend SDK*](tools-glossary.md#tool-frontend-sdk), [*Tool host*](tools-glossary.md#tool-host), [*Tool launch action*](tools-glossary.md#tool-launch-action).

An in-app provider may declare a *tool launch action* for selected rows:

```python
metadata = ToolMetadata(
    name="Example comparison",
    description="Compare selected items.",
    ui=InAppToolUI(entrypoint="frontend/tool.js", sdk_version=1),
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

The supported *stable table identifiers* are `samples`, `inventory`,
`equipment`, and `collection-items`. datalab validates that an action has a
provider-local slug ID, a non-empty label, at least one unique table, and
selection bounds satisfying `1 <= min_items <= max_items <= 100`.
Standalone providers cannot declare this action in v1.

When a user first opens the *selected-items dropdown*, the webapp reads the
current-user *tool catalog*. It inserts applicable tool actions after **Add to
collection** and leaves built-in actions available if catalog loading fails.
Actions remain visible but disabled when the selection is outside the declared
bounds or a row has no *item refcode*. Disabled or unavailable providers
contribute no actions.

An enabled action navigates through the normal *tool host*:

```text
/tools/example-comparison?action=compare-selected&items=test%3AABC&items=test%3ADEF
```

The repeated `items` values are ordered, deduplicated *item refcodes*. No item
name, mutable item ID, blocks, or complete table row is handed to the plugin.
The URL is still untrusted input: the tool must fetch current data through
permission-aware API routes.

Frontend SDK v1 exposes the normalized *selection query parameters*:

```javascript
const { actionId, itemRefcodes } = sdk.selection.current();
await sdk.selection.replaceItemRefcodes([...itemRefcodes, nextRefcode]);
```

`replaceItemRefcodes()` preserves unrelated query state, so adding or removing
items keeps the comparison bookmarkable. This *tool launch action* is unrelated
to the packaging *Python entry point* used to discover the provider.

### Standalone tool declaration

**Terms used:** [*Copier*](tools-glossary.md#copier), [*Launch code*](tools-glossary.md#launch-code), [*Permanent API key*](tools-glossary.md#permanent-api-key), [*Standalone tool*](tools-glossary.md#standalone-tool).

The standalone *Copier* variant generates this form:

```python
metadata = ToolMetadata(
    name="Example tool",
    description="A separate application.",
    ui=StandaloneToolUI(open_mode="new_tab"),
)

def launch(self, context, grants):
    code = grants.issue("example-tool")
    return ToolLaunchResult(
        url=f"https://tool.example/#datalab_launch_code={code}",
    )
```

The browser validates the returned HTTP(S) URL and opens it in a new tab.
*Standalone tools* do not receive the frontend SDK or datalab Vue components.
For a browser bootstrap page, carry the *launch code* in the URL fragment so
the initial request and normal proxy logs do not contain it, then remove the
fragment immediately. A separately hosted page should pass the code to its
trusted backend, which authenticates itself and performs the server-to-server
exchange.

A separately hosted UI is outside datalab's automatic route protection. If it
needs a datalab-hosted exchange or callback, the installed provider must expose
that endpoint through a `SERVICE` blueprint. Setting `blueprint = None` is
sufficient only for a data-independent external UI or when another installed
service already provides the required callback. External tools must not receive
MongoDB credentials, Flask secrets, *permanent API keys*, or direct database
access.

### In-app tool declaration

**Terms used:** [*Copier*](tools-glossary.md#copier), [*Provider ID*](tools-glossary.md#provider-id).

An in-app provider declares a relative compiled entrypoint and the frontend SDK
version it was built against:

```python
metadata = ToolMetadata(
    name="Example comparison",
    description="Compare data without leaving datalab.",
    ui=InAppToolUI(
        open_mode="same_tab",
        entrypoint="frontend/tool.js",
        sdk_version=1,
    ),
)
blueprint = TOOL_BLUEPRINT

def launch(self, context, grants):
    return ToolLaunchResult()
```

*In-app tool* providers must have a blueprint, and the entrypoint must be a
canonical relative path below that provider's namespace. Absolute URLs,
traversal segments, encoded path separators, queries, and fragments are
rejected. The webapp loads bundles only from:

```text
<datalab API>/tools/plugins/<tool-id>/<entrypoint>
```

The bundle synchronously registers its component:

```javascript
window.DatalabToolSDK.register({
  id: "example-comparison",
  sdkVersion: 1,
  component: ExampleComparison,
});
```

SDK version 1 exposes the host Vue runtime, selected datalab components,
authenticated `get` and `post` API helpers, navigation helpers, and the normal
dialog service. The frontend can use query parameters and nested paths below
`/tools/<tool-id>/...`. It should use the SDK surface rather than importing the
webapp's private Vuex store or relying on internal source paths.

The in-app tool loader checks the requested *provider ID*, SDK version, provider
namespace, registration, and load timeout. These checks prevent accidental
misconfiguration; they are not a sandbox for an untrusted plugin.

The in-app *Copier* variant builds `frontend/src/main.js`,
`frontend/src/ToolView.vue`, and its CSS into the one classic
`static/frontend/tool.js` bundle expected by the loader. Vue is externalized to
`window.DatalabToolSDK.vue`; the plugin must not ship a second runtime.
The stylesheet is embedded into the JavaScript bundle and scoped below a
tool-specific root class.

Run `yarn install` and `yarn build` in the generated `frontend/` directory
before packaging the Python distribution. Commit and review the resulting
dependency lockfile and compiled bundle. A deployment administrator must be
able to verify that the browser artifact is the one built from the reviewed
source; installing the Python provider alone does not make the JavaScript
trustworthy. The generated source distribution contains the `frontend` source
and lockfile for that review; its wheel contains the compiled browser asset.

## Item comparison example plugin

**Terms used:** [*Comparison tool plugin*](tools-glossary.md#comparison-tool-plugin), [*Item refcode*](tools-glossary.md#item-refcode), [*Table-selection tool action*](tools-glossary.md#table-selection-tool-action), [*Tool frontend SDK*](tools-glossary.md#tool-frontend-sdk), [*Tool plugin*](tools-glossary.md#tool-plugin).

`plugin_examples/comparison_tool` converts the earlier cross-sample work into
the independently installable *comparison tool plugin*. It renders inside
datalab and declares **Compare selected** for Samples, Inventory, and items
within a collection. It deliberately does not contribute the action to
Equipment.

The action passes ordered *item refcodes*. The plugin retrieves every selected
item through `/items/<refcode>`, then uses the returned current item ID only for
its permission-checked preview and overlay requests. Opening the plugin from the
Tools menu without a selection still shows the empty comparison page. See the
example [README](../../plugin_examples/comparison_tool/README.md) for build and
deployment instructions.
