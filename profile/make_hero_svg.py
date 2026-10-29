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


# the promptics.io logo (speech bubble and wordmark), drawn in its own 36 2 382 92 box
LOGO = f'''<path d="M102.7,8H52.2c-3.1,0-5.9,1.3-8,3.3c-3.2,3.2-3.3,7.2-3.3,8c0,12.5,0,25,0,37.5c0,0.7,0,1.4,0,2.1v32.3l18.3-16.7c11.2,0,32.5,0,43.5,0c6.2,0,11.3-5.1,11.3-11.3V19.3C114,13.1,109,8,102.7,8z" fill="none" stroke="{INK}" stroke-width="7.4758" stroke-linecap="round" stroke-linejoin="round"/><polyline points="69,57.1 87.5,41.3 69,25.5" fill="none" stroke="{INK}" stroke-width="7.4758" stroke-linecap="round" stroke-linejoin="round"/><path d="M161.6,36.8c0,7.6-5.6,13.5-12.5,13.5c-3.7,0-6.5-1.4-8.3-3.7v13.3h-6.6V24h6.6v3c1.8-2.4,4.6-3.7,8.3-3.7C155.9,23.3,161.6,29.2,161.6,36.8zM154.9,36.8c0-4.3-3-7.2-7.1-7.2s-7.1,2.9-7.1,7.2s3,7.2,7.1,7.2S154.9,41.1,154.9,36.8zM179.6,23.5v7.4c-3.4-0.4-7.8,1.1-7.8,6.5v12.3h-6.6V24h6.6v4.4C173.1,24.9,176.4,23.5,179.6,23.5zM180.1,36.8c0-7.6,6-13.5,13.5-13.5s13.6,5.9,13.6,13.5s-6,13.5-13.6,13.5C186.1,50.3,180.1,44.4,180.1,36.8zM200.6,36.8c0-4.2-3-7.1-7-7.1c-3.9,0-6.9,2.9-6.9,7.1s3,7.1,6.9,7.1C197.6,43.9,200.6,40.9,200.6,36.8zM248.9,33.8v15.8h-6.6V34.3c0-3-1.5-4.9-4.3-4.9c-2.9,0-4.8,1.9-4.8,5.8v14.4h-6.6V34.3c0-3-1.5-4.9-4.3-4.9s-4.8,1.9-4.8,5.8v14.4h-6.6V24h6.6v2.7c1.4-2.2,3.8-3.4,7.1-3.4c3.2,0,5.5,1.3,7,3.7c1.6-2.3,4.2-3.7,7.6-3.7C245.1,23.3,248.9,27.4,248.9,33.8zM281,36.8c0,7.6-5.6,13.5-12.5,13.5c-3.7,0-6.5-1.4-8.3-3.7v13.3h-6.6V24h6.6v3c1.8-2.4,4.6-3.7,8.3-3.7C275.3,23.3,281,29.2,281,36.8zM274.4,36.8c0-4.3-3-7.2-7.1-7.2s-7.1,2.9-7.1,7.2s3,7.2,7.1,7.2C271.3,44,274.4,41.1,274.4,36.8zM292.9,30.3V41c0,2.8,2,2.8,5.8,2.6v6c-9.3,1-12.4-1.7-12.4-8.6V30.3h-4.5V24h4.5v-7.3h6.6V24h5.8v6.4h-5.8V30.3zM301.6,16.8c0-2.2,1.8-4.1,4.1-4.1c2.3,0,4.1,1.9,4.1,4.1s-1.8,4.1-4.1,4.1C303.5,20.9,301.6,19,301.6,16.8zM302.4,24h6.6v25.6h-6.6V24zM312.7,36.8c0-7.6,5.7-13.5,13.5-13.5c5,0,9.4,2.7,11.5,6.6l-5.7,3.3c-1-2.1-3.2-3.4-5.8-3.4c-3.9,0-6.9,2.9-6.9,7s2.9,7,6.9,7c2.7,0,4.9-1.3,5.9-3.4l5.7,3.3c-2.2,4-6.6,6.7-11.6,6.7C318.4,50.3,312.7,44.4,312.7,36.8zM359.6,42.1c0,5.5-4.8,8.2-10.3,8.2c-5.1,0-8.9-2.2-10.8-6.1l5.7-3.2c0.7,2.1,2.5,3.3,5,3.3c2.1,0,3.5-0.7,3.5-2.2c0-3.7-13.2-1.7-13.2-10.7c0-5.2,4.5-8.2,9.7-8.2c4.2,0,7.7,1.9,9.7,5.4l-5.6,3.1c-0.8-1.6-2.2-2.6-4.1-2.6c-1.6,0-3,0.7-3,2.1C346.3,35,359.6,32.7,359.6,42.1z" fill="{INK}"/><path d="M363,45.9c0-2.4,1.9-4.4,4.4-4.4c2.4,0,4.4,1.9,4.4,4.4c0,2.4-1.9,4.4-4.4,4.4C364.9,50.3,363,48.3,363,45.9zM375.4,16.8c0-2.2,1.8-4.1,4.1-4.1c2.3,0,4.1,1.9,4.1,4.1s-1.8,4.1-4.1,4.1C377.3,20.9,375.4,19,375.4,16.8zM376.2,24h6.6v25.6h-6.6V24zM386.5,36.8c0-7.6,6-13.5,13.5-13.5s13.6,5.9,13.6,13.5s-6,13.5-13.6,13.5S386.5,44.4,386.5,36.8zM407,36.8c0-4.2-3-7.1-7-7.1c-3.9,0-6.9,2.9-6.9,7.1s3,7.1,6.9,7.1C404,43.9,407,40.9,407,36.8z" fill="{ACCENT}"/>'''


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
for i, (line, ys) in enumerate((("We're here for what comes after the software factory.", ys1),
                                 ("Wherever you are on the way there.", ys2))):
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
    f'aria-label="The bottleneck moved! You\'ve automated your workflow. Now what? We\'re here for what comes after the software factory. '
    f'Wherever you are on the way there.">'
    f"<style>{style}</style>"
    f'<rect width="{W}" height="{H}" rx="24" fill="{BG}"/>'
    + f'<g class="logo" transform="translate({W - PAD - 382 * 0.3913:.1f},{PAD - 24}) scale(0.3913) translate(-36,-2)">{LOGO}</g>'
    + "".join(out)
    + "</svg>"
)
open(OUT, "w").write(svg)
print(f"{OUT}: {W}x{H}, {len(svg) // 1024} KB, swipe at {t_swipe:.0f} ms, two-liner at {t_sub:.0f} ms")
