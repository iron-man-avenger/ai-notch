import React, { useEffect, type ReactNode } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";

interface OrbitBorderProps {
  children: ReactNode;
  className?: string;
  ringColors?: string[];
  rotate?: number;
  padding?: number;
  rounded?: number;
  onClick?: () => void;
}

export const OrbitBorder: React.FC<OrbitBorderProps> = ({
  children,
  className = "",
  ringColors = ["#6366f1", "#a855f7", "#ec4899", "#3b82f6"],
  rotate = 0,
  padding = 1.5,
  rounded = 16,
  onClick
}) => {
  const angle = useMotionValue(0);

  const animatedBorder = useTransform(
    angle,
    (a) => `linear-gradient(${a}deg, ${ringColors.join(", ")})`
  );

  useEffect(() => {
    const controls = animate(angle, 360, {
      duration: 6,
      repeat: Infinity,
      ease: "linear",
    });
    return () => controls.stop();
  }, [angle]);

  return (
    <motion.div
      className="inline-block relative cursor-pointer"
      style={{
        background: animatedBorder,
        rotate: `${rotate}deg`,
        padding: `${padding}px`,
        borderRadius: `${rounded}px`
      }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
    >
      <div
        className={`bg-slate-900/90 backdrop-blur-md ${className}`}
        style={{ borderRadius: `${Math.max(0, rounded - padding)}px` }}
      >
        {children}
      </div>
    </motion.div>
  );
};

export default OrbitBorder;
