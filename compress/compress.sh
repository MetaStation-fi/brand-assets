#!/usr/bin/env bash
#
# Encode source icons to lossless WebP, the format every served folder in this
# repo uses (see the WebP note in ../README.md).
#
# Lossless, not quality-95 lossy: these are flat logo marks, where lossless is
# both exact and usually smaller than the PNG it replaces. `-z 9` is the
# slowest/densest lossless preset — worth it for assets encoded once and served
# forever.
#
# Drop 144x144 PNG/JPEG sources at the root of this folder and run
# `pnpm compress` from lib/. Output lands in compress/out/.
set -euo pipefail

INPUT_DIR="$(dirname "$0")"
OUTPUT_DIR="$INPUT_DIR/out"

mkdir -p "$OUTPUT_DIR"

shopt -s nullglob
src_files=("$INPUT_DIR"/*.png "$INPUT_DIR"/*.jpg "$INPUT_DIR"/*.jpeg)
shopt -u nullglob

if [ ${#src_files[@]} -eq 0 ]; then
  echo "❌ No PNG/JPEG files found in $INPUT_DIR. Please place your 144x144 sources at the root of this folder."
  exit 1
fi

for f in "${src_files[@]}"; do
  filename="$(basename "${f%.*}").webp"
  cwebp -lossless -z 9 -exact -quiet "$f" -o "$OUTPUT_DIR/$filename"
  echo "✔ $(basename "$f") -> $filename"
done
