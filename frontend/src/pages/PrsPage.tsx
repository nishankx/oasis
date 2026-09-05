import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { GitPullRequest, RefreshCw, ExternalLink, CheckCircle2, Clock, ArrowRight, XCircle } from 'lucide-react';
import { api } from '../lib/api';
import type { PRStatusResponse } from '../types';
import { useTelemetryStore } from '../store/useTelemetryStore';

export const PrsPage: React.FC = () => {
  const navigate = useNavigate();
  const { addToast } = useTelemetryStore();
  const [prs, setPrs] = useState<PRStatusResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [pollingId, setPollingId] = useState<string | null>(null);

  // Scroll tracking
  const { scrollY } = useScroll();
  const headerY = useTransform(scrollY, [0, 300], [0, -10]);

  const fetchPrs = async () => {
    setLoading(true);
    try {
      const list = await api.listUserPrs();
      setPrs(list || []);
    } catch {
      setPrs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPrs();
  }, []);

  const handlePollStatus = async (prId: string) => {
    setPollingId(prId);
    try {
      const updated = await api.getPrStatus(prId);
      setPrs((prev) => prev.map((p) => (p.id === prId ? updated : p)));
      addToast({
        type: 'success',
        title: 'PR STATUS UPDATED',
        message: `Current state: ${updated.status.toUpperCase()}`,
      });
    } catch {
      addToast({
        type: 'warning',
        title: 'POLL NOTICE',
        message: 'No status updates reported by upstream GitHub.',
      });
    } finally {
      setPollingId(null);
    }
  };

  return (
    <div className="min-h-[calc(100vh-140px)] w-full max-w-4xl mx-auto py-12 px-4 sm:px-6 bg-transparent space-y-8">
      {/* Top Header with Scroll Parallax */}
      <motion.div style={{ y: headerY }} className="flex items-center justify-between will-change-transform">
        <div>
          <h1 className="font-display font-bold text-2xl sm:text-3xl text-white tracking-tight">
            Pull Requests
          </h1>
          <p className="text-xs text-text-secondary mt-1">
            Track upstream GitHub merges, CI validation, and gatekeeper confidence.
          </p>
        </div>

        <motion.button
          onClick={fetchPrs}
          whileHover={{ scale: 1.05, y: -1 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 550, damping: 25 }}
          className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-white transition-colors cursor-pointer"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </motion.button>
      </motion.div>

      {/* PRs List with Snappy Spring Cards */}
      {prs.length === 0 ? (
        <div className="rounded-[8px] bg-white/[0.02] p-12 text-center max-w-sm mx-auto space-y-4 border border-white/[0.06]">
          <div className="h-10 w-10 rounded-full bg-white/[0.04] flex items-center justify-center mx-auto text-text-muted">
            <GitPullRequest className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">No Pull Requests Yet</h2>
            <p className="text-xs text-text-secondary mt-1">
              Work on an open issue, evaluate your patch, and submit a PR to earn verified points.
            </p>
          </div>
          <motion.button
            onClick={() => navigate('/discovery')}
            whileHover={{ scale: 1.04, y: -2 }}
            whileTap={{ scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 550, damping: 25 }}
            className="inline-flex items-center gap-2 bg-accent-violet hover:bg-[#6c28d9] text-white font-medium text-xs px-4 py-2 rounded-full shadow-[0_0_15px_rgba(125,57,235,0.3)] transition-all cursor-pointer"
          >
            <span>Discover Repos</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </motion.button>
        </div>
      ) : (
        <div className="space-y-3.5">
          {prs.map((pr) => {
            const isMerged = pr.status === 'merged';
            const isClosed = pr.status === 'closed';
            const isPolled = pollingId === pr.id;

            return (
              <motion.div
                key={pr.id}
                whileHover={{ y: -3, scale: 1.008 }}
                whileTap={{ scale: 0.99 }}
                transition={{ type: 'spring', stiffness: 500, damping: 26, mass: 0.75 }}
                className="group relative p-5 rounded-[8px] bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.07] hover:border-accent-violet/50 shadow-[0_4px_20px_rgba(0,0,0,0.5)] hover:shadow-[0_12px_32px_-8px_rgba(125,57,235,0.25)] transition-all duration-300 flex flex-col sm:flex-row sm:items-center justify-between gap-4 overflow-hidden cursor-default"
              >
                {/* Luminous hairline top border reveal */}
                <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-accent-violet/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

                <div className="space-y-1.5 relative z-10">
                  <div className="flex items-center gap-2.5">
                    {isMerged ? (
                      <CheckCircle2 className="h-4 w-4 text-accent-lime shrink-0" />
                    ) : isClosed ? (
                      <XCircle className="h-4 w-4 text-accent-error shrink-0" />
                    ) : (
                      <Clock className="h-4 w-4 text-accent-violet shrink-0" />
                    )}
                    <span className="font-semibold text-white text-sm group-hover:text-accent-violet transition-colors duration-200">
                      {pr.repo_full_name} #{pr.pr_number}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-[4px] text-[10px] uppercase font-mono font-medium ${
                        isMerged
                          ? 'bg-accent-lime/10 text-accent-lime'
                          : isClosed
                          ? 'bg-accent-error/10 text-accent-error'
                          : 'bg-accent-violet/15 text-accent-violet'
                      }`}
                    >
                      {pr.status}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-4 text-text-secondary text-xs">
                    <span className="font-mono text-[11px]">Branch: {pr.branch_name}</span>
                    <span className="text-accent-lime font-mono text-[11px]">
                      Confidence: {pr.gatekeeper_confidence}%
                    </span>
                    {pr.points_awarded > 0 && (
                      <span className="text-accent-lime font-mono text-[11px] font-semibold">
                        +{pr.points_awarded} pts
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end sm:self-center shrink-0 relative z-10">
                  <motion.button
                    onClick={() => handlePollStatus(pr.id)}
                    disabled={isPolled}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-[4px] bg-white/[0.04] hover:bg-white/[0.08] text-xs text-text-secondary hover:text-white transition-colors cursor-pointer disabled:opacity-40"
                  >
                    <RefreshCw className={`h-3 w-3 ${isPolled ? 'animate-spin' : ''}`} />
                    <span>Check Status</span>
                  </motion.button>

                  <motion.a
                    href={pr.html_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="flex items-center gap-1 text-xs text-accent-violet hover:text-accent-violet-hover cursor-pointer"
                  >
                    <span>GitHub</span>
                    <ExternalLink className="h-3 w-3" />
                  </motion.a>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
};
