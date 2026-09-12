#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "============================================"
echo " Yellow Pages Scraper - Linux Build"
echo "============================================"
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found."
  exit 1
fi

if [[ ! -d venv ]]; then
  echo "Creating virtual environment..."
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-build.txt

rm -rf build dist/YellowPagesScraper

echo
echo "Running PyInstaller..."
python -m PyInstaller --noconfirm --clean YellowPagesScraper.spec

cat > dist/YellowPagesScraper/README_PORTABLE.txt <<'EOF'
Yellow Pages Scraper - Portable App
==================================

Requirements on this PC:
  1. Google Chrome / Chromium installed
  2. Linux desktop (GUI)

How to run:
  ./YellowPagesScraper

If permission denied:
  chmod +x YellowPagesScraper

Output files are created next to the binary in:
  output/data/
  output/logs/
  output/app/

You do NOT need Python or pip on this PC.
Keep the whole YellowPagesScraper folder together.
EOF

echo
echo "BUILD SUCCESS"
echo "App folder: $(pwd)/dist/YellowPagesScraper/"
echo "Binary:     $(pwd)/dist/YellowPagesScraper/YellowPagesScraper"
echo
echo "Zip and copy dist/YellowPagesScraper to other Linux PCs."
echo "Target PC still needs Google Chrome installed."
