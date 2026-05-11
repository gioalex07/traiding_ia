CREATE TABLE IF NOT EXISTS trade_outcomes (
    id               uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    environment      text          NOT NULL,
    symbol           text          NOT NULL,
    strategy_id      text          NOT NULL,
    open_order_id    uuid          NOT NULL,
    close_order_id   uuid,
    open_price       numeric(20,8) NOT NULL,
    close_price      numeric(20,8) NOT NULL,
    quantity         numeric(20,8) NOT NULL,
    open_notional    numeric(20,8) NOT NULL,
    close_notional   numeric(20,8) NOT NULL,
    realized_pnl     numeric(20,8) NOT NULL,
    pnl_pct          numeric(10,4) NOT NULL,
    close_reason     text          NOT NULL,
    opened_at        timestamptz   NOT NULL,
    closed_at        timestamptz   NOT NULL DEFAULT now(),
    duration_seconds int           NOT NULL,
    created_at       timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trade_outcomes_closed_at  ON trade_outcomes (closed_at DESC);
CREATE INDEX IF NOT EXISTS idx_trade_outcomes_symbol     ON trade_outcomes (symbol, environment);
CREATE INDEX IF NOT EXISTS idx_trade_outcomes_strategy   ON trade_outcomes (strategy_id);
