"use client";

import Image from "next/image";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import ParticipantsService from "~/app/services/participants";
import Loading from "~/components/Loading";
import Section from "~/components/Section";

type Voting = {
  id: number;
  title: string;
  status: string;
};

type Candidate = {
  id: number;
  name: string;
  image: string;
  location: string;
  vote_count: number;
  percentage: number;
  is_user_vote?: boolean;
};

type VotingResults = {
  voting: Voting;
  total_votes: number;
  current_vote: { id: number; participant: number } | null;
  leaders: Candidate[];
  candidates: Candidate[];
};

const POLL_INTERVAL_MS = 5000;

function formatUpdatedAt(date: Date | null) {
  if (!date) return "--:--:--";
  return date.toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function CandidateImage({ candidate }: { candidate: Candidate }) {
  return (
    <Image
      src={candidate.image || "/logo.png"}
      alt={candidate.name}
      width={88}
      height={88}
      className="h-20 w-20 rounded-2xl object-cover shadow-sm"
    />
  );
}

export default function LeaderboardPage() {
  const { t } = useTranslation("common");
  const [results, setResults] = useState<VotingResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const loadResults = useCallback(async (silent = false) => {
    if (silent) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const currentVotingResponse = await ParticipantsService.getCurrentVoting();
      const votingId = currentVotingResponse.data.id;
      const resultsResponse = await ParticipantsService.getVotingResults(votingId);
      setResults(resultsResponse.data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err: any) {
      if (!silent) setResults(null);
      if (err?.response?.status === 404) {
        setError(t("leaderboard.no_active_voting"));
      } else {
        setError(t("leaderboard.error"));
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [t]);

  useEffect(() => {
    loadResults(false);
    const interval = window.setInterval(() => loadResults(true), POLL_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [loadResults]);

  const leaders = results?.leaders ?? [];
  const leaderTitle = useMemo(() => {
    if (leaders.length > 1) return t("leaderboard.tied_leaders");
    return t("leaderboard.leader");
  }, [leaders.length, t]);

  return (
    <main className="min-h-screen bg-[#f7a817] bg-[url(/background.png)] bg-contain text-[#7a3507]">
      <Section>
        <div className="relative h-10">
          <Image
            className="absolute top-0 h-auto w-full"
            height={20}
            width={500}
            alt=""
            src="/oyu_2_small.png"
          />
        </div>

        <div className="mx-auto flex min-h-screen w-[92%] max-w-3xl flex-col gap-5 py-6">
          <header className="rounded-[28px] bg-white/95 p-5 shadow-[0_16px_50px_rgba(113,55,8,0.18)]">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-extrabold uppercase tracking-[0.18em] text-orange">
                  BAI QYMYZ
                </p>
                <h1 className="mt-2 text-3xl font-extrabold leading-tight text-orange">
                  {t("leaderboard.title")}
                </h1>
                <p className="mt-2 text-sm font-bold text-[#7a3507]/70">
                  {t("leaderboard.subtitle")}
                </p>
              </div>
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-orange/10">
                <Image src="/vote.svg" alt="" width={28} height={28} />
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-[#fff3d7] p-4">
                <p className="text-xs font-extrabold uppercase text-[#9b5a10]/70">
                  {t("leaderboard.total_votes")}
                </p>
                <p className="mt-1 text-3xl font-black text-orange">
                  {results?.total_votes ?? 0}
                </p>
              </div>
              <div className="rounded-2xl bg-[#fff3d7] p-4">
                <p className="text-xs font-extrabold uppercase text-[#9b5a10]/70">
                  {t("leaderboard.last_updated", {
                    time: formatUpdatedAt(lastUpdated),
                  })}
                </p>
                <div className="mt-2 flex min-h-8 items-center gap-2 text-sm font-extrabold text-orange">
                  {refreshing && (
                    <span className="h-5 w-5 rounded-full border-4 border-orange border-t-transparent animate-spin" />
                  )}
                  <span>{refreshing ? t("leaderboard.refreshing") : "Live"}</span>
                </div>
              </div>
            </div>
          </header>

          {loading ? (
            <div className="flex h-72 items-center justify-center rounded-[28px] bg-white/95">
              <Loading color="orange" />
            </div>
          ) : error ? (
            <div className="rounded-[28px] bg-white/95 p-8 text-center shadow-[0_16px_50px_rgba(113,55,8,0.15)]">
              <p className="text-xl font-extrabold text-orange">{error}</p>
              <p className="mt-2 text-sm font-bold text-[#7a3507]/65">
                {t("leaderboard.empty")}
              </p>
            </div>
          ) : results ? (
            <>
              <section className="rounded-[28px] bg-white/95 p-5 shadow-[0_16px_50px_rgba(113,55,8,0.16)]">
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-xl font-extrabold text-orange">
                    {leaderTitle}
                  </h2>
                  <span className="rounded-full bg-orange px-3 py-1 text-xs font-extrabold text-white">
                    {leaders.length || 0}
                  </span>
                </div>

                {leaders.length > 0 ? (
                  <div className="mt-4 flex flex-col gap-3">
                    {leaders.map((leader) => (
                      <div
                        key={leader.id}
                        className="flex items-center gap-4 rounded-2xl bg-gradient-to-r from-[#fff1c8] to-white p-3"
                      >
                        <CandidateImage candidate={leader} />
                        <div className="min-w-0 flex-1">
                          <p className="text-lg font-extrabold leading-tight text-[#7a3507]">
                            {leader.name}
                          </p>
                          <p className="mt-1 line-clamp-2 text-xs font-bold text-[#7a3507]/60">
                            {leader.location}
                          </p>
                          <p className="mt-2 text-sm font-extrabold text-orange">
                            {leader.vote_count} {t("home.votes")} ·{" "}
                            {leader.percentage.toFixed(1)}%
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-4 text-sm font-bold text-[#7a3507]/65">
                    {t("leaderboard.empty")}
                  </p>
                )}
              </section>

              <section className="rounded-[28px] bg-white/95 p-5 shadow-[0_16px_50px_rgba(113,55,8,0.16)]">
                <h2 className="text-xl font-extrabold text-orange">
                  {t("leaderboard.ranking")}
                </h2>
                <div className="mt-4 flex flex-col gap-3">
                  {results.candidates.length > 0 ? (
                    results.candidates.map((candidate, index) => (
                      <article
                        key={candidate.id}
                        className="rounded-2xl border border-orange/15 bg-white p-3"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-orange text-sm font-black text-white">
                            {index + 1}
                          </div>
                          <CandidateImage candidate={candidate} />
                          <div className="min-w-0 flex-1">
                            <p className="text-base font-extrabold leading-tight text-[#7a3507]">
                              {candidate.name}
                            </p>
                            <p className="mt-1 line-clamp-1 text-xs font-bold text-[#7a3507]/60">
                              {candidate.location}
                            </p>
                            <div className="mt-2 flex items-center justify-between gap-2 text-xs font-extrabold text-orange">
                              <span>
                                {candidate.vote_count} {t("home.votes")}
                              </span>
                              <span>{candidate.percentage.toFixed(1)}%</span>
                            </div>
                          </div>
                        </div>
                        <div className="mt-3 h-2 overflow-hidden rounded-full bg-orange/10">
                          <div
                            className="h-full rounded-full bg-orange transition-all duration-500"
                            style={{
                              width: `${Math.min(candidate.percentage, 100)}%`,
                            }}
                          />
                        </div>
                      </article>
                    ))
                  ) : (
                    <p className="rounded-2xl bg-[#fff3d7] p-5 text-center text-sm font-bold text-[#7a3507]/70">
                      {t("leaderboard.empty")}
                    </p>
                  )}
                </div>
              </section>
            </>
          ) : null}
        </div>
      </Section>
    </main>
  );
}
