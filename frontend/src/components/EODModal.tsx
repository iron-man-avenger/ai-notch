import React, { useState, useEffect } from 'react';
import { 
  Sparkles, 
  Send, 
  Check, 
  ExternalLink, 
  X, 
  Clock, 
  Layers, 
  RefreshCw,
  Copy,
  CheckCheck
} from 'lucide-react';
import { api } from '../api';
import type { EODTaskProposal, AppSummary } from '../types';

interface EODModalProps {
  onClose: () => void;
  onTasksUpdated: () => void;
}

export const EODModal: React.FC<EODModalProps> = ({ onClose, onTasksUpdated }) => {
  const [appSummary, setAppSummary] = useState<AppSummary[]>([]);
  const [tasks, setTasks] = useState<EODTaskProposal[]>([]);
  const [loading, setLoading] = useState(false);
  const [pushing, setPushing] = useState(false);
  const [pushResults, setPushResults] = useState<any[] | null>(null);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);

  useEffect(() => {
    loadSummary();
    handleGenerate();
  }, []);

  const loadSummary = async () => {
    try {
      const summary = await api.getAppSummary();
      setAppSummary(summary);
    } catch (err) {
      console.error(err);
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    setPushResults(null);
    try {
      const res = await api.generateEOD();
      setTasks(res.tasks.map(t => ({ ...t, selected: true })));
    } catch (err) {
      console.error('Failed to generate EOD summary', err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSelect = (index: number) => {
    setTasks(prev => prev.map((t, i) => i === index ? { ...t, selected: !t.selected } : t));
  };

  const handleTitleChange = (index: number, val: string) => {
    setTasks(prev => prev.map((t, i) => i === index ? { ...t, title: val } : t));
  };

  const handleDescChange = (index: number, val: string) => {
    setTasks(prev => prev.map((t, i) => i === index ? { ...t, description: val } : t));
  };

  const handleCopyTask = async (task: EODTaskProposal, index: number) => {
    const text = `📌 Task: ${task.title} (${task.time_spent})\n${task.description}`;
    await api.copyToClipboard(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleCopyAll = async () => {
    const selected = tasks.filter(t => t.selected !== false);
    if (selected.length === 0) return;

    const report = selected.map((t, idx) => 
      `${idx + 1}. ${t.title} [Time: ${t.time_spent}]\n${t.description}`
    ).join('\n\n');

    await api.copyToClipboard(`📅 Daily Work Summary:\n\n${report}`);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2500);
  };

  const handlePushToDevOps = async () => {
    const selected = tasks.filter(t => t.selected !== false);
    if (selected.length === 0) return;

    setPushing(true);
    try {
      const res = await api.pushToDevOps(selected);
      setPushResults(res.results);
      onTasksUpdated();
    } catch (err) {
      console.error('Failed to push to Azure DevOps', err);
    } finally {
      setPushing(false);
    }
  };

  const formatSeconds = (sec: number) => {
    const hrs = Math.floor(sec / 3600);
    const mins = Math.floor((sec % 3600) / 60);
    if (hrs > 0) return `${hrs}h ${mins}m`;
    return `${mins}m`;
  };

  const totalTrackedSeconds = appSummary.reduce((acc, curr) => acc + curr.total_seconds, 0);

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
      <div className="clean-white-panel w-full max-w-2xl max-h-[88vh] rounded-3xl p-6 flex flex-col border border-neutral-300 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-neutral-200">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-2xl bg-black text-white">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-black flex items-center gap-2">
                Daily Work Summary & Tasks
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-neutral-100 text-black border border-neutral-200">
                  Gemini AI Active
                </span>
              </h2>
              <p className="text-xs text-neutral-500">
                Synthesizes your activity into clean work items with Title, Description, and Duration.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-black p-2 rounded-xl hover:bg-neutral-100 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4">
          
          {/* Today's Stats Ribbon */}
          <div className="bg-neutral-50 rounded-2xl p-3 border border-neutral-200 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1.5 text-xs text-neutral-700">
                <Clock className="w-4 h-4 text-black" />
                <span>Tracked Today: <strong className="text-black">{formatSeconds(totalTrackedSeconds)}</strong></span>
              </div>
              <div className="hidden sm:flex items-center gap-1.5 text-xs text-neutral-500">
                <Layers className="w-3.5 h-3.5 text-neutral-400" />
                <span>{appSummary.length} Apps active</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {tasks.length > 0 && (
                <button
                  onClick={handleCopyAll}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-neutral-100 text-black text-xs font-semibold border border-neutral-300 transition cursor-pointer shadow-sm"
                >
                  {copiedAll ? (
                    <>
                      <CheckCheck className="w-3.5 h-3.5 text-black" />
                      <span>Copied All!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 text-neutral-600" />
                      <span>Copy All as Summary</span>
                    </>
                  )}
                </button>
              )}

              <button
                type="button"
                onClick={handleGenerate}
                disabled={loading}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-black hover:bg-neutral-800 text-white text-xs font-semibold transition cursor-pointer disabled:opacity-50 shadow-sm"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Analyzing with Gemini...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{tasks.length > 0 ? "Re-generate" : "Generate Tasks"}</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* App breakdown chips */}
          <div className="flex flex-wrap gap-1.5">
            {appSummary.map((item) => (
              <span
                key={item.app_name}
                className="text-[11px] px-2.5 py-1 rounded-lg bg-neutral-100 text-neutral-700 border border-neutral-200 flex items-center gap-1.5"
              >
                <span className="font-semibold text-black">{item.app_name}:</span>
                <span className="text-neutral-600 font-mono">{formatSeconds(item.total_seconds)}</span>
              </span>
            ))}
          </div>

          {/* DevOps Push Results Banner */}
          {pushResults && (
            <div className="p-3.5 rounded-2xl bg-neutral-100 border border-neutral-300 text-black text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-black">
                <Check className="w-4 h-4" />
                <span>Tasks Processed:</span>
              </div>
              <ul className="space-y-1 pl-5 list-disc text-[11px] text-neutral-700">
                {pushResults.map((r, i) => (
                  <li key={i}>
                    {r.title} — {r.message}
                    {r.url && (
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-2 inline-flex items-center gap-0.5 text-black font-semibold hover:underline"
                      >
                        View in Azure DevOps <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tasks List */}
          {tasks.length === 0 && !loading && (
            <div className="text-center py-10 text-neutral-400 space-y-2">
              <Sparkles className="w-8 h-8 mx-auto text-neutral-300" />
              <p className="text-sm">Click "Generate Tasks" above to have Gemini synthesize today's window history into tasks!</p>
            </div>
          )}

          {tasks.map((task, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-2xl border transition-all ${
                task.selected !== false
                  ? 'bg-white border-neutral-300 shadow-sm'
                  : 'bg-neutral-50 border-neutral-200 opacity-60'
              }`}
            >
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  checked={task.selected !== false}
                  onChange={() => handleToggleSelect(idx)}
                  className="mt-1.5 h-4 w-4 rounded border-neutral-300 text-black focus:ring-black cursor-pointer accent-black"
                />

                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <input
                      type="text"
                      value={task.title}
                      onChange={(e) => handleTitleChange(idx, e.target.value)}
                      className="w-full bg-neutral-50 border border-neutral-200 rounded-xl px-2.5 py-1 text-xs font-semibold text-black focus:outline-none focus:border-black"
                    />
                    
                    {/* Time Duration Badge & Copy Button */}
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <span className="text-[11px] font-mono text-black bg-neutral-100 px-2 py-0.5 rounded-md border border-neutral-200 flex items-center gap-1 font-semibold">
                        <Clock className="w-3 h-3 text-black" />
                        {task.time_spent}
                      </span>

                      <button
                        onClick={() => handleCopyTask(task, idx)}
                        title="Copy Task (Title, Description & Time)"
                        className="p-1 rounded-md bg-neutral-100 hover:bg-neutral-200 text-black border border-neutral-200 transition cursor-pointer"
                      >
                        {copiedIndex === idx ? (
                          <Check className="w-3.5 h-3.5 text-black" />
                        ) : (
                          <Copy className="w-3.5 h-3.5 text-neutral-600" />
                        )}
                      </button>
                    </div>
                  </div>

                  <textarea
                    rows={3}
                    value={task.description}
                    onChange={(e) => handleDescChange(idx, e.target.value)}
                    className="w-full bg-neutral-50 border border-neutral-200 rounded-xl px-2.5 py-1.5 text-xs text-neutral-800 focus:outline-none focus:border-black resize-none font-sans"
                  />

                  {task.tags && task.tags.length > 0 && (
                    <div className="flex gap-1">
                      {task.tags.map((t) => (
                        <span key={t} className="text-[10px] px-2 py-0.5 rounded-md bg-neutral-100 text-neutral-600 border border-neutral-200 font-medium">
                          #{t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-neutral-200 flex items-center justify-between">
          <div className="text-xs text-neutral-500">
            {tasks.filter(t => t.selected !== false).length} of {tasks.length} tasks selected
          </div>

          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs text-neutral-600 hover:text-black hover:bg-neutral-100 transition cursor-pointer font-medium"
            >
              Close
            </button>
            
            <button
              onClick={handlePushToDevOps}
              disabled={pushing || tasks.filter(t => t.selected !== false).length === 0}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-neutral-100 hover:bg-neutral-200 text-black border border-neutral-300 transition disabled:opacity-50 cursor-pointer shadow-sm"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{pushing ? 'Processing...' : 'Push to Azure DevOps (Optional)'}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

export default EODModal;
