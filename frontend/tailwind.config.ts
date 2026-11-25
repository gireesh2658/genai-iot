import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#F6F8F5",
        surface: "#FFFFFF",
        well: "#EEF3F0",
        hairline: "#E5EAE7",
        brand: {
          DEFAULT: "#2A67B1",
          hover: "#215491",
          tint: "#EAF2FD",
        },
        signal: {
          DEFAULT: "#17857B",
          mint: "#DDF3EA",
          lavender: "#6459BA",
        },
        ink: {
          DEFAULT: "#2B3748",
          secondary: "#556578",
          muted: "#667587",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "Segoe UI Variable Text",
          "Segoe UI",
          "-apple-system",
          "BlinkMacSystemFont",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "Cascadia Mono", "Consolas", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
