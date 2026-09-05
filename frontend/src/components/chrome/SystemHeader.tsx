import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { LogOut, X, Sparkles, Check } from 'lucide-react';
import { GithubIcon } from '../ui/GithubIcon';
import { CommandPalette } from '../ui/CommandPalette';
import { useAuthStore } from '../../store/useAuthStore';
import { useTelemetryStore } from '../../store/useTelemetryStore';
import { api } from '../../lib/api';

export const SystemHeader: React.FC = () => {
  const location = useLocation();
  const { user, isAuthenticated, logout, loginWithGithub } = useAuthStore();
  const { addToast } = useTelemetryStore();

  const [userScore, setUserScore] = useState<number | null>(null);
  const [isPricingOpen, setIsPricingOpen] = useState(false);
  const [isCmdOpen, setIsCmdOpen] = useState(false);

  // Framer motion scroll-linked transforms
  const { scrollY, scrollYProgress } = useScroll();
  const navY = useTransform(scrollY, [0, 120], [0, -3]);
  const navScale = useTransform(scrollY, [0, 120], [1, 0.985]);
  const progressWidth = useTransform(scrollYProgress, [0, 1], ['0%', '100%']);

  // Global Cmd+K / Ctrl+K keyboard shortcut listener
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCmdOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  useEffect(() => {
    if (isAuthenticated && user?.username) {
      api.getPublicProfile(user.username)
        .then((p) => {
          if (p && typeof p.cumulative_score === 'number') {
            setUserScore(p.cumulative_score);
          }
        })
        .catch(() => {});
    } else {
      setUserScore(null);
    }
  }, [isAuthenticated, user?.username]);

  const navLinks = [
    { label: 'Pricing', isModal: true, onClick: () => setIsPricingOpen(true) },
    { label: 'Discover', path: '/discovery' },
    { label: 'Pull Requests', path: '/prs' },
  ];

  return (
    <>
      {/* Floating Centered Pill / Capsule Navbar with Fixed Positioning to Stay On Screen When Scrolling */}
      <header className="fixed top-7 left-0 right-0 z-50 select-none flex justify-center pointer-events-none px-4 sm:px-6">
        <motion.div
          style={{ y: navY, scale: navScale }}
          className="pointer-events-auto relative flex h-12 items-center justify-between px-6 sm:px-8 w-full max-w-2xl rounded-full glass-nav border border-white/[0.08] hover:border-white/[0.18] shadow-[0_12px_36px_rgba(0,0,0,0.85)] transition-colors duration-300 overflow-hidden will-change-transform"
        >
          {/* Brand Wordmark (Left) */}
          <Link to="/" className="flex items-center gap-2 group shrink-0">
            <motion.span
              whileHover={{ scale: 1.06 }}
              whileTap={{ scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 550, damping: 25 }}
              className="font-display font-black text-base tracking-tight text-white transition-colors group-hover:text-accent-lime inline-block"
            >
              oasis<span className="text-accent-violet group-hover:text-accent-lime">.</span>
            </motion.span>
          </Link>

          {/* Nav Links (Center) */}
          <nav className="flex items-center gap-3 sm:gap-5 text-xs font-sans">
            {navLinks.map((link) => {
              if (link.isModal) {
                return (
                  <motion.button
                    key={link.label}
                    onClick={link.onClick}
                    whileHover={{ y: -1, scale: 1.04 }}
                    whileTap={{ scale: 0.95 }}
                    transition={{ type: 'spring', stiffness: 550, damping: 25 }}
                    className="text-text-secondary hover:text-white transition-colors cursor-pointer py-1 px-2.5 rounded-full hover:bg-white/[0.04] hover:text-accent-lime"
                  >
                    {link.label}
                  </motion.button>
                );
              }

              const isActive =
                location.pathname === link.path ||
                (link.path?.startsWith('/profile') && location.pathname.startsWith('/profile'));

              return (
                <Link
                  key={link.path}
                  to={link.path!}
                  className={`transition-colors py-1 px-2.5 rounded-full relative ${
                    isActive
                      ? 'text-accent-lime font-medium bg-white/[0.05]'
                      : 'text-text-secondary hover:text-white hover:bg-white/[0.04]'
                  }`}
                >
                  <motion.span
                    whileHover={{ y: -1 }}
                    whileTap={{ scale: 0.95 }}
                    transition={{ type: 'spring', stiffness: 550, damping: 25 }}
                    className="inline-block"
                  >
                    {link.label}
                  </motion.span>
                </Link>
              );
            })}
          </nav>

          {/* Auth State (Right) */}
          <div className="flex items-center gap-2.5 shrink-0">
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2.5">
                <Link
                  to={`/profile/${user.username}`}
                  className="flex items-center gap-2 py-1 px-2 rounded-full hover:bg-white/[0.04] transition-colors"
                >
                  {user.avatar_url ? (
                    <img
                      src={user.avatar_url}
                      alt={user.username}
                      className="h-5 w-5 rounded-full ring-1 ring-white/15"
                    />
                  ) : (
                    <div className="h-5 w-5 rounded-full bg-accent-violet/20 text-accent-violet flex items-center justify-center text-[10px] font-mono">
                      {user.username.slice(0, 1).toUpperCase()}
                    </div>
                  )}
                  <span className="text-white text-xs font-medium hidden sm:inline">@{user.username}</span>

                  <span className="text-[11px] font-mono text-accent-lime font-bold tracking-tight">
                    {userScore !== null ? `${userScore} pts` : '0 pts'}
                  </span>
                </Link>

                <motion.button
                  onClick={() => logout()}
                  whileHover={{ scale: 1.15, rotate: 8 }}
                  whileTap={{ scale: 0.9 }}
                  transition={{ type: 'spring', stiffness: 600, damping: 20 }}
                  title="Sign Out"
                  className="p-1.5 text-text-muted hover:text-accent-error transition-colors rounded-full hover:bg-white/[0.04] cursor-pointer"
                >
                  <LogOut className="h-3.5 w-3.5" />
                </motion.button>
              </div>
            ) : (
              <motion.button
                onClick={async () => {
                  try {
                    await loginWithGithub();
                  } catch (err: any) {
                    addToast({
                      type: 'error',
                      title: 'AUTHENTICATION FAILED',
                      message: err.message || 'Failed to initiate GitHub authentication.',
                    });
                  }
                }}
                whileHover={{ scale: 1.04, y: -1 }}
                whileTap={{ scale: 0.95 }}
                transition={{ type: 'spring', stiffness: 550, damping: 25 }}
                className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-accent-violet hover:bg-[#6c28d9] border border-white/10 hover:border-white/25 text-white text-xs font-medium shadow-[0_0_15px_rgba(125,57,235,0.3)] hover:shadow-[0_0_20px_rgba(125,57,235,0.45)] transition-all cursor-pointer"
              >
                <GithubIcon className="h-3.5 w-3.5" />
                <span>Sign in</span>
              </motion.button>
            )}
          </div>

          {/* Micro Scroll Progress Line along bottom of pill */}
          <motion.div
            style={{ width: progressWidth }}
            className="absolute bottom-0 left-0 h-[2px] bg-gradient-to-r from-accent-violet via-accent-lime to-accent-violet pointer-events-none opacity-80"
          />
        </motion.div>
      </header>

      {/* Command Palette Modal */}
      <CommandPalette isOpen={isCmdOpen} onClose={() => setIsCmdOpen(false)} />

      {/* Pricing Modal */}
      {isPricingOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
          <div className="w-full max-w-lg bg-[#09090C] rounded-[8px] p-6 shadow-2xl space-y-6 border border-white/[0.08]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-accent-lime" />
                <h2 className="text-base font-bold text-white font-sans">Open-Source Developer Tier</h2>
              </div>
              <button
                onClick={() => setIsPricingOpen(false)}
                className="text-text-muted hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed">
              Oasis is completely free for individual open-source developers contributing to vetted GitHub repositories. All AI evaluations and isolated workspaces are included.
            </p>

            <div className="p-4 rounded-[6px] bg-white/[0.02] space-y-2.5 text-xs text-text-secondary border border-white/[0.04]">
              <div className="flex items-center gap-2 text-white">
                <Check className="h-3.5 w-3.5 text-accent-lime" />
                <span>Unlimited Gatekeeper AI evaluations</span>
              </div>
              <div className="flex items-center gap-2 text-white">
                <Check className="h-3.5 w-3.5 text-accent-lime" />
                <span>Ephemeral in-browser Monaco workspaces</span>
              </div>
              <div className="flex items-center gap-2 text-white">
                <Check className="h-3.5 w-3.5 text-accent-lime" />
                <span>Automated PR webhook scoring & public profiles</span>
              </div>
              <div className="flex items-center gap-2 text-white">
                <Check className="h-3.5 w-3.5 text-accent-lime" />
                <span>Free-tier multi-provider LLM inference</span>
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setIsPricingOpen(false)}
                className="px-4 py-2 rounded-full bg-accent-violet hover:bg-[#5227FF] text-white text-xs font-medium transition-all"
              >
                Continue Reviewing
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
