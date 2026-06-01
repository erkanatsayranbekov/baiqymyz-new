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
    return await api.post("/api/register/", {
      phone_number: phone,
    });
  }

  // @ts-ignore
  static async requestOtp(phone) {
    return await api.post("/api/auth/otp/request/", {
      phone,
    });
  }

  // @ts-ignore
  static async verifyOtp(phone, code) {
    return await api.post("/api/auth/otp/verify/", {
      phone,
      code,
    });
  }

  static async getMe() {
    return await api.get("/api/auth/me/");
  }

  // @ts-ignore
  static async generateManagerOtp(phone) {
    return await api.post("/api/manager/otp/generate/", {
      phone,
    });
  }

  // @ts-ignore
  static async requestManagerOtp(phone, password) {
    return await api.post("/api/manager/auth/request-otp/", {
      phone,
      password,
    });
  }

  // @ts-ignore
  static async verifyManagerOtp(phone, ticket, code) {
    return await api.post("/api/manager/auth/verify/", {
      phone,
      ticket,
      code,
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
    AuthService.notifyAuthChanged();
  }

  static logoutManagerLocal() {
    AuthService.logoutLocal();
  }

  // @ts-ignore
  static async checkPhoneNumber(phone) {
    return await api.get(`/api/users/${phone}`);
  }
}
