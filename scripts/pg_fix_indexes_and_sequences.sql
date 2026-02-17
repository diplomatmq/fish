-- Fix Postgres indexes, sequences and repair chat_id in caught_fish
-- Run this inside psql connected to your DATABASE_URL
-- Example:
--   psql "$DATABASE_URL" -f scripts/pg_fix_indexes_and_sequences.sql

-- 1) Create missing unique indexes used by ON CONFLICT targets
CREATE UNIQUE INDEX IF NOT EXISTS players_user_chat_key ON players (user_id, chat_id);
CREATE UNIQUE INDEX IF NOT EXISTS player_nets_user_net_key ON player_nets (user_id, net_name);
CREATE UNIQUE INDEX IF NOT EXISTS player_rods_user_rod_key ON player_rods (user_id, rod_name);
CREATE UNIQUE INDEX IF NOT EXISTS player_baits_user_bait_key ON player_baits (user_id, bait_name);
CREATE UNIQUE INDEX IF NOT EXISTS rods_name_key ON rods (name);
CREATE UNIQUE INDEX IF NOT EXISTS fish_name_key ON fish (name);
CREATE UNIQUE INDEX IF NOT EXISTS baits_name_key ON baits (name);
CREATE UNIQUE INDEX IF NOT EXISTS locations_name_key ON locations (name);
CREATE UNIQUE INDEX IF NOT EXISTS weather_location_key ON weather (location);
CREATE UNIQUE INDEX IF NOT EXISTS system_flags_key ON system_flags (key);

-- 2) Adjust all serial sequences so nextval will not collide with existing ids
DO $$
DECLARE
  r RECORD;
  seqname text;
  maxval bigint;
BEGIN
  FOR r IN
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE column_default LIKE 'nextval(%' AND table_schema = 'public'
  LOOP
    seqname := pg_get_serial_sequence(r.table_name, r.column_name);
    IF seqname IS NOT NULL THEN
      EXECUTE format('SELECT COALESCE(MAX(%I),0) FROM %I', r.column_name, r.table_name) INTO maxval;
      IF maxval IS NULL THEN
        maxval := 0;
      END IF;
      -- set last_value = maxval so nextval() will return maxval+1
      EXECUTE format('SELECT setval(%L, %s, true)', seqname, maxval);
      RAISE NOTICE 'Adjusted sequence % for %.% to %', seqname, r.table_name, r.column_name, maxval;
    END IF;
  END LOOP;
END$$;

-- 3) Repair caught_fish.chat_id using most recent players.chat_id for the user (if available)
WITH latest_chat AS (
  SELECT DISTINCT ON (user_id) user_id, chat_id
  FROM players
  WHERE chat_id IS NOT NULL AND chat_id <> -1
  ORDER BY user_id, created_at DESC
)
UPDATE caught_fish cf
SET chat_id = lc.chat_id
FROM latest_chat lc
WHERE cf.user_id = lc.user_id
  AND (cf.chat_id IS NULL OR cf.chat_id = -1);

-- 4) Optional: show remaining problematic rows
-- SELECT COUNT(*) FROM caught_fish WHERE chat_id IS NULL OR chat_id = -1;

-- End of script
