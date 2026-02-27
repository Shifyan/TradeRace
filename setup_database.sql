-- SQL Script to setup the recommendations table in Supabase

CREATE TABLE IF NOT EXISTS public.recommendations (
    id BIGSERIAL PRIMARY KEY,
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    analysis JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraint to prevent duplicate entries for the same ticker on the same day
    UNIQUE(ticker, date)
);

-- Optional: Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_recommendations_ticker_date ON public.recommendations(ticker, date);

-- Enable Row Level Security (RLS) if needed, 
-- or you can disable it for simplified testing in the Supabase Dashboard.
ALTER TABLE public.recommendations ENABLE ROW LEVEL SECURITY;

-- Creating a policy to allow all actions for the service_role key 
-- (which is usually what's used in backend servers)
CREATE POLICY "Allow system access" ON public.recommendations
FOR ALL TO service_role
USING (true)
WITH CHECK (true);
