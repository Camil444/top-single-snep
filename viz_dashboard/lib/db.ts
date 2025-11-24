import { Pool } from "pg";

const pool = new Pool({
  user: "db_user",
  password: "db_password",
  host: "localhost",
  port: 5432,
  database: "db",
});

export default pool;
