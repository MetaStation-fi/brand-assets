#!/usr/bin/env node

// Drop the jsDelivr edge cache for the icons a push just changed.
//
// The frontend resolves icons through a floating ref
// (cdn.jsdelivr.net/gh/MetaStation-fi/brand-assets@main), so nothing has to be
// tagged or redeployed to ship artwork — but a branch ref is cached at the edge
// for 12h (s-maxage=43200). Purging makes a push visible immediately.
//
// Brand-new files do not strictly need this: jsDelivr answers a miss with
// `no-cache, no-store`, so a 404 is never cached. Replacements do, and running
// it on every push is simpler than reasoning about which case a file is in.
//
// Usage:
//   node scripts/purge-cdn.js                 # files changed in HEAD
//   node scripts/purge-cdn.js HEAD~3          # files changed since a ref
//   node scripts/purge-cdn.js assets/BTC.webp # explicit paths
//   node scripts/purge-cdn.js --dry-run

const { execFileSync } = require("child_process");
const path = require("path");

const REPO = "MetaStation-fi/brand-assets";
const REF = "main";
const PURGE_ENDPOINT = "https://purge.jsdelivr.net/";
// The API rejects oversized batches; 20 paths per request is the documented cap.
const BATCH = 20;
// Only the folders the app actually resolves against are worth purging.
const SERVED_DIRS = ["assets/", "HIP3-Favicons/", "networks/", "brand/"];

const colors = { reset: "\x1b[0m", red: "\x1b[31m", green: "\x1b[32m", yellow: "\x1b[33m" };
const log = (msg, color = "reset") => console.log(`${colors[color]}${msg}${colors.reset}`);

function git(...args) {
  return execFileSync("git", args, {
    cwd: path.join(__dirname, ".."),
    encoding: "utf-8",
  }).trim();
}

function changedFiles(ref) {
  // Deleted files are skipped: purging a path that no longer exists is a no-op
  // at best and re-caches a 404 at worst.
  const out = git("diff", "--name-only", "--diff-filter=d", `${ref}..HEAD`);
  return out ? out.split("\n") : [];
}

async function purge(paths) {
  const res = await fetch(PURGE_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: paths }),
  });
  if (!res.ok) throw new Error(`purge failed: ${res.status} ${await res.text()}`);
  return res.json();
}

async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes("--dry-run");
  const rest = args.filter((a) => a !== "--dry-run");

  let files;
  if (rest.some((a) => a.includes("/"))) {
    files = rest;
  } else {
    const ref = rest[0] || "HEAD~1";
    files = changedFiles(ref);
    log(`changed since ${ref}: ${files.length} file(s)`);
  }

  const served = files.filter((f) => SERVED_DIRS.some((d) => f.startsWith(d)));
  if (!served.length) {
    log("nothing served changed — no purge needed", "yellow");
    return;
  }

  const paths = served.map((f) => `/gh/${REPO}@${REF}/${f}`);
  log(`purging ${paths.length} path(s) on @${REF}`);

  if (dryRun) {
    paths.forEach((p) => log(`  ${p}`));
    return;
  }

  let throttled = 0;
  for (let i = 0; i < paths.length; i += BATCH) {
    const batch = paths.slice(i, i + BATCH);
    const result = await purge(batch);
    for (const [p, info] of Object.entries(result.paths || {})) {
      if (info.throttled) {
        throttled++;
        log(`  throttled: ${p}`, "yellow");
      }
    }
    log(`  batch ${Math.floor(i / BATCH) + 1}: ${batch.length} path(s) — ${result.status}`);
  }

  if (throttled) {
    log(`${throttled} path(s) throttled; they clear on the 12h edge TTL anyway`, "yellow");
  }
  log("done", "green");
}

main().catch((err) => {
  log(err.message, "red");
  process.exit(1);
});
