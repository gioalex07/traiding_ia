ALTER TABLE orders ADD COLUMN IF NOT EXISTS filled_price numeric(20, 8);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS filled_qty   numeric(20, 8);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS filled_at    timestamptz;

CREATE INDEX IF NOT EXISTS idx_orders_submitted
    ON orders (broker_order_id)
    WHERE status = 'submitted' AND broker_order_id IS NOT NULL;
