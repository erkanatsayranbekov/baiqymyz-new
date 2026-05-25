import { api } from "~/utils/axios";

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
   * @param {{ latitude: number, longitude: number }} location
   */
  static async submitVote(votingId, participantId, location) {
    return await api.post("/api/votes/", {
      voting: votingId,
      participant: participantId,
      latitude: location.latitude,
      longitude: location.longitude,
    });
  }
}
