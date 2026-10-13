import React, { useEffect } from "react";
import { motion, useMotionValue, useTransform, animate, useSpring } from "framer-motion";

interface PulsePingProps {
  size?: number;
  className?: string;
}

export const PulsePing: React.FC<PulsePingProps> = ({ size = 10, className = "" }) => {
  const angle = useMotionValue(0);
  const colorIndex = useMotionValue(0);

  const smoothAngle = useSpring(angle, { stiffness: 30, damping: 20 });
  const smoothIndex = useSpring(colorIndex, { stiffness: 15, damping: 15 });

  const gradients = [
    ["#10b981", "#34d399", "#6ee7b7"], // Emerald
    ["#3b82f6", "#60a5fa", "#93c5fd"], // Blue
    ["#8b5cf6", "#a78bfa", "#c4b5fd"], // Purple
    ["#06b6d4", "#22d3ee", "#67e8f9"], // Cyan
  ];

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

  const background = useTransform([smoothAngle, smoothIndex], (values: number[]) => {
    const [a, i] = values;
    const index = Math.floor(i) % gradients.length;
    const nextIndex = (index + 1) % gradients.length;
    const t = i - Math.floor(i);

    const [c1a, c2a, c3a] = gradients[index];
    const [c1b, c2b, c3b] = gradients[nextIndex];

    const c1 = mix(c1a, c1b, t);
    const c2 = mix(c2a, c2b, t);
    const c3 = mix(c3a, c3b, t);

    return `linear-gradient(${a}deg, ${c1} 10%, ${c2} 60%, ${c3} 100%)`;
  });

  useEffect(() => {
    const aCtrl = animate(angle, 360, {
      duration: 8,
      ease: "linear",
      repeat: Infinity,
    });

    const cCtrl = animate(colorIndex, gradients.length, {
      duration: gradients.length * 4,
      ease: "linear",
      repeat: Infinity,
    });

    return () => {
      aCtrl.stop();
      cCtrl.stop();
    };
  }, [angle, colorIndex, gradients.length]);

  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      <motion.div
        style={{
          width: size,
          height: size,
          background,
        }}
        className="rounded-full shadow-lg"
      />
      <motion.div
        animate={{ scale: [1, 2.2, 1], opacity: [0.6, 0, 0.6] }}
        transition={{ duration: 2, repeat: Infinity, ease: "easeOut" }}
        className="absolute rounded-full bg-emerald-400/40"
        style={{ width: size, height: size }}
      />
    </div>
  );
};

export default PulsePing;
