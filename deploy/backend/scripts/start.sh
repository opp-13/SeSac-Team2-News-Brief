#!/bin/bash
set -euxo pipefail

# Assumes install_was.sh has already installed uv for ec2-user and created a
# `newsbrief-backend.service` unit that runs
# `/home/ec2-user/backend/.venv/bin/uvicorn app.main:app ...` -- reconcile the
# unit name/paths here with whatever install_was.sh actually sets up.
sudo -u ec2-user bash -c '
  cd /home/ec2-user/backend
  export PATH="$HOME/.local/bin:$PATH"
  uv sync --frozen
'

sudo systemctl daemon-reload
sudo systemctl restart newsbrief-backend
