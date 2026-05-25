# syntax=docker/dockerfile:1.6
#
# Custom Odoo 19 image — prunes the bundled addons folder so only
# core (base/web/base_setup) + HR (and its hard dependencies) remain.
# Everything else (Sale, Purchase, Stock, Accounting, CRM, Website, MRP, …)
# is removed at build time, so users cannot install or even see those apps.
#

FROM odoo:19.0

LABEL maintainer="ZenCore DevOps <devops@zencore.local>"
LABEL org.opencontainers.image.title="odoo19-custom"
LABEL org.opencontainers.image.description="Odoo 19 limited to Core + HR + custom addons"

USER root

# --- Whitelist-prune Odoo's bundled addons --------------------------------------
COPY scripts/prune_addons.py /tmp/prune_addons.py

RUN python3 /tmp/prune_addons.py \
    && rm -f /tmp/prune_addons.py

# --- Ensure required runtime dirs exist with correct ownership -------------------
RUN mkdir -p /mnt/extra-addons /var/log/odoo \
    && chown -R odoo:odoo /mnt/extra-addons /var/log/odoo

# --- Install curl (used by the healthcheck) -------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

USER odoo

EXPOSE 8069 8072

# Keep the official Odoo image entrypoint (handles PASSWORD_FILE → CLI flags).
# Just override CMD to point to our config file.
CMD ["odoo", "-c", "/etc/odoo/odoo.conf"]
