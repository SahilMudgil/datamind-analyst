-- Enable vector extension in app_db
CREATE EXTENSION IF NOT EXISTS vector;

-- Create target demo database ecommerce_db
SELECT 'CREATE DATABASE ecommerce_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'ecommerce_db')\gexec

-- Connect to ecommerce_db and enable vector extension
\c ecommerce_db
CREATE EXTENSION IF NOT EXISTS vector;
