#!/usr/bin/env bash
set -e

# TODO для создания баз прописать свой вариант
export VARIANT="v4"
export SCRIPT_PATH=/docker-entrypoint-initdb.d/
export PGPASSWORD=postgres
psql -f "$SCRIPT_PATH/scripts/db-$VARIANT.sql"

psql -f "$SCRIPT_PATH/scripts/seed-v4-libraries.sql"
psql -f "$SCRIPT_PATH/scripts/seed-v4-ratings.sql"