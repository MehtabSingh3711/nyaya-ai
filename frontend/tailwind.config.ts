import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        'morning-snow': 'var(--morning-snow)',
        'amazon-mist': 'var(--amazon-mist)',
        'black-kite': 'var(--black-kite)',
        'toxic-orange': 'var(--toxic-orange)',
        'rose-gold': 'var(--rose-gold)',
        'muted-copper': 'var(--muted-copper)',
        'dark-mahogany': 'var(--dark-mahogany)',
        'aqua-mist': 'var(--aqua-mist)',
        'safe-bg': 'var(--safe-bg)',
        'safe-text': 'var(--safe-text)',
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        display: ["Outfit", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
