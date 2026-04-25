const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config) => {
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      "@": path.resolve(__dirname, "src"),
    };
    return config;
  },
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://backend:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
  // Allow embedding Qdrant / Neo4j dashboards in iframes. They're on different
  // ports (8080, 8081) on the same host → cross-origin, so we relax frame-src
  // to include http/https on any port. frame-ancestors stays 'self' (controls
  // who can embed US, not who we embed).
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          {
            key: "Content-Security-Policy",
            value:
              "frame-ancestors 'self'; frame-src 'self' http: https:;",
          },
        ],
      },
    ];
  },
};
module.exports = nextConfig;
