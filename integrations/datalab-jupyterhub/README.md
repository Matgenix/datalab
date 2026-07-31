# datalab-jupyterhub

The *datalab JupyterHub integration* connects an independently managed
*JupyterHub* to the datalab
**Tools** launch flow. It is also installed in the Compose-managed image.

Configure *JupyterHub* with:

```python
from datalab_jupyterhub import DatalabAuthenticator

c.JupyterHub.authenticator_class = DatalabAuthenticator
c.DatalabAuthenticator.api_url = "https://api.example.org"
c.DatalabAuthenticator.client_id = "jupyterhub"
c.DatalabAuthenticator.client_secret = "<deployment secret>"
c.DatalabAuthenticator.enable_auth_state = True
c.DatalabAuthenticator.allow_all = True
c.DatalabAuthenticator.auto_login = True
```

Set `JUPYTERHUB_CRYPT_KEY` to a persistent 32-byte hex-encoded key. The
authenticator exchanges `datalab_launch_code` at
`POST /v0.1/tools/plugins/jupyter/exchange` using HTTP Basic client
credentials. It stores the returned *tool access token* in encrypted *Hub*
`auth_state` and injects it into only that user's server.

The external deployment owns its spawner, per-user storage, resource limits,
culling, proxy, TLS, and single-user image. Install `datalab-api` in that image
and use `datalab-jupyter-singleuser` as the spawner command to install the
*IPython startup file* and create the first-login welcome notebook before starting
`jupyterhub-singleuser`. Keep each server's lifetime within the
*delegated tool session lifetime*.

Every Python kernel preloads `datalab`, an authenticated `DatalabClient`, and
`current_user`, the launch-time *current-user snapshot*. A *kernel banner*
advertises those names in a Jupyter console. The package also enables a
Jupyter Server *notebook save hook* that adds a *new-notebook banner* to blank
notebooks when they are first created. At startup, the integration installs the
banner HTML at
`~/.local/share/datalab-jupyterhub/banner.html`; the hook copies that template
into a non-editable but deletable Markdown cell. Existing and imported
notebooks are not modified. The banner includes a collapsed **Examples and
help** section with read-only client examples and a link to the complete Python
API reference.

The integration also handles the Jupyter **Open in notebook** table action.
After JupyterHub authenticates the user, it forwards a second short-lived,
single-use code to the authenticated user server. The server exchanges that
code using its delegated tool access token, creates a notebook with a dedicated
kernel, and executes its visible selected-items initialization cell once.

That cell defines `selected_item_refcodes`, `selected_items`, and
`selected_item_errors`. It remains in the notebook so the user can rerun it
after a kernel restart or a later reopening. Ordinary notebooks and consoles
do not receive these selection-specific variables.

The Compose-managed single-user image includes SciPy, pandas, Matplotlib,
seaborn, ipywidgets, lmfit, uncertainties, Pint, openpyxl, h5py, and tqdm.
External deployments choose and maintain their own analysis packages.

The Compose image also sets this JupyterLab default:

```json
{
  "@jupyterlab/notebook-extension:tracker": {
    "showEditorForReadOnlyMarkdown": false
  }
}
```

It keeps read-only Markdown cells rendered instead of exposing their editor.
Administrators of an external deployment should merge the same entry into the
JupyterLab application directory's `settings/overrides.json`.

The authenticator registers `/hub/datalab-login` below the configured *Hub* base
URL. datalab launches this handler directly so that every *launch code* is
exchanged even if the browser already has a *JupyterHub* login cookie.
