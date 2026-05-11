-- Extend worker_config with timeframe and signal age settings
INSERT INTO worker_config (key, value, updated_by) VALUES
    ('watched_timeframe',      '5Min', 'bootstrap'),
    ('signal_max_age_seconds', '1200', 'bootstrap')
ON CONFLICT (key) DO NOTHING;
