"use client";

import { useState, useEffect } from "react";
import {
  Mic,
  Music,
  Trophy,
  TrendingUp,
  Calendar,
  Moon,
  Sun,
  X,
} from "lucide-react";

interface Stat {
  name: string;
  distinct_songs: number;
  longest_streak: number;
  top_streak_song?: string;
}

interface SongDetail {
  titre: string;
  artiste: string;
  best_rank: number;
  first_year: number;
  max_streak: number;
  total_weeks: number;
}

function ArtistImage({
  name,
  size = "small",
  className,
}: {
  name: string;
  size?: "small" | "large";
  className?: string;
}) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!name) return;
    const cached = sessionStorage.getItem(`artist_img_${name}`);
    if (cached) {
      setImageUrl(cached);
      return;
    }

    fetch(`/api/artist-image?artist=${encodeURIComponent(name)}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.imageUrl) {
          setImageUrl(data.imageUrl);
          sessionStorage.setItem(`artist_img_${name}`, data.imageUrl);
        }
      })
      .catch((err) => console.error(err));
  }, [name]);

  const sizeClasses =
    size === "large" ? "w-32 h-32 text-3xl" : "w-10 h-10 text-xs";
  const imgClasses =
    size === "large"
      ? "w-32 h-32 border-4 border-white dark:border-[#171717] shadow-xl"
      : "w-10 h-10";

  if (!imageUrl)
    return (
      <div
        className={`rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-gray-500 dark:text-gray-400 shrink-0 ${
          className || sizeClasses
        }`}
      >
        {name.substring(0, 2)}
      </div>
    );

  return (
    <img
      src={imageUrl}
      alt={name}
      className={`rounded-full object-cover border border-gray-200 dark:border-gray-700 shrink-0 ${
        className || imgClasses
      }`}
    />
  );
}

function ArtistModal({
  name,
  type,
  startYear,
  startWeek,
  endYear,
  endWeek,
  rankLimit,
  onClose,
}: {
  name: string;
  type: string;
  startYear: number;
  startWeek: number;
  endYear: number;
  endWeek: number;
  rankLimit: number;
  onClose: () => void;
}) {
  const [songs, setSongs] = useState<SongDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<"rank" | "streak">("rank");

  useEffect(() => {
    // Fetch top songs
    const params = new URLSearchParams({
      name,
      type,
      startYear: startYear.toString(),
      startWeek: startWeek.toString(),
      endYear: endYear.toString(),
      endWeek: endWeek.toString(),
      rankLimit: rankLimit.toString(),
    });

    fetch(`/api/artist-details?${params}`)
      .then((res) => res.json())
      .then((data) => {
        setSongs(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, [name, type, startYear, startWeek, endYear, endWeek]);

  const sortedSongs = [...songs].sort((a, b) => {
    if (sortBy === "rank") return a.best_rank - b.best_rank;
    return b.total_weeks - a.total_weeks;
  });

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-[#171717] rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="relative h-32 bg-gradient-to-r from-blue-500 to-purple-600">
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="absolute top-4 right-4 p-2 bg-black/20 hover:bg-black/40 rounded-full text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="absolute -bottom-16 left-6">
            <ArtistImage name={name} size="large" />
          </div>
        </div>

        <div className="pt-20 px-6 pb-6">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
            {name}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-6 capitalize">
            {type === "producer" ? "Producteur" : "Artiste"}
          </p>

          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Trophy className="w-4 h-4 text-yellow-500" />
              Titres classés
            </h3>
            <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
              <button
                onClick={() => setSortBy("rank")}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                  sortBy === "rank"
                    ? "bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm"
                    : "text-gray-500 dark:text-gray-400"
                }`}
              >
                Meilleur Rang
              </button>
              <button
                onClick={() => setSortBy("streak")}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                  sortBy === "streak"
                    ? "bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm"
                    : "text-gray-500 dark:text-gray-400"
                }`}
              >
                Longévité
              </button>
            </div>
          </div>

          <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2">
            {loading
              ? [...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="h-12 bg-gray-100 dark:bg-gray-700/50 rounded-lg animate-pulse"
                  />
                ))
              : sortedSongs.map((song, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-700/30 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
                  >
                    <div className="flex items-center gap-3 overflow-hidden">
                      <span
                        className={`
                      w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0
                      ${
                        song.best_rank <= 10
                          ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-400"
                          : "bg-gray-200 text-gray-600 dark:bg-gray-600 dark:text-gray-300"
                      }
                    `}
                      >
                        {song.best_rank}
                      </span>
                      <div className="min-w-0">
                        <p className="font-medium text-gray-900 dark:text-white truncate text-sm">
                          {song.titre}{" "}
                          <span className="text-gray-500 dark:text-gray-400 font-normal">
                            - {song.artiste}
                          </span>
                        </p>
                        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                          <span>{song.first_year}</span>
                          <span>•</span>
                          <span className="text-blue-600 dark:text-blue-400">
                            {song.total_weeks} semaines
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Podium({
  top3,
  onSelect,
}: {
  top3: Stat[];
  onSelect: (name: string) => void;
}) {
  if (top3.length < 3) return null;

  const [first, second, third] = top3;

  return (
    <div className="flex justify-center items-end gap-4 sm:gap-8 mb-12 mt-8">
      {/* Second Place */}
      <div
        className="flex flex-col items-center cursor-pointer group"
        onClick={() => onSelect(second.name)}
      >
        <div className="relative">
          <div className="w-32 h-32 sm:w-40 sm:h-40 rounded-full border-4 border-gray-200 dark:border-gray-700 overflow-hidden shadow-lg transition-transform group-hover:scale-105">
            <ArtistImage
              name={second.name}
              className="w-full h-full object-cover"
            />
          </div>
          <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 font-bold rounded-full w-10 h-10 flex items-center justify-center border-2 border-white dark:border-[#171717] z-10">
            2
          </div>
        </div>
        <p className="mt-4 font-semibold text-gray-900 dark:text-white text-center max-w-[120px] truncate">
          {second.name}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {second.distinct_songs} titres
        </p>
      </div>

      {/* First Place */}
      <div
        className="flex flex-col items-center cursor-pointer group -translate-y-8"
        onClick={() => onSelect(first.name)}
      >
        <div className="relative">
          <div className="w-40 h-40 sm:w-52 sm:h-52 rounded-full border-4 border-yellow-400 overflow-hidden shadow-xl transition-transform group-hover:scale-105">
            <ArtistImage
              name={first.name}
              className="w-full h-full object-cover"
            />
          </div>
          <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 bg-yellow-400 text-yellow-900 font-bold rounded-full w-12 h-12 flex items-center justify-center border-4 border-white dark:border-[#171717] z-10 text-xl">
            1
          </div>
        </div>
        <p className="mt-5 font-bold text-xl text-gray-900 dark:text-white text-center max-w-[160px] truncate">
          {first.name}
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {first.distinct_songs} titres
        </p>
      </div>

      {/* Third Place */}
      <div
        className="flex flex-col items-center cursor-pointer group"
        onClick={() => onSelect(third.name)}
      >
        <div className="relative">
          <div className="w-32 h-32 sm:w-40 sm:h-40 rounded-full border-4 border-orange-300 overflow-hidden shadow-lg transition-transform group-hover:scale-105">
            <ArtistImage
              name={third.name}
              className="w-full h-full object-cover"
            />
          </div>
          <div className="absolute -bottom-3 left-1/2 -translate-x-1/2 bg-orange-300 text-orange-900 font-bold rounded-full w-10 h-10 flex items-center justify-center border-2 border-white dark:border-[#171717] z-10">
            3
          </div>
        </div>
        <p className="mt-4 font-semibold text-gray-900 dark:text-white text-center max-w-[120px] truncate">
          {third.name}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {third.distinct_songs} titres
        </p>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<"producer" | "artist" | "genre">(
    "producer"
  );
  const [stats, setStats] = useState<Stat[]>([]);
  const [genres, setGenres] = useState<{ genre: string; count: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [selectedArtist, setSelectedArtist] = useState<string | null>(null);

  // Filter state
  const [startYear, setStartYear] = useState(2020);
  const [startWeek, setStartWeek] = useState(1);
  const [endYear, setEndYear] = useState(2025);
  const [endWeek, setEndWeek] = useState(53);
  const [rankLimit, setRankLimit] = useState(200);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [darkMode]);

  useEffect(() => {
    if (activeTab === "genre") {
      fetchGenres();
    } else {
      fetchStats();
    }
  }, [activeTab, startYear, startWeek, endYear, endWeek, rankLimit]);

  const fetchGenres = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/genres");
      if (!res.ok) throw new Error("Failed to fetch genres");
      const data = await res.json();
      setGenres(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        type: activeTab,
        startYear: startYear.toString(),
        startWeek: startWeek.toString(),
        endYear: endYear.toString(),
        endWeek: endWeek.toString(),
        rankLimit: rankLimit.toString(),
      });
      const res = await fetch(`/api/stats?${params}`);
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        setStats(data);
      } else {
        console.error("Received invalid data format:", data);
        setStats([]);
      }
    } catch (error) {
      console.error("Failed to fetch stats", error);
      setStats([]);
    } finally {
      setLoading(false);
    }
  };

  const top10 = stats.slice(0, 10);
  const top3 = top10.slice(0, 3);
  const rest = top10.slice(3);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-[#0a0a0a] p-8 font-sans text-gray-900 dark:text-gray-100 transition-colors duration-200">
      {selectedArtist && (
        <ArtistModal
          name={selectedArtist}
          type={activeTab}
          startYear={startYear}
          startWeek={startWeek}
          endYear={endYear}
          endWeek={endWeek}
          rankLimit={rankLimit}
          onClose={() => setSelectedArtist(null)}
        />
      )}
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white uppercase tracking-wide">
              FRENCH TOP CHARTS ANALYTICS
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1 text-sm">
              Sources: SNEP & Genius API • Last Update:{" "}
              <span suppressHydrationWarning>
                {new Date().toLocaleDateString()}
              </span>
            </p>
          </div>

          <div className="flex items-center gap-4">
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 rounded-full bg-white dark:bg-[#171717] border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
              aria-label="Toggle dark mode"
            >
              {darkMode ? (
                <Sun className="w-5 h-5" />
              ) : (
                <Moon className="w-5 h-5" />
              )}
            </button>

            {/* Filters */}
            <div className="bg-white dark:bg-[#171717] p-4 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 flex flex-wrap gap-4 items-end">
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Classement
                </label>
                <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                  <button
                    onClick={() => setRankLimit(50)}
                    className={`px-3 py-1 text-sm font-medium rounded-md transition-all ${
                      rankLimit === 50
                        ? "bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm"
                        : "text-gray-500 dark:text-gray-400"
                    }`}
                  >
                    Top 50
                  </button>
                  <button
                    onClick={() => setRankLimit(200)}
                    className={`px-3 py-1 text-sm font-medium rounded-md transition-all ${
                      rankLimit === 200
                        ? "bg-white dark:bg-gray-600 text-blue-600 dark:text-blue-400 shadow-sm"
                        : "text-gray-500 dark:text-gray-400"
                    }`}
                  >
                    Top 200
                  </button>
                </div>
              </div>
              <div className="w-px h-10 bg-gray-200 dark:bg-gray-700 mx-2"></div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Début
                </label>
                <div className="flex gap-2">
                  <select
                    aria-label="Année de début"
                    value={startYear}
                    onChange={(e) => setStartYear(Number(e.target.value))}
                    className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                  >
                    {[2020, 2021, 2022, 2023, 2024, 2025].map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))}
                  </select>
                  <input
                    aria-label="Semaine de début"
                    type="number"
                    min="1"
                    max="53"
                    value={startWeek}
                    onChange={(e) => setStartWeek(Number(e.target.value))}
                    className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md px-3 py-1.5 text-sm w-16 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                  />
                </div>
              </div>
              <div className="text-gray-300 dark:text-gray-600 pb-2">→</div>
              <div className="space-y-1">
                <label className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Fin
                </label>
                <div className="flex gap-2">
                  <select
                    aria-label="Année de fin"
                    value={endYear}
                    onChange={(e) => setEndYear(Number(e.target.value))}
                    className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                  >
                    {[2020, 2021, 2022, 2023, 2024, 2025].map((y) => (
                      <option key={y} value={y}>
                        {y}
                      </option>
                    ))}
                  </select>
                  <input
                    aria-label="Semaine de fin"
                    type="number"
                    min="1"
                    max="53"
                    value={endWeek}
                    onChange={(e) => setEndWeek(Number(e.target.value))}
                    className="bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md px-3 py-1.5 text-sm w-16 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:text-white"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex p-1 bg-gray-200 dark:bg-[#171717] rounded-lg w-fit">
          <button
            onClick={() => setActiveTab("producer")}
            className={`px-6 py-2.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === "producer"
                ? "bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
            }`}
          >
            <Music className="w-4 h-4" />
            Producteurs (Beatmakers)
          </button>
          <button
            onClick={() => setActiveTab("artist")}
            className={`px-6 py-2.5 rounded-md text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
              activeTab === "artist"
                ? "bg-white dark:bg-gray-700 text-purple-600 dark:text-purple-400 shadow-sm"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
            }`}
          >
            <Mic className="w-4 h-4" />
            Artistes
          </button>
        </div>

        {/* Content */}
        {activeTab === "genre" ? (
          <div className="bg-white dark:bg-[#171717] rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6 flex items-center gap-2">
              <Trophy className="w-5 h-5 text-green-500" />
              Répartition par Genre Musical
            </h2>
            <div className="space-y-4">
              {loading
                ? [...Array(5)].map((_, i) => (
                    <div
                      key={i}
                      className="h-8 bg-gray-100 dark:bg-gray-700 rounded animate-pulse"
                    />
                  ))
                : genres.map((g, i) => (
                    <div key={i} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium text-gray-900 dark:text-white">
                          {g.genre}
                        </span>
                        <span className="text-gray-500 dark:text-gray-400">
                          {g.count} titres
                        </span>
                      </div>
                      <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500 rounded-full"
                          style={{
                            width: `${
                              (g.count /
                                Math.max(...genres.map((x) => x.count))) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Top 10 Card */}
            <div className="lg:col-span-2 bg-white dark:bg-[#171717] rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
              <div className="p-6 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Trophy
                    className={`w-5 h-5 ${
                      activeTab === "producer"
                        ? "text-yellow-500"
                        : "text-purple-500"
                    }`}
                  />
                  Top 10 {activeTab === "producer" ? "Producteurs" : "Artistes"}
                </h2>
                <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                  Par titres distincts
                </span>
              </div>

              {!loading && top3.length === 3 && (
                <Podium top3={top3} onSelect={setSelectedArtist} />
              )}

              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50/50 dark:bg-gray-700/50">
                    <tr>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Rang
                      </th>
                      <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Nom
                      </th>
                      <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Titres Distincts
                      </th>
                      <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Série Max (Semaines)
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                    {loading
                      ? [...Array(10)].map((_, i) => (
                          <tr key={i} className="animate-pulse">
                            <td className="px-6 py-4">
                              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-8"></div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-12 ml-auto"></div>
                            </td>
                            <td className="px-6 py-4">
                              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-12 ml-auto"></div>
                            </td>
                          </tr>
                        ))
                      : rest.map((stat, index) => (
                          <tr
                            key={stat.name}
                            onClick={() => setSelectedArtist(stat.name)}
                            className="hover:bg-gray-50/50 dark:hover:bg-gray-700/50 transition-colors cursor-pointer group"
                          >
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span
                                className={`
                              inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700
                            `}
                              >
                                {index + 4}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap font-medium text-gray-900 dark:text-white flex items-center gap-3">
                              <ArtistImage name={stat.name} />
                              <span className="group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                {stat.name}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right font-semibold text-gray-900 dark:text-white">
                              {stat.distinct_songs}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-gray-600 dark:text-gray-400">
                              <div className="flex flex-col items-end">
                                <span className="font-medium text-gray-900 dark:text-white">
                                  {stat.longest_streak}
                                </span>
                                {stat.top_streak_song && (
                                  <span
                                    className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[150px]"
                                    title={stat.top_streak_song}
                                  >
                                    {stat.top_streak_song}
                                  </span>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Stats Card */}
            <div className="space-y-6">
              <div className="bg-gradient-to-br from-blue-500 to-blue-600 dark:from-blue-600 dark:to-blue-800 rounded-2xl shadow-lg p-6 text-white">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-white/20 rounded-lg">
                    <TrendingUp className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="font-semibold text-lg">Performance</h3>
                </div>
                <div className="space-y-4">
                  <div>
                    <p className="text-blue-100 text-sm">Record de longévité</p>
                    <div className="flex items-baseline gap-2 mt-1">
                      <span className="text-3xl font-bold">
                        {loading
                          ? "-"
                          : Math.max(...stats.map((s) => s.longest_streak), 0)}
                      </span>
                      <span className="text-blue-100 text-sm">
                        semaines au total
                      </span>
                    </div>
                    <div className="mt-2">
                      <p className="text-xs text-blue-200">
                        Détenu par{" "}
                        <span className="font-semibold">
                          {loading
                            ? "..."
                            : [...stats].sort(
                                (a, b) => b.longest_streak - a.longest_streak
                              )[0]?.name || "-"}
                        </span>
                      </p>
                      {stats.length > 0 &&
                        [...stats].sort(
                          (a, b) => b.longest_streak - a.longest_streak
                        )[0]?.top_streak_song && (
                          <p className="text-xs text-blue-200 mt-0.5 italic">
                            Principalement avec "
                            {
                              [...stats].sort(
                                (a, b) => b.longest_streak - a.longest_streak
                              )[0]?.top_streak_song
                            }
                            "
                          </p>
                        )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white dark:bg-[#171717] rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700 p-6">
                <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
                  Détails de la période
                </h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between py-2 border-b border-gray-50 dark:border-gray-700">
                    <span className="text-gray-500 dark:text-gray-400">
                      Début
                    </span>
                    <span className="font-medium dark:text-gray-200">
                      Semaine {startWeek}, {startYear}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-gray-50 dark:border-gray-700">
                    <span className="text-gray-500 dark:text-gray-400">
                      Fin
                    </span>
                    <span className="font-medium dark:text-gray-200">
                      Semaine {endWeek}, {endYear}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-gray-50 dark:border-gray-700">
                    <span className="text-gray-500 dark:text-gray-400">
                      Classement
                    </span>
                    <span className="font-medium dark:text-gray-200">
                      Top {rankLimit}
                    </span>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-gray-500 dark:text-gray-400">
                      Total analysé
                    </span>
                    <span className="font-medium text-blue-600 dark:text-blue-400">
                      {stats.length}{" "}
                      {activeTab === "producer" ? "producteurs" : "artistes"}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
