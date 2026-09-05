/**
 * Oasis Design System Tokens
 * Strict Minimalist Dark-Native System
 * Primary Locked Palette: #000000, #7D39EB, #C6FF33, #FFFFFF
 */

export const DESIGN_TOKENS = {
  meta: {
    name: "Oasis Design System",
    version: "2.0.0",
    aesthetic: "True black canvas, unified borderless surfaces, high-contrast violet and lime accents",
  },

  // Color Palette
  colors: {
    bg: {
      canvas: "#000000",       // Pure black background throughout
      surface: "#09090C",      // Lifted surface for Monaco chrome, terminal, elevated panels
      modal: "#111116",        // Elevated modal surface with blur
      hover: "rgba(255, 255, 255, 0.03)", // Borderless hover lift
      hoverStrong: "rgba(255, 255, 255, 0.06)",
    },
    accent: {
      violet: "#7D39EB",       // Primary accent: CTAs, active states, focus rings
      violetHover: "#9052F2",  // Interactive hover violet
      violetMuted: "rgba(125, 57, 235, 0.12)",
      violetGlow: "rgba(125, 57, 235, 0.35)",

      lime: "#C6FF33",         // Secondary accent: success states, highlights, key numbers/scores
      limeHover: "#D8FF66",    // Luminous lime hover
      limeMuted: "rgba(198, 255, 51, 0.12)",
      limeGlow: "rgba(198, 255, 51, 0.28)",

      error: "#FF3366",        // Single reserved destructive/error/rejection tone
      errorHover: "#FF5C85",
      errorMuted: "rgba(255, 51, 102, 0.12)",
    },
    text: {
      primary: "#FFFFFF",      // Primary text and icons
      secondary: "#8E8E9E",    // Descriptions, timestamps, secondary copy
      muted: "#4E4E5C",        // Inactive tabs, disabled, subtle hints
      accentViolet: "#7D39EB",
      accentLime: "#C6FF33",
      accentError: "#FF3366",
    },
    terminal: {
      bg: "#09090C",
      text: "#E2E8F0",
      keyword: "#BD93F9",      // Violet/magenta tone
      string: "#FFB86C",       // Warm amber tone
      number: "#80FFEA",       // Cyan tone
      comment: "#5C6773",      // Slate-green tone
      success: "#C6FF33",      // Secondary accent lime
      error: "#FF3366",        // Reserved neon rose
    }
  },

  // Typography Scale
  typography: {
    fonts: {
      display: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
      mono: "'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace",
      sans: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    },
    tracking: {
      tightest: "-0.04em",
      tight: "-0.02em",
      normal: "0em",
      wide: "0.04em",
      widest: "0.08em",
    },
    scale: {
      motto: "clamp(2.5rem, 6vw, 4.75rem)",
      h1: "clamp(1.75rem, 3.5vw, 2.75rem)",
      h2: "1.5rem",
      h3: "1.125rem",
      body: "0.875rem",
      caption: "0.75rem",
      mono: "0.8125rem",
    }
  },

  // Layout Spacing & Radii (4-6px standard)
  layout: {
    radii: {
      sm: "4px",               // Subtle rounded corners for buttons, inputs
      md: "6px",               // Panels and modal containers
      lg: "8px",
      full: "9999px",          // Avatar badges
    },
    headerHeight: "56px",
  }
} as const;

export type DesignTokens = typeof DESIGN_TOKENS;
