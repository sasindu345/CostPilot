#!/bin/bash
# Starts a new version of CostPilot. GitHub Actions runs this on the server through AWS.
# Usage: deploy.sh <image-prefix> <image-tag> <parameter-path>
set -euo pipefail

image_prefix=$1
image_tag=$2
parameter_path=$3

release_dir=$(cd "$(dirname "$0")" && pwd)
base_dir=/opt/costpilot
keep_releases=3
cd "$release_dir"

# Ask the server which AWS region it is in.
token=$(curl -fsS -X PUT http://169.254.169.254/latest/api/token \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
AWS_REGION=$(curl -fsS -H "X-aws-ec2-metadata-token: $token" \
  http://169.254.169.254/latest/meta-data/placement/region)
export AWS_REGION

echo "Fetching settings"
./fetch-settings.sh "$parameter_path" .env
printf "IMAGE_PREFIX='%s'\nIMAGE_TAG='%s'\n" "$image_prefix" "$image_tag" >>.env

# GHCR needs a login while the repository is private. The token never goes in .env.
./fetch-settings.sh "$parameter_path/registry" "$base_dir/registry.env" 2>/dev/null || true
if [ -s "$base_dir/registry.env" ]; then
  (
    set -a
    # shellcheck source=/dev/null
    . "$base_dir/registry.env"
    echo "$GHCR_TOKEN" | docker login ghcr.io --username "$GHCR_USER" --password-stdin
  )
fi

echo "Starting version $image_tag"
docker compose pull --quiet
docker compose up --detach --wait --wait-timeout 600 --remove-orphans
ln -sfn "$release_dir" "$base_dir/current"

echo "Installing the nightly backup"
install -m 644 systemd/costpilot-backup.service systemd/costpilot-backup.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now costpilot-backup.timer

echo "Removing old versions"
docker image prune --all --force --filter "until=72h" >/dev/null
find "$base_dir/releases" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' |
  sort -rn | tail -n +$((keep_releases + 1)) | cut -d' ' -f2- | xargs -r rm -rf

echo "Memory use"
free -m
docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}'
