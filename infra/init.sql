-- Extensions required by the application.
-- This file is mounted into postgres initdb and runs once on first start.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
