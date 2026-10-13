import React, { useEffect, useRef } from 'react';
import { BotEngine } from '../coucou/mochi/engine';
import { Sound } from '../coucou/core/sound';
import { voice } from '../utils/voice';
import type { BotStateName, BotEmoteName } from '../coucou/core/layout';
import type { Outfit } from '../coucou/mochi/wardrobe';

interface MochiProps {
  state?: BotStateName | 'meeting' | 'waving' | 'listening';
  emote?: BotEmoteName;
  outfit?: Outfit;
  size?: number; // logical pixels (e.g. 20, 32, 48, 76)
  interactive?: boolean;
  talking?: boolean;
  onClick?: () => void;
  onContextMenu?: (e: React.MouseEvent) => void;
  className?: string;
  badge?: 'dots' | 'bang' | 'question' | 'dot' | 'working' | 'none';
}

export const Mochi: React.FC<MochiProps> = ({
  state = 'idle',
  emote,
  outfit = 'none',
  size = 32,
  interactive = true,
  talking,
  onClick,
  onContextMenu,
  className = '',
  badge
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<BotEngine | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(performance.now());
  const greetedRef = useRef(false);

  // Map legacy state strings if any
  const normalizedState: BotStateName = 
    state === 'meeting' ? 'working' :
    state === 'listening' ? 'question' :
    state === 'waving' ? 'idle' :
    (state as BotStateName);

  // Initialize engine once
  if (!engineRef.current) {
    const eng = new BotEngine();
    eng.particleOverhang = 0;
    eng.setState(normalizedState, true);
    if (outfit !== 'none') eng.setOutfit(outfit);
    engineRef.current = eng;
  }

  // Preload Coucou audio on first render
  useEffect(() => {
    Sound.preload().catch(() => {});
  }, []);

  // Talking speech articulation sync
  useEffect(() => {
    if (talking !== undefined && engineRef.current) {
      engineRef.current.setTalking(talking);
    }
  }, [talking]);

  useEffect(() => {
    const unsub = voice.onTalkingChange((isTalking) => {
      if (talking === undefined && engineRef.current) {
        engineRef.current.setTalking(isTalking);
      }
    });
    return unsub;
  }, [talking]);

  // Sync state & badges
  useEffect(() => {
    const engine = engineRef.current;
    if (!engine) return;

    engine.setState(normalizedState);

    if (badge && badge !== 'none') {
      const kind = badge === 'working' ? 'dots' : badge;
      engine.setBadge({ kind: kind as any, color: [0.23, 0.62, 1] });
    }

    if (state === 'waving' && !greetedRef.current) {
      greetedRef.current = true;
      engine.greet();
    } else if (state !== 'waving') {
      greetedRef.current = false;
    }
  }, [normalizedState, badge, state]);

  // Sync outfit
  useEffect(() => {
    if (engineRef.current) {
      engineRef.current.setOutfit(outfit);
    }
  }, [outfit]);

  // Trigger emote if passed
  useEffect(() => {
    if (engineRef.current && emote) {
      engineRef.current.triggerEmote(emote, 2.0);
    }
  }, [emote]);

  // Main Canvas Render Loop (30-60fps, DPR aware)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let isRunning = true;
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(size * dpr);
    canvas.height = Math.round(size * dpr);

    const render = (now: number) => {
      if (!isRunning) return;
      const dt = Math.min(0.1, (now - lastTimeRef.current) / 1000);
      lastTimeRef.current = now;

      const engine = engineRef.current;
      if (engine) {
        engine.update(dt);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.clearRect(0, 0, size, size);
        engine.draw(ctx, size, size);
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    lastTimeRef.current = performance.now();
    animFrameRef.current = requestAnimationFrame(render);

    return () => {
      isRunning = false;
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [size]);

  // Cursor Tracking (Mochi's eyes follow the mouse naturally)
  useEffect(() => {
    if (!interactive) return;
    const handleMouseMove = (e: MouseEvent) => {
      const canvas = canvasRef.current;
      const engine = engineRef.current;
      if (!canvas || !engine) return;
      const rect = canvas.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;

      // Positive dx (cursor right of Mochi) -> eyes move right (+lookX)
      // Negative dy (cursor above Mochi) -> eyes move up (+lookY)
      // Positive dy (cursor below Mochi) -> eyes move down (-lookY)
      engine.lookX = Math.tanh(dx / 70);
      engine.lookY = -Math.tanh(dy / 50);
    };

    const handleMouseLeave = () => {
      const engine = engineRef.current;
      if (engine) {
        engine.lookX = 0;
        engine.lookY = 0;
      }
    };

    window.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseleave', handleMouseLeave);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [interactive]);

  const handleClick = () => {
    if (!interactive) return;
    const engine = engineRef.current;
    if (engine) {
      engine.slap();
    }
    onClick?.();
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    if (onContextMenu) {
      e.preventDefault();
      onContextMenu(e);
    }
  };

  return (
    <canvas
      ref={canvasRef}
      onClick={handleClick}
      onContextMenu={handleContextMenu}
      style={{
        width: size,
        height: size,
        cursor: interactive ? 'pointer' : 'default',
        verticalAlign: 'middle'
      }}
      className={`select-none ${className}`}
    />
  );
};

export default Mochi;
