import React, { useEffect, useMemo, type ReactNode } from "react";
import { motion, animate, useMotionValue, useSpring, useTransform } from "framer-motion";

interface AnimatedGradientBadgeProps {
  children: ReactNode;
  className?: string;
  duration?: number;
  rotationDuration?: number;
  gradients?: string[][];
  onClick?: () => void;
}

const defaultGradients = [
  ["#1e1b4b", "#312e81", "#4338ca"],
  ["#312e81", "#4338ca", "#6366f1"],
  ["#1e293b", "#334155", "#475569"],
  ["#0f172a", "#1e293b", "#334155"],
  ["#3730a3", "#4f46e5", "#6366f1"],
];

export const AnimatedGradientBadge: React.FC<AnimatedGradientBadgeProps> = ({
  children,
  className = "",
  duration = 5,
  rotationDuration = 10,
  gradients = defaultGradients,
  onClick
}) => {
  const safeGradients = useMemo(
    () => (gradients && gradients.length >= 2 ? gradients : defaultGradients),
    [gradients]
  );

  const angle = useMotionValue(0);
  const colorIndex = useMotionValue(0);
  const smoothIndex = useSpring(colorIndex, {
    stiffness: 15,
    damping: 15,
  });

  const mix = (start: string, end: string, progress: number) => {
    const s = parseInt(start.slice(1), 16);
    const e = parseInt(end.slice(1), 16);
    const sr = (s >> 16) & 255;
    const sg = (s >> 8) & 255;
    const sb = s & 255;
    const er = (e >> 16) & 255;
    const eg = (e >> 8) & 255;
    const eb = e & 255;
    const r = Math.round(sr + (er - sr) * progress);
    const g = Math.round(sg + (eg - sg) * progress);
    const b = Math.round(sb + (eb - sb) * progress);
    return `rgb(${r}, ${g}, ${b})`;
  };

  const background = useTransform(
    [angle, smoothIndex],
    (latest) => {
      const [a, iRaw] = latest as number[];
      const len = safeGradients.length;
      const i = Number.isFinite(iRaw) ? iRaw : 0;
      const index = ((Math.floor(i) % len) + len) % len;
      const next = (index + 1) % len;
      const t = i - Math.floor(i);

      const [c1a, c2a, c3a] = safeGradients[index] ?? safeGradients[0];
      const [c1b, c2b, c3b] = safeGradients[next] ?? safeGradients[0];

      return `linear-gradient(${a}deg,
        ${mix(c1a, c1b, t)} 10%,
        ${mix(c2a, c2b, t)} 60%,
        ${mix(c3a, c3b, t)} 100%)`;
    }
  );

  useEffect(() => {
    const rotate = animate(angle, 360, {
      duration: rotationDuration,
      ease: "linear",
      repeat: Infinity,
    });
    const colors = animate(colorIndex, safeGradients.length, {
      duration: safeGradients.length * duration,
      ease: "linear",
      repeat: Infinity,
    });
    return () => {
      rotate.stop();
      colors.stop();
    };
  }, [angle, colorIndex, safeGradients, duration, rotationDuration]);

  return (
    <motion.div
      style={{ background }}
      onClick={onClick}
      className={`rounded-xl border border-white/10 ${className}`}
    >
      {children}
    </motion.div>
  );
};

export default AnimatedGradientBadge;
