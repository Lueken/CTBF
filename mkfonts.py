"""Regenerate fonts/ and the @font-face block the pages carry inline.

Run this if the weights or families ever change. It does two jobs:

  1. Pulls the latin woff2 subsets straight from Google's CSS so we self-host
     them. One physical file backs several weights -- both families ship as
     variable fonts -- so three files cover everything the site uses.

  2. Computes the size-adjust / ascent / descent overrides that let a system
     font stand in for the real one without changing where anything sits.

On (2), the obvious shortcut is wrong: OS/2 xAvgCharWidth is not comparable
across fonts. Georgia reports it with version-1 semantics (frequency-weighted
lowercase) while the Google fonts use version-4 (mean of every glyph), so
dividing one by the other says Cormorant is 23% WIDER than Georgia when it is
really about 10% narrower. Measure the advance widths here instead, with one
formula applied to both sides.

Two fallback tiers, because the metric-compatible families split into groups
and no single adjustment serves both:

    tier 1   Georgia, Gelasio                                    Windows, macOS, iOS
    tier 2   Times New Roman, Liberation Serif, Tinos, Nimbus    Linux, headless CI

Arial, Liberation Sans, Arimo and Helvetica share one metric set, so the sans
side needs a single tier with a longer src list.

Needs: fonttools, brotli (to read woff2).
"""
import os
import re
import urllib.request

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'fonts')
WIN = r'C:\Windows\Fonts'

GOOGLE_CSS = ('https://fonts.googleapis.com/css2'
              '?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400'
              '&family=Karla:wght@400;500;600;700&display=swap')
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

# Relative frequency of characters in ordinary English prose, which is what the
# pages are made of. Weighting by this tracks real line lengths far better than
# a flat mean over the whole glyph set.
FREQ = {
    ' ': 18.3, 'e': 10.2, 't': 7.5, 'a': 6.5, 'o': 6.1, 'i': 5.7, 'n': 5.7, 's': 5.3,
    'r': 5.0, 'h': 5.0, 'l': 3.3, 'd': 3.3, 'u': 2.3, 'c': 2.3, 'm': 2.0, 'f': 1.8,
    'w': 1.7, 'g': 1.6, 'p': 1.6, 'y': 1.6, 'b': 1.2, 'v': 0.8, 'k': 0.6, 'x': 0.2,
    'j': 0.1, 'q': 0.1, 'z': 0.1,
    'E': 0.6, 'T': 0.5, 'A': 0.4, 'O': 0.4, 'I': 0.4, 'N': 0.3, 'S': 0.3, 'R': 0.3,
    'H': 0.3, 'L': 0.2, 'D': 0.2, 'C': 0.2, 'M': 0.2, 'F': 0.1, 'W': 0.1, 'B': 0.1,
}


def fetch(url, **headers):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={'User-Agent': UA, **headers}), timeout=40).read()


def download_subsets():
    """Save the latin woff2 of every face, deduped -- one file serves many weights."""
    css = fetch(GOOGLE_CSS).decode('utf-8')
    os.makedirs(FONTS, exist_ok=True)
    seen = {}
    for block in re.findall(r'@font-face\s*\{(.*?)\}', css, re.S):
        urange = re.search(r'unicode-range:\s*([^;]+);', block)
        if not urange or 'U+0000-00FF' not in urange.group(1):
            continue                                    # latin subset only
        family = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        style = re.search(r'font-style:\s*(\w+)', block).group(1)
        url = re.search(r'url\((https://[^)]+)\)', block).group(1)
        if url in seen:
            continue
        name = f"{family.lower().replace(' ', '-')}-{style}-latin.woff2"
        data = fetch(url)
        open(os.path.join(FONTS, name), 'wb').write(data)
        seen[url] = name
        print(f'  {len(data)/1024:6.1f} KB  {name}')


def load(path, weight=None):
    f = TTFont(path, lazy=False)
    if weight is not None and 'fvar' in f:
        f = instantiateVariableFont(f, {'wght': weight}, inplace=False, updateFontNames=False)
    return f


def avg_advance(f):
    upem, cmap, hmtx = f['head'].unitsPerEm, f.getBestCmap(), f['hmtx']
    total = weight = 0.0
    for ch, w in FREQ.items():
        g = cmap.get(ord(ch))
        if g:
            total += (hmtx[g][0] / upem) * w
            weight += w
    return total / weight


def vmetrics(f):
    os2, upem = f['OS/2'], f['head'].unitsPerEm
    return os2.sTypoAscender / upem, abs(os2.sTypoDescender) / upem, os2.sTypoLineGap / upem


GEORGIA = "local('Georgia'), local('Gelasio')"
GEORGIA_I = "local('Georgia Italic'), local('Gelasio Italic')"
TIMES = "local('Times New Roman'), local('Liberation Serif'), local('Tinos'), local('Nimbus Roman')"
TIMES_I = "local('Times New Roman Italic'), local('Liberation Serif Italic'), local('Tinos Italic')"
ARIAL = "local('Arial'), local('Liberation Sans'), local('Arimo'), local('Helvetica')"

WEBFONTS = [
    ("'Cormorant Garamond'", 'cormorant-garamond-normal-latin.woff2', 'normal', '300 700'),
    ("'Cormorant Garamond'", 'cormorant-garamond-italic-latin.woff2', 'italic', '400'),
    ("'Karla'",              'karla-normal-latin.woff2',              'normal', '400 800'),
]
FALLBACKS = [
    # css family, webfont file, weight to sample, system font, src list, italic
    ('Cormorant Fallback',  'cormorant-garamond-normal-latin.woff2', 600,  'georgia.ttf',  GEORGIA,   False),
    ('Cormorant Fallback',  'cormorant-garamond-italic-latin.woff2', None, 'georgiai.ttf', GEORGIA_I, True),
    ('Cormorant Fallback2', 'cormorant-garamond-normal-latin.woff2', 600,  'times.ttf',    TIMES,     False),
    ('Cormorant Fallback2', 'cormorant-garamond-italic-latin.woff2', None, 'timesi.ttf',   TIMES_I,   True),
    ('Karla Fallback',      'karla-normal-latin.woff2',              400,  'arial.ttf',    ARIAL,     False),
]


def build_css():
    out = ['/* Self-hosted: type no longer waits on two cross-origin round trips',
           '   (the stylesheet, then the font files) before a word can be styled. */']
    for family, fname, style, wght in WEBFONTS:
        out += ['@font-face { font-family:%s; font-style:%s; font-weight:%s; font-display:swap;'
                % (family, style, wght),
                "  src:url(/fonts/%s) format('woff2'); }" % fname]

    out += ['',
            '/* Metric-matched fallbacks, so the page laid out in a system font occupies',
            '   exactly the space the real face will and nothing moves when it arrives.',
            '   Tier 1 is the Georgia metric group, tier 2 the Times group; between them',
            '   they cover Windows, macOS, iOS and Linux. */']

    for family, fname, wt, sysfont, src, italic in FALLBACKS:
        web = load(os.path.join(FONTS, fname), wt)
        sysf = load(os.path.join(WIN, sysfont))
        adjust = avg_advance(web) / avg_advance(sysf)
        asc, desc, gap = vmetrics(web)
        print(f'  {family:20s} vs {sysfont:13s} size-adjust {adjust*100:6.2f}%')
        out += ["@font-face { font-family:'%s';%s src:%s;"
                % (family, ' font-style:italic;' if italic else '', src),
                '  size-adjust:%.2f%%; ascent-override:%.2f%%; descent-override:%.2f%%;'
                ' line-gap-override:%.2f%%; }'
                % (adjust * 100, asc / adjust * 100, desc / adjust * 100, gap / adjust * 100)]
    return '\n'.join(out)


def main():
    print('downloading latin subsets:')
    download_subsets()
    print('\ncomputing fallback metrics:')
    css = build_css()
    # Printed rather than written: the site has no build step, and a stray
    # fontface.css at the root would just get deployed. Paste the block at the
    # top of each page's <style> if it has changed.
    print('\n' + '-' * 72)
    print(css)


if __name__ == '__main__':
    main()
