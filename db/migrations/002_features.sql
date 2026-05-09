CREATE TABLE IF NOT EXISTS features (
    time timestamptz NOT NULL,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    feature_set text NOT NULL,
    values jsonb NOT NULL,
    source_bar_count integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (time, symbol, timeframe, feature_set)
);

SELECT create_hypertable('features', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_features_symbol_time ON features (symbol, timeframe, time DESC);

