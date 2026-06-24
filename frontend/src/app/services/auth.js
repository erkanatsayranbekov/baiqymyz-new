import { api } from "~/utils/axios";

export default class AuthService {
  // @ts-ignore
  static async login(phone, password) {
    return await api.post("/api/login/", {
      phone_number: phone,
      password,
    });
  }

  // @ts-ignore
  static async register(phone) {
    return await AuthService.loginByPhone(phone);
  }

  static getFingerprintPayload() {
    if (typeof window === "undefined") {
      return {
        browser_fingerprint: "",
        soft_fingerprint: "",
        network_fingerprint: "",
        signals: {},
      };
    }

    const signals = {
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "",
      language: navigator.language || "",
      languages: Array.isArray(navigator.languages) ? navigator.languages : [],
      platform: navigator.platform || "",
      userAgent: navigator.userAgent || "",
      screen: {
        width: window.screen?.width || 0,
        height: window.screen?.height || 0,
        colorDepth: window.screen?.colorDepth || 0,
        pixelRatio: window.devicePixelRatio || 1,
      },
      hardwareConcurrency: navigator.hardwareConcurrency || 0,
      maxTouchPoints: navigator.maxTouchPoints || 0,
    };

    const stable = JSON.stringify(signals);
    return {
      browser_fingerprint: `${signals.userAgent}|${signals.platform}|${signals.language}`,
      soft_fingerprint: stable,
      network_fingerprint: `${signals.timezone}|${signals.languages.join(",")}`,
      signals,
    };
  }

  // @ts-ignore
  static async loginByPhone(phone) {
    return await api.post("/api/auth/phone/", {
      phone,
      ...AuthService.getFingerprintPayload(),
    });
  }

  static async getMe() {
    return await api.get("/api/auth/me/");
  }

  // @ts-ignore
  static async loginManager(phone, password) {
    return await api.post("/api/manager/auth/login/", {
      phone,
      password,
    });
  }

  static async getManagerMe() {
    return await api.get("/api/manager/auth/me/");
  }

  static notifyAuthChanged() {
    if (typeof window === "undefined") return;
    window.dispatchEvent(new Event("auth-changed"));
  }

  static logoutLocal() {
    if (typeof window === "undefined") return;
    localStorage.removeItem("authToken");
    localStorage.removeItem("phone");
    localStorage.removeItem("managerSessionExpiresAt");
    localStorage.removeItem("authState");
    AuthService.notifyAuthChanged();
  }

  static async logout() {
    try {
      await api.post("/api/auth/logout/");
    } finally {
      AuthService.logoutLocal();
    }
  }

  static logoutManagerLocal() {
    AuthService.logoutLocal();
  }

  // @ts-ignore
  static async checkPhoneNumber(phone) {
    return await api.get(`/api/users/${phone}`);
  }
}
