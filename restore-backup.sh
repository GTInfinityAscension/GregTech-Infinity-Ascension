#!/usr/bin/env bash
# Restores a world from an FTB Backups 2 backup (the backups/ folder of this instance or server).
#
# Usage: close Minecraft (or stop the server), then run from this folder:
#   ./restore-backup.sh            pick a backup from a list
#   ./restore-backup.sh FILE.zip   restore that backup
#
# The current copy of the world is never deleted: it is renamed to "<world>.before-restore-<date>".
set -euo pipefail

cd "$(dirname "$0")"
BACKUPS=backups

die() { echo "Error: $*" >&2; exit 1; }

[ -d "$BACKUPS" ] || die "no '$BACKUPS' folder here. Run this script from the instance (.minecraft) or server folder."

unzip_to() { # zip, destination
    if command -v unzip >/dev/null; then unzip -q "$1" -d "$2"
    elif command -v bsdtar >/dev/null; then bsdtar -xf "$1" -C "$2"
    elif command -v python3 >/dev/null; then python3 -m zipfile -e "$1" "$2"
    else die "install 'unzip' (or bsdtar or python3) to extract the backup."; fi
}

sha1_of() {
    if command -v sha1sum >/dev/null; then sha1sum "$1" | cut -d' ' -f1
    elif command -v shasum >/dev/null; then shasum -a 1 "$1" | cut -d' ' -f1
    fi
}

# Expected SHA-1 recorded by FTB Backups in backups.json (empty when unknown).
recorded_sha1() {
    [ -f "$BACKUPS/backups.json" ] || return 0
    local name; name=$(basename "$1")
    tr -d '\n' < "$BACKUPS/backups.json" | grep -o "{[^{}]*${name//./\\.}[^{}]*}" \
        | grep -o '"sha1": *"[0-9a-f]*"' | grep -o '[0-9a-f]\{40\}' | head -n1 || true
}

if [ $# -ge 1 ]; then
    ZIP=$1
else
    mapfile -t ZIPS < <(ls -1t "$BACKUPS"/*.zip 2>/dev/null || true)
    [ ${#ZIPS[@]} -gt 0 ] || die "no backups (.zip) in '$BACKUPS'."
    echo "Backups, newest first:"
    for i in "${!ZIPS[@]}"; do
        size=$(du -h "${ZIPS[$i]}" | cut -f1)
        printf '  %2d) %s  (%s)\n' $((i + 1)) "$(basename "${ZIPS[$i]}")" "$size"
    done
    read -rp "Number of the backup to restore (empty to cancel): " pick
    [ -n "$pick" ] || exit 0
    [[ "$pick" =~ ^[0-9]+$ ]] && [ "$pick" -ge 1 ] && [ "$pick" -le ${#ZIPS[@]} ] || die "invalid choice."
    ZIP=${ZIPS[$((pick - 1))]}
fi
[ -f "$ZIP" ] || die "file not found: $ZIP"

expected=$(recorded_sha1 "$ZIP")
if [ -n "$expected" ]; then
    actual=$(sha1_of "$ZIP")
    if [ -n "$actual" ] && [ "$actual" != "$expected" ]; then
        die "the backup is damaged (SHA-1 differs from backups.json)."
    fi
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
unzip_to "$ZIP" "$TMP"

# Client backups contain saves/<world>/, server backups contain <world>/.
LEVEL=$(find "$TMP" -maxdepth 3 -name level.dat -print -quit)
[ -n "$LEVEL" ] || die "this backup has no level.dat; it is not a world backup."
SRC=$(dirname "$LEVEL")
WORLD=$(basename "$SRC")
if [ "$(basename "$(dirname "$SRC")")" = saves ] || [ -d saves ]; then
    DEST="saves/$WORLD"
else
    DEST="$WORLD"
fi

echo
echo "Backup: $(basename "$ZIP")"
echo "World:  $DEST"
echo "Make sure Minecraft (or the server) is closed."
read -rp "Restore? The current world will be kept as a renamed copy. [y/N] " ok
[[ "$ok" =~ ^[yYsS] ]] || exit 0

if [ -e "$DEST" ]; then
    KEEP="$DEST.before-restore-$(date +%Y-%m-%d_%H-%M-%S)"
    mv "$DEST" "$KEEP"
    echo "Current world kept as: $KEEP"
fi
mkdir -p "$(dirname "$DEST")"
mv "$SRC" "$DEST"
echo "Done. '$WORLD' was restored from $(basename "$ZIP")."
