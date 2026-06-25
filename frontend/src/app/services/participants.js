import { api } from "~/utils/axios";
import AuthService from "~/app/services/auth";
import { env } from "~/env";

export default class ParticipantsService {
  static async getParticipants() {
    return await api.get("/api/participants");
  }

  static async getSortedParticipants() {
    return await api.get("/api/participants?sorted=True");
  }

  static async getCurrentVoting() {
    return await api.get("/api/votings/current/");
  }

  /**
   * @param {number|string} votingId
   */
  static async getVotingResults(votingId) {
    return await api.get(`/api/votings/${votingId}/results/`);
  }

  /**
   * @param {number|string} votingId
   */
  static async getCurrentVote(votingId) {
    return await api.get("/api/votes/current/", {
      params: { voting: votingId },
    });
  }

  /**
   * @param {number|string} votingId
   * @param {number|string} participantId
   * @param {{ latitude: number, longitude: number } | null | undefined} location
   */
  static async submitVote(votingId, participantId, location) {
    /** @type {Record<string, unknown>} */
    const payload = {
      voting: votingId,
      participant: participantId,
      ...AuthService.getFingerprintPayload(),
    };
    if (location) {
      payload.latitude = location.latitude;
      payload.longitude = location.longitude;
    }
    if (env.NEXT_PUBLIC_DISABLE_GEOLOCATION === "true") {
      payload.geo_bypass = true;
    }
    return await api.post("/api/votes/", payload);
  }
}
