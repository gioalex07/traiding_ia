ALTER TABLE orders ADD COLUMN IF NOT EXISTS broker_order_id text;
CREATE INDEX IF NOT EXISTS idx_orders_broker_order_id ON orders (broker_order_id) WHERE broker_order_id IS NOT NULL;
