import { NextResponse } from "next/server";
import pool from "@/lib/db";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const artistName = searchParams.get("name");
  const type = searchParams.get("type") || "artist"; // 'artist' or 'producer'
  const startYear = parseInt(searchParams.get("startYear") || "2020");
  const startWeek = parseInt(searchParams.get("startWeek") || "1");
  const endYear = parseInt(searchParams.get("endYear") || "2025");
  const endWeek = parseInt(searchParams.get("endWeek") || "53");
  const rankLimit = parseInt(searchParams.get("rankLimit") || "200");

  if (!artistName) {
    return NextResponse.json(
      { error: "Artist name is required" },
      { status: 400 }
    );
  }

  try {
    const years = [2020, 2021, 2022, 2023, 2024, 2025];
    const unionQuery = years
      .map((y) => `SELECT * FROM top_singles_${y}`)
      .join(" UNION ALL ");

    let whereClause = "";
    if (type === "producer") {
      whereClause = `(UPPER(producer_1) = UPPER($1) OR UPPER(producer_2) = UPPER($1))`;
    } else if (type === "editeur") {
      whereClause = `(UPPER(editeur) = UPPER($1))`;
    } else {
      whereClause = `(UPPER(artiste) = UPPER($1) OR UPPER(artiste_2) = UPPER($1) OR UPPER(artiste_3) = UPPER($1) OR UPPER(artiste_4) = UPPER($1))`;
    }

    // Query to get all occurrences of the artist's songs
    const query = `
      WITH all_data AS (${unionQuery})
      SELECT 
        titre,
        artiste,
        classement,
        annee,
        semaine
      FROM all_data
      WHERE ${whereClause}
      AND (
        (annee > $2 OR (annee = $2 AND semaine >= $3))
        AND
        (annee < $4 OR (annee = $4 AND semaine <= $5))
      )
      AND classement <= $6
    `;

    const result = await pool.query(query, [
      artistName,
      startYear,
      startWeek,
      endYear,
      endWeek,
      rankLimit,
    ]);

    // Process in JS to calculate stats per song
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
      const key = row.titre; // Group by title (and maybe artist if needed, but usually title is enough for one artist context)
      if (!songStats[key]) {
        songStats[key] = {
          titre: row.titre,
          artiste: row.artiste,
          best_rank: row.classement,
          first_year: row.annee,
          weeks: [],
        };
      }

      // Update best rank
      if (row.classement < songStats[key].best_rank) {
        songStats[key].best_rank = row.classement;
      }
      // Update first year
      if (row.annee < songStats[key].first_year) {
        songStats[key].first_year = row.annee;
      }

      songStats[key].weeks.push({ year: row.annee, week: row.semaine });
    });

    // Calculate streaks for each song
    const processedSongs = Object.values(songStats).map((song) => {
      // Sort weeks
      song.weeks.sort((a, b) => (a.year - b.year) * 100 + (a.week - b.week));

      let maxStreak = 0;
      let currentStreak = 0;
      let lastYear = -1;
      let lastWeek = -1;

      song.weeks.forEach((w) => {
        const currentYear = w.year;
        const currentWeek = w.week;

        let isConsecutive = false;
        if (lastYear === -1) {
          isConsecutive = false;
        } else if (currentYear === lastYear && currentWeek === lastWeek + 1) {
          isConsecutive = true;
        } else if (
          currentYear === lastYear + 1 &&
          currentWeek === 1 &&
          lastWeek >= 52
        ) {
          isConsecutive = true;
        } else if (currentYear === lastYear && currentWeek === lastWeek) {
          return; // Same week duplicate
        }

        if (lastYear === -1) {
          currentStreak = 1;
        } else if (isConsecutive) {
          currentStreak++;
        } else {
          if (currentStreak > maxStreak) maxStreak = currentStreak;
          currentStreak = 1;
        }
        lastYear = currentYear;
        lastWeek = currentWeek;
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

    // Return all songs (frontend will sort and limit)
    // But we can sort by best_rank by default
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
