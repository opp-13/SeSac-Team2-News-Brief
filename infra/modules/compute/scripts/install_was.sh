#!/bin/bash
set -euxo pipefail


## CodeDeploy Agnet INSTALL

sudo yum update
sudo yum install wget -y

## 기존 code deploy agent 삭제, 아마 필요 없을  듯
# `|| true` -- 새 인스턴스엔 이 바이너리가 애초에 없어서 "No such file or
# directory"로 실패하고, set -e 때문에 여기서 스크립트 전체가 죽어서
# 그 아래 wget/install이 실행조차 안 됐었다.
CODEDEPLOY_BIN="/opt/codedeploy-agent/bin/codedeploy-agent"
$CODEDEPLOY_BIN stop || true
yum erase codedeploy-agent -y || true

cd /home/ec2-user
wget https://aws-codedeploy-ap-northeast-2.s3.ap-northeast-2.amazonaws.com/latestv2/install
chmod +x ./install
sudo ./install auto
systemctl enable --now codedeploy-agent


## ELSE

sudo dnf update -y

sudo dnf install -y python3.14

python3 --version

sudo dnf install -y git
git --version

curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version

echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
uv --version