#!/bin/bash
# Writes the production settings from Parameter Store into a file only root can read.
# Usage: fetch-settings.sh <parameter-path> <output-file>
set -euo pipefail

parameter_path=$1
output=$2

umask 077
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT

aws ssm get-parameters-by-path --path "$parameter_path" --with-decryption \
  --query 'Parameters[].[Name,Value]' --output text |
  while IFS=$'\t' read -r name value; do
    if [[ $value == *"'"* ]]; then
      echo "Setting ${name##*/} contains a single quote, which .env files cannot hold." >&2
      exit 1
    fi
    # Single quotes stop Docker Compose from reading $ signs in passwords as variables.
    printf "%s='%s'\n" "${name##*/}" "$value"
  done >"$tmp"

if [ ! -s "$tmp" ]; then
  echo "No settings found under $parameter_path. See docs/guides/deployment.md." >&2
  exit 1
fi
mv "$tmp" "$output"
trap - EXIT
