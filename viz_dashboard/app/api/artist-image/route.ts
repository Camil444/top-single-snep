import { NextResponse } from "next/server";

const GENIUS_ACCESS_TOKEN = process.env.GENIUS_ACCESS_TOKEN;

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const artist = searchParams.get("artist");

  if (!artist) {
    return NextResponse.json(
      { error: "Artist name is required" },
      { status: 400 }
    );
  }

  // Special case for JUL using local image
  if (artist.toUpperCase() === "JUL") {
    return NextResponse.json({ imageUrl: "/jul_picture.jpg" });
  }

  // Special case for SCH using local image
  if (artist.toUpperCase() === "SCH") {
    return NextResponse.json({ imageUrl: "/sch_picture.jpg" });
  }

  if (!GENIUS_ACCESS_TOKEN) {
    console.warn("GENIUS_ACCESS_TOKEN is not set");
    return NextResponse.json({ imageUrl: null });
  }

  try {
    const res = await fetch(
      `https://api.genius.com/search?q=${encodeURIComponent(artist)}`,
      {
        headers: {
          Authorization: `Bearer ${GENIUS_ACCESS_TOKEN}`,
        },
      }
    );

    if (!res.ok) {
      throw new Error(`Genius API error: ${res.statusText}`);
    }

    const data = await res.json();
    if (!data || !data.response || !data.response.hits) {
      console.log("No hits found or invalid response");
      return NextResponse.json({ imageUrl: null });
    }
    const hits = data.response.hits;
    // console.log(`Found ${hits ? hits.length : 0} hits for ${artist}`);

    if (hits && hits.length > 0) {
      // Filter for exact artist match first
      const exactMatch = hits.find(
        (hit: any) =>
          hit.result.primary_artist.name.toLowerCase() === artist.toLowerCase()
      );

      if (exactMatch) {
        // console.log("Found exact match");
        return NextResponse.json({
          imageUrl: exactMatch.result.primary_artist.image_url,
        });
      }

      // If no exact match in primary_artist, check producers/featured in the first few hits
      // We need to fetch song details for this
      for (const hit of hits.slice(0, 5)) {
        try {
          // console.log(`Fetching song ${hit.result.id}`);
          const songRes = await fetch(
            `https://api.genius.com/songs/${hit.result.id}`,
            {
              headers: {
                Authorization: `Bearer ${GENIUS_ACCESS_TOKEN}`,
              },
            }
          );

          if (songRes.ok) {
            const songData = await songRes.json();
            if (songData && songData.response && songData.response.song) {
              const song = songData.response.song;

              // Check producer_artists
              if (song.producer_artists) {
                const producerMatch = song.producer_artists.find(
                  (p: any) => p.name.toLowerCase() === artist.toLowerCase()
                );
                if (producerMatch) {
                  // console.log("Found producer match");
                  return NextResponse.json({
                    imageUrl: producerMatch.image_url,
                  });
                }
              }

              // Check featured_artists
              if (song.featured_artists) {
                const featuredMatch = song.featured_artists.find(
                  (p: any) => p.name.toLowerCase() === artist.toLowerCase()
                );
                if (featuredMatch) {
                  // console.log("Found featured match");
                  return NextResponse.json({
                    imageUrl: featuredMatch.image_url,
                  });
                }
              }
            }
          }
        } catch (e) {
          console.error("Error fetching song details", e);
        }
      }

      // Fallback to the first hit if no exact match
      // console.log("Fallback to first hit");
      const hit = hits[0];
      const imageUrl = hit.result.primary_artist.image_url;
      return NextResponse.json({ imageUrl });
    }

    return NextResponse.json({ imageUrl: null });
  } catch (error) {
    console.error("Error fetching artist image:", error);
    return NextResponse.json({ imageUrl: null });
  }
}
