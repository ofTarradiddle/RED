#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m publishing.build
exec python3 serve.py "$@"
