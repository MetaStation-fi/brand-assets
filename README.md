# crypto-icons

Provide crypto icons assets by ledgerId

## Disclaimer

Some of the icons provided are trademarks: they are the property of their respective owners.

## @ledgerhq/crypto-icons

See @ledgerhq/crypto-icons library README here: [lib/README.md](lib/README.md)

## Format: lossless WebP

Every icon this repo **serves** is 144x144 lossless WebP — `assets/`,
`HIP3-Favicons/`, `networks/` and `brand/`. The icon origin is moving to an R2
bucket where WebP is the target format, so the whole set was converted up front
(690 files, 5.67 MB → 3.85 MB) rather than at cutover.

Lossless, not quality-95 lossy: these are flat logo marks, where lossless is
both exact and usually smaller than the PNG it replaces.

Four kinds of file are deliberately **not** WebP:

| File | Why it stays |
|---|---|
| `*.svg` (3 in `HIP3-Favicons/`) | Vector — already resolution-free and smaller |
| `brand/metastation-favicon.ico` | Multi-size container with no WebP equivalent |
| `brand/metastation-favicon-{32,180,192}.png` | `apple-touch-icon` and `<link rel="icon">`; iOS home-screen icons are PNG-only |
| `brand/metastation-social-card.png` | Open Graph / Twitter card — several social crawlers and link unfurlers still do not decode WebP |
| `masters/*` | Source masters, not served |

`icons-v1` is the last all-PNG cut; `icons-v2` is the first WebP one.

## How icons reach production

The app resolves every icon through
`cdn.jsdelivr.net/gh/MetaStation-fi/brand-assets@main` — a **floating ref**, not
a tag (changed 2026-09-10; the tag pin meant every batch of artwork needed a tag
plus a frontend deploy, and ~1000 committed icons sat invisible behind
`icons-v2` while live markets drew letter avatars).

So publishing an icon is:

```bash
node scripts/verify-icons.js     # the gate the tag bump used to be
git add -A && git commit -m 'icons: ...' && git push origin main
node scripts/purge-cdn.js        # drop the edge cache for what changed
```

Notes on the caching, measured against jsDelivr rather than assumed:

- A missing file returns `no-cache, no-store`, so a **new** icon is never masked
  by a cached 404 — it appears as soon as the edge re-resolves `main`.
- A branch ref is edge-cached for 12h (`s-maxage=43200`); `purge-cdn.js` makes a
  push visible immediately.
- A file already served is browser-cached for 7 days (`max-age=604800`), which no
  purge can reach — so **replace** artwork under a new filename rather than
  overwriting, or accept the week.

Tags are still cut occasionally as rollback points, but nothing wires to them.
To roll production back, point `ICON_ORIGIN` in
`metastation-frontend/src/config/tokenIcons.js` at a tag; that is the only time
that line should change.

## How to upload a new icon

### Prerequisites

- Find the ledgerIds of the coin on various networks using [CoinRadar](https://coinradar.ledger.com/)
- Prepare a 144x144 source image with a background (no transparent background). If in doubt, contact the design team or WXP team
- Use a recognizable name for the file (ticker or coin name)

### Compress the images

1. Add the PNG/JPEG files to the `compress/` folder
2. Run `pnpm compress` from the `lib` folder (needs `cwebp` from libwebp on PATH)
3. Move the resulting `.webp` files to the `assets/` folder

**Important:** Icon files must be **≤50 KB** after compression (41 KB is already large - aim for smaller file sizes when possible). The verification script will check this automatically.

### Mapping

Add the ledgerIds in `assets/_record.json` following this structure:

```json
"{icon_file_name}": {
  "ids": [
    "{first_ledger_id}",
    "{second_ledger_id}"
  ]
}
```

Then run `pnpm generate:index` to update the mapping in `assets/index.json`.

### Verification

Run the verification script to check that all icons are valid:

```bash
node scripts/verify-icons.js
```

This script validates:

- All icon files exist
- File sizes are within limits (default: **50 KB max** for 144×144 PNG icons - note that 50 KB is already large, aim for smaller sizes)
- All ledger IDs are valid against the API

**Options:**

- `--max-size <KB>`: Set custom file size limit (default: 50 KB)
- `--concurrency <N>`: Set API request concurrency (default: 5)

**Example:**

```bash
node scripts/verify-icons.js --max-size 50 --concurrency 10
```

### Note

Storybook relies on the icons already in production, so if you don't see your icon in your storybook branch, that's expected.
