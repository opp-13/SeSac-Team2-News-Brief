#!/bin/bash
set -euxo pipefail

# requirements.txt is the dependency source of truth (backend/pyproject.toml
# carries no [project.dependencies] section on purpose -- see its header
# comment), so this is a plain venv + pip install, not uv.
sudo dnf install -y python3.14

sudo chown -R ec2-user:ec2-user /home/ec2-user/backend

sudo -u ec2-user bash -c '
  cd /home/ec2-user/backend
  python3.14 -m venv .venv
  .venv/bin/pip install -r requirements.txt
'

# No systemd unit is guaranteed to exist -- this repo's install_was.sh
# doesn't register one for the real backend (it's still bootstrapping a
# placeholder app). The deploy script owns creating/updating the unit itself
# so a deployment works regardless of what the instance bootstrap set up.
sudo tee /etc/systemd/system/newsbrief-backend.service > /dev/null <<'EOF'
[Unit]
Description=NewsBrief FastAPI backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/backend
ExecStart=/home/ec2-user/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable newsbrief-backend
sudo systemctl restart newsbrief-backend
