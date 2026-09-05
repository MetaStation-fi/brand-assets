# Documentation assets

CDN-hosted assets for the MetaStation documentation site
(`metastation.fi/docs`), served through jsDelivr so the docs origin serves no
images of its own.

## Layout

```
docs/screens/<section>/<id>.webp          desktop capture, 1440x900 @2x
docs/screens/<section>/<id>--mobile.webp  mobile capture,  390x844 @3x
```

Sections mirror the docs IA: `getting-started`, `trading`, `automation`,
`social-trading`, `wallet`, `security`.

## Referencing them

Always tag-pinned, never `@main` — `@main` is mutable and cached hard:

```
https://cdn.jsdelivr.net/gh/MetaStation-fi/brand-assets@docs-v1/docs/screens/<section>/<id>.webp
```

The docs site resolves these through `customFields.screensCdn` in
`docusaurus.config.js`, so a new tag is a one-line change there rather than an
edit to every page.

## Updating

These are generated, not hand-made. Regenerate them in the docs repo
(`scripts/capture-screens.mjs`), copy the output here, then commit and cut the
next `docs-v*` tag and bump `screensCdn`.

Captures are redacted at capture time — emails, wallet addresses, API keys,
webhook tokens and platform account ids are masked before the pixel is taken,
and the capture run fails if a forbidden term is still visible. Do not add
screenshots here by hand: a hand-taken capture has had none of that applied.
