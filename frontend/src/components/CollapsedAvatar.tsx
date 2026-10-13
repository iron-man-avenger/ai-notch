import React, { useRef } from 'react';
import { BotAvatar } from 'bot-avatars';
import { Maximize2 } from 'lucide-react';
import { api } from '../api';

interface CollapsedAvatarProps {
  isBusy: boolean;
  onExpand: () => void;
  pendingCount: number;
}

export const CollapsedAvatar: React.FC<CollapsedAvatarProps> = ({
  isBusy,
  onExpand,
  pendingCount
}) => {
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);

  const handleMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = false;
    dragStartRef.current = { x: e.screenX, y: e.screenY };

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!dragStartRef.current) return;
      const dx = moveEvent.screenX - dragStartRef.current.x;
      const dy = moveEvent.screenY - dragStartRef.current.y;
      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
        isDraggingRef.current = true;
        api.moveWindow(dx, dy);
        dragStartRef.current = { x: moveEvent.screenX, y: moveEvent.screenY };
      }
    };

    const handleMouseUp = () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const handleClick = () => {
    if (!isDraggingRef.current) {
      onExpand();
    }
  };

  return (
    <div
      onMouseDown={handleMouseDown}
      onClick={handleClick}
      title="Click to open Assistant Dock (Drag to move)"
      className="relative flex items-center justify-center w-14 h-14 bg-white border border-neutral-300 rounded-full shadow-lg shadow-black/10 cursor-pointer hover:scale-105 active:scale-95 transition-transform group"
    >
      {/* Bot Avatar from libraries-dev */}
      <div className="pointer-events-none flex items-center justify-center">
        <BotAvatar
          type="circle"
          state={isBusy ? 'working' : 'default'}
          size={36}
          shading="plastic"
        />
      </div>

      {/* Pending badge */}
      {pendingCount > 0 && (
        <span className="absolute -top-1 -right-1 bg-black text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
          {pendingCount}
        </span>
      )}

      {/* Hover Expand Indicator */}
      <div className="absolute inset-0 bg-black/5 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
        <Maximize2 className="w-3.5 h-3.5 text-black" />
      </div>
    </div>
  );
};

export default CollapsedAvatar;
