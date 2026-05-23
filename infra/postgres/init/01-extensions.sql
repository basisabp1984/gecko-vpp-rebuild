-- GECKO VPP — Postgres extension bootstrap.
-- Runs on first container init only (when pgdata is empty).

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
