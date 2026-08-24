#!/bin/bash
set -euxo pipefail

# `|| true` -- the first-ever deployment to a fresh instance won't have this
# container yet.
sudo docker stop backend || true
sudo docker rm backend || true
