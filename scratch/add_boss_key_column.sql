-- Add boss_key column to support per-boss-type difficulty aggregation
-- (GET /api/difficulty/{boss_key} in pixel-runner-api).

ALTER TABLE pixel_runner.sessions ADD COLUMN IF NOT EXISTS boss_key TEXT;

-- Speeds up filtering+ordering in database.get_recent_sessions(boss_key, limit).
CREATE INDEX IF NOT EXISTS idx_sessions_boss_key_ended_at
    ON pixel_runner.sessions (boss_key, ended_at DESC);

-- No RLS policy changes needed: RLS is enabled with zero policies on this table
-- (see remediate_security.sql) and the API always connects via the service-role
-- key, which bypasses RLS entirely. This is a nullable column, so no backfill
-- is required for existing rows.
