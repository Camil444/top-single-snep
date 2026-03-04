import { NextResponse } from "next/server";
import pool from "@/lib/db";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const artistName = searchParams.get("name");
  const type = searchParams.get("type") || "artist";
  const startYear = parseInt(searchParams.get("startYear") || "2020");
  const startWeek = parseInt(searchParams.get("startWeek") || "1");
  const endYear = parseInt(searchParams.get("endYear") || "2026");
  const endWeek = parseInt(searchParams.get("endWeek") || "53");
  const rankLimit = parseInt(searchParams.get("rankLimit") || "200");

  if (!artistName) {
    return NextResponse.json(
      { error: "Artist name is required" },
      { status: 400 }
    );
  }

  try {
    let query = "";

    if (type === "producer") {
      query = `
        SELECT s.titre, a_main.name AS artiste, ce.classement, ce.annee, ce.semaine
        FROM chart_entries ce
        JOIN songs s ON ce.song_id = s.id
        JOIN song_producers sp ON s.id = sp.song_id
        JOIN producers p ON sp.producer_id = p.id
        JOIN song_artists sa_main ON s.id = sa_main.song_id AND sa_main.position = 1
        JOIN artists a_main ON sa_main.artist_id = a_main.id
        WHERE UPPER(p.name) = UPPER($1)
          AND (ce.annee > $2 OR (ce.annee = $2 AND ce.semaine >= $3))
          AND (ce.annee < $4 OR (ce.annee = $4 AND ce.semaine <= $5))
          AND ce.classement <= $6
      `;
    } else if (type === "editeur") {
      query = `
        SELECT s.titre, a_main.name AS artiste, ce.classement, ce.annee, ce.semaine
        FROM chart_entries ce
        JOIN songs s ON ce.song_id = s.id
        JOIN labels l ON s.label_id = l.id
        JOIN song_artists sa_main ON s.id = sa_main.song_id AND sa_main.position = 1
        JOIN artists a_main ON sa_main.artist_id = a_main.id
        WHERE UPPER(l.name) = UPPER($1)
          AND (ce.annee > $2 OR (ce.annee = $2 AND ce.semaine >= $3))
          AND (ce.annee < $4 OR (ce.annee = $4 AND ce.semaine <= $5))
          AND ce.classement <= $6
      `;
    } else {
      query = `
        SELECT s.titre, a_main.name AS artiste, ce.classement, ce.annee, ce.semaine
        FROM chart_entries ce
        JOIN songs s ON ce.song_id = s.id
        JOIN song_artists sa ON s.id = sa.song_id
        JOIN artists ar ON sa.artist_id = ar.id
        JOIN song_artists sa_main ON s.id = sa_main.song_id AND sa_main.position = 1
        JOIN artists a_main ON sa_main.artist_id = a_main.id
        WHERE UPPER(ar.name) = UPPER($1)
          AND (ce.annee > $2 OR (ce.annee = $2 AND ce.semaine >= $3))
          AND (ce.annee < $4 OR (ce.annee = $4 AND ce.semaine <= $5))
          AND ce.classement <= $6
      `;
    }

    const result = await pool.query(query, [
      artistName,
      startYear,
      startWeek,
      endYear,
      endWeek,
      rankLimit,
    ]);

    const songStats: Record<
      string,
      {
        titre: string;
        artiste: string;
        best_rank: number;
        first_year: number;
        weeks: { year: number; week: number }[];
      }
    > = {};

    result.rows.forEach((row) => {
      const key = row.titre;
      if (!songStats[key]) {
        songStats[key] = {
          titre: row.titre,
          artiste: row.artiste,
          best_rank: row.classement,
          first_year: row.annee,
          weeks: [],
        };
      }
      if (row.classement < songStats[key].best_rank) {
        songStats[key].best_rank = row.classement;
      }
      if (row.annee < songStats[key].first_year) {
        songStats[key].first_year = row.annee;
      }
      songStats[key].weeks.push({ year: row.annee, week: row.semaine });
    });

    const processedSongs = Object.values(songStats).map((song) => {
      song.weeks.sort((a, b) => (a.year - b.year) * 100 + (a.week - b.week));

      let maxStreak = 0;
      let currentStreak = 0;
      let lastYear = -1;
      let lastWeek = -1;

      song.weeks.forEach((w) => {
        const isConsecutive =
          lastYear !== -1 &&
          ((w.year === lastYear && w.week === lastWeek + 1) ||
            (w.year === lastYear + 1 && w.week === 1 && lastWeek >= 52));

        if (lastYear === -1) {
          currentStreak = 1;
        } else if (w.year === lastYear && w.week === lastWeek) {
          return; // duplicate
        } else if (isConsecutive) {
          currentStreak++;
        } else {
          if (currentStreak > maxStreak) maxStreak = currentStreak;
          currentStreak = 1;
        }
        lastYear = w.year;
        lastWeek = w.week;
      });

      if (currentStreak > maxStreak) maxStreak = currentStreak;

      return {
        titre: song.titre,
        artiste: song.artiste,
        best_rank: song.best_rank,
        first_year: song.first_year,
        max_streak: maxStreak,
        total_weeks: song.weeks.length,
      };
    });

    processedSongs.sort((a, b) => a.best_rank - b.best_rank);

    return NextResponse.json(processedSongs);
  } catch (error) {
    console.error("Database error:", error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 }
    );
  }
}
