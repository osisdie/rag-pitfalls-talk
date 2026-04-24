/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://backend:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
  // Allow embedding Qdrant / Neo4j dashboards in iframes served from same origin.
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Content-Security-Policy", value: "frame-ancestors 'self'" },
        ],
      },
    ];
  },
};
module.exports = nextConfig;
