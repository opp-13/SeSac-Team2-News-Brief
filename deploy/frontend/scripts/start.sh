#!/bin/bash
set -euxo pipefail

# `restart` instead of `reload` -- install_web.sh installs nginx via dnf but
# doesn't guarantee it's enabled/running, so this can't assume an active
# service to reload. `restart` starts it if it's down and restarts it if not,
# so the deploy is self-contained either way.
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
