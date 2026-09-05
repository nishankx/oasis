/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          canvas: "#000000",      // Pure black canvas throughout
          base: "#000000",        // Alias for canvas
          surface: "#09090C",     // Distinct lifted surface (Monaco, terminal, elevated panels)
          modal: "#111116",       // Elevated modal surface
          elevated: "#111116",
          hover: "rgba(255, 255, 255, 0.03)",
          highlight: "rgba(255, 255, 255, 0.06)",
          subtle: "rgba(255, 255, 255, 0.02)",
        },
        accent: {
          violet: "#7D39EB",      // Primary brand accent
          'violet-hover': "#9052F2",
          'violet-muted': "rgba(125, 57, 235, 0.12)",
          'violet-glow': "rgba(125, 57, 235, 0.35)",

          lime: "#C6FF33",        // Secondary accent
          'lime-hover': "#D8FF66",
          'lime-muted': "rgba(198, 255, 51, 0.12)",
          'lime-glow': "rgba(198, 255, 51, 0.28)",

          error: "#FF3366",       // Single reserved destructive/error/rejection tone
          'error-hover': "#FF5C85",
          'error-muted': "rgba(255, 51, 102, 0.12)",

          // Backward compatibility aliases for existing components
          coral: "#FF3366",
          'coral-muted': "rgba(255, 51, 102, 0.12)",
          cyan: "#80FFEA",
          'cyan-muted': "rgba(128, 255, 234, 0.12)",
          amber: "#FFB86C",
          'amber-muted': "rgba(255, 184, 108, 0.15)",
        },
        text: {
          primary: "#FFFFFF",
          secondary: "#8E8E9E",
          muted: "#4E4E5C",
          violet: "#7D39EB",
          lime: "#C6FF33",
          error: "#FF3366",
        },
        terminal: {
          bg: "#09090C",
          text: "#E2E8F0",
          keyword: "#BD93F9",
          string: "#FFB86C",
          number: "#80FFEA",
          comment: "#5C6773",
          success: "#C6FF33",
          error: "#FF3366",
          dim: "#4E4E5C",
        }
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['"Inter"', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '4px',
        sm: '4px',
        md: '6px',
        lg: '8px',
      },
      animation: {
        'ambient-breath': 'ambient-breath 8s ease-in-out infinite',
        'pulse-subtle': 'pulse-subtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        'ambient-breath': {
          '0%, 100%': { transform: 'scale(1) translate(-50%, -50%)', opacity: '0.08' },
          '50%': { transform: 'scale(1.25) translate(-48%, -52%)', opacity: '0.14' },
        },
        'pulse-subtle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      }
    },
  },
  plugins: [],
}
