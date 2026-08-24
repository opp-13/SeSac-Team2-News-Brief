#!/bin/bash
set -euxo pipefail

IMAGE=$(cat /home/ec2-user/backend-deploy/image.txt)
sudo docker pull "$IMAGE"
sudo docker run -d --name backend --restart unless-stopped -p 8000:8000 \
  --env-file /home/ec2-user/backend-deploy/backend.env \
  "$IMAGE"
