import { NextResponse } from "next/server";
import pool from "@/lib/db";

// Returns the min and max available week for each year in chart_entries
export async function GET() {
  try {
    const result = await pool.query(`
      SELECT annee, MIN(semaine) AS min_week, MAX(semaine) AS max_week
      FROM chart_entries
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
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 }
    );
  }
}
