import React, { useRef } from 'react';
import { 
  Bell, 
  Newspaper, 
  Settings as SettingsIcon, 
  PhoneCall, 
  Sparkles, 
  GripHorizontal,
  Minimize2
} from 'lucide-react';
import { BotAvatar } from 'bot-avatars';
import type { ActivityInfo } from '../types';
import { api } from '../api';

interface DockBarProps {
  activity: ActivityInfo;
  inMeeting: boolean;
  meetingSubject?: string;
  pendingTasksCount: number;
  onOpenEOD: () => void;
  onOpenTasks: () => void;
  onOpenNews: () => void;
  onOpenSettings: () => void;
  onSimulateCall: () => void;
  onCollapse: () => void;
}

export const DockBar: React.FC<DockBarProps> = ({
  activity,
  inMeeting,
  meetingSubject,
  pendingTasksCount,
  onOpenEOD,
  onOpenTasks,
  onOpenNews,
  onOpenSettings,
  onSimulateCall,
  onCollapse
}) => {
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);

  // Smooth dragging mechanism that directly moves the native Windows dock
  const handleDragStart = (e: React.MouseEvent) => {
    dragStartRef.current = { x: e.screenX, y: e.screenY };

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!dragStartRef.current) return;
      const dx = moveEvent.screenX - dragStartRef.current.x;
      const dy = moveEvent.screenY - dragStartRef.current.y;
      if (dx !== 0 || dy !== 0) {
        api.moveWindow(dx, dy);
        dragStartRef.current = { x: moveEvent.screenX, y: moveEvent.screenY };
      }
    };

    const handleMouseUp = () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      dragStartRef.current = null;
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    if (mins >= 60) {
      const hrs = Math.floor(mins / 60);
      return `${hrs}h ${mins % 60}m`;
    }
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="clean-white-panel rounded-full px-3 py-1.5 flex items-center gap-2 select-none shadow-xl border border-neutral-200 transition-all">
      
      {/* Native Drag Handle */}
      <div 
        onMouseDown={handleDragStart}
        title="Drag dock to move"
        className="flex items-center justify-center p-1.5 text-neutral-400 hover:text-black cursor-grab active:cursor-grabbing transition"
      >
        <GripHorizontal className="w-4 h-4" />
      </div>

      {/* Bot Avatar Mascot from libraries-dev */}
      <div 
        onClick={onCollapse}
        title="Click to collapse dock into avatar icon"
        className="flex items-center justify-center cursor-pointer hover:scale-105 active:scale-95 transition-transform"
      >
        <BotAvatar
          type="circle"
          state={inMeeting ? 'working' : 'default'}
          size={32}
          shading="plastic"
        />
      </div>

      {/* Real-time Tracking Pill: Pure White / Neutral */}
      <div className="flex items-center gap-2 bg-neutral-100 rounded-full px-3 py-1 border border-neutral-200 min-w-[200px] max-w-[320px]">
        {inMeeting ? (
          <div className="flex items-center gap-2 overflow-hidden">
            <span className="w-2 h-2 rounded-full bg-black animate-pulse flex-shrink-0" />
            <div className="flex flex-col overflow-hidden text-left">
              <span className="text-[10px] font-bold text-black uppercase tracking-wider flex items-center gap-1">
                <PhoneCall className="w-2.5 h-2.5" /> Teams Call
              </span>
              <span className="text-xs text-neutral-800 font-medium truncate max-w-[180px]">
                {meetingSubject || "Active Meeting"}
              </span>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 w-full overflow-hidden">
            <span className="w-2 h-2 rounded-full bg-black flex-shrink-0" />
            <div className="flex flex-col overflow-hidden text-left flex-grow">
              <div className="flex items-center justify-between text-[11px] font-semibold text-black">
                <span className="truncate max-w-[140px]">{activity.app}</span>
                <span className="text-[10px] text-neutral-500 font-mono font-normal">{formatTime(activity.duration)}</span>
              </div>
              <span className="text-[11px] text-neutral-600 truncate" title={activity.title}>
                {activity.title}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Actions: Clean Black & White Buttons */}
      <div className="flex items-center gap-1">
        
        {/* End of Day Summary Button (Solid Black with White Text) */}
        <button
          onClick={onOpenEOD}
          title="Daily Task Summary"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-black hover:bg-neutral-800 text-white text-xs font-semibold transition cursor-pointer"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>EOD Tasks</span>
        </button>

        {/* Tasks & Follow-up Reminders */}
        <button
          onClick={onOpenTasks}
          title="Tasks & Meeting Reminders"
          className="relative p-2 rounded-full hover:bg-neutral-100 text-black border border-transparent hover:border-neutral-200 transition cursor-pointer"
        >
          <Bell className="w-4 h-4" />
          {pendingTasksCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 bg-black text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
              {pendingTasksCount}
            </span>
          )}
        </button>

        {/* Relevant News */}
        <button
          onClick={onOpenNews}
          title="Context Tech News"
          className="p-2 rounded-full hover:bg-neutral-100 text-black border border-transparent hover:border-neutral-200 transition cursor-pointer"
        >
          <Newspaper className="w-4 h-4" />
        </button>

        {/* Settings */}
        <button
          onClick={onOpenSettings}
          title="Settings"
          className="p-2 rounded-full hover:bg-neutral-100 text-black border border-transparent hover:border-neutral-200 transition cursor-pointer"
        >
          <SettingsIcon className="w-4 h-4" />
        </button>

        {/* Test Call Simulation Button */}
        <button
          onClick={onSimulateCall}
          title="Simulate Teams Call Finish"
          className="px-2 py-1 text-[10px] font-medium rounded-full bg-neutral-100 hover:bg-neutral-200 text-neutral-700 transition cursor-pointer"
        >
          Test Call
        </button>

        {/* Collapse into Avatar Button */}
        <button
          onClick={onCollapse}
          title="Minimize dock into small avatar icon"
          className="p-1.5 rounded-full hover:bg-neutral-100 text-neutral-500 hover:text-black transition cursor-pointer"
        >
          <Minimize2 className="w-3.5 h-3.5" />
        </button>
      </div>

    </div>
  );
};

export default DockBar;
