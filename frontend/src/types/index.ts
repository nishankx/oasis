/**
 * Oasis TypeScript Models
 * Mirrors Backend Pydantic Schemas
 */

export interface UserRecord {
  id: string;
  github_id: number;
  username: string;
  name?: string;
  email?: string;
  avatar_url?: string;
  created_at: string;
  last_login: string;
}

export interface AuthSessionResponse {
  authenticated: boolean;
  user: UserRecord | null;
  token: string | null;
}

export interface IssueItem {
  number: number;
  title: string;
  body?: string;
  labels: string[];
  html_url: string;
  comments_count: number;
  created_at: string;
}

export interface CandidateRepo {
  id: number;
  name: string;
  full_name: string;
  owner: string;
  html_url: string;
  description?: string;
  language?: string;
  topics: string[];
  stars_count: number;
  forks_count: number;
  open_issues_count: number;
  pushed_at: string;
  score: number; // 0.0 - 100.0 match percent
  recommended_issue?: IssueItem | null;
  score_reasons: string[];
}

export interface DiscoveryResponse {
  repos: CandidateRepo[];
  total: number;
  cached: boolean;
  cached_at?: string;
  expires_at?: string;
}

export interface WorkspaceSession {
  id?: string;
  workspace_id: string;
  user_id: number | string;
  repo_url: string;
  repo_full_name: string;
  issue_number: number;
  branch_name: string;
  local_path?: string;
  relevant_files?: string[];
  created_at: string;
  last_accessed?: string;
  last_accessed_at?: string;
  expires_at?: string;
  status: string;
}

export interface FileNode {
  name: string;
  path: string;
  is_dir: boolean;
  size_bytes?: number;
  children?: FileNode[];
}

export interface SaveFileRequest {
  path: string;
  content: string;
}

export interface SaveFileResponse {
  success: boolean;
  bytes_written: number;
}

export interface FileContentResponse {
  path: string;
  content: string;
  language: string;
  size_bytes: number;
}

export interface WorkspaceDiffResponse {
  workspace_id: string;
  has_changes: boolean;
  raw_diff: string;
  files_changed: string[];
  insertions: number;
  deletions: number;
}

export interface GatekeeperDimensions {
  relevance: number;        // 0-100
  non_triviality: number;   // 0-100
  correctness: number;      // 0-100
  closure_likelihood: number; // 0-100
}

export interface GatekeeperVerdict {
  approved: boolean;
  confidence_score: number;
  reasoning: string;
  dimensions: GatekeeperDimensions;
  suggestions?: string[];
}

export interface PushPRResponse {
  success: boolean;
  pr_id?: string;
  pr_url?: string;
  pr_number?: number;
  branch_name: string;
  gatekeeper_verdict: GatekeeperVerdict;
  points_awarded?: number;
  message?: string;
}

export interface PRStatusResponse {
  id: string;
  user_id: string;
  workspace_id: string;
  repo_full_name: string;
  issue_number: number;
  pr_number: number;
  html_url: string;
  branch_name: string;
  status: 'open' | 'ci_pending' | 'ci_passed' | 'ci_failed' | 'merged' | 'closed' | 'not_accepted';
  gatekeeper_confidence: number;
  gatekeeper_reasoning?: string;
  points_awarded: number;
  created_at: string;
  updated_at: string;
}

export interface ExpertiseVector {
  languages: Record<string, number>;
  topics: Record<string, number>;
  activity_level: string;
  last_computed: string;
}

export interface ProfileRecord {
  user_id: string;
  username: string;
  expertise: ExpertiseVector;
  cumulative_score: number;
  rank_tier: string;
  total_prs: number;
  merged_prs: number;
}

export interface PublicUserProfile {
  username: string;
  name?: string;
  avatar_url?: string;
  cumulative_score: number;
  rank_tier: string;
  expertise: ExpertiseVector;
  recent_contributions_count: number;
}

export interface ContributionRecord {
  id: string;
  user_id: string;
  pr_id: string;
  repo_full_name: string;
  issue_number: number;
  pr_number: number;
  points: number;
  reason: string;
  created_at: string;
}

export interface LeaderboardEntry {
  rank: number;
  username: string;
  avatar_url?: string;
  score: number;
  rank_tier: string;
  total_prs: number;
  merged_prs: number;
}

export interface PlatformStats {
  prs_processed: number;
  prs_merged: number;
  contributors: number;
  repos_touched: number;
  avg_confidence: number;
  uptime: string;
  agent_status: string;
  system_status: string;
}

export interface ActivityEvent {
  id: string;
  type: string;
  text: string;
  time: string;
}
