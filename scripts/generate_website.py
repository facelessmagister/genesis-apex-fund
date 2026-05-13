#!/usr/bin/env python3
"""
generate_website.py — Apex Fund Website Generator
Reads daily JSON reports and generates a static promotional website.
Run after apex-fund-pipeline and apex-fund-report complete.
"""
import json, os, sys, glob, re
from pathlib import Path
from datetime import datetime

ROOT = Path('/root/genesis/companies/apex-fund')
REPORTS_DIR = ROOT / 'data/reports'
WEBSITE_DIR = ROOT / 'website'
OUTPUT = WEBSITE_DIR / 'index.html'

def load_reports(limit=30):
    """Load recent daily reports newest first."""
    files = sorted(glob.glob(str(REPORTS_DIR / 'daily-*.json')), reverse=True)
    reports = []
    for f in files[:limit]:
        try:
            with open(f) as fh:
                reports.append(json.load(fh))
        except Exception:
            continue
    return reports

def fmt_usd(v):
    return f"${v:,.2f}" if v >= 1 else f"${v:.4f}"

def fmt_pct(v):
    color = "#10b981" if v >= 0 else "#ef4444"
    sign = "+" if v >= 0 else ""
    return f'<span style="color:{color}">{sign}{v:.2f}%</span>'

def build_report_cards(reports):
    """Build HTML cards for each daily report."""
    cards = []
    for r in reports:
        p = r.get('portfolio', {})
        m = r.get('metrics', {})
        alerts = r.get('alerts', [])
        date = r.get('date', '?')

        dd = p.get('drawdown_pct', 0)
        dd_color = "#ef4444" if dd >= 8 else "#f59e0b" if dd >= 5 else "#10b981"
        dd_html = f'<span style="color:{dd_color}">{dd:.2f}%</span>'

        alert_badge = ""
        if alerts:
            alert_badge = f'<span class="badge alert">{len(alerts)} alert{"s" if len(alerts)>1 else ""}</span>'

        positions_html = ""
        positions = r.get('positions', {})
        top_gainers = sorted(positions.items(), key=lambda x: x[1].get('pnl_pct', 0), reverse=True)[:3]
        top_losers = sorted(positions.items(), key=lambda x: x[1].get('pnl_pct', 0))[:3]

        if top_gainers:
            positions_html += '<div class="pos-section"><h5>Top Gainers</h5>'
            for ticker, data in top_gainers:
                positions_html += f'<div class="pos-row"><span class="ticker">{ticker.replace("USDT","")}</span><span class="pnl" style="color:#10b981">+{data.get("pnl_pct",0):.2f}%</span></div>'
            positions_html += '</div>'
        if top_losers:
            positions_html += '<div class="pos-section"><h5>Top Losers</h5>'
            for ticker, data in top_losers:
                positions_html += f'<div class="pos-row"><span class="ticker">{ticker.replace("USDT","")}</span><span class="pnl" style="color:#ef4444">{data.get("pnl_pct",0):.2f}%</span></div>'
            positions_html += '</div>'

        card = f"""
<div class="report-card">
  <div class="report-header">
    <h4>{date}</h4>
    {alert_badge}
  </div>
  <div class="report-grid">
    <div class="metric">
      <span class="label">Total Value</span>
      <span class="value">{fmt_usd(p.get('total_value_usdt', 0))}</span>
    </div>
    <div class="metric">
      <span class="label">Cash</span>
      <span class="value">{fmt_usd(p.get('cash_usdt', 0))}</span>
    </div>
    <div class="metric">
      <span class="label">Positions</span>
      <span class="value">{fmt_usd(p.get('position_value_usdt', 0))}</span>
    </div>
    <div class="metric">
      <span class="label">Drawdown</span>
      <span class="value">{dd_html}</span>
    </div>
    <div class="metric">
      <span class="label">Unrealized PnL</span>
      <span class="value">{fmt_pct(p.get('unrealized_pnl', 0))}</span>
    </div>
    <div class="metric">
      <span class="label">Open Positions</span>
      <span class="value">{m.get('open_positions', 0)}</span>
    </div>
  </div>
  {positions_html}
</div>
"""
        cards.append(card)
    return "\n".join(cards)

def build_positions_table(reports):
    """Build a summary table of all current positions from latest report."""
    if not reports:
        return "<p>No data available.</p>"
    latest = reports[0]
    positions = latest.get('positions', {})
    if not positions:
        return "<p>No open positions.</p>"

    rows = []
    for ticker, data in sorted(positions.items(), key=lambda x: x[1].get('pnl_pct', 0), reverse=True):
        pnl = data.get('pnl_pct', 0)
        color = "#10b981" if pnl >= 0 else "#ef4444"
        sign = "+" if pnl >= 0 else ""
        rows.append(f"""
    <tr>
      <td><strong>{ticker.replace('USDT','')}</strong></td>
      <td>{data.get('amount',0):.4f}</td>
      <td>${data.get('entry',0):.6f}</td>
      <td>${data.get('current',0):.6f}</td>
      <td>{fmt_usd(data.get('value_usdt',0))}</td>
      <td style="color:{color}">{sign}{pnl:.2f}%</td>
    </tr>
""")
    return "\n".join(rows)

def generate():
    reports = load_reports(limit=30)
    report_cards = build_report_cards(reports)
    positions_table = build_positions_table(reports)

    # Compute summary stats from latest report
    latest = reports[0] if reports else {}
    lp = latest.get('portfolio', {})
    total_value = lp.get('total_value_usdt', 0)
    peak = lp.get('peak_value_usdt', total_value)
    drawdown = lp.get('drawdown_pct', 0)
    unrealized = lp.get('unrealized_pnl', 0)
    open_pos = latest.get('metrics', {}).get('open_positions', 0)

    # Determine mood color for hero
    mood_color = "#10b981" if drawdown < 3 else "#f59e0b" if drawdown < 8 else "#ef4444"

    # Chart data: total value over time
    chart_labels = []
    chart_values = []
    for r in reversed(reports[-14:]):  # last 14 days
        chart_labels.append(r.get('date', '')[5:])  # MM-DD
        chart_values.append(r.get('portfolio', {}).get('total_value_usdt', 0))

    chart_labels_js = json.dumps(chart_labels)
    chart_values_js = json.dumps(chart_values)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Apex Fund — Autonomous AI Portfolio Management</title>
<style>
:root {{
  --bg: #0a0e17;
  --bg-elevated: #111827;
  --bg-card: #1a1f2e;
  --border: #232b3e;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --accent: #3b82f6;
  --accent-glow: rgba(59,130,246,0.3);
  --green: #10b981;
  --red: #ef4444;
  --amber: #f59e0b;
  --max-width: 1200px;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* Navigation */
nav {{
  position: fixed; top: 0; left: 0; right: 0;
  background: rgba(10,14,23,0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  z-index: 1000;
}}
.nav-inner {{
  max-width: var(--max-width); margin: 0 auto;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 64px;
}}
.logo {{ font-size: 1.4rem; font-weight: 800; letter-spacing: -0.5px; }}
.logo span {{ color: var(--accent); }}
.nav-links {{ display: flex; gap: 32px; list-style: none; }}
.nav-links a {{ color: var(--text-muted); font-size: 0.9rem; font-weight: 500; transition: color 0.2s; }}
.nav-links a:hover {{ color: var(--text); }}

/* Hero */
.hero {{
  padding: 140px 24px 80px;
  text-align: center;
  background: linear-gradient(180deg, var(--bg) 0%, var(--bg-elevated) 100%);
  border-bottom: 1px solid var(--border);
}}
.hero h1 {{
  font-size: 3rem; font-weight: 800; letter-spacing: -1px;
  margin-bottom: 16px; max-width: 800px; margin-left: auto; margin-right: auto;
}}
.hero p {{
  font-size: 1.15rem; color: var(--text-muted); max-width: 640px;
  margin: 0 auto 32px;
}}
.hero .badge-bar {{
  display: inline-flex; gap: 12px; flex-wrap: wrap; justify-content: center;
}}
.hero .badge {{
  background: var(--bg-card); border: 1px solid var(--border);
  padding: 6px 16px; border-radius: 999px; font-size: 0.8rem;
  color: var(--text-muted); display: inline-flex; align-items: center; gap: 6px;
}}
.hero .badge::before {{
  content: ""; width: 8px; height: 8px; border-radius: 50%;
  background: var(--green); animation: pulse 2s infinite;
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.4; }}
}}

/* Live Stats Bar */
.stats-bar {{
  background: var(--bg-card); border-bottom: 1px solid var(--border);
  padding: 24px;
}}
.stats-inner {{
  max-width: var(--max-width); margin: 0 auto;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 24px;
}}
.stat {{
  text-align: center; padding: 16px;
  background: var(--bg-elevated); border-radius: 12px; border: 1px solid var(--border);
}}
.stat .value {{
  font-size: 1.6rem; font-weight: 700; color: var(--text);
  display: block; margin-bottom: 4px;
}}
.stat .label {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }}
.stat .change {{ font-size: 0.85rem; margin-top: 4px; }}

/* Sections */
section {{
  max-width: var(--max-width); margin: 0 auto; padding: 80px 24px;
}}
section h2 {{
  font-size: 2rem; font-weight: 700; margin-bottom: 16px;
}}
section .subtitle {{
  color: var(--text-muted); font-size: 1.05rem; max-width: 600px; margin-bottom: 48px;
}}

/* Value Props */
.values-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px;
}}
.value-card {{
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 16px; padding: 32px; transition: transform 0.2s, border-color 0.2s;
}}
.value-card:hover {{
  transform: translateY(-4px); border-color: var(--accent);
}}
.value-card .icon {{
  width: 48px; height: 48px; border-radius: 12px;
  background: linear-gradient(135deg, var(--accent), #8b5cf6);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem; margin-bottom: 20px;
}}
.value-card h3 {{ font-size: 1.15rem; margin-bottom: 10px; }}
.value-card p {{ color: var(--text-muted); font-size: 0.9rem; line-height: 1.5; }}

/* Reports */
.reports-grid {{
  display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px;
}}
.report-card {{
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 16px; padding: 24px;
}}
.report-header {{
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border);
}}
.report-header h4 {{ font-size: 1.1rem; font-weight: 600; }}
.badge.alert {{
  background: rgba(239,68,68,0.15); color: var(--red);
  border: 1px solid rgba(239,68,68,0.3); padding: 2px 10px;
  border-radius: 999px; font-size: 0.75rem; font-weight: 600;
}}
.report-grid {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
}}
.metric {{
  background: var(--bg-elevated); border-radius: 10px; padding: 12px;
  text-align: center;
}}
.metric .label {{
  display: block; font-size: 0.7rem; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;
}}
.metric .value {{ font-size: 1.05rem; font-weight: 600; }}
.pos-section {{ margin-top: 16px; }}
.pos-section h5 {{ font-size: 0.8rem; color: var(--text-muted); margin-bottom: 6px; text-transform: uppercase; }}
.pos-row {{
  display: flex; justify-content: space-between; padding: 4px 0;
  font-size: 0.85rem; border-bottom: 1px solid var(--border);
}}
.pos-row:last-child {{ border-bottom: none; }}
.pos-row .ticker {{ font-weight: 600; }}

/* Positions Table */
.table-wrap {{
  overflow-x: auto; background: var(--bg-card);
  border: 1px solid var(--border); border-radius: 16px;
}}
table {{
  width: 100%; border-collapse: collapse; font-size: 0.9rem;
}}
th, td {{ padding: 14px 18px; text-align: left; border-bottom: 1px solid var(--border); }}
th {{
  background: var(--bg-elevated); font-size: 0.75rem; text-transform: uppercase;
  letter-spacing: 0.5px; color: var(--text-muted); font-weight: 600;
}}
tr:hover {{ background: rgba(59,130,246,0.05); }}

/* Chart */
.chart-container {{
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 16px; padding: 24px; margin-bottom: 48px;
}}
.chart-container h3 {{ font-size: 1.1rem; margin-bottom: 16px; }}

/* CTA */
.cta-section {{
  background: linear-gradient(135deg, var(--accent), #8b5cf6);
  border-radius: 24px; padding: 64px 32px; text-align: center;
}}
.cta-section h2 {{ color: #fff; margin-bottom: 12px; }}
.cta-section p {{ color: rgba(255,255,255,0.8); max-width: 500px; margin: 0 auto 28px; }}
.cta-btn {{
  display: inline-block; background: #fff; color: var(--accent);
  padding: 14px 36px; border-radius: 999px; font-weight: 700;
  font-size: 1rem; transition: transform 0.2s, box-shadow 0.2s;
}}
.cta-btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); text-decoration: none; }}

/* Contact */
.contact-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 24px;
}}
.contact-card {{
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: 16px; padding: 28px; text-align: center;
}}
.contact-card .icon {{ font-size: 2rem; margin-bottom: 12px; }}
.contact-card h4 {{ margin-bottom: 8px; }}
.contact-card p {{ color: var(--text-muted); font-size: 0.9rem; }}

/* Footer */
footer {{
  border-top: 1px solid var(--border); padding: 40px 24px;
  text-align: center; color: var(--text-muted); font-size: 0.85rem;
}}
footer .footer-links {{
  display: flex; justify-content: center; gap: 24px; margin-bottom: 16px;
}}

/* Scrollbar */
::-webkit-scrollbar {{ width: 8px; }}
::-webkit-scrollbar-track {{ background: var(--bg); }}
::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}

@media (max-width: 768px) {{
  .hero h1 {{ font-size: 2rem; }}
  .report-grid {{ grid-template-columns: repeat(2, 1fr); }}
  .nav-links {{ display: none; }}
}}
</style>
</head>
<body>

<nav>
  <div class="nav-inner">
    <div class="logo">Apex<span>Fund</span></div>
    <ul class="nav-links">
      <li><a href="#about">About</a></li>
      <li><a href="#live">Live Portfolio</a></li>
      <li><a href="#reports">Daily Reports</a></li>
      <li><a href="#positions">Positions</a></li>
      <li><a href="#contact">Contact</a></li>
    </ul>
  </div>
</nav>

<!-- Hero -->
<div class="hero">
  <div class="badge-bar">
    <span class="badge">Autonomous AI Trading Active</span>
    <span class="badge" style="--green:{mood_color}">Portfolio Status: {"Healthy" if drawdown < 5 else "Cautious" if drawdown < 8 else "Under Review"}</span>
  </div>
  <h1>Autonomous AI Portfolio Management by Genesis</h1>
  <p>Apex Fund is a fully autonomous AI-driven portfolio management business under Genesis. Trades, risk management, and reporting are executed 24/7 by intelligent agents — with full transparency and zero emotional bias.</p>
</div>

<!-- Live Stats -->
<div class="stats-bar" id="live">
  <div class="stats-inner">
    <div class="stat">
      <span class="value">{fmt_usd(total_value)}</span>
      <span class="label">Portfolio Value</span>
      <span class="change" style="color:{mood_color}">Drawdown {drawdown:.2f}%</span>
    </div>
    <div class="stat">
      <span class="value">{fmt_usd(lp.get('cash_usdt', 0))}</span>
      <span class="label">Cash Reserve</span>
    </div>
    <div class="stat">
      <span class="value">{open_pos}</span>
      <span class="label">Open Positions</span>
    </div>
    <div class="stat">
      <span class="value">{fmt_usd(unrealized)}</span>
      <span class="label">Unrealized PnL</span>
      <span class="change" style="color:{'#10b981' if unrealized >= 0 else '#ef4444'}">{('+' if unrealized >= 0 else '') + f'{unrealized:.2f}'}</span>
    </div>
    <div class="stat">
      <span class="value">{fmt_usd(peak)}</span>
      <span class="label">Peak Value</span>
    </div>
    <div class="stat">
      <span class="value">Daily</span>
      <span class="label">Update Frequency</span>
    </div>
  </div>
</div>

<!-- About / Values -->
<section id="about">
  <h2>Why Apex Fund?</h2>
  <p class="subtitle">A Genesis autonomous business that delivers institutional-grade portfolio management without the institutional overhead.</p>
  <div class="values-grid">
    <div class="value-card">
      <div class="icon">&#9889;</div>
      <h3>24/7 Autonomous Execution</h3>
      <p>Our AI agents monitor markets continuously, identify opportunities, and execute trades around the clock — never sleeping, never hesitating.</p>
    </div>
    <div class="value-card">
      <div class="icon">&#128274;</div>
      <h3>Emotionless Risk Management</h3>
      <p>All positions are sized and managed by algorithms that enforce strict risk guardrails — no FOMO, no panic selling, no revenge trading.</p>
    </div>
    <div class="value-card">
      <div class="icon">&#128202;</div>
      <h3>Transparent Daily Reporting</h3>
      <p>Every position, every PnL movement, every portfolio update is logged and published automatically. Full visibility into your money.</p>
    </div>
    <div class="value-card">
      <div class="icon">&#9851;</div>
      <h3>Adaptive Portfolio Rebalancing</h3>
      <p>The portfolio self-adjusts based on market conditions and performance — rotating capital toward strength and away from weakness.</p>
    </div>
    <div class="value-card">
      <div class="icon">&#128640;</div>
      <h3>Scalable Automation</h3>
      <p>From a single portfolio to hundreds — the same autonomous infrastructure scales seamlessly without adding headcount.</p>
    </div>
    <div class="value-card">
      <div class="icon">&#129302;</div>
      <h3>Zero Human Bias</h3>
      <p>Decisions are data-driven and consistent. The agents apply the same disciplined criteria to every trade, every day.</p>
    </div>
  </div>
</section>

<!-- Chart -->
<section>
  <div class="chart-container">
    <h3>Portfolio Value — Last 14 Days</h3>
    <canvas id="valueChart" height="100"></canvas>
  </div>
</section>

<!-- Daily Reports -->
<section id="reports">
  <h2>Daily Performance Reports</h2>
  <p class="subtitle">Auto-generated every day at 02:00 server time. No human touches the keyboard.</p>
  <div class="reports-grid">
    {report_cards}
  </div>
</section>

<!-- Positions -->
<section id="positions">
  <h2>Current Positions</h2>
  <p class="subtitle">Live snapshot of all open holdings sorted by performance.</p>
  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Asset</th><th>Amount</th><th>Entry</th><th>Current</th><th>Value</th><th>PnL</th></tr>
      </thead>
      <tbody>
        {positions_table}
      </tbody>
    </table>
  </div>
</section>

<!-- CTA -->
<section>
  <div class="cta-section">
    <h2>Want Your Own Autonomous Fund?</h2>
    <p>We design, build, and deploy custom autonomous portfolio management systems for funds, family offices, and high-net-worth individuals.</p>
    <a href="#contact" class="cta-btn">Get in Touch</a>
  </div>
</section>

<!-- Contact -->
<section id="contact">
  <h2>Contact</h2>
  <p class="subtitle">All connections and inquiries route through our primary presence.</p>
  <div class="contact-grid">
    <div class="contact-card">
      <div class="icon">&#128100;</div>
      <h4>GitHub</h4>
      <p><a href="https://github.com/facelessmagister" target="_blank">github.com/facelessmagister</a></p>
      <p style="margin-top:4px; font-size:0.8rem;">Connections & collaborations found here</p>
    </div>
    <div class="contact-card">
      <div class="icon">&#127759;</div>
      <h4>Genesis Swarm</h4>
      <p>Apex Fund is one of 5 autonomous AI businesses operating under the Genesis umbrella.</p>
    </div>
    <div class="contact-card">
      <div class="icon">&#128161;</div>
      <h4>Services</h4>
      <p>Custom autonomous portfolio management automation, AI trading infrastructure, and reporting systems.</p>
    </div>
  </div>
</section>

<footer>
  <div class="footer-links">
    <a href="https://github.com/facelessmagister" target="_blank">GitHub</a>
    <a href="#about">About</a>
    <a href="#reports">Reports</a>
    <a href="#contact">Contact</a>
  </div>
  <p>Apex Fund — an autonomous AI business under Genesis. All portfolio management, trade execution, and reporting are performed autonomously by AI agents. This website updates automatically after each daily report cycle.</p>
  <p style="margin-top:8px;">&copy; {datetime.now().year} Apex Fund. Built by machines, for humans.</p>
</footer>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
const ctx = document.getElementById('valueChart').getContext('2d');
const gradient = ctx.createLinearGradient(0, 0, 0, 100);
gradient.addColorStop(0, 'rgba(59,130,246,0.3)');
gradient.addColorStop(1, 'rgba(59,130,246,0.0)');
new Chart(ctx, {{
  type: 'line',
  data: {{
    labels: {chart_labels_js},
    datasets: [{{
      label: 'Portfolio Value (USDT)',
      data: {chart_values_js},
      borderColor: '#3b82f6',
      backgroundColor: gradient,
      fill: true,
      tension: 0.4,
      pointRadius: 3,
      pointBackgroundColor: '#3b82f6',
      borderWidth: 2
    }}]
  }},
  options: {{
    responsive: true,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ grid: {{ color: '#232b3e' }}, ticks: {{ color: '#94a3b8' }} }},
      y: {{ grid: {{ color: '#232b3e' }}, ticks: {{ color: '#94a3b8' }} }}
    }}
  }}
}});
</script>

</body>
</html>
"""

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Generated {OUTPUT} ({len(html)} bytes)")
    print(f"Reports included: {len(reports)}")
    print(f"Latest portfolio value: {fmt_usd(total_value)}")
    return 0

if __name__ == '__main__':
    sys.exit(generate())
