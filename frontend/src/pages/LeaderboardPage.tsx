import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Trophy, ArrowUpRight, ArrowRight } from 'lucide-react';
import { api } from '../lib/api';
import type { LeaderboardEntry } from '../types';

export const LeaderboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Scroll tracking
  const { scrollY } = useScroll();
  const headerY = useTransform(scrollY, [0, 300], [0, -10]);

  useEffect(() => {
    setIsLoading(true);
    api.getLeaderboard(50)
      .then((data) => {
        setEntries(data || []);
      })
      .catch(() => {
        setEntries([]);
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="min-h-[calc(100vh-140px)] w-full max-w-4xl mx-auto py-12 px-4 sm:px-6 bg-transparent space-y-8">
      {/* Header with Scroll Parallax */}
      <motion.div style={{ y: headerY }} className="will-change-transform">
        <h1 className="font-display font-bold text-2xl sm:text-3xl text-white tracking-tight">
          Leaderboard
        </h1>
        <p className="text-xs text-text-secondary mt-1">
          Top open-source contributors ranked by verified gatekeeper evaluations and merged pull requests.
        </p>
      </motion.div>

      {/* Leaderboard Table / Empty State */}
      {isLoading ? (
        <div className="p-12 text-center rounded-[8px] bg-white/[0.02] border border-white/[0.06]">
          <div className="h-8 w-8 rounded-full border-2 border-accent-violet border-t-transparent animate-spin mx-auto mb-3" />
          <p className="text-text-muted text-xs font-mono">Loading rankings...</p>
        </div>
      ) : entries.length === 0 ? (
        <div className="rounded-[8px] bg-white/[0.02] p-12 text-center max-w-sm mx-auto space-y-4 border border-white/[0.06]">
          <div className="h-10 w-10 rounded-full bg-white/[0.04] flex items-center justify-center mx-auto text-text-muted">
            <Trophy className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Leaderboard Open</h2>
            <p className="text-xs text-text-secondary mt-1">
              No merged contributions recorded yet. Solve an open issue to claim rank #1.
            </p>
          </div>
          <motion.button
            onClick={() => navigate('/discovery')}
            whileHover={{ scale: 1.04, y: -2 }}
            whileTap={{ scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 550, damping: 25 }}
            className="inline-flex items-center gap-2 bg-accent-violet hover:bg-[#6c28d9] text-white font-medium text-xs px-4 py-2 rounded-full shadow-[0_0_15px_rgba(125,57,235,0.3)] transition-all cursor-pointer"
          >
            <span>Start Reviewing</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </motion.button>
        </div>
      ) : (
        <div className="rounded-[8px] bg-white/[0.02] border border-white/[0.06] overflow-hidden text-xs shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
          <div className="grid grid-cols-12 px-6 py-3 text-text-muted text-[11px] font-medium border-b border-white/[0.04] bg-white/[0.01]">
            <div className="col-span-1">Rank</div>
            <div className="col-span-5 sm:col-span-4">Developer</div>
            <div className="col-span-3 sm:col-span-3">Tier</div>
            <div className="hidden sm:block sm:col-span-2 text-right">Merged PRs</div>
            <div className="col-span-3 sm:col-span-2 text-right">Points</div>
          </div>

          <div className="divide-y divide-white/[0.03]">
            {entries.map((dev) => (
              <motion.div
                key={dev.username}
                whileHover={{ x: 4, backgroundColor: "rgba(255, 255, 255, 0.035)" }}
                transition={{ type: 'spring', stiffness: 550, damping: 26 }}
              >
                <Link
                  to={`/profile/${dev.username}`}
                  className="grid grid-cols-12 items-center px-6 py-4 transition-colors group"
                >
                  {/* Rank */}
                  <div className="col-span-1 flex items-center font-mono">
                    {dev.rank === 1 && <span className="text-accent-lime font-bold">#01</span>}
                    {dev.rank === 2 && <span className="text-accent-violet font-bold">#02</span>}
                    {dev.rank === 3 && <span className="text-white font-bold">#03</span>}
                    {dev.rank > 3 && <span className="text-text-muted">#{String(dev.rank).padStart(2, '0')}</span>}
                  </div>

                  {/* Developer */}
                  <div className="col-span-5 sm:col-span-4 flex items-center gap-3">
                    {dev.avatar_url ? (
                      <img
                        src={dev.avatar_url}
                        alt={dev.username}
                        className="h-6 w-6 rounded-full object-cover ring-1 ring-white/10 group-hover:ring-accent-violet/50 transition-all"
                      />
                    ) : (
                      <div className="h-6 w-6 rounded-full bg-white/[0.04] text-accent-violet flex items-center justify-center font-bold text-[10px]">
                        {dev.username.slice(0, 2).toUpperCase()}
                      </div>
                    )}
                    <span className="font-medium text-white group-hover:text-accent-violet transition-colors">
                      @{dev.username}
                    </span>
                  </div>

                  {/* Tier */}
                  <div className="col-span-3 sm:col-span-3">
                    <span className="px-2 py-0.5 rounded-[4px] text-[10px] bg-white/[0.03] text-text-secondary border border-white/[0.04]">
                      {dev.rank_tier}
                    </span>
                  </div>

                  {/* Merged PRs */}
                  <div className="hidden sm:block sm:col-span-2 text-right text-text-secondary font-mono">
                    {dev.merged_prs} / {dev.total_prs}
                  </div>

                  {/* Score */}
                  <div className="col-span-3 sm:col-span-2 text-right font-mono font-medium text-accent-lime flex items-center justify-end gap-1">
                    <span>{(dev.score || 0).toLocaleString()}</span>
                    <ArrowUpRight className="h-3 w-3 text-text-muted group-hover:text-accent-lime group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all" />
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
