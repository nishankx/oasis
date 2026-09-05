import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { ArrowRight } from 'lucide-react';
import { GithubIcon } from '../components/ui/GithubIcon';
import { useAuthStore } from '../store/useAuthStore';
import { useTelemetryStore } from '../store/useTelemetryStore';
import {
  wordRevealContainer,
  wordRevealItem,
  buttonStaggerVariants,
} from '../lib/motion';

const MOTTO_WORDS = ['Review', 'Code', 'the', 'Right', 'Way'];

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, loginWithGithub } = useAuthStore();
  const { addToast } = useTelemetryStore();

  // Scroll parallax for hero motto and CTA
  const { scrollY } = useScroll();
  const heroY = useTransform(scrollY, [0, 400], [0, -50]);
  const heroOpacity = useTransform(scrollY, [0, 300], [1, 0.25]);
  const heroScale = useTransform(scrollY, [0, 400], [1, 0.96]);

  const handleAction = async () => {
    if (isAuthenticated) {
      navigate('/discovery');
    } else {
      try {
        await loginWithGithub();
      } catch (err: any) {
        addToast({
          type: 'error',
          title: 'AUTHENTICATION ERROR',
          message: err.message || 'Failed to initiate GitHub authentication.',
        });
      }
    }
  };

  return (
    <div className="min-h-[calc(100vh-160px)] w-full flex flex-col items-center justify-center relative px-6 select-none bg-transparent">
      {/* Hero Content Container with Scroll-Linked Parallax */}
      <motion.div
        style={{ y: heroY, opacity: heroOpacity, scale: heroScale }}
        className="relative z-10 flex flex-col items-center text-center max-w-4xl mx-auto space-y-12 will-change-transform"
      >
        {/* Word-by-Word Typographic Motto Reveal with Snappy Spring */}
        <motion.h1
          variants={wordRevealContainer}
          initial="hidden"
          animate="visible"
          className="font-display font-black text-4xl sm:text-6xl md:text-7xl lg:text-8xl text-white tracking-tight leading-[1.08] flex flex-wrap items-center justify-center gap-x-3 sm:gap-x-5 drop-shadow-[0_4px_30px_rgba(0,0,0,0.9)]"
        >
          {MOTTO_WORDS.map((word, index) => (
            <motion.span
              key={index}
              variants={wordRevealItem}
              whileHover={{ scale: 1.08, y: -4, color: "#C6FF33" }}
              transition={{ type: "spring", stiffness: 600, damping: 20 }}
              className="inline-block cursor-default select-none"
            >
              {word}
            </motion.span>
          ))}
        </motion.h1>

        {/* Staggered Minimalist CTA Button with Abrupt Spring */}
        <motion.div
          variants={buttonStaggerVariants}
          initial="hidden"
          animate="visible"
        >
          <motion.button
            onClick={handleAction}
            whileHover={{ y: -4, scale: 1.04 }}
            whileTap={{ scale: 0.95 }}
            transition={{ type: "spring", stiffness: 500, damping: 22, mass: 0.7 }}
            className="group relative flex items-center gap-3.5 px-9 py-4 rounded-full bg-accent-violet hover:bg-[#6c28d9] border border-white/15 hover:border-white/35 text-white font-sans font-medium text-sm transition-colors duration-200 shadow-[0_0_25px_rgba(125,57,235,0.4)] hover:shadow-[0_0_40px_rgba(125,57,235,0.6)] cursor-pointer overflow-hidden"
          >
            {/* Subtle animated shimmer highlight across button */}
            <motion.div
              animate={{
                x: ['-100%', '200%'],
              }}
              transition={{
                repeat: Infinity,
                duration: 3,
                ease: 'easeInOut',
                repeatDelay: 2,
              }}
              className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-white/15 to-transparent pointer-events-none -skew-x-12"
            />

            {!isAuthenticated && (
              <GithubIcon className="h-4 w-4 text-white group-hover:rotate-12 transition-transform duration-200" />
            )}
            <span className="group-hover:translate-x-0.5 transition-transform duration-150">
              {isAuthenticated ? 'Open Discover' : 'Sign in with GitHub'}
            </span>
            <ArrowRight className="h-4 w-4 text-white/70 group-hover:text-white group-hover:translate-x-1.5 transition-all duration-200" />
          </motion.button>
        </motion.div>
      </motion.div>
    </div>
  );
};
