import React, { useEffect, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AnimatePresence, motion, useScroll, useTransform } from 'framer-motion';
import Lenis from 'lenis';
import { SystemHeader } from './components/chrome/SystemHeader';
import { ToastContainer } from './components/chrome/ToastContainer';
import { LandingPage } from './pages/LandingPage';
import { AuthCallbackPage } from './pages/AuthCallbackPage';
import { useAuthStore } from './store/useAuthStore';
import { pageTransitionVariants } from './lib/motion';
import { Loader2 } from 'lucide-react';

// Lazy-loaded pages
const DiscoveryPage = lazy(() => import('./pages/DiscoveryPage').then(m => ({ default: m.DiscoveryPage })));
const WorkspacePage = lazy(() => import('./pages/WorkspacePage').then(m => ({ default: m.WorkspacePage })));
const WorkspacesListPage = lazy(() => import('./pages/WorkspacesListPage').then(m => ({ default: m.WorkspacesListPage })));
const PrsPage = lazy(() => import('./pages/PrsPage').then(m => ({ default: m.PrsPage })));
const ProfilePage = lazy(() => import('./pages/ProfilePage').then(m => ({ default: m.ProfilePage })));
const LeaderboardPage = lazy(() => import('./pages/LeaderboardPage').then(m => ({ default: m.LeaderboardPage })));

const PageLoader = () => (
  <div className="min-h-[60vh] flex flex-col items-center justify-center gap-3 font-mono text-xs text-text-muted">
    <Loader2 className="h-5 w-5 text-accent-violet animate-spin" />
    <span className="tracking-widest uppercase text-[10px]">Loading module...</span>
  </div>
);

const AnimatedRoutes: React.FC = () => {
  const location = useLocation();
  const isWorkspace = location.pathname.startsWith('/workspace');

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        variants={isWorkspace ? undefined : pageTransitionVariants}
        initial={isWorkspace ? undefined : 'initial'}
        animate={isWorkspace ? undefined : 'animate'}
        exit={isWorkspace ? undefined : 'exit'}
        className="flex-1 flex flex-col"
      >
        <Suspense fallback={<PageLoader />}>
          <Routes location={location}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/auth/callback" element={<AuthCallbackPage />} />
            <Route path="/discovery" element={<DiscoveryPage />} />
            <Route path="/workspaces" element={<WorkspacesListPage />} />
            <Route path="/workspace/:id" element={<WorkspacePage />} />
            <Route path="/prs" element={<PrsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/profile/:username" element={<ProfilePage />} />
            <Route path="/leaderboard" element={<LeaderboardPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </motion.div>
    </AnimatePresence>
  );
};

const AppContent: React.FC = () => {
  const location = useLocation();
  const isWorkspace = location.pathname.startsWith('/workspace');

  // Scroll tracking for ambient background parallax
  const { scrollY } = useScroll();
  const topGlowY = useTransform(scrollY, [0, 1000], [0, -140]);
  const midGlowY = useTransform(scrollY, [0, 1000], [0, 120]);
  const bottomGlowY = useTransform(scrollY, [0, 1000], [0, -90]);
  const linesY = useTransform(scrollY, [0, 1000], [0, -30]);

  useEffect(() => {
    // Respect reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return;
    }

    const lenis = new Lenis({
      duration: 1.0,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    });

    let frameId: number;
    function raf(time: number) {
      lenis.raf(time);
      frameId = requestAnimationFrame(raf);
    }
    frameId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(frameId);
      lenis.destroy();
    };
  }, []);

  return (
    <div className="flex flex-col min-h-screen bg-[#040406] text-text-primary selection:bg-accent-violet selection:text-white font-sans text-xs relative">
      {/* Global Minimalist Architectural Background: Prominent Grid Lines + Brighter Tint + Ambient Parallax Glows */}
      <div
        aria-hidden="true"
        className="fixed inset-0 z-0 pointer-events-none bg-minimal-lines overflow-hidden"
      >
        {/* Luminous atmospheric depth vignette with brighter violet/obsidian tint */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_90%_65%_at_50%_0%,rgba(38,28,62,0.85)_0%,rgba(18,14,30,0.92)_45%,#040406_100%)]" />

        {/* Parallax ambient background glows powered by useScroll + useTransform */}
        {/* Center top ambient violet glow */}
        <motion.div
          style={{ y: topGlowY }}
          className="absolute -top-28 left-1/2 -translate-x-1/2 w-[720px] h-[380px] bg-[radial-gradient(ellipse_at_center,rgba(125,57,235,0.22)_0%,rgba(82,39,255,0.08)_50%,transparent_75%)] blur-3xl pointer-events-none will-change-transform"
        />

        {/* Mid-left ambient glow */}
        <motion.div
          style={{ y: midGlowY }}
          className="absolute top-1/3 -left-28 w-[500px] h-[500px] bg-[radial-gradient(circle_at_center,rgba(125,57,235,0.12)_0%,transparent_70%)] blur-3xl pointer-events-none will-change-transform"
        />

        {/* Lower-right ambient glow */}
        <motion.div
          style={{ y: bottomGlowY }}
          className="absolute bottom-12 -right-28 w-[600px] h-[500px] bg-[radial-gradient(circle_at_center,rgba(82,39,255,0.12)_0%,transparent_70%)] blur-3xl pointer-events-none will-change-transform"
        />

        {/* Delicate architectural vertical guide lines */}
        <motion.div
          style={{ y: linesY }}
          className="absolute inset-0 max-w-5xl mx-auto border-x border-white/[0.04] pointer-events-none"
        />
      </div>

      {/* Floating Centered Button-Like Navbar (Omitted on Workspace for full-screen Monaco) */}
      {!isWorkspace && (
        <div className="relative z-50">
          <SystemHeader />
        </div>
      )}

      {/* Route Content (Full-height on workspace, padded below fixed navbar on other pages) */}
      <main className={`flex-1 flex flex-col relative z-10 ${!isWorkspace ? 'pt-24' : ''}`}>
        <AnimatedRoutes />
      </main>

      {/* Async Toast Notifications */}
      <ToastContainer />
    </div>
  );
};

export function App() {
  const { initSession } = useAuthStore();

  useEffect(() => {
    initSession();
  }, [initSession]);

  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}

export default App;
