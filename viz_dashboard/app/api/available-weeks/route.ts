import { NextResponse } from "next/server";
import { Client } from "pg";

export async function GET() {
  const client = new Client({
    connectionString:
      process.env.DATABASE_URL || "postgresql://db_user:db_password@localhost:5432/db",
    ssl: process.env.DATABASE_URL ? { rejectUnauthorized: false } : false,
  });

  try {
    await client.connect();
    const result = await client.query(`
      SELECT annee, MIN(semaine) AS min_week, MAX(semaine) AS max_week
      FROM public.chart_entries
      GROUP BY annee
      ORDER BY annee
    `);

    const limits: Record<number, { min: number; max: number }> = {};
    result.rows.forEach((row) => {
      limits[row.annee] = {
        min: row.min_week,
        max: row.max_week,
      };
    });

    return NextResponse.json(limits);
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  } finally {
    await client.end();
  }
}
