import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#0ea5e9",
          dim: "#0369a1",
        },
      },
      animation: {
        "bounce-slow": "bounce 1.2s infinite",
      },
    },
  },
  plugins: [],
};
export default config;
