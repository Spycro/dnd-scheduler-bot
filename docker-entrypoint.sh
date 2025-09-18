#!/bin/sh
set -eu

# ensure expected directories exist
for dir in /app /data; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
    fi
done

ensure_dir() {
    target="$1"
    expected_mode="$2"

    owner=$(stat -c %U "$target")
    group=$(stat -c %G "$target")
    if [ "$owner" != "bot" ] || [ "$group" != "bot" ]; then
        echo "[entrypoint] $target must be owned by bot:bot but is ${owner}:${group}." >&2
        echo "[entrypoint] Adjust the host volume ownership before starting the container." >&2
        exit 1
    fi

    current_mode=$(stat -c %a "$target")
    if [ "$current_mode" != "$expected_mode" ]; then
        chmod "$expected_mode" "$target"
    fi
}

ensure_dir /app 750
ensure_dir /data 700

exec "$@"
