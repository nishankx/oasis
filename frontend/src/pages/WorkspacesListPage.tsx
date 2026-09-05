import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Trash2, Code2, Clock, GitBranch, ArrowRight, RefreshCw, Terminal } from 'lucide-react';
import { api } from '../lib/api';
import type { WorkspaceSession } from '../types';
import { useTelemetryStore } from '../store/useTelemetryStore';

export const WorkspacesListPage: React.FC = () => {
  const navigate = useNavigate();
  const { addToast } = useTelemetryStore();
  const [workspaces, setWorkspaces] = useState<WorkspaceSession[]>([]);
  const [loading, setLoading] = useState(true);

  // Scroll tracking
  const { scrollY } = useScroll();
  const headerY = useTransform(scrollY, [0, 300], [0, -10]);

  const fetchWorkspaces = async () => {
    setLoading(true);
    try {
      const list = await api.listWorkspaces();
      setWorkspaces(list || []);
    } catch {
      setWorkspaces([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspaces();
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteWorkspace(id);
      setWorkspaces((prev) => prev.filter((w) => w.workspace_id !== id));
      addToast({
        type: 'info',
        title: 'WORKSPACE DESTROYED',
        message: `Sandbox '${id}' was cleaned up.`,
      });
    } catch {
      setWorkspaces((prev) => prev.filter((w) => w.workspace_id !== id));
      addToast({
        type: 'info',
        title: 'WORKSPACE REMOVED',
        message: `Sandbox '${id}' removed from active list.`,
      });
    }
  };

  return (
    <div className="min-h-[calc(100vh-140px)] w-full max-w-4xl mx-auto py-12 px-4 sm:px-6 bg-transparent space-y-8">
      {/* Header with Scroll Parallax */}
      <motion.div style={{ y: headerY }} className="flex items-center justify-between will-change-transform">
        <div>
          <h1 className="font-display font-bold text-2xl sm:text-3xl text-white tracking-tight">
            Workspaces
          </h1>
          <p className="text-xs text-text-secondary mt-1">
            Active isolated sandbox environments and staged patches.
          </p>
        </div>

        <motion.button
          onClick={fetchWorkspaces}
          whileHover={{ scale: 1.05, y: -1 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 550, damping: 25 }}
          className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-white transition-colors cursor-pointer"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </motion.button>
      </motion.div>

      {/* Workspaces List */}
      {workspaces.length === 0 ? (
        <div className="p-12 text-center rounded-[8px] bg-white/[0.02] text-text-secondary max-w-sm mx-auto space-y-4 border border-white/[0.06]">
          <div className="h-10 w-10 rounded-full bg-white/[0.04] flex items-center justify-center mx-auto text-text-muted">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">No Active Sandboxes</h2>
            <p className="text-xs text-text-secondary mt-1">
              Select a repository from Discover to initialize an isolated Monaco workspace.
            </p>
          </div>
          <motion.button
            onClick={() => navigate('/discovery')}
            whileHover={{ scale: 1.04, y: -2 }}
            whileTap={{ scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 550, damping: 25 }}
            className="mt-2 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent-violet hover:bg-[#6c28d9] text-white font-medium text-xs transition-all shadow-[0_0_15px_rgba(125,57,235,0.3)] cursor-pointer"
          >
            <span>Explore Repos</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </motion.button>
        </div>
      ) : (
        <div className="space-y-3.5">
          {workspaces.map((ws) => (
            <motion.div
              key={ws.workspace_id}
              onClick={() => navigate(`/workspace/${ws.workspace_id}?repo=${encodeURIComponent(ws.repo_full_name)}&issue=${ws.issue_number}`)}
              whileHover={{ y: -3, scale: 1.008 }}
              whileTap={{ scale: 0.99 }}
              transition={{ type: 'spring', stiffness: 500, damping: 26, mass: 0.75 }}
              className="group relative p-5 rounded-[8px] bg-white/[0.02] hover:bg-white/[0.04] border border-white/[0.07] hover:border-accent-violet/50 shadow-[0_4px_20px_rgba(0,0,0,0.5)] hover:shadow-[0_12px_32px_-8px_rgba(125,57,235,0.25)] cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all overflow-hidden"
            >
              {/* Luminous hairline top border reveal */}
              <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-accent-violet/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

              <div className="space-y-1 relative z-10">
                <div className="flex items-center gap-2.5">
                  <Code2 className="h-4 w-4 text-accent-violet" />
                  <span className="font-semibold text-white text-sm group-hover:text-accent-violet transition-colors">
                    {ws.repo_full_name}
                  </span>
                  <span className="text-text-muted text-xs">#{ws.issue_number}</span>
                  <span className="px-1.5 py-0.2 rounded-[3px] text-[10px] font-mono text-accent-lime bg-accent-lime/10 uppercase">
                    {ws.status}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-text-secondary text-xs">
                  <span className="flex items-center gap-1 font-mono text-[11px]">
                    <GitBranch className="h-3 w-3 text-text-muted" />
                    {ws.branch_name}
                  </span>
                  <span className="flex items-center gap-1 text-text-muted text-[11px] font-mono">
                    <Clock className="h-3 w-3" />
                    {ws.workspace_id}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3 relative z-10">
                <motion.button
                  onClick={(e) => handleDelete(ws.workspace_id, e)}
                  whileHover={{ scale: 1.15, color: '#FF3366' }}
                  whileTap={{ scale: 0.9 }}
                  title="Destroy workspace"
                  className="p-2 rounded-[4px] text-text-muted hover:bg-white/[0.04] transition-colors cursor-pointer"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </motion.button>

                <div className="flex items-center gap-1 px-3.5 py-1.5 rounded-[4px] bg-accent-violet hover:bg-[#6c28d9] text-white font-medium text-xs transition-colors shadow-[0_0_12px_rgba(125,57,235,0.3)]">
                  <span>Resume Editor</span>
                  <ArrowRight className="h-3 w-3" />
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
};
