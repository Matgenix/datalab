# datalab Hello Standalone Tool

**Terms used:** [*Browser session*](../../pydatalab/docs/tools-glossary.md#browser-session), [*Launch code*](../../pydatalab/docs/tools-glossary.md#launch-code), [*Permission-aware API*](../../pydatalab/docs/tools-glossary.md#permission-aware-api), [*Provider blueprint*](../../pydatalab/docs/tools-glossary.md#provider-blueprint), [*Sample*](../../pydatalab/docs/tools-glossary.md#sample), [*Standalone tool*](../../pydatalab/docs/tools-glossary.md#standalone-tool), [*Tool access token*](../../pydatalab/docs/tools-glossary.md#tool-access-token).

Minimal *standalone tool* plugin. It opens in a new tab, exchanges a *launch code*,
and prints one datalab-backed message. datalab automatically protects its
*provider blueprint* with the active *browser session*; the resulting tool access
token accesses *samples* through the normal *permission-aware API*.

## Local installation

**Terms used:** [*plugins.toml*](../../pydatalab/docs/tools-glossary.md#plugins-toml).

Add the package to the root `plugins.toml`:

```toml
dependencies = ["datalab-hello-standalone-tool"]

[tool.uv.sources]
datalab-hello-standalone-tool = { path = "plugin_examples/hello_standalone_tool" }
```

Then install datalab with plugins:

```shell
cd pydatalab
uv run invoke dev.install
```

See `pydatalab/docs/tools-tutorials/standalone-hello-world.md`.
