import React, { useEffect, useState, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Compass,
  Layers,
  GitPullRequest,
  User,
  Trophy,
  ArrowRight,
  ExternalLink,
  Code2,
} from 'lucide-react';
import { api } from '../../lib/api';
import type { CandidateRepo } from '../../types';
import { useAuthStore } from '../../store/useAuthStore';
import { modalScaleVariants } from '../../lib/motion';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

interface CommandItem {
  id: string;
  title: string;
  category: 'Navigation' | 'Repositories' | 'Actions';
  icon: React.ComponentType<{ className?: string }>;
  hint?: string;
  action: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [repos, setRepos] = useState<CandidateRepo[]>([]);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Load candidate repos once for searching
  useEffect(() => {
    if (isOpen) {
      api.getRecommendedRepos(15)
        .then((res) => {
          if (res?.repos) setRepos(res.repos);
        })
        .catch(() => {});
    }
  }, [isOpen]);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Build searchable items
  const allItems: CommandItem[] = useMemo(() => {
    const navItems: CommandItem[] = [
      {
        id: 'nav-discover',
        title: 'Discover Repositories',
        category: 'Navigation',
        icon: Compass,
        hint: 'Find open review issues',
        action: () => {
          navigate('/discovery');
          onClose();
        },
      },
      {
        id: 'nav-workspaces',
        title: 'Workspaces',
        category: 'Navigation',
        icon: Layers,
        hint: 'Active sandboxes',
        action: () => {
          navigate('/workspaces');
          onClose();
        },
      },
      {
        id: 'nav-prs',
        title: 'Pull Requests & CI',
        category: 'Navigation',
        icon: GitPullRequest,
        hint: 'Monitored pull requests',
        action: () => {
          navigate('/prs');
          onClose();
        },
      },
      {
        id: 'nav-leaderboard',
        title: 'Leaderboard Rankings',
        category: 'Navigation',
        icon: Trophy,
        hint: 'Top contributors',
        action: () => {
          navigate('/leaderboard');
          onClose();
        },
      },
    ];

    if (user?.username) {
      navItems.push({
        id: 'nav-profile',
        title: `Developer Profile (@${user.username})`,
        category: 'Navigation',
        icon: User,
        hint: 'Contribution DNA',
        action: () => {
          navigate(`/profile/${user.username}`);
          onClose();
        },
      });
    }

    const repoItems: CommandItem[] = repos.map((repo) => ({
      id: `repo-${repo.id}`,
      title: repo.full_name,
      category: 'Repositories',
      icon: Code2,
      hint: `${Math.round(repo.score)}% match · ${repo.language || 'Code'}`,
      action: async () => {
        onClose();
        try {
          const session = await api.prepareWorkspace(repo.html_url, repo.recommended_issue?.number || 1);
          navigate(`/workspace/${session.workspace_id}`);
        } catch {
          navigate(`/discovery`);
        }
      },
    }));

    return [...navItems, ...repoItems];
  }, [navigate, onClose, repos, user]);

  const filteredItems = useMemo(() => {
    const q = query.toLowerCase().trim();
    if (!q) return allItems;
    return allItems.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        (item.hint && item.hint.toLowerCase().includes(q))
    );
  }, [allItems, query]);

  // Handle keyboard arrow navigation & Escape
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredItems.length));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filteredItems[selectedIndex]) {
          filteredItems[selectedIndex].action();
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [filteredItems, isOpen, onClose, selectedIndex]);

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100000] flex items-start justify-center pt-24 px-4">
          {/* Backdrop Blur */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/75 backdrop-blur-md"
          />

          {/* Modal Container */}
          <motion.div
            variants={modalScaleVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="relative w-full max-w-xl rounded-[6px] bg-[#09090C] border border-white/[0.08] shadow-[0_20px_50px_rgba(0,0,0,0.9),0_0_30px_rgba(125,57,235,0.12)] overflow-hidden"
          >
            {/* Search Input Field */}
            <div className="flex items-center gap-3 px-4 py-3.5 border-b border-white/[0.06]">
              <Search className="h-4 w-4 text-text-muted shrink-0" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                placeholder="Type a command or search repositories..."
                className="w-full bg-transparent text-sm text-white placeholder:text-text-muted focus:outline-none font-sans"
              />
              <kbd className="px-1.5 py-0.5 rounded-[3px] bg-white/[0.04] border border-white/[0.08] text-[10px] text-text-muted font-mono">
                ESC
              </kbd>
            </div>

            {/* Results List */}
            <div className="max-h-80 overflow-y-auto p-2 space-y-1">
              {filteredItems.length === 0 ? (
                <div className="py-8 text-center text-xs text-text-muted">
                  No matching commands or repositories found.
                </div>
              ) : (
                filteredItems.map((item, index) => {
                  const isSelected = index === selectedIndex;
                  const Icon = item.icon;

                  return (
                    <div
                      key={item.id}
                      onClick={() => item.action()}
                      onMouseEnter={() => setSelectedIndex(index)}
                      className={`flex items-center justify-between px-3 py-2.5 rounded-[4px] cursor-pointer transition-all duration-100 ${
                        isSelected
                          ? 'bg-accent-violet/15 text-white border border-accent-violet/30'
                          : 'text-text-secondary hover:text-white border border-transparent'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <Icon className={`h-4 w-4 shrink-0 ${isSelected ? 'text-accent-lime' : 'text-text-muted'}`} />
                        <div className="truncate">
                          <span className="text-xs font-sans font-medium text-white truncate block">
                            {item.title}
                          </span>
                          {item.hint && (
                            <span className="text-[11px] text-text-muted truncate block">
                              {item.hint}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="shrink-0 flex items-center gap-2 text-[10px] font-mono text-text-muted">
                        <span className="px-1.5 py-0.5 rounded bg-white/[0.03]">
                          {item.category}
                        </span>
                        {isSelected && <ArrowRight className="h-3 w-3 text-accent-lime" />}
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Command Palette Footer */}
            <div className="flex items-center justify-between px-4 py-2 bg-black/40 border-t border-white/[0.04] text-[11px] text-text-muted font-mono">
              <div className="flex items-center gap-3">
                <span>↑↓ Navigate</span>
                <span>↵ Select</span>
              </div>
              <span className="text-accent-lime">oasis quick search</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
