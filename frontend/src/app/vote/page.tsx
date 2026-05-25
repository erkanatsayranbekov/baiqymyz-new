"use client";

import Image from "next/image";
import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ToastContainer, toast } from "react-toastify";
import { YMaps, Map, Placemark } from "@pbe/react-yandex-maps";
import ParticipantsService from "~/app/services/participants";
import Loading from "~/components/Loading";
import { useTranslation } from "react-i18next";
import Section from "~/components/Section";
import Input from "~/components/Input";
import {
  calculateDistanceMeters,
  EVENT_LOCATION,
  EVENT_RADIUS_METERS,
  getCurrentCoordinates,
} from "./geo";

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
  current_vote: { id: number; participant: number } | null;
  leaders: Candidate[];
  candidates: Candidate[];
};

export default function VotePage() {
  const { t } = useTranslation("common");
  const router = useRouter();
  const [results, setResults] = useState<VotingResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [isVoting, setIsVoting] = useState(false);
  const [isCheckingLocation, setIsCheckingLocation] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [pendingCandidate, setPendingCandidate] = useState<Candidate | null>(null);

  const selectedCandidate = useMemo(() => {
    if (!results?.current_vote) return null;
    return results.candidates.find(
      (candidate) => candidate.id === results.current_vote?.participant
    ) ?? null;
  }, [results]);

  const loadResults = async (votingId?: number) => {
    const targetVotingId = votingId ?? results?.voting.id;
    const response = targetVotingId
      ? await ParticipantsService.getVotingResults(targetVotingId)
      : await ParticipantsService.getCurrentVoting().then(({ data }) =>
          ParticipantsService.getVotingResults(data.id)
        );
    setResults(response.data);
  };

  useEffect(() => {
    const token = localStorage.getItem("authToken");
    if (!token) {
      router.push("/login?next=/vote");
      return;
    }

    loadResults()
      .catch((err) => {
        toast.error(t("home.vote_error"));
        console.error("Error fetching voting results:", err);
      })
      .finally(() => setLoading(false));
  }, [router]);

  const showVoteError = (err: any) => {
    if (err.response?.status === 401) {
      toast.error(t("home.vote_unauthorized"));
      router.push("/login?next=/vote");
      return;
    }
    if (err.response?.status === 403) {
      const detail = err.response.data?.detail;
      toast.error(
        detail === "Voting is only available at the event location."
          ? t("home.location_error_outside")
          : detail || t("home.voting_closed")
      );
      return;
    }
    if (err.response?.status === 400) {
      toast.error(err.response.data?.detail || t("home.candidate_unavailable"));
      return;
    }
    if (err.response?.status === 429) {
      toast.error(t("home.too_many_vote_attempts"));
      return;
    }
    toast.error(t("home.vote_error"));
  };

  const getAllowedVotingLocation = async () => {
    setIsCheckingLocation(true);
    try {
      const location = await getCurrentCoordinates();
      const distance = calculateDistanceMeters(location, EVENT_LOCATION);
      if (distance > EVENT_RADIUS_METERS) {
        toast.error(t("home.location_error_outside"));
        return null;
      }
      return location;
    } catch (err: any) {
      if (err?.message === "GEOLOCATION_UNSUPPORTED") {
        toast.error(t("home.location_error_unsupported"));
      } else if (err?.code === 1) {
        toast.error(t("home.location_error_denied"));
      } else if (err?.code === 2) {
        toast.error(t("home.location_error_unavailable"));
      } else if (err?.code === 3) {
        toast.error(t("home.location_error_timeout"));
      } else {
        toast.error(t("home.location_error_failed"));
      }
      return null;
    } finally {
      setIsCheckingLocation(false);
    }
  };

  const submitVote = async (candidate: Candidate) => {
    if (!results || isVoting || isCheckingLocation) return;

    const location = await getAllowedVotingLocation();
    if (!location) {
      setPendingCandidate(null);
      return;
    }

    setIsVoting(true);
    try {
      await ParticipantsService.submitVote(results.voting.id, candidate.id, location);
      toast.success(
        selectedCandidate && selectedCandidate.id !== candidate.id
          ? t("home.vote_changed")
          : t("home.vote_success")
      );
      await loadResults(results.voting.id);
    } catch (err: any) {
      showVoteError(err);
      console.error("Vote submission failed:", err);
    } finally {
      setIsVoting(false);
      setPendingCandidate(null);
    }
  };

  const handleCandidateSelect = (candidate: Candidate) => {
    if (isVoting || isCheckingLocation) return;
    if (selectedCandidate?.id === candidate.id) {
      toast.info(t("home.already_your_vote"));
      return;
    }
    if (selectedCandidate) {
      setPendingCandidate(candidate);
      return;
    }
    submitVote(candidate);
  };

  const filteredCandidates =
    results?.candidates.filter((candidate) =>
      candidate.name.toLowerCase().includes(searchTerm.toLowerCase())
    ) ?? [];

  return (
    <main className="bg-[url(/background.png)] bg-contain min-h-screen flex flex-col">
      <ToastContainer />
      <div className="flex flex-col flex-1">
        <Section>
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
                  {t("home.title")}
                </h1>
                <img
                  src="/vote.svg"
                  alt={t("home.title")}
                  className="w-10 h-10"
                />
              </div>
              {results && (
                <div className="text-orange font-extrabold">
                  {t("home.total_votes")}: {results.total_votes}
                </div>
              )}
            </div>
            <div className="border-orange w-full border-[0.5px] my-4"></div>
            <h2 className="text-xl font-extrabold text-orange">
              {selectedCandidate
                ? `${t("home.current_vote")}: ${selectedCandidate.name}`
                : t("home.select_candidate")}
            </h2>
            <p className="mt-2 text-sm font-bold text-orange/80">
              {t("home.location_vote_notice")}
            </p>
            <Input
              className="border-orange! text-orange! my-6"
              placeholder={t("home.search_placeholder")}
              value={searchTerm}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchTerm(e.target.value)}
            />
            <div className="flex flex-col gap-6">
              {loading ? (
                <div className="flex items-center justify-center h-64">
                  <Loading color="orange" />
                </div>
              ) : filteredCandidates.length > 0 ? (
                filteredCandidates.map((candidate) => (
                  <div
                    key={candidate.id}
                    className={`w-full rounded-2xl border-2 flex gap-4 overflow-hidden p-3 ${
                      candidate.is_user_vote
                        ? "border-orange bg-orange/10 text-orange"
                        : "border-orange/20 bg-white text-orange"
                    }`}
                  >
                    <div className="w-[110px] shrink-0">
                      <Image
                        src={candidate.image || "/logo.png"}
                        alt={candidate.name}
                        width={110}
                        height={140}
                        className="object-cover rounded-2xl w-[110px] h-[140px]"
                      />
                    </div>
                    <div className="flex flex-1 flex-col gap-2">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-lg font-extrabold text-left">
                            {candidate.name}
                          </p>
                          <p className="text-[11px] font-bold text-black/50">
                            {candidate.location}
                          </p>
                        </div>
                        {candidate.is_user_vote && (
                          <span className="rounded-full bg-orange px-4 py-1 text-sm font-extrabold text-white">
                            {t("home.your_vote")}
                          </span>
                        )}
                      </div>
                      <div className="flex flex-wrap items-center gap-3 text-sm font-bold text-black/50">
                        <span>{candidate.vote_count} {t("home.votes")}</span>
                        <span>{candidate.percentage.toFixed(1)}%</span>
                        {results?.leaders.some((leader) => leader.id === candidate.id) && (
                          <span className="text-orange">{t("home.leader")}</span>
                        )}
                      </div>
                      <button
                        type="button"
                        disabled={isVoting || isCheckingLocation || candidate.is_user_vote}
                        onClick={() => handleCandidateSelect(candidate)}
                        className="mt-auto h-12 w-full rounded-2xl bg-orange px-6 font-extrabold text-white disabled:bg-orange/50"
                      >
                        {candidate.is_user_vote ? t("home.your_vote") : t("home.vote_for_candidate")}
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border-2 border-orange/20 bg-white p-8 text-center text-orange">
                  <p className="text-xl font-extrabold">
                    {results?.candidates.length
                      ? t("home.no_candidates_found")
                      : t("home.voting_unavailable")}
                  </p>
                </div>
              )}
            </div>
          </div>

          <div className="bg-map-section w-full h-auto py-8 bg-cover ">
            <div className="w-[90%] mx-auto flex flex-col gap-8">
              <div className="font-extrabold text-orange">
                <div className="flex gap-3 items-center">
                  <Image
                    src={"/pin.svg"}
                    alt="pin"
                    width={200}
                    height={200}
                    className="w-[35px] h-[35px]"
                  />
                  <div>
                    <p className="text-md font-bold uppercase">
                      {t("home.astana")}
                    </p>
                    <p className="text-md font-bold uppercase">
                      {t("home.hippodrome")}
                    </p>
                  </div>
                </div>
              </div>
              <div className="border-orange border-2 rounded-4xl overflow-hidden">
                <YMaps
                  query={{
                    lang: "ru_RU",
                    apikey: "536168cc-8dbb-4923-a06f-9a6bd5a9cf15",
                  }}
                >
                  <Map
                    defaultState={{ center: [EVENT_LOCATION.latitude, EVENT_LOCATION.longitude], zoom: 15 }}
                    className=" lg:w-[50%] w-full h-[300px]"
                  >
                    <Placemark
                      geometry={[EVENT_LOCATION.latitude, EVENT_LOCATION.longitude]}
                      options={{ iconColor: "#f00" }}
                    />
                  </Map>
                </YMaps>
              </div>
            </div>
          </div>

          <Image
            priority
            src={"/map_section2.png"}
            alt="pin"
            width={200}
            height={200}
            className="bg-contain w-full h-auto"
          />
        </Section>
      </div>

      {pendingCandidate && selectedCandidate && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center">
          <div className="bg-white p-6 rounded-2xl max-w-md w-[90%] shadow-lg text-center">
            <h2 className="text-2xl font-bold text-orange mb-4">
              {t("home.change_vote_title")}
            </h2>
            <p className="text-gray-700 text-sm mb-6">
              {t("home.change_vote_text", {
                from: selectedCandidate.name,
                to: pendingCandidate.name,
              })}
            </p>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setPendingCandidate(null)}
                className="h-12 flex-1 rounded-2xl border border-orange font-extrabold text-orange"
              >
                {t("home.cancel")}
              </button>
              <button
                type="button"
                onClick={() => submitVote(pendingCandidate)}
                disabled={isCheckingLocation || isVoting}
                className="h-12 flex-1 rounded-2xl bg-orange font-extrabold text-white disabled:bg-orange/50"
              >
                {t("home.confirm")}
              </button>
            </div>
          </div>
        </div>
      )}

      {(isVoting || isCheckingLocation) && (
        <div className="fixed inset-0 z-[100] bg-black/60 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4 text-white font-extrabold">
            <Loading color="white" />
            {isCheckingLocation && <p>{t("home.location_checking")}</p>}
          </div>
        </div>
      )}
    </main>
  );
}
