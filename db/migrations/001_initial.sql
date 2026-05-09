CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS audit_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type text NOT NULL,
    environment text NOT NULL,
    correlation_id text NOT NULL,
    actor text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_correlation_id ON audit_events (correlation_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events (event_type);

CREATE TABLE IF NOT EXISTS risk_decisions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    environment text NOT NULL,
    strategy_id text NOT NULL,
    signal_id text NOT NULL,
    symbol text NOT NULL,
    decision_status text NOT NULL,
    approved boolean NOT NULL,
    reasons jsonb NOT NULL,
    requested_notional numeric(20, 8) NOT NULL,
    max_notional_allowed numeric(20, 8) NOT NULL,
    order_payload jsonb NOT NULL,
    portfolio_payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_risk_decisions_created_at ON risk_decisions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_risk_decisions_signal_id ON risk_decisions (signal_id);
CREATE INDEX IF NOT EXISTS idx_risk_decisions_symbol ON risk_decisions (symbol);

CREATE TABLE IF NOT EXISTS market_data_ohlcv (
    time timestamptz NOT NULL,
    broker text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    open numeric(20, 8) NOT NULL,
    high numeric(20, 8) NOT NULL,
    low numeric(20, 8) NOT NULL,
    close numeric(20, 8) NOT NULL,
    volume numeric(28, 8) NOT NULL,
    source_quality text NOT NULL DEFAULT 'unknown',
    PRIMARY KEY (time, broker, symbol, timeframe)
);

SELECT create_hypertable('market_data_ohlcv', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    time timestamptz NOT NULL,
    environment text NOT NULL,
    nav numeric(20, 8) NOT NULL,
    cash numeric(20, 8) NOT NULL,
    pnl_daily numeric(12, 6) NOT NULL,
    drawdown numeric(12, 6) NOT NULL,
    exposure jsonb NOT NULL,
    PRIMARY KEY (time, environment)
);

SELECT create_hypertable('portfolio_snapshots', 'time', if_not_exists => TRUE);

