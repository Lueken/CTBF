"""Generate the CTBF icon set from the logo mark. Run with Pillow installed."""
from PIL import Image

TEAL = (0x02, 0x7d, 0x9f)          # rail teal, matches the manifest theme_color

src = Image.open('img/ctbf_inc.png').convert('RGB')
w, h = src.size
s = min(w, h)
base = src.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))

def png(img, path):
    img.quantize(colors=256, dither=Image.FLOYDSTEINBERG).save(path, 'PNG', optimize=True)

def square(n):
    return base.resize((n, n), Image.LANCZOS)

png(square(512), 'img/icon-512.png')
png(square(192), 'img/icon-192.png')
png(square(180), 'apple-touch-icon.png')

# Maskable: Android may crop to a circle of 80% diameter, so the mark has to fit
# inside a 290px square inscribed in that circle. Pad the rest with the rail teal.
mask = Image.new('RGB', (512, 512), TEAL)
mask.paste(square(288), (112, 112))
png(mask, 'img/icon-maskable-512.png')

# Multi-size .ico for legacy /favicon.ico requests.
square(48).save('favicon.ico', sizes=[(16, 16), (32, 32), (48, 48)])
