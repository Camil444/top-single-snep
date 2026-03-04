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
    let sql = "";

    if (type === "producer") {
      sql = `SELECT name FROM producers WHERE name ILIKE $1 ORDER BY name LIMIT 10`;
    } else if (type === "editeur") {
      sql = `SELECT name FROM labels WHERE name ILIKE $1 ORDER BY name LIMIT 10`;
    } else {
      sql = `SELECT name FROM artists WHERE name ILIKE $1 ORDER BY name LIMIT 10`;
    }

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
