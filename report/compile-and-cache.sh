#!/usr/bin/env bash
# =============================================================================
# compile-and-cache.sh
# -----------------------------------------------------------------------------
# Local pdflatex build script for main.tex .
#
# History:
#   v1: tried tikz `external` library to cache rendered figures into
#       tikz-cache/ for Overleaf upload, but the document contains an
#       lstlisting block with Chinese characters (~ line 3273), which
#       crashes the external subprocess (Invalid UTF-8 byte sequence).
#       Reverted to direct in-document TikZ rendering --- works on both
#       local pdflatex and Overleaf without external caching.
#
# This script:
#   1. Sanity-checks the local TeX toolchain.
#   2. Compiles main.tex with -shell-escape (still useful for some packages).
#   3. Summarises overfull \hbox warnings (visually-significant ones, >= 10 pt).
#   4. Lists outstanding LaTeX warnings worth attention.
#
# Run from any directory; the script cd's into the report/ folder by itself.
# =============================================================================

set -euo pipefail

# ---- Resolve the report directory regardless of where this script is run from
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---- Try to make BasicTeX visible if a fresh shell didn't pick up PATH yet
if ! command -v pdflatex >/dev/null 2>&1; then
    if [ -x /usr/libexec/path_helper ]; then
        eval "$(/usr/libexec/path_helper -s)"
    fi
    # Common BasicTeX/MacTeX install location
    if [ -d /Library/TeX/texbin ]; then
        export PATH="/Library/TeX/texbin:$PATH"
    fi
fi

echo "============================================================"
echo " Step 0 / 4 :  Toolchain sanity check"
echo "============================================================"
missing=0
for cmd in pdflatex latexmk; do
    if command -v "$cmd" >/dev/null 2>&1; then
        echo "  OK   $cmd  ->  $(command -v "$cmd")"
    else
        echo "  FAIL $cmd  ->  not found"
        missing=$((missing + 1))
    fi
done
if [ "$missing" -gt 0 ]; then
    echo ""
    echo "ERROR: TeX toolchain not found. Install BasicTeX first:"
    echo "    brew install --cask basictex"
    echo "    eval \"\$(/usr/libexec/path_helper)\""
    echo "    sudo tlmgr update --self"
    echo "    sudo tlmgr install acmart hyperxmp xkeyval bookmark \\"
    echo "                       multirow algorithm cm-super"
    exit 1
fi
echo ""

echo "============================================================"
echo " Step 1 / 4 :  Clean previous artefacts"
echo "============================================================"
# Remove main.* aux files so the next compile is clean.
rm -f main.aux main.log main.out main.toc main.fls main.fdb_latexmk \
      main.synctex.gz main.bbl main.blg main.bcf main.run.xml \
      main.auxlock
# Remove leftover tikz external droppings from the v1 attempt (if any).
find . -maxdepth 1 -name "main-figure*" -delete 2>/dev/null || true
echo "  cleaned"
echo ""

echo "============================================================"
echo " Step 2 / 4 :  Compile main.tex"
echo "============================================================"
echo "  Expected: 30--45 s (rule-of-thumb: 6 TikZ figures + 46 listings)"
echo ""
# -pdf            : produce PDF
# -shell-escape   : kept on as a courtesy for any package that wants it
# -interaction=nonstopmode : don't pause on errors
# -file-line-error: print errors as file:line: message (machine-readable)
# -bibtex         : main.tex uses classic \bibliographystyle / \bibliography
# -f              : keep going past undefined citation/reference warnings
#                   on the first 1-2 passes; latexmk re-runs pdflatex after
#                   bibtex resolves them. Without -f, latexmk treats the
#                   first pdflatex's exit code 1 as fatal.
latexmk -pdf -shell-escape \
        -interaction=nonstopmode \
        -file-line-error \
        -bibtex \
        -f \
        main.tex || true   # judge success by main.pdf existence, not exit code

if [ -f main.pdf ]; then
    pages=$(grep -oE "Output written on main\\.pdf \\([0-9]+ pages" main.log 2>/dev/null | grep -oE "[0-9]+" | head -1)
    pages="${pages:-???}"
    echo ""
    echo "  Compilation: SUCCESS  ($(du -h main.pdf | cut -f1), $pages pages)"
else
    echo ""
    echo "  Compilation: FAILED --- main.pdf was not produced"
    echo "  Inspect main.log:"
    tail -40 main.log
    exit 1
fi
echo ""

echo "============================================================"
echo " Step 3 / 4 :  Overfull \\hbox warnings"
echo "============================================================"
if grep -qE "Overfull \\\\hbox" main.log 2>/dev/null; then
    total=$(grep -cE "Overfull \\\\hbox" main.log)
    echo "  Total overfull \\hbox: $total"
    echo ""
    echo "  Visually significant (>= 10.0 pt --- ~3.5mm, you'll see them):"
    sig=$(grep -nE "Overfull \\\\hbox \\([0-9]{2,}\\." main.log || true)
    if [ -n "$sig" ]; then
        echo "$sig" | sed 's/^/    /'
    else
        echo "    (none)"
    fi
    echo ""
    echo "  Minor (< 10 pt --- not worth chasing unless you want perfection):"
    minor=$(grep -nE "Overfull \\\\hbox \\([0-9]\\." main.log || true)
    if [ -n "$minor" ]; then
        echo "$minor" | sed 's/^/    /' | head -10
        nm=$(echo "$minor" | wc -l | tr -d ' ')
        if [ "$nm" -gt 10 ]; then
            echo "    ... and $((nm - 10)) more"
        fi
    else
        echo "    (none)"
    fi
else
    echo "  No overfull \\hbox warnings."
fi
echo ""

echo "============================================================"
echo " Step 4 / 4 :  Other warnings worth checking"
echo "============================================================"
warn=$(grep -nE "LaTeX Warning|Undefined" main.log 2>/dev/null | \
       grep -vE "Citation .* on page|Reference .* on page" | head -20 || true)
if [ -n "$warn" ]; then
    echo "$warn" | sed 's/^/    /'
else
    echo "  (none worth chasing)"
fi
echo ""

# Float-too-large is its own category --- usually a wide table or figure
# that doesn't fit any page. Worth showing separately.
echo "  Float too large for page (manual check needed):"
ftl=$(grep -nE "Float too large" main.log 2>/dev/null || true)
if [ -n "$ftl" ]; then
    echo "$ftl" | sed 's/^/    /'
else
    echo "    (none)"
fi
echo ""

echo "============================================================"
echo " Done"
echo "============================================================"
echo "  PDF: $(pwd)/main.pdf"
echo ""
echo "  To inspect overfull lines, e.g. 'lines 800--811', open main.tex"
echo "  at that range and check whether a long word, URL, or \\texttt{}"
echo "  needs an \\allowbreak or hyphenation hint."
echo ""
