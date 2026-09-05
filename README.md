# OASIS Monorepo

<div align="center">

```
  ██████╗  █████╗ ███████╗██╗███████╗
 ██╔═══██╗██╔══██╗██╔════╝██║██╔════╝
 ██║   ██║███████║███████╗██║███████╗
 ██║   ██║██╔══██║╚════██║██║╚════██║
 ╚██████╔╝██║  ██║███████║██║███████║
  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝╚══════╝
```

**The Autonomous Open-Source Contribution Platform & AI PR Meaningfulness Gatekeeper**

[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x%20%2F%206.0-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-8.2-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Framer Motion](https://img.shields.io/badge/Framer_Motion-13.2-black.svg?logo=framer&logoColor=white)](https://www.framer.com/motion/)
[![Monaco Editor](https://img.shields.io/badge/Monaco_Editor-0.52-1E1E1E.svg?logo=visualstudiocode&logoColor=white)](https://microsoft.github.io/monaco-editor/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

*Review Code the Right Way. Autonomous PR evaluation, ephemeral in-browser development sandboxes, and verified open-source contribution scoring.*

</div>

---

## 📑 Table of Contents

- [Overview & Value Proposition](#-overview--value-proposition)
- [System Architecture](#-system-architecture)
- [Repository Structure](#-repository-structure)
- [Component 1: `oasis-agent` (CLI & Gatekeeper Engine)](#-component-1-oasis-agent-cli--gatekeeper-engine)
  - [4-Dimensional Meaningfulness Gatekeeper](#4-dimensional-meaningfulness-gatekeeper)
  - [100% Free-Tier Multi-Provider LLM Routing](#100-free-tier-multi-provider-llm-routing)
  - [Task-to-Provider Routing Table](#task-to-provider-routing-table)
  - [CLI Command Reference](#cli-command-reference)
  - [Developer-Led vs Autonomous Workflows](#developer-led-vs-autonomous-workflows)
  - [Reversible Git Operations & Local Cleanup](#reversible-git-operations--local-cleanup)
  - [Audit Logging & Report Formats](#audit-logging--report-formats)
  - [Data Privacy & Public Repo Notice](#-data-privacy-notice)
- [Component 2: `oasis-backend` (API & Core Services)](#-component-2-oasis-backend-api--core-services)
  - [Service Layer Architecture](#service-layer-architecture)
  - [Ephemeral Monaco Sandboxes Lifecycle](#ephemeral-monaco-sandboxes-lifecycle)
  - [Database Schema & SQLite Tables](#database-schema--sqlite-tables)
  - [REST API Endpoint Directory](#rest-api-endpoint-directory)
  - [GitHub Webhooks & Verified Scoring Algorithm](#github-webhooks--verified-scoring-algorithm)
  - [Fernet At-Rest Token Encryption](#fernet-at-rest-token-encryption)
- [Component 3: `frontend` (Web Application & Monaco IDE)](#-component-3-frontend-web-application--monaco-ide)
  - [Locked Color Palette & Visual System](#locked-color-palette--visual-system)
  - [Framer Motion Physics & Spring Grammar](#framer-motion-physics--spring-grammar)
  - [Screen Breakdown & Route Map](#screen-breakdown--route-map)
  - [Monaco Workspace & Full-Screen Layout](#monaco-workspace--full-screen-layout)
  - [State Management & Telemetry](#state-management--telemetry)
- [Component 4: CI/CD & Automation](#-component-4-cicd--automation)
  - [GitHub Actions PR Gatekeeper Workflow](#github-actions-pr-gatekeeper-workflow)
  - [Monorepo Matrix CI Workflow](#monorepo-matrix-ci-workflow)
- [Installation & Local Setup](#-installation--local-setup)
  - [Prerequisites](#prerequisites)
  - [Environment Configuration (.env)](#environment-configuration-env)
  - [Backend Setup](#backend-setup)
  - [Agent Setup](#agent-setup)
  - [Frontend Setup](#frontend-setup)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [Security Model](#-security-model)
- [License](#-license)

---

## 💡 Overview & Value Proposition

Open-source maintainers face an unrelenting barrage of low-quality, AI-generated, or superficial pull requests—edits that alter whitespace, reformat docstrings without substance, or introduce broken fixes that consume hundreds of human review hours. Meanwhile, developers looking to contribute face steep onboarding friction: finding relevant issues, cloning unfamiliar repos, configuring runtimes, and getting meaningful feedback.

**OASIS** solves both sides of the equation with a unified monorepo platform:

1. **For Maintainers & Repositories**: A deterministic, multi-stage **Meaningfulness Gatekeeper** that evaluates every proposed pull request against the actual linked issue. Diffs that fail relevance, safety, or closure likelihood are blocked pre-push or flagged automatically in GitHub Actions.
2. **For Contributors**: A personalized **Repository Discovery Graph** matching AST skill vectors to open issues, coupled with an instant **In-Browser Monaco Workspace** running isolated sandboxes where fixes can be written, tested, and pre-checked in seconds.
3. **For the Open-Source Ecosystem**: A **Verified Contribution Scoring Engine** that awards tamper-proof karma points only when meaningful PRs pass Gatekeeper scrutiny and successfully merge upstream.

---

## 🏛 System Architecture

The following diagram illustrates how the CLI agent, backend API, browser frontend, GitHub API, and free-tier LLM providers interact across the entire contribution lifecycle:

```mermaid
flowchart TD
    subgraph ClientLayer ["Client & Interface Layer"]
        CLI["CLI: oasis-agent<br/>(Terminal / Typer / Rich)"]
        WEB["Web Platform<br/>(React 19 / Monaco / Framer Motion)"]
        GHA["GitHub Actions CI<br/>(oasis-agent-check.yml)"]
    end

    subgraph BackendGateway ["FastAPI Core Services (:8000)"]
        AUTH["AuthService<br/>(GitHub OAuth + Fernet JWT)"]
        DISC["DiscoveryService<br/>(AST Matching & GitHub Search)"]
        WS_SVC["WorkspaceService<br/>(Ephemeral Sandboxes)"]
        AGENT_GW["AgentGateway<br/>(Context & Diff Synthesis)"]
        PR_SVC["PRService<br/>(GitHub Branching & PRs)"]
        SCORE["ScoringService<br/>(Gamified Verified Points)"]
        HOOKS["WebhookHandler<br/>(PR Sync & Merge Tracking)"]
    end

    subgraph AgentEngine ["Gatekeeper Evaluation Engine"]
        HEUR["Deterministic Heuristics<br/>(Whitespace / Empty / Irrelevant)"]
        TESTS["Local Test Runner<br/>(pytest / unittest / npm test)"]
        JUDGE["Semantic LLM Judge<br/>(Relevance / Safety / Closure)"]
        HEUR --> TESTS --> JUDGE
    end

    subgraph FreeTierLLM ["Multi-Provider Failover Pool (100% Free Tier)"]
        GROQ["Groq Cloud<br/>(llama-3.3-70b / gpt-oss-120b)"]
        GEMINI["Google AI Studio<br/>(gemini-flash-latest)"]
        OR["OpenRouter<br/>(nemotron-3-nano / minimax-m3)"]
        NIM["NVIDIA NIM<br/>(llama-3.2-11b-vision)"]
        GROQ -- 429 / Error --> GEMINI
        GEMINI -- 429 / Error --> OR
        OR -- 429 / Error --> NIM
    end

    subgraph StorageLayer ["Persistence & Sandboxes"]
        SQLITE[("SQLite Database<br/>(oasis_backend.db)")]
        SANDBOX[("Ephemeral Workspaces<br/>(.oasis-workspaces/)")]
        AUDIT[("Local Agent Audit DB<br/>(.oasis-agent/history.db)")]
    end

    subgraph ExternalServices ["External Ecosystem"]
        GH["GitHub REST & GraphQL API"]
        UPSTREAM["Upstream Open-Source Repositories"]
    end

    CLI -->|Local Git Ops| AgentEngine
    CLI -->|Push & PR| GH
    CLI -->|Run Audits| AUDIT
    GHA -->|CI Gatekeeper| AgentEngine

    WEB -->|REST & WebSockets| BackendGateway
    AUTH --> SQLITE
    DISC --> SQLITE
    DISC --> GH
    WS_SVC --> SANDBOX
    WS_SVC --> SQLITE
    SCORE --> SQLITE
    PR_SVC --> GH
    HOOKS <-- Webhook Events -- GH

    AGENT_GW --> AgentEngine
    JUDGE <--> FreeTierLLM
```

---

## 📦 Repository Structure

The Oasis monorepo is structured cleanly into isolated, single-responsibility workspaces:

```
oasis/
├── agent/                          # Autonomous CLI Agent & Gatekeeper Engine (oasis-agent)
│   ├── oasis_agent/
│   │   ├── cli.py                  # Typer CLI application, commands, and Rich UX
│   │   ├── orchestrator.py         # End-to-end contribution & evaluation pipeline
│   │   ├── config.py               # Settings loader, YAML parser, provider configs
│   │   ├── models.py               # Pydantic data schemas for diffs, reviews & runs
│   │   ├── evaluator/              # Gatekeeper evaluation modules
│   │   │   ├── heuristics.py       # Deterministic fast-path filters (empty/whitespace/trivial)
│   │   │   ├── judge.py            # Multi-provider LLM semantic scoring judge
│   │   │   └── test_runner.py      # Automated local unit test executor
│   │   ├── git_ops/                # Safe Git operations & reversible patching
│   │   │   ├── client.py           # Git command wrapper (clone, checkout, diff, commit)
│   │   │   └── branch_manager.py   # Isolated branch lifecycle (oasis-agent/fix-issue-*)
│   │   ├── github_api/             # GitHub REST API client (issues, PRs, comments)
│   │   ├── llm/                    # Free-tier LLM client & failover engine
│   │   │   ├── client.py           # Universal HTTP client with backoff & failover
│   │   │   ├── providers.py        # Adapter interfaces (Groq, Gemini, OpenRouter, NIM)
│   │   │   ├── prompts.py          # Strict system & evaluation prompts
│   │   │   ├── router.py           # Dynamic task-to-provider routing manager
│   │   │   └── parser.py           # Defensive JSON & diff response sanitizers
│   │   ├── repo_context/           # Ingestion & search
│   │   │   ├── cloner.py           # Shallow & targeted repository cloning
│   │   │   ├── editor.py           # Reversible unified diff patch applicator
│   │   │   ├── inspector.py        # Filetree scanning & AST metadata extraction
│   │   │   └── search.py           # Keyword, symbol & relevance searcher
│   │   └── reporter/               # Reporting & persistence
│   │       ├── comments.py         # GitHub Markdown review comment builder
│   │       ├── formatter.py        # Rich terminal panels & tables
│   │       └── store.py            # SQLite audit log & JSON/MD report persistence
│   ├── tests/                      # Pytest suite covering all agent modules
│   ├── pyproject.toml              # Packaging spec for oasis-agent CLI
│   └── oasis-agent.config.yaml     # Default provider routing & gatekeeper thresholds
│
├── backend/                        # FastAPI REST API Backend (oasis-backend)
│   ├── oasis_backend/
│   │   ├── main.py                 # FastAPI application, lifespan, middleware & routes
│   │   ├── config.py               # Pydantic BaseSettings, env resolution, Fernet keys
│   │   ├── api/v1/                 # Modular API route controllers
│   │   │   ├── auth.py             # GitHub OAuth & JWT session management
│   │   │   ├── discovery.py        # Personalized repo recommendations
│   │   │   ├── workspace.py        # In-browser ephemeral Monaco workspaces
│   │   │   ├── agent.py            # Agent gateway for web-based AI fixes & evaluations
│   │   │   ├── pr.py               # PR pushing, listing, and GitHub sync
│   │   │   ├── profile.py          # Developer DNA vectors & language breakdowns
│   │   │   ├── scoring.py          # Contribution karma & global leaderboard
│   │   │   ├── stats.py            # Aggregate platform metrics & live activity stream
│   │   │   └── webhooks.py         # Inbound GitHub webhook listener & PR merge verification
│   │   ├── database/               # Database management
│   │   │   ├── connection.py       # Async SQLite database context manager
│   │   │   ├── schema.sql          # DDL tables, foreign keys, and indexes
│   │   │   └── repositories/       # Data Access Objects (User, PR, Workspace, etc.)
│   │   ├── models/                 # Pydantic request & response transfer schemas
│   │   └── services/               # Core business logic implementations
│   │       ├── agent_gateway.py    # Bridge between FastAPI and oasis-agent core
│   │       ├── auth_service.py     # OAuth token exchange & encryption
│   │       ├── discovery_service.py# Developer-to-repo affinity matching
│   │       ├── pr_service.py       # PR lifecycle, diff extraction, and status sync
│   │       ├── profile_service.py  # Profile aggregation & rank tier calculation
│   │       ├── scoring_service.py  # Verified contribution scoring rules
│   │       └── workspace_service.py# Ephemeral sandbox creation, file CRUD, diffing
│   ├── tests/                      # Pytest suite for backend endpoints & services
│   └── pyproject.toml              # Packaging spec for oasis-backend
│
├── frontend/                       # Web Application (React 19 + Vite + TypeScript)
│   ├── src/
│   │   ├── App.tsx                 # Root layout, fixed floating navbar, router views
│   │   ├── index.css               # Hairline grid background, scrollbar styles, typography
│   │   ├── tokens/design-tokens.ts # Locked color constants, font stacks, and radii
│   │   ├── lib/
│   │   │   ├── api.ts              # Typed Axios/Fetch client with auth interceptors
│   │   │   └── motion.ts           # Framer Motion spring presets & stagger transitions
│   │   ├── pages/                  # SPA route views
│   │   │   ├── LandingPage.tsx     # Ultra-minimalist hero ("Review Code the Right Way")
│   │   │   ├── DiscoveryPage.tsx   # Repo matcher with fixed-breadth search & filters
│   │   │   ├── WorkspacePage.tsx   # Full-screen Monaco IDE with custom Back navigation
│   │   │   ├── WorkspacesListPage.tsx # Active ephemeral sandbox manager
│   │   │   ├── PrsPage.tsx         # Tracked PR cards with Gatekeeper verdict badges
│   │   │   ├── ProfilePage.tsx     # Developer DNA vector, skill graphs, tier progression
│   │   │   ├── LeaderboardPage.tsx # Global rank tier table & score breakdowns
│   │   │   └── AuthCallbackPage.tsx# GitHub OAuth callback token receiver
│   │   ├── components/             # Reusable UI components
│   │   │   ├── chrome/             # Navigation, floating pill navbar, toast notifications
│   │   │   └── ui/                 # Command palette, modals, icons, metrics
│   │   └── store/                  # Zustand global state stores
│   │       ├── useAuthStore.ts     # User authentication, token, and profile state
│   │       └── useTelemetryStore.ts# Performance metrics & activity logs
│   ├── package.json                # Frontend npm dependencies & scripts
│   └── vite.config.ts              # Vite bundler configuration & local dev proxy
│
├── .github/                        # CI/CD & Automation
│   └── workflows/
│       ├── ci.yml                  # Matrix test suite across Python 3.10-3.13
│       └── oasis-agent-check.yml   # Reusable PR Meaningfulness Gatekeeper action
│
├── examples/                       # Sample review reports & evaluation artifacts
├── .env.example                    # Comprehensive environment template
└── README.md                       # Monorepo documentation (this file)
```

---

## 🤖 Component 1: `oasis-agent` (CLI & Gatekeeper Engine)

`oasis-agent` is an autonomous AI CLI tool and review engine designed to end the epidemic of trivial, low-effort pull requests. It acts as a personal pre-push guardian for developers and an automated gatekeeper for open-source maintainers.

### 4-Dimensional Meaningfulness Gatekeeper

When a diff is submitted for review, it passes through a rigorous 3-stage funnel:

```
[ Proposed Diff ] 
       │
       ▼
1. Deterministic Heuristics (Instant fail on whitespace, comments, or 0 lines)
       │
       ▼
2. Automated Local Test Suite (pytest, npm test, unittest must pass)
       │
       ▼
3. Semantic LLM Judge (Scores 4 independent dimensions 0.0 - 1.0)
       │
       ├── Relevance (0.35 weight)
       ├── Non-Triviality (0.25 weight)
       ├── Correctness & Safety (0.20 weight)
       └── Issue Closure Likelihood (0.20 weight)
       │
       ▼
[ Verdict: Conf >= 0.70 ? APPROVED : REJECTED ]
```

| Dimension | Description | Typical Failure Reasons |
| :--- | :--- | :--- |
| **Relevance** | Does the diff modify code paths, files, and functions directly linked to the issue description? | Editing unrelated files, modifying unrelated docs, or wandering into distant modules. |
| **Non-Triviality** | Does the change solve a genuine engineering problem rather than padding commit counts? | Formatting whitespace, fixing one typo in a README, renaming a local variable without impact. |
| **Correctness & Safety** | Is the logic sound, free of obvious regressions, and validated by tests? | Syntax errors, broken imports, uncaught exceptions, breaking existing test assertions. |
| **Closure Likelihood** | Would a busy upstream maintainer accept this patch as a complete, satisfactory fix? | Partial implementations, leaving TODO stubs, fixing a symptom while ignoring root cause. |

---

### 100% Free-Tier Multi-Provider LLM Routing

`oasis-agent` was engineered from the ground up to **never require paid API subscriptions**. It implements a resilient multi-provider client that leverages generous free-tier quotas across top AI platforms:

1. **Groq Cloud**: Lightning-fast inference on open models (`llama-3.3-70b-versatile`, `openai/gpt-oss-120b`).
2. **Google AI Studio**: Huge context windows with `gemini-flash-latest` for analyzing entire repository files.
3. **OpenRouter**: Access to community reasoning models (`nvidia/nemotron-3-nano-omni-30b`, `minimax/minimax-m3:free`).
4. **NVIDIA NIM**: Enterprise-grade Llama-3.2 instances on accelerated infrastructure.

#### Transparent Failover Mechanism

If a provider encounters:
- **HTTP 429** (Rate Limit Exceeded)
- **HTTP 5xx** (Provider Downtime or Overload)
- **Connection Timeout** (Exceeding configured threshold)

The client performs exponential backoff, instantly fails over to the next candidate in the fallback chain, and prunes unconfigured providers dynamically—ensuring zero interruptions.

---

### Task-to-Provider Routing Table

Each specialized task in `oasis-agent` is assigned to an optimal primary provider with multi-level fallbacks (configurable in `oasis-agent.config.yaml`):

| Task Identifier | Purpose | Primary Provider | Fallback Chain |
| :--- | :--- | :--- | :--- |
| `context_mapping` | Ingesting files, extracting AST signatures & symbols | `groq_gpt_oss` | `google_gemini_flash`, `nvidia_nim` |
| `codebase_search` | Scanning codebase for relevance keywords | `groq_gpt_oss` | `groq_qwen`, `google_gemini_flash` |
| `code_editing` | Proposing unified diff patches for bugs | `groq_gpt_oss` | `google_gemini_flash`, `openrouter_nemotron`, `nvidia_nim` |
| `meaningfulness_judgment` | Evaluating diff quality across 4 dimensions | `groq_gpt_oss` | `google_gemini_flash`, `openrouter_nemotron`, `nvidia_nim` |
| `pr_description_generation` | Synthesizing clean PR titles, summaries & test notes | `groq_gpt_oss` | `google_gemini_flash`, `openrouter_minimax` |
| `review_report_generation` | Building detailed markdown scorecards | `groq_gpt_oss` | `google_gemini_flash`, `openrouter_minimax` |

---

### CLI Command Reference

`oasis-agent` exposes an ergonomic CLI built with `typer` and formatted with `rich`:

| Command | Arguments / Flags | Description |
| :--- | :--- | :--- |
| `oasis-agent work` | `--repo <url>` `--issue <id>` | **Start Workspace**: Clones repo, checks out issue branch, extracts issue context, and detects test runners. |
| `oasis-agent check` | None | **Pre-Flight Check**: Evaluates your current uncommitted or committed local diff against the linked issue without pushing. |
| `oasis-agent push` | `[--keep]` | **Gatekeeper Push**: Runs full evaluation. If approved, commits changes, pushes branch, opens a GitHub PR, and cleans up local repo. |
| `oasis-agent run` | `--repo <url>` `--issue <id>` `[--dry-run]` | **Autonomous Mode**: Clones repo, searches code, writes AI patch, verifies tests, gatekeeps, and opens PR autonomously. |
| `oasis-agent review` | `<pr_number>` `--repo <owner/repo>` | **PR Review**: Evaluates an existing remote GitHub PR against its linked issue and posts a Gatekeeper verdict comment. |
| `oasis-agent history` | `[--limit 10]` | **Audit Log**: Displays tabular history of past runs, confidence scores, and verdicts from the local SQLite audit database. |
| `oasis-agent status` | None | **Diagnostics**: Tests API key connectivity, checks rate limits, and verifies Git/GitHub access. |
| `oasis-agent configure` | None | **Interactive Setup**: Prompts for API keys and writes them safely to `.env`. |

---

### Developer-Led vs Autonomous Workflows

#### 1. Developer-Led Workflow (Recommended)
You write the code, while the agent ensures quality:
```bash
# 1. Initialize workspace for an issue
oasis-agent work --repo https://github.com/pallets/flask --issue 5020

# 2. Write your fix in your favorite editor (VS Code, Cursor, Vim)
cd flask
$EDITOR flask/app.py

# 3. Test your diff before pushing (interactive dry-run)
oasis-agent check

# 4. Push and open PR (automatically verified and cleaned up)
oasis-agent push
```

#### 2. Autonomous Workflow
The agent investigates the issue and writes the patch:
```bash
# Autonomous generation with dry-run safety
oasis-agent run --repo https://github.com/owner/repo --issue 42 --dry-run

# Autonomous generation and direct PR submission
oasis-agent run --repo https://github.com/owner/repo --issue 42
```

---

### Reversible Git Operations & Local Cleanup

To protect developers and maintainers from pollution:
- **Clean Branch Isolation**: All work occurs on dedicated branches: `oasis-agent/fix-issue-<issue_number>`.
- **Reversible Patching**: If an AI patch fails gatekeeper evaluation, `oasis-agent` executes a complete rollback (`git reset --hard HEAD` and restores original state). No broken commits are pushed.
- **Zero-Footprint Cleanup**: When `oasis-agent push` succeeds, it opens the GitHub PR, stores the run report permanently in `~/.oasis-agent/`, and automatically removes the temporary local clone directory (unless `--keep` is specified).

---

### Audit Logging & Report Formats

Every single run generates persistent artifacts:
1. **Interactive Terminal Output**: Colored Rich panels, score breakdown tables, and status spinners.
2. **Markdown Reports**: Saved to `.oasis-agent/reports/run_<id>.md` with detailed rationale.
3. **Structured JSON**: Saved to `.oasis-agent/reports/run_<id>.json` for programmatic consumption.
4. **SQLite Audit Database**: Saved to `.oasis-agent/history.db` tracking timestamps, repo names, PR URLs, verdicts, and confidence scores.

---

### ⚠️ Data Privacy Notice

> [!WARNING]
> **Public Repository Usage Only**  
> `oasis-agent` is designed to run against **public open-source repositories** using free-tier LLM providers. Prompts, diffs, and issue context transmitted to free endpoints may be used by model providers for training or evaluation under their respective Terms of Service. **Do not use `oasis-agent` with proprietary or confidential corporate codebases without appropriate enterprise agreements.**

---

## ⚡ Component 2: `oasis-backend` (API & Core Services)

`oasis-backend` is a high-performance asynchronous FastAPI service (`oasis_backend.main:app`) that manages user sessions, repository recommendations, ephemeral browser sandboxes, and verified contribution scoring.

### Service Layer Architecture

The backend adheres to a clean layered architecture:

```
[ Fast API Router (/api/v1) ]
            │
            ▼
[ Service Layer (Business Logic) ]
 ├── AuthService        -> GitHub OAuth, JWT session minting, Fernet encryption
 ├── DiscoveryService   -> AST vector matching & GitHub Search API queries
 ├── WorkspaceService   -> Ephemeral Git sandboxes, file CRUD, diff generator
 ├── AgentGateway       -> Python bridge to oasis-agent orchestrator & models
 ├── PRService          -> GitHub PR creation, CI check polling, status sync
 ├── ScoringService     -> Gamified contribution rules, bonus multipliers
 └── ProfileService     -> Developer DNA aggregation, language proficiencies
            │
            ▼
[ Data Access Layer (Repositories) ]
 └── User, Profile, Workspace, PullRequest, Contribution Repositories
            │
            ▼
[ Async SQLite Connection (oasis_backend.db) ]
```

---

### Ephemeral Monaco Sandboxes Lifecycle

When a developer clicks **"Launch Workspace"** on the web app:

1. **Allocation (`POST /api/v1/workspace/prepare`)**:
   - Creates a unique workspace sandbox directory in `.oasis-workspaces/<workspace_id>`.
   - Clones the target GitHub repository (shallow clone for maximum speed).
   - Fetches target issue metadata and branches off `oasis-agent/fix-issue-<id>`.
   - Generates recursive file tree JSON and marks identified relevant files.
2. **Editing (`GET` / `PUT /api/v1/workspace/{id}/file`)**:
   - Feeds file content directly to the browser's Monaco code editor.
   - Saves file modifications to the local sandbox filesystem in real-time.
3. **Diffing (`GET /api/v1/workspace/{id}/diff`)**:
   - Executes `git diff` against the upstream base branch to calculate unified diff patches.
4. **AI Assistance (`POST /api/v1/workspace/{id}/ai-fix`)**:
   - Triggers `oasis-agent` code editor in the background, proposing an automated diff.
5. **Gatekeeper Pre-Flight & Push (`POST /api/v1/pr/push`)**:
   - Runs full Meaningfulness evaluation on the staged changes.
   - If approved, commits changes, pushes the branch using the developer's encrypted GitHub token, and opens a Pull Request on GitHub.
6. **Teardown (`DELETE /api/v1/workspace/{id}`)**:
   - Cleans up directory files and marks workspace status as `archived`.

---

### Database Schema & SQLite Tables

The backend stores persistent state in SQLite (`.oasis-agent/oasis_backend.db`):

| Table Name | Primary Key | Key Columns | Purpose |
| :--- | :--- | :--- | :--- |
| `users` | `id` (Auto Inc) | `github_id`, `username`, `email`, `avatar_url`, `encrypted_access_token` | Authenticated developers with encrypted GitHub tokens. |
| `profiles` | `user_id` (FK) | `languages_json`, `topics_json`, `cumulative_score`, `rank_tier`, `last_computed` | Developer DNA, expertise vector, and overall score. |
| `profile_snapshots` | `id` (Auto Inc) | `user_id`, `cumulative_score`, `snapshot_timestamp` | Historical progress snapshots for radar and progression charts. |
| `discovery_cache` | `user_id` (FK) | `repos_json`, `cached_at`, `expires_at` | Cached repository recommendations (TTL: 6 hours). |
| `workspaces` | `id` (UUID string) | `user_id`, `repo_url`, `repo_full_name`, `issue_number`, `branch_name`, `local_path`, `status` | Ephemeral Monaco sandbox sessions. |
| `pull_requests` | `id` (UUID string) | `workspace_id`, `user_id`, `repo_full_name`, `pr_number`, `pr_url`, `status`, `ci_status`, `gatekeeper_verdict_json` | Tracked pull requests and their verification verdicts. |
| `contributions` | `id` (UUID string) | `user_id`, `pr_id`, `base_score`, `confidence_bonus`, `diff_bonus`, `total_score`, `breakdown_json` | Verified contribution karma records. |

---

### REST API Endpoint Directory

All endpoints are hosted under `/api/v1` with interactive OpenAPI docs available at `http://localhost:8000/docs`.

#### System & Metrics
- `GET /health`: System health, version, and runtime status.
- `GET /api/v1/stats/platform`: Global platform statistics (total PRs merged, contributors, repos touched, gatekeeper pass rate).
- `GET /api/v1/stats/activity`: Real-time platform activity stream for tickers.

#### Authentication (`/api/v1/auth`)
- `GET /api/v1/auth/github/url`: Generates GitHub OAuth authorization URL with requested scopes.
- `POST /api/v1/auth/github/callback`: Exchanges OAuth authorization code for an encrypted token and mints a JWT session.
- `GET /api/v1/auth/session`: Validates current Bearer JWT and returns profile metadata.
- `POST /api/v1/auth/logout`: Clears authentication state.

#### Discovery & Recommendation (`/api/v1/discovery`)
- `GET /api/v1/discovery/repos`: Returns personalized repository and issue recommendations scored by developer affinity.
- `POST /api/v1/discovery/refresh`: Bypasses cache and performs live GitHub search query.

#### Ephemeral Workspaces (`/api/v1/workspace`)
- `POST /api/v1/workspace/prepare`: Allocates an ephemeral sandbox and checks out the issue branch.
- `GET /api/v1/workspace`: Lists all active workspaces for the current user.
- `GET /api/v1/workspace/{id}`: Retrieves metadata for a specific workspace.
- `GET /api/v1/workspace/{id}/tree`: Returns recursive file tree for the Monaco editor navigation sidebar.
- `GET /api/v1/workspace/{id}/file?path={rel_path}`: Reads raw file content from the sandbox.
- `PUT /api/v1/workspace/{id}/file`: Writes updated code to the sandbox filesystem.
- `GET /api/v1/workspace/{id}/diff`: Generates unified git diff of unstaged/staged modifications.
- `POST /api/v1/workspace/{id}/ai-fix`: Prompts agent to propose an automated fix.
- `DELETE /api/v1/workspace/{id}`: Destroys the ephemeral sandbox directory.

#### Gatekeeper & Pull Requests (`/api/v1/pr` & `/api/v1/agent`)
- `POST /api/v1/agent/evaluate`: Evaluates workspace changes against the issue without pushing.
- `POST /api/v1/pr/push`: Evaluates diff; if approved, commits, pushes, and opens GitHub PR.
- `GET /api/v1/pr`: Lists all pull requests opened through Oasis.
- `GET /api/v1/pr/{id}/status`: Polls upstream GitHub PR state, CI checks, and merge status.

#### Profile & Gamification (`/api/v1/profile` & `/api/v1/scoring`)
- `GET /api/v1/profile/me`: Returns developer DNA, language distribution, and rank tier.
- `POST /api/v1/profile/refresh`: Re-indexes user's public GitHub history to update skill vectors.
- `GET /api/v1/profile/{username}`: Returns public profile for any user.
- `GET /api/v1/scoring/leaderboard`: Global contributor rankings sorted by verified karma points.
- `GET /api/v1/scoring/contributions/me`: Breakdown of points earned by the current user.

#### GitHub Webhooks (`/api/v1/webhooks`)
- `POST /api/v1/webhooks/github`: Receives webhook events (`pull_request`, `check_run`), updates PR states, and awards verified contribution points upon upstream merge.

---

### GitHub Webhooks & Verified Scoring Algorithm

Oasis prevents point farming by verifying that code was actually accepted and merged upstream. When a `pull_request.closed` event is received with `merged == true`:

$$\text{Total Score} = \text{Base Score} + \text{Confidence Bonus} + \text{Diff Bonus} + \text{Repo Tier Bonus}$$

- **Base Score**: 100 points for any merged PR.
- **Gatekeeper Confidence Bonus**: Up to 50 points based on Gatekeeper certainty score ($(\text{score} - 0.70) \times 166$).
- **Diff Complexity Bonus**: Up to 30 points based on non-trivial lines changed and tests added.
- **Repo Tier Bonus**: 20–50 bonus points for contributing to high-star or critical infrastructure repositories.

---

### Fernet At-Rest Token Encryption

User GitHub Personal Access Tokens are **never stored in plain text**. The backend uses symmetric **Fernet encryption** (AES-128 in CBC mode with PKCS7 padding and HMAC-SHA256 authentication). The encryption key is derived securely from `JWT_SECRET_KEY` or specified explicitly via `ENCRYPTION_KEY`.

---

## 🎨 Component 3: `frontend` (Web Application & Monaco IDE)

The Oasis frontend is a state-of-the-art Single Page Application built with **React 19**, **Vite**, **TypeScript**, **TailwindCSS**, and **Framer Motion**.

### Locked Color Palette & Visual System

The design system employs a focused, high-contrast palette:

| Token | Hex Value | Semantic Usage |
| :--- | :--- | :--- |
| **Obsidian** | `#000000` | Primary application canvas, deep contrast backgrounds |
| **Violet** | `#7D39EB` | Primary interactive accent, CTAs, active indicators, focus rings |
| **Lime** | `#C6FF33` | Secondary accent, high-confidence verdicts, success badges, karma scores |
| **Pure White** | `#FFFFFF` | Primary typography, active icons, crisp hover borders |
| **Rose / Crimson** | `#EF4444` | Reserved strictly for Gatekeeper rejections and destructive actions |

#### Minimalist Background & Atmosphere
- **Hairline Grid**: Subtle 56px grid lines rendered via CSS linear gradients (`rgba(255, 255, 255, 0.08)`).
- **Multi-Plane Radial Glows**: Soft violet (`rgba(125, 57, 235, 0.12)`) and lime (`rgba(198, 255, 51, 0.05)`) atmospheric ambient glows that shift dynamically via mouse parallax.
- **Scrollbar Stability**: Built with `scrollbar-gutter: stable` to ensure search bars and cards maintain constant breadth across views.

---

### Framer Motion Physics & Spring Grammar

Animations throughout Oasis prioritize physicality, restraint, and snappy responsiveness:

- **Spring Physics**: Fast, abrupt damping curves (`stiffness: 400`, `damping: 30`) with durations around `0.25s - 0.3s`.
- **Scroll Compression**: The floating pill navbar (`fixed top-7`) compresses smoothly via `useScroll` and `useTransform` as the user navigates down the page.
- **Staggered Word Reveals**: Landing page headlines and modal banners reveal text using word-by-word staggered spring animations.
- **Card Hover Elevation**: Repository cards feature subtle border-glow shifts and micro-translations without jarring layout shifts.

---

### Screen Breakdown & Route Map

| Path | Component | Description |
| :--- | :--- | :--- |
| `/` | `LandingPage.tsx` | Minimalist hero with single motto *"Review Code the Right Way"*, live metric counter, and one primary CTA (*"Launch Workspace"*). |
| `/discover` | `DiscoveryPage.tsx` | Developer-matched repository search, filterable by difficulty (`good-first-issue`), tags, and language affinity. |
| `/workspace/:id` | `WorkspacePage.tsx` | **Full-screen Monaco code editor** with file tree, diff viewer, test runner, AI fix trigger, and Gatekeeper push modal. |
| `/workspaces` | `WorkspacesListPage.tsx` | Active sandboxes dashboard with last-accessed timestamps and cleanup options. |
| `/prs` | `PrsPage.tsx` | Pull Request tracker displaying CI status, Gatekeeper scorecards, and merge verification. |
| `/leaderboard` | `LeaderboardPage.tsx` | Global contributor leaderboard with tier badges and verified karma points. |
| `/profile` | `ProfilePage.tsx` | Developer DNA vector radar chart, language proficiencies, and contribution activity heatmap. |
| `/auth/callback` | `AuthCallbackPage.tsx` | Receives GitHub OAuth code, hydrates JWT session, and redirects smoothly. |

---

### Monaco Workspace & Full-Screen Layout

In `/workspace/:id`, the floating navbar is intentionally hidden, and a dedicated **"← Back to Discover"** button is integrated directly into the workspace header next to the *Local Workspace* title. This provides the Monaco editor with **100% full-screen vertical viewport height (`h-screen`)**, maximizing code visibility for complex debugging sessions.

---

### State Management & Telemetry

- **`useAuthStore` (Zustand)**: Manages authentication token persistence in `localStorage`, developer profile metadata, and OAuth login/logout flows.
- **`useTelemetryStore` (Zustand)**: Records client-side event latencies, Gatekeeper pre-flight execution times, and editor interactions.
- **TanStack React Query**: Manages server state caching, background refetching, and optimistic updates.

---

## 🔄 Component 4: CI/CD & Automation

Oasis integrates seamlessly into GitHub workflows for both monorepo development and external PR gatekeeping.

### GitHub Actions PR Gatekeeper Workflow

You can use `oasis-agent` as a PR Gatekeeper in **any** GitHub repository. Add `.github/workflows/oasis-agent-check.yml`:

```yaml
name: oasis-agent PR Meaningfulness Gatekeeper

on:
  pull_request:
    types: [opened, synchronize, reopened]
  workflow_dispatch:
    inputs:
      pr_number:
        description: "Pull Request number to evaluate"
        required: true

permissions:
  contents: read
  pull-requests: write
  issues: write

jobs:
  gatekeeper-check:
    name: Evaluate PR Meaningfulness
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install oasis-agent
        run: |
          python -m pip install --upgrade pip
          pip install ./agent

      - name: Run Test Suite (Local Verification)
        id: test_run
        continue-on-error: true
        run: |
          if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
            pytest || true
          elif [ -f "package.json" ]; then
            npm test || true
          fi

      - name: Evaluate Meaningfulness Gatekeeper
        env:
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
          NVIDIA_API_KEY: ${{ secrets.NVIDIA_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          PR_NUM="${{ github.event.pull_request.number || inputs.pr_number }}"
          oasis-agent review "$PR_NUM" --repo "${{ github.repository }}"
```

---

### Monorepo Matrix CI Workflow

The Oasis repository is validated continuously on every push and pull request across Python 3.10, 3.11, 3.12, and 3.13 via `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ./agent[dev]

      - name: Run Pytest Suite
        run: |
          pytest agent/tests -v
```

---

## 🚀 Installation & Local Setup

### Prerequisites

Ensure you have the following installed on your development machine:
- **Python 3.10+**
- **Node.js 18+** and **npm 9+**
- **Git 2.25+** (configured with your name and email)

---

### Environment Configuration (.env)

Create a `.env` file in the root of the repository. You can obtain free API keys from the links provided below:

```env
# ==============================================================================
# LLM Providers (All Free-Tier APIs)
# ==============================================================================
# Groq: https://console.groq.com/keys
GROQ_API_KEY=gsk_...

# Google AI Studio: https://aistudio.google.com/app/apikey
GOOGLE_API_KEY=AIzaSy...

# OpenRouter: https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-v1-...

# NVIDIA NIM: https://build.nvidia.com/
NVIDIA_API_KEY=nvapi-...

# ==============================================================================
# GitHub Integration
# ==============================================================================
# Personal Access Token with repo scope: https://github.com/settings/tokens
GITHUB_TOKEN=ghp_...

# GitHub OAuth App Credentials (for web login)
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret
GITHUB_REDIRECT_URI=http://localhost:3000/auth/callback
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here

# ==============================================================================
# Oasis Backend Configuration
# ==============================================================================
PORT=8000
HOST=0.0.0.0
DEBUG=True
JWT_SECRET_KEY=oasis-super-secret-key-change-in-production-32bytes
# Optional: 32-byte urlsafe base64 key for Fernet token encryption
# ENCRYPTION_KEY=...
```

---

### Backend Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# 3. Install backend and dev dependencies
pip install -e .[dev]

# 4. Start the FastAPI development server with auto-reload
uvicorn oasis_backend.main:app --host 0.0.0.0 --port 8000 --reload
```
The API is now running at `http://localhost:8000` (OpenAPI Docs at `http://localhost:8000/docs`).

---

### Agent Setup

```bash
# 1. Navigate to agent directory
cd agent

# 2. Install agent in editable mode
pip install -e .[dev]

# 3. Verify CLI installation
oasis-agent --version

# 4. Check LLM connectivity and rate limits
oasis-agent status
```

---

### Frontend Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Install npm packages
npm install

# 3. Start Vite development server
npm run dev
```
The web application is now running at `http://localhost:3000`.

---

## 🧪 Testing & Quality Assurance

### Run Agent Tests
```bash
pytest agent/tests -v
```
Validates deterministic heuristics, LLM failover fallback chains, AST parser sanitizers, Git branch operations, and CLI commands.

### Run Backend Tests
```bash
pytest backend/tests -v
```
Validates FastAPI routes, GitHub OAuth token encryption, ephemeral workspace file CRUD, and webhook signature verification.

### Run Frontend Typecheck & Build
```bash
cd frontend
npm run build
```
Validates TypeScript compilation across all React components, hooks, and stores.

---

## 🔒 Security Model

1. **At-Rest Token Encryption**: GitHub tokens are never written to disk in plain text. Tokens are encrypted using 256-bit symmetric Fernet keys before database storage.
2. **Ephemeral Sandbox Isolation**: Workspaces run in segregated directories under `.oasis-workspaces/`. Path traversal checks ensure users cannot read or write outside their allocated sandbox.
3. **Webhook Verification**: All incoming GitHub webhooks are verified using HMAC-SHA256 signatures against `GITHUB_WEBHOOK_SECRET`.
4. **Non-Destructive Git Guards**: Diffs are staged in temporary branches (`oasis-agent/fix-issue-*`) and rolled back cleanly upon Gatekeeper rejection.

---

## 📄 License

This monorepo is open-source software licensed under the [MIT License](LICENSE).

---

<div align="center">
<b>OASIS</b> — Empowering the next generation of open-source engineering.
</div>
