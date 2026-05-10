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
      document.getElementById("last-refresh").textContent = new Date().toLocaleTimeString();
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
    refresh();
    setInterval(refresh, 15000);
  </script>
</body>
</html>
"""
