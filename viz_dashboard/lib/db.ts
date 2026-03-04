import { Pool } from "pg";

const pool = new Pool({
  connectionString:
    process.env.DATABASE_URL || "postgresql://db_user:db_password@localhost:5432/db",
  ssl: process.env.DATABASE_URL ? { rejectUnauthorized: false } : false,
});

export default pool;
