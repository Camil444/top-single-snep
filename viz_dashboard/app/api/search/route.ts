import { NextResponse } from "next/server";
import pool from "@/lib/db";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const query = searchParams.get("q");
  const type = searchParams.get("type") || "artist";

  if (!query || query.length < 2) {
    return NextResponse.json([]);
  }

  try {
    const years = [2020, 2021, 2022, 2023, 2024, 2025];
    const unionQuery = years
      .map((y) => `SELECT * FROM top_singles_${y}`)
      .join(" UNION ALL ");

    let columnQuery = "";
    if (type === "producer") {
      columnQuery = `
            SELECT DISTINCT producer_1 as name FROM all_data WHERE producer_1 ILIKE $1
            UNION
            SELECT DISTINCT producer_2 as name FROM all_data WHERE producer_2 ILIKE $1
        `;
    } else if (type === "editeur") {
      columnQuery = `SELECT DISTINCT editeur as name FROM all_data WHERE editeur ILIKE $1`;
    } else {
      columnQuery = `
            SELECT DISTINCT artiste as name FROM all_data WHERE artiste ILIKE $1
            UNION
            SELECT DISTINCT artiste_2 as name FROM all_data WHERE artiste_2 ILIKE $1
            UNION
            SELECT DISTINCT artiste_3 as name FROM all_data WHERE artiste_3 ILIKE $1
            UNION
            SELECT DISTINCT artiste_4 as name FROM all_data WHERE artiste_4 ILIKE $1
        `;
    }

    const sql = `
        WITH all_data AS (${unionQuery})
        SELECT DISTINCT name FROM (
            ${columnQuery}
        ) t
        WHERE name IS NOT NULL AND name <> ''
        ORDER BY name
        LIMIT 10
    `;

    const result = await pool.query(sql, [`%${query}%`]);
    return NextResponse.json(result.rows.map((r) => r.name));
  } catch (error) {
    console.error(error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 }
    );
  }
}
