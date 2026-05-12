CREATE TABLE IF NOT EXISTS signal_labels (
    id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id    uuid        NOT NULL UNIQUE,
    symbol       text        NOT NULL,
    timeframe    text        NOT NULL,
    direction    text        NOT NULL,
    entry_price  numeric(20,8) NOT NULL,
    outcome      text        NOT NULL,   -- 'win' | 'loss' | 'timeout'
    exit_bars    int         NOT NULL,
    pnl_pct      numeric(10,4) NOT NULL,
    tp_pct       numeric(6,2) NOT NULL,
    sl_pct       numeric(6,2) NOT NULL,
    labeled_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signal_labels_symbol    ON signal_labels (symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_signal_labels_outcome   ON signal_labels (outcome);
CREATE INDEX IF NOT EXISTS idx_signal_labels_direction ON signal_labels (direction);
