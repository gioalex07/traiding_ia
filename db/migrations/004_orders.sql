CREATE TABLE IF NOT EXISTS orders (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    environment text NOT NULL,
    status text NOT NULL,
    broker text NOT NULL,
    symbol text NOT NULL,
    side text NOT NULL,
    order_type text NOT NULL,
    quantity numeric(20, 8) NOT NULL,
    estimated_price numeric(20, 8) NOT NULL,
    stop_loss_price numeric(20, 8),
    take_profit_price numeric(20, 8),
    strategy_id text NOT NULL,
    signal_id uuid NOT NULL,
    idempotency_key text NOT NULL UNIQUE,
    risk_decision jsonb NOT NULL,
    raw_payload jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_signal_id ON orders (signal_id);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders (symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);

