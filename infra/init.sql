-- Extensions required by the application.
-- This file is mounted into postgres initdb and runs once on first start.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Create postgres role for compatibility (pgAdmin, backup tools, etc.)
-- Runs as sinodik (superuser from POSTGRES_USER)
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
    CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD 'postgres';
  END IF;
END
$$;
