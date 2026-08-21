#!/bin/bash
set -euxo pipefail

# `|| true` -- the first-ever deployment to a fresh instance won't have this
# unit yet (start.sh creates it on first successful deploy).
sudo systemctl stop newsbrief-backend || true
