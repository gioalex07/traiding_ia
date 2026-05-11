DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>RAC Dashboard</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #18202a;
      --muted: #667085;
      --line: #d8dee8;
      --good: #0f766e;
      --warn: #b45309;
      --bad: #b91c1c;
      --ink: #263241;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      background: #111827;
      color: #fff;
      border-bottom: 1px solid #0b1220;
    }
    h1 { margin: 0; font-size: 20px; font-weight: 700; letter-spacing: 0; }
    .sub { color: #cbd5e1; font-size: 13px; }
    main { padding: 18px; max-width: 1500px; margin: 0 auto; }
    .grid {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: 14px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      min-width: 0;
      overflow: hidden;
    }
    .panel h2 {
      margin: 0;
      padding: 12px 14px;
      font-size: 14px;
      border-bottom: 1px solid var(--line);
      background: #fafbfc;
    }
    .content { padding: 14px; }
    .span-3 { grid-column: span 3; }
    .span-4 { grid-column: span 4; }
    .span-6 { grid-column: span 6; }
    .span-8 { grid-column: span 8; }
    .span-12 { grid-column: span 12; }
    .metric { display: grid; gap: 4px; }
    .metric .value { font-size: 24px; font-weight: 750; color: var(--ink); overflow-wrap: anywhere; }
    .label { color: var(--muted); font-size: 12px; }
    .status {
      display: inline-flex;
      align-items: center;
      min-height: 28px;
      padding: 4px 9px;
      border-radius: 999px;
      font-weight: 650;
      border: 1px solid var(--line);
      background: #f8fafc;
    }
    .status.good { color: var(--good); border-color: #99f6e4; background: #ecfdf5; }
    .status.warn { color: var(--warn); border-color: #fed7aa; background: #fffbeb; }
    .status.bad { color: var(--bad); border-color: #fecaca; background: #fef2f2; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th, td {
      padding: 8px 10px;
      border-bottom: 1px solid #edf0f5;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }
    th { color: var(--muted); font-size: 12px; font-weight: 650; background: #fbfcfe; }
    tr:last-child td { border-bottom: 0; }
    .actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    button {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      border-radius: 6px;
      padding: 8px 10px;
      cursor: pointer;
      min-height: 36px;
      font-weight: 650;
    }
    button.danger { color: #fff; background: var(--bad); border-color: var(--bad); }
    button.secondary { color: var(--ink); background: #eef2f7; }
    input, select {
      width: 100%;
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 7px 9px;
      color: var(--text);
      background: #fff;
      font: inherit;
    }
    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr 1fr 1fr 1fr auto;
      gap: 10px;
      align-items: end;
    }
    .field { display: grid; gap: 5px; min-width: 0; }
    .pipeline-result {
      margin-top: 12px;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }
    canvas {
      width: 100%;
      height: 220px;
      display: block;
      border: 1px solid #edf0f5;
      border-radius: 6px;
      background: #fff;
    }
    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      margin: 0;
      color: #334155;
      font-size: 12px;
    }
    .error { color: var(--bad); }
    .muted { color: var(--muted); }
    @media (max-width: 1000px) {
      .span-3, .span-4, .span-6, .span-8 { grid-column: span 12; }
      .form-grid { grid-template-columns: 1fr; }
      header { align-items: flex-start; flex-direction: column; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>RAC</h1>
      <div class="sub">Robo Advisor / Autonomous Capital</div>
    </div>
    <div class="actions">
      <span id="last-refresh" class="sub"></span>
      <button class="secondary" onclick="refresh()">Refresh</button>
      <button class="secondary" onclick="markToMarket()">Mark to Market</button>
      <button class="secondary" onclick="checkConsistency()">Check Consistency</button>
      <button class="secondary" onclick="reconcileOrders()">Reconcile Orders</button>
      <button class="danger" onclick="activateKillSwitch()">Kill Switch</button>
      <button onclick="resetKillSwitch()">Reset</button>
    </div>
  </header>
  <main>
    <div class="grid">
      <section class="panel span-3">
        <h2>Mode</h2>
        <div class="content metric">
          <span id="mode" class="value">-</span>
          <span id="broker" class="label">-</span>
        </div>
      </section>
      <section class="panel span-3">
        <h2>Kill Switch</h2>
        <div class="content">
          <span id="kill" class="status">-</span>
          <div id="kill-reason" class="label"></div>
        </div>
      </section>
      <section class="panel span-3">
        <h2>Alpaca Paper</h2>
        <div class="content metric">
          <span id="equity" class="value">-</span>
          <span id="cash" class="label">-</span>
        </div>
      </section>
      <section class="panel span-3">
        <h2>Local AI</h2>
        <div class="content">
          <span id="ai" class="status">-</span>
          <div id="ai-models" class="label"></div>
        </div>
      </section>

      <section class="panel span-4">
        <h2>Portfolio Snapshot</h2>
        <div class="content" id="portfolio-snapshot"></div>
      </section>
      <section class="panel span-4">
        <h2>RAC Positions</h2>
        <div class="content" id="portfolio-positions"></div>
      </section>
      <section class="panel span-4">
        <h2>Broker Positions</h2>
        <div class="content" id="broker-positions"></div>
      </section>
      <section class="panel span-6">
        <h2>Fills Today</h2>
        <div class="content" id="fills-today"><span class="muted">Loading...</span></div>
      </section>
      <section class="panel span-6">
        <h2>Fills This Week</h2>
        <div class="content" id="fills-week"><span class="muted">Loading...</span></div>
      </section>
      <section class="panel span-12">
        <h2>Mark to Market</h2>
        <div class="content" id="mark-to-market">
          <span class="muted">Run to update NAV from latest available prices</span>
        </div>
      </section>
      <section class="panel span-12">
        <h2>Portfolio Consistency</h2>
        <div class="content" id="portfolio-consistency">
          <span class="muted">Checking RAC positions against Alpaca</span>
        </div>
      </section>
      <section class="panel span-12">
        <h2>Order Reconciliation</h2>
        <div class="content" id="reconciliation">
          <span class="muted">Run to sync submitted paper orders with Alpaca</span>
        </div>
      </section>

      <section class="panel span-12">
        <h2>Paper Analysis Pipeline</h2>
        <div class="content">
          <div class="form-grid">
            <label class="field">
              <span class="label">Symbol</span>
              <input id="pipeline-symbol" value="AAPL" autocomplete="off">
            </label>
            <label class="field">
              <span class="label">Timeframe</span>
              <input id="pipeline-timeframe" value="1Day" autocomplete="off">
            </label>
            <label class="field">
              <span class="label">Strategy</span>
              <select id="pipeline-strategy">
                <option value="trend_following_v1">trend_following_v1</option>
                <option value="mean_reversion_v1">mean_reversion_v1</option>
              </select>
            </label>
            <label class="field"><span class="label">Start</span><input id="pipeline-start" type="date"></label>
            <label class="field"><span class="label">End</span><input id="pipeline-end" type="date"></label>
            <button class="secondary" onclick="runPipeline()">Run</button>
          </div>
          <div class="pipeline-result" id="pipeline-result"><span class="muted">No run in this session</span></div>
        </div>
      </section>

      <section class="panel span-12">
        <h2>NAV History
          <span style="float:right;font-weight:normal;font-size:12px;display:flex;gap:6px">
            <button class="secondary" id="nav-7d"  onclick="setNavRange(7)">7d</button>
            <button class="secondary" id="nav-30d" onclick="setNavRange(30)">30d</button>
            <button class="secondary" id="nav-all" onclick="setNavRange(0)">All</button>
          </span>
        </h2>
        <div class="content"><canvas id="nav-chart"></canvas></div>
      </section>

      <section class="panel span-12">
        <h2>Worker Config <span class="label" style="font-weight:normal">— applies next cycle</span></h2>
        <div class="content">
          <div class="form-grid" style="grid-template-columns:1fr 1fr 1fr 1fr auto">
            <label class="field">
              <span class="label">Min Confidence (0–1)</span>
              <input id="cfg-confidence" type="number" min="0" max="1" step="0.05" value="0.5">
            </label>
            <label class="field">
              <span class="label">Timeframe</span>
              <select id="cfg-timeframe">
                <option value="1Min">1Min</option>
                <option value="5Min" selected>5Min</option>
                <option value="15Min">15Min</option>
                <option value="1Hour">1Hour</option>
                <option value="1Day">1Day</option>
              </select>
            </label>
            <label class="field">
              <span class="label">Max Signal Age (seconds)</span>
              <input id="cfg-maxage" type="number" min="60" step="60" value="1200">
            </label>
            <label class="field">
              <span class="label">Symbols (comma-separated)</span>
              <input id="cfg-symbols" value="AAPL,MSFT,SPY" autocomplete="off">
            </label>
            <button class="secondary" onclick="saveWorkerConfig()">Save</button>
          </div>
          <div id="cfg-result" style="margin-top:8px"></div>
        </div>
      </section>
      <section class="panel span-12">
        <h2>Audit Trail</h2>
        <div class="content" id="audit-trail"><span class="muted">Loading...</span></div>
      </section>
      <section class="panel span-12">
        <h2>Strategy Performance</h2>
        <div class="content" id="strategy-performance"><span class="muted">Loading...</span></div>
      </section>
      <section class="panel span-6"><h2>Latest Signals</h2><div class="content" id="signals"></div></section>
      <section class="panel span-6"><h2>Latest Orders</h2><div class="content" id="orders"></div></section>
      <section class="panel span-12"><h2>Backtests</h2><div class="content" id="backtests"></div></section>
    </div>
  </main>
  <script>
    const fmtMoney = value => {
      const n = Number(value);
      if (!Number.isFinite(n)) return "-";
      return n.toLocaleString(undefined, { style: "currency", currency: "USD" });
    };
    const fmtNum = value => {
      const n = Number(value);
      if (!Number.isFinite(n)) return "-";
      return n.toLocaleString(undefined, { maximumFractionDigits: 6 });
    };
    function isoDate(daysAgo) {
      const d = new Date();
      d.setDate(d.getDate() - daysAgo);
      return d.toISOString().slice(0, 10);
    }
    const unwrap = section => section && section.ok ? section.data : null;
    const error = section => section && !section.ok
      ? `<span class="error">${section.error}</span>`
      : `<span class="muted">No data</span>`;
    const statusClass = value => (
      value === true || value === "available" || value === "paper_configured"
    ) ? "good" : value ? "warn" : "bad";
    function rows(items, columns) {
      if (!items || !items.length) return '<span class="muted">No rows</span>';
      return `<table><thead><tr>${columns.map(c => `<th>${c.label}</th>`).join("")}</tr></thead><tbody>` +
        items.map(item => `<tr>${columns.map(c => {
          const value = c.render ? c.render(item) : (item[c.key] ?? "-");
          return `<td>${value}</td>`;
        }).join("")}</tr>`).join("") +
        `</tbody></table>`;
    }
    let _cfgFocused = false;
    document.addEventListener("DOMContentLoaded", () => {
      ["cfg-confidence", "cfg-symbols", "cfg-timeframe", "cfg-maxage"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.addEventListener("focus", () => { _cfgFocused = true; });
          el.addEventListener("blur",  () => { _cfgFocused = false; });
        }
      });
    });
    async function loadWorkerConfig() {
      if (_cfgFocused) return;
      try {
        const resp = await fetch("/admin/worker-config", { cache: "no-store" });
        const data = await resp.json();
        const map  = Object.fromEntries(data.map(x => [x.key, x.value]));
        if (map.min_signal_confidence)
          document.getElementById("cfg-confidence").value = map.min_signal_confidence;
        if (map.watched_symbols)
          document.getElementById("cfg-symbols").value = map.watched_symbols;
        if (map.watched_timeframe)
          document.getElementById("cfg-timeframe").value = map.watched_timeframe;
        if (map.signal_max_age_seconds)
          document.getElementById("cfg-maxage").value = map.signal_max_age_seconds;
      } catch (_) {}
    }
    async function saveWorkerConfig() {
      const confidence = document.getElementById("cfg-confidence").value.trim();
      const symbols    = document.getElementById("cfg-symbols").value.trim();
      const timeframe  = document.getElementById("cfg-timeframe").value.trim();
      const maxage     = document.getElementById("cfg-maxage").value.trim();
      const resultEl   = document.getElementById("cfg-result");
      if (!confidence || !symbols || !timeframe || !maxage) {
        resultEl.innerHTML = '<span class="error">All fields are required</span>';
        return;
      }
      try {
        await Promise.all([
          fetch("/admin/worker-config/min_signal_confidence", {
            method: "PUT", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: confidence, actor: "dashboard" }),
          }),
          fetch("/admin/worker-config/watched_symbols", {
            method: "PUT", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: symbols, actor: "dashboard" }),
          }),
          fetch("/admin/worker-config/watched_timeframe", {
            method: "PUT", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: timeframe, actor: "dashboard" }),
          }),
          fetch("/admin/worker-config/signal_max_age_seconds", {
            method: "PUT", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ value: maxage, actor: "dashboard" }),
          }),
        ]);
        resultEl.innerHTML = '<span style="color:var(--good)">Saved — applies on next worker cycle</span>';
        setTimeout(() => { resultEl.innerHTML = ""; }, 4000);
      } catch (e) {
        resultEl.innerHTML = `<span class="error">${e.message}</span>`;
      }
    }

    async function loadAuditTrail() {
      try {
        const resp = await fetch("/audit/events?environment=paper&limit=20", { cache: "no-store" });
        const data = await resp.json();
        document.getElementById("audit-trail").innerHTML = data.length
          ? rows(data, [
              { label: "Time", render: x => new Date(x.created_at).toLocaleTimeString() },
              { label: "Event", key: "event_type" },
              { label: "Actor", key: "actor" },
              { label: "Correlation", render: x => String(x.correlation_id).slice(0, 24) + "…" },
            ])
          : '<span class="muted">No audit events yet</span>';
      } catch (e) {
        document.getElementById("audit-trail").innerHTML = `<span class="error">${e.message}</span>`;
      }
    }

    async function loadStrategyPerformance() {
      try {
        const resp = await fetch("/strategies/performance?environment=paper", { cache: "no-store" });
        const data = await resp.json();
        document.getElementById("strategy-performance").innerHTML = data.length
          ? rows(data, [
              { label: "Strategy", key: "strategy_id" },
              { label: "Buys", key: "buys" },
              { label: "Sells", key: "sells" },
              { label: "Bought", render: x => fmtMoney(x.buy_notional) },
              { label: "Sold", render: x => fmtMoney(x.sell_notional) },
              { label: "Realized P&L", render: x => {
                  const n = Number(x.realized_pnl);
                  const cls = n >= 0 ? "good" : "bad";
                  return `<span style="color:var(--${cls})">${fmtMoney(n)}</span>`;
              }},
            ])
          : '<span class="muted">No fills recorded yet</span>';
      } catch (e) {
        document.getElementById("strategy-performance").innerHTML = `<span class="error">${e.message}</span>`;
      }
    }

    async function refresh() {
      const response = await fetch("/dashboard/data", { cache: "no-store" });
      const data = await response.json();
      const caps = unwrap(data.capabilities) || {};
      const kill = unwrap(data.kill_switch) || {};
      const ai = unwrap(data.ai) || {};
      const account = unwrap(data.broker_account);
      const brokerPositions = unwrap(data.broker_positions);
      const snapshot = unwrap(data.portfolio_snapshot);
      const portfolioHistory = unwrap(data.portfolio_history);
      const racPositions = unwrap(data.portfolio_positions);
      const consistency = unwrap(data.portfolio_consistency);
      const orders = unwrap(data.orders);
      const signals = unwrap(data.signals);
      const backtests = unwrap(data.backtests);

      document.getElementById("mode").textContent = caps.trading_mode || "-";
      document.getElementById("broker").textContent = `${caps.broker_configured || "-"} / ${caps.broker_status || "-"}`;
      document.getElementById("kill").textContent = kill.active ? "ACTIVE" : "inactive";
      document.getElementById("kill").className = `status ${kill.active ? "bad" : "good"}`;
      document.getElementById("kill-reason").textContent = kill.reason || "";
      document.getElementById("equity").textContent = account ? fmtMoney(account.equity) : "-";
      document.getElementById("cash").textContent = account
        ? `cash ${fmtMoney(account.cash)} / buying power ${fmtMoney(account.buying_power)}`
        : error(data.broker_account);
      document.getElementById("ai").textContent = ai.status || "-";
      document.getElementById("ai").className = `status ${statusClass(ai.status)}`;
      document.getElementById("ai-models").textContent = (ai.models || []).join(", ");
      if (snapshot && Object.keys(snapshot).length) {
        const dd = Math.max(0, Number(snapshot.drawdown) || 0);
        const maxDd = 5;
        const ddPct = Math.min(dd / maxDd * 100, 100);
        const ddColor = dd < 2 ? "good" : dd < 4 ? "warn" : "bad";
        const pnl = Number(snapshot.pnl_daily) || 0;
        const pnlSign = pnl >= 0 ? "+" : "";
        const pnlColor = pnl >= 0 ? "good" : "bad";
        document.getElementById("portfolio-snapshot").innerHTML = `
          <div class="metric">
            <span class="value">${fmtMoney(snapshot.nav)}</span>
            <span class="label">
              cash ${fmtMoney(snapshot.cash)} &nbsp;·&nbsp;
              <span style="color:var(--${pnlColor})">${pnlSign}${fmtMoney(pnl)} today</span>
            </span>
          </div>
          <div style="margin-top:10px">
            <div class="label" style="display:flex;justify-content:space-between">
              <span>Drawdown</span><span style="color:var(--${ddColor})">${dd.toFixed(2)}%</span>
            </div>
            <div style="background:#edf0f5;border-radius:4px;height:8px;margin-top:4px">
              <div style="background:var(--${ddColor});width:${ddPct}%;height:8px;
                border-radius:4px;transition:width 0.4s"></div>
            </div>
            <div class="label" style="text-align:right;margin-top:2px">max ${maxDd}%</div>
          </div>`;
      } else {
        document.getElementById("portfolio-snapshot").innerHTML = error(data.portfolio_snapshot);
      }
      document.getElementById("portfolio-positions").innerHTML = rows(racPositions, [
        { label: "Symbol", key: "symbol" }, { label: "Qty", render: x => fmtNum(x.quantity) },
        { label: "Avg", render: x => fmtMoney(x.average_price) },
        { label: "Value", render: x => fmtMoney(x.market_value) }
      ]);
      document.getElementById("broker-positions").innerHTML = rows(brokerPositions, [
        { label: "Symbol", key: "symbol" }, { label: "Qty", render: x => fmtNum(x.quantity) },
        { label: "Value", render: x => fmtMoney(x.market_value) }
      ]);
      if (consistency) {
        renderConsistency(consistency);
      } else {
        document.getElementById("portfolio-consistency").innerHTML = error(data.portfolio_consistency);
      }
      document.getElementById("signals").innerHTML = rows(signals, [
        { label: "Time",     render: x => new Date(x.time).toLocaleTimeString() },
        { label: "Symbol",   key: "symbol" },
        { label: "Dir",      render: x => {
          const c = x.direction==="buy" ? "good" : x.direction==="sell" ? "bad" : "muted";
          return `<span style="color:var(--${c});font-weight:650">${x.direction.toUpperCase()}</span>`;
        }},
        { label: "Conf",     render: x => {
          const v = Number(x.confidence);
          const c = v >= 0.7 ? "good" : v >= 0.5 ? "warn" : "muted";
          return `<span style="color:var(--${c})">${v.toFixed(3)}</span>`;
        }},
        { label: "Strategy", render: x => x.strategy_id.replace("_v1","") },
      ]);
      document.getElementById("orders").innerHTML = rows(orders, [
        { label: "Time",   render: x => new Date(x.created_at).toLocaleTimeString() },
        { label: "Symbol", key: "symbol" },
        { label: "Side",   render: x => {
          const c = x.side==="buy" ? "good" : "bad";
          return `<span style="color:var(--${c});font-weight:650">${x.side.toUpperCase()}</span>`;
        }},
        { label: "Status", render: x => {
          const c = x.status==="filled" ? "good" : x.status==="submitted" ? "warn" : "muted";
          return `<span style="color:var(--${c})">${x.status}</span>`;
        }},
        { label: "Price",  render: x => fmtMoney(x.filled_price || x.estimated_price) },
      ]);
      document.getElementById("backtests").innerHTML = rows(backtests, [
        { label: "Symbol",   key: "symbol" },
        { label: "Strategy", key: "strategy_id" },
        { label: "Created",  render: x => new Date(x.created_at).toLocaleDateString() },
      ]);
      loadNavHistory();
      document.getElementById("last-refresh").textContent = new Date().toLocaleTimeString();
      loadFills();
      loadWorkerConfig();
      loadAuditTrail();
      loadStrategyPerformance();
    }
    function renderConsistency(data) {
      const className = data.status === "ok" ? "good" : data.status === "degraded" ? "warn" : "bad";
      document.getElementById("portfolio-consistency").innerHTML = `
        <span class="status ${className}">${data.status}</span>
        <div class="label">order gate ${data.block_order_execution ? "blocked" : "open"}</div>
        ${rows(data.diffs, [
          { label: "Symbol", key: "symbol" },
          { label: "Severity", key: "severity" },
          { label: "RAC Qty", render: x => fmtNum(x.rac_quantity) },
          { label: "Broker Qty", render: x => fmtNum(x.broker_quantity) },
          { label: "Qty Diff", render: x => fmtNum(x.quantity_diff) },
          { label: "Reasons", render: x => (x.reasons || []).join(", ") || "-" }
        ])}
      `;
    }
    async function checkConsistency() {
      const resultEl = document.getElementById("portfolio-consistency");
      resultEl.innerHTML = '<span class="muted">Checking portfolio consistency...</span>';
      try {
        const response = await fetch("/portfolio/consistency?environment=paper", { cache: "no-store" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || response.statusText);
        renderConsistency(data);
      } catch (err) {
        resultEl.innerHTML = `<span class="error">${err.message}</span>`;
      }
    }
    async function markToMarket() {
      const resultEl = document.getElementById("mark-to-market");
      resultEl.innerHTML = '<span class="muted">Updating paper NAV...</span>';
      try {
        const response = await fetch(
          "/portfolio/mark-to-market?environment=paper&timeframe=1Day",
          { method: "POST" }
        );
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || response.statusText);
        resultEl.innerHTML = `
          <div class="metric">
            <span class="value">${fmtMoney(data.nav)}</span>
            <span class="label">
              cash ${fmtMoney(data.cash)} / positions ${fmtMoney(data.positions_value)} / ${data.status}
            </span>
          </div>
          ${rows(data.positions, [
            { label: "Symbol", key: "symbol" },
            { label: "Qty", render: x => fmtNum(x.quantity) },
            { label: "Last", render: x => fmtMoney(x.latest_price) },
            { label: "Unrealized", render: x => fmtMoney(x.unrealized_pnl) },
            { label: "Error", render: x => x.error || "-" }
          ])}
        `;
        refresh();
      } catch (err) {
        resultEl.innerHTML = `<span class="error">${err.message}</span>`;
      }
    }
    async function reconcileOrders() {
      const resultEl = document.getElementById("reconciliation");
      resultEl.innerHTML = '<span class="muted">Reconciling submitted orders...</span>';
      try {
        const response = await fetch("/orders/reconcile", { method: "POST" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || response.statusText);
        resultEl.innerHTML = `
          <div class="metric">
            <span class="value">${data.filled} filled</span>
            <span class="label">
              checked ${data.checked} / pending ${data.pending} / cancelled ${data.cancelled}
            </span>
          </div>
          <pre>${JSON.stringify(data.errors || [], null, 2)}</pre>
        `;
        refresh();
      } catch (err) {
        resultEl.innerHTML = `<span class="error">${err.message}</span>`;
      }
    }
    async function runPipeline() {
      const resultEl = document.getElementById("pipeline-result");
      resultEl.innerHTML = '<span class="muted">Running paper analysis...</span>';
      const payload = {
        symbol: document.getElementById("pipeline-symbol").value.trim().toUpperCase(),
        timeframe: document.getElementById("pipeline-timeframe").value.trim(),
        strategy_id: document.getElementById("pipeline-strategy").value,
        start: `${document.getElementById("pipeline-start").value}T00:00:00Z`,
        end: `${document.getElementById("pipeline-end").value}T23:59:59Z`,
        feature_set: "technical_v1",
        limit: 300,
        explain: true
      };
      try {
        const response = await fetch("/pipeline/paper/run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || response.statusText);
        resultEl.innerHTML = `
          <div class="metric">
            <span class="value">${data.latest_signal_direction || "no signal"}</span>
            <span class="label">
              ${data.symbol} ${data.timeframe} / fetched ${data.fetched}, accepted ${data.accepted},
              features ${data.features_computed}, signals ${data.signals_generated}
            </span>
          </div>
          <pre>${data.ai_explanation || `AI status: ${data.ai_status || "not_requested"}`}</pre>
        `;
        refresh();
      } catch (err) {
        resultEl.innerHTML = `<span class="error">${err.message}</span>`;
      }
    }
    // ── NAV Chart ──────────────────────────────────────────────────────
    let _navPoints = [];
    let _navRange  = 0;

    async function loadNavHistory() {
      const limit = _navRange === 0 ? 1000 : _navRange <= 7 ? 300 : 700;
      try {
        const resp = await fetch(
          `/portfolio/history?environment=paper&limit=${limit}`,
          { cache: "no-store" }
        );
        _navPoints = await resp.json();
      } catch (_) { _navPoints = []; }
      drawNavChart();
    }

    function setNavRange(days) {
      _navRange = days;
      document.querySelectorAll("[id^='nav-']").forEach(b => {
        b.style.fontWeight = "";
        b.style.background = "";
      });
      const key = days === 7 ? "7d" : days === 30 ? "30d" : "all";
      const btn = document.getElementById("nav-" + key);
      if (btn) { btn.style.fontWeight = "700"; btn.style.background = "#dbeafe"; }
      loadNavHistory();
    }

    function drawNavChart() {
      let points = _navPoints;
      if (_navRange > 0) {
        const cutoff = Date.now() - _navRange * 86400000;
        points = _navPoints.filter(p => new Date(p.time).getTime() >= cutoff);
      }

      const canvas = document.getElementById("nav-chart");
      if (!canvas) return;
      const rect  = canvas.getBoundingClientRect();
      const scale = window.devicePixelRatio || 1;
      canvas.width  = Math.max(400, Math.floor(rect.width  * scale));
      canvas.height = Math.max(220, Math.floor(rect.height * scale));
      const ctx = canvas.getContext("2d");
      ctx.scale(scale, scale);
      const W = canvas.width / scale;
      const H = canvas.height / scale;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, W, H);

      const navVals = points.map(p => Number(p.nav)).filter(Number.isFinite);
      if (navVals.length < 2) {
        ctx.fillStyle = "#667085";
        ctx.font = "13px system-ui";
        ctx.fillText("No NAV history yet — data arrives each worker cycle", 16, 28);
        return;
      }

      const PL = 72, PR = 12, PT = 20, PB = 36;
      const chartW = W - PL - PR;
      const chartH = H - PT - PB;
      const minV = Math.min(...navVals);
      const maxV = Math.max(...navVals);
      const rangeV = maxV === minV ? 1 : maxV - minV;

      // Y grid + labels
      const ySteps = 4;
      ctx.font = "10px system-ui";
      ctx.textAlign = "right";
      for (let i = 0; i <= ySteps; i++) {
        const val = minV + (rangeV / ySteps) * i;
        const y   = PT + chartH - (i / ySteps) * chartH;
        ctx.strokeStyle = "#edf0f5";
        ctx.lineWidth   = 1;
        ctx.beginPath(); ctx.moveTo(PL, y); ctx.lineTo(PL + chartW, y); ctx.stroke();
        ctx.fillStyle = "#94a3b8";
        ctx.fillText(fmtMoney(val), PL - 4, y + 3);
      }

      // X labels (up to 6 evenly spaced)
      const xCount = Math.min(6, points.length - 1);
      ctx.textAlign = "center";
      for (let i = 0; i <= xCount; i++) {
        const idx  = Math.round(i * (points.length - 1) / xCount);
        const x    = PL + (idx / (points.length - 1)) * chartW;
        const d    = new Date(points[idx].time);
        const hh   = String(d.getHours()).padStart(2,"0");
        const mm   = String(d.getMinutes()).padStart(2,"0");
        const lbl  = `${d.getMonth()+1}/${d.getDate()} ${hh}:${mm}`;
        ctx.fillStyle = "#94a3b8";
        ctx.fillText(lbl, x, H - PB + 14);
      }

      // Line + fill
      const positive = navVals[navVals.length - 1] >= navVals[0];
      const lineColor = positive ? "#0f766e" : "#b91c1c";
      const fillColor = positive ? "rgba(15,118,110,0.08)" : "rgba(185,28,28,0.06)";

      ctx.beginPath();
      navVals.forEach((v, i) => {
        const x = PL + (i / (navVals.length - 1)) * chartW;
        const y = PT + chartH - ((v - minV) / rangeV) * chartH;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      });
      ctx.strokeStyle = lineColor;
      ctx.lineWidth   = 2;
      ctx.stroke();

      // Area fill under line
      ctx.lineTo(PL + chartW, PT + chartH);
      ctx.lineTo(PL, PT + chartH);
      ctx.closePath();
      ctx.fillStyle = fillColor;
      ctx.fill();

      // Current NAV label top-left
      ctx.fillStyle = "#263241";
      ctx.font      = "bold 13px system-ui";
      ctx.textAlign = "left";
      ctx.fillText(fmtMoney(navVals[navVals.length - 1]), PL + 4, PT + 14);

      // Hover tooltip
      canvas._navPoints = points;
      canvas._navMeta   = { PL, PR, PT, PB, chartW, chartH, minV, rangeV };
    }

    // Tooltip on hover
    (function setupNavTooltip() {
      const canvas  = document.getElementById("nav-chart");
      const tooltip = document.createElement("div");
      tooltip.style.cssText =
        "position:fixed;background:#1e293b;color:#f1f5f9;padding:6px 10px;" +
        "border-radius:6px;font-size:12px;pointer-events:none;display:none;z-index:99";
      document.body.appendChild(tooltip);

      canvas.addEventListener("mousemove", e => {
        const pts = canvas._navPoints;
        const m   = canvas._navMeta;
        if (!pts || pts.length < 2 || !m) return;
        const rect = canvas.getBoundingClientRect();
        const mx   = e.clientX - rect.left;
        if (mx < m.PL || mx > m.PL + m.chartW) { tooltip.style.display = "none"; return; }
        const frac = (mx - m.PL) / m.chartW;
        const idx  = Math.round(frac * (pts.length - 1));
        const pt   = pts[Math.max(0, Math.min(idx, pts.length - 1))];
        const d    = new Date(pt.time);
        tooltip.innerHTML =
          `<b>${fmtMoney(pt.nav)}</b><br>` +
          `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
        tooltip.style.display = "block";
        tooltip.style.left    = (e.clientX + 14) + "px";
        tooltip.style.top     = (e.clientY - 10) + "px";
      });
      canvas.addEventListener("mouseleave", () => { tooltip.style.display = "none"; });
    })();
    async function loadFills() {
      const cols = [
        { label: "Time",     render: x => new Date(x.created_at).toLocaleTimeString() },
        { label: "Symbol",   key: "symbol" },
        { label: "Side",     render: x => {
          const c = x.side === "buy" ? "good" : "bad";
          return `<span style="color:var(--${c})">${x.side.toUpperCase()}</span>`;
        }},
        { label: "Qty",      render: x => fmtNum(x.quantity) },
        { label: "Price",    render: x => fmtMoney(x.price) },
        { label: "Notional", render: x => fmtMoney(x.notional) },
      ];
      try {
        const [r1, r2] = await Promise.all([
          fetch("/portfolio/fills?environment=paper&days=1", { cache: "no-store" }),
          fetch("/portfolio/fills?environment=paper&days=7", { cache: "no-store" }),
        ]);
        const today = await r1.json();
        const week  = await r2.json();
        document.getElementById("fills-today").innerHTML =
          today.length ? rows(today, cols) : '<span class="muted">No fills today</span>';
        document.getElementById("fills-week").innerHTML =
          week.length ? rows(week, cols) : '<span class="muted">No fills this week</span>';
      } catch (e) {
        document.getElementById("fills-today").innerHTML = `<span class="error">${e.message}</span>`;
      }
    }
    async function activateKillSwitch() {
      const reason = prompt("Reason");
      if (!reason) return;
      await fetch("/admin/kill-switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason, actor: "dashboard" })
      });
      refresh();
    }
    async function resetKillSwitch() {
      const reason = prompt("Reason");
      if (!reason) return;
      await fetch("/admin/kill-switch/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason, actor: "dashboard" })
      });
      refresh();
    }
    document.getElementById("pipeline-start").value = isoDate(45);
    document.getElementById("pipeline-end").value = isoDate(1);
    setNavRange(0); // inicializa con "All" activo
    refresh();
    setInterval(refresh, 15000);
    window.addEventListener("resize", () => { drawNavChart(); });
  </script>
</body>
</html>
"""
