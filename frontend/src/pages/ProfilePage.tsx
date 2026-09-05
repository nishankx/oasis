import React, { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Award,
  Zap,
  GitPullRequest,
  ExternalLink,
  Share2,
  Sparkles,
  User,
  ArrowRight,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { api } from '../lib/api';
import type { PublicUserProfile, ContributionRecord, PRStatusResponse } from '../types';
import { useAuthStore } from '../store/useAuthStore';
import { useTelemetryStore } from '../store/useTelemetryStore';

export const ProfilePage: React.FC = () => {
  const { username } = useParams<{ username?: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { addToast } = useTelemetryStore();

  const targetUsername = username || user?.username || 'developer';

  const [profile, setProfile] = useState<PublicUserProfile | null>(null);
  const [contributions, setContributions] = useState<ContributionRecord[]>([]);
  const [prs, setPrs] = useState<PRStatusResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [notFound, setNotFound] = useState<boolean>(false);

  useEffect(() => {
    setIsLoading(true);
    setNotFound(false);

    api.getPublicProfile(targetUsername)
      .then((prof) => {
        setProfile(prof);
      })
      .catch(() => {
        setProfile(null);
        setNotFound(true);
      })
      .finally(() => setIsLoading(false));

    api.getUserContributions(targetUsername)
      .then(setContributions)
      .catch(() => setContributions([]));

    api.listUserPrs()
      .then((data) => {
        setPrs(data || []);
      })
      .catch(() => {
        setPrs([]);
      });
  }, [targetUsername]);

  const handleCopyProfileLink = () => {
    navigator.clipboard.writeText(window.location.href);
    addToast({
      type: 'success',
      title: 'PROFILE LINK COPIED',
      message: 'Sharable public link copied to clipboard.',
    });
  };

  const chartData = useMemo(() => {
    if (!prs || prs.length === 0) return [];

    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthlyMap: { [key: string]: number } = {};

    prs.forEach((pr) => {
      const d = new Date(pr.created_at);
      const m = monthNames[d.getMonth()];
      monthlyMap[m] = (monthlyMap[m] || 0) + (pr.points_awarded || 0);
    });

    let runningTotal = 0;
    return Object.entries(monthlyMap).map(([month, score]) => {
      runningTotal += score;
      return { month, score: runningTotal };
    });
  }, [prs]);

  if (isLoading) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center p-6">
        <div className="space-y-3 text-center">
          <div className="h-8 w-8 rounded-full border-2 border-accent-violet border-t-transparent animate-spin mx-auto" />
          <p className="text-text-muted text-xs font-mono">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (notFound || !profile) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center p-6">
        <div className="rounded-[6px] bg-white/[0.02] p-8 max-w-sm w-full text-center space-y-4">
          <div className="h-10 w-10 rounded-full bg-white/[0.04] flex items-center justify-center mx-auto text-text-muted">
            <User className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Profile Not Found</h2>
            <p className="text-xs text-text-secondary mt-1">
              No developer record found for "@{targetUsername}".
            </p>
          </div>
          <button
            onClick={() => navigate('/discovery')}
            className="inline-flex items-center gap-2 bg-accent-violet hover:bg-accent-violet-hover text-white font-medium text-xs px-4 py-2 rounded-[4px] transition-all"
          >
            <span>Explore Repos</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    );
  }

  const languages = profile.expertise?.languages || {};

  return (
    <div className="min-h-screen w-full max-w-4xl mx-auto py-12 px-4 sm:px-6 bg-transparent space-y-8">
      {/* Profile Banner Panel — Unified Surface, No Hard Borders */}
      <div className="rounded-[6px] bg-white/[0.02] p-8 transition-all hover:bg-white/[0.03]">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          {/* Avatar & User Info */}
          <div className="flex items-center gap-5">
            <div className="relative">
              {profile.avatar_url ? (
                <img
                  src={profile.avatar_url}
                  alt={profile.username}
                  className="h-16 w-16 rounded-[6px] object-cover ring-1 ring-white/10"
                />
              ) : (
                <div className="h-16 w-16 rounded-[6px] bg-white/[0.04] flex items-center justify-center text-accent-violet font-mono text-lg font-bold">
                  {profile.username.slice(0, 2).toUpperCase()}
                </div>
              )}
            </div>

            <div className="space-y-1">
              <div className="flex items-center gap-2.5">
                <h1 className="font-display font-bold text-2xl text-white">
                  {profile.name || `@${profile.username}`}
                </h1>
                <span className="text-xs text-text-muted">@{profile.username}</span>
              </div>

              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded-[4px] text-xs font-mono text-accent-lime bg-white/[0.03]">
                  <Award className="h-3 w-3 inline mr-1" />
                  {profile.rank_tier || 'Active Contributor'}
                </span>
              </div>
            </div>
          </div>

          {/* Score Readout & Actions */}
          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-[10px] font-mono text-text-muted uppercase tracking-wider">
                Score
              </div>
              <div className="font-mono font-bold text-3xl text-accent-lime">
                {(profile.cumulative_score || 0).toLocaleString()}
              </div>
              <div className="text-[11px] font-mono text-text-secondary flex items-center justify-end gap-1 mt-0.5">
                <Zap className="h-3 w-3 text-accent-violet" />
                <span>{profile.recent_contributions_count || 0} PRs</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={async () => {
                  addToast({ type: 'info', title: 'SYNCHRONIZING', message: 'Re-indexing GitHub profile...' });
                  try {
                    const updated = await api.refreshMyProfile();
                    setProfile({
                      username: updated.username,
                      cumulative_score: updated.cumulative_score,
                      rank_tier: updated.rank_tier,
                      expertise: updated.expertise,
                      recent_contributions_count: updated.total_prs,
                    });
                    addToast({ type: 'success', title: 'SYNCHRONIZED', message: 'Profile updated.' });
                  } catch (err: any) {
                    addToast({ type: 'warning', title: 'SYNC NOTICE', message: err.message || 'Could not refresh profile.' });
                  }
                }}
                title="Sync profile"
                className="p-2.5 rounded-[4px] bg-white/[0.03] hover:bg-white/[0.07] text-text-secondary hover:text-white transition-all cursor-pointer"
              >
                <Sparkles className="h-3.5 w-3.5" />
              </button>

              <button
                onClick={handleCopyProfileLink}
                title="Share public profile"
                className="p-2.5 rounded-[4px] bg-white/[0.03] hover:bg-white/[0.07] text-text-secondary hover:text-white transition-all cursor-pointer"
              >
                <Share2 className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Tech Stack Tags */}
        {Object.keys(languages).length > 0 && (
          <div className="mt-6 pt-5 border-t border-white/[0.04] flex flex-wrap items-center gap-2 text-xs">
            <span className="text-text-muted text-[11px] mr-1">Stack:</span>
            {Object.entries(languages).map(([lang, proficiency]) => (
              <span
                key={lang}
                className="px-2 py-0.5 rounded-[4px] bg-white/[0.03] text-white flex items-center gap-1.5 text-xs"
              >
                <span>{lang}</span>
                <span className="text-accent-lime text-[10px] font-mono">{proficiency}%</span>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Contribution Trajectory Chart */}
      {chartData.length > 0 && (
        <div className="rounded-[6px] bg-white/[0.02] p-6 space-y-4">
          <div className="flex items-center justify-between text-xs">
            <span className="text-white font-semibold">Contribution Trajectory</span>
            <span className="text-text-muted font-mono text-[11px]">Points Over Time</span>
          </div>

          <div className="h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="scoreGlow" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7D39EB" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#7D39EB" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="month" stroke="#2E2E3A" tick={{ fill: '#8E8E9E', fontSize: 11 }} />
                <YAxis stroke="#2E2E3A" tick={{ fill: '#8E8E9E', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#09090C',
                    border: 'none',
                    borderRadius: '4px',
                    color: '#FFFFFF',
                    fontSize: '12px',
                  }}
                />
                <Area type="monotone" dataKey="score" stroke="#7D39EB" strokeWidth={2} fillOpacity={1} fill="url(#scoreGlow)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Pull Requests List */}
      <div className="rounded-[6px] bg-white/[0.02] p-6 space-y-4">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-white font-semibold">
            <GitPullRequest className="h-4 w-4 text-accent-violet" />
            <span>Pull Requests ({prs.length})</span>
          </div>
        </div>

        {prs.length === 0 ? (
          <p className="text-xs text-text-muted py-6 text-center">
            No pull requests recorded yet.
          </p>
        ) : (
          <div className="divide-y divide-white/[0.03]">
            {prs.map((pr) => (
              <div key={pr.id} className="py-3 flex items-center justify-between gap-3 text-xs">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white">{pr.repo_full_name}</span>
                    <span className="text-text-muted">#{pr.pr_number}</span>
                    <span className={`px-1.5 py-0.2 rounded-[3px] text-[10px] font-mono uppercase ${
                      pr.status === 'merged'
                        ? 'text-accent-lime bg-accent-lime/10'
                        : pr.status === 'closed'
                        ? 'text-accent-error bg-accent-error/10'
                        : 'text-accent-violet bg-accent-violet/10'
                    }`}>
                      {pr.status}
                    </span>
                  </div>
                  <div className="text-text-secondary text-[11px] mt-0.5">
                    Issue #{pr.issue_number} · Confidence: {pr.gatekeeper_confidence}%
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-accent-lime font-mono font-medium">+{pr.points_awarded} pts</div>
                  </div>

                  <a
                    href={pr.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded-[4px] hover:bg-white/[0.05] text-text-secondary hover:text-white transition-colors"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
