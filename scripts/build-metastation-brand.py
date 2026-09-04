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

from PIL import Image, ImageChops, ImageDraw, ImageFont
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "brand"
# Masters live in this repo so the set is reproducible without depending on a
# checkout of the app or the docs site sitting at a particular path.
# metastation-logo-master.png is 4096x1488 — the same artwork as the 798x290
# copy in metastation-frontend/public/logo.png, at the resolution that lets the
# large variants downsample instead of upscale.
MASTER = REPO / "masters" / "metastation-logo-master.png"
# The square mark (stacked META / STATION), confirmed correct by the brand
# owner — resized here, never redrawn.
SQUARE = REPO / "masters" / "metastation-square-master.webp"

# Brand colours, taken from the site's own config (announcementBar) and the
# gradient endpoints sampled off the master.
INK = (13, 26, 46)          # #0d1a2e  deep navy
GRAD_START = (118, 223, 210)  # teal, left end of the band
GRAD_END = (178, 248, 159)    # lime, right end

OUT.mkdir(parents=True, exist_ok=True)


# THE authoritative source for the horizontal logo. This is the file the brand
# owner edits; masters/metastation-logo-master.png in this repo is a copy of it.
#
# History worth keeping: the first pass of this script built from a copy taken
# out of the docs repo's git history, which turned out to be an older, WASHED-OUT
# revision of the gradient — the real artwork is far more saturated. The two
# differed by a mean of 26.6/255 across 52% of pixels, and the pale version
# shipped to production before anyone noticed. Hence check_master_drift(): a
# stale master is not visible by eye at navbar size, only by measurement.
#
# Note the filename is log.png, not logo.png.
APP_LOGO = Path(r"E:\Projects\Metastation.fi2\metastation-frontend\src\Img\log.png")


def check_master_drift(master: Image.Image) -> None:
    """Warn loudly if masters/ no longer matches the app's logo.png.

    Compares the two as silhouettes and as flattened pixels at a common size.
    Resampling between 4096 and 798 wide leaves a mean difference of roughly
    2-3/255 with no structural change; an actual redraw shows up as ghosted or
    doubled letterforms and a much larger mean. The threshold sits between.
    """
    if not APP_LOGO.exists():
        print(f"  (drift check skipped: {APP_LOGO} not found)")
        return
    app = Image.open(APP_LOGO).convert("RGBA")

    ar_m, ar_a = master.size[0] / master.size[1], app.size[0] / app.size[1]
    if abs(ar_m - ar_a) > 0.01:
        print(f"  !! ASPECT MISMATCH: master {ar_m:.4f} vs app logo {ar_a:.4f}")
        print(f"  !! The artwork has been reshaped. Refresh {MASTER.name} before shipping.")
        return

    N = (798, 290)

    def flat(im):
        c = Image.new("RGBA", im.size, (255, 255, 255, 255))
        c.alpha_composite(im)
        return c.convert("L").resize(N, Image.LANCZOS)

    d = ImageChops.difference(flat(master), flat(app))
    px = list(d.getdata())
    mean = sum(px) / len(px)
    heavy = sum(1 for v in px if v > 32) / len(px)

    if mean > 8 or heavy > 0.05:
        print(f"  !! MASTER DRIFT: mean diff {mean:.2f}/255, {100*heavy:.2f}% of pixels differ heavily.")
        print(f"  !! {APP_LOGO.name} looks like DIFFERENT artwork, not just a different resolution.")
        print(f"  !! Refresh {MASTER} from the current source before shipping, or the site")
        print(f"  !! will keep serving the old logo.")
    else:
        print(f"  drift check ok: mean diff {mean:.2f}/255, {100*heavy:.2f}% heavy "
              f"— consistent with resampling, same artwork")


def load_master() -> Image.Image:
    if not MASTER.exists():
        raise SystemExit(f"master not found: {MASTER}")
    im = Image.open(MASTER).convert("RGBA")
    print(f"master: {im.size[0]}x{im.size[1]}  aspect {im.size[0]/im.size[1]:.4f}")
    check_master_drift(im)
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


def build_icon_and_avatar():
    """The square mark (stacked META / STATION). Used for blog author avatars,
    cards and slots. Its wordmark is a knockout too, so it is emitted twice:

      metastation-icon-*   transparent, for surfaces that supply their own
                           background and want the mark to adapt
      metastation-avatar-* composited onto a solid navy plate, for circular
                           avatars — otherwise the glyphs flip colour between
                           light and dark theme and the crop looks accidental
    """
    if not SQUARE.exists():
        print(f"  skip: square master not found at {SQUARE}")
        return
    sq = Image.open(SQUARE).convert("RGBA")
    print(f"  square master: {sq.size[0]}x{sq.size[1]}")

    for h in (96, 192):
        out = sq.resize((h, h), Image.LANCZOS)
        p = OUT / f"metastation-icon-{h}.webp"
        out.save(p, "WEBP", quality=90, method=6)
        print(f"  {p.name:36s} {h}x{h:<6d} {p.stat().st_size/1024:7.1f} KB")

    for h in (96, 192):
        plate = Image.new("RGBA", (h, h), INK + (255,))
        # Inset slightly so the mark is not flush to the circle's crop edge.
        inset = round(h * 0.10)
        mark = sq.resize((h - 2 * inset, h - 2 * inset), Image.LANCZOS)
        plate.alpha_composite(mark, (inset, inset))
        p = OUT / f"metastation-avatar-{h}.webp"
        plate.convert("RGB").save(p, "WEBP", quality=90, method=6)
        print(f"  {p.name:36s} {h}x{h:<6d} {p.stat().st_size/1024:7.1f} KB")


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

    print("\nsquare mark:")
    build_icon_and_avatar()


if __name__ == "__main__":
    main()
