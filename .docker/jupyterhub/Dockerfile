FROM jupyterhub/jupyterhub:5.5.0

ARG DOCKERSPAWNER_VERSION=14.0.0
ARG IDLE_CULLER_VERSION=2.0.0
ARG JUPYTERLAB_VERSION=4.6.2

COPY integrations/datalab-jupyterhub /tmp/datalab-jupyterhub

RUN python3 -m pip install --no-cache-dir \
        "dockerspawner==${DOCKERSPAWNER_VERSION}" \
        "jupyterhub-idle-culler==${IDLE_CULLER_VERSION}" \
        "jupyterlab==${JUPYTERLAB_VERSION}" \
        /tmp/datalab-jupyterhub \
    && rm -rf /tmp/datalab-jupyterhub

COPY .docker/jupyterhub/jupyterlab-overrides.json \
    /srv/venv/share/jupyter/lab/settings/overrides.json

RUN if ! getent group 100 >/dev/null; then groupadd --gid 100 users; fi \
    && if ! id jovyan >/dev/null 2>&1 && ! getent passwd 1000 >/dev/null; then \
        useradd --uid 1000 --gid 100 --home-dir /home/jovyan --create-home --shell /bin/bash jovyan; \
    fi \
    && mkdir -p /home/jovyan/work /srv/jupyterhub \
    && chown -R 1000:100 /home/jovyan

COPY .docker/jupyterhub/jupyterhub_config.py /etc/jupyterhub/jupyterhub_config.py

EXPOSE 8000

CMD ["jupyterhub", "-f", "/etc/jupyterhub/jupyterhub_config.py"]
