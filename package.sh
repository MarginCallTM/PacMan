#!/bin/sh
# Packaging spec (subject ch. VII): build the Itch.io bundle.
#
#   ./package.sh   ->   dist/pacman-42.zip
#
# The bundle is a self-contained folder: our game wheel (built here by
# uv build), the two assigned dependency wheels as-is, the commented
# default config, player instructions, and a single `pacman` launcher
# that installs into a local venv on first run, then starts the game.
# Regenerable live during the review with this one script (`make build`).
set -e
cd "$(dirname "$0")"

echo "Building the game wheel..."
uv build --quiet

echo "Assembling the bundle..."
rm -rf dist/pacman-42 dist/pacman-42.zip
mkdir -p dist/pacman-42
cp dist/pacman-*-py3-none-any.whl \
   mazegenerator-*-py3-none-any.whl \
   mlx-*-py3-none-any.whl \
   config.json \
   packaging/INSTRUCTIONS.txt \
   packaging/pacman \
   dist/pacman-42/
chmod +x dist/pacman-42/pacman

cd dist && python3 -m zipfile -c pacman-42.zip pacman-42
echo "Done: dist/pacman-42.zip"
