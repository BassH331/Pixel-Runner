-- Remediate Row Level Security (RLS) on pixel_runner tables

-- 1. Enable RLS on all tables in pixel_runner schema
ALTER TABLE pixel_runner.configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pixel_runner.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pixel_runner.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE pixel_runner.frame_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE pixel_runner.storylines ENABLE ROW LEVEL SECURITY;

-- 2. Security Notes:
-- Since the backend API on Vercel communicates with Supabase using the SUPABASE_SERVICE_KEY (service_role),
-- it completely bypasses all RLS policies. 
-- By enabling RLS and leaving no policies, the database is locked down from any direct public access using
-- the anon/publishable API key. All access must securely flow through the Vercel API middleware.
