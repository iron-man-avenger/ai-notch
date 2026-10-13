import React, { useRef } from "react";
import { motion, useMotionTemplate, useMotionValue } from "framer-motion";

interface SpotlightBackgroundProps {
  className?: string;
  spotlightSize?: number;
}

export const SpotlightBackground: React.FC<SpotlightBackgroundProps> = ({
  className = "",
  spotlightSize = 220,
}) => {
  const backgroundRef = useRef<HTMLDivElement>(null);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  function handleMouseMove(e: React.MouseEvent) {
    if (!backgroundRef.current) return;
    const rect = backgroundRef.current.getBoundingClientRect();
    mouseX.set(e.clientX - rect.left);
    mouseY.set(e.clientY - rect.top);
  }

  return (
    <div
      ref={backgroundRef}
      onMouseMove={handleMouseMove}
      className={`absolute inset-0 overflow-hidden pointer-events-auto rounded-3xl ${className}`}
    >
      {/* Base Layer: Soft dots with subtle opacity */}
      <div
        className="absolute inset-0 
        [background-image:radial-gradient(rgba(255,255,255,0.08)_1px,transparent_1px)] 
        [background-size:20px_20px] 
        [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_60%,transparent_100%)]"
      />

      {/* Hover Layer: Interactive dynamic cursor spotlight */}
      <motion.div
        className="absolute inset-0 
        [background-image:radial-gradient(rgba(99,102,241,0.25)_2px,transparent_2px)] 
        [background-size:20px_20px]"
        style={{
          maskImage: useMotionTemplate`radial-gradient(circle ${spotlightSize}px at ${mouseX}px ${mouseY}px, black 0%, transparent 100%)`,
          WebkitMaskImage: useMotionTemplate`radial-gradient(circle ${spotlightSize}px at ${mouseX}px ${mouseY}px, black 0%, transparent 100%)`,
        }}
      />
    </div>
  );
};

export default SpotlightBackground;
