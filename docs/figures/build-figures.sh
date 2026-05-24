#!/usr/bin/env bash
# Build the standalone TikZ figures into PDF / PNG / SVG.
#
# Usage:
#     ./build-figures.sh                    # PDF + PNG (300 dpi)
#     ./build-figures.sh --bw               # also emit a grayscale PDF
#     ./build-figures.sh --svg              # also emit SVG (needs pdf2svg)
#     ./build-figures.sh --all              # PDF + PNG + grayscale + SVG
#
# Requirements:
#     pdflatex (TeX Live)         - mandatory
#     ImageMagick `magick`/`convert` OR `pdftoppm`  - for PNG
#     pdf2svg                     - for SVG (optional)
set -euo pipefail

cd "$(dirname "$0")"

EMIT_BW=0
EMIT_SVG=0
case "${1:-}" in
    --bw)   EMIT_BW=1 ;;
    --svg)  EMIT_SVG=1 ;;
    --all)  EMIT_BW=1; EMIT_SVG=1 ;;
    "")     ;;
    *)      echo "Unknown flag: $1"; exit 2 ;;
esac

FIGURES=(component-diagram)

crop_pdf () {
    local base="$1"
    if command -v pdfcrop >/dev/null 2>&1; then
        pdfcrop --margins '6 6 6 6' "${base}.pdf" "${base}.pdf" \
            > "${base}.crop.log" 2>&1 || true
    fi
}

emit_png () {
    local base="$1"
    if command -v pdftoppm >/dev/null 2>&1; then
        pdftoppm -r 300 -png "${base}.pdf" "${base}"
        # pdftoppm appends "-1" for single-page docs; normalise.
        [ -f "${base}-1.png" ] && mv -f "${base}-1.png" "${base}.png"
    elif command -v magick >/dev/null 2>&1; then
        magick -density 300 "${base}.pdf" -quality 95 "${base}.png"
    elif command -v convert >/dev/null 2>&1; then
        convert -density 300 "${base}.pdf" -quality 95 "${base}.png"
    elif command -v sips >/dev/null 2>&1; then
        # macOS native fallback: sips renders at 144 dpi by default; we
        # ask for 1600 px on the long edge which is roughly equivalent
        # for a paper-sized figure (~5x letter inches).
        sips -s format png --resampleHeightWidthMax 1600 \
            "${base}.pdf" --out "${base}.png" >/dev/null 2>&1
    else
        echo "  [warn] no pdftoppm / ImageMagick / sips found, skipping PNG for ${base}"
    fi
}

emit_svg () {
    local base="$1"
    if command -v pdf2svg >/dev/null 2>&1; then
        pdf2svg "${base}.pdf" "${base}.svg"
    else
        echo "  [warn] pdf2svg not installed, skipping SVG for ${base}"
    fi
}

for fig in "${FIGURES[@]}"; do
    echo "==> ${fig}.tex"
    pdflatex -interaction=nonstopmode -halt-on-error "${fig}.tex" \
        > "${fig}.build.log" 2>&1 || { tail -40 "${fig}.build.log"; exit 1; }
    crop_pdf "${fig}"
    emit_png "${fig}"
    [ "$EMIT_SVG" -eq 1 ] && emit_svg "${fig}"

    if [ "$EMIT_BW" -eq 1 ]; then
        echo "==> ${fig}.tex (grayscale)"
        pdflatex -interaction=nonstopmode -halt-on-error \
            -jobname "${fig}-bw" \
            "\def\BW{1}\input{${fig}.tex}" \
            > "${fig}-bw.build.log" 2>&1 || { tail -40 "${fig}-bw.build.log"; exit 1; }
        crop_pdf "${fig}-bw"
        emit_png "${fig}-bw"
        [ "$EMIT_SVG" -eq 1 ] && emit_svg "${fig}-bw"
    fi
done

# Tidy up auxiliary files; keep the artefacts.
rm -f -- *.aux *.log *.out *.fls *.fdb_latexmk *.build.log *.crop.log

echo "Done. Artefacts:"
ls -1 -- *.pdf *.png *.svg 2>/dev/null | sed 's/^/  /'
