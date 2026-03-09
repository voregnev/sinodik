-- Clear all application data. Run when needed (e.g. dev reset).
-- Order: child table first, then parents.

TRUNCATE TABLE commemorations, orders, persons
  RESTART IDENTITY
  CASCADE;
