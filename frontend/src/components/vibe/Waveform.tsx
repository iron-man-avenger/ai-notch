import React from "react";
import { motion } from "framer-motion";

interface WaveformProps {
  barCount?: number;
  color?: string;
  className?: string;
}

const DEFAULT_SCALES = [0.4, 0.9, 0.3, 1.2, 0.7, 0.5, 1.0, 0.6, 0.8];

export const Waveform: React.FC<WaveformProps> = ({
  barCount = 7,
  color = "#f43f5e", // Rose/Red for Teams call
  className = ""
}) => {
  const bars = Array.from({ length: barCount });

  return (
    <div className={`flex items-center gap-1 ${className}`}>
      {bars.map((_, i) => {
        const delay = i * 0.12;
        const baseScale = DEFAULT_SCALES[i % DEFAULT_SCALES.length];

        return (
          <motion.div
            key={i}
            className="w-1 h-3.5 rounded-full"
            style={{ backgroundColor: color }}
            animate={{
              scaleY: [baseScale, 1.6, 0.4, baseScale],
            }}
            transition={{
              duration: 1.1,
              repeat: Infinity,
              ease: "easeInOut",
              delay,
            }}
          />
        );
      })}
    </div>
  );
};

export default Waveform;
