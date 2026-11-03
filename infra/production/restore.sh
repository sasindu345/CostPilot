#!/bin/bash
# Restores a backup made by backup.sh. Run it from the folder with the Compose file.
#
# Usage:
#   restore.sh check <backup>     Restores into spare copies, compares row counts, then drops the copies.
#                                 The live data is not touched.
#   restore.sh replace <backup>   Replaces the live databases. The app is stopped while this runs.
#
# <backup> is a local folder, an s3:// folder, or "latest" for the newest backup in S3.
set -euo pipefail

mode=${1:?Usage: restore.sh check|replace <backup>}
source=${2:?Usage: restore.sh check|replace <backup>}
script_dir=$(dirname "$(readlink -f "$0")")

workdir=$(mktemp -d)
trap 'rm -rf "$workdir"' EXIT

if [[ $source == latest || $source == s3://* ]]; then
  set -a
  # shellcheck source=/dev/null
  . ./.env
  set +a
  if [ "$source" = latest ]; then
    newest=$(aws s3 ls "s3://$S3_BUCKET/backups/" | awk '{print $2}' | sort | tail -n 1)
    [ -n "$newest" ] || { echo "No backups found in s3://$S3_BUCKET/backups/" >&2; exit 1; }
    source="s3://$S3_BUCKET/backups/${newest%/}"
  fi
  aws s3 cp --recursive --only-show-errors "$source" "$workdir"
else
  cp "$source"/* "$workdir/"
fi
echo "Restoring from $source"

# Runs a Postgres tool as the admin user. "app" means the database named in POSTGRES_DB.
as_admin() {
  docker compose exec -T postgres sh -c '
    database=$1
    shift
    [ "$database" = app ] && database=$POSTGRES_DB
    "$@" --username "$POSTGRES_USER" --dbname "$database"
  ' _ "$@"
}

# The real name of a database: "app" becomes POSTGRES_DB.
real_name() {
  docker compose exec -T postgres sh -c '[ "$1" = app ] && echo "$POSTGRES_DB" || echo "$1"' _ "$1"
}

restore_into() {
  local database=$1 target=$2 owner
  owner=$(as_admin "$database" psql --quiet --no-align --tuples-only \
    --command "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = current_database()")
  docker compose exec -T postgres sh -c 'dropdb --username "$POSTGRES_USER" --if-exists "$1"' _ "$target"
  docker compose exec -T postgres sh -c \
    'createdb --username "$POSTGRES_USER" --owner "$1" "$2"' _ "$owner" "$target"
  docker compose exec -T postgres sh -c \
    'pg_restore --username "$POSTGRES_USER" --dbname "$1" --exit-on-error' _ "$target" \
    <"$workdir/$database.dump"
}

case $mode in
  check)
    for database in app keycloak; do
      copy="$(real_name "$database")_restore_check"
      restore_into "$database" "$copy"
      as_admin "$copy" psql --quiet --no-align --tuples-only \
        <"$script_dir/table-counts.sql" >"$workdir/$database.restored"
      docker compose exec -T postgres sh -c 'dropdb --username "$POSTGRES_USER" "$1"' _ "$copy"
      if ! diff -u "$workdir/$database.counts" "$workdir/$database.restored"; then
        echo "Restore check FAILED for $database: row counts differ." >&2
        exit 1
      fi
      tables=$(wc -l <"$workdir/$database.counts" | tr -d ' ')
      rows=$(awk -F'|' '{sum += $2} END {print sum + 0}' "$workdir/$database.counts")
      echo "Restore check passed for $database: $tables tables, $rows rows"
    done
    ;;
  replace)
    echo "This replaces the live databases with the backup. Type 'replace' to go on."
    read -r answer
    [ "$answer" = replace ] || { echo "Stopped. Nothing changed."; exit 1; }
    docker compose stop api worker keycloak
    for database in app keycloak; do
      restore_into "$database" "$(real_name "$database")"
    done
    docker compose up --detach --wait
    echo "Restore finished"
    ;;
  *)
    echo "Unknown mode: $mode. Use check or replace." >&2
    exit 1
    ;;
esac
