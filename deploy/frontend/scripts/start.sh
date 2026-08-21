#!/bin/bash
set -euxo pipefail

sudo nginx -t
sudo systemctl reload nginx
