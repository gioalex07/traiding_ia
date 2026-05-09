CREATE TABLE IF NOT EXISTS backtests (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id     text        NOT NULL,
    symbol          text        NOT NULL,
    timeframe       text        NOT NULL,
    start_time      timestamptz NOT NULL,
    end_time        timestamptz NOT NULL,
    initial_cash    numeric(20, 8) NOT NULL,
    final_equity    numeric(20, 8),
    bars_processed  int,
    params          jsonb       NOT NULL DEFAULT '{}',
    metrics         jsonb,
    status          text        NOT NULL DEFAULT 'completed',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_backtests_strategy   ON backtests (strategy_id);
CREATE INDEX IF NOT EXISTS idx_backtests_symbol      ON backtests (symbol);
CREATE INDEX IF NOT EXISTS idx_backtests_created_at  ON backtests (created_at DESC);
