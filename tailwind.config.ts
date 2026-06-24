import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: "#f6f7f9",
        ink: "#17202a",
        muted: "#667085",
        border: "#d9dee7",
        brand: "#0f766e",
        accent: "#2563eb",
        danger: "#dc2626",
        warning: "#b45309"
      },
      boxShadow: {
        panel: "0 1px 2px rgba(16, 24, 40, 0.08)"
      }
    },
  },
  plugins: [],
};

export default config;
