#!/usr/bin/env python3
"""
Build the optimised MetaStation brand assets served from the jsDelivr CDN.

Source of truth is the 4096x1488 master. It is the same artwork as the 798x290
copy in metastation-frontend/public/logo.png, just at higher resolution, so it
downsamples cleanly with Lanczos.

About the artwork: the "MetaStation" letterforms are TRANSPARENT KNOCKOUTS in
the gradient band, not white paint (~54% of the master's pixels are alpha<32).
That is deliberate and makes the mark adapt to its surroundings — the wordmark
reads white on a light page and near-black on a dark one. Two consequences:

  * never place it on a busy or gradient background; the letterforms will show
    that background through and turn to mush
  * a social card must composite it onto a solid plate, which is what
    build_social_card() does

Run:  python scripts/build-metastation-brand.py
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "brand"
MASTER = Path(r"E:\Projects\Metastation.fi2\MetaStation-Docs-and-Blogs\static\img\metastation-logo.png")

# Brand colours, taken from the site's own config (announcementBar) and the
# gradient endpoints sampled off the master.
INK = (13, 26, 46)          # #0d1a2e  deep navy
GRAD_START = (118, 223, 210)  # teal, left end of the band
GRAD_END = (178, 248, 159)    # lime, right end

OUT.mkdir(parents=True, exist_ok=True)


def load_master() -> Image.Image:
    if not MASTER.exists():
        raise SystemExit(f"master not found: {MASTER}")
    im = Image.open(MASTER).convert("RGBA")
    print(f"master: {im.size[0]}x{im.size[1]}  aspect {im.size[0]/im.size[1]:.4f}")
    return im


def emit(im: Image.Image, height: int, stem: str, formats=("webp", "png")):
    """Downscale to a target height, preserving aspect and alpha."""
    w = round(height * im.size[0] / im.size[1])
    resized = im.resize((w, height), Image.LANCZOS)
    for fmt in formats:
        path = OUT / f"{stem}.{fmt}"
        if fmt == "webp":
            # quality=90 is visually lossless for flat gradient art at these
            # sizes; method=6 is the slowest/smallest encoder setting.
            resized.save(path, "WEBP", quality=90, method=6)
        else:
            resized.save(path, "PNG", optimize=True)
        print(f"  {path.name:36s} {w}x{height:<5d} {path.stat().st_size/1024:7.1f} KB")


def build_social_card(logo: Image.Image):
    """1200x630 og:image. Referenced by docusaurus.config.js but never existed,
    so every docs and blog page has been shipping a broken og:image."""
    W, H = 1200, 630
    card = Image.new("RGBA", (W, H), INK + (255,))
    d = ImageDraw.Draw(card)

    # Subtle diagonal accent echoing the logo's angled band, kept low-contrast
    # so it never competes with the wordmark.
    d.polygon([(0, H), (W, H - 190), (W, H), (0, H)], fill=(20, 38, 64, 255))

    # Logo at 62% of card width, optically centred slightly above middle to
    # leave room for the tagline.
    target_w = int(W * 0.62)
    lh = round(target_w * logo.size[1] / logo.size[0])
    card.alpha_composite(logo.resize((target_w, lh), Image.LANCZOS),
                         ((W - target_w) // 2, int(H * 0.30) - lh // 2))

    # Tagline, straight from the site config.
    text = "Trade Anywhere. Automate Everything."
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\seguisb.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    tw = d.textlength(text, font=font)
    d.text(((W - tw) / 2, int(H * 0.60)), text, font=font, fill=(205, 232, 219, 255))

    sub = "metastation.fi/docs"
    try:
        font2 = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 30)
    except OSError:
        font2 = ImageFont.load_default()
    sw = d.textlength(sub, font=font2)
    d.text(((W - sw) / 2, int(H * 0.72)), sub, font=font2, fill=GRAD_END + (255,))

    path = OUT / "metastation-social-card.png"
    card.convert("RGB").save(path, "PNG", optimize=True)
    print(f"  {path.name:36s} {W}x{H:<5d} {path.stat().st_size/1024:7.1f} KB")


def build_wordmark_white(logo: Image.Image, height: int = 96):
    """Solid-white wordmark on transparent, for the rare surface where the
    knockout would fail (a coloured or photographic background). Derived by
    using the band's own alpha as an inverse mask: where the band is opaque the
    wordmark is absent, where the letterforms are punched through it is white."""
    w = round(height * logo.size[0] / logo.size[1])
    small = logo.resize((w, height), Image.LANCZOS)
    alpha = small.getchannel("A")

    # Letterforms are the transparent holes INSIDE the band's bounding area.
    # Restrict to the band's vertical extent so the transparent margins above
    # and below the banner are not mistaken for glyphs.
    bbox = alpha.point(lambda v: 255 if v > 128 else 0).getbbox()
    inv = alpha.point(lambda v: 255 - v)
    mask = Image.new("L", small.size, 0)
    mask.paste(inv.crop(bbox), bbox)

    out = Image.new("RGBA", small.size, (255, 255, 255, 0))
    out.putalpha(mask)
    white = Image.new("RGBA", small.size, (255, 255, 255, 255))
    white.putalpha(mask)

    path = OUT / "metastation-wordmark-white.webp"
    white.save(path, "WEBP", quality=90, method=6)
    print(f"  {path.name:36s} {w}x{height:<5d} {path.stat().st_size/1024:7.1f} KB")


def main():
    logo = load_master()

    print("\nhorizontal logo:")
    # 96px tall covers a 32px navbar at 3x DPR and scales down crisply.
    emit(logo, 96, "metastation-logo")
    emit(logo, 192, "metastation-logo@2x", formats=("webp",))
    emit(logo, 320, "metastation-logo-lg", formats=("webp",))

    print("\nsocial card:")
    build_social_card(logo)

    print("\nwordmark:")
    build_wordmark_white(logo)


if __name__ == "__main__":
    main()
