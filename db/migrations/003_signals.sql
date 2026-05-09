CREATE TABLE IF NOT EXISTS signals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    time timestamptz NOT NULL,
    environment text NOT NULL,
    strategy_id text NOT NULL,
    strategy_version text NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    direction text NOT NULL,
    confidence numeric(12, 6) NOT NULL,
    stop_loss_pct numeric(12, 6) NOT NULL,
    take_profit_pct numeric(12, 6) NOT NULL,
    max_position_pct numeric(12, 6) NOT NULL,
    invalidation_rules jsonb NOT NULL,
    raw_payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signals_created_at ON signals (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_symbol_time ON signals (symbol, timeframe, time DESC);
CREATE INDEX IF NOT EXISTS idx_signals_strategy ON signals (strategy_id, strategy_version);

