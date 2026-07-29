# datalab Hello In-App Tool

**Terms used:** [*Browser session*](../../pydatalab/docs/tools-glossary.md#browser-session), [*In-app tool*](../../pydatalab/docs/tools-glossary.md#in-app-tool), [*Permission-aware API*](../../pydatalab/docs/tools-glossary.md#permission-aware-api), [*Provider blueprint*](../../pydatalab/docs/tools-glossary.md#provider-blueprint).

Minimal *in-app tool* plugin. It renders below the normal datalab navigation,
uses the frontend SDK, and prints one datalab-backed message. datalab
automatically protects its *provider blueprint*, while the SDK uses the current
*browser session* for normal *permission-aware API* requests.

## Build the frontend bundle

```shell
cd plugin_examples/hello_in_app_tool/frontend
yarn install
yarn build
```

## Local installation

**Terms used:** [*plugins.toml*](../../pydatalab/docs/tools-glossary.md#plugins-toml).

Add the package to the root `plugins.toml`:

```toml
dependencies = ["datalab-hello-in-app-tool"]

[tool.uv.sources]
datalab-hello-in-app-tool = { path = "plugin_examples/hello_in_app_tool" }
```

Then install datalab with plugins:

```shell
cd pydatalab
uv run invoke dev.install
```

See `pydatalab/docs/tools-tutorials/in-app-hello-world.md`.
