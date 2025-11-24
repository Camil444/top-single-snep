import { NextResponse } from "next/server";
import pool from "@/lib/db";

export async function GET(request: Request) {
  try {
    // We need to join the yearly tables with the song_genres table
    // Since we don't have a single 'songs' table, we union them first
    const years = [2020, 2021, 2022, 2023, 2024, 2025];
    const unionQuery = years
      .map((y) => `SELECT titre, artiste FROM top_singles_${y}`)
      .join(" UNION ALL ");

    const query = `
      WITH all_songs AS (${unionQuery}),
      genre_counts AS (
        SELECT 
          COALESCE(g.genre, 'Non classé') as genre,
          COUNT(*) as count
        FROM all_songs s
        LEFT JOIN song_genres g ON s.titre = g.titre AND s.artiste = g.artiste
        GROUP BY genre
      )
      SELECT * FROM genre_counts
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
