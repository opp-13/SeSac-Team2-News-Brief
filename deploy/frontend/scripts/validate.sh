#!/bin/bash
set -euxo pipefail

sleep 2   # give the container a moment to bind before checking
curl -fsS http://localhost/ > /dev/null
