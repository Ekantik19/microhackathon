import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  output: "standalone",
  // Test servers use their own build folder so they can run next to `make dev` (one `next dev` per folder).
  distDir: process.env.NEXT_DIST_DIR || ".next",
  devIndicators: false, // keeps demo recordings clean; errors still surface
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async redirects() {
    return [{ source: "/", destination: "/match/demo_01", permanent: false }];
  },
};

export default nextConfig;
