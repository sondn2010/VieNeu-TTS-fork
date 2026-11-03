import type { NextConfig } from "next";

// `output: "export"` disallows `rewrites` outright — `next build` throws if
// the key is merely present, regardless of what it returns — so the key
// must not exist at all outside `next dev` (which never builds a static
// export and ignores `output` for serving).
const isDev = process.env.NODE_ENV === "development";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  ...(isDev
    ? {
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: "http://localhost:8100/api/:path*",
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
