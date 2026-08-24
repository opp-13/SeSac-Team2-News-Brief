#!/bin/bash
set -euxo pipefail

# Full nginx.conf overwrite (not a conf.d snippet) -- the dnf-installed
# nginx package's default config already defines an inline `server {
# default_server }` block in nginx.conf itself, so a separate conf.d file
# would collide with it. Owning the whole file here keeps this idempotent
# and self-contained, same as the systemd unit in the backend's start.sh.
#
# api.team2.local is the internal NLB's private DNS alias
# (infra/modules/network/dns.tf) -- requires enable_private_dns = true.
sudo tee /etc/nginx/nginx.conf > /dev/null <<'EOF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

http {
    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                       '$status $body_bytes_sent "$http_referer" '
                       '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile            on;
    tcp_nopush          on;
    keepalive_timeout   65;
    types_hash_max_size 4096;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    server {
        listen       80 default_server;
        listen       [::]:80 default_server;
        server_name  _;
        root         /usr/share/nginx/html;

        # React Router client-side routing -- fall back to index.html for
        # any path that isn't a real static file.
        location / {
            try_files $uri $uri/ /index.html;
        }

        location /api/ {
            proxy_pass http://api.team2.local:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
EOF

# `restart` instead of `reload` -- install_web.sh installs nginx via dnf but
# doesn't guarantee it's enabled/running, so this can't assume an active
# service to reload. `restart` starts it if it's down and restarts it if not,
# so the deploy is self-contained either way.
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
