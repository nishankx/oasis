-- Oasis Database Schema (SQLite)

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    github_id INTEGER UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    name TEXT,
    email TEXT,
    avatar_url TEXT,
    encrypted_access_token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_github_id ON users(github_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    languages_json TEXT NOT NULL DEFAULT '{}',
    topics_json TEXT NOT NULL DEFAULT '{}',
    activity_level TEXT NOT NULL DEFAULT 'medium',
    cumulative_score INTEGER NOT NULL DEFAULT 0,
    rank_tier TEXT NOT NULL DEFAULT 'Novice Contributor',
    last_computed TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profile_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    languages_json TEXT NOT NULL,
    topics_json TEXT NOT NULL,
    activity_level TEXT NOT NULL,
    cumulative_score INTEGER NOT NULL,
    snapshot_timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_user_time ON profile_snapshots(user_id, snapshot_timestamp);

CREATE TABLE IF NOT EXISTS discovery_cache (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    repos_json TEXT NOT NULL,
    cached_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    repo_url TEXT NOT NULL,
    repo_full_name TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    branch_name TEXT NOT NULL,
    local_path TEXT NOT NULL,
    relevant_files_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    last_accessed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workspaces_user ON workspaces(user_id, status);

CREATE TABLE IF NOT EXISTS pull_requests (
    id TEXT PRIMARY KEY,
    workspace_id TEXT REFERENCES workspaces(id) ON DELETE SET NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    repo_full_name TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    pr_url TEXT NOT NULL,
    head_branch TEXT NOT NULL,
    base_branch TEXT NOT NULL DEFAULT 'main',
    gatekeeper_verdict_json TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    ci_status TEXT,
    merged_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_prs_user ON pull_requests(user_id, status);
CREATE INDEX IF NOT EXISTS idx_prs_repo_num ON pull_requests(repo_full_name, pr_number);

CREATE TABLE IF NOT EXISTS contributions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pr_id TEXT NOT NULL REFERENCES pull_requests(id) ON DELETE CASCADE,
    base_score INTEGER NOT NULL DEFAULT 100,
    confidence_bonus INTEGER NOT NULL DEFAULT 0,
    diff_bonus INTEGER NOT NULL DEFAULT 0,
    repo_bonus INTEGER NOT NULL DEFAULT 0,
    total_score INTEGER NOT NULL,
    breakdown_json TEXT NOT NULL,
    awarded_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contributions_user ON contributions(user_id);
CREATE INDEX IF NOT EXISTS idx_contributions_pr ON contributions(pr_id);
