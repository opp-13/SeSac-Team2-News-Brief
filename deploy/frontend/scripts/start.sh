#!/bin/bash
set -euxo pipefail

IMAGE=$(cat /home/ec2-user/frontend-deploy/image.txt)
sudo docker pull "$IMAGE"
sudo docker run -d --name frontend --restart unless-stopped -p 80:80 "$IMAGE"
