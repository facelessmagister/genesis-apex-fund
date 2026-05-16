#!/usr/bin/env bash
# generate-and-push.sh — Regenerate Apex Fund website, commit, push to GitHub
# Vercel auto-deploys on every push. No CLI needed.
set -euo pipefail

cd /root/genesis/companies/apex-fund/website

# Regenerate site from latest reports
python3 scripts/generate_website.py

# Update site-config
DATE=$(date +%Y-%m-%d)
cat > site-config.json <<EOF
{
  "projectId": "prj_gG4fpcX9WCFZCqVreyBLAOFPUUX3",
  "orgId": "team_qnXasLsdOXvgG6Q9ZzwYqtbR",
  "projectName": "genesis-apex-fund",
  "publicUrl": "https://genesis-apex-fund.vercel.app",
  "deployedAt": "$DATE",
  "type": "static-html",
  "source": "/root/genesis/companies/apex-fund/website"
}
EOF

# Commit and push — Vercel auto-deploys on push
git add .
git commit -m "auto: daily report update $DATE" || true
git push origin master
