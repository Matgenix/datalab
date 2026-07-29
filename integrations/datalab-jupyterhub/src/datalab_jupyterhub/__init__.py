"""JupyterHub integration for datalab Tools."""

from .authenticator import DatalabAuthenticator

__all__ = ("DatalabAuthenticator",)


def _jupyter_server_extension_points() -> list[dict[str, str]]:
    """Expose the new-notebook banner as a Jupyter Server extension."""

    return [{"module": "datalab_jupyterhub.notebooks"}]
