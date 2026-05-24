# Generating the README hero image

The README references `docs/assets/hero.png`. The committed copy was
generated from the prompt below and cropped to a 1264 x 528 banner
(approx. 2.4:1). The original 1264 x 848 source image is also
checked in at
`docs/assets/A_wide_horizontal_hero_banner__2026-05-24T09-01-44.png`
so the hero can be re-cropped or re-styled without re-running the
generator. The prompt below is the source of truth: regenerate any
time, drop the result in at `docs/assets/hero.png`.

## Recommended: nano banana (Gemini 2.5 Flash Image) prompt

The prompt below is calibrated for a **wide hero banner (1536 x 640)**
that reads well at thumbnail size on a GitHub repo card and at full size
on the README. It is deliberately concrete (specific shapes, colours,
ratios) so the model does not drift.

> **Tip.** If you want the image to feel less "AI-generated", ask for a
> slightly desaturated palette and **no text** in the image, then add
> the title in the README itself. Image generators are notoriously bad
> at rendering long English text, and a clean visual + Markdown title
> beats a model that misspells "CleanTest" four different ways.

```text
A wide horizontal hero banner, 1536x640 pixels, for a software-engineering
open-source project called CleanTest-Agent. The visual metaphor is a
"data refinery" pipeline:

Left third: a chaotic stream of stylised code snippets and small
geometric shapes representing noisy unit-test samples (broken brackets,
question marks, red dots, fragmented annotation symbols like @ and #).
Show this as a turbulent flow with warm, slightly desaturated tones
(coral, terracotta, dusty orange) on a near-white background.

Centre: three vertical filter columns drawn as cylindrical or trapezoidal
funnels labelled subtly (no text inside the funnels themselves), each
catching some of the chaotic shapes as the flow passes through. The
funnels should look like industrial filters, not literal kitchen
strainers --- think clean engineering schematic style. Use cool teal /
slate blue for the filter bodies. A few minimalist linear icons on each
filter hint at its function: a tiny syntax-tree branching glyph on the
first, two interlinked nodes on the second, a small bar-chart-like
gauge on the third.

Right third: the same shapes, now neat and orderly, flowing out as a
clean dataset --- arrange them as a tidy grid of small green-tinted
tiles streaming rightward off the page. Add a single small green check
glyph far right.

Style: clean isometric or 3/4 perspective, flat illustration with subtle
depth, generous negative space, no photo-realism, no glow/neon, no
gradient backgrounds. Fine 1.5 px line weight, geometric shapes with
slightly rounded corners. Overall feel: a high-end developer-tool landing
page hero (think Linear, Vercel, Supabase aesthetic --- not generic AI
poster art). White or off-white (#FAFAFA) background, no border, the
illustration should bleed slightly off the right edge to suggest motion.

Absolutely no text or letterforms anywhere in the image. No logos. No
human figures. No watermarks. Output as a transparent-background or
white-background PNG.
```

### Negative prompt (if your tool supports it)

```text
text, words, letters, typography, watermark, logo, person, hand, face,
glow, neon, gradient sky, photorealistic, 3D render, cluttered, busy,
generic AI art, fantasy, sci-fi, cyberpunk
```

## Where to save the result

```bash
mkdir -p docs/assets
# Save the generated PNG as:
docs/assets/hero.png
```

The README references it as:

```markdown
<img src="docs/assets/hero.png" alt="CleanTest-Agent" width="720">
```

## Alternative: derive a hero from the LaTeX architecture diagram

If you would rather use a real diagram from the paper (cleaner academic
feel, works well for an academic-leaning README), export Figure 4 of the
report (the component diagram) to PNG:

```bash
cd report
# Crop just the page that contains the component diagram (page ~22):
pdftk main.pdf cat 22 output /tmp/component.pdf  # adjust page number
# Then convert to PNG at 300 DPI:
sips -s format png --resampleHeightWidth 1280 720 /tmp/component.pdf \
     --out docs/assets/hero.png
# (Or use ImageMagick: convert -density 300 /tmp/component.pdf docs/assets/hero.png)
```

That gives you a recognisable "this is the architecture diagram from the
paper" hero, which is friendlier to academic readers than abstract art
but less impressive on social-media link previews.

## Banner-bar alternative (no image at all)

If you skip the image entirely, a clean ASCII-art banner near the top of
the README also works. The repo already has one ready to drop in:

```text
   _____ _                 _____         _      _                    _   
  / ____| |               |_   _|       | |    | |                  | |  
 | |    | | ___  __ _ _ __  | |  ___ ___| |_   /_\  __ _  ___  _ __ | |_ 
 | |    | |/ _ \/ _` | '_ \ | | / _ / __| __| / _ \/ _` |/ _ \| '_ \| __|
 | |____| |  __/ (_| | | | || ||  __\__ \ |_ / ___ \ (_| |  __/| | | | |_ 
  \_____|_|\___|\__,_|_| |_|\_/ \___|___/\__//_/   \_\__, |\___|_| |_|\__|
                                                      __/ |
                                                     |___/
```

Put it inside an HTML `<pre>` block at the top of the README and it
renders fine on GitHub.
