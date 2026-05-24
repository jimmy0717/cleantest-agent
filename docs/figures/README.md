# Standalone figures

Standalone, paper-grade reproductions of the diagrams in `report/main.tex`.
Each `.tex` file in this directory builds to a single-figure PDF / PNG /
SVG that can be reused outside the report (slides, READMEs, social
posts) without re-rendering the whole 67-page manuscript.

## Available figures

| Figure | Source | Reproduces |
|---|---|---|
| `component-diagram.tex` | `report/main.tex` Section 6 (System Design) | "Component Diagram: Module Dependencies" -- UML 2.5.1 component diagram of the four skill components, the five core modules, and four external libraries. |

Each TeX source carries the same node coordinates, fills, and dependency
edges as the manuscript figure, so the standalone artefact is a faithful
extract rather than a re-drawing.

## Build

```bash
./build-figures.sh           # PDF + PNG, paper colour palette
./build-figures.sh --bw      # also emit a print-safe grayscale PDF + PNG
./build-figures.sh --svg     # also emit SVG (requires pdf2svg)
./build-figures.sh --all     # PDF + PNG + grayscale + SVG
```

Outputs land next to the source `.tex`. Auxiliary build files are
removed automatically.

## Requirements

| Tool | Purpose | Where to get it |
|---|---|---|
| `pdflatex` | TeX engine | TeX Live, MacTeX, BasicTeX |
| `pdftoppm` *or* `magick`/`convert` *or* `sips` (macOS) | PDF -> PNG | poppler / ImageMagick / built-in |
| `pdf2svg` (optional) | PDF -> SVG | `brew install pdf2svg` |
| `pdfcrop` (optional) | tighter bounding box | `tlmgr install pdfcrop` |

The TeX sources only depend on `tikz`, `lmodern`, `T1` font encoding,
and `geometry` -- all four ship with BasicTeX out of the box.

## Colour vs. grayscale

The default palette mirrors the report:

- **Skills** -- soft orange (`orange!10`), three nodes plus the
  orchestrator.
- **Core modules** -- soft blue (`blue!10`), five nodes.
- **External libraries** -- light grey (`gray!10`), four nodes,
  carrying the custom `<<library>>` stereotype.

The grayscale variant maps these to three distinguishable gray levels
(0.92 / 0.85 / 0.78) and is intended for camera-ready prints that
would otherwise lose the orange / blue contrast on a B&W laser
printer. Pass `\def\BW{1}` (the wrapper script does this with the
`--bw` flag) to produce the grayscale build.

## Notation

All diagrams follow UML 2.5.1 conventions:

- `<<component>>` is the standard UML 2.5.1 component stereotype
  (Section 11.6 of the UML 2.5.1 specification).
- `<<library>>` is a profile extension used to mark third-party
  binaries; it is declared inline in the figure caption of the
  manuscript and reused here for consistency.
- Dependency edges are dashed lines with open V-shaped stick
  arrowheads (UML 2.5.1 Section 7.8.4). They are *not* triangular,
  which would denote generalisation or realisation.

## Citing the figure

If you reuse a figure in a paper, slide deck, or blog post, the
canonical citation is the report itself:

> Yong Yang, "CleanTest-Agent: A Multi-Agent Skill-Orchestrated System
> for Unit Test Training Data Quality Assurance", 2026. Figure
> "Component Diagram: Module Dependencies", Section 6.
