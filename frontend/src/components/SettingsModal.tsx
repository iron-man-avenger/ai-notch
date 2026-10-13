import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Key, Zap, Cloud, Save, ExternalLink, X, Check } from 'lucide-react';
import { api } from '../api';
import type { AppSettings } from '../types';

interface SettingsModalProps {
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ onClose }) => {
  const [settings, setSettings] = useState<AppSettings>({
    gemini_api_key: '',
    groq_api_key: '',
    azure_org: '',
    azure_project: '',
    azure_pat: '',
    azure_item_type: 'Task'
  });
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [autostart, setAutostart] = useState(false);

  useEffect(() => {
    loadSettings();
    loadAutostart();
  }, []);

  const loadSettings = async () => {
    try {
      const data = await api.getSettings();
      setSettings(prev => ({ ...prev, ...data }));
    } catch (err) {
      console.error(err);
    }
  };

  const loadAutostart = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8765/api/settings/autostart').then(r => r.json());
      setAutostart(!!res.enabled);
    } catch (err) {
      console.error(err);
    }
  };

  const toggleAutostart = async () => {
    const next = !autostart;
    setAutostart(next);
    try {
      await fetch('http://127.0.0.1:8765/api/settings/autostart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: next })
      });
    } catch (err) {
      console.error(err);
      setAutostart(!next);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.updateSettings(settings);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
      <div className="clean-white-panel w-full max-w-lg rounded-3xl p-6 border border-neutral-300 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-neutral-200">
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-2xl bg-black text-white">
              <SettingsIcon className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-black">Assistant Settings</h2>
              <p className="text-xs text-neutral-500">Configure your Gemini API key & Azure DevOps connection.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-black p-2 rounded-xl hover:bg-neutral-100 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSave} className="py-4 space-y-4">
          
          {/* Gemini API Key */}
          <div className="space-y-1.5 bg-neutral-50 p-3.5 rounded-2xl border border-neutral-200">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-black flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-black" /> Google Gemini API Key
              </label>
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-[10px] text-black font-semibold hover:underline flex items-center gap-0.5"
              >
                Get Free Key <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
            <input
              type="password"
              placeholder="AIzaSy..."
              value={settings.gemini_api_key || ''}
              onChange={(e) => setSettings({ ...settings, gemini_api_key: e.target.value })}
              className="w-full bg-white border border-neutral-300 rounded-xl px-3 py-2 text-xs text-black placeholder-neutral-400 focus:outline-none focus:border-black font-mono"
            />
            <p className="text-[10px] text-neutral-500">
              Used for intelligent End-of-Day task extraction, agentic tool reasoning, and notch assistant chat.
            </p>
          </div>

          {/* Groq Cloud API Key (Whisper Turbo STT) */}
          <div className="space-y-1.5 bg-neutral-50 p-3.5 rounded-2xl border border-neutral-200">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-black flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-black" /> Groq Cloud API Key (Whisper Turbo STT)
              </label>
              <a
                href="https://console.groq.com/keys"
                target="_blank"
                rel="noreferrer"
                className="text-[10px] text-black font-semibold hover:underline flex items-center gap-0.5"
              >
                Get Free Key <ExternalLink className="w-2.5 h-2.5" />
              </a>
            </div>
            <input
              type="password"
              placeholder="gsk_..."
              value={settings.groq_api_key || ''}
              onChange={(e) => setSettings({ ...settings, groq_api_key: e.target.value })}
              className="w-full bg-white border border-neutral-300 rounded-xl px-3 py-2 text-xs text-black placeholder-neutral-400 focus:outline-none focus:border-black font-mono"
            />
            <p className="text-[10px] text-neutral-500">
              Powers ultra-fast (~150ms) speech-to-text recognition with Whisper Large v3 Turbo (Hindi, Hinglish & English).
            </p>
          </div>

          {/* Azure DevOps Settings */}
          <div className="space-y-3 bg-neutral-50 p-3.5 rounded-2xl border border-neutral-200">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-black flex items-center gap-1.5">
                <Cloud className="w-3.5 h-3.5 text-black" /> Azure DevOps Connection
              </label>
              <span className="text-[10px] text-neutral-500">REST API v7.1</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="block text-[10px] font-semibold text-neutral-700 mb-1">Organization Name</span>
                <input
                  type="text"
                  placeholder="e.g. MyCompanyOrg"
                  value={settings.azure_org || ''}
                  onChange={(e) => setSettings({ ...settings, azure_org: e.target.value })}
                  className="w-full bg-white border border-neutral-300 rounded-xl px-2.5 py-1.5 text-xs text-black placeholder-neutral-400 focus:outline-none focus:border-black"
                />
              </div>

              <div>
                <span className="block text-[10px] font-semibold text-neutral-700 mb-1">Project Name</span>
                <input
                  type="text"
                  placeholder="e.g. CorePlatform"
                  value={settings.azure_project || ''}
                  onChange={(e) => setSettings({ ...settings, azure_project: e.target.value })}
                  className="w-full bg-white border border-neutral-300 rounded-xl px-2.5 py-1.5 text-xs text-black placeholder-neutral-400 focus:outline-none focus:border-black"
                />
              </div>
            </div>

            <div>
              <span className="block text-[10px] font-semibold text-neutral-700 mb-1">Personal Access Token (PAT)</span>
              <input
                type="password"
                placeholder="Paste Azure DevOps PAT with Work Items (Read & Write) scope"
                value={settings.azure_pat || ''}
                onChange={(e) => setSettings({ ...settings, azure_pat: e.target.value })}
                className="w-full bg-white border border-neutral-300 rounded-xl px-3 py-1.5 text-xs text-black placeholder-neutral-400 focus:outline-none focus:border-black font-mono"
              />
            </div>

            <div>
              <span className="block text-[10px] font-semibold text-neutral-700 mb-1">Default Work Item Type</span>
              <select
                value={settings.azure_item_type || 'Task'}
                onChange={(e) => setSettings({ ...settings, azure_item_type: e.target.value })}
                className="w-full bg-white border border-neutral-300 rounded-xl px-3 py-1.5 text-xs text-black focus:outline-none focus:border-black"
              >
                <option value="Task">Task</option>
                <option value="User Story">User Story</option>
                <option value="Issue">Issue</option>
                <option value="Bug">Bug</option>
              </select>
            </div>
          </div>

          {/* Autostart on Boot */}
          <div className="flex items-center justify-between p-3.5 bg-neutral-50 rounded-2xl border border-neutral-200">
            <div>
              <span className="block text-xs font-semibold text-black">Start on Windows Boot</span>
              <span className="block text-[11px] text-neutral-500">Automatically awake Mochi silently when your laptop powers on</span>
            </div>
            <button
              type="button"
              onClick={toggleAutostart}
              className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${autostart ? 'bg-black' : 'bg-neutral-300'}`}
            >
              <span
                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out ${autostart ? 'translate-x-5' : 'translate-x-0'}`}
              />
            </button>
          </div>

          {/* Footer Save Button */}
          <div className="flex items-center justify-between pt-2">
            {savedSuccess ? (
              <span className="text-xs text-black flex items-center gap-1 font-semibold">
                <Check className="w-3.5 h-3.5" /> Settings saved!
              </span>
            ) : <span />}

            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs text-neutral-600 hover:text-black hover:bg-neutral-100 transition font-medium cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-1.5 px-5 py-2 rounded-xl text-xs font-semibold bg-black hover:bg-neutral-800 text-white shadow-sm transition disabled:opacity-50 cursor-pointer"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{saving ? 'Saving...' : 'Save Settings'}</span>
              </button>
            </div>
          </div>

        </form>

      </div>
    </div>
  );
};

export default SettingsModal;
