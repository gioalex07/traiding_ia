CREATE TABLE IF NOT EXISTS kill_switch_events (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    action      text        NOT NULL CHECK (action IN ('activate', 'deactivate')),
    reason      text        NOT NULL,
    actor       text        NOT NULL DEFAULT 'api',
    environment text        NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_kill_switch_env_created
    ON kill_switch_events (environment, created_at DESC);
