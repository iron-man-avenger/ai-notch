import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  Circle, 
  Trash2, 
  Plus, 
  PhoneCall, 
  Sparkles, 
  Clock, 
  X,
  Copy,
  Check
} from 'lucide-react';
import type { TaskItem } from '../types';
import { api } from '../api';

interface TasksDrawerProps {
  tasks: TaskItem[];
  onClose: () => void;
  onRefresh: () => void;
  selectedTaskId?: number | null;
}

export const TasksDrawer: React.FC<TasksDrawerProps> = ({ tasks, onClose, onRefresh, selectedTaskId }) => {
  const [newTitle, setNewTitle] = useState('');
  const [newInterval, setNewInterval] = useState(30);
  const [editingTaskId, setEditingTaskId] = useState<number | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [isScanningTeams, setIsScanningTeams] = useState(false);

  const handleScanTeams = async () => {
    setIsScanningTeams(true);
    try {
      const res = await api.scanTeamsScreen('Dhiraj');
      if (res && res.success) {
        onRefresh();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsScanningTeams(false);
    }
  };

  useEffect(() => {
    if (selectedTaskId) {
      const timer = setTimeout(() => {
        const el = document.getElementById(`task-drawer-item-${selectedTaskId}`);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [selectedTaskId]);

  const handleUpdateInterval = async (id: number, intervalMins: number) => {
    try {
      await api.updateTaskInterval(id, intervalMins);
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleCopyTask = async (task: TaskItem) => {
    const text = `📌 ${task.title}${task.description ? `\n${task.description}` : ''}`;
    await api.copyToClipboard(text);
    setCopiedId(task.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleToggle = async (id: number) => {
    try {
      await api.toggleTask(id);
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteTask(id);
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm("Are you sure you want to delete all tasks?")) return;
    try {
      await api.deleteAllTasks();
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;

    try {
      await api.createTask({
        title: newTitle.trim(),
        reminder_interval_mins: newInterval,
        source: 'manual'
      });
      setNewTitle('');
      onRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const pendingTasks = [...tasks].filter(t => t.status === 'pending').sort((a, b) => (b.id || 0) - (a.id || 0));
  const completedTasks = [...tasks].filter(t => t.status === 'completed').sort((a, b) => (b.id || 0) - (a.id || 0));

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 flex justify-end">
      <div className="clean-white-panel w-full max-w-md h-full p-6 flex flex-col border-l border-neutral-200 shadow-2xl animate-in slide-in-from-right duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-neutral-200">
          <div>
            <h2 className="text-base font-bold text-black flex items-center gap-2">
              Action Items & Reminders
              <span className="text-xs px-2 py-0.5 rounded-full bg-neutral-100 text-black border border-neutral-200 font-bold">
                {pendingTasks.length} Pending
              </span>
            </h2>
            <p className="text-xs text-neutral-500">
              Meeting follow-ups will remind you until marked as done.
            </p>
          </div>
          <div className="flex items-center gap-2">
            {tasks.length > 0 && (
              <button
                onClick={handleDeleteAll}
                title="Delete all tasks"
                className="text-[11px] text-red-600 hover:text-red-700 hover:bg-red-50 border border-red-200 px-2.5 py-1 rounded-xl transition flex items-center gap-1 cursor-pointer font-medium"
              >
                <Trash2 className="w-3.5 h-3.5" /> Clear All
              </button>
            )}
            <button
              onClick={onClose}
              className="text-neutral-400 hover:text-black p-2 rounded-xl hover:bg-neutral-100 transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Quick Add Form */}
        <form onSubmit={handleAdd} className="my-4 space-y-2">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Add a new quick task or reminder..."
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="flex-1 bg-neutral-50 border border-neutral-300 rounded-xl px-3 py-2 text-xs text-black placeholder-neutral-400 focus:outline-none focus:border-black"
            />
            <button
              type="submit"
              disabled={!newTitle.trim()}
              className="p-2 bg-black hover:bg-neutral-800 text-white rounded-xl transition disabled:opacity-50 cursor-pointer shadow-sm"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-2 text-[10px] text-neutral-500">
            <span>Reminder interval:</span>
            {[2, 5, 15, 30, 60].map((m) => (
              <button
                type="button"
                key={m}
                onClick={() => setNewInterval(m)}
                className={`px-2 py-0.5 rounded cursor-pointer font-medium transition ${newInterval === m ? 'bg-black text-white' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}`}
              >
                {m}m
              </button>
            ))}
          </div>
        </form>
 
        {/* 1-Click Scan Teams for Tasks */}
        <div className="mb-3">
          <button
            type="button"
            onClick={handleScanTeams}
            disabled={isScanningTeams}
            className="w-full flex items-center justify-between px-3 py-2 rounded-xl bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-900 transition cursor-pointer text-xs font-semibold disabled:opacity-60 shadow-xs"
          >
            <div className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-blue-600 animate-pulse" />
              <span>{isScanningTeams ? 'Inspecting screen for tasks...' : "Scan Teams Screen for Dhiraj's Tasks"}</span>
            </div>
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-200 text-blue-800 font-bold uppercase tracking-wider">
              {isScanningTeams ? 'Scanning...' : '1-Click Scan'}
            </span>
          </button>
        </div>

        {/* Tasks List */}
        <div className="flex-1 overflow-y-auto space-y-3 pr-1">
          {pendingTasks.length === 0 && completedTasks.length === 0 && (
            <div className="text-center py-12 text-neutral-400 text-xs">
              No tasks logged yet. Tasks from Teams calls and EOD summaries will appear here!
            </div>
          )}

          {pendingTasks.map((t) => (
            <div
              key={t.id}
              id={`task-drawer-item-${t.id}`}
              className={`p-3.5 rounded-2xl bg-neutral-50 border transition space-y-2 group ${
                selectedTaskId === t.id
                  ? 'ring-2 ring-emerald-500 bg-emerald-50/70 border-emerald-300 shadow-md'
                  : 'border-neutral-200 hover:border-neutral-300'
              }`}
            >
              <div className="flex items-start gap-2.5">
                <button
                  type="button"
                  onClick={() => handleToggle(t.id)}
                  title="Mark as completed"
                  className="mt-0.5 text-neutral-400 hover:text-emerald-600 transition cursor-pointer flex-shrink-0"
                >
                  <Circle className="w-4 h-4 min-w-[16px] min-h-[16px] max-w-[16px] max-h-[16px] aspect-square flex-shrink-0" />
                </button>
                <div className="flex-1">
                  <h4 className="text-xs font-semibold text-black leading-tight">
                    {t.title}
                  </h4>
                  {t.description && (
                    <p className="text-[11px] text-neutral-600 mt-1 line-clamp-2">
                      {t.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                  <button
                    onClick={() => handleCopyTask(t)}
                    title="Copy task"
                    className="text-neutral-400 hover:text-black p-1 rounded hover:bg-neutral-200 transition"
                  >
                    {copiedId === t.id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                  <button
                    onClick={() => handleDelete(t.id)}
                    title="Delete task"
                    className="text-neutral-400 hover:text-red-600 p-1 rounded hover:bg-red-50 transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between text-[10px] text-neutral-500 pt-1 border-t border-neutral-200">
                <span className="flex items-center gap-1">
                  {t.source === 'teams_call' ? (
                    <span className="text-black flex items-center gap-1 font-semibold">
                      <PhoneCall className="w-3 h-3" /> Teams Call Follow-up
                    </span>
                  ) : t.source === 'eod_gemini' ? (
                    <span className="text-black flex items-center gap-1 font-semibold">
                      <Sparkles className="w-3 h-3" /> Gemini EOD
                    </span>
                  ) : (
                    <span>Manual Task</span>
                  )}
                </span>

                <div className="flex items-center gap-1.5">
                  <div className="relative">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingTaskId(editingTaskId === t.id ? null : t.id);
                      }}
                      title={`Remind every ${t.reminder_interval_mins || 30}m. Click to change.`}
                      className="flex items-center gap-1 text-neutral-600 hover:text-black hover:bg-neutral-200 px-1.5 py-0.5 rounded-md transition cursor-pointer text-[10px]"
                    >
                      <Clock className="w-3 h-3 text-amber-600" />
                      <span>Remind: <strong>{t.reminder_interval_mins || 30}m</strong></span>
                    </button>

                    {editingTaskId === t.id && (
                      <div 
                        className="absolute right-0 bottom-full mb-1 z-30 flex items-center gap-1 bg-white border border-neutral-300 rounded-xl p-1 shadow-xl animate-in fade-in zoom-in-95 duration-100"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {[2, 5, 15, 30, 60].map((mins) => (
                          <button
                            key={mins}
                            type="button"
                            onClick={() => {
                              handleUpdateInterval(t.id, mins);
                              setEditingTaskId(null);
                            }}
                            className={`px-1.5 py-0.5 text-[10px] rounded-md font-semibold transition cursor-pointer ${
                              (t.reminder_interval_mins || 30) === mins
                                ? 'bg-black text-white'
                                : 'text-neutral-600 hover:text-black hover:bg-neutral-100'
                            }`}
                          >
                            {mins}m
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* +5m Quick Extend */}
                  <button
                    type="button"
                    onClick={async () => {
                      await api.extendTask(t.id, 5);
                      onRefresh();
                    }}
                    title="Extend reminder by +5 minutes"
                    className="flex items-center gap-0.5 text-neutral-500 hover:text-black hover:bg-neutral-200 px-1.5 py-0.5 rounded-md transition cursor-pointer text-[10px] font-medium"
                  >
                    <Plus className="w-2.5 h-2.5" />
                    <span>5m</span>
                  </button>
                </div>
              </div>
            </div>
          ))}

          {/* Completed Section */}
          {completedTasks.length > 0 && (
            <div className="pt-4 border-t border-neutral-200">
              <h3 className="text-xs font-bold text-neutral-500 mb-2">
                Completed ({completedTasks.length})
              </h3>
              <div className="space-y-2">
                {completedTasks.map((t) => (
                  <div
                    key={t.id}
                    id={`task-drawer-item-${t.id}`}
                    className={`p-3 rounded-xl bg-neutral-100 border flex items-center justify-between transition ${
                      selectedTaskId === t.id
                        ? 'ring-2 ring-emerald-500 bg-emerald-50/70 border-emerald-300 opacity-100 shadow-md'
                        : 'border-neutral-200 opacity-60 hover:opacity-90'
                    }`}
                  >
                    <div className="flex items-center gap-2 flex-1 min-w-0 mr-2">
                      <button
                        type="button"
                        onClick={() => handleToggle(t.id)}
                        title="Mark as pending"
                        className="text-emerald-600 hover:text-neutral-500 transition cursor-pointer flex-shrink-0"
                      >
                        <CheckCircle2 className="w-4 h-4 min-w-[16px] min-h-[16px] max-w-[16px] max-h-[16px] aspect-square flex-shrink-0" />
                      </button>
                      <span className="text-xs line-through text-neutral-500 font-medium truncate">
                        {t.title}
                      </span>
                    </div>
                    {t.devops_id && (
                      <span className="text-[10px] text-black font-mono font-bold">
                        DevOps #{t.devops_id}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
};

export default TasksDrawer;
