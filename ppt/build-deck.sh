#!/usr/bin/env bash
# Build the presentation deck from slides-marp.md into PDF + PPTX.
#
# Usage:
#   ./build-deck.sh                     # PDF + PPTX (default)
#   ./build-deck.sh --pdf-only          # PDF only
#   ./build-deck.sh --html              # also emit HTML preview
#
# Requirements:
#   node + npx (npx will pull @marp-team/marp-cli on demand)
#   Chrome / Chromium for PDF / PPTX conversion (bundled with marp-cli's
#   chromium-bidi by default; falls back to system Chrome via PUPPETEER_EXECUTABLE_PATH).
set -euo pipefail

cd "$(dirname "$0")"

SRC="slides-marp.md"
[ -f "$SRC" ] || { echo "Source not found: $SRC"; exit 1; }

EMIT_PDF=1
EMIT_PPTX=1
EMIT_HTML=0
case "${1:-}" in
    --pdf-only) EMIT_PPTX=0 ;;
    --pptx-only) EMIT_PDF=0 ;;
    --html)      EMIT_HTML=1 ;;
    "")          ;;
    *) echo "Unknown flag: $1"; exit 2 ;;
esac

# Use a pinned marp-cli version so the build is reproducible on any
# machine; bump the pin deliberately when upgrading.
MARP="npx --yes @marp-team/marp-cli@4.4.0"

if [ "$EMIT_PDF" -eq 1 ]; then
    echo "==> Building CleanTest-Agent.pdf"
    $MARP --pdf --allow-local-files --output CleanTest-Agent.pdf "$SRC"
fi

if [ "$EMIT_PPTX" -eq 1 ]; then
    echo "==> Building CleanTest-Agent.pptx"
    $MARP --pptx --allow-local-files --output CleanTest-Agent.pptx "$SRC"
fi

if [ "$EMIT_HTML" -eq 1 ]; then
    echo "==> Building CleanTest-Agent.html (preview)"
    $MARP --html --allow-local-files --output CleanTest-Agent.html "$SRC"
fi

echo
echo "Done. Artefacts:"
ls -lh CleanTest-Agent.* 2>/dev/null | awk '{print "  ", $9, "(", $5, ")"}'
