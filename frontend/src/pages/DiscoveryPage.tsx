import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence, useScroll, useTransform, useAnimation } from 'framer-motion';
import {
  RefreshCw,
  Star,
  Search,
  X,
  Code2,
  ExternalLink,
  Loader2,
  Activity,
} from 'lucide-react';
import { GithubIcon } from '../components/ui/GithubIcon';
import { api } from '../lib/api';
import type { CandidateRepo } from '../types';
import { useAuthStore } from '../store/useAuthStore';
import { useTelemetryStore } from '../store/useTelemetryStore';
import {
  MOTION,
  rowStaggerContainer,
  rowStaggerItem,
} from '../lib/motion';

// Count-Up Hook for Understated Match Score
const useCountUp = (target: number, duration = 650) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let start = 0;
    const startTime = performance.now();

    const update = (now: number) => {
      const progress = Math.min((now - startTime) / duration, 1);
      // Ease out quartic
      const easeProgress = 1 - Math.pow(1 - progress, 4);
      setCount(Math.round(easeProgress * target));

      if (progress < 1) {
        requestAnimationFrame(update);
      }
    };

    requestAnimationFrame(update);
  }, [target, duration]);

  return count;
};

interface RepoRowProps {
  repo: CandidateRepo;
  isPreparing: boolean;
  onLaunch: (repo: CandidateRepo) => void;
}

const RepoRow: React.FC<RepoRowProps> = ({ repo, isPreparing, onLaunch }) => {
  const countScore = useCountUp(Math.round(repo.score));
  const rowRef = useRef<HTMLDivElement | null>(null);

  return (
    <motion.div
      ref={rowRef}
      variants={rowStaggerItem}
      layout
      whileHover={{ y: -3, scale: 1.008 }}
      transition={{ type: 'spring', stiffness: 420, damping: 28 }}
      className="group relative p-5 rounded-[8px] bg-white/[0.02] hover:bg-white/[0.045] border border-white/[0.07] hover:border-accent-violet/50 shadow-[0_4px_20px_rgba(0,0,0,0.6)] hover:shadow-[0_12px_32px_-8px_rgba(125,57,235,0.28),0_0_20px_rgba(125,57,235,0.12)] transition-all duration-300 overflow-hidden cursor-pointer"
    >
      {/* Luminous top border hairline reveal on hover */}
      <div className="absolute inset-x-0 top-0 h-[1.5px] bg-gradient-to-r from-transparent via-accent-violet/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

      {/* Ambient background bloom inside card on hover */}
      <div className="absolute inset-0 bg-gradient-to-b from-accent-violet/[0.05] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" />

      <div className="relative z-10 flex items-start justify-between gap-4">
        {/* Left: Avatar + Repo Info */}
        <div className="flex items-start gap-3.5 flex-1 min-w-0">
          <div className="h-7 w-7 rounded-[4px] bg-white/[0.04] group-hover:bg-accent-violet/15 text-text-secondary group-hover:text-accent-violet flex items-center justify-center font-mono text-[10px] shrink-0 mt-0.5 border border-white/[0.06] group-hover:border-accent-violet/40 group-hover:scale-105 transition-all duration-200">
            {repo.name.slice(0, 2).toUpperCase()}
          </div>

          <div className="space-y-1.5 flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap">
              <a
                href={repo.html_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-sans font-semibold text-sm sm:text-base text-white hover:text-accent-violet transition-colors flex items-center gap-1.5 truncate"
              >
                <span>{repo.full_name}</span>
                <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 text-accent-violet transition-all duration-200" />
              </a>

              {/* Animated Counting Match Score with Hover Pulse */}
              <span className="font-mono text-[11px] text-accent-lime font-medium tracking-tight group-hover:scale-105 transition-transform duration-200">
                {countScore}% match
              </span>

              {/* Live Activity Sparkline Micro-Preview (Reveals on Hover) */}
              <div
                className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 hidden sm:flex items-center gap-1.5 px-2 py-0.5 rounded-[4px] bg-white/[0.03] text-[10px] font-mono text-text-muted"
                title="Activity pulse indicator"
              >
                <Activity className="h-3 w-3 text-accent-lime" />
                <div className="flex items-end gap-0.5 h-2.5">
                  <span className="w-0.5 h-1.5 bg-accent-lime/60 rounded-full" />
                  <span className="w-0.5 h-2.5 bg-accent-lime rounded-full" />
                  <span className="w-0.5 h-2 bg-accent-lime/80 rounded-full" />
                  <span className="w-0.5 h-1 bg-accent-lime/40 rounded-full" />
                </div>
                <span>active</span>
              </div>

              {/* 1-2 Subtle Tags */}
              {repo.language && (
                <span className="px-2 py-0.5 rounded-[4px] bg-white/[0.02] text-[11px] text-text-secondary border border-white/[0.04]">
                  {repo.language}
                </span>
              )}
              <span className="flex items-center gap-1 text-[11px] text-text-muted">
                <Star className="h-3 w-3 group-hover:text-accent-lime transition-colors duration-200" />
                <span>{repo.stars_count.toLocaleString()}</span>
              </span>
            </div>

            {/* One-Line Description */}
            <p className="text-xs text-text-secondary truncate leading-relaxed">
              {repo.description || 'Open source codebase with available review tasks.'}
            </p>

            {/* Recommended Issue Subtext */}
            {repo.recommended_issue && (
              <p className="text-[11px] text-text-muted truncate pt-0.5">
                <span className="text-white/70">Issue #{repo.recommended_issue.number}:</span>{' '}
                "{repo.recommended_issue.title}"
              </p>
            )}
          </div>
        </div>

        {/* Right: "Open in Editor" (Appears Only on Hover with Smooth Slide) */}
        <div className="shrink-0 flex items-center self-center pl-2">
          <button
            onClick={() => onLaunch(repo)}
            disabled={isPreparing}
            className="opacity-0 group-hover:opacity-100 translate-x-2 group-hover:translate-x-0 transition-all duration-200 flex items-center gap-1.5 px-3.5 py-1.5 rounded-[4px] bg-accent-violet hover:bg-[#6c28d9] border border-white/10 hover:border-white/25 text-white text-xs font-medium shadow-[0_0_15px_rgba(125,57,235,0.3)] hover:shadow-[0_0_20px_rgba(125,57,235,0.45)] cursor-pointer"
          >
            {isPreparing ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Code2 className="h-3 w-3" />
            )}
            <span>{isPreparing ? 'Loading...' : 'Open in Editor'}</span>
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export const DiscoveryPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, loginWithGithub } = useAuthStore();
  const { addToast } = useTelemetryStore();

  const [activeTab, setActiveTab] = useState<'match' | 'trending' | 'good-first' | 'impact'>('match');
  const [repos, setRepos] = useState<CandidateRepo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [cooldownSeconds, setCooldownSeconds] = useState(0);
  const [preparingRepoId, setPreparingRepoId] = useState<number | null>(null);

  // Framer motion scroll effects & imperative animation controls
  const { scrollY } = useScroll();
  const headerY = useTransform(scrollY, [0, 300], [0, -10]);
  const refreshControls = useAnimation();

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchActive, setIsSearchActive] = useState(false);

  const fetchRecommendations = async (refresh = false) => {
    if (refresh) setIsRefreshing(true);
    else setIsLoading(true);

    try {
      const res = refresh ? await api.refreshDiscovery() : await api.getRecommendedRepos();
      if (res && res.repos) {
        setRepos(res.repos);
      } else {
        setRepos([]);
      }
    } catch {
      setRepos([]);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = searchQuery.trim();
    if (!query) {
      handleClearSearch();
      return;
    }

    setIsSearching(true);
    setIsLoading(true);
    setIsSearchActive(true);

    try {
      const res = await api.searchRepos(query);
      if (res && res.repos) {
        setRepos(res.repos);
        addToast({
          type: 'info',
          title: 'REPOSITORY SEARCH COMPLETE',
          message: `Discovered ${res.repos.length} repositories matching "${query}".`,
        });
      } else {
        setRepos([]);
      }
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'SEARCH FAILED',
        message: err.message || 'Failed to search GitHub repositories.',
      });
      setRepos([]);
    } finally {
      setIsSearching(false);
      setIsLoading(false);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setIsSearchActive(false);
    fetchRecommendations();
  };

  useEffect(() => {
    fetchRecommendations();
  }, []);

  // Cooldown countdown timer
  useEffect(() => {
    if (cooldownSeconds <= 0) return;
    const timer = setInterval(() => {
      setCooldownSeconds((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldownSeconds]);

  const handleRefresh = async () => {
    if (cooldownSeconds > 0) {
      addToast({
        type: 'warning',
        title: 'RATE LIMIT COOLDOWN',
        message: `Please wait ${cooldownSeconds}s before re-querying GitHub search.`,
      });
      return;
    }

    refreshControls.start({
      rotate: [0, 360],
      transition: { duration: 0.35, ease: [0.22, 1, 0.36, 1] },
    });

    setCooldownSeconds(60);
    fetchRecommendations(true);
    addToast({
      type: 'info',
      title: 'RECOMMENDATIONS REFRESHED',
      message: 'Queried fresh repository and issue recommendations.',
    });
  };

  const handleLaunchWorkspace = async (repo: CandidateRepo) => {
    const issueNumber = repo.recommended_issue?.number || 1;
    setPreparingRepoId(repo.id);

    addToast({
      type: 'info',
      title: 'INITIALIZING WORKSPACE',
      message: `Cloning ${repo.full_name} into isolated sandbox...`,
    });

    try {
      const session = await api.prepareWorkspace(repo.html_url, issueNumber);
      navigate(`/workspace/${session.workspace_id}`);
    } catch (err: any) {
      addToast({
        type: 'error',
        title: 'WORKSPACE PREPARATION FAILED',
        message: err.message || 'Failed to initialize workspace repository.',
      });
    } finally {
      setPreparingRepoId(null);
    }
  };

  const filteredRepos = repos.filter((repo) => {
    if (activeTab === 'match') return true;
    if (activeTab === 'trending') return repo.stars_count > 40000;
    if (activeTab === 'good-first') return repo.recommended_issue?.labels.some((l) => l.toLowerCase().includes('good first issue'));
    if (activeTab === 'impact') return repo.open_issues_count > 300;
    return true;
  });

  const filterTabs = [
    { key: 'match', label: '01 Best Match' },
    { key: 'trending', label: '02 Trending' },
    { key: 'good-first', label: '03 Good First Issue' },
    { key: 'impact', label: '04 High Impact' },
  ] as const;

  return (
    <div className="min-h-[calc(100vh-140px)] w-full max-w-4xl mx-auto py-12 px-4 sm:px-6 bg-transparent">
      {/* Minimal Header with subtle scroll parallax */}
      <motion.div
        style={{ y: headerY }}
        className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4 mb-8 w-full will-change-transform"
      >
        <div>
          <h1 className="font-display font-bold text-2xl sm:text-3xl text-white tracking-tight">
            Discover
          </h1>
          <p className="text-xs text-text-secondary mt-1">
            Repositories and issues matched to your skills and review criteria.
          </p>
        </div>

        {/* Refresh Action with Snappy Spring Hover */}
        <motion.button
          onClick={handleRefresh}
          disabled={isRefreshing || cooldownSeconds > 0}
          whileHover={{ scale: 1.05, y: -1 }}
          whileTap={{ scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 550, damping: 25 }}
          className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-white transition-colors disabled:opacity-40 disabled:hover:text-text-secondary self-start sm:self-auto cursor-pointer"
        >
          <motion.div animate={refreshControls}>
            <RefreshCw className={`h-3 w-3 ${isRefreshing ? 'animate-spin' : ''}`} />
          </motion.div>
          <span>{cooldownSeconds > 0 ? `Cooldown (${cooldownSeconds}s)` : 'Refresh'}</span>
        </motion.button>
      </motion.div>

      {/* Search Input - Fixed stable breadth with Spring Focus */}
      <form onSubmit={handleSearch} className="mb-8 w-full block">
        <div className="relative w-full transition-transform duration-200 focus-within:scale-[1.008]">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search repositories by name, topic, or owner/repo..."
            className="w-full pl-10 pr-20 py-2.5 bg-white/[0.02] hover:bg-white/[0.04] focus:bg-white/[0.05] border border-white/[0.06] hover:border-white/[0.12] rounded-[6px] text-xs text-white placeholder:text-text-muted focus:outline-none focus:border-accent-violet focus:shadow-[0_0_20px_rgba(125,57,235,0.25)] transition-all"
          />
          {searchQuery && (
            <motion.button
              type="button"
              onClick={handleClearSearch}
              whileHover={{ scale: 1.15 }}
              whileTap={{ scale: 0.9 }}
              transition={{ type: 'spring', stiffness: 600, damping: 20 }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-white cursor-pointer"
            >
              <X className="h-3.5 w-3.5" />
            </motion.button>
          )}
        </div>
      </form>

      {/* Filter Tabs with Sliding Motion Underline Indicator & Snappy Springs */}
      {!isSearchActive && (
        <div className="flex items-center gap-8 mb-8 select-none text-xs border-b border-white/[0.04] pb-px w-full">
          {filterTabs.map((tab) => {
            const isActive = activeTab === tab.key;
            return (
              <motion.button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                whileHover={{ y: -2 }}
                whileTap={{ scale: 0.96 }}
                transition={{ type: 'spring', stiffness: 550, damping: 26 }}
                className={`pb-2.5 transition-colors cursor-pointer relative font-sans ${
                  isActive
                    ? 'text-white font-medium'
                    : 'text-text-secondary hover:text-white'
                }`}
              >
                <span>{tab.label}</span>
                {isActive && (
                  <motion.span
                    layoutId="activeFilterUnderline"
                    transition={{
                      type: 'spring',
                      stiffness: 550,
                      damping: 26,
                      mass: 0.7,
                    }}
                    className="absolute bottom-0 left-0 right-0 h-[2px] bg-accent-violet rounded-full shadow-[0_0_12px_rgba(125,57,235,0.6)]"
                  />
                )}
              </motion.button>
            );
          })}
        </div>
      )}

      {/* Staggered Repo Entries List with AnimatePresence */}
      {isLoading ? (
        <div className="space-y-4 py-6 w-full">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="p-5 rounded-[6px] bg-white/[0.01] border border-white/[0.04] animate-pulse h-20" />
          ))}
        </div>
      ) : filteredRepos.length === 0 ? (
        <div className="py-20 text-center space-y-4 max-w-sm mx-auto">
          <p className="text-xs text-text-secondary">
            {isSearchActive
              ? `No repositories matched "${searchQuery}".`
              : 'No matching recommendations found for this filter.'}
          </p>
          {!isAuthenticated ? (
            <motion.button
              onClick={() => loginWithGithub()}
              whileHover={{ scale: 1.04, y: -2 }}
              whileTap={{ scale: 0.96 }}
              transition={{ type: 'spring', stiffness: 550, damping: 25 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-[4px] bg-accent-violet text-white text-xs font-medium hover:bg-accent-violet-hover shadow-[0_0_15px_rgba(125,57,235,0.3)] transition-all cursor-pointer"
            >
              <GithubIcon className="h-3.5 w-3.5" />
              <span>Sign in with GitHub</span>
            </motion.button>
          ) : (
            <motion.button
              onClick={handleRefresh}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="text-xs text-accent-violet hover:underline cursor-pointer"
            >
              Query GitHub Search
            </motion.button>
          )}
        </div>
      ) : (
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab + (isSearchActive ? searchQuery : '')}
            variants={rowStaggerContainer}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="space-y-3.5 w-full"
          >
            {filteredRepos.map((repo) => (
              <RepoRow
                key={repo.id}
                repo={repo}
                isPreparing={preparingRepoId === repo.id}
                onLaunch={handleLaunchWorkspace}
              />
            ))}
          </motion.div>
        </AnimatePresence>
      )}
    </div>
  );
};
