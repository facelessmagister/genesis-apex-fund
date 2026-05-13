#!/usr/bin/env bash
# apex-website-update.sh — Regenerate Apex Fund website after daily report cycle
set -euo pipefail

cd /root/genesis/companies/apex-fund/website
python3 scripts/generate_website.py

# Deploy to Vercel
/mnt/c/Users/netfl/AppData/Roaming/npm/vercel deploy --yes --prod --cwd . 2>&1
