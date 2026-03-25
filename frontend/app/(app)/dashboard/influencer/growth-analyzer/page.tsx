"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getCurrentUser } from "@/lib/user";
import { getCreatorSummary, getCachedCreatorSummary } from "@/lib/ai";
import { Button } from "@/components/ui/button";

interface CreatorSummary {
  creator_id?: string;
  summary?: string;
  strengths?: string[];
  improvement_areas?: string[];
  best_brand_categories?: string[];
  recommended_content_formats?: string[];
}

export default function GrowthAnalyzerPage() {
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [summary, setSummary] = useState<CreatorSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const data = await getCurrentUser();
        setUser(data);
      } catch {
        router.replace("/login");
      }
    }
    loadUser();
  }, [router]);

  useEffect(() => {
    async function initSummary() {
      try {
        const cached = await getCachedCreatorSummary();
        if (cached) {
          setSummary(cached);
        }
      } catch (err) {
        // Safe to ignore cache miss
      }
    }
    initSummary();
  }, []);

  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCreatorSummary();
      setSummary(data);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to generate summary. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#06070C] text-white">
      {/* Background Effects */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-[-20%] left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-cyan-500/20 blur-[140px] animate-[floatSlow_18s_ease-in-out_infinite]" />
        <div className="absolute bottom-[-30%] left-[10%] h-[500px] w-[500px] rounded-full bg-indigo-500/15 blur-[140px]" />
        <div className="absolute bottom-[-30%] right-[10%] h-[500px] w-[500px] rounded-full bg-purple-500/15 blur-[160px]" />
      </div>

      <main className="relative z-10 flex min-h-screen flex-col items-center px-6 py-16">
        {/* Header */}
        <div className="text-center max-w-2xl mb-12">
          <button
            onClick={() => router.back()}
            className="mb-8 flex items-center gap-2 text-sm text-gray-400 hover:text-white transition mx-auto"
          >
            ← Back
          </button>
          <h1 className="text-5xl md:text-6xl font-semibold tracking-tight">
            AI Growth Analyzer
          </h1>
          <p className="mt-4 text-lg text-gray-400">
            Get an AI-powered analysis of your creator profile — strengths, opportunities, and actionable insights.
          </p>
        </div>

        {/* Analyze Button */}
        {!summary && (
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="rounded-full bg-white px-10 py-4 text-base font-semibold text-black hover:bg-gray-100 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="flex items-center gap-3">
                <svg
                  className="animate-spin h-5 w-5 text-black"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Analyzing your profile...
              </span>
            ) : (
              "✦ Analyze My Profile"
            )}
          </button>
        )}

        {/* Error */}
        {error && (
          <div className="mt-8 max-w-xl w-full rounded-2xl border border-red-500/20 bg-red-500/10 px-6 py-5 text-center text-red-400">
            {error}
          </div>
        )}

        {/* Results */}
        {summary && (
          <div className="mt-10 w-full max-w-4xl space-y-6 animate-[fadeIn_0.6s_ease-in]">
            {/* Summary Card */}
            {summary.summary && (
              <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black p-8">
                <h2 className="text-xl font-semibold mb-3 text-cyan-400">📋 Profile Summary</h2>
                <p className="text-gray-300 leading-relaxed text-base">{summary.summary}</p>
              </div>
            )}

            <div className="grid md:grid-cols-2 gap-6">
              {/* Strengths */}
              {summary.strengths && summary.strengths.length > 0 && (
                <SectionCard
                  title="💪 Strengths"
                  items={summary.strengths}
                  accentClass="text-green-400"
                  dotClass="bg-green-400"
                />
              )}

              {/* Improvement Areas */}
              {summary.improvement_areas && summary.improvement_areas.length > 0 && (
                <SectionCard
                  title="🎯 Areas to Improve"
                  items={summary.improvement_areas}
                  accentClass="text-amber-400"
                  dotClass="bg-amber-400"
                />
              )}

              {/* Best Brand Categories */}
              {summary.best_brand_categories && summary.best_brand_categories.length > 0 && (
                <SectionCard
                  title="🏷️ Best Brand Categories"
                  items={summary.best_brand_categories}
                  accentClass="text-indigo-400"
                  dotClass="bg-indigo-400"
                />
              )}

              {/* Recommended Content Formats */}
              {summary.recommended_content_formats && summary.recommended_content_formats.length > 0 && (
                <SectionCard
                  title="🎬 Recommended Content Formats"
                  items={summary.recommended_content_formats}
                  accentClass="text-purple-400"
                  dotClass="bg-purple-400"
                />
              )}
            </div>

            {/* Re-analyze */}
            <div className="flex justify-center pt-4">
              <button
                onClick={handleAnalyze}
                disabled={loading}
                className="rounded-full border border-white/20 px-8 py-3 text-sm text-gray-300 hover:bg-white/10 transition disabled:opacity-50"
              >
                {loading ? "Analyzing..." : "↺ Re-Analyze"}
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function SectionCard({
  title,
  items,
  accentClass,
  dotClass,
}: {
  title: string;
  items: string[];
  accentClass: string;
  dotClass: string;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0E1220] to-black p-6">
      <h2 className={`text-lg font-semibold mb-4 ${accentClass}`}>{title}</h2>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-3 text-gray-300 text-sm">
            <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dotClass}`} />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
