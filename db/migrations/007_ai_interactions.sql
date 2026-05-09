CREATE TABLE IF NOT EXISTS ai_interactions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    environment text NOT NULL,
    interaction_type text NOT NULL,
    prompt_template_id text NOT NULL,
    prompt_version text NOT NULL,
    model_name text,
    input_ref text,
    prompt text NOT NULL,
    response text,
    status text NOT NULL,
    latency_ms integer,
    error text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ai_interactions_created_at ON ai_interactions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_interactions_input_ref ON ai_interactions (input_ref);
CREATE INDEX IF NOT EXISTS idx_ai_interactions_type ON ai_interactions (interaction_type);

