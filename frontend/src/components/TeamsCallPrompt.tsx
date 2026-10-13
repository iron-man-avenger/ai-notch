import React, { useState } from 'react';
import { PhoneOff, Clock, CheckCircle2, X } from 'lucide-react';
import { api } from '../api';

interface TeamsCallPromptProps {
  subject: string;
  onClose: () => void;
  onTaskCreated: () => void;
}

export const TeamsCallPrompt: React.FC<TeamsCallPromptProps> = ({
  subject,
  onClose,
  onTaskCreated
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [intervalMins, setIntervalMins] = useState(30);
  const [saving, setSaving] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    setSaving(true);
    try {
      await api.createTask({
        title: title.trim(),
        description: description.trim() || `Follow-up action item from meeting: ${subject}`,
        source: 'teams_call',
        reminder_interval_mins: intervalMins
      });
      onTaskCreated();
      onClose();
    } catch (err) {
      console.error('Failed to create call follow-up task', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
      <div className="clean-white-panel relative w-full max-w-md rounded-3xl p-6 border border-neutral-300 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-black text-white flex items-center justify-center">
              <PhoneOff className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-black">Teams Meeting Ended</h3>
              <p className="text-xs text-neutral-500 truncate max-w-[260px]">
                {subject || "Microsoft Teams Call"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-black p-1 rounded-lg hover:bg-neutral-100 transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-neutral-600 mb-4">
          Did you get any action items or to-dos from this call? Add them here so you don't forget—I'll remind you until they're finished!
        </p>

        <form onSubmit={handleSave} className="space-y-3">
          <div>
            <label className="block text-[11px] font-semibold text-neutral-800 mb-1">
              Task / Action Item Title
            </label>
            <input
              type="text"
              required
              autoFocus
              placeholder="e.g., Send updated API documentation to John"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full bg-neutral-50 border border-neutral-300 rounded-xl px-3 py-2 text-xs text-black placeholder-neutral-400 focus:outline-none focus:border-black transition"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-neutral-800 mb-1">
              Notes or Meeting Context (Optional)
            </label>
            <textarea
              rows={2}
              placeholder="Key decisions, deadlines, or deliverables discussed..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-neutral-50 border border-neutral-300 rounded-xl px-3 py-2 text-xs text-black placeholder-neutral-400 focus:outline-none focus:border-black transition resize-none"
            />
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-neutral-800 mb-1 flex items-center gap-1">
              <Clock className="w-3 h-3 text-black" /> Reminder Frequency (until done)
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[15, 30, 60].map((mins) => (
                <button
                  type="button"
                  key={mins}
                  onClick={() => setIntervalMins(mins)}
                  className={`py-1.5 px-2 text-xs rounded-lg border font-semibold transition cursor-pointer ${
                    intervalMins === mins
                      ? 'bg-black text-white border-black'
                      : 'bg-neutral-50 text-neutral-600 border-neutral-200 hover:bg-neutral-100'
                  }`}
                >
                  Every {mins}m
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-2 rounded-xl text-xs text-neutral-500 hover:text-black hover:bg-neutral-100 transition cursor-pointer font-medium"
            >
              Skip
            </button>
            <button
              type="submit"
              disabled={saving || !title.trim()}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-black hover:bg-neutral-800 text-white transition disabled:opacity-50 cursor-pointer shadow-sm"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>{saving ? 'Saving...' : 'Set Reminder'}</span>
            </button>
          </div>
        </form>

      </div>
    </div>
  );
};

export default TeamsCallPrompt;
