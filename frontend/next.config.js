import "./src/env.js";

const apiUrl = process.env.NEXT_PUBLIC_API_URL;
const apiHost = apiUrl ? new URL(apiUrl).hostname : null;

/** @type {import("next").NextConfig} */
const config = {
  images: {
    domains: Array.from(new Set(["baiqymyz.kz", "localhost", "172.20.10.2", ...(apiHost ? [apiHost] : [])])),
  },
};

export default config;
