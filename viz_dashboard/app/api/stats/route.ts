import { NextResponse } from "next/server";
import pool from "@/lib/db";

export const revalidate = 300; // Cache for 5 minutes

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type") || "producer";
  const startYear = parseInt(searchParams.get("startYear") || "2020");
  const startWeek = parseInt(searchParams.get("startWeek") || "1");
  const endYear = parseInt(searchParams.get("endYear") || "2026");
  const endWeek = parseInt(searchParams.get("endWeek") || "53");
  const rankLimit = parseInt(searchParams.get("rankLimit") || "200");

  try {
    let entitySelect = "";

    if (type === "producer") {
      entitySelect = `
        SELECT p.name, s.titre, a.name AS artiste, ce.annee, ce.semaine, ce.classement AS rang
        FROM chart_entries ce
        JOIN songs s ON ce.song_id = s.id
        JOIN song_producers sp ON s.id = sp.song_id
        JOIN producers p ON sp.producer_id = p.id
        JOIN song_artists sa ON s.id = sa.song_id AND sa.position = 1
        JOIN artists a ON sa.artist_id = a.id
      `;
    } else if (type === "editeur") {
      entitySelect = `
        SELECT l.name, s.titre, a.name AS artiste, ce.annee, ce.semaine, ce.classement AS rang
        FROM chart_entries ce
        JOIN songs s ON ce.song_id = s.id
        JOIN labels l ON s.label_id = l.id
        JOIN song_artists sa ON s.id = sa.song_id AND sa.position = 1
        JOIN artists a ON sa.artist_id = a.id
      `;
    } else {
      entitySelect = `
        SELECT ar.name, s.titre, a_main.name AS artiste, ce.annee, ce.semaine, ce.classement AS rang
        FROM chart_entries ce
        JOIN songs s ON ce.song_id = s.id
        JOIN song_artists sa ON s.id = sa.song_id
        JOIN artists ar ON sa.artist_id = ar.id
        JOIN song_artists sa_main ON s.id = sa_main.song_id AND sa_main.position = 1
        JOIN artists a_main ON sa_main.artist_id = a_main.id
      `;
    }

    const query = `
      WITH entities AS (
        ${entitySelect}
        WHERE (ce.annee > $1 OR (ce.annee = $1 AND ce.semaine >= $2))
          AND (ce.annee < $3 OR (ce.annee = $3 AND ce.semaine <= $4))
          AND ce.classement <= $5
      ),
      stats AS (
        SELECT
          name,
          COUNT(DISTINCT titre || ' - ' || artiste) AS distinct_songs
        FROM entities
        GROUP BY name
      )
      SELECT
        s.name,
        s.distinct_songs,
        e.annee,
        e.semaine,
        e.titre
      FROM stats s
      JOIN entities e ON s.name = e.name
      ORDER BY s.distinct_songs DESC
    `;

    const result = await pool.query(query, [
      startYear,
      startWeek,
      endYear,
      endWeek,
      rankLimit,
    ]);

    const entityStats: Record<
      string,
      {
        name: string;
        distinct_songs: number;
        weeks: { year: number; week: number; title: string }[];
      }
    > = {};

    result.rows.forEach((row) => {
      if (!entityStats[row.name]) {
        entityStats[row.name] = {
          name: row.name,
          distinct_songs: parseInt(row.distinct_songs),
          weeks: [],
        };
      }
      entityStats[row.name].weeks.push({
        year: row.annee,
        week: row.semaine,
        title: row.titre,
      });
    });

    const finalStats = Object.values(entityStats).map((p) => {
      const songWeeks: Record<string, { year: number; week: number }[]> = {};
      p.weeks.forEach((w) => {
        if (!songWeeks[w.title]) songWeeks[w.title] = [];
        songWeeks[w.title].push({ year: w.year, week: w.week });
      });

      let maxSongStreak = 0;
      let maxSongName: string | null = null;

      Object.entries(songWeeks).forEach(([title, weeks]) => {
        if (weeks.length > maxSongStreak) {
          maxSongStreak = weeks.length;
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
