#!/bin/bash
set -euxo pipefail

# `|| true` -- the first-ever deployment to a fresh instance won't have this
# unit yet (it's created by install_was.sh's systemd setup, not by this repo).
sudo systemctl stop newsbrief-backend || true
