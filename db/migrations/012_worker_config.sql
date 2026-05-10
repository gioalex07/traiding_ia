CREATE TABLE IF NOT EXISTS worker_config (
    key         text        PRIMARY KEY,
    value       text        NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now(),
    updated_by  text        NOT NULL DEFAULT 'system'
);

-- Seed defaults so the table is never empty after bootstrap
INSERT INTO worker_config (key, value, updated_by) VALUES
    ('min_signal_confidence', '0.6',       'bootstrap'),
    ('watched_symbols',       'AAPL,MSFT,SPY', 'bootstrap')
ON CONFLICT (key) DO NOTHING;
