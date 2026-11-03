#!/bin/bash
# Run on your own computer. Copies a filled-in settings file into Parameter Store, encrypted.
# Usage: put-settings.sh <settings-file> [parameter-path]
# Lines starting with registry/ go into a separate folder that never reaches the app.
set -euo pipefail

file=${1:?Usage: put-settings.sh <settings-file> [parameter-path]}
parameter_path=${2:-/costpilot/prod}
count=0

while IFS= read -r line || [ -n "$line" ]; do
  [[ -z $line || $line == \#* ]] && continue
  key=${line%%=*}
  value=${line#*=}
  if [ -z "$value" ]; then
    echo "Skipped $key: it has no value."
    continue
  fi
  aws ssm put-parameter --name "$parameter_path/$key" --type SecureString \
    --value "$value" --overwrite --no-cli-pager >/dev/null
  count=$((count + 1))
done <"$file"

echo "Saved $count settings under $parameter_path"
