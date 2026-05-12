DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RAC Dashboard</title>
  <style>
    :root {
      --sb: #0f172a; --sb-hover: #1e293b; --sb-active: #3b82f6; --sb-text: #94a3b8;
      --bg: #f1f5f9; --panel: #ffffff; --border: #e2e8f0;
      --text: #0f172a; --muted: #64748b; --ink: #1e293b;
      --good: #10b981; --warn: #f59e0b; --bad: #ef4444; --blue: #3b82f6;
      --sb-w: 220px;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font: 13px/1.5 system-ui,-apple-system,sans-serif; background: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }

    /* ── Sidebar ─────────────────────────────────────────── */
    .sb { width: var(--sb-w); background: var(--sb); display: flex; flex-direction: column; flex-shrink: 0; }
    .sb-logo { padding: 20px 18px 12px; border-bottom: 1px solid #1e293b; }
    .sb-logo h1 { color: #fff; font-size: 20px; font-weight: 800; letter-spacing: -0.5px; }
    .sb-logo .tagline { color: var(--sb-text); font-size: 11px; margin-top: 2px; }
    .sb-nav { flex: 1; padding: 10px 10px; overflow-y: auto; }
    .nav-section { color: #475569; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; padding: 14px 8px 6px; }
    .nav-item { display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: 7px; color: var(--sb-text); cursor: pointer; transition: all 0.15s; font-size: 13px; font-weight: 500; user-select: none; }
    .nav-item:hover { background: var(--sb-hover); color: #e2e8f0; }
    .nav-item.active { background: var(--sb-active); color: #fff; }
    .nav-item svg { width: 16px; height: 16px; flex-shrink: 0; }
    .sb-status { padding: 12px 14px; border-top: 1px solid #1e293b; display: flex; flex-direction: column; gap: 8px; }
    .sb-badge { display: flex; align-items: center; gap: 6px; font-size: 11px; }
    .dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
    .dot-green { background: var(--good); }
    .dot-red { background: var(--bad); }
    .dot-yellow { background: var(--warn); }

    /* ── Main area ───────────────────────────────────────── */
    .app { flex: 1; display: flex; flex-direction: column; min-width: 0; overflow: hidden; }

    /* ── Topbar ──────────────────────────────────────────── */
    .topbar { background: var(--panel); border-bottom: 1px solid var(--border); padding: 0 20px; height: 56px; display: flex; align-items: center; justify-content: space-between; flex-shrink: 0; gap: 16px; }
    .topbar-left { display: flex; align-items: center; gap: 16px; min-width: 0; }
    .page-title { font-size: 15px; font-weight: 700; color: var(--ink); white-space: nowrap; }
    .topbar-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
    #header-pnl { font-size: 18px; font-weight: 800; }
    #market-clock { font-size: 12px; }
    .chip { display: inline-flex; align-items: center; gap: 5px; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; }
    .chip-green { background: #ecfdf5; color: var(--good); }
    .chip-red { background: #fef2f2; color: var(--bad); }
    .chip-gray { background: #f1f5f9; color: var(--muted); }
    .chip-yellow { background: #fffbeb; color: var(--warn); }
    #last-refresh { font-size: 11px; color: var(--muted); }
    btn, button { border: 1px solid var(--border); background: #fff; color: var(--ink); border-radius: 7px; padding: 6px 12px; cursor: pointer; font: inherit; font-weight: 600; font-size: 12px; transition: background 0.12s; }
    button:hover { background: #f8fafc; }
    button.danger { background: var(--bad); color: #fff; border-color: var(--bad); }
    button.danger:hover { background: #dc2626; }
    button.primary { background: var(--blue); color: #fff; border-color: var(--blue); }
    button.sm { padding: 4px 8px; font-size: 11px; }

    /* ── Content ─────────────────────────────────────────── */
    .content { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
    .section { display: none; flex-direction: column; gap: 16px; }
    .section.active { display: flex; }

    /* ── Cards & Panels ──────────────────────────────────── */
    .card { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
    .card-header { padding: 12px 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; background: #fafbfc; }
    .card-title { font-size: 13px; font-weight: 700; color: var(--ink); }
    .card-body { padding: 14px 16px; }
    .card-body.no-pad { padding: 0; }

    /* ── KPI row ─────────────────────────────────────────── */
    .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
    .kpi { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }
    .kpi-label { font-size: 11px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-value { font-size: 24px; font-weight: 800; color: var(--ink); margin-top: 4px; line-height: 1; }
    .kpi-sub { font-size: 11px; margin-top: 5px; }

    /* ── Two-column grids ────────────────────────────────── */
    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
    .col-8-4 { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; }

    /* ── Tables ──────────────────────────────────────────── */
    table { width: 100%; border-collapse: collapse; }
    th { font-size: 11px; color: var(--muted); font-weight: 700; padding: 8px 12px; text-align: left; background: #fafbfc; border-bottom: 1px solid var(--border); }
    td { padding: 9px 12px; border-bottom: 1px solid #f1f5f9; font-size: 12px; vertical-align: middle; }
    tr:last-child td { border-bottom: none; }
    tr:hover td { background: #f8fafc; }

    /* ── Misc ────────────────────────────────────────────── */
    .muted { color: var(--muted); }
    .error { color: var(--bad); }
    .good { color: var(--good); }
    .warn { color: var(--warn); }
    .bad  { color: var(--bad);  }
    canvas { display: block; width: 100%; }
    input, select { border: 1px solid var(--border); border-radius: 6px; padding: 7px 10px; font: inherit; font-size: 12px; color: var(--text); background: #fff; width: 100%; }
    .field { display: flex; flex-direction: column; gap: 4px; }
    .field label { font-size: 11px; font-weight: 600; color: var(--muted); }
    .form-row { display: flex; gap: 10px; align-items: flex-end; flex-wrap: wrap; }
    .form-row .field { flex: 1; min-width: 120px; }
    .progress-track { background: #e2e8f0; border-radius: 4px; height: 6px; }
    .progress-fill { height: 6px; border-radius: 4px; transition: width 0.4s; }
    .pos-card { border: 1px solid var(--border); border-radius: 8px; padding: 14px; background: #fff; }
    .pos-row { display: flex; justify-content: space-between; align-items: flex-start; }
    .divider { height: 1px; background: var(--border); margin: 10px 0; }

    /* ── Responsive ──────────────────────────────────────── */
    @media(max-width:900px) {
      body { flex-direction: column; }
      .sb { width: 100%; height: auto; flex-direction: row; overflow-x: auto; }
      .sb-logo, .sb-status, .nav-section { display: none; }
      .sb-nav { display: flex; flex-direction: row; padding: 8px; gap: 4px; }
      .nav-item { padding: 7px 12px; white-space: nowrap; }
      .kpi-row { grid-template-columns: 1fr 1fr; }
      .grid-2, .grid-3, .col-8-4 { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<!-- ── Sidebar ─────────────────────────────────────────────── -->
<aside class="sb">
  <div class="sb-logo">
    <h1>RAC</h1>
    <div class="tagline">Robo Advisor · Autonomous Capital</div>
  </div>
  <nav class="sb-nav">
    <div class="nav-section">Trading</div>
    <div class="nav-item active" data-sec="overview">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>
      Overview
    </div>
    <div class="nav-item" data-sec="portfolio">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2"/></svg>
      Portfolio
    </div>
    <div class="nav-item" data-sec="trading">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
      Signals & Orders
    </div>
    <div class="nav-section">Intelligence</div>
    <div class="nav-item" data-sec="ml">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/></svg>
      Machine Learning
    </div>
    <div class="nav-item" data-sec="backtest">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-4.5"/></svg>
      Backtests
    </div>
    <div class="nav-section">Admin</div>
    <div class="nav-item" data-sec="system">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
      System
    </div>
  </nav>
  <div id="sb-prices" style="padding:10px 14px;border-top:1px solid #1e293b;display:flex;flex-direction:column;gap:5px"></div>
  <div class="sb-status">
    <div class="sb-badge"><div class="dot dot-green" id="sb-worker-dot"></div><span id="sb-worker-status" style="color:var(--sb-text);font-size:11px">Worker</span></div>
    <div class="sb-badge"><div class="dot" id="sb-ks-dot" style="background:var(--good)"></div><span id="sb-ks-status" style="color:var(--sb-text);font-size:11px">Kill Switch</span></div>
    <div style="color:#475569;font-size:10px" id="sb-refresh"></div>
  </div>
</aside>

<!-- ── Main app ─────────────────────────────────────────────── -->
<div class="app">
  <!-- Topbar -->
  <header class="topbar">
    <div class="topbar-left">
      <span class="page-title" id="page-title">Overview</span>
      <span id="market-clock"></span>
    </div>
    <div class="topbar-right">
      <span id="header-pnl"></span>
      <span id="last-refresh"></span>
      <button class="sm" onclick="refresh()">↻ Refresh</button>
      <button class="sm" onclick="markToMarket()">Mark to Market</button>
      <button class="sm danger" onclick="activateKillSwitch()">Kill Switch</button>
      <button class="sm" onclick="resetKillSwitch()">Reset KS</button>
    </div>
  </header>

  <!-- Content -->
  <main class="content">

    <!-- ═══ OVERVIEW ══════════════════════════════════════════ -->
    <section class="section active" id="s-overview">
      <!-- KPI row -->
      <div class="kpi-row" style="grid-template-columns:repeat(5,1fr)">
        <div class="kpi">
          <div class="kpi-label">NAV (RAC)</div>
          <div class="kpi-value" id="kpi-nav">—</div>
          <div class="kpi-sub" id="kpi-nav-sub"></div>
        </div>
        <div class="kpi">
          <div class="kpi-label">P&L Today</div>
          <div class="kpi-value" id="kpi-pnl">—</div>
          <div class="kpi-sub muted" id="kpi-pnl-sub"></div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Drawdown</div>
          <div class="kpi-value" id="kpi-dd">—</div>
          <div class="kpi-sub" id="kpi-dd-bar" style="margin-top:6px"></div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Alpaca Equity</div>
          <div class="kpi-value" id="kpi-equity">—</div>
          <div class="kpi-sub muted" id="kpi-equity-sub"></div>
        </div>
        <div class="kpi">
          <div class="kpi-label">Deployed</div>
          <div class="kpi-value" id="kpi-exposure">—</div>
          <div class="kpi-sub" id="kpi-exposure-bar" style="margin-top:6px"></div>
        </div>
      </div>

      <!-- Quick actions -->
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="sm" onclick="markToMarket()">↻ Mark to Market</button>
        <button class="sm" onclick="reconcileOrders()">⇄ Reconcile Orders</button>
        <button class="sm" onclick="checkConsistency()">✓ Check Consistency</button>
        <span id="quick-action-result" class="muted" style="font-size:11px;align-self:center"></span>
      </div>

      <!-- Daily P&L bar chart -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">Daily P&L — last 14 days</span>
          <span id="pnl-chart-total" class="muted" style="font-size:12px"></span>
        </div>
        <div class="card-body" style="padding:10px 16px">
          <canvas id="pnl-chart" style="height:120px"></canvas>
        </div>
      </div>

      <!-- Live Positions -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">Open Positions — Live</span>
          <span class="muted" style="font-size:11px" id="pos-count"></span>
        </div>
        <div class="card-body" id="live-positions"><span class="muted">Loading…</span></div>
      </div>

      <!-- NAV Chart -->
      <div class="card">
        <div class="card-header">
          <span class="card-title">NAV History</span>
          <div style="display:flex;gap:6px">
            <button class="sm" id="nav-7d"  onclick="setNavRange(7)">7d</button>
            <button class="sm" id="nav-30d" onclick="setNavRange(30)">30d</button>
            <button class="sm" id="nav-all" onclick="setNavRange(0)">All</button>
          </div>
        </div>
        <div class="card-body" style="padding:10px 16px">
          <canvas id="nav-chart" style="height:220px"></canvas>
        </div>
      </div>

      <!-- Broker status row -->
      <div class="grid-3">
        <div class="card">
          <div class="card-header"><span class="card-title">Mode</span></div>
          <div class="card-body"><span id="mode" class="kpi-value" style="font-size:16px">—</span><div class="muted" id="broker" style="font-size:11px;margin-top:4px"></div></div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Alpaca Account</span></div>
          <div class="card-body"><span id="equity" class="kpi-value" style="font-size:16px">—</span><div class="muted" id="cash" style="font-size:11px;margin-top:4px"></div></div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Local AI</span></div>
          <div class="card-body"><span id="ai" style="font-size:13px;font-weight:700">—</span><div class="muted" id="ai-models" style="font-size:11px;margin-top:4px"></div></div>
        </div>
      </div>
    </section>

    <!-- ═══ PORTFOLIO ═════════════════════════════════════════ -->
    <section class="section" id="s-portfolio">
      <div class="grid-2">
        <div class="card"><div class="card-header"><span class="card-title">Fills Today</span></div><div class="card-body no-pad" id="fills-today"><div class="card-body muted">Loading…</div></div></div>
        <div class="card"><div class="card-header"><span class="card-title">Fills This Week</span></div><div class="card-body no-pad" id="fills-week"><div class="card-body muted">Loading…</div></div></div>
      </div>

      <div class="col-8-4">
        <div class="card">
          <div class="card-header"><span class="card-title">Trade Outcomes</span></div>
          <div class="card-body no-pad" id="trade-outcomes"><div class="card-body muted">Loading…</div></div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Strategy P&L</span></div>
          <div class="card-body no-pad" id="strategy-summary"><div class="card-body muted">Loading…</div></div>
        </div>
      </div>

      <div class="grid-2">
        <div class="card"><div class="card-header"><span class="card-title">RAC Positions</span></div><div class="card-body no-pad" id="portfolio-positions"><div class="card-body muted">Loading…</div></div></div>
        <div class="card"><div class="card-header"><span class="card-title">Broker Positions</span></div><div class="card-body no-pad" id="broker-positions"><div class="card-body muted">Loading…</div></div></div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Portfolio Consistency</span>
          <button class="sm" onclick="checkConsistency()">Check Now</button>
        </div>
        <div class="card-body" id="portfolio-consistency"><span class="muted">Click Check Now to verify RAC vs Alpaca positions</span></div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Mark to Market</span>
          <button class="sm primary" onclick="markToMarket()">Run MTM</button>
        </div>
        <div class="card-body" id="mark-to-market"><span class="muted">Click Run MTM to reprice positions from Alpaca</span></div>
      </div>
    </section>

    <!-- ═══ SIGNALS & ORDERS ══════════════════════════════════ -->
    <section class="section" id="s-trading">
      <div class="card">
        <div class="card-header"><span class="card-title">Strategy Performance (fills)</span></div>
        <div class="card-body no-pad" id="strategy-performance"><div class="card-body muted">Loading…</div></div>
      </div>

      <div class="grid-2">
        <div class="card"><div class="card-header"><span class="card-title">Latest Signals</span></div><div class="card-body no-pad" id="signals"><div class="card-body muted">Loading…</div></div></div>
        <div class="card"><div class="card-header"><span class="card-title">Latest Orders</span></div><div class="card-body no-pad" id="orders"><div class="card-body muted">Loading…</div></div></div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Paper Analysis Pipeline</span>
        </div>
        <div class="card-body">
          <div class="form-row">
            <div class="field"><label>Symbol</label><input id="pipeline-symbol" value="AAPL"></div>
            <div class="field"><label>Timeframe</label><input id="pipeline-timeframe" value="1Day"></div>
            <div class="field"><label>Strategy</label>
              <select id="pipeline-strategy">
                <option value="trend_following_v1">trend_following_v1</option>
                <option value="mean_reversion_v1">mean_reversion_v1</option>
              </select>
            </div>
            <div class="field"><label>Start</label><input id="pipeline-start" type="date"></div>
            <div class="field"><label>End</label><input id="pipeline-end" type="date"></div>
            <button onclick="runPipeline()">Run</button>
          </div>
          <div id="pipeline-result" style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)"><span class="muted">No run in this session</span></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Order Reconciliation</span>
          <button class="sm" onclick="reconcileOrders()">Reconcile</button>
        </div>
        <div class="card-body" id="reconciliation"><span class="muted">Click Reconcile to sync submitted orders with Alpaca</span></div>
      </div>
    </section>

    <!-- ═══ MACHINE LEARNING ══════════════════════════════════ -->
    <section class="section" id="s-ml">
      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <span class="card-title">Signal Labels</span>
            <button class="sm" onclick="runLabel()">Label Now</button>
          </div>
          <div class="card-body" id="ml-stats"><span class="muted">Loading…</span></div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Win / Loss Distribution</span></div>
          <div class="card-body" style="padding:10px 16px">
            <canvas id="wl-chart" style="height:180px"></canvas>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <span class="card-title">Feature Importance</span>
          <button class="sm primary" onclick="runTrain()">Train Model</button>
        </div>
        <div class="card-body" id="ml-train-result">
          <canvas id="fi-chart" style="height:200px"></canvas>
        </div>
      </div>
    </section>

    <!-- ═══ BACKTESTS ═════════════════════════════════════════ -->
    <section class="section" id="s-backtest">
      <div class="card">
        <div class="card-header"><span class="card-title">Backtest History</span></div>
        <div class="card-body no-pad" id="backtests"><div class="card-body muted">Loading…</div></div>
      </div>
    </section>

    <!-- ═══ SYSTEM ════════════════════════════════════════════ -->
    <section class="section" id="s-system">
      <div class="grid-2">
        <div class="card">
          <div class="card-header"><span class="card-title">Kill Switch</span></div>
          <div class="card-body">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
              <span id="kill" style="font-size:14px;font-weight:700">—</span>
              <span id="kill-reason" class="muted" style="font-size:12px"></span>
            </div>
            <div style="display:flex;gap:8px">
              <button class="danger" onclick="activateKillSwitch()">Activate</button>
              <button onclick="resetKillSwitch()">Reset</button>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Bootstrap</span></div>
          <div class="card-body">
            <p class="muted" style="font-size:12px;margin-bottom:12px">Run DB migrations. Safe to run multiple times.</p>
            <button onclick="doBootstrap()">Run Bootstrap</button>
            <div id="bootstrap-result" style="margin-top:8px"></div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">Worker Config <span class="muted" style="font-weight:400">— applies on next cycle</span></span></div>
        <div class="card-body">
          <div class="form-row">
            <div class="field" style="max-width:160px"><label>Min Confidence (0–1)</label><input id="cfg-confidence" type="number" min="0" max="1" step="0.05" value="0.5"></div>
            <div class="field" style="max-width:130px"><label>Timeframe</label>
              <select id="cfg-timeframe"><option value="1Min">1Min</option><option value="5Min" selected>5Min</option><option value="15Min">15Min</option><option value="1Day">1Day</option></select>
            </div>
            <div class="field" style="max-width:160px"><label>Max Signal Age (s)</label><input id="cfg-maxage" type="number" min="60" step="60" value="1200"></div>
            <div class="field"><label>Symbols</label><input id="cfg-symbols" value="AAPL,MSFT,SPY"></div>
            <button onclick="saveWorkerConfig()">Save</button>
          </div>
          <div id="cfg-result" style="margin-top:8px"></div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">Audit Trail</span></div>
        <div class="card-body no-pad" id="audit-trail"><div class="card-body muted">Loading…</div></div>
      </div>
    </section>

  </main><!-- end .content -->
</div><!-- end .app -->

<script>
// ── Utilities ───────────────────────────────────────────────
const $ = id => document.getElementById(id);
const fmtMoney = v => { const n=Number(v); return Number.isFinite(n)?n.toLocaleString(undefined,{style:'currency',currency:'USD'}):'-'; };
const fmtNum   = v => { const n=Number(v); return Number.isFinite(n)?n.toLocaleString(undefined,{maximumFractionDigits:4}):'-'; };
const fmtPct   = v => { const n=Number(v); return Number.isFinite(n)?(n>=0?'+':'')+n.toFixed(2)+'%':'-'; };
const isoDate  = d => { const dt=new Date(); dt.setDate(dt.getDate()-d); return dt.toISOString().slice(0,10); };
const unwrap   = s => s&&s.ok?s.data:null;
const errMsg   = s => s&&!s.ok?`<span class="error">${s.error}</span>`:`<span class="muted">No data</span>`;

function rows(items, cols) {
  if (!items||!items.length) return '<div style="padding:12px" class="muted">No data</div>';
  return `<table><thead><tr>${cols.map(c=>`<th>${c.label}</th>`).join('')}</tr></thead><tbody>`+
    items.map(r=>`<tr>${cols.map(c=>`<td>${c.render?c.render(r):(r[c.key]??'-')}</td>`).join('')}</tr>`).join('')+
    `</tbody></table>`;
}

// ── Navigation ──────────────────────────────────────────────
const TITLES = {overview:'Overview',portfolio:'Portfolio',trading:'Signals & Orders',ml:'Machine Learning',backtest:'Backtests',system:'System'};
let currentSection = 'overview';

document.querySelectorAll('.nav-item[data-sec]').forEach(el => {
  el.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
    document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
    el.classList.add('active');
    currentSection = el.dataset.sec;
    $('s-'+currentSection).classList.add('active');
    $('page-title').textContent = TITLES[currentSection]||currentSection;
    loadSection(currentSection);
  });
});

function loadSection(sec) {
  if (sec==='ml')      { loadMlStats(); }
  if (sec==='backtest'){ loadBacktests(); }
  if (sec==='system')  { loadAuditTrail(); loadWorkerConfig(); }
  if (sec==='portfolio'){ loadFills(); loadTradeOutcomes(); }
  if (sec==='trading') { loadStrategyPerformance(); }
}

// ── Market clock ────────────────────────────────────────────
const BASELINE = 100000;
function isDST(d){const j=new Date(d.getFullYear(),0,1),l=new Date(d.getFullYear(),6,1);return d.getTimezoneOffset()<Math.max(j.getTimezoneOffset(),l.getTimezoneOffset());}
function toET(d){const o=isDST(d)?-4:-5;return new Date(d.getTime()+(d.getTimezoneOffset()+o*60)*60000);}
function fmtCd(ms){if(ms<=0)return'0m';const h=Math.floor(ms/3600000),m=Math.floor((ms%3600000)/60000);return h>0?`${h}h ${m}m`:`${m}m`;}
function updateClock(){
  const now=new Date(),et=toET(now),d=et.getDay(),min=et.getHours()*60+et.getMinutes(),O=570,C=960;
  let badge,sub,dotCls;
  if(d===0||d===6){badge='WEEKEND';dotCls='chip-gray';sub=`Opens in ${fmtCd(((d===6?2:1)*1440+O-min)*60000)}`;}
  else if(min<O){badge='PRE-MARKET';dotCls='chip-yellow';sub=`Opens in ${fmtCd((O-min)*60000)}`;}
  else if(min<C){badge='OPEN';dotCls='chip-green';sub=`Closes in ${fmtCd((C-min)*60000)}`;}
  else{badge='AFTER-HOURS';dotCls='chip-gray';sub=`Opens in ${fmtCd((O+1440-min)*60000)}`;}
  $('market-clock').innerHTML=`<span class="chip ${dotCls}">● ${badge}</span> <span class="muted" style="font-size:11px">${sub}</span>`;
}
setInterval(updateClock,30000); updateClock();

function updateHeaderPnl(equity){
  if(!equity)return;
  const pnl=equity-BASELINE,pct=pnl/BASELINE*100,sign=pnl>=0?'+':'',col=pnl>=0?'var(--good)':'var(--bad)';
  $('header-pnl').innerHTML=`<span style="color:${col};font-weight:800">${sign}${fmtMoney(pnl)} <span style="font-size:12px">(${sign}${pct.toFixed(2)}%)</span></span>`;
}

// ── Main refresh ────────────────────────────────────────────
async function refresh(){
  const resp=await fetch('/dashboard/data',{cache:'no-store'});
  const data=await resp.json();
  const caps=unwrap(data.capabilities)||{};
  const kill=unwrap(data.kill_switch)||{};
  const ai=unwrap(data.ai)||{};
  const acct=unwrap(data.broker_account);
  const snap=unwrap(data.portfolio_snapshot);
  const hist=unwrap(data.portfolio_history);
  const racPos=unwrap(data.portfolio_positions);
  const brkPos=unwrap(data.broker_positions);
  const cons=unwrap(data.portfolio_consistency);
  const sigs=unwrap(data.signals);
  const ords=unwrap(data.orders);

  const ts=new Date().toLocaleTimeString();
  $('last-refresh').textContent=`Updated ${ts}`;
  $('sb-refresh').textContent=ts;

  // Sidebar status
  $('sb-worker-dot').style.background='var(--good)';
  $('sb-worker-status').textContent=`Worker · ${caps.trading_mode||'-'}`;
  const ksActive=kill.active;
  $('sb-ks-dot').style.background=ksActive?'var(--bad)':'var(--good)';
  $('sb-ks-status').textContent=ksActive?'Kill Switch ACTIVE':'Kill Switch off';

  // Topbar
  if(acct) updateHeaderPnl(acct.equity);

  // Kill switch
  $('kill').innerHTML=`<span style="color:${ksActive?'var(--bad)':'var(--good)'}">${ksActive?'● ACTIVE':'● inactive'}</span>`;
  $('kill-reason').textContent=kill.reason||'';

  // Overview KPIs
  if(snap){
    const nav=Number(snap.nav),pnl=Number(snap.pnl_daily),dd=Math.max(0,Number(snap.drawdown)||0);
    const pnlCol=pnl>=0?'var(--good)':'var(--bad)',ddCol=dd<2?'var(--good)':dd<4?'var(--warn)':'var(--bad)';
    $('kpi-nav').textContent=fmtMoney(nav);
    $('kpi-nav-sub').innerHTML=`<span class="muted">cash ${fmtMoney(snap.cash)}</span>`;
    $('kpi-pnl').innerHTML=`<span style="color:${pnlCol}">${pnl>=0?'+':''}${fmtMoney(pnl)}</span>`;
    $('kpi-dd').innerHTML=`<span style="color:${ddCol}">${dd.toFixed(2)}%</span>`;
    $('kpi-dd-bar').innerHTML=`<div class="progress-track"><div class="progress-fill" style="width:${Math.min(dd/5*100,100)}%;background:${ddCol}"></div></div>`;
  }
  if(acct){
    const eq=Number(acct.equity),cash=Number(acct.cash);
    const pnl=eq-BASELINE,col=pnl>=0?'var(--good)':'var(--bad)';
    const deployed=eq>0?(eq-cash)/eq*100:0;
    const depCol=deployed>80?'var(--bad)':deployed>50?'var(--warn)':'var(--good)';
    $('kpi-equity').textContent=fmtMoney(eq);
    $('kpi-equity-sub').innerHTML=`<span style="color:${col}">${pnl>=0?'+':''}${fmtMoney(pnl)} vs $100k</span>`;
    $('kpi-exposure').innerHTML=`<span style="color:${depCol}">${deployed.toFixed(1)}%</span>`;
    $('kpi-exposure-bar').innerHTML=`<div class="progress-track"><div class="progress-fill" style="width:${Math.min(deployed,100)}%;background:${depCol}"></div></div><div class="muted" style="font-size:10px;margin-top:2px">${fmtMoney(eq-cash)} deployed</div>`;
    $('equity').textContent=fmtMoney(eq);
    $('cash').textContent=`cash ${fmtMoney(acct.cash)} · buying power ${fmtMoney(acct.buying_power)}`;
  }
  $('mode').textContent=caps.trading_mode||'-';
  $('broker').textContent=`${caps.broker_configured||'-'} / ${caps.broker_status||'-'}`;
  $('ai').innerHTML=`<span style="color:${ai.status==='available'?'var(--good)':'var(--muted)'}">${ai.status||'unavailable'}</span>`;
  $('ai-models').textContent=(ai.models||[]).join(', ')||'—';

  // Signals & Orders
  $('signals').innerHTML=rows(sigs,[
    {label:'Time',render:x=>new Date(x.time).toLocaleTimeString()},
    {label:'Symbol',key:'symbol'},
    {label:'Dir',render:x=>{const c=x.direction==='buy'?'good':x.direction==='sell'?'bad':'muted';return`<span class="${c}" style="font-weight:700">${x.direction.toUpperCase()}</span>`;}},
    {label:'Conf',render:x=>{const v=Number(x.confidence),c=v>=0.7?'good':v>=0.5?'warn':'muted';return`<span class="${c}">${v.toFixed(3)}</span>`;}},
    {label:'Strategy',render:x=>x.strategy_id.replace('_v1','')},
  ]);
  $('orders').innerHTML=rows(ords,[
    {label:'Time',render:x=>new Date(x.created_at).toLocaleTimeString()},
    {label:'Symbol',key:'symbol'},
    {label:'Side',render:x=>`<span class="${x.side==='buy'?'good':'bad'}" style="font-weight:700">${x.side.toUpperCase()}</span>`},
    {label:'Status',render:x=>{const c=x.status==='filled'?'good':x.status==='submitted'?'warn':'muted';return`<span class="${c}">${x.status}</span>`;}},
    {label:'Price',render:x=>fmtMoney(x.filled_price||x.estimated_price)},
  ]);

  // Portfolio positions
  $('portfolio-positions').innerHTML=rows(racPos,[
    {label:'Symbol',key:'symbol'},
    {label:'Qty',render:x=>fmtNum(x.quantity)},
    {label:'Avg',render:x=>fmtMoney(x.average_price)},
    {label:'Value',render:x=>fmtMoney(x.market_value)},
  ]);
  $('broker-positions').innerHTML=rows(brkPos,[
    {label:'Symbol',key:'symbol'},
    {label:'Qty',render:x=>fmtNum(x.quantity)},
    {label:'Value',render:x=>fmtMoney(x.market_value)},
  ]);

  // Consistency
  if(cons) renderConsistency(cons);

  // Charts
  drawNavChart(hist||[]);
  loadDailyPnl();

  // Sidebar ticker
  loadLivePositions().then(() => {
    updateSidebarPrices(_lastLivePos, brkPos);
  });

  // Section-specific
  if(currentSection==='portfolio') { loadFills(); loadTradeOutcomes(); }
  if(currentSection==='trading')   { loadStrategyPerformance(); }
  if(currentSection==='ml')        { loadMlStats(); }
  if(currentSection==='system')    { loadAuditTrail(); loadWorkerConfig(); }
  if(currentSection==='backtest')  { loadBacktests(); }
}

// ── Sidebar price ticker ─────────────────────────────────────
function updateSidebarPrices(livePositions, brokerPositions) {
  const sb = $('sb-prices');
  if (!sb) return;
  // Combine: show prices from live positions + broker positions without a RAC position
  const shown = {};
  (livePositions || []).forEach(p => {
    shown[p.symbol] = {
      price: p.current_price,
      pnl_pct: p.pnl_pct,
      has_position: true,
    };
  });
  (brokerPositions || []).forEach(p => {
    if (!shown[p.symbol]) shown[p.symbol] = { price: p.market_value / p.quantity, pnl_pct: null, has_position: true };
  });
  if (!Object.keys(shown).length) { sb.innerHTML = ''; return; }
  sb.innerHTML = Object.entries(shown).map(([sym, d]) => {
    const col = d.pnl_pct == null ? '#94a3b8' : d.pnl_pct >= 0 ? '#10b981' : '#ef4444';
    const pct = d.pnl_pct != null ? ` <span style="color:${col};font-size:10px">${d.pnl_pct >= 0 ? '+' : ''}${Number(d.pnl_pct).toFixed(2)}%</span>` : '';
    return `<div style="display:flex;justify-content:space-between;align-items:center">
      <span style="color:#94a3b8;font-size:11px;font-weight:600">${sym}</span>
      <span style="color:#e2e8f0;font-size:11px;font-weight:700">${fmtMoney(d.price)}${pct}</span>
    </div>`;
  }).join('');
}

// ── Daily P&L bar chart ───────────────────────────────────────
let _lastDailyPnl = [];
async function loadDailyPnl() {
  try {
    const r = await fetch('/portfolio/daily-pnl?environment=paper&days=14', { cache: 'no-store' });
    _lastDailyPnl = await r.json();
    drawPnlChart(_lastDailyPnl);
  } catch (_) {}
}
function drawPnlChart(days) {
  const cv = $('pnl-chart');
  if (!cv || !days.length) return;
  const sc = window.devicePixelRatio || 1, rc = cv.getBoundingClientRect();
  cv.width = Math.max(300, Math.floor(rc.width * sc));
  cv.height = Math.floor(120 * sc);
  const ctx = cv.getContext('2d');
  ctx.scale(sc, sc);
  const W = cv.width / sc, H = cv.height / sc;
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H);

  const pnls = days.map(d => d.pnl);
  const maxAbs = Math.max(...pnls.map(Math.abs), 1);
  const PT = 12, PB = 22, PL = 10, PR = 10;
  const chartH = H - PT - PB, chartW = W - PL - PR;
  const barW = Math.max(4, chartW / days.length - 3);
  const totalPnl = pnls.reduce((a, b) => a + b, 0);
  const tot = $('pnl-chart-total');
  if (tot) {
    const col = totalPnl >= 0 ? 'var(--good)' : 'var(--bad)';
    tot.innerHTML = `<span style="color:${col};font-weight:700">${totalPnl >= 0 ? '+' : ''}${fmtMoney(totalPnl)} (14d)</span>`;
  }

  // Zero line
  const zeroY = PT + chartH / 2;
  ctx.strokeStyle = '#e2e8f0'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(PL, zeroY); ctx.lineTo(W - PR, zeroY); ctx.stroke();

  days.forEach((d, i) => {
    const x = PL + i * (chartW / days.length) + (chartW / days.length - barW) / 2;
    const pct = d.pnl / maxAbs;
    const barH = Math.max(2, Math.abs(pct) * (chartH / 2 - 4));
    const positive = d.pnl >= 0;
    const y = positive ? zeroY - barH : zeroY;
    ctx.fillStyle = positive ? '#10b981' : '#ef4444';
    ctx.fillRect(x, y, barW, barH);

    // Date label
    const dt = new Date(d.date + 'T12:00:00');
    const lbl = `${dt.getMonth() + 1}/${dt.getDate()}`;
    ctx.fillStyle = '#94a3b8'; ctx.font = '9px system-ui'; ctx.textAlign = 'center';
    ctx.fillText(lbl, x + barW / 2, H - PB + 12);
  });
}

// ── Live Positions ──────────────────────────────────────────
let _lastLivePos = [];
async function loadLivePositions(){
  try{
    const r=await fetch('/portfolio/live-positions?environment=paper',{cache:'no-store'});
    const data=await r.json();
    _lastLivePos = data;
    $('pos-count').textContent=data.length?`${data.length} open`:'no positions';
    if(!data.length){$('live-positions').innerHTML='<span class="muted">No open positions</span>';return;}
    $('live-positions').innerHTML='<div style="display:flex;flex-direction:column;gap:10px">'+data.map(p=>{
      const pnlCol=p.unrealized_pnl>=0?'var(--good)':'var(--bad)',s=p.unrealized_pnl>=0?'+':'';
      const prog=p.progress_pct!=null?p.progress_pct:null;
      const fc=prog!=null?(prog>66?'var(--good)':prog>33?'var(--warn)':'var(--bad)'):'var(--muted)';
      return`<div class="pos-card">
        <div class="pos-row">
          <div><span style="font-size:16px;font-weight:800">${p.symbol}</span> <span class="muted" style="font-size:12px">${fmtNum(p.quantity)} sh</span></div>
          <div style="text-align:right"><div style="font-size:16px;font-weight:800;color:${pnlCol}">${s}${fmtMoney(p.unrealized_pnl)} <span style="font-size:11px">(${s}${p.pnl_pct.toFixed(2)}%)</span></div>
          <div class="muted" style="font-size:11px"><span style="color:var(--bad)">SL ${(p.dist_to_sl_pct||0).toFixed(2)}%</span> · <span style="color:var(--good)">TP ${(p.dist_to_tp_pct||0).toFixed(2)}%</span></div></div>
        </div>
        <div class="muted" style="font-size:11px;margin-top:6px;display:flex;gap:16px">
          <span>Entry ${fmtMoney(p.avg_entry_price)}</span><span>Now ${fmtMoney(p.current_price)}</span><span>Value ${fmtMoney(p.market_value)}</span>
        </div>
        ${prog!=null?`<div class="progress-track" style="margin-top:8px"><div class="progress-fill" style="width:${prog}%;background:${fc}"></div></div>
        <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--muted);margin-top:2px"><span style="color:var(--bad)">SL ${fmtMoney(p.stop_loss_price)}</span><span>${prog.toFixed(0)}% to TP</span><span style="color:var(--good)">TP ${fmtMoney(p.take_profit_price)}</span></div>`:''}
      </div>`;
    }).join('')+'</div>';
  }catch(e){$('live-positions').innerHTML=`<span class="error">${e.message}</span>`;}
}

// ── NAV Chart ───────────────────────────────────────────────
let _navPts=[],_navRange=0;
async function loadNavHistory(){
  const lim=_navRange===0?1000:_navRange<=7?300:700;
  try{const r=await fetch(`/portfolio/history?environment=paper&limit=${lim}`,{cache:'no-store'});_navPts=await r.json();}catch(_){_navPts=[];}
  drawNavChart(_navPts);
}
function setNavRange(d){
  _navRange=d;
  ['7d','30d','all'].forEach(k=>{ const b=$('nav-'+k); if(b){b.style.fontWeight='';b.style.background='';} });
  const k=d===7?'7d':d===30?'30d':'all'; const b=$('nav-'+k);
  if(b){b.style.fontWeight='800';b.style.background='#eff6ff';}
  loadNavHistory();
}
function drawNavChart(all){
  _navPts=all||[];
  let pts=_navPts;
  if(_navRange>0){const c=Date.now()-_navRange*86400000;pts=_navPts.filter(p=>new Date(p.time).getTime()>=c);}
  const cv=$('nav-chart'); if(!cv)return;
  const rc=cv.getBoundingClientRect(),sc=window.devicePixelRatio||1;
  cv.width=Math.max(400,Math.floor(rc.width*sc)); cv.height=Math.max(220,Math.floor(220*sc));
  const ctx=cv.getContext('2d'); ctx.scale(sc,sc);
  const W=cv.width/sc,H=cv.height/sc;
  ctx.clearRect(0,0,W,H); ctx.fillStyle='#fff'; ctx.fillRect(0,0,W,H);
  const navV=pts.map(p=>Number(p.nav)).filter(Number.isFinite);
  if(navV.length<2){ctx.fillStyle='#94a3b8';ctx.font='13px system-ui';ctx.fillText('No NAV history yet',16,28);return;}
  const PL=72,PR=12,PT=24,PB=36,CW=W-PL-PR,CH=H-PT-PB;
  const mn=Math.min(...navV),mx=Math.max(...navV),rn=mx===mn?1:mx-mn;
  ctx.font='10px system-ui'; ctx.textAlign='right'; ctx.fillStyle='#94a3b8';
  for(let i=0;i<=4;i++){
    const v=mn+(rn/4)*i,y=PT+CH-(i/4)*CH;
    ctx.strokeStyle='#f1f5f9'; ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(PL,y);ctx.lineTo(PL+CW,y);ctx.stroke();
    ctx.fillText(fmtMoney(v),PL-4,y+3);
  }
  const xn=Math.min(6,pts.length-1);
  ctx.textAlign='center';
  for(let i=0;i<=xn;i++){
    const idx=Math.round(i*(pts.length-1)/xn),x=PL+(idx/(pts.length-1))*CW;
    const dt=new Date(pts[idx].time);
    const hh=String(dt.getHours()).padStart(2,'0'),mm=String(dt.getMinutes()).padStart(2,'0');
    ctx.fillText(`${dt.getMonth()+1}/${dt.getDate()} ${hh}:${mm}`,x,H-PB+14);
  }
  const pos=navV[navV.length-1]>=navV[0];
  const lc=pos?'#10b981':'#ef4444',fc=pos?'rgba(16,185,129,0.08)':'rgba(239,68,68,0.06)';
  ctx.beginPath();
  navV.forEach((v,i)=>{const x=PL+(i/(navV.length-1))*CW,y=PT+CH-((v-mn)/rn)*CH;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);});
  ctx.strokeStyle=lc; ctx.lineWidth=2; ctx.stroke();
  ctx.lineTo(PL+CW,PT+CH); ctx.lineTo(PL,PT+CH); ctx.closePath(); ctx.fillStyle=fc; ctx.fill();
  ctx.fillStyle='#0f172a'; ctx.font='bold 13px system-ui'; ctx.textAlign='left';
  ctx.fillText(fmtMoney(navV[navV.length-1]),PL+4,PT+16);
  // Tooltip
  cv._pts=pts; cv._meta={PL,PR,PT,PB,CW,CH,mn,rn};
}
(()=>{
  const cv=$('nav-chart'); if(!cv)return;
  const tt=document.createElement('div');
  tt.style.cssText='position:fixed;background:#0f172a;color:#f1f5f9;padding:6px 10px;border-radius:6px;font-size:12px;pointer-events:none;display:none;z-index:99';
  document.body.appendChild(tt);
  cv.addEventListener('mousemove',e=>{
    const pts=cv._pts,m=cv._meta;
    if(!pts||pts.length<2||!m)return;
    const rc=cv.getBoundingClientRect(),mx=e.clientX-rc.left;
    if(mx<m.PL||mx>m.PL+m.CW){tt.style.display='none';return;}
    const idx=Math.round((mx-m.PL)/m.CW*(pts.length-1));
    const pt=pts[Math.max(0,Math.min(idx,pts.length-1))];
    const dt=new Date(pt.time);
    tt.innerHTML=`<b>${fmtMoney(pt.nav)}</b><br>${dt.toLocaleDateString()} ${dt.toLocaleTimeString()}`;
    tt.style.display='block'; tt.style.left=(e.clientX+12)+'px'; tt.style.top=(e.clientY-8)+'px';
  });
  cv.addEventListener('mouseleave',()=>{tt.style.display='none';});
})();

// ── Fills ────────────────────────────────────────────────────
async function loadFills(){
  const cols=[
    {label:'Time',render:x=>new Date(x.created_at).toLocaleTimeString()},
    {label:'Symbol',key:'symbol'},
    {label:'Side',render:x=>`<span class="${x.side==='buy'?'good':'bad'}" style="font-weight:700">${x.side.toUpperCase()}</span>`},
    {label:'Qty',render:x=>fmtNum(x.quantity)},
    {label:'Price',render:x=>fmtMoney(x.price)},
    {label:'Notional',render:x=>fmtMoney(x.notional)},
  ];
  try{
    const [r1,r2]=await Promise.all([
      fetch('/portfolio/fills?environment=paper&days=1',{cache:'no-store'}),
      fetch('/portfolio/fills?environment=paper&days=7',{cache:'no-store'}),
    ]);
    $('fills-today').innerHTML=rows(await r1.json(),cols);
    $('fills-week').innerHTML=rows(await r2.json(),cols);
  }catch(e){$('fills-today').innerHTML=`<span class="error card-body">${e.message}</span>`;}
}

// ── Trade Outcomes ──────────────────────────────────────────
async function loadTradeOutcomes(){
  try{
    const [r1,r2]=await Promise.all([
      fetch('/trade-outcomes?environment=paper&limit=15',{cache:'no-store'}),
      fetch('/trade-outcomes/summary?environment=paper',{cache:'no-store'}),
    ]);
    const outs=await r1.json(),sum=await r2.json();
    $('trade-outcomes').innerHTML=rows(outs,[
      {label:'Closed',render:x=>new Date(x.closed_at).toLocaleTimeString()},
      {label:'Symbol',key:'symbol'},
      {label:'Strategy',render:x=>x.strategy_id.replace('_v1','')},
      {label:'Reason',key:'close_reason'},
      {label:'Entry',render:x=>fmtMoney(x.open_price)},
      {label:'Exit',render:x=>fmtMoney(x.close_price)},
      {label:'P&L',render:x=>{const n=Number(x.realized_pnl),p=Number(x.pnl_pct),c=n>=0?'good':'bad';return`<span class="${c}">${fmtMoney(n)} (${p>=0?'+':''}${p.toFixed(2)}%)</span>`;}},
      {label:'Dur',render:x=>{const s=Number(x.duration_seconds);return s<3600?`${Math.round(s/60)}m`:`${(s/3600).toFixed(1)}h`;}},
    ]);
    $('strategy-summary').innerHTML=rows(sum,[
      {label:'Strategy',render:x=>x.strategy_id.replace('_v1','')},
      {label:'W/L',render:x=>`${x.wins}/${x.losses}`},
      {label:'P&L',render:x=>{const n=Number(x.total_pnl),c=n>=0?'good':'bad';return`<span class="${c}">${fmtMoney(n)}</span>`;}},
      {label:'Avg %',render:x=>{const p=Number(x.avg_pnl_pct),c=p>=0?'good':'bad';return`<span class="${c}">${p>=0?'+':''}${p.toFixed(2)}%</span>`;}},
    ]);
  }catch(e){$('trade-outcomes').innerHTML=`<span class="error">${e.message}</span>`;}
}

// ── Strategy Performance ─────────────────────────────────────
async function loadStrategyPerformance(){
  try{
    const r=await fetch('/strategies/performance?environment=paper',{cache:'no-store'});
    const data=await r.json();
    $('strategy-performance').innerHTML=rows(data,[
      {label:'Strategy',key:'strategy_id'},
      {label:'Buys',key:'buys'},{label:'Sells',key:'sells'},
      {label:'Bought',render:x=>fmtMoney(x.buy_notional)},
      {label:'Sold',render:x=>fmtMoney(x.sell_notional)},
      {label:'Realized P&L',render:x=>{const n=Number(x.realized_pnl),c=n>=0?'good':'bad';return`<span class="${c}">${fmtMoney(n)}</span>`;}},
    ]);
  }catch(e){$('strategy-performance').innerHTML=`<span class="error">${e.message}</span>`;}
}

// ── ML ───────────────────────────────────────────────────────
let _mlImportance={};
async function loadMlStats(){
  try{
    const r=await fetch('/ml/stats',{cache:'no-store'});
    const d=await r.json();
    const total=Number(d.total)||0;
    $('ml-stats').innerHTML=`
      <div class="kpi-row" style="grid-template-columns:repeat(3,1fr);margin-bottom:12px">
        <div class="kpi" style="padding:12px"><div class="kpi-label">Total Labeled</div><div class="kpi-value" style="font-size:18px">${total.toLocaleString()}</div></div>
        <div class="kpi" style="padding:12px"><div class="kpi-label">Win Rate</div><div class="kpi-value" style="font-size:18px;color:var(--good)">${d.win_rate_pct||0}%</div></div>
        <div class="kpi" style="padding:12px"><div class="kpi-label">Avg P&L</div><div class="kpi-value" style="font-size:18px;color:${Number(d.avg_pnl_pct)>=0?'var(--good)':'var(--bad)'}">${Number(d.avg_pnl_pct||0).toFixed(2)}%</div></div>
      </div>
      <div style="font-size:12px;color:var(--muted)">
        Wins: ${Number(d.wins||0).toLocaleString()} · Losses: ${Number(d.losses||0).toLocaleString()} · Timeouts: ${Number(d.timeouts||0).toLocaleString()}
      </div>`;
    drawWLChart(Number(d.wins||0),Number(d.losses||0),Number(d.timeouts||0));
    if(_mlImportance&&Object.keys(_mlImportance).length>0) drawFIChart(_mlImportance);
  }catch(e){$('ml-stats').innerHTML=`<span class="error">${e.message}</span>`;}
}
async function runLabel(){
  $('ml-stats').innerHTML='<span class="muted">Labeling signals…</span>';
  try{const r=await fetch('/ml/label?tp_pct=3.0&sl_pct=1.0&batch_size=2000',{method:'POST'});const d=await r.json();await loadMlStats();console.log('label result',d);}
  catch(e){$('ml-stats').innerHTML=`<span class="error">${e.message}</span>`;}
}
async function runTrain(){
  $('ml-train-result').innerHTML='<span class="muted">Training… this may take a moment.</span>';
  try{
    const r=await fetch('/ml/train?n_estimators=100',{method:'POST'});
    const d=await r.json();
    if(d.error){$('ml-train-result').innerHTML=`<span class="error">${d.error}</span>`;return;}
    _mlImportance=d.feature_importance||{};
    $('ml-train-result').innerHTML=`
      <div class="kpi-row" style="grid-template-columns:repeat(4,1fr);margin-bottom:14px">
        <div class="kpi" style="padding:12px"><div class="kpi-label">Accuracy</div><div class="kpi-value" style="font-size:18px">${(Number(d.accuracy||0)*100).toFixed(1)}%</div></div>
        <div class="kpi" style="padding:12px"><div class="kpi-label">ROC-AUC</div><div class="kpi-value" style="font-size:18px">${d.cv_roc_auc_mean||0}</div></div>
        <div class="kpi" style="padding:12px"><div class="kpi-label">Precision Win</div><div class="kpi-value" style="font-size:18px">${(Number(d.precision_win||0)*100).toFixed(1)}%</div></div>
        <div class="kpi" style="padding:12px"><div class="kpi-label">Samples</div><div class="kpi-value" style="font-size:18px">${(Number(d.samples_train||0)+Number(d.samples_test||0)).toLocaleString()}</div></div>
      </div>
      <canvas id="fi-chart" style="height:200px"></canvas>`;
    drawFIChart(_mlImportance);
  }catch(e){$('ml-train-result').innerHTML=`<span class="error">${e.message}</span>`;}
}
function drawWLChart(wins,losses,timeouts){
  const cv=$('wl-chart'); if(!cv)return;
  const sc=window.devicePixelRatio||1,rc=cv.getBoundingClientRect();
  cv.width=Math.floor(rc.width*sc); cv.height=Math.floor(180*sc);
  const ctx=cv.getContext('2d'); ctx.scale(sc,sc);
  const W=cv.width/sc,H=cv.height/sc;
  ctx.clearRect(0,0,W,H);
  const total=wins+losses+timeouts; if(!total){ctx.fillStyle='#94a3b8';ctx.font='13px system-ui';ctx.fillText('No data yet',12,28);return;}
  const cx=W/2,cy=H/2,r=Math.min(cx,cy)-20;
  const segs=[{v:wins,c:'#10b981',l:'Win'},{v:losses,c:'#ef4444',l:'Loss'},{v:timeouts,c:'#94a3b8',l:'Timeout'}];
  let start=-Math.PI/2;
  segs.forEach(s=>{
    const a=(s.v/total)*Math.PI*2;
    ctx.beginPath(); ctx.moveTo(cx,cy); ctx.arc(cx,cy,r,start,start+a); ctx.closePath();
    ctx.fillStyle=s.c; ctx.fill();
    start+=a;
  });
  ctx.beginPath(); ctx.arc(cx,cy,r*0.55,0,Math.PI*2); ctx.fillStyle='#fff'; ctx.fill();
  ctx.fillStyle='#0f172a'; ctx.font='bold 16px system-ui'; ctx.textAlign='center'; ctx.textBaseline='middle';
  ctx.fillText(`${((wins/total)*100).toFixed(0)}%`,cx,cy-8);
  ctx.font='11px system-ui'; ctx.fillStyle='#94a3b8'; ctx.fillText('win rate',cx,cy+10);
  // Legend
  let lx=10,ly=H-14;
  segs.forEach(s=>{
    ctx.fillStyle=s.c; ctx.fillRect(lx,ly-8,10,10);
    ctx.fillStyle='#64748b'; ctx.font='10px system-ui'; ctx.textAlign='left'; ctx.textBaseline='middle';
    ctx.fillText(`${s.l} ${s.v.toLocaleString()}`,lx+14,ly-3);
    lx+=ctx.measureText(`${s.l} ${s.v.toLocaleString()}`).width+28;
  });
}
function drawFIChart(importance){
  const cv=$('fi-chart'); if(!cv)return;
  const entries=Object.entries(importance).sort((a,b)=>b[1]-a[1]).slice(0,8);
  if(!entries.length)return;
  const sc=window.devicePixelRatio||1,rc=cv.getBoundingClientRect();
  cv.width=Math.floor(rc.width*sc); cv.height=Math.floor(200*sc);
  const ctx=cv.getContext('2d'); ctx.scale(sc,sc);
  const W=cv.width/sc,H=cv.height/sc;
  ctx.clearRect(0,0,W,H);
  const PL=120,PR=40,PT=10,PB=10,bH=18,gap=4;
  const maxV=entries[0][1];
  entries.forEach(([k,v],i)=>{
    const y=PT+i*(bH+gap),bW=(v/maxV)*(W-PL-PR);
    ctx.fillStyle='#3b82f6'; ctx.fillRect(PL,y,bW,bH);
    ctx.fillStyle='#0f172a'; ctx.font='11px system-ui'; ctx.textAlign='right'; ctx.textBaseline='middle';
    ctx.fillText(k.replace('_',' '),PL-6,y+bH/2);
    ctx.fillStyle='#64748b'; ctx.textAlign='left';
    ctx.fillText((v*100).toFixed(1)+'%',PL+bW+6,y+bH/2);
  });
}

// ── Audit Trail ──────────────────────────────────────────────
async function loadAuditTrail(){
  try{
    const r=await fetch('/audit/events?environment=paper&limit=20',{cache:'no-store'});
    $('audit-trail').innerHTML=rows(await r.json(),[
      {label:'Time',render:x=>new Date(x.created_at).toLocaleTimeString()},
      {label:'Event',key:'event_type'},
      {label:'Actor',key:'actor'},
      {label:'Correlation',render:x=>String(x.correlation_id).slice(0,28)+'…'},
    ]);
  }catch(e){$('audit-trail').innerHTML=`<span class="error">${e.message}</span>`;}
}

// ── Backtests ────────────────────────────────────────────────
async function loadBacktests(){
  try{
    const r=await fetch('/backtest/list?limit=20',{cache:'no-store'});
    $('backtests').innerHTML=rows(await r.json(),[
      {label:'Symbol',key:'symbol'},
      {label:'Strategy',key:'strategy_id'},
      {label:'Created',render:x=>new Date(x.created_at).toLocaleDateString()},
    ]);
  }catch(e){$('backtests').innerHTML=`<span class="error">${e.message}</span>`;}
}

// ── Worker Config ────────────────────────────────────────────
let _cfgFocused=false;
document.addEventListener('DOMContentLoaded',()=>{
  ['cfg-confidence','cfg-symbols','cfg-timeframe','cfg-maxage'].forEach(id=>{
    const el=$(id); if(!el)return;
    el.addEventListener('focus',()=>{_cfgFocused=true;});
    el.addEventListener('blur', ()=>{_cfgFocused=false;});
  });
});
async function loadWorkerConfig(){
  if(_cfgFocused)return;
  try{
    const r=await fetch('/admin/worker-config',{cache:'no-store'});
    const data=await r.json();
    const map=Object.fromEntries(data.map(x=>[x.key,x.value]));
    if(map.min_signal_confidence) $('cfg-confidence').value=map.min_signal_confidence;
    if(map.watched_symbols)       $('cfg-symbols').value=map.watched_symbols;
    if(map.watched_timeframe)     $('cfg-timeframe').value=map.watched_timeframe;
    if(map.signal_max_age_seconds)$('cfg-maxage').value=map.signal_max_age_seconds;
  }catch(_){}
}
async function saveWorkerConfig(){
  const vals={min_signal_confidence:$('cfg-confidence').value,watched_symbols:$('cfg-symbols').value,watched_timeframe:$('cfg-timeframe').value,signal_max_age_seconds:$('cfg-maxage').value};
  try{
    await Promise.all(Object.entries(vals).map(([k,v])=>fetch(`/admin/worker-config/${k}`,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({value:v,actor:'dashboard'})})));
    $('cfg-result').innerHTML='<span class="good">Saved — applies on next worker cycle</span>';
    setTimeout(()=>{$('cfg-result').innerHTML='';},4000);
  }catch(e){$('cfg-result').innerHTML=`<span class="error">${e.message}</span>`;}
}

// ── Portfolio actions ────────────────────────────────────────
function renderConsistency(d){
  const c=d.status==='ok'?'good':d.status==='degraded'?'warn':'bad';
  $('portfolio-consistency').innerHTML=`<span class="${c}" style="font-weight:700">● ${d.status}</span> <span class="muted" style="font-size:11px">order gate ${d.block_order_execution?'BLOCKED':'open'}</span>`+
    (d.diffs&&d.diffs.length?'<div style="margin-top:8px">'+rows(d.diffs,[{label:'Symbol',key:'symbol'},{label:'Severity',key:'severity'},{label:'RAC Qty',render:x=>fmtNum(x.rac_quantity)},{label:'Broker Qty',render:x=>fmtNum(x.broker_quantity)},{label:'Reasons',render:x=>(x.reasons||[]).join(', ')}])+'</div>':'');
}
async function checkConsistency(){
  $('portfolio-consistency').innerHTML='<span class="muted">Checking…</span>';
  try{const r=await fetch('/portfolio/consistency?environment=paper',{cache:'no-store'});renderConsistency(await r.json());}
  catch(e){$('portfolio-consistency').innerHTML=`<span class="error">${e.message}</span>`;}
}
async function markToMarket(){
  $('mark-to-market').innerHTML='<span class="muted">Updating NAV…</span>';
  try{
    const r=await fetch('/portfolio/mark-to-market?environment=paper&timeframe=1Day',{method:'POST'});
    const d=await r.json();
    $('mark-to-market').innerHTML=`<div style="font-size:14px;font-weight:800">${fmtMoney(d.nav)}</div><div class="muted" style="font-size:11px">cash ${fmtMoney(d.cash)} · positions ${fmtMoney(d.positions_value)}</div>`+
      rows(d.positions,[{label:'Symbol',key:'symbol'},{label:'Qty',render:x=>fmtNum(x.quantity)},{label:'Last',render:x=>fmtMoney(x.latest_price)},{label:'Unrealized',render:x=>fmtMoney(x.unrealized_pnl)}]);
    refresh();
  }catch(e){$('mark-to-market').innerHTML=`<span class="error">${e.message}</span>`;}
}
async function reconcileOrders(){
  const q=$('quick-action-result');
  if(q) q.textContent='Reconciling…';
  $('reconciliation').innerHTML='<span class="muted">Reconciling…</span>';
  try{
    const r=await fetch('/orders/reconcile',{method:'POST'});const d=await r.json();
    const msg=`✓ Reconcile: ${d.filled} filled · ${d.pending} pending`;
    if(q){q.textContent=msg;setTimeout(()=>{q.textContent='';},5000);}
    $('reconciliation').innerHTML=`<span style="font-weight:700">${d.filled} filled</span> <span class="muted">· checked ${d.checked} · pending ${d.pending} · cancelled ${d.cancelled}</span>`;
    refresh();
  }catch(e){
    if(q) q.textContent='Error reconciling';
    $('reconciliation').innerHTML=`<span class="error">${e.message}</span>`;
  }
}
async function runPipeline(){
  $('pipeline-result').innerHTML='<span class="muted">Running…</span>';
  const payload={symbol:$('pipeline-symbol').value.trim().toUpperCase(),timeframe:$('pipeline-timeframe').value.trim(),strategy_id:$('pipeline-strategy').value,start:`${$('pipeline-start').value}T00:00:00Z`,end:`${$('pipeline-end').value}T23:59:59Z`,feature_set:'technical_v1',limit:300,explain:false};
  try{
    const r=await fetch('/pipeline/paper/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const d=await r.json();
    $('pipeline-result').innerHTML=`<span style="font-weight:700">${d.latest_signal_direction||'no signal'}</span> <span class="muted">· ${d.symbol} ${d.timeframe} · fetched ${d.fetched} · features ${d.features_computed} · signals ${d.signals_generated}</span>`;
    refresh();
  }catch(e){$('pipeline-result').innerHTML=`<span class="error">${e.message}</span>`;}
}

// ── Kill switch ──────────────────────────────────────────────
async function activateKillSwitch(){
  const r=prompt('Reason for activating kill switch:');if(!r)return;
  await fetch('/admin/kill-switch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:r,actor:'dashboard'})});
  refresh();
}
async function resetKillSwitch(){
  const r=prompt('Reason for resetting:');if(!r)return;
  await fetch('/admin/kill-switch/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({reason:r,actor:'dashboard'})});
  refresh();
}
async function doBootstrap(){
  $('bootstrap-result').innerHTML='<span class="muted">Running…</span>';
  try{const r=await fetch('/admin/bootstrap',{method:'POST'});const d=await r.json();$('bootstrap-result').innerHTML=`<span class="good">${d.status}</span>`;}
  catch(e){$('bootstrap-result').innerHTML=`<span class="error">${e.message}</span>`;}
}

// ── Init ─────────────────────────────────────────────────────
$('pipeline-start').value=isoDate(45);
$('pipeline-end').value=isoDate(1);
setNavRange(0);
refresh();
setInterval(refresh,15000);
window.addEventListener('resize',()=>{drawNavChart(_navPts);drawPnlChart(_lastDailyPnl);});
</script>
</body>
</html>
"""
