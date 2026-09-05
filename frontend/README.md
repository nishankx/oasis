# Oasis Frontend (`oasis-frontend`)

A dark-first, high-contrast developer platform frontend inspired directly by [wpkoi.com](https://wpkoi.com/)'s visual and interaction language — adapted for open-source repository recommendations, Monaco in-browser development sandboxes, and AI-gatekept pull requests.

---

## 🎨 Design Direction & WPKoi Inspirations

- **High-Contrast Dark Aesthetic**: Deep obsidian backgrounds (`#0A0B0E`, `#12141A`) avoiding washed-out grays.
- **Electric Cyber-Lime (`#D4FF00`)**: Primary punch accent signaling active systems, verified scores, and high-confidence gatekeeper approvals.
- **System / Terminal Motifs**:
  - Persistent micro-readout header: `"STATUS: ONLINE · AGENT: READY · LAST SYNC: 12s ago"`
  - Live mouse coordinate tracker: `[X: 1048 Y: 0392]` in the hero corner.
  - Infinite horizontal marquee ticker streaming contributor events (`oasis-agent approved fix in vercel/next.js • alice_dev earned +42 pts`).
- **Oversized Hero Typography**: Bold, tightly tracked wordmark headline (`CONTRIBUTE. GET REVIEWED. GET SCORED.`).
- **Theme-Card Grid & Hashtags**: Micro-labels (`#AUTOMATE_CONTRIBUTIONS`, `#LLM_GATEKEEPER`, `#MONACO_SANDBOX`) and hover reveal actions (`OPEN IN EDITOR →`).
- **Numbered Category Browsing**: `001 BEST MATCH`, `002 TRENDING`, `003 GOOD FIRST ISSUE`, `004 HIGH IMPACT`.
- **Platform Stats Trust Bar**: Aggregate trust counters for merged PRs, active contributors, repos touched, and gatekeeper confidence.

---

## 🧭 Minimalist Page Structure & Backend Endpoint Mapping

| Page / Route | Component | Backend Endpoints & Events | Purpose |
| :--- | :--- | :--- | :--- |
| `/` | `LandingPage.tsx` | `GET /api/v1/stats/platform`<br>`GET /api/v1/stats/activity`<br>`GET /api/v1/discovery/repos` | Minimal hero, live stats pill, top matched issue cards with 1-click workspace launch. |
| `/auth/callback` | `AuthCallbackPage.tsx` | `POST /api/v1/auth/github/callback`<br>`GET /api/v1/auth/session` | Terminal boot sequence animation masking profile synthesis latency. |
| `/discovery` | `DiscoveryPage.tsx` | `GET /api/v1/discovery/repos`<br>`POST /api/v1/discovery/refresh`<br>`POST /api/v1/workspace/prepare` | Issue recommendation cards, numbered filter tabs, cooldown rate-limit timer. |
| `/workspaces` | `WorkspacesListPage.tsx` | `GET /api/v1/workspace`<br>`DELETE /api/v1/workspace/:id` | Active sandboxes dashboard; resume IDE or teardown ephemeral environments. |
| `/workspace/:id` | `WorkspacePage.tsx` | `GET /api/v1/workspace/:id`<br>`GET /api/v1/workspace/:id/tree`<br>`GET /api/v1/workspace/:id/file`<br>`PUT /api/v1/workspace/:id/file`<br>`GET /api/v1/workspace/:id/diff`<br>`POST /api/v1/agent/context`<br>`POST /api/v1/agent/suggest-fix`<br>`POST /api/v1/agent/evaluate`<br>`POST /api/v1/pr/push`<br>`DELETE /api/v1/workspace/:id` | Action-driven Monaco IDE: SAVE, DIFF, CONTEXT, AI FIX, EVALUATE, PUSH PR, TEARDOWN. |
| `/prs` | `PrsPage.tsx` | `GET /api/v1/pr`<br>`GET /api/v1/pr/:id/status`<br>`POST /api/v1/webhooks/github` | User PR list, live CI status polling, and incoming webhook test simulator. |
| `/profile/:username` | `ProfilePage.tsx` | `GET /api/v1/profile/:username`<br>`POST /api/v1/profile/refresh`<br>`GET /api/v1/scoring/contributions/:username`<br>`GET /api/v1/pr` | Developer DNA, RE-SYNC profile action, score trajectory chart, verified PR ledger. |
| `/leaderboard` | `LeaderboardPage.tsx` | `GET /api/v1/scoring/leaderboard` | Global developer ranking table, rank tiers, verified points. |

---

## ⚡ Real-Time Events & Telemetry

The frontend subscribes to real-time events via WebSocket (`/api/v1/ws`) or fallback polling:
1. `pr_approved` / `pr_merged`: Tickers recent merges across open source repositories.
2. `gatekeeper_progress`: Emits evaluation status changes (`evaluating` → `approved` / `rejected`).
3. `score_update`: Animates profile score counters and fires toast notifications.

---

## 📦 Design Tokens (`src/tokens/design-tokens.ts`)

```typescript
export const DESIGN_TOKENS = {
  colors: {
    bg: {
      base: "#0A0B0E",       // Deep obsidian terminal base
      surface: "#12141A",    // Card & panel surface
      elevated: "#181B24",   // Modals, popovers, Monaco gutter
      highlight: "#222634",  // Structural borders
    },
    accent: {
      lime: "#D4FF00",       // Primary WPKoi cyber-lime
      cyan: "#00F5FF",       // Monaco syntax, AI agent
      coral: "#FF453A",      // Gatekeeper rejection
      amber: "#FFB800",      // Cooldowns & warnings
    },
    text: {
      primary: "#F3F4F6",
      secondary: "#9CA3AF",
      terminal: "#D4FF00",
    }
  }
};
```

---

## 🚀 Running the Frontend

### 1. Install Dependencies
```powershell
cd frontend
npm install
```

### 2. Start Vite Development Server
```powershell
npm run dev
```
Runs at `http://localhost:5173` (or the configured port).

### 3. Production Build
```powershell
npm run build
```
Generates an optimized, code-split bundle where Monaco Editor and heavy route assets are asynchronously lazy-loaded (`< 100 kB` initial landing bundle).
