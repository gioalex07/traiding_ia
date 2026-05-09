CREATE TABLE IF NOT EXISTS positions (
    environment text NOT NULL,
    symbol text NOT NULL,
    quantity numeric(20, 8) NOT NULL,
    average_price numeric(20, 8) NOT NULL,
    market_value numeric(20, 8) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (environment, symbol)
);

CREATE TABLE IF NOT EXISTS fills (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    environment text NOT NULL,
    order_id uuid NOT NULL,
    symbol text NOT NULL,
    side text NOT NULL,
    quantity numeric(20, 8) NOT NULL,
    price numeric(20, 8) NOT NULL,
    notional numeric(20, 8) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fills_order_id ON fills (order_id);
CREATE INDEX IF NOT EXISTS idx_fills_symbol_created_at ON fills (symbol, created_at DESC);

