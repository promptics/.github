"""Render the promptics.io hero animation as a self-contained animated SVG.

Text is converted to outlines (Inter from the site theme), so the SVG needs no
web font and looks the same wherever it is shown as an image, e.g. on GitHub.
The timeline mirrors the homepage script: line 1 is typed, line 2 slams in,
"Now what?" is typed and gets a yellow swipe, then the two-liner slams in.

usage: python make_hero_svg.py <dir with inter-latin-600/800.woff2> hero.svg  (needs fonttools, brotli)
"""
import random
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

FONTS, OUT = sys.argv[1], sys.argv[2]
INK, ACCENT, HERE, BG = "#13254D", "#51A6E5", "#FFE500", "#FFFFFF"
W, PAD = 1200, 64
random.seed(7)  # typing jitter like the site, but the same on every build


class Face:
    def __init__(self, weight):
        self.f = TTFont(f"{FONTS}/inter-latin-{weight}.woff2")
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upm = self.f["head"].unitsPerEm
        kern = {}
        gpos = self.f["GPOS"].table if "GPOS" in self.f else None
        if gpos:
            for lookup in gpos.LookupList.Lookup:
                if lookup.LookupType != 2:
                    continue
                for st in lookup.SubTable:
                    if st.Format != 1:
                        continue
                    cov = st.Coverage.glyphs
                    for i, ps in enumerate(st.PairSet):
                        for pvr in ps.PairValueRecord:
                            v = getattr(pvr.Value1, "XAdvance", 0) or 0
                            if v:
                                kern[(cov[i], pvr.SecondGlyph)] = v
        self.kern = kern

    def glyphs(self, text, size, tracking, x0, base):
        """Yield (char, path d, x, advance) for each character, laid out on one line."""
        s = size / self.upm
        x = x0
        prev = None
        for ch in text:
            name = self.cmap[ord(ch)]
            if prev:
                x += self.kern.get((prev, name), 0) * s
            pen = SVGPathPen(self.gs)
            self.gs[name].draw(TransformPen(pen, (s, 0, 0, -s, x, base)))
            adv = self.gs[name].width * s + tracking * size
            yield ch, pen.getCommands(), x, adv
            x += adv
            prev = name


def width(face, text, size, tracking):
    return sum(a for *_, a in face.glyphs(text, size, tracking, 0, 0))


h1 = Face(800)
sub = Face(600)
H1, H1_LH, H1_TR = 84, 84 * 0.98, -0.045
SUB, SUB_LH, SUB_TR = 30, 30 * 1.3, -0.02

out, css = [], []
t = 350  # ms, as on the site


def typed(face, text, size, tr, x, base, color, t):
    """Characters appear one by one; returns end time and caret steps."""
    carets = []
    for ch, d, gx, adv in face.glyphs(text, size, tr, x, base):
        if d:
            out.append(f'<path class="g" style="animation-delay:{t:.0f}ms" fill="{color}" d="{d}"/>')
        carets.append((t, gx + adv))
        t += 40 if ch == " " else 38 + random.random() * 55
    return t, carets


def caret(steps, base, size, until):
    """A caret that sits after the last typed character, one rect per step."""
    for i, (start, cx) in enumerate(steps):
        end = steps[i + 1][0] if i + 1 < len(steps) else until
        out.append(
            f'<rect class="c" style="animation-delay:{start:.0f}ms;animation-duration:{max(end - start, 1):.0f}ms" '
            f'x="{cx + .03 * size:.1f}" y="{base - .78 * size:.1f}" width="{.07 * size:.1f}" height="{.82 * size:.1f}" fill="{INK}"/>'
        )


def slam_words(face, words_xy, size, tr, base, color, start, cls):
    for word, x in words_xy:
        paths = "".join(f'<path d="{d}"/>' for _, d, *_ in face.glyphs(word, size, tr, x, base) if d)
        out.append(f'<g class="{cls}" style="animation-delay:{start:.0f}ms" fill="{color}">{paths}</g>')


y1 = PAD + H1 * 0.78
y2 = y1 + H1_LH
y3 = y2 + H1_LH

out.append('<g class="h1">')
# line 1, typed
t_end1, c1 = typed(h1, "The bottleneck moved!", H1, H1_TR, PAD, y1, INK, t)
caret(c1, y1, H1, t_end1 + 280)
# lines 2 and 3a slam in word by word, all at once, then the headline jolts
t_slam = t_end1 + 280
space = width(h1, " ", H1, H1_TR)
x = PAD
words2 = []
for w in "You've automated your".split(" "):
    words2.append((w, x))
    x += width(h1, w, H1, H1_TR) + space
slam_words(h1, words2, H1, H1_TR, y2, ACCENT, t_slam, "s")
slam_words(h1, [("workflow.", PAD)], H1, H1_TR, y3, ACCENT, t_slam, "s")
css.append(f".h1{{animation:jolt .28s ease-out {t_slam + 220:.0f}ms}}")
# "Now what?" typed on a yellow swipe
x_now = PAD + width(h1, "workflow.", H1, H1_TR) + space
w_now = width(h1, "Now what?", H1, H1_TR)
t_now = t_slam + 650
# the swipe starts after typing, so draw the rect first (behind the glyphs)
rect_at = len(out)
t_end3, c3 = typed(h1, "Now what?", H1, H1_TR, x_now, y3, INK, t_now)
t_swipe = t_end3 + 160
out.insert(
    rect_at,
    f'<rect class="hl" style="animation-delay:{t_swipe:.0f}ms" x="{x_now - .06 * H1:.1f}" y="{y3 - .40 * H1:.1f}" '
    f'width="{w_now + .12 * H1:.1f}" height="{.47 * H1:.1f}" fill="{HERE}"/>',
)
caret(c3, y3, H1, t_swipe + 900)
out.append("</g>")

# the two-liner, after a moment to read the headline
t_sub = t_swipe + 900
ys1 = y3 + H1 * 0.22 + 28 + SUB * 1.05
ys2 = ys1 + SUB_LH
out.append('<g class="sub">')
for i, (line, ys) in enumerate((("We help you build software faster, with control.", ys1),
                                 ("And we clear the bottlenecks that come with it.", ys2))):
    slam_words(sub, [(line, PAD)], SUB, SUB_TR, ys, INK, t_sub + i * 520, "s2")
    css.append(f".sub{{animation:jolt .28s ease-out {t_sub + 220:.0f}ms}}") if i == 0 else None
out.append("</g>")

H = round(ys2 + SUB * 0.3 + PAD)
style = f"""
.g{{opacity:0;animation:on 1ms linear forwards}}
.c{{opacity:0;animation-name:blip;animation-timing-function:step-end}}
.s,.s2{{opacity:0;transform-box:fill-box;transform-origin:center;animation:slam .5s cubic-bezier(.2,1.5,.4,1) forwards}}
.s2{{animation-name:slam2}}
.hl{{transform-box:fill-box;transform-origin:left;transform:scaleX(0);animation:swipe .26s cubic-bezier(.8,0,.2,1) forwards}}
{chr(10).join(css)}
@keyframes on{{to{{opacity:1}}}}
@keyframes blip{{0%{{opacity:1}}100%{{opacity:0}}}}
@keyframes slam{{0%{{opacity:0;transform:translateY({-.7*H1:.0f}px) scale(1.06)}}55%{{opacity:1;transform:translateY({.06*H1:.0f}px) scale(.99)}}100%{{opacity:1;transform:none}}}}
@keyframes slam2{{0%{{opacity:0;transform:translateY({-.7*SUB:.0f}px) scale(1.06)}}55%{{opacity:1;transform:translateY({.06*SUB:.0f}px) scale(.99)}}100%{{opacity:1;transform:none}}}}
@keyframes jolt{{0%,100%{{transform:none}}30%{{transform:translate(-3px,2px)}}60%{{transform:translate(2px,-1px)}}}}
@keyframes swipe{{to{{transform:scaleX(1)}}}}
@media (prefers-reduced-motion:reduce){{.g,.s,.s2{{opacity:1;animation:none}}.hl{{transform:none;animation:none}}.c{{display:none}}.h1,.sub{{animation:none}}}}
"""
svg = (
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
    f'aria-label="The bottleneck moved! You\'ve automated your workflow. Now what? We help you build software faster, '
    f'with control. And we clear the bottlenecks that come with it.">'
    f"<style>{style}</style>"
    f'<rect width="{W}" height="{H}" rx="24" fill="{BG}"/>'
    + "".join(out)
    + "</svg>"
)
open(OUT, "w").write(svg)
print(f"{OUT}: {W}x{H}, {len(svg) // 1024} KB, swipe at {t_swipe:.0f} ms, two-liner at {t_sub:.0f} ms")
