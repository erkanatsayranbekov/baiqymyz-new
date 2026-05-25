import axios from "axios";
import { env } from "~/env";

export const api = axios.create({
  baseURL: env.NEXT_PUBLIC_API_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * @param {import("axios").InternalAxiosRequestConfig} config
 */
api.interceptors.request.use((config) => {
  if (typeof window === "undefined") return config;

  const token = localStorage.getItem("authToken");
  if (token) {
    config.headers.set("Authorization", `Token ${token}`);
  }

  return config;
});
