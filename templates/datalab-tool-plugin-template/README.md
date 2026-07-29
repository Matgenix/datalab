<!-- This file was edited with the assistance of an AI model and requires human review from the contributor. -->
# datalab tool plugin template

**Terms used:** [*Authentication*](../../pydatalab/docs/tools-glossary.md#authentication), [*Browser session*](../../pydatalab/docs/tools-glossary.md#browser-session), [*Copier*](../../pydatalab/docs/tools-glossary.md#copier), [*datalab tool*](../../pydatalab/docs/tools-glossary.md#datalab-tool), [*In-app tool*](../../pydatalab/docs/tools-glossary.md#in-app-tool), [*Item*](../../pydatalab/docs/tools-glossary.md#item), [*Standalone tool*](../../pydatalab/docs/tools-glossary.md#standalone-tool), [*Table-selection tool action*](../../pydatalab/docs/tools-glossary.md#table-selection-tool-action), [*Tool access token*](../../pydatalab/docs/tools-glossary.md#tool-access-token), [*Tool plugin*](../../pydatalab/docs/tools-glossary.md#tool-plugin), [*Tool plugin template*](../../pydatalab/docs/tools-glossary.md#tool-plugin-template).

This is the in-repository *Copier* template for *datalab tool* plugins. It can
generate either:

- a standalone application that uses a short-lived *tool access token*; or
- a trusted *in-app tool* that renders inside datalab and uses the current
  *browser session* through the frontend SDK.

Generate a new plugin repository from the datalab checkout:

```shell
uvx copier copy templates/datalab-tool-plugin-template ../my-datalab-tool
```

The generated project includes the provider, Flask blueprint, package entry
point, and an example of the selected UI contract. In-app projects also include
a small Vite build that emits one classic JavaScript bundle and externalizes Vue
to datalab's host runtime. Either UI kind may open in the current tab or a new
tab.

For an in-app project, the template optionally declares one
*table-selection tool action*. The action can appear in the selected-items
dropdown of Samples, Inventory, Equipment, or items within a collection. When
this option is disabled, the generated provider and Vue component contain no
selection-specific code.

datalab automatically authenticates every route in the provider's declared
blueprint. Browser-session *authentication* is the default; service integrations
must declare service *authentication* and validate their machine client. The
starter UIs access user data through the normal datalab API, where existing
*item* and collection permission filters apply.

Both variants are trusted extensions. Deployment administrators must review the
generated Python package and its dependencies. For *in-app tools*, they must also
review the frontend source, dependency lockfile, and compiled JavaScript before
installing or upgrading the plugin. For separately hosted *standalone tools*,
they must additionally trust the remote operator, backend, *tool access token*
destination, and data retention and deletion policies.
