"use client";

import Image from "next/image";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ToastContainer, toast } from "react-toastify";
import { YMaps, Map, Placemark } from "@pbe/react-yandex-maps";
import ParticipantsService from "~/app/services/participants";
import AuthService from "~/app/services/auth";
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

type AuthUser = {
  id: number;
  phone_number: string;
  device_conflict?: boolean;
  bound_phone_mask?: string;
};

type LocationConsentRequest = {
  resolve: (allowed: boolean) => void;
};

const LOCATION_CONSENT_SECONDS = 10;
const GEO_WARNING_STORAGE_KEY = "baiqymyzGeoWarningSeen";

async function getGeolocationPermissionState() {
  if (
    typeof navigator === "undefined" ||
    !navigator.permissions ||
    !navigator.permissions.query
  ) {
    return "unsupported";
  }

  try {
    const status = await navigator.permissions.query({
      name: "geolocation" as PermissionName,
    });
    return status.state;
  } catch {
    return "unsupported";
  }
}

export default function VotePage() {
  const { t } = useTranslation("common");
  const router = useRouter();
  const [results, setResults] = useState<VotingResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [isVoting, setIsVoting] = useState(false);
  const [isCheckingLocation, setIsCheckingLocation] = useState(false);
  const [locationConsentRequest, setLocationConsentRequest] =
    useState<LocationConsentRequest | null>(null);
  const [locationConsentCountdown, setLocationConsentCountdown] = useState(
    LOCATION_CONSENT_SECONDS
  );
  const locationConsentRequestRef = useRef<LocationConsentRequest | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [pendingCandidate, setPendingCandidate] = useState<Candidate | null>(null);
  const [deviceConflict, setDeviceConflict] = useState<{ boundPhoneMask: string } | null>(null);
  const isLocationConsentOpen = Boolean(locationConsentRequest);
  const isDeviceConflictOpen = Boolean(deviceConflict);
  const canResolveLocationConsent = locationConsentCountdown <= 0;

  const selectedCandidate = useMemo(() => {
    if (!results?.current_vote) return null;
    return results.candidates.find(
      (candidate) => candidate.id === results.current_vote?.participant
    ) ?? null;
  }, [results]);

  const orderedCandidates = useMemo(() => {
    if (!results?.candidates) return [];

    const selectedParticipantId = results.current_vote?.participant;
    if (!selectedParticipantId) return results.candidates;

    const selected = results.candidates.find(
      (candidate) => candidate.id === selectedParticipantId
    );
    if (!selected) return results.candidates;

    return [
      selected,
      ...results.candidates.filter(
        (candidate) => candidate.id !== selectedParticipantId
      ),
    ];
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
    AuthService.getMe()
      .then(({ data }) => {
        setAuthUser(data);
        return loadResults();
      })
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          router.push("/login?next=/vote");
          return;
        }
        toast.error(t("home.vote_error"));
        console.error("Error fetching voting results:", err);
      })
      .finally(() => setLoading(false));
  }, [router]);

  useEffect(() => {
    if (!locationConsentRequest) return;

    setLocationConsentCountdown(LOCATION_CONSENT_SECONDS);
    const timer = window.setInterval(() => {
      setLocationConsentCountdown((current) => Math.max(0, current - 1));
    }, 1000);

    return () => window.clearInterval(timer);
  }, [locationConsentRequest]);

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
    if (
      err.response?.status === 409 &&
      err.response.data?.code === "DEVICE_BOUND_TO_OTHER_PHONE"
    ) {
      setDeviceConflict({
        boundPhoneMask: err.response.data?.bound_phone_mask || "",
      });
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

  const requestLocationConsent = () =>
    new Promise<boolean>((resolve) => {
      if (locationConsentRequestRef.current) {
        resolve(false);
        return;
      }

      const request = { resolve };
      locationConsentRequestRef.current = request;
      setLocationConsentRequest(request);
    });

  const resolveLocationConsent = (allowed: boolean) => {
    const request = locationConsentRequestRef.current;
    if (!canResolveLocationConsent || !request) return;
    request.resolve(allowed);
    locationConsentRequestRef.current = null;
    setLocationConsentRequest(null);
  };

  const getAllowedVotingLocation = async () => {
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      toast.error(t("home.location_error_unsupported"));
      return null;
    }

    const permissionState = await getGeolocationPermissionState();
    if (permissionState === "denied") {
      toast.error(t("home.location_error_denied"));
      return null;
    }

    const hasSeenGeoWarning =
      typeof window !== "undefined" &&
      window.localStorage.getItem(GEO_WARNING_STORAGE_KEY) === "true";

    if (permissionState !== "granted" && !hasSeenGeoWarning) {
      const consentGranted = await requestLocationConsent();
      if (!consentGranted) return null;
      window.localStorage.setItem(GEO_WARNING_STORAGE_KEY, "true");
    }

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

  const showDeviceConflict = () => {
    setPendingCandidate(null);
    setDeviceConflict({
      boundPhoneMask: authUser?.bound_phone_mask || "",
    });
  };

  const closeDeviceConflict = async () => {
    setDeviceConflict(null);
    try {
      await AuthService.logout();
    } finally {
      router.push("/login?next=/vote");
    }
  };

  const submitVote = async (candidate: Candidate) => {
    if (
      !results ||
      isVoting ||
      isCheckingLocation ||
      isLocationConsentOpen ||
      isDeviceConflictOpen
    ) return;

    if (authUser?.device_conflict) {
      showDeviceConflict();
      return;
    }

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
    if (isVoting || isCheckingLocation || isLocationConsentOpen || isDeviceConflictOpen) return;
    if (authUser?.device_conflict) {
      showDeviceConflict();
      return;
    }
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
    orderedCandidates.filter((candidate) =>
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
                filteredCandidates.map((candidate, index) => (
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
                          <span className="mb-2 inline-flex h-7 min-w-10 items-center justify-center rounded-full bg-orange/10 px-3 text-xs font-extrabold text-orange">
                            #{index + 1}
                          </span>
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
                        disabled={
                          isVoting ||
                          isCheckingLocation ||
                          isLocationConsentOpen ||
                          isDeviceConflictOpen ||
                          candidate.is_user_vote
                        }
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
                disabled={isCheckingLocation || isVoting || isLocationConsentOpen || isDeviceConflictOpen}
                className="h-12 flex-1 rounded-2xl bg-orange font-extrabold text-white disabled:bg-orange/50"
              >
                {t("home.confirm")}
              </button>
            </div>
          </div>
        </div>
      )}

      {deviceConflict && (
        <div className="fixed inset-0 z-[90] bg-black/60 flex items-center justify-center px-4">
          <div
            className="w-full max-w-md rounded-2xl bg-white p-6 text-center shadow-lg"
            role="dialog"
            aria-modal="true"
            aria-labelledby="device-conflict-title"
          >
            <h2
              id="device-conflict-title"
              className="mb-4 text-2xl font-extrabold text-orange"
            >
              {t("home.device_conflict_title")}
            </h2>
            <p className="mb-6 text-sm font-bold text-gray-700">
              {t("home.device_conflict_text", {
                phone: deviceConflict.boundPhoneMask || t("home.device_conflict_unknown_phone"),
              })}
            </p>
            <button
              type="button"
              onClick={closeDeviceConflict}
              className="min-h-14 w-full rounded-2xl bg-orange px-5 py-3 text-center text-sm font-extrabold leading-tight text-white"
            >
              {t("home.device_conflict_button")}
            </button>
          </div>
        </div>
      )}

      {locationConsentRequest && (
        <div className="fixed inset-0 z-[80] bg-black/60 flex items-center justify-center px-4">
          <div
            className="w-full max-w-md rounded-2xl bg-white p-6 text-center shadow-lg"
            role="dialog"
            aria-modal="true"
            aria-labelledby="location-consent-title"
          >
            <h2
              id="location-consent-title"
              className="mb-4 text-2xl font-extrabold text-orange"
            >
              {t("home.location_modal_title")}
            </h2>
            <p className="mb-4 text-sm font-bold text-gray-700">
              {t("home.location_modal_text")}
            </p>
            <p className="mb-6 text-sm font-extrabold text-orange">
              {canResolveLocationConsent
                ? t("home.location_modal_ready")
                : t("home.location_modal_countdown", {
                    seconds: locationConsentCountdown,
                  })}
            </p>
            <div className="grid w-full grid-cols-1 gap-3 md:grid-cols-2">
              <button
                type="button"
                onClick={() => resolveLocationConsent(false)}
                disabled={!canResolveLocationConsent}
                className="min-h-14 w-full rounded-2xl border-2 border-orange px-5 py-3 text-center font-extrabold text-orange text-sm leading-tight disabled:border-orange/40 disabled:text-orange/40"
              >
                {t("home.location_modal_close")}
              </button>
              <button
                type="button"
                onClick={() => resolveLocationConsent(true)}
                disabled={!canResolveLocationConsent}
                className="min-h-14 w-full rounded-2xl bg-orange px-5 py-3 text-center font-extrabold text-sm text-white leading-tight disabled:bg-orange/50"
              >
                {t("home.location_modal_allow")}
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
