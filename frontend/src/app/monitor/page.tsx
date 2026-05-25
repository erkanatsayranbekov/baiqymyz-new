"use client";

import Image from "next/image";
import React, { useEffect, useState } from "react";
import ParticipantsService from "~/app/services/participants";
import Loading from "~/components/Loading";
import { useTranslation } from "react-i18next";
import Input from "~/components/Input";

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
  is_user_vote: boolean;
};

type VotingResults = {
  voting: Voting;
  total_votes: number;
  leaders: Candidate[];
  candidates: Candidate[];
};

export default function MonitorPage() {
  const { t } = useTranslation("common");
  const [results, setResults] = useState<VotingResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  const fetchResults = async () => {
    const currentVoting = await ParticipantsService.getCurrentVoting();
    const response = await ParticipantsService.getVotingResults(currentVoting.data.id);
    setResults(response.data);
  };

  useEffect(() => {
    fetchResults()
      .catch((err) => console.error("Error fetching voting results:", err))
      .finally(() => setLoading(false));

    const interval = setInterval(() => {
      fetchResults().catch((err) => console.error("Error refreshing voting results:", err));
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  const filteredCandidates =
    results?.candidates.filter((candidate) =>
      candidate.name.toLowerCase().includes(searchTerm.toLowerCase())
    ) ?? [];

  return (
    <main className="bg-contain min-h-screen flex flex-col">
      <div className="flex flex-col flex-1">
        <div className="relative h-10">
          <Image
            className="absolute w-full top-0"
            height={20}
            width={500}
            alt="image"
            src="/oyu_2_small.png"
          />
        </div>

        <div className="w-[90%] mx-auto pt-8 flex-1">
          <div className="flex flex-wrap gap-4 items-center justify-between">
            <div className="flex gap-4 items-center">
              <h1 className="text-4xl font-extrabold text-orange">
                {t("home.results_title")}
              </h1>
              <img src="/vote.svg" alt={t("home.results_title")} className="w-10 h-10" />
            </div>
            {results && (
              <div className="text-orange font-extrabold">
                {t("home.total_votes")}: {results.total_votes}
              </div>
            )}
          </div>
          <div className="border-orange w-full border-[0.5px] my-4"></div>
          <Input
            className="border-orange! text-orange! my-6"
            placeholder={t("home.search_placeholder")}
            value={searchTerm}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
          />
          <div className="flex flex-wrap gap-4">
            {loading ? (
              <div className="flex items-center justify-center h-64 w-full">
                <Loading color="orange" />
              </div>
            ) : filteredCandidates.length > 0 ? (
              filteredCandidates.map((candidate, index) => (
                <div
                  key={candidate.id}
                  className="w-full md:w-[420px] rounded-2xl border-2 border-orange/20 bg-white text-orange flex justify-start overflow-hidden gap-3 p-3 relative"
                >
                  <div className="text-2xl font-extrabold w-8">{index + 1}</div>
                  <Image
                    src={candidate.image || "/logo.png"}
                    alt={candidate.name}
                    width={100}
                    height={100}
                    className="object-cover rounded-2xl w-[100px] h-[100px]"
                  />
                  <div className="flex flex-1 flex-col gap-2">
                    <div>
                      <p className="text-lg font-extrabold text-left">
                        {candidate.name}
                      </p>
                      <p className="text-[10px] font-extrabold text-black/40">
                        {candidate.location}
                      </p>
                    </div>
                    <div className="text-xl font-extrabold text-left">
                      {candidate.vote_count} {t("home.votes")} · {candidate.percentage.toFixed(1)}%
                    </div>
                    {results?.leaders.some((leader) => leader.id === candidate.id) && (
                      <div className="text-sm font-extrabold text-orange">
                        {t("home.leader")}
                      </div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="w-full rounded-2xl border-2 border-orange/20 bg-white p-8 text-center text-orange">
                <p className="text-xl font-extrabold">
                  {results?.candidates.length
                    ? t("home.no_candidates_found")
                    : t("home.voting_unavailable")}
                </p>
              </div>
            )}
          </div>
        </div>

        <div className="relative h-10">
          <Image
            className="absolute w-full top-0"
            height={20}
            width={500}
            alt="image"
            src="/oyu_2_small.png"
          />
        </div>
      </div>
    </main>
  );
}
