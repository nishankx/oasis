import React, { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';

interface Point {
  x: number;
  y: number;
  char: string;
  isInteractive: boolean;
}

const TRAIL_CHARS = ['+', '*', ':', '.', "'", '"', '\\', '/'];
const INTERACTIVE_CHARS = ['#', '>', '@', '$', '*', '+'];
const MAX_TRAIL_LENGTH = 8;
const MAGNETIC_PROXIMITY = 45; // Pixels distance to trigger subtle pull
const MAGNETIC_STRENGTH = 0.28; // Subtle pull factor

export const AsciiCursor: React.FC = () => {
  const location = useLocation();
  const [isSupported, setIsSupported] = useState(true);

  const realMouse = useRef<{ x: number; y: number }>({ x: -100, y: -100 });
  const springHead = useRef<{ x: number; y: number; vx: number; vy: number }>({
    x: -100,
    y: -100,
    vx: 0,
    vy: 0,
  });
  const trailRef = useRef<Point[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);
  const animFrameId = useRef<number | null>(null);

  const isInteractiveRef = useRef(false);
  const isSuppressedRef = useRef(false);

  // Suppress entirely in Monaco workspace
  const isWorkspaceRoute = location.pathname.startsWith('/workspace');

  useEffect(() => {
    // Check touch devices or reduced motion
    const isTouch = 'ontouchstart' in window || window.matchMedia('(pointer: coarse)').matches;
    const isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (isTouch || isReducedMotion || isWorkspaceRoute) {
      setIsSupported(false);
      return;
    }

    setIsSupported(true);

    const handleMouseMove = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;

      // Disable inside Monaco editor or suppress tags
      if (
        target?.closest('.no-ascii-cursor') ||
        target?.closest('.monaco-editor') ||
        target?.tagName === 'INPUT' ||
        target?.tagName === 'TEXTAREA' ||
        target?.tagName === 'SELECT'
      ) {
        isSuppressedRef.current = true;
        return;
      }

      isSuppressedRef.current = false;

      let mx = e.clientX;
      let my = e.clientY;

      // Magnetic Attraction Check: Find nearest interactive element
      const interactiveEl = target?.closest('button, a, [role="button"], input[type="submit"]') as HTMLElement | null;
      if (interactiveEl) {
        isInteractiveRef.current = true;
        const rect = interactiveEl.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const dist = Math.hypot(mx - centerX, my - centerY);

        if (dist < MAGNETIC_PROXIMITY + Math.max(rect.width, rect.height) / 2) {
          // Gently pull target coordinates toward element center
          mx += (centerX - mx) * MAGNETIC_STRENGTH;
          my += (centerY - my) * MAGNETIC_STRENGTH;
        }
      } else {
        isInteractiveRef.current = false;
      }

      realMouse.current = { x: mx, y: my };
    };

    const handleMouseLeave = () => {
      isSuppressedRef.current = true;
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseleave', handleMouseLeave);

    // Initialize trail points
    trailRef.current = Array.from({ length: MAX_TRAIL_LENGTH }, () => ({
      x: -100,
      y: -100,
      char: '+',
      isInteractive: false,
    }));

    let charCycle = 0;

    // Physical Spring Loop with inertia and lag
    const updatePhysics = () => {
      if (!isSuppressedRef.current && realMouse.current.x > 0) {
        charCycle++;
        const isInteractive = isInteractiveRef.current;

        // Spring interpolation for head position
        const dx = realMouse.current.x - springHead.current.x;
        const dy = realMouse.current.y - springHead.current.y;

        // Spring stiffness & damping constants
        const springK = 0.24;
        springHead.current.vx = springHead.current.vx * 0.65 + dx * springK;
        springHead.current.vy = springHead.current.vy * 0.65 + dy * springK;

        springHead.current.x += springHead.current.vx;
        springHead.current.y += springHead.current.vy;

        // Shift characters
        const charSet = isInteractive ? INTERACTIVE_CHARS : TRAIL_CHARS;
        const activeChar = charSet[Math.floor(charCycle / 3) % charSet.length];

        // Lead point follows spring head
        trailRef.current[0].x = springHead.current.x;
        trailRef.current[0].y = springHead.current.y;
        trailRef.current[0].char = activeChar;
        trailRef.current[0].isInteractive = isInteractive;

        // Subsequent trail points drift with spring lag behind previous points
        for (let i = 1; i < MAX_TRAIL_LENGTH; i++) {
          const prev = trailRef.current[i - 1];
          const curr = trailRef.current[i];
          const lag = 0.38 - i * 0.02;

          curr.x += (prev.x - curr.x) * lag;
          curr.y += (prev.y - curr.y) * lag;
          curr.char = charSet[(Math.floor(charCycle / 3) + i) % charSet.length];
          curr.isInteractive = isInteractive;
        }

        // Render directly to DOM nodes
        if (containerRef.current) {
          const nodes = containerRef.current.children;
          for (let i = 0; i < MAX_TRAIL_LENGTH; i++) {
            const el = nodes[i] as HTMLElement | undefined;
            const pt = trailRef.current[i];
            if (el) {
              const opacity = Math.max(0, 1 - (i * 0.14));
              el.style.transform = `translate3d(${pt.x}px, ${pt.y}px, 0)`;
              el.textContent = pt.char;
              el.style.opacity = `${opacity}`;
              el.style.color = isInteractive
                ? (i === 0 ? '#C6FF33' : '#7D39EB')
                : '#FFFFFF';
              el.style.display = 'block';
            }
          }
        }
      } else if (containerRef.current) {
        const nodes = containerRef.current.children;
        for (let i = 0; i < nodes.length; i++) {
          (nodes[i] as HTMLElement).style.display = 'none';
        }
      }

      animFrameId.current = requestAnimationFrame(updatePhysics);
    };

    animFrameId.current = requestAnimationFrame(updatePhysics);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      if (animFrameId.current) {
        cancelAnimationFrame(animFrameId.current);
      }
    };
  }, [isWorkspaceRoute]);

  if (!isSupported || isWorkspaceRoute) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 z-[99999] overflow-hidden select-none font-mono text-xs font-bold leading-none"
    >
      {Array.from({ length: MAX_TRAIL_LENGTH }).map((_, index) => (
        <span
          key={index}
          style={{
            position: 'absolute',
            top: -6,
            left: -6,
            willChange: 'transform, opacity',
            transition: 'color 0.12s ease',
            textShadow: index === 0 ? '0 0 10px rgba(125,57,235,0.7)' : 'none',
            display: 'none',
          }}
        >
          +
        </span>
      ))}
    </div>
  );
};
