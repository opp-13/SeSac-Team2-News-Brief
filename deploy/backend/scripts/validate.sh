#!/bin/bash
set -euxo pipefail

sleep 3   # give uvicorn a moment to bind before checking
curl -fsS http://localhost:8000/health > /dev/null
