import { NextResponse } from "next/server";
import pool from "@/lib/db";

export async function GET() {
  try {
    const query = `
      SELECT
        COALESCE(g.genre, 'Non classé') AS genre,
        COUNT(*) AS count
      FROM songs s
      LEFT JOIN song_genres g ON s.id = g.song_id
      GROUP BY genre
      ORDER BY count DESC
    `;

    const result = await pool.query(query);
    return NextResponse.json(result.rows);
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 }
    );
  }
}
