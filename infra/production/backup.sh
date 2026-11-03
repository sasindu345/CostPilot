#!/bin/bash
# Backs up both databases: the app's and Keycloak's.
# Bill files are already in S3, and Qdrant can be rebuilt with `make reindex`.
#
# Usage, from the folder with the Compose file:
#   backup.sh                  to s3://$S3_BUCKET/backups, encrypted by S3
#   backup.sh <local-folder>   to a folder, used by `make backup-check`
set -euo pipefail

if [ $# -ge 1 ]; then
  destination=$1
else
  set -a
  # shellcheck source=/dev/null
  . ./.env
  set +a
  destination="s3://$S3_BUCKET/backups"
fi

stamp=$(date -u +%Y-%m-%dT%H%M%SZ)
workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

script_dir=$(dirname "$(readlink -f "$0")")

# "app" means the database named in POSTGRES_DB inside the container.
in_database() {
  local database=$1
  shift
  docker compose exec -T postgres sh -c '
    name=$1
    shift
    [ "$name" = app ] && name=$POSTGRES_DB
    "$@" --username "$POSTGRES_USER" --dbname "$name"
  ' _ "$database" "$@"
}

for database in app keycloak; do
  in_database "$database" pg_dump --format custom >"$workdir/$database.dump"
  # Row counts let restore.sh prove the backup restores in full.
  in_database "$database" psql --quiet --no-align --tuples-only \
    <"$script_dir/table-counts.sql" >"$workdir/$database.counts"
done

if [[ $destination == s3://* ]]; then
  aws s3 cp --recursive --only-show-errors --sse AES256 "$workdir" "$destination/$stamp"
else
  mkdir -p "$destination/$stamp"
  cp "$workdir"/* "$destination/$stamp/"
fi
echo "Backup saved to $destination/$stamp"
