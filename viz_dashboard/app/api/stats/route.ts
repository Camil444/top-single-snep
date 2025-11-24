import { NextResponse } from "next/server";
import pool from "@/lib/db";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type") || "producer"; // 'producer' or 'artist'
  const startYear = parseInt(searchParams.get("startYear") || "2020");
  const startWeek = parseInt(searchParams.get("startWeek") || "1");
  const endYear = parseInt(searchParams.get("endYear") || "2025");
  const endWeek = parseInt(searchParams.get("endWeek") || "53");
  const rankLimit = parseInt(searchParams.get("rankLimit") || "200");

  try {
    // Construct the UNION ALL query dynamically based on available years
    // We know the years are 2020-2025
    const years = [2020, 2021, 2022, 2023, 2024, 2025];
    const unionQuery = years
      .map((y) => `SELECT * FROM top_singles_${y}`)
      .join(" UNION ALL ");

    let entityQuery = "";
    if (type === "producer") {
      entityQuery = `
        SELECT UPPER(TRIM(producer_1)) as name, titre, artiste, annee, semaine, classement as rang FROM all_data WHERE producer_1 IS NOT NULL AND TRIM(producer_1) <> ''
        UNION ALL
        SELECT UPPER(TRIM(producer_2)) as name, titre, artiste, annee, semaine, classement as rang FROM all_data WHERE producer_2 IS NOT NULL AND TRIM(producer_2) <> ''
      `;
    } else {
      entityQuery = `
        SELECT UPPER(TRIM(artiste)) as name, titre, artiste, annee, semaine, classement as rang FROM all_data WHERE artiste IS NOT NULL AND TRIM(artiste) <> ''
        UNION ALL
        SELECT UPPER(TRIM(artiste_2)) as name, titre, artiste, annee, semaine, classement as rang FROM all_data WHERE artiste_2 IS NOT NULL AND TRIM(artiste_2) <> ''
        UNION ALL
        SELECT UPPER(TRIM(artiste_3)) as name, titre, artiste, annee, semaine, classement as rang FROM all_data WHERE artiste_3 IS NOT NULL AND TRIM(artiste_3) <> ''
        UNION ALL
        SELECT UPPER(TRIM(artiste_4)) as name, titre, artiste, annee, semaine, classement as rang FROM all_data WHERE artiste_4 IS NOT NULL AND TRIM(artiste_4) <> ''
      `;
    }

    const query = `
      WITH all_data AS (${unionQuery}),
      entities AS (
        ${entityQuery}
      ),
      filtered_entities AS (
        SELECT * FROM entities
        WHERE (annee > $1 OR (annee = $1 AND semaine >= $2))
          AND (annee < $3 OR (annee = $3 AND semaine <= $4))
          AND rang <= $5
      ),
      stats AS (
        SELECT 
          name,
          COUNT(DISTINCT titre || ' - ' || artiste) as distinct_songs
        FROM filtered_entities
        GROUP BY name
      ),
      weeks_active AS (
        SELECT name, annee, semaine, titre
        FROM filtered_entities
      )
      SELECT 
        s.name,
        s.distinct_songs,
        wa.annee,
        wa.semaine,
        wa.titre
      FROM stats s
      JOIN weeks_active wa ON s.name = wa.name
      ORDER BY s.distinct_songs DESC
    `;

    const result = await pool.query(query, [
      startYear,
      startWeek,
      endYear,
      endWeek,
      rankLimit,
    ]);

    // Process streaks in JavaScript
    const producerStats: Record<
      string,
      {
        name: string;
        distinct_songs: number;
        weeks: { year: number; week: number; title: string }[];
      }
    > = {};

    result.rows.forEach((row) => {
      if (!producerStats[row.name]) {
        producerStats[row.name] = {
          name: row.name,
          distinct_songs: parseInt(row.distinct_songs),
          weeks: [],
        };
      }
      producerStats[row.name].weeks.push({
        year: row.annee,
        week: row.semaine,
        title: row.titre,
      });
    });

    // Calculate longest streak for each producer
    const finalStats = Object.values(producerStats).map((p) => {
      // Group weeks by song title
      const songWeeks: Record<string, { year: number; week: number }[]> = {};
      p.weeks.forEach((w) => {
        if (!songWeeks[w.title]) {
          songWeeks[w.title] = [];
        }
        songWeeks[w.title].push({ year: w.year, week: w.week });
      });

      let maxSongStreak = 0;
      let maxSongName: string | null = null;

      // Calculate max weeks for each song
      Object.entries(songWeeks).forEach(([title, weeks]) => {
        const totalWeeks = weeks.length;

        if (totalWeeks > maxSongStreak) {
          maxSongStreak = totalWeeks;
          maxSongName = title;
        }
      });

      return {
        name: p.name,
        distinct_songs: p.distinct_songs,
        longest_streak: maxSongStreak,
        top_streak_song: maxSongName,
      };
    });

    // Sort by distinct songs and take top 50 (to be safe, UI will show top 5)
    finalStats.sort((a, b) => b.distinct_songs - a.distinct_songs);

    return NextResponse.json(finalStats);
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 }
    );
  }
}
