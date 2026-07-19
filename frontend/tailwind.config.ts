import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#0A0A0B",
        surface: {
          DEFAULT: "#111114",
          raised: "#16161A",
        },
        hairline: "#26262B",
        content: {
          primary: "#E4E4E7",
          muted: "#A1A1AA",
          faint: "#71717A",
        },
        accent: {
          cyan: "#22D3EE",
          amber: "#F59E0B",
        },
        semantic: {
          success: "#34D399",
          danger: "#F87171",
          info: "#60A5FA",
        },
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      borderRadius: {
        md: "6px",
      },
      boxShadow: {
        subtle: "0 1px 2px 0 rgba(0, 0, 0, 0.4)",
        raised: "0 4px 16px -4px rgba(0, 0, 0, 0.5)",
      },
      keyframes: {
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(2px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "pulse-dot": "pulse-dot 1.2s ease-in-out infinite",
        "fade-in": "fade-in 0.18s ease-out",
      },
    },
  },
  plugins: [],
};

export default config;
