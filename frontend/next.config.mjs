/** @type {import('next').NextConfig} */
const configuredBackend = (
  process.env.BACKEND_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  ""
)
  .trim()
  .replace(/\/$/, "");
const backendUrl = configuredBackend || (process.env.RENDER ? "" : "http://127.0.0.1:8000");

const nextConfig = {
  reactStrictMode: true,
  experimental: {
    proxyTimeout: 300000,
  },
  async rewrites() {
    if (!backendUrl) {
      return [];
    }
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
      {
        source: "/health",
        destination: `${backendUrl}/health`,
      },
      {
        source: "/docs",
        destination: `${backendUrl}/docs`,
      },
      {
        source: "/openapi.json",
        destination: `${backendUrl}/openapi.json`,
      },
    ];
  },
};

export default nextConfig;
