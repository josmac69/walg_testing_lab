#!/bin/bash
set -e

# Run the wal-g exporter daemon in the background as postgres
gosu postgres python3 /usr/local/bin/walg_exporter.py &

# Exec the standard postgres docker entrypoint script
exec docker-entrypoint.sh "$@"
