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
      <button class="danger" onclick="activateKillSwitch()">Kill Switch</button>
      <button onclick="resetKillSwitch()">Reset</button>
    </div>
  </header>
  <main>
    <div class="grid">
      <section class="panel span-3"><h2>Mode</h2><div class="content metric"><span id="mode" class="value">-</span><span id="broker" class="label">-</span></div></section>
      <section class="panel span-3"><h2>Kill Switch</h2><div class="content"><span id="kill" class="status">-</span><div id="kill-reason" class="label"></div></div></section>
      <section class="panel span-3"><h2>Alpaca Paper</h2><div class="content metric"><span id="equity" class="value">-</span><span id="cash" class="label">-</span></div></section>
      <section class="panel span-3"><h2>Local AI</h2><div class="content"><span id="ai" class="status">-</span><div id="ai-models" class="label"></div></div></section>

      <section class="panel span-4"><h2>Portfolio Snapshot</h2><div class="content" id="portfolio-snapshot"></div></section>
      <section class="panel span-4"><h2>RAC Positions</h2><div class="content" id="portfolio-positions"></div></section>
      <section class="panel span-4"><h2>Broker Positions</h2><div class="content" id="broker-positions"></div></section>
      <section class="panel span-12"><h2>Mark to Market</h2><div class="content" id="mark-to-market"><span class="muted">Run to update NAV from latest available prices</span></div></section>

      <section class="panel span-12">
        <h2>Paper Analysis Pipeline</h2>
        <div class="content">
          <div class="form-grid">
            <label class="field"><span class="label">Symbol</span><input id="pipeline-symbol" value="AAPL" autocomplete="off"></label>
            <label class="field"><span class="label">Timeframe</span><input id="pipeline-timeframe" value="1Day" autocomplete="off"></label>
            <label class="field"><span class="label">Strategy</span><select id="pipeline-strategy"><option value="trend_following_v1">trend_following_v1</option><option value="mean_reversion_v1">mean_reversion_v1</option></select></label>
            <label class="field"><span class="label">Start</span><input id="pipeline-start" type="date"></label>
            <label class="field"><span class="label">End</span><input id="pipeline-end" type="date"></label>
            <button class="secondary" onclick="runPipeline()">Run</button>
          </div>
          <div class="pipeline-result" id="pipeline-result"><span class="muted">No run in this session</span></div>
        </div>
      </section>

      <section class="panel span-12"><h2>NAV History</h2><div class="content"><canvas id="nav-chart"></canvas></div></section>

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
    const error = section => section && !section.ok ? `<span class="error">${section.error}</span>` : `<span class="muted">No data</span>`;
    const statusClass = value => value === true || value === "available" || value === "paper_configured" ? "good" : value ? "warn" : "bad";
    function rows(items, columns) {
      if (!items || !items.length) return '<span class="muted">No rows</span>';
      return `<table><thead><tr>${columns.map(c => `<th>${c.label}</th>`).join("")}</tr></thead><tbody>` +
        items.map(item => `<tr>${columns.map(c => `<td>${c.render ? c.render(item) : (item[c.key] ?? "-")}</td>`).join("")}</tr>`).join("") +
        `</tbody></table>`;
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
      const orders = unwrap(data.orders);
      const signals = unwrap(data.signals);
      const backtests = unwrap(data.backtests);

      document.getElementById("mode").textContent = caps.trading_mode || "-";
      document.getElementById("broker").textContent = `${caps.broker_configured || "-"} / ${caps.broker_status || "-"}`;
      document.getElementById("kill").textContent = kill.active ? "ACTIVE" : "inactive";
      document.getElementById("kill").className = `status ${kill.active ? "bad" : "good"}`;
      document.getElementById("kill-reason").textContent = kill.reason || "";
      document.getElementById("equity").textContent = account ? fmtMoney(account.equity) : "-";
      document.getElementById("cash").textContent = account ? `cash ${fmtMoney(account.cash)} / buying power ${fmtMoney(account.buying_power)}` : error(data.broker_account);
      document.getElementById("ai").textContent = ai.status || "-";
      document.getElementById("ai").className = `status ${statusClass(ai.status)}`;
      document.getElementById("ai-models").textContent = (ai.models || []).join(", ");
      document.getElementById("portfolio-snapshot").innerHTML = snapshot && Object.keys(snapshot).length
        ? `<div class="metric"><span class="value">${fmtMoney(snapshot.nav)}</span><span class="label">cash ${fmtMoney(snapshot.cash)} / drawdown ${fmtNum(snapshot.drawdown)}</span></div><pre>${JSON.stringify(snapshot.exposure || {}, null, 2)}</pre>`
        : error(data.portfolio_snapshot);
      document.getElementById("portfolio-positions").innerHTML = rows(racPositions, [
        { label: "Symbol", key: "symbol" }, { label: "Qty", render: x => fmtNum(x.quantity) },
        { label: "Avg", render: x => fmtMoney(x.average_price) }, { label: "Value", render: x => fmtMoney(x.market_value) }
      ]);
      document.getElementById("broker-positions").innerHTML = rows(brokerPositions, [
        { label: "Symbol", key: "symbol" }, { label: "Qty", render: x => fmtNum(x.quantity) },
        { label: "Value", render: x => fmtMoney(x.market_value) }
      ]);
      document.getElementById("signals").innerHTML = rows(signals, [
        { label: "Symbol", key: "symbol" }, { label: "Dir", key: "direction" },
        { label: "Conf", render: x => fmtNum(x.confidence) }, { label: "Strategy", key: "strategy_id" }
      ]);
      document.getElementById("orders").innerHTML = rows(orders, [
        { label: "Symbol", key: "symbol" }, { label: "Side", key: "side" },
        { label: "Status", key: "status" }, { label: "Qty", render: x => fmtNum(x.quantity) },
        { label: "Price", render: x => fmtMoney(x.estimated_price) }
      ]);
      document.getElementById("backtests").innerHTML = rows(backtests, [
        { label: "ID", key: "id" }, { label: "Symbol", key: "symbol" },
        { label: "Strategy", key: "strategy_id" }, { label: "Created", key: "created_at" }
      ]);
      drawNavChart(portfolioHistory || []);
      document.getElementById("last-refresh").textContent = new Date().toLocaleTimeString();
    }
    async function markToMarket() {
      const resultEl = document.getElementById("mark-to-market");
      resultEl.innerHTML = '<span class="muted">Updating paper NAV...</span>';
      try {
        const response = await fetch("/portfolio/mark-to-market?environment=paper&timeframe=1Day", { method: "POST" });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || response.statusText);
        resultEl.innerHTML = `
          <div class="metric"><span class="value">${fmtMoney(data.nav)}</span><span class="label">cash ${fmtMoney(data.cash)} / positions ${fmtMoney(data.positions_value)} / ${data.status}</span></div>
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
          <div class="metric"><span class="value">${data.latest_signal_direction || "no signal"}</span><span class="label">${data.symbol} ${data.timeframe} / fetched ${data.fetched}, accepted ${data.accepted}, features ${data.features_computed}, signals ${data.signals_generated}</span></div>
          <pre>${data.ai_explanation || `AI status: ${data.ai_status || "not_requested"}`}</pre>
        `;
        refresh();
      } catch (err) {
        resultEl.innerHTML = `<span class="error">${err.message}</span>`;
      }
    }
    function drawNavChart(points) {
      const canvas = document.getElementById("nav-chart");
      const rect = canvas.getBoundingClientRect();
      const scale = window.devicePixelRatio || 1;
      canvas.width = Math.max(300, Math.floor(rect.width * scale));
      canvas.height = Math.max(180, Math.floor(rect.height * scale));
      const ctx = canvas.getContext("2d");
      ctx.scale(scale, scale);
      const width = canvas.width / scale;
      const height = canvas.height / scale;
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, width, height);
      const values = (points || []).map(p => Number(p.nav)).filter(Number.isFinite);
      if (values.length < 2) {
        ctx.fillStyle = "#667085";
        ctx.font = "13px system-ui";
        ctx.fillText("No NAV history yet", 16, 28);
        return;
      }
      const pad = 28;
      const min = Math.min(...values);
      const max = Math.max(...values);
      const range = max === min ? 1 : max - min;
      ctx.strokeStyle = "#d8dee8";
      ctx.lineWidth = 1;
      for (let i = 0; i < 4; i++) {
        const y = pad + i * ((height - pad * 2) / 3);
        ctx.beginPath();
        ctx.moveTo(pad, y);
        ctx.lineTo(width - pad, y);
        ctx.stroke();
      }
      ctx.strokeStyle = "#0f766e";
      ctx.lineWidth = 2;
      ctx.beginPath();
      values.forEach((value, index) => {
        const x = pad + (index / (values.length - 1)) * (width - pad * 2);
        const y = height - pad - ((value - min) / range) * (height - pad * 2);
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.fillStyle = "#263241";
      ctx.font = "12px system-ui";
      ctx.fillText(fmtMoney(values[values.length - 1]), pad, 18);
    }
    async function activateKillSwitch() {
      const reason = prompt("Reason");
      if (!reason) return;
      await fetch("/admin/kill-switch", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason, actor: "dashboard" }) });
      refresh();
    }
    async function resetKillSwitch() {
      const reason = prompt("Reason");
      if (!reason) return;
      await fetch("/admin/kill-switch/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason, actor: "dashboard" }) });
      refresh();
    }
    document.getElementById("pipeline-start").value = isoDate(45);
    document.getElementById("pipeline-end").value = isoDate(1);
    refresh();
    setInterval(refresh, 15000);
    window.addEventListener("resize", () => refresh());
  </script>
</body>
</html>
"""
