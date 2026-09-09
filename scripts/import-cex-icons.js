#!/usr/bin/env node
/**
 * Import surveyed CEX token icons into assets/.
 *
 * Source: docs/Assets/CEX Icons/.cache/downloaded_icons — the unified staging
 * cache from the Binance / Bybit / KuCoin icon survey. Those files are a mix
 * of PNG, JPG and WebP at whatever size the source CDN served.
 *
 * This normalises every one of them to the repo's convention, which the
 * frontend resolver (metastation-frontend/src/config/tokenIcons.js) depends on
 * literally: UPPERCASE symbol, .webp extension, 144x144, lossless, <= 50 KB.
 *
 * An existing asset is NEVER overwritten. The repo's own icons are curated;
 * the survey's are scraped, so on a collision the curated one wins. Pass
 * --overwrite only if you have decided otherwise for a specific run.
 *
 * sharp lives in metastation-backend/node_modules (this repo has no package
 * manifest of its own), so run it from there:
 *
 *   cd metastation-backend
 *   node ../brand-assets/scripts/import-cex-icons.js [--dry-run] [--overwrite]
 *
 * After importing, cut the next tag (icons-v3) and bump ICON_ORIGIN in
 * tokenIcons.js. The tag and the extension must move together.
 */

const fs = require("fs");
const path = require("path");
const { execFile } = require("child_process");

const REPO = path.join(__dirname, "..", "..");

// Node resolves from the script's own directory, and this repo has no
// node_modules, so sharp is loaded from the backend's tree by path.
const sharp = (() => {
  try {
    return require("sharp");
  } catch {
    return require(path.join(REPO, "metastation-backend", "node_modules", "sharp"));
  }
})();
const SOURCE_DIR = path.join(
  REPO,
  "docs",
  "Assets",
  "CEX Icons",
  ".cache",
  "downloaded_icons"
);
const TARGET_DIR = path.join(__dirname, "..", "assets");

const SIZE = 144;
const MAX_BYTES = 50 * 1024;
const SOURCE_EXT = new Set([".png", ".jpg", ".jpeg", ".webp"]);

const dryRun = process.argv.includes("--dry-run");
const overwrite = process.argv.includes("--overwrite");

/**
 * 274 of the staged files are AVIF wearing a .png extension — DexScreener's
 * CDN serves AVIF regardless of the URL, and the downloader saved the response
 * under the requested name. sharp's bundled libvips has no AVIF decoder
 * ("Bitstream not supported by this decoder"), so those are decoded through
 * ffmpeg first. Detection is by magic bytes, never by extension, since the
 * extension is exactly what lied.
 */
const isAvif = (buffer) => buffer.subarray(4, 12).toString("latin1") === "ftypavif";

const FFMPEG = process.env.FFMPEG_PATH || "ffmpeg";

const avifToPng = (file) =>
  new Promise((resolve, reject) => {
    // Two flags here are load-bearing, and getting either wrong hangs the whole
    // import at ~40s of CPU while wall-clock runs into the hours:
    //   -nostdin      ffmpeg otherwise reads stdin for its interactive key
    //                 handler, and a piped stdin nobody closes never ends.
    //   -f image2pipe the plain `image2` muxer wants to seek its output to fix
    //                 up the header, which a pipe cannot do. It works when you
    //                 redirect to a real file and blocks when you don't.
    // The timeout is the backstop: one undecodable file must cost 60 seconds,
    // not the run.
    execFile(
      FFMPEG,
      ["-nostdin", "-v", "error", "-i", file, "-frames:v", "1", "-pix_fmt", "rgba",
       "-f", "image2pipe", "-vcodec", "png", "-y", "pipe:1"],
      { maxBuffer: 64 * 1024 * 1024, encoding: "buffer", timeout: 60000 },
      (err, stdout) => (err ? reject(err) : resolve(stdout))
    );
  });

/** File contents as something sharp can open, transcoding AVIF on the way. */
const readDecodable = async (file) => {
  const buffer = fs.readFileSync(file);
  return isAvif(buffer) ? avifToPng(file) : buffer;
};

/**
 * Run `worker` over `items` with a bounded number in flight.
 *
 * Serial was ~1s per file once ffmpeg entered the picture, which is 17 minutes
 * for this set with nothing on screen. sharp does its work on libuv threads and
 * ffmpeg is a separate process, so both parallelise well.
 */
async function mapWithConcurrency(items, limit, worker) {
  let cursor = 0;
  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (cursor < items.length) {
      const index = cursor++;
      await worker(items[index], index);
    }
  });
  await Promise.all(runners);
}

/** 144x144 lossless WebP, transparent padding, never upscaled past the box. */
const encode = (input) =>
  sharp(input)
    .resize(SIZE, SIZE, {
      fit: "contain",
      background: { r: 0, g: 0, b: 0, alpha: 0 },
    })
    .webp({ lossless: true, effort: 6 })
    .toBuffer();

/**
 * Lossless is the convention, but a photographic source (some equity logos are
 * JPEGs) can blow past 50 KB losslessly. Step down through near-lossless
 * rather than shipping a 200 KB icon.
 */
async function encodeWithinBudget(input) {
  const lossless = await encode(input);
  if (lossless.length <= MAX_BYTES) return { buffer: lossless, mode: "lossless" };

  for (const quality of [95, 90, 80, 70]) {
    const buffer = await sharp(input)
      .resize(SIZE, SIZE, {
        fit: "contain",
        background: { r: 0, g: 0, b: 0, alpha: 0 },
      })
      .webp({ quality, effort: 6 })
      .toBuffer();
    if (buffer.length <= MAX_BYTES) return { buffer, mode: `q${quality}` };
  }
  return { buffer: null, mode: "too-large" };
}

(async () => {
  if (!fs.existsSync(SOURCE_DIR)) {
    console.error(`Source directory not found: ${SOURCE_DIR}`);
    process.exit(1);
  }

  const files = fs
    .readdirSync(SOURCE_DIR)
    .filter((file) => SOURCE_EXT.has(path.extname(file).toLowerCase()));

  // Uppercasing can collide ("btc.png" and "BTC.png"). Keep the larger source.
  const bySymbol = new Map();
  for (const file of files) {
    const symbol = path.basename(file, path.extname(file)).toUpperCase();
    const full = path.join(SOURCE_DIR, file);
    const size = fs.statSync(full).size;
    const seen = bySymbol.get(symbol);
    if (!seen || size > seen.size) bySymbol.set(symbol, { file: full, size });
  }

  const result = {
    imported: [],
    skippedExisting: [],
    collisions: files.length - bySymbol.size,
    failed: [],
    tooLarge: [],
    lossy: [],
  };

  const entries = Array.from(bySymbol).sort();
  let done = 0;

  await mapWithConcurrency(entries, 8, async ([symbol, { file }]) => {
    const target = path.join(TARGET_DIR, `${symbol}.webp`);

    if (!overwrite && fs.existsSync(target)) {
      result.skippedExisting.push(symbol);
    } else {
      try {
        const { buffer, mode } = await encodeWithinBudget(await readDecodable(file));
        if (!buffer) {
          result.tooLarge.push(symbol);
        } else {
          if (mode !== "lossless") result.lossy.push(`${symbol} (${mode})`);
          if (!dryRun) fs.writeFileSync(target, buffer);
          result.imported.push(symbol);
        }
      } catch (e) {
        result.failed.push(`${symbol}: ${String(e.message).split("\n")[0]}`);
      }
    }

    done += 1;
    if (done % 50 === 0 || done === entries.length) {
      process.stderr.write(
        `  ${done}/${entries.length}  imported ${result.imported.length}  failed ${result.failed.length}\n`
      );
    }
  });

  console.log(`source files              ${files.length}`);
  console.log(`unique symbols            ${bySymbol.size}`);
  console.log(`  case collisions merged  ${result.collisions}`);
  console.log(`imported${dryRun ? " (dry run)" : "        "}          ${result.imported.length}`);
  console.log(`  re-encoded lossy        ${result.lossy.length}`);
  console.log(`skipped, already present  ${result.skippedExisting.length}`);
  console.log(`over 50 KB, not written   ${result.tooLarge.length}`);
  console.log(`failed to decode          ${result.failed.length}`);

  if (result.lossy.length) console.log(`\nlossy: ${result.lossy.join(", ")}`);
  if (result.tooLarge.length) console.log(`\ntoo large: ${result.tooLarge.join(", ")}`);
  if (result.failed.length) console.log(`\nfailed:\n  ${result.failed.join("\n  ")}`);
})();
