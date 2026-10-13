import React, { useState, useRef, useEffect } from 'react';
import { 
  ChevronDown, 
  ChevronLeft,
  Sparkles, 
  Check, 
  Clock, 
  Trash2,
  ExternalLink,
  Loader2,
  Mic,
  Eye,
  Languages,
  Volume2,
  FileText,
  Plus
} from 'lucide-react';
import { ThinkingOrb } from 'thinking-orbs';
import { Mochi } from './Mochi';
import { WardrobePicker } from './WardrobePicker';
import { MarkdownMessage } from './MarkdownMessage';
import type { ActivityInfo, TaskItem, VisionResult, ReplySuggestion } from '../types';
import { api } from '../api';
import { sounds } from '../utils/sound';
import { voice } from '../utils/voice';
import { ICONS } from '../coucou/views/icons';
import { resolveOutfit, seasonalOutfit, OUTFIT_LABELS, type OutfitSelection, type Outfit } from '../coucou/mochi/wardrobe';

export const CoucouIcon: React.FC<{ path: string; size?: number; className?: string }> = ({ path, size = 14, className = '' }) => (
  <svg viewBox="0 0 24 24" width={size} height={size} fill="currentColor" className={`inline-block ${className}`}>
    <path d={path} />
  </svg>
);

interface CoucouIslandProps {
  activity: ActivityInfo;
  inMeeting: boolean;
  meetingSubject?: string;
  pendingTasksCount: number;
  tasks: TaskItem[];
  onTasksRefresh: () => void;
  taskProposal?: {
    title: string;
    sender?: string;
    description?: string;
    priority?: string;
  } | null;
  onAcceptProposal?: () => void;
  onDismissProposal?: () => void;
  activeReminder?: {
    task: TaskItem;
    title: string;
    message?: string;
  } | null;
  onDismissReminder?: () => void;
  isExpanded: boolean;
  onExpand: () => void;
  onCollapse: () => void;
  onOpenEOD: () => void;
  onOpenTasks: () => void;
  onOpenSettings: () => void;
  onSimulateCall: () => void;
  currentOutfit?: OutfitSelection;
  onSelectOutfit?: (outfit: OutfitSelection) => void;
  onHeightChange?: (height: number) => void;
  targetTab?: 'overview' | 'chat' | 'tasks' | 'wardrobe' | null;
  visionResult?: VisionResult | null;
  replySuggestion?: ReplySuggestion | null;
  isAnalyzingScreen?: boolean;
  onDismissVision?: () => void;
  onDismissReply?: () => void;
  onTriggerVision?: () => void;
  latestVoiceData?: {
    userText?: string;
    replyText?: string;
    action?: string;
    detailedAnswer?: string;
    searchResults?: any[];
  } | null;
  activeResearch?: {
    status: 'searching' | 'completed';
    query: string;
    userText?: string;
    detailedAnswer?: string;
    spokenReply?: string;
    results?: any[];
  } | null;
  onClearResearch?: () => void;
  onClearVoiceData?: () => void;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'mochi';
  text: string;
  timestamp: Date;
  isResearch?: boolean;
  isLoading?: boolean;
  researchQuery?: string;
  sources?: Array<{ title: string; link: string; snippet?: string }>;
  citations?: string[];
}

export const CoucouIsland: React.FC<CoucouIslandProps> = ({
  activity,
  inMeeting,
  meetingSubject,
  pendingTasksCount,
  tasks,
  onTasksRefresh,
  taskProposal,
  onAcceptProposal,
  onDismissProposal,
  activeReminder,
  onDismissReminder,
  isExpanded,
  onExpand,
  onCollapse,
  onOpenEOD,
  onOpenTasks,
  onOpenSettings,
  onSimulateCall: _onSimulateCall,
  currentOutfit = 'auto',
  onSelectOutfit,
  onHeightChange,
  targetTab,
  visionResult,
  replySuggestion,
  isAnalyzingScreen,
  onDismissVision,
  onDismissReply,
  onTriggerVision,
  latestVoiceData,
  activeResearch,
  onClearResearch,
  onClearVoiceData,
}) => {
  // Navigation tabs: overview, chat, tasks, wardrobe
  const [activeTab, setActiveTab] = useState<'overview' | 'chat' | 'tasks' | 'wardrobe'>('overview');
  const [showVisionHub, setShowVisionHub] = useState(false);
  const [pointerCountingDown, setPointerCountingDown] = useState(false);
  const [visionScope, setVisionScope] = useState<'fullscreen' | 'pointer'>('fullscreen');
  const [customVisionPrompt, setCustomVisionPrompt] = useState('');

  const executeVisionAction = async (focus: string, defaultQuery: string) => {
    const query = customVisionPrompt.trim() || defaultQuery;
    setShowVisionHub(false);
    setCustomVisionPrompt('');

    if (visionScope === 'pointer') {
      setPointerCountingDown(true);
      if (onTriggerVision) onTriggerVision();
      sounds.playClick();
      try {
        await api.analyzeScreen(query, focus, 'pointer', 2.0);
      } finally {
        setPointerCountingDown(false);
      }
    } else {
      if (onTriggerVision) onTriggerVision();
      sounds.playClick();
      await api.analyzeScreen(query, focus, 'fullscreen', 0.0);
    }
  };

  useEffect(() => {
    if (targetTab) {
      setActiveTab(targetTab);
    }
  }, [targetTab]);
  const [copied, setCopied] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);

  // Real-Time Voice AI & J.A.R.V.I.S. Ambient hands-free state
  const [jarvisHandsFree, setJarvisHandsFree] = useState(voice.jarvisMode);
  const [jarvisLanguage, setJarvisLanguage] = useState(voice.currentLanguage);
  const [voiceActive, setVoiceActive] = useState(voice.jarvisMode);
  const [voiceMode, setVoiceMode] = useState<'idle' | 'listening' | 'thinking' | 'speaking'>('idle');
  const [voiceInterimText, setVoiceInterimText] = useState('');
  const [voiceReplyText, setVoiceReplyText] = useState('');
  const [isChatVoiceRecording, setIsChatVoiceRecording] = useState(false);

  // Effective display text combining native Windows Voice + Web Voice
  const displayVoiceUser = latestVoiceData?.userText || '';
  const displayVoiceReply = latestVoiceData?.replyText || voiceReplyText;
  const isResearching = activeResearch?.status === 'searching';

  // Coucou Responsive Content & Processing State
  const isProcessing = Boolean(isAnalyzingScreen || isResearching || voiceMode === 'listening' || voiceMode === 'thinking' || voiceMode === 'speaking');
  const hasActiveContent = Boolean(showVisionHub || pointerCountingDown || isProcessing || replySuggestion || visionResult || activeReminder || taskProposal || voiceInterimText || displayVoiceReply || activeResearch);

  // Wardrobe temporary hover preview
  const [previewOutfit, setPreviewOutfit] = useState<Outfit | null>(null);
  const [hoveredSelection, setHoveredSelection] = useState<OutfitSelection | null>(null);

  // Tasks Tab state
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskInterval, setNewTaskInterval] = useState<number>(30);
  const [editingTaskIntervalId, setEditingTaskIntervalId] = useState<number | null>(null);
  const [taskFilter, setTaskFilter] = useState<'all' | 'pending' | 'completed'>('all');
  const [creatingTask, setCreatingTask] = useState(false);

  // Gemini AI chat inside Island (Full conversation history with research tracking)
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'mochi',
      text: "Hi! I am Mochi, your Windows AI assistant. Ask me anything, or ask me to research topics on the web!",
      timestamp: new Date()
    }
  ]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // ── Coucou File Drop Experience State ──────────────────────
  const [dragOver, setDragOver] = useState(false);
  const [dragState, setDragState] = useState<'idle' | 'dropping' | 'uploading' | 'choose'>('idle');
  const [droppedFile, setDroppedFile] = useState<{ name: string; size: number; content: string } | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [attachedFile, setAttachedFile] = useState<{ name: string; size: number; content: string } | null>(null);

  // ── Coucou Model Picker State ──────────────────────────────
  const [selectedProvider, setSelectedProvider] = useState<'google' | 'groq' | 'openai' | 'anthropic' | 'local'>('google');
  const [selectedModel, setSelectedModel] = useState<string>('gemini-3.5-flash-lite');
  const [showModelPicker, setShowModelPicker] = useState(false);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (activeTab === 'chat') {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, activeTab, chatLoading]);

  // Synchronize Live Web Research into Chat conversation thread
  useEffect(() => {
    if (!activeResearch) return;

    if (activeResearch.status === 'searching') {
      const q = activeResearch.query;
      const userText = activeResearch.userText || `Research ${q} on web`;
      setChatMessages(prev => {
        const exists = prev.some(m => m.id === `res-${q}`);
        if (exists) return prev;
        return [
          ...prev,
          {
            id: `u-${Date.now()}`,
            sender: 'user',
            text: userText,
            timestamp: new Date()
          },
          {
            id: `res-${q}`,
            sender: 'mochi',
            text: `Searching Google & the web for "${q}"...`,
            isResearch: true,
            isLoading: true,
            researchQuery: q,
            timestamp: new Date()
          }
        ];
      });
    } else if (activeResearch.status === 'completed') {
      const q = activeResearch.query;
      setChatMessages(prev => {
        const found = prev.some(m => m.id === `res-${q}`);
        if (found) {
          return prev.map(m => {
            if (m.id === `res-${q}`) {
              return {
                ...m,
                isLoading: false,
                text: activeResearch.detailedAnswer || activeResearch.spokenReply || "Here is what I found on the web.",
                sources: activeResearch.results || []
              };
            }
            return m;
          });
        }
        return [
          ...prev,
          {
            id: `u-${Date.now()}`,
            sender: 'user',
            text: activeResearch.userText || `Research ${q} on web`,
            timestamp: new Date()
          },
          {
            id: `res-${q}`,
            sender: 'mochi',
            text: activeResearch.detailedAnswer || activeResearch.spokenReply || "Here is what I found on the web.",
            isResearch: true,
            isLoading: false,
            researchQuery: q,
            sources: activeResearch.results || [],
            timestamp: new Date()
          }
        ];
      });
    }
  }, [activeResearch]);

  // Synchronize general voice interactions into Chat thread
  useEffect(() => {
    if (!latestVoiceData || !latestVoiceData.userText || !latestVoiceData.replyText) return;
    if (activeResearch && activeResearch.query && latestVoiceData.userText.toLowerCase().includes(activeResearch.query.toLowerCase())) return;

    setChatMessages(prev => {
      const lastMsg = prev[prev.length - 1];
      if (lastMsg && (lastMsg.text === latestVoiceData.replyText || lastMsg.text === latestVoiceData.detailedAnswer)) return prev;
      return [
        ...prev,
        {
          id: `u-voice-${Date.now()}`,
          sender: 'user',
          text: latestVoiceData.userText || '',
          timestamp: new Date()
        },
        {
          id: `b-voice-${Date.now()}`,
          sender: 'mochi',
          text: latestVoiceData.detailedAnswer || latestVoiceData.replyText || '',
          sources: latestVoiceData.searchResults || [],
          timestamp: new Date()
        }
      ];
    });
  }, [latestVoiceData]);

  // Mouse hover debounce timers
  const enterTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const leaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Calculate dynamic expanded height matching Coucou's exact compact architecture:
  // - Upload / Drag Drop: 176px (Coucou exact)
  // - Overview Idle: 175px
  // - Rephrase Draft: 270px - 310px (generous reading height)
  // - Screen Vision: 290px
  // - Active Reminder: 215px
  // - Chat: 300px - 360px
  // - Tasks: 280px
  // - Wardrobe: 220px
  const expandedHeight = (
    dragOver || dragState !== 'idle' ? 190 :
    activeTab === 'chat' ? (chatMessages.length > 2 ? 360 : 300) :
    activeTab === 'tasks' ? 280 :
    activeTab === 'wardrobe' ? 220 :
    showVisionHub ? 340 :
    pointerCountingDown ? 230 :
    isAnalyzingScreen ? 220 :
    visionResult ? 340 :
    replySuggestion ? (replySuggestion.reply.length > 120 ? 310 : 270) :
    displayVoiceReply || voiceMode === 'speaking' ? 260 :
    activeReminder ? 295 :
    hasActiveContent ? 250 :
    175
  );

  // Notify parent of height changes to synchronize native transparent window
  useEffect(() => {
    if (isExpanded) {
      onHeightChange?.(expandedHeight);
    } else {
      onHeightChange?.(36);
    }
  }, [isExpanded, expandedHeight, onHeightChange]);

  // If a new task proposal arrives, automatically switch to tasks tab if user clicks or opens
  useEffect(() => {
    if (taskProposal && isExpanded) {
      // Keep user in overview or let them see the task alert pill
    }
  }, [taskProposal]);

  // ── J.A.R.V.I.S. Ambient Continuous Voice Connection ─────────────────────────
  useEffect(() => {
    // 1. Sync voice status with Mochi expression & UI indicator
    const unsubStatus = voice.onStatusChange((status) => {
      if (status === 'listening') setVoiceMode('listening');
      else if (status === 'thinking') setVoiceMode('thinking');
      else if (status === 'speaking') setVoiceMode('speaking');
      else if (status === 'standby') setVoiceMode('idle');
      else if (status === 'off') setVoiceMode('idle');
    });

    // 2. Hands-Free Query Trigger (User speaks "Mochi..." or query in Hindi/English hands-free)
    const unsubQuery = voice.onQueryDetected(async (query, rawTranscript) => {
      setVoiceInterimText(rawTranscript);
      setVoiceMode('thinking');
      sounds.playClick();
      if (!isExpanded) onExpand();

      try {
        const res = await api.processVoice(query);
        setVoiceReplyText(res.reply);
        setVoiceMode('speaking');
        voice.speak(res.reply, () => {
          setVoiceMode('idle');
        });
        if (res.action === 'create_task') {
          onTasksRefresh();
          sounds.playComplete();
        }
      } catch {
        setVoiceMode('idle');
        sounds.playError();
      }
    });

    // 3. Auto-start on application mount! Mochi is alive immediately like JARVIS!
    if (voice.jarvisMode) {
      voice.startJarvis();
    }

    return () => {
      unsubStatus();
      unsubQuery();
    };
  }, [isExpanded, onExpand, onTasksRefresh]);

  const handleMouseEnter = () => {
    if (leaveTimerRef.current) {
      clearTimeout(leaveTimerRef.current);
      leaveTimerRef.current = null;
    }
    if (!isExpanded) {
      enterTimerRef.current = setTimeout(() => {
        onExpand();
        sounds.playExpand();
      }, 50);
    }
  };

  const handleMouseLeave = () => {
    if (enterTimerRef.current) {
      clearTimeout(enterTimerRef.current);
      enterTimerRef.current = null;
    }
    if (isExpanded) {
      leaveTimerRef.current = setTimeout(() => {
        onCollapse();
        sounds.playCollapse();
      }, 5000); // 5 second grace period when cursor leaves notch
    }
  };

  const handleImmediateCollapse = () => {
    if (enterTimerRef.current) clearTimeout(enterTimerRef.current);
    if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current);
    setShowVisionHub(false);
    onCollapse();
    sounds.playCollapse();
  };

  const dragStartRef = useRef<{ x: number; y: number } | null>(null);
  const isDraggingRef = useRef(false);

  // Smooth dragging handler that translates the native Windows desktop dock
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;

    // Do NOT drag when clicking buttons, inputs, links or Mochi canvas
    const target = e.target as HTMLElement;
    if (target.closest('button, input, textarea, a, select, [role="button"], canvas')) {
      return;
    }

    dragStartRef.current = { x: e.screenX, y: e.screenY };
    isDraggingRef.current = false;

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!dragStartRef.current) return;
      const dx = moveEvent.screenX - dragStartRef.current.x;
      const dy = moveEvent.screenY - dragStartRef.current.y;

      if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
        isDraggingRef.current = true;
      }

      if (dx !== 0 || dy !== 0) {
        api.moveWindow(dx, dy);
        dragStartRef.current = { x: moveEvent.screenX, y: moveEvent.screenY };
      }
    };

    const handleMouseUp = () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      dragStartRef.current = null;
      setTimeout(() => {
        isDraggingRef.current = false;
      }, 80);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  };

  const handleDoubleClickSnap = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest('button, input, textarea, a, select, canvas')) return;
    api.snapTop();
    sounds.playClick();
  };

  const toggleSound = () => {
    const next = !soundEnabled;
    setSoundEnabled(next);
    sounds.enabled = next;
    voice.enabled = next;
    sounds.playToggle(next);
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

  const formatTimeNumbers = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    if (mins >= 60) {
      const hrs = Math.floor(mins / 60);
      const remMins = mins % 60;
      return `${hrs}h ${remMins}m`;
    }
    if (mins > 0) return `${mins}m`;
    return `${seconds || 0}s`;
  };

  const formatBytes = (bytes: number) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const MODEL_PROVIDERS = [
    {
      id: 'google',
      name: 'Google',
      accent: '#22d3ee',
      models: [
        { id: 'gemini-3.5-flash-lite', label: 'gemini-3.5-flash-lite (1s ⚡)' },
        { id: 'gemini-3.5-flash', label: 'gemini-3.5-flash (Smart & Fast)' },
        { id: 'gemini-3.1-flash-lite', label: 'gemini-3.1-flash-lite' },
        { id: 'gemini-flash-latest', label: 'gemini-flash-latest' },
      ]
    },
    {
      id: 'groq',
      name: 'Groq',
      accent: '#f97316',
      models: [
        { id: 'openai/gpt-oss-20b', label: 'Groq GPT-OSS 20B (0.6s ⚡)' },
        { id: 'qwen/qwen3.8-27b', label: 'Groq Qwen 27B' },
      ]
    },
    {
      id: 'openai',
      name: 'OpenAI',
      accent: '#10a37f',
      models: [
        { id: 'gpt-4o-mini', label: 'gpt-4o-mini' },
        { id: 'gpt-4o', label: 'gpt-4o' }
      ]
    },
    {
      id: 'anthropic',
      name: 'Anthropic',
      accent: '#d97706',
      models: [
        { id: 'claude-3-5-sonnet', label: 'claude-3-5-sonnet' }
      ]
    },
    {
      id: 'local',
      name: 'Local',
      accent: '#8b5cf6',
      models: [
        { id: 'ollama', label: 'Ollama / Local LLM' }
      ]
    }
  ];


  // ── Real-Time Voice & JARVIS Controls ─────────────────────────────────────
  const handleToggleVoice = async () => {
    sounds.playClick();
    const next = !voice.jarvisMode;
    voice.setJarvisMode(next);
    setJarvisHandsFree(next);
    setVoiceActive(next);
    try {
      await fetch('http://127.0.0.1:8765/api/voice/toggle-listening', { method: 'POST' });
    } catch {}
    if (next) {
      voice.speak("Listening mode active.");
    }
  };

  // On-demand Voice Query from Chat only (starts on click only!)
  const handleToggleChatVoice = async () => {
    if (isChatVoiceRecording) {
      setIsChatVoiceRecording(false);
      return;
    }

    sounds.playClick();
    setIsChatVoiceRecording(true);

    try {
      const res = await api.listenOnce();
      if (res && res.success && res.text) {
        sounds.playComplete();
        const spoken = res.text.trim();
        setChatInput(spoken);
        handleSendChat(spoken);
      } else if (res && res.error && res.error !== "No speech detected.") {
        console.warn("[Voice listenOnce]", res.error);
      }
    } catch (err) {
      console.warn("[Voice listenOnce Error]", err);
    } finally {
      setIsChatVoiceRecording(false);
    }
  };

  const handleToggleLanguage = () => {
    sounds.playClick();
    const nextLang = jarvisLanguage === 'hi-IN' ? 'en-US' : 'hi-IN';
    setJarvisLanguage(nextLang);
    voice.setLanguage(nextLang);
    sounds.playToggle(true);
  };

  // ── Coucou File Drag & Drop Handlers ───────────────────────
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
    if (!isExpanded) {
      onExpand();
      sounds.playExpand();
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget as Node)) return;
    setDragOver(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    sounds.playToggle(true);
    setDragState('uploading');
    setUploadProgress(0.15);

    let textContent = '';
    try {
      textContent = await file.text();
    } catch {
      textContent = `[File: ${file.name}, size: ${file.size} bytes]`;
    }

    setDroppedFile({
      name: file.name,
      size: file.size,
      content: textContent
    });

    let p = 0.15;
    const interval = setInterval(() => {
      p += 0.28;
      if (p >= 1.0) {
        clearInterval(interval);
        setUploadProgress(1.0);
        sounds.playComplete();
        setTimeout(() => {
          setDragState('choose');
        }, 250);
      } else {
        setUploadProgress(Math.min(0.95, p));
        sounds.playClick();
      }
    }, 120);
  };

  const handleChooseAskQuestion = () => {
    if (droppedFile) {
      setAttachedFile(droppedFile);
      setDragState('idle');
      setActiveTab('chat');
      sounds.playClick();
    }
  };

  const handleCancelDrop = () => {
    setDragState('idle');
    setDroppedFile(null);
    setUploadProgress(0);
    sounds.playCollapse();
  };

  // Chat Submission handler (Conversational with Live Web Research progress & file attachment)
  const handleSendChat = async (queryText?: string) => {
    const q = (queryText || chatInput).trim();
    if (!q || chatLoading) return;

    sounds.playClick();
    setChatLoading(true);
    if (!queryText) setChatInput('');

    const fileToSend = attachedFile;
    // Detach file chip after sending
    setAttachedFile(null);

    const userMsgId = `u-${Date.now()}`;
    const botMsgId = `b-${Date.now()}`;
    const isResearchQuery = /(?:research|search|google|find|look up)\b/i.test(q);
    const userDisplayText = fileToSend ? `[Attached: ${fileToSend.name}]\n${q}` : q;

    setChatMessages(prev => [
      ...prev,
      {
        id: userMsgId,
        sender: 'user',
        text: userDisplayText,
        timestamp: new Date()
      },
      {
        id: botMsgId,
        sender: 'mochi',
        text: isResearchQuery ? `Searching Google & the web for "${q}"...` : (fileToSend ? `Analyzing ${fileToSend.name}...` : 'Thinking...'),
        isLoading: true,
        isResearch: isResearchQuery,
        researchQuery: q,
        timestamp: new Date()
      }
    ]);

    try {
      const res = await api.askChat(q, fileToSend, selectedModel);
      setChatMessages(prev => prev.map(m => {
        if (m.id === botMsgId) {
          return {
            ...m,
            text: res.reply || 'No response received.',
            isLoading: false,
            sources: res.sources || [],
            citations: res.citations || []
          };
        }
        return m;
      }));
      sounds.playComplete();
      sounds.playComplete();
    } catch {
      setChatMessages(prev => prev.map(m => {
        if (m.id === botMsgId) {
          return {
            ...m,
            text: 'Sorry, I had trouble reaching the AI assistant. Please check your network or API key.',
            isLoading: false
          };
        }
        return m;
      }));
      sounds.playError();
    } finally {
      setChatLoading(false);
    }
  };

  // Quick Task Creation inside notch
  const handleCreateTask = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!newTaskTitle.trim() || creatingTask) return;

    setCreatingTask(true);
    sounds.playClick();
    try {
      await api.createTask({
        title: newTaskTitle.trim(),
        reminder_interval_mins: newTaskInterval,
        source: 'island_quick'
      });
      setNewTaskTitle('');
      onTasksRefresh();
      sounds.playComplete();
    } catch (err) {
      console.error(err);
      sounds.playError();
    } finally {
      setCreatingTask(false);
    }
  };

  const handleUpdateTaskInterval = async (taskId: number, intervalMins: number) => {
    sounds.playClick();
    try {
      await api.updateTaskInterval(taskId, intervalMins);
      onTasksRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleTask = async (taskId: number) => {
    sounds.playClick();
    try {
      await api.toggleTask(taskId);
      onTasksRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteTask = async (taskId: number) => {
    sounds.playClick();
    try {
      await api.deleteTask(taskId);
      onTasksRefresh();
    } catch (err) {
      console.error(err);
    }
  };

  // Mochi right-click handler: Toggles Wardrobe view!
  const handleMochiContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!isExpanded) onExpand();
    setActiveTab(prev => prev === 'wardrobe' ? 'overview' : 'wardrobe');
    sounds.playClick();
  };

  // Active outfit resolution: Preview overrides saved choice while hovering
  const activeOutfit: Outfit = previewOutfit ?? resolveOutfit(currentOutfit, new Date());

  const filteredTasks = tasks.filter(t => {
    if (taskFilter === 'pending') return t.status === 'pending';
    if (taskFilter === 'completed') return t.status === 'completed';
    return true;
  });

  const compactWidth = 288;
  const expandedWidth = 640;

  return (
    <div
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseDown={handleMouseDown}
      onDoubleClick={handleDoubleClickSnap}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative select-none flex flex-col justify-start bg-black backdrop-blur-2xl shadow-[0_16px_36px_rgba(0,0,0,0.75)] transition-all ease-[cubic-bezier(0.16,1,0.3,1)] ${
        !isExpanded ? 'cursor-grab active:cursor-grabbing hover:bg-black/95' : ''
      }`}
      style={{
        width: isExpanded ? expandedWidth : compactWidth,
        height: isExpanded ? expandedHeight : 34,
        borderTopLeftRadius: 0,
        borderTopRightRadius: 0,
        borderBottomLeftRadius: isExpanded ? 22 : 14,
        borderBottomRightRadius: isExpanded ? 22 : 14,
        borderTop: 'none',
        borderLeft: '1px solid rgba(255, 255, 255, 0.12)',
        borderRight: '1px solid rgba(255, 255, 255, 0.12)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
        transformOrigin: 'top center',
        transitionProperty: 'width, height, border-radius, background',
        transitionDuration: '300ms',
        transitionTimingFunction: 'cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Coucou Authentic Reverse Notch Fillet Ears (glued to screen bezel) */}
      <div
        className="absolute top-0 pointer-events-none"
        style={{
          left: -14,
          width: 14,
          height: 14,
          background: 'radial-gradient(circle at 0 100%, transparent 13.5px, #000 14px)',
        }}
      />
      <div
        className="absolute top-0 pointer-events-none"
        style={{
          right: -14,
          width: 14,
          height: 14,
          background: 'radial-gradient(circle at 100% 100%, transparent 13.5px, #000 14px)',
        }}
      />

      {/* ─────────────────────────────────────────────────────────────
          ROW 1: COMPACT NOTCH / HEADER BAR (Height: 34px-36px)
          ───────────────────────────────────────────────────────────── */}
      <div 
        className={`w-full h-[34px] flex items-center justify-between px-2.5 flex-shrink-0 ${
          !isExpanded ? 'cursor-grab active:cursor-grabbing' : ''
        }`}
        onClick={() => {
          if (isDraggingRef.current) return;
          if (!isExpanded) {
            onExpand();
            sounds.playExpand();
          }
        }}
      >
        {!isExpanded ? (
          /* COMPACT VIEW (Coucou Dynamic Notch Pill) */
          <div className="w-full h-full flex items-center justify-between">
            {isProcessing ? (
              /* Live Processing Ticker in Compact Notch */
              <div className="flex items-center gap-1.5 overflow-hidden flex-1 mr-1 px-1">
                <Mochi
                  state={isResearching ? "searching" : isAnalyzingScreen ? "thinking" : "working"}
                  outfit={activeOutfit}
                  size={20}
                  badge="working"
                />
                <span className="shimmer text-[11px] font-semibold truncate flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping inline-block" />
                  <span>
                    {isAnalyzingScreen ? "Inspecting screen..." : isResearching ? `Searching: ${activeResearch?.query || "web"}...` : "AI working..."}
                  </span>
                </span>
              </div>
            ) : (
              /* Left: Mini Mochi with outfit + App name + JARVIS indicator */
              <div className="flex items-center gap-1.5 overflow-hidden flex-1 mr-1">
                <Mochi
                  state={inMeeting ? 'meeting' : activity.app !== 'Idle' ? 'working' : 'idle'}
                  outfit={activeOutfit}
                  size={20}
                  badge={inMeeting ? 'working' : 'dots'}
                  onContextMenu={handleMochiContextMenu}
                />
                <span className="text-[11px] font-semibold text-neutral-100 truncate max-w-[110px]">
                  {inMeeting ? (meetingSubject || "Teams Meeting") : activity.app}
                </span>
                {jarvisHandsFree && (
                  <span 
                    title={`JARVIS Active (${jarvisLanguage === 'hi-IN' ? 'Hindi/EN' : 'EN'})`}
                    className="flex items-center justify-center w-3.5 h-3.5 rounded-full bg-cyan-950/60 border border-cyan-500/40 text-cyan-300 flex-shrink-0"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                  </span>
                )}
              </div>
            )}

            {/* Right: Time + Pending Counter + Down arrow */}
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <span className="text-[10px] text-neutral-400 font-mono font-medium">
                {formatTime(activity.duration)}
              </span>
              {(pendingTasksCount > 0 || taskProposal) && (
                <span className="w-3.5 h-3.5 rounded-full bg-rose-500 text-white text-[8px] font-bold flex items-center justify-center animate-pulse">
                  {pendingTasksCount || 1}
                </span>
              )}
              <ChevronDown className="w-3 h-3 text-neutral-400" />
            </div>
          </div>
        ) : (
          /* EXPANDED HEADER (Tabs, Indicator, Actions) */
          <>
            {/* Left Navigation Tabs: Overview (Home), AI Chat, Tasks (Expandable), Wardrobe (Coucou Skins) */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => { setActiveTab('overview'); sounds.playClick(); }}
                title="Overview & Activity Status"
                className={`w-7 h-6 rounded-lg flex items-center justify-center transition cursor-pointer ${
                  activeTab === 'overview' ? 'bg-white/15 text-white' : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
                }`}
              >
                <CoucouIcon path={ICONS.house} size={13} />
              </button>

              <button
                onClick={() => { setActiveTab('chat'); sounds.playClick(); }}
                title="Ask Gemini Assistant"
                className={`w-7 h-6 rounded-lg flex items-center justify-center transition cursor-pointer relative ${
                  activeTab === 'chat' ? 'bg-white/15 text-white' : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
                }`}
              >
                <CoucouIcon path={ICONS.bubble} size={13} />
                <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-blue-400" />
              </button>

              <button
                onClick={() => { setActiveTab('tasks'); sounds.playClick(); }}
                title="Tasks & Follow-up Actions (Click to Expand)"
                className={`w-7 h-6 rounded-lg flex items-center justify-center transition cursor-pointer relative ${
                  activeTab === 'tasks' ? 'bg-white/15 text-white' : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
                }`}
              >
                <CoucouIcon path={ICONS.plus} size={13} />
                {(pendingTasksCount > 0 || taskProposal) && (
                  <span className="absolute -top-1 -right-1 min-w-[13px] h-[13px] rounded-full bg-rose-500 text-white text-[8px] font-bold flex items-center justify-center px-0.5 animate-pulse">
                    {pendingTasksCount || 1}
                  </span>
                )}
              </button>

              <button
                onClick={() => { setActiveTab(activeTab === 'wardrobe' ? 'overview' : 'wardrobe'); sounds.playClick(); }}
                title="Mochi Wardrobe (Outfits & Skins)"
                className={`w-7 h-6 rounded-lg flex items-center justify-center transition cursor-pointer relative ${
                  activeTab === 'wardrobe' ? 'bg-white/15 text-white' : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
                }`}
              >
                <CoucouIcon path={ICONS.hanger} size={14} />
              </button>
            </div>

            {/* Notch Center Gap Indicator / Drag Handle or Blinking Yellow Reminder Pill */}
            {activeReminder ? (
              <button 
                type="button"
                onClick={() => { setActiveTab('overview'); onExpand(); sounds.playClick(); }}
                title={`Task Reminder: ${activeReminder.title} (Click to open)`}
                className="flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/50 hover:bg-amber-400/30 transition cursor-pointer animate-pulse shadow-md shadow-amber-500/20 flex-shrink-0"
              >
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-80" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400" />
                </span>
                <Clock className="w-3 h-3 text-amber-400" />
                <span className="text-[10.5px] font-bold tracking-wide">Reminder</span>
              </button>
            ) : (
              <div 
                title="Drag Notch anywhere (Double-click to snap top)"
                className="w-16 h-1 rounded-full bg-white/20 hover:bg-white/40 cursor-grab active:cursor-grabbing transition" 
              />
            )}

            {/* Right Action Buttons */}
            <div className="flex items-center gap-1.5">
              {/* JARVIS Status & Toggle Button */}
              <button
                onClick={handleToggleVoice}
                title={
                  voiceMode === 'listening' ? "Hearing speech..." :
                  voiceMode === 'thinking' ? "Thinking..." :
                  voiceMode === 'speaking' ? "Speaking..." :
                  jarvisHandsFree ? "JARVIS Ambient Listening Active (Click to Mute)" : "Microphone Muted (Click to Enable)"
                }
                className={`w-7 h-6 rounded-lg flex items-center justify-center transition cursor-pointer relative ${
                  jarvisHandsFree 
                    ? voiceMode === 'listening'
                      ? 'bg-amber-500/20 text-amber-300'
                      : voiceMode === 'thinking'
                      ? 'bg-purple-500/20 text-purple-300'
                      : voiceMode === 'speaking'
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : 'bg-cyan-500/20 text-cyan-300'
                    : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
                }`}
              >
                <Mic className={`w-3.5 h-3.5 ${jarvisHandsFree ? (voiceMode === 'listening' ? 'animate-pulse' : '') : 'opacity-60'}`} />
                {jarvisHandsFree && (
                  <span className={`absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full ${
                    voiceMode === 'listening' ? 'bg-amber-400 animate-ping' :
                    voiceMode === 'thinking' ? 'bg-purple-400 animate-pulse' :
                    voiceMode === 'speaking' ? 'bg-emerald-400' :
                    'bg-cyan-400'
                  }`} />
                )}
              </button>

              {/* Language Switcher: Hindi/Hinglish to English or English Only */}
              <button
                onClick={handleToggleLanguage}
                title={`Language: ${jarvisLanguage === 'hi-IN' ? 'Hindi/Hinglish → English' : 'English Only'} (Click to toggle)`}
                className={`w-7 h-6 rounded-lg flex items-center justify-center transition cursor-pointer relative ${
                  jarvisLanguage === 'hi-IN' ? 'text-amber-300 bg-amber-500/10' : 'text-neutral-400 hover:bg-white/5 hover:text-neutral-200'
                }`}
              >
                <Languages className="w-3.5 h-3.5" />
              </button>

              {/* Vision Intelligence Hub (Ctrl+Shift+S) */}
              <button
                onClick={() => {
                  sounds.playClick();
                  setActiveTab('overview');
                  if (!isExpanded) onExpand();
                  if (showVisionHub) {
                    setShowVisionHub(false);
                  } else {
                    if (visionResult) onDismissVision?.();
                    if (replySuggestion) onDismissReply?.();
                    setShowVisionHub(true);
                  }
                }}
                title="Vision Intelligence Hub: Diagnose Error, Rephrase, or Suggest Reply"
                className={`w-7 h-6 rounded-lg flex items-center justify-center transition cursor-pointer ${
                  showVisionHub || isAnalyzingScreen || visionResult ? 'bg-indigo-500/20 text-indigo-300' : 'text-neutral-400 hover:bg-white/5 hover:text-indigo-300'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={toggleSound}
                title={soundEnabled ? "Mute Sounds" : "Unmute Sounds"}
                className="p-1 rounded-md text-neutral-400 hover:text-white hover:bg-white/5 transition cursor-pointer"
              >
                <CoucouIcon path={soundEnabled ? ICONS.speakerOn : ICONS.speakerOff} size={13} />
              </button>

              <button
                onClick={() => { onOpenSettings(); sounds.playClick(); }}
                title="Settings"
                className="p-1 rounded-md text-neutral-400 hover:text-white hover:bg-white/5 transition cursor-pointer"
              >
                <CoucouIcon path={ICONS.gear} size={13} />
              </button>

              <button
                onClick={handleImmediateCollapse}
                title="Collapse Notch"
                className="p-1 rounded-md text-neutral-400 hover:text-white hover:bg-white/5 transition cursor-pointer"
              >
                <CoucouIcon path={ICONS.chevronUp} size={13} />
              </button>

              <button
                onClick={() => api.quitApp()}
                title="Quit Assistant App"
                className="p-1 rounded-md text-neutral-500 hover:text-rose-400 hover:bg-white/5 transition cursor-pointer"
              >
                <CoucouIcon path={ICONS.xmark} size={13} />
              </button>
            </div>
          </>
        )}
      </div>

      {/* ─────────────────────────────────────────────────────────────
          ROW 2: EXPANDED BODY
          ───────────────────────────────────────────────────────────── */}
      {isExpanded && (
        <div 
          className="flex-1 p-3 flex gap-3 overflow-hidden animate-in fade-in duration-200"
          style={{ height: expandedHeight - 36 }}
        >
          {/* ─────────────────────────────────────────────────────────────
              COUCOU FILE DROP VIEWS (Upload progress / Choose card / Drop zone)
              ───────────────────────────────────────────────────────────── */}
          {(dragOver || dragState !== 'idle') ? (
            dragState === 'uploading' ? (
              /* Upload Progress View (Coucou buildUploading) */
              <div 
                className="flex-1 coucou-card-wash p-3.5 flex items-center gap-3.5 relative overflow-hidden animate-in fade-in duration-150 text-left"
                style={{ '--wash': 'rgba(34, 197, 94, 0.22)' } as React.CSSProperties}
              >
                <Mochi state="working" outfit={activeOutfit} size={48} badge="working" />
                <div className="flex-1 flex flex-col justify-center gap-2 overflow-hidden">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-white truncate max-w-[360px] flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                      {uploadProgress >= 1 ? `✓ ${droppedFile?.name || 'File'}` : `Ingesting ${droppedFile?.name || 'file'}...`}
                    </span>
                    <span className="text-emerald-400 font-mono text-xs font-bold">
                      {Math.round(uploadProgress * 100)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-neutral-900 rounded-full overflow-hidden border border-white/10 p-0.5">
                    <div 
                      className="h-full bg-gradient-to-r from-emerald-500 via-cyan-400 to-emerald-400 rounded-full transition-all duration-150"
                      style={{ width: `${Math.round(uploadProgress * 100)}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-neutral-400">
                    Preparing context chip for Gemini Assistant...
                  </span>
                </div>
              </div>
            ) : dragState === 'choose' ? (
              /* Choose Action Card (Coucou buildChoose) */
              <div 
                className="flex-1 coucou-card-wash p-3.5 flex items-center justify-between relative overflow-hidden animate-in fade-in duration-150 text-left"
                style={{ '--wash': 'rgba(99, 102, 241, 0.22)' } as React.CSSProperties}
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <Mochi state="idle" outfit={activeOutfit} size={48} badge="dots" />
                  <div className="flex flex-col gap-1 min-w-0">
                    <div className="text-xs text-white truncate">
                      <b className="text-cyan-300 font-bold">{droppedFile?.name}</b> <span className="text-neutral-400">({formatBytes(droppedFile?.size || 0)}) is ready.</span>
                    </div>
                    <span className="text-[11px] text-neutral-300">
                      What do you want to do with it?
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={handleChooseAskQuestion}
                    className="coucou-btn coucou-btn-primary text-xs"
                  >
                    <CoucouIcon path={ICONS.bubble} size={12} />
                    <span>Ask a Question</span>
                  </button>
                  <button
                    onClick={handleCancelDrop}
                    className="coucou-btn coucou-btn-secondary text-xs"
                  >
                    <span>Cancel</span>
                  </button>
                </div>
              </div>
            ) : (
              /* Drag Over Active Marching Ants Box (Coucou buildUpload) */
              <div className="flex-1 relative flex flex-col items-center justify-center p-3 coucou-card overflow-hidden">
                <svg className="coucou-drop-frame" preserveAspectRatio="none">
                  <rect
                    x="1.5"
                    y="1.5"
                    width="calc(100% - 3px)"
                    height="calc(100% - 3px)"
                    rx="18"
                    fill="none"
                    strokeWidth="1.5"
                    strokeDasharray="6 5"
                  />
                </svg>
                <div className="flex flex-col items-center gap-1.5 z-10">
                  <span className="text-xs font-bold text-white tracking-wide">
                    Drop your files here
                  </span>
                  <div className="flex items-center gap-1.5 text-[10px] text-neutral-400 font-medium">
                    <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10">PDF</span>
                    <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10">Images</span>
                    <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10">Code</span>
                    <span className="px-2 py-0.5 rounded-full bg-white/5 border border-white/10">Docs</span>
                  </div>
                </div>
              </div>
            )
          ) : (
            <>
          {/* ─────────────────────────────────────────────────────────────
              TAB 1: OVERVIEW (Home view, 210px height)
              ───────────────────────────────────────────────────────────── */}
          {activeTab === 'overview' && (
            hasActiveContent ? (
              /* ── COUCOU RESPONSIVE FULL-WIDTH ACTIVE / PROCESSING CARD ── */
              <div 
                className="flex-1 h-full coucou-card-wash p-3 flex flex-col justify-between overflow-hidden animate-in fade-in duration-150 text-left"
                style={{
                  '--wash': replySuggestion ? 'rgba(99, 102, 241, 0.18)' :
                            isAnalyzingScreen ? 'rgba(34, 211, 238, 0.18)' :
                            voiceMode === 'thinking' ? 'rgba(168, 85, 247, 0.18)' :
                            voiceMode === 'listening' ? 'rgba(245, 165, 36, 0.18)' :
                            voiceMode === 'speaking' ? 'rgba(34, 197, 94, 0.18)' :
                            'rgba(99, 102, 241, 0.14)'
                } as React.CSSProperties}
              >
                {/* 1. Coucou Who-Row: Compact Mochi, Dot, Small App Name, Time in Numbers, Live Status Tag, Fold Button */}
                <div className="flex items-center justify-between pb-2 border-b border-white/5 relative z-10 flex-shrink-0">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="relative flex-shrink-0">
                      <Mochi
                        state={voiceMode === 'listening' ? 'listening' : voiceMode === 'thinking' ? 'thinking' : inMeeting ? 'meeting' : activity.app !== 'Idle' ? 'working' : 'idle'}
                        outfit={activeOutfit}
                        size={26}
                        badge={voiceActive ? 'bang' : inMeeting ? 'working' : 'dots'}
                      />
                    </div>

                    {/* Small App Name + Time in Numbers (Minimalist) */}
                    <div className="flex items-center gap-1.5 text-xs text-neutral-300 font-medium truncate">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0 animate-pulse" />
                      <span className="font-semibold text-white truncate max-w-[140px]" title={activity.app}>
                        {activity.app}
                      </span>
                      <span className="text-neutral-500 font-mono">•</span>
                      <span className="text-neutral-400 font-mono text-[11px]">
                        {formatTimeNumbers(activity.duration)}
                      </span>
                    </div>

                    {/* Status Pill with Coucou Shimmer when processing */}
                    <div className="ml-1.5 flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.06] border border-white/10">
                      {isAnalyzingScreen ? (
                        <span className="shimmer text-[11px] font-semibold flex items-center gap-1.5">
                          <Loader2 className="w-3 h-3 animate-spin text-cyan-400 inline" />
                          <span>Screen Vision Active</span>
                        </span>
                      ) : isResearching ? (
                        <span className="shimmer text-[11px] font-semibold flex items-center gap-1.5 text-cyan-300">
                          <Loader2 className="w-3 h-3 animate-spin text-cyan-400 inline" />
                          <span>Searching Web...</span>
                        </span>
                      ) : activeResearch?.status === 'completed' ? (
                        <span className="text-cyan-300 text-[11px] font-bold flex items-center gap-1">
                          <Sparkles className="w-3 h-3 text-cyan-400" />
                          <span>Research Ready</span>
                        </span>
                      ) : voiceMode === 'listening' ? (
                        <span className="shimmer text-[11px] font-semibold flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping inline-block" />
                          <span>Listening...</span>
                        </span>
                      ) : voiceMode === 'thinking' ? (
                        <span className="shimmer text-[11px] font-semibold flex items-center gap-1.5">
                          <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse inline-block" />
                          <span>Processing...</span>
                        </span>
                      ) : voiceMode === 'speaking' ? (
                        <span className="text-emerald-300 text-[11px] font-semibold flex items-center gap-1.5">
                          <Volume2 className="w-3 h-3 text-emerald-400 inline animate-pulse" />
                          <span>JARVIS Speaking</span>
                        </span>
                      ) : replySuggestion ? (
                        <span className="text-amber-300 text-[11px] font-bold flex items-center gap-1">
                          <Sparkles className="w-3 h-3 text-amber-300 animate-pulse" />
                          <span>Rephrased Draft</span>
                        </span>
                      ) : showVisionHub ? (
                        <span className="text-indigo-300 text-[11px] font-bold flex items-center gap-1">
                          <Eye className="w-3 h-3 text-indigo-400" />
                          <span>Vision Hub</span>
                        </span>
                      ) : visionResult ? (
                        <span className="text-indigo-300 text-[11px] font-bold flex items-center gap-1">
                          <Eye className="w-3 h-3 text-indigo-400" />
                          <span>Vision Result</span>
                        </span>
                      ) : activeReminder ? (
                        <span className="text-amber-300 text-[11px] font-bold flex items-center gap-1.5 animate-pulse">
                          <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-80" />
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400" />
                          </span>
                          <Clock className="w-3 h-3 text-amber-400" />
                          <span>Reminder</span>
                        </span>
                      ) : taskProposal ? (
                        <span className="text-cyan-300 text-[11px] font-bold flex items-center gap-1">
                          <Sparkles className="w-3 h-3 text-cyan-400" />
                          <span>New Task</span>
                        </span>
                      ) : (
                        <span className="text-neutral-400 text-[11px]">Active</span>
                      )}
                    </div>
                  </div>

                  {/* Right: Coucou Fold Button */}
                  <button
                    onClick={() => {
                      sounds.playCollapse();
                      setShowVisionHub(false);
                      setPointerCountingDown(false);
                      if (replySuggestion) onDismissReply?.();
                      if (visionResult) onDismissVision?.();
                      if (activeReminder) onDismissReminder?.();
                      if (taskProposal) onDismissProposal?.();
                      onClearResearch?.();
                      onClearVoiceData?.();
                      setVoiceInterimText('');
                      setVoiceReplyText('');
                    }}
                    title="Dismiss to Idle"
                    className="w-5 h-5 rounded-full bg-white/10 hover:bg-white/20 text-neutral-400 hover:text-white flex items-center justify-center transition cursor-pointer flex-shrink-0"
                  >
                    <CoucouIcon path={ICONS.xmark} size={9} />
                  </button>
                </div>

                {/* 2. Middle Body: Full-width live process ticker or content */}
                <div className="flex-1 flex flex-col justify-center py-2 overflow-hidden relative z-10">
                  {/* Case 0: Vision Intelligence Hub (Redesigned with Scope Selector, 4 Tools & Custom Bar) */}
                  {showVisionHub ? (
                    <div className="flex flex-col gap-2 overflow-hidden flex-1 animate-in fade-in duration-150 justify-between">
                      {/* Header: Title + Scope Modifier Pills (Full Screen vs Pointer 2s) + Target App */}
                      <div className="flex items-center justify-between pb-1 border-b border-white/5 flex-shrink-0">
                        <div className="flex items-center gap-1.5">
                          <Eye className="w-3.5 h-3.5 text-indigo-400" />
                          <span className="text-xs font-bold text-white tracking-wide">
                            Vision Intelligence
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          {/* Scope Selector: Full Screen vs Pointer */}
                          <div className="flex items-center bg-white/[0.06] p-0.5 rounded-lg border border-white/10 text-[10px]">
                            <button
                              type="button"
                              onClick={() => { setVisionScope('fullscreen'); sounds.playClick(); }}
                              className={`px-2 py-0.5 rounded-md font-medium transition cursor-pointer flex items-center gap-1 ${
                                visionScope === 'fullscreen'
                                  ? 'bg-indigo-600 text-white font-bold shadow-xs'
                                  : 'text-neutral-400 hover:text-white'
                              }`}
                            >
                              <span>🖥️ Full Screen</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => { setVisionScope('pointer'); sounds.playClick(); }}
                              className={`px-2 py-0.5 rounded-md font-medium transition cursor-pointer flex items-center gap-1 ${
                                visionScope === 'pointer'
                                  ? 'bg-amber-600 text-white font-bold shadow-xs'
                                  : 'text-neutral-400 hover:text-white'
                              }`}
                            >
                              <span>🎯 Mouse (2s)</span>
                            </button>
                          </div>

                          <span className="text-[10px] text-neutral-400 font-mono truncate max-w-[80px]" title={activity.app || "Desktop"}>
                            {activity.app || "Desktop"}
                          </span>

                          {/* Close Button */}
                          <button
                            onClick={() => {
                              setShowVisionHub(false);
                              setCustomVisionPrompt('');
                              sounds.playClick();
                            }}
                            title="Close Vision Hub"
                            className="w-4 h-4 rounded-full bg-white/5 hover:bg-white/15 text-neutral-400 hover:text-white flex items-center justify-center transition cursor-pointer"
                          >
                            <CoucouIcon path={ICONS.xmark} size={8} />
                          </button>
                        </div>
                      </div>

                      {/* 4 Tool Cards in 2x2 Grid (1-Click Execution with Themed Mini Mochi Avatars) */}
                      <div className="grid grid-cols-2 gap-2 my-auto">
                        {/* 1. Diagnose Error (Red / Cyberpunk Mochi with Sunglasses & Bang badge) */}
                        <button
                          onClick={() => executeVisionAction(
                            'error_diagnosis',
                            'Diagnose the error, exception, or failure visible on screen and provide the exact fix'
                          )}
                          className="flex flex-col items-start justify-center gap-0.5 p-2 rounded-xl bg-white/[0.04] hover:bg-rose-950/30 border border-white/10 hover:border-rose-500/40 transition cursor-pointer text-left group min-h-[52px]"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-lg bg-rose-500/15 border border-rose-500/30 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform shadow-xs">
                              <Mochi outfit="sunglasses" state="thinking" badge="bang" size={20} interactive={false} />
                            </div>
                            <span className="text-[11px] font-bold text-white group-hover:text-rose-200">
                              Diagnose Error
                            </span>
                          </div>
                          <span className="text-[9px] text-neutral-400 leading-tight">
                            Bugs, stack traces, terminal logs & fix
                          </span>
                        </button>

                        {/* 2. Extract Fields & Data (Cyan / Developer Mochi with Round Glasses) */}
                        <button
                          onClick={() => executeVisionAction(
                            'data_extraction',
                            'Extract all visible form fields, work item details, and tables. Distinguish required vs optional fields and format cleanly.'
                          )}
                          className="flex flex-col items-start justify-center gap-0.5 p-2 rounded-xl bg-white/[0.04] hover:bg-cyan-950/30 border border-white/10 hover:border-cyan-500/40 transition cursor-pointer text-left group min-h-[52px]"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform shadow-xs">
                              <Mochi outfit="roundGlasses" state="working" badge="working" size={20} interactive={false} />
                            </div>
                            <span className="text-[11px] font-bold text-white group-hover:text-cyan-200">
                              Extract Fields & Data
                            </span>
                          </div>
                          <span className="text-[9px] text-neutral-400 leading-tight">
                            Azure DevOps, Jira, forms (required vs optional)
                          </span>
                        </button>

                        {/* 3. Rephrase Text (Purple / Wizard Scribe Mochi with Witch Hat) */}
                        <button
                          onClick={() => executeVisionAction(
                            'rephrase',
                            'Identify draft or highlighted text on screen and rephrase into executive English'
                          )}
                          className="flex flex-col items-start justify-center gap-0.5 p-2 rounded-xl bg-white/[0.04] hover:bg-purple-950/30 border border-white/10 hover:border-purple-500/40 transition cursor-pointer text-left group min-h-[52px]"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-lg bg-purple-500/15 border border-purple-500/30 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform shadow-xs">
                              <Mochi outfit="witchHat" state="question" badge="dots" size={20} interactive={false} />
                            </div>
                            <span className="text-[11px] font-bold text-white group-hover:text-purple-200">
                              Rephrase Text
                            </span>
                          </div>
                          <span className="text-[9px] text-neutral-400 leading-tight">
                            Polish drafts or selected text into executive English
                          </span>
                        </button>

                        {/* 4. Suggest Reply (Emerald / Diplomat Mochi with Crown) */}
                        <button
                          onClick={() => executeVisionAction(
                            'teams_reply',
                            'Suggest an executive, professional reply to the message on screen'
                          )}
                          className="flex flex-col items-start justify-center gap-0.5 p-2 rounded-xl bg-white/[0.04] hover:bg-emerald-950/30 border border-white/10 hover:border-emerald-500/40 transition cursor-pointer text-left group min-h-[52px]"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform shadow-xs">
                              <Mochi outfit="crown" state="idle" badge="question" size={20} interactive={false} />
                            </div>
                            <span className="text-[11px] font-bold text-white group-hover:text-emerald-200">
                              Suggest Reply
                            </span>
                          </div>
                          <span className="text-[9px] text-neutral-400 leading-tight">
                            Executive response for Teams chats or emails
                          </span>
                        </button>
                      </div>

                      {/* Optional Custom Instruction Bar (Bottom) */}
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          if (customVisionPrompt.trim()) {
                            executeVisionAction('general', customVisionPrompt.trim());
                          }
                        }}
                        className="flex items-center gap-1.5 h-[28px] px-2.5 rounded-lg bg-white/[0.05] border border-white/10 focus-within:border-indigo-400/50 transition-all flex-shrink-0"
                      >
                        <input
                          type="text"
                          value={customVisionPrompt}
                          onChange={(e) => setCustomVisionPrompt(e.target.value)}
                          placeholder="Optional instruction (or click a tool above)..."
                          className="flex-1 min-w-0 bg-transparent text-[11px] text-white placeholder-neutral-500 focus:outline-none"
                        />
                        {customVisionPrompt.trim() && (
                          <button
                            type="submit"
                            className="text-[10px] font-bold text-indigo-300 hover:text-white px-2 py-0.5 rounded bg-indigo-600/60 hover:bg-indigo-600 transition cursor-pointer"
                          >
                            Run
                          </button>
                        )}
                      </form>
                    </div>
                  ) : pointerCountingDown ? (
                    <div className="flex flex-col gap-2 p-3 rounded-xl bg-amber-950/30 border border-amber-500/30 animate-pulse">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-amber-200 flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                          <span>Hover your cursor over the target content...</span>
                        </span>
                        <span className="text-[10px] text-amber-300 font-mono font-bold bg-amber-500/20 px-2 py-0.5 rounded-full">
                          Capturing in 2s
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-amber-500 via-amber-300 to-amber-500 animate-[coucou-shimmer_1.5s_infinite] w-full" />
                      </div>
                      <span className="text-[10px] text-neutral-400">
                        Position your mouse over the target window, form, code, or chat to crop a 720×500 area
                      </span>
                    </div>
                  ) : isAnalyzingScreen ? (
                    <div className="flex flex-col gap-2 p-3 rounded-xl bg-indigo-950/30 border border-indigo-500/20">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Mochi outfit="roundGlasses" state="thinking" badge="dots" size={22} interactive={false} />
                          <span className="shimmer text-xs font-semibold text-cyan-200">
                            Analyzing screen & processing vision request...
                          </span>
                        </div>
                        <span className="text-[10px] text-cyan-300 font-mono">Vision AI</span>
                      </div>
                      <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-purple-500 via-cyan-400 to-indigo-500 animate-[coucou-shimmer_1.5s_infinite] w-full" />
                      </div>
                    </div>
                  ) : isResearching ? (
                    <div className="flex flex-col gap-2 p-3 rounded-xl bg-cyan-950/30 border border-cyan-500/20">
                      <div className="flex items-center justify-between">
                        <span className="shimmer text-xs font-semibold text-cyan-200">
                          Searching Google & the web for "{activeResearch?.query}"...
                        </span>
                        <span className="text-[10px] text-cyan-400 font-mono">Live Search</span>
                      </div>
                      <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-cyan-400 via-blue-500 to-cyan-400 animate-[coucou-shimmer_1.5s_infinite] w-full" />
                      </div>
                    </div>
                  ) : voiceMode === 'listening' ? (
                    <div className="flex flex-col gap-2 p-3 rounded-xl bg-amber-950/30 border border-amber-500/20">
                      <div className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping" />
                        <span className="shimmer text-xs font-medium">
                          {voiceInterimText ? `"${voiceInterimText}"` : "Listening... Speak naturally in English or Hindi"}
                        </span>
                      </div>
                    </div>
                  ) : voiceMode === 'thinking' ? (
                    <div className="flex flex-col gap-2 p-3 rounded-xl bg-purple-950/30 border border-purple-500/20">
                      <div className="flex items-center justify-between">
                        <span className="shimmer text-xs font-semibold">
                          {voiceInterimText ? `Reasoning for: "${voiceInterimText}"` : "Reasoning & executing agent tools..."}
                        </span>
                        <span className="text-[10px] text-purple-300 font-mono">Groq + Gemini</span>
                      </div>
                      <div className="w-full h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-purple-500 via-cyan-400 to-purple-500 animate-[coucou-shimmer_1.5s_infinite] w-full" />
                      </div>
                    </div>
                  ) : (voiceMode === 'speaking' || displayVoiceReply) ? (
                    <div className="flex flex-col gap-2 overflow-hidden">
                      {displayVoiceUser && (
                        <div className="text-[11px] text-neutral-400 font-medium px-1 flex items-center gap-1.5 truncate">
                          <span className="text-neutral-500 font-mono text-[10px] uppercase">You:</span>
                          <span className="text-neutral-200 italic truncate">"{displayVoiceUser}"</span>
                        </div>
                      )}
                      <div className="coucou-code flex items-start gap-2.5 overflow-y-auto max-h-[120px]">
                        <Volume2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5 animate-pulse" />
                        <span className="text-[#f5f6f8] text-xs font-medium leading-relaxed select-text">
                          {displayVoiceReply || "JARVIS is replying..."}
                        </span>
                      </div>
                      {(latestVoiceData?.detailedAnswer || latestVoiceData?.action === 'web_search' || activeResearch) && (
                        <button
                          onClick={() => { setActiveTab('chat'); sounds.playClick(); }}
                          className="self-start text-[11px] font-semibold text-cyan-300 hover:text-white px-2.5 py-1 rounded-full bg-cyan-950/60 border border-cyan-500/30 hover:border-cyan-400 transition cursor-pointer flex items-center gap-1.5"
                        >
                          <CoucouIcon path={ICONS.bubble} size={11} />
                          <span>View Full Research in Chat 💬</span>
                        </button>
                      )}
                    </div>
                  ) : replySuggestion ? (
                    /* Case 2: Rephrase Draft Output with Transparent Input */
                    <div className="flex flex-col gap-2 overflow-hidden flex-1 justify-center select-text">
                      {/* What was captured as input from screen */}
                      <div className="p-2 rounded-xl bg-white/[0.04] border border-white/10 flex flex-col gap-0.5 flex-shrink-0">
                        <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider">
                          <span className="flex items-center gap-1.5 text-cyan-300">
                            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                            Input Captured from Screen
                          </span>
                          <span className="text-neutral-500 font-mono text-[9px]">Original</span>
                        </div>
                        <div className="text-[11px] text-neutral-300 italic truncate" title={replySuggestion.original}>
                          "{replySuggestion.original || "Highlighted screen text / prompt"}"
                        </div>
                      </div>

                      {/* Polished English Output */}
                      <div className="coucou-code text-[12.5px] text-[#f5f6f8] font-medium leading-relaxed overflow-y-auto max-h-[120px] border-indigo-500/30 bg-indigo-950/25 p-3 rounded-xl shadow-inner">
                        <div className="text-[10px] font-bold text-indigo-300 uppercase tracking-wider mb-1 flex items-center gap-1">
                          <Sparkles className="w-3 h-3 text-indigo-400" />
                          <span>Polished English</span>
                        </div>
                        "{replySuggestion.reply}"
                      </div>
                    </div>
                  ) : visionResult ? (
                    /* Case 3: Complete Screen Vision Inspection Card */
                    <div className="flex flex-col gap-2 overflow-hidden flex-1 justify-center select-text">
                      {/* Top: Input Context Row (What Vision captured & read) */}
                      <div className="flex items-center gap-2.5 p-2 rounded-xl bg-white/[0.04] border border-white/10 flex-shrink-0">
                        {visionResult.thumbnail_b64 ? (
                          <div className="relative rounded-lg overflow-hidden border border-white/15 w-[76px] h-[44px] flex-shrink-0 shadow-md">
                            <img
                              src={`data:image/jpeg;base64,${visionResult.thumbnail_b64}`}
                              alt="Captured Desktop Screen"
                              className="w-full h-full object-cover"
                            />
                            <div className="absolute inset-0 bg-indigo-500/10 pointer-events-none" />
                          </div>
                        ) : (
                          <div className="w-[44px] h-[44px] rounded-lg bg-indigo-950/60 border border-indigo-500/30 flex items-center justify-center flex-shrink-0">
                            <Eye className="w-5 h-5 text-indigo-400" />
                          </div>
                        )}

                        <div className="flex flex-col min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-1">
                            <span className="text-[10px] font-bold text-indigo-300 uppercase tracking-wider flex items-center gap-1 truncate">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block animate-pulse" />
                              {visionResult.active_app ? `Screen: ${visionResult.active_app}` : "Full Desktop Screen"}
                              {visionResult.inspection_mode && (
                                <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-200 font-mono ml-1">
                                  {visionResult.inspection_mode}
                                </span>
                              )}
                            </span>
                            {visionResult.captured_at && (
                              <span className="text-[9.5px] text-neutral-400 font-mono">
                                {visionResult.captured_at}
                              </span>
                            )}
                          </div>
                          <span className="text-[11px] text-neutral-200 truncate font-medium" title={visionResult.summary}>
                            {visionResult.summary || "Full desktop screen captured & analyzed"}
                          </span>
                          {visionResult.detected_input && (
                            <span className="text-[10px] text-cyan-300/90 font-mono truncate" title={visionResult.detected_input}>
                              Input: "{visionResult.detected_input}"
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Middle: AI Observation & Diagnosis */}
                      <div className="flex-1 flex flex-col gap-1 overflow-y-auto max-h-[145px] p-2.5 rounded-xl bg-indigo-950/20 border border-indigo-500/25">
                        <div className="flex items-center gap-1.5 text-[10px] font-bold text-indigo-300 uppercase tracking-wider">
                          <Sparkles className="w-3 h-3 text-indigo-400" />
                          <span>Diagnosis & Analysis</span>
                        </div>
                        <div className="text-xs text-[#f5f6f8] font-medium leading-relaxed">
                          {visionResult.diagnosis || visionResult.summary}
                        </div>

                        {visionResult.suggested_action && (
                          <div className="mt-1 pt-1 border-t border-white/5 text-[11px] text-amber-200 flex items-start gap-1.5">
                            <span className="font-bold text-amber-300 flex-shrink-0">Suggested Fix:</span>
                            <span>{visionResult.suggested_action}</span>
                          </div>
                        )}

                        {visionResult.suggested_reply && (
                          <div className="mt-1 pt-1 border-t border-white/5 text-[11px] text-emerald-300 flex flex-col gap-1">
                            <span className="font-bold text-emerald-400 flex items-center gap-1">
                              <Sparkles className="w-3 h-3 text-emerald-400" />
                              <span>{visionResult.suggested_reply.includes(':') || visionResult.suggested_reply.includes('|') || visionResult.suggested_reply.includes('\n') ? 'Extracted Data & Form Fields:' : 'Suggested Output:'}</span>
                            </span>
                            <div className="whitespace-pre-wrap font-mono text-[10.5px] bg-black/40 p-2 rounded-lg border border-emerald-500/20 select-text max-h-[90px] overflow-y-auto text-neutral-100">
                              {visionResult.suggested_reply}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : activeReminder ? (
                    /* Case 4: Spacious & High-Contrast Task Reminder Card */
                    <div className="flex flex-col justify-between gap-2.5 p-3.5 rounded-2xl bg-gradient-to-b from-amber-500/[0.12] to-amber-500/[0.04] border border-amber-500/40 relative overflow-hidden backdrop-blur-md shadow-lg shadow-amber-950/20 select-text flex-1">
                      {/* Top Row: Glowing Beacon + Badge + Interval + Source */}
                      <div className="flex items-center justify-between pb-1.5 border-b border-amber-500/20 flex-shrink-0">
                        <div className="flex items-center gap-2">
                          <span className="relative flex h-2.5 w-2.5">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-80" />
                            <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-400 shadow-sm shadow-amber-400" />
                          </span>
                          <span className="text-[11px] font-black text-amber-300 uppercase tracking-wider flex items-center gap-1.5">
                            <Clock className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
                            <span>Task Reminder</span>
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {activeReminder.task?.source && activeReminder.task.source !== 'manual' && (
                            <span className="text-[9.5px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-200 border border-amber-500/30 font-medium">
                              {activeReminder.task.source.startsWith('teams_') 
                                ? `Teams: ${activeReminder.task.source.replace('teams_', '')}`
                                : (activeReminder.task.source as string) === 'island_quick' 
                                  ? 'Quick Task' 
                                  : activeReminder.task.source}
                            </span>
                          )}
                          <span className="text-[10px] text-amber-200/90 font-mono font-bold bg-amber-500/25 px-2.5 py-0.5 rounded-full border border-amber-500/30">
                            every {activeReminder.task?.reminder_interval_mins || (activeReminder as any).interval_mins || 30}m
                          </span>
                        </div>
                      </div>

                      {/* Middle: Prominent Bold Task Title & Description */}
                      <div className="flex flex-col gap-1.5 my-auto overflow-y-auto max-h-[100px] pr-1">
                        <div className="text-[14px] font-bold text-white leading-snug select-text">
                          {activeReminder.task?.title || activeReminder.title || (activeReminder as any).message || "Follow up on pending task"}
                        </div>

                        {activeReminder.task?.description && 
                         activeReminder.task.description.trim() !== (activeReminder.task?.title || activeReminder.title || '').trim() && 
                         !activeReminder.task.description.startsWith('Task reminder:') ? (
                          <div className="text-[11.5px] text-neutral-300 select-text leading-relaxed bg-black/40 p-2 rounded-xl border border-white/10 italic">
                            {activeReminder.task.description}
                          </div>
                        ) : (
                          <div className="text-[10.5px] text-neutral-400 flex items-center gap-2 font-mono">
                            <span>Status: Pending</span>
                            {activeReminder.task?.created_at && (
                              <>
                                <span>•</span>
                                <span>Created: {new Date(activeReminder.task.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : taskProposal ? (
                    /* Case 5: Detected Task Proposal */
                    <div className="flex items-center justify-between p-2.5 rounded-xl bg-blue-950/30 border border-blue-500/20">
                      <div className="flex flex-col min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] uppercase font-bold text-blue-300">
                            {taskProposal.sender ? `Task from ${taskProposal.sender}` : 'Teams Task'}
                          </span>
                          <span className="text-[9px] px-1.5 rounded-full bg-blue-500/20 text-blue-300 font-mono">
                            {taskProposal.priority || 'High'}
                          </span>
                        </div>
                        <span className="text-xs font-semibold text-white truncate">{taskProposal.title}</span>
                      </div>
                    </div>
                  ) : null}
                </div>

                {/* 3. Coucou Actions Footer Row */}
                <div className="flex items-center justify-between pt-1.5 border-t border-white/5 relative z-10 flex-shrink-0">
                  <div className="flex items-center gap-2">
                    {activeReminder ? (
                      /* Snooze / Extend Buttons: +5m and +15m */
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={async () => {
                            const tid = activeReminder.task?.id || (activeReminder as any).task_id;
                            if (tid) {
                              sounds.playClick();
                              await api.extendTask(tid, 5);
                              onDismissReminder?.();
                              onTasksRefresh();
                            }
                          }}
                          title="Snooze reminder by 5 minutes"
                          className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 text-xs font-bold transition active:scale-95 cursor-pointer shadow-xs"
                        >
                          <Plus className="w-3.5 h-3.5 stroke-[3]" />
                          <span>5m</span>
                        </button>
                        <button
                          onClick={async () => {
                            const tid = activeReminder.task?.id || (activeReminder as any).task_id;
                            if (tid) {
                              sounds.playClick();
                              await api.extendTask(tid, 15);
                              onDismissReminder?.();
                              onTasksRefresh();
                            }
                          }}
                          title="Snooze reminder by 15 minutes"
                          className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 text-xs font-bold transition active:scale-95 cursor-pointer shadow-xs"
                        >
                          <Plus className="w-3.5 h-3.5 stroke-[3]" />
                          <span>15m</span>
                        </button>
                      </div>
                    ) : (
                      <span className="text-[10.5px] text-neutral-400">
                        {showVisionHub ? "Select a vision action for your screen" :
                         replySuggestion ? "Click Copy or press Ctrl+C to paste" :
                         visionResult ? "Full desktop screen inspected" :
                         isProcessing ? "Processing in background" : "Coucou Desktop Island"}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {activeReminder ? (
                      <>
                        <button
                          onClick={onDismissReminder}
                          className="coucou-btn coucou-btn-secondary text-[11px]"
                        >
                          <span>Dismiss</span>
                        </button>
                        <button
                          onClick={() => {
                            const tid = activeReminder.task?.id || (activeReminder as any).task_id;
                            if (tid) handleToggleTask(tid);
                            onDismissReminder?.();
                          }}
                          className="coucou-btn coucou-btn-primary text-[11px] font-bold"
                        >
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Mark Done</span>
                        </button>
                      </>
                    ) : showVisionHub ? (
                      <button
                        onClick={() => {
                          sounds.playClick();
                          setShowVisionHub(false);
                          if (visionResult) onDismissVision?.();
                          if (replySuggestion) onDismissReply?.();
                        }}
                        className="coucou-btn coucou-btn-secondary text-[11px]"
                      >
                        <span>Cancel</span>
                      </button>
                    ) : replySuggestion ? (
                      <>
                        <button
                          onClick={onDismissReply}
                          className="coucou-btn coucou-btn-secondary text-[11px]"
                        >
                          <span>Dismiss</span>
                        </button>
                        <button
                          onClick={async () => {
                            await api.copyToClipboard(replySuggestion.reply);
                            sounds.playComplete();
                            setCopied(true);
                            setTimeout(() => setCopied(false), 2000);
                          }}
                          className="coucou-btn coucou-btn-primary text-[11px]"
                        >
                          {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <CoucouIcon path={ICONS.copy} size={11} />}
                          <span>{copied ? "Copied!" : "Copy"}</span>
                          <span className="coucou-kbd">Ctrl+C</span>
                        </button>
                      </>
                    ) : visionResult ? (
                      <>
                        <button
                          onClick={() => {
                            setShowVisionHub(true);
                            if (onDismissVision) onDismissVision();
                          }}
                          className="coucou-btn coucou-btn-secondary text-[11px]"
                          title="Switch to another vision mode"
                        >
                          <Eye className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Modes</span>
                        </button>
                        <button
                          onClick={onDismissVision}
                          className="coucou-btn coucou-btn-secondary text-[11px]"
                        >
                          <span>Dismiss</span>
                        </button>
                        {(visionResult.suggested_reply || visionResult.suggested_action || visionResult.diagnosis) && (
                          <button
                            onClick={async () => {
                              const textToCopy = visionResult.suggested_reply || visionResult.suggested_action || visionResult.diagnosis;
                              if (textToCopy) {
                                await api.copyToClipboard(textToCopy);
                                sounds.playComplete();
                                setCopied(true);
                                setTimeout(() => setCopied(false), 2000);
                              }
                            }}
                            className="coucou-btn coucou-btn-primary text-[11px]"
                          >
                            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <CoucouIcon path={ICONS.copy} size={11} />}
                            <span>{copied ? "Copied!" : "Copy"}</span>
                            <span className="coucou-kbd">Ctrl+C</span>
                          </button>
                        )}
                      </>
                    ) : taskProposal ? (
                      <>
                        <button
                          onClick={onDismissProposal}
                          className="coucou-btn coucou-btn-secondary text-[11px]"
                        >
                          <span>Dismiss</span>
                        </button>
                        <button
                          onClick={onAcceptProposal}
                          className="coucou-btn coucou-btn-primary text-[11px]"
                        >
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                          <span>Accept Task</span>
                        </button>
                      </>
                    ) : displayVoiceReply ? (
                      <button
                        onClick={async () => {
                          await api.copyToClipboard(displayVoiceReply);
                          sounds.playComplete();
                          setCopied(true);
                          setTimeout(() => setCopied(false), 2000);
                        }}
                        className="coucou-btn coucou-btn-primary text-[11px]"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <CoucouIcon path={ICONS.copy} size={11} />}
                        <span>{copied ? "Copied!" : "Copy"}</span>
                      </button>
                    ) : isProcessing ? (
                      <button
                        onClick={() => {
                          sounds.playCollapse();
                          if (onDismissVision) onDismissVision();
                          setVoiceMode('idle');
                        }}
                        className="coucou-btn coucou-btn-secondary text-[11px]"
                      >
                        <span>Cancel</span>
                      </button>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : (
              /* ── IDLE ZEN CARD (COUCOU 160PX COMPACT CARD) ── */
              <>
                {/* Left Card: Compact Mochi + App Focus + Time in Mono Numbers */}
                <div className="w-[230px] flex items-center gap-3 p-3 rounded-2xl bg-[#141518] border border-white/8 flex-shrink-0">
                  {/* Left: Compact Mochi with Outfit Badge */}
                  <div className="relative group flex-shrink-0 flex items-center justify-center">
                    <Mochi
                      state={voiceMode === 'listening' ? 'listening' : voiceMode === 'thinking' ? 'thinking' : inMeeting ? 'meeting' : activity.app !== 'Idle' ? 'working' : 'idle'}
                      outfit={activeOutfit}
                      size={52}
                      badge={voiceActive ? 'bang' : inMeeting ? 'working' : 'dots'}
                      onContextMenu={handleMochiContextMenu}
                    />
                    <button
                      onClick={() => { setActiveTab('wardrobe'); sounds.playClick(); }}
                      title="Open Mochi Wardrobe Skins"
                      className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-neutral-900 border border-white/20 text-neutral-300 hover:text-white flex items-center justify-center opacity-80 group-hover:opacity-100 transition shadow cursor-pointer"
                    >
                      <CoucouIcon path={ICONS.hanger} size={9} />
                    </button>
                  </div>

                  {/* Right: Clean App Info & Time Tracking */}
                  <div className="flex-1 min-w-0 flex flex-col justify-center gap-1 text-left">
                    <div className="flex flex-col overflow-hidden">
                      <span className="text-xs font-bold text-white truncate" title={activity.app}>
                        {activity.app}
                      </span>
                      <span className="text-[10px] text-neutral-400 truncate">
                        {inMeeting ? "Teams Meeting" : "Active Focus"}
                      </span>
                    </div>

                    <div className="flex flex-col gap-0.5 text-[11px]">
                      <div className="flex items-center gap-1.5 text-emerald-400 font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        <span className="truncate text-[10.5px]">Tracking</span>
                      </div>
                      <div className="flex items-center gap-1 text-neutral-300 text-[10px]">
                        <Clock className="w-2.5 h-2.5 text-neutral-400 flex-shrink-0" />
                        <span className="truncate">Today: <strong className="text-white font-mono">{formatTime(activity.duration)}</strong></span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Card: 4 Coucou Action Pills in clean 2x2 Grid (Coucou exact replica) */}
                <div className="flex-1 flex flex-col justify-center p-3 rounded-2xl bg-[#141518] border border-white/8 text-left overflow-hidden">
                  <div className="w-full grid grid-cols-2 gap-2.5 my-auto">
                    {/* Pill 1: Ask Mochi */}
                    <button
                      onClick={() => { setActiveTab('chat'); sounds.playClick(); }}
                      className="coucou-pill-btn group text-left h-[42px] px-3.5 flex items-center gap-2.5"
                      title="Ask Mochi (AI Chat)"
                    >
                      <CoucouIcon path={ICONS.bubble} size={13} className="text-cyan-400 group-hover:text-cyan-300 transition-colors flex-shrink-0" />
                      <span className="text-xs font-medium text-neutral-200 group-hover:text-white truncate">Ask Mochi</span>
                    </button>

                    {/* Pill 2: Tasks */}
                    <button
                      onClick={() => { setActiveTab('tasks'); sounds.playClick(); }}
                      className="coucou-pill-btn group text-left h-[42px] px-3.5 flex items-center gap-2.5 relative"
                      title="View & Manage Tasks"
                    >
                      <Check className="w-3.5 h-3.5 text-emerald-400 group-hover:text-emerald-300 transition-colors flex-shrink-0" />
                      <span className="text-xs font-medium text-neutral-200 group-hover:text-white truncate">Tasks</span>
                      {pendingTasksCount > 0 && (
                        <span className="coucou-pill-badge">{pendingTasksCount}</span>
                      )}
                    </button>

                    {/* Pill 3: Screen Vision */}
                    <button
                      onClick={() => {
                        sounds.playClick();
                        if (visionResult) onDismissVision?.();
                        if (replySuggestion) onDismissReply?.();
                        setShowVisionHub(true);
                      }}
                      className="coucou-pill-btn group text-left h-[42px] px-3.5 flex items-center gap-2.5"
                      title="Vision Intelligence Hub (Ctrl+Shift+S)"
                    >
                      <Eye className="w-3.5 h-3.5 text-indigo-400 group-hover:text-indigo-300 transition-colors flex-shrink-0" />
                      <span className="text-xs font-medium text-neutral-200 group-hover:text-white truncate">Vision</span>
                    </button>

                    {/* Pill 4: EOD Tasks (Azure DevOps Work Items & Daily Work Summary) */}
                    <button
                      onClick={() => { onOpenEOD(); sounds.playClick(); }}
                      className="coucou-pill-btn group text-left h-[42px] px-3.5 flex items-center gap-2.5"
                      title="End of Day AI Summary & Push to Azure DevOps"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-amber-400 group-hover:text-amber-300 transition-colors flex-shrink-0" />
                      <span className="text-xs font-medium text-neutral-200 group-hover:text-white truncate">EOD Tasks</span>
                    </button>
                  </div>
                </div>
              </>
            )
          )}

          {/* ─────────────────────────────────────────────────────────────
              TAB 2: AI CHAT (Gemini Assistant)
              ───────────────────────────────────────────────────────────── */}
          {/* ─────────────────────────────────────────────────────────────
              TAB 2: AI CHAT (Gemini Assistant & Live Web Research)
              ───────────────────────────────────────────────────────────── */}
          {/* ─────────────────────────────────────────────────────────────
              TAB 2: AI CHAT (Coucou Single Unified Window with Mochi Companion)
              ───────────────────────────────────────────────────────────── */}
          {activeTab === 'chat' && (
            <div 
              className="flex-1 relative w-full h-full coucou-card-wash border border-white/10 rounded-2xl overflow-hidden flex flex-col text-left select-none animate-in fade-in duration-150"
              style={{
                '--wash': 'rgba(99, 102, 241, 0.16)'
              } as React.CSSProperties}
            >
              {/* Full-width Chat Body: full width without left indentation */}
              <div className="relative z-10 h-full flex flex-col justify-between px-3 py-2.5 gap-1.5">
                
                {/* 1. Context File Chip (when file is dropped/attached) */}
                {attachedFile && (
                  <div className="flex items-center gap-2 px-1 pt-0.5 flex-shrink-0">
                    <div className="coucou-chip">
                      <span className="coucou-chip-dot" />
                      <span className="font-semibold text-white truncate max-w-[260px] text-xs">
                        {attachedFile.name}
                      </span>
                      <span className="text-[10px] text-neutral-400 font-mono">
                        ({formatBytes(attachedFile.size)})
                      </span>
                      <button
                        type="button"
                        onClick={() => setAttachedFile(null)}
                        title="Remove file"
                        className="ml-1 text-neutral-400 hover:text-white cursor-pointer"
                      >
                        <CoucouIcon path={ICONS.xmark} size={9} />
                      </button>
                    </div>
                  </div>
                )}

                {/* 2. Full-Width Chat Log (Spacious, Wide Stream) */}
                <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-2.5 min-h-0">
                  {chatMessages.map((msg) => (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
                    >
                      {msg.sender === 'user' ? (
                        /* Coucou User Bubble */
                        <div className="bg-white/[0.12] border border-white/10 text-white rounded-2xl rounded-tr-xs px-3.5 py-1.5 text-xs font-sans leading-relaxed select-text shadow-sm max-w-[85%]">
                          {msg.text}
                        </div>
                      ) : (
                        /* Coucou Mochi Reply */
                        <div className="w-full text-xs font-sans text-neutral-100 select-text flex flex-col gap-1.5">
                          {msg.isLoading ? (
                            /* libraries.dev Thinking Orb live loader! */
                            <div className="flex items-center gap-2.5 py-1 text-cyan-300">
                              <ThinkingOrb
                                state={msg.isResearch ? "searching" : "breathing"}
                                size={20}
                                theme="dark"
                                aria-label="Mochi is thinking"
                              />
                              <span className="shimmer text-[11px] font-medium text-neutral-200">
                                {msg.isResearch ? `Searching the web for "${msg.researchQuery || 'topics'}"...` : "Thinking..."}
                              </span>
                            </div>
                          ) : (
                            <>
                              <MarkdownMessage content={msg.text} />

                              {/* Verified Sources */}
                              {msg.sources && msg.sources.length > 0 && (
                                <div className="mt-1 flex flex-wrap gap-1.5">
                                  {msg.sources.map((src, sIdx) => (
                                    <a
                                      key={sIdx}
                                      href={src.link}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      title={src.snippet || src.title}
                                      className="text-[9.5px] px-2 py-0.5 rounded-full bg-white/5 hover:bg-white/15 text-cyan-300 hover:text-white border border-white/10 flex items-center gap-1 transition"
                                    >
                                      <ExternalLink className="w-2.5 h-2.5 flex-shrink-0" />
                                      <span className="truncate max-w-[150px]">{src.title}</span>
                                    </a>
                                  ))}
                                </div>
                              )}

                              {/* RAG Knowledge Citations */}
                              {msg.citations && msg.citations.length > 0 && (
                                <div className="mt-1 flex flex-wrap gap-1">
                                  {msg.citations.map((cite, cIdx) => (
                                    <span
                                      key={cIdx}
                                      className="text-[9px] px-2 py-0.5 rounded-full bg-indigo-950/60 text-indigo-300 border border-indigo-500/30 font-mono tracking-tight flex items-center gap-1"
                                    >
                                      <FileText className="w-2.5 h-2.5 flex-shrink-0" />
                                      <span>{cite}</span>
                                    </span>
                                  ))}
                                </div>
                              )}

                              {/* Copy action */}
                              <div className="flex justify-end pt-0.5">
                                <button
                                  onClick={async () => {
                                    await api.copyToClipboard(msg.text);
                                    sounds.playComplete();
                                  }}
                                  title="Copy text"
                                  className="text-[10px] text-neutral-500 hover:text-neutral-300 px-1.5 py-0.5 rounded hover:bg-white/5 flex items-center gap-1 transition cursor-pointer"
                                >
                                  <CoucouIcon path={ICONS.copy} size={10} />
                                  <span>Copy</span>
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Global Loading Thinking Orb if pending message */}
                  {chatLoading && !chatMessages.some(m => m.isLoading) && (
                    <div className="flex items-center gap-2.5 py-1 text-cyan-300">
                      <ThinkingOrb state="breathing" size={20} theme="dark" aria-label="Mochi is thinking" />
                      <span className="shimmer text-[11px] font-medium text-neutral-300">Mochi is thinking...</span>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                {/* 3. Model Selector & Clear Action Row */}
                <div className="relative flex items-center justify-between px-1 flex-shrink-0">
                  {chatMessages.length > 1 ? (
                    <button
                      onClick={() => {
                        setChatMessages([{
                          id: 'welcome',
                          sender: 'mochi',
                          text: "Hi! I am Mochi, your Windows AI assistant. Ask me anything, or ask me to research topics on the web!",
                          timestamp: new Date()
                        }]);
                        sounds.playClick();
                      }}
                      title="Clear conversation"
                      className="text-[10px] text-neutral-500 hover:text-rose-300 flex items-center gap-1 transition px-1 py-0.5 rounded hover:bg-white/5 cursor-pointer"
                    >
                      <Trash2 className="w-2.5 h-2.5" />
                      <span>Clear</span>
                    </button>
                  ) : <div />}

                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setShowModelPicker(prev => !prev)}
                      className="coucou-model-btn text-[10px] py-0.5 px-2"
                      title="Switch provider or model"
                    >
                      <span 
                        className="w-1.5 h-1.5 rounded-full" 
                        style={{ background: MODEL_PROVIDERS.find(p => p.id === selectedProvider)?.accent || '#22d3ee' }} 
                      />
                      <span className="font-medium text-[10px]">
                        {selectedModel}
                      </span>
                      <CoucouIcon path={ICONS.chevronUpDown} size={9} className="opacity-60" />
                    </button>

                    {showModelPicker && (
                      <div className="absolute bottom-6 right-0 z-40 w-72 p-2 rounded-xl bg-[#16171b] border border-white/15 shadow-2xl flex flex-col gap-2">
                        {/* Provider Chips */}
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {MODEL_PROVIDERS.map(p => (
                            <button
                              key={p.id}
                              type="button"
                              onClick={() => {
                                setSelectedProvider(p.id as any);
                                setSelectedModel(p.models[0].id);
                                sounds.playClick();
                              }}
                              className={`px-2 py-0.5 rounded-full text-[10px] font-medium flex items-center gap-1 transition cursor-pointer ${
                                selectedProvider === p.id 
                                ? 'bg-white/20 text-white font-bold border border-white/25' 
                                : 'bg-white/5 text-neutral-400 hover:text-neutral-200 border border-white/5'
                              }`}
                            >
                              <span className="w-1.5 h-1.5 rounded-full" style={{ background: p.accent }} />
                              <span>{p.name}</span>
                            </button>
                          ))}
                        </div>

                        <div className="h-px bg-white/10 w-full" />

                        {/* Model List */}
                        <div className="flex flex-col gap-1 max-h-32 overflow-y-auto">
                          {MODEL_PROVIDERS.find(p => p.id === selectedProvider)?.models.map(m => (
                            <button
                              key={m.id}
                              type="button"
                              onClick={() => {
                                setSelectedModel(m.id);
                                setShowModelPicker(false);
                                sounds.playComplete();
                              }}
                              className={`w-full px-2 py-1 rounded-lg text-left text-[11px] flex items-center justify-between transition cursor-pointer ${
                                selectedModel === m.id
                                  ? 'bg-white/15 text-white font-semibold'
                                  : 'text-neutral-300 hover:bg-white/5 hover:text-white'
                              }`}
                            >
                              <span className="truncate">{m.label}</span>
                              {selectedModel === m.id && <Check className="w-3 h-3 text-cyan-400 flex-shrink-0" />}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* 4. Bottom Row: Mochi on Left + Reduced-Height Sleek Chat Bar */}
                <div className="flex items-center gap-2.5 flex-shrink-0">
                  {/* Bottom-left Mochi Companion */}
                  <div 
                    className="relative flex-shrink-0 group cursor-pointer flex items-center justify-center"
                    onClick={() => { setActiveTab('wardrobe'); sounds.playClick(); }}
                    title="Mochi Assistant (Click for Wardrobe Skins)"
                    onContextMenu={handleMochiContextMenu}
                  >
                    <Mochi
                      state={chatLoading ? 'thinking' : voiceMode === 'listening' ? 'listening' : 'idle'}
                      outfit={activeOutfit}
                      size={38}
                      badge={voiceActive ? 'bang' : 'dots'}
                    />
                  </div>

                  {/* Reduced Height Sleek Input Bar */}
                  <form
                    onSubmit={(e) => { e.preventDefault(); handleSendChat(); }}
                    className="flex-1 flex items-center gap-2 h-[32px] px-3 rounded-full bg-white/[0.06] border border-white/10 focus-within:border-white/20 focus-within:bg-white/[0.09] transition-all"
                  >
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder={isChatVoiceRecording ? "🎙️ Listening... Speak now..." : "Ask me anything…"}
                      spellCheck={false}
                      className="flex-1 min-w-0 bg-transparent text-[12px] text-white placeholder-neutral-500 focus:outline-none"
                    />

                    {/* Click-to-Speak Microphone button */}
                    <button
                      type="button"
                      onClick={handleToggleChatVoice}
                      title={isChatVoiceRecording ? "Stop voice listening" : "Click to speak voice message"}
                      className={`w-6 h-6 rounded-full flex items-center justify-center transition cursor-pointer flex-shrink-0 ${
                        isChatVoiceRecording 
                          ? 'bg-rose-500 text-white animate-pulse shadow-[0_0_12px_rgba(244,63,94,0.6)]' 
                          : 'bg-white/5 hover:bg-white/15 text-neutral-400 hover:text-white'
                      }`}
                    >
                      {isChatVoiceRecording ? (
                        <ThinkingOrb state="listening" size={20} theme="dark" aria-label="Listening" />
                      ) : (
                        <Mic className="w-3 h-3" />
                      )}
                    </button>

                    {/* Send Button: Coucou exact round white button with black up-arrow */}
                    <button
                      type="submit"
                      disabled={!chatInput.trim() || chatLoading}
                      title="Send"
                      className="w-6 h-6 rounded-full bg-white text-black hover:bg-neutral-200 disabled:opacity-35 flex items-center justify-center transition cursor-pointer flex-shrink-0 shadow-xs"
                    >
                      <CoucouIcon path={ICONS.arrowUp} size={10} />
                    </button>
                  </form>
                </div>
              </div>
            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────
              TAB 3: FULL EXPANDED TASKS (Height: 320px, No Clipping!)
              ───────────────────────────────────────────────────────────── */}
          {activeTab === 'tasks' && (
            <div className="flex-1 flex gap-3 overflow-hidden text-left">
              {/* Left Column: Mochi & Task Stats / Filters */}
              <div className="w-[175px] flex flex-col justify-between p-3 rounded-2xl bg-neutral-950/70 border border-white/5 flex-shrink-0">
                <div className="flex flex-col gap-2.5">
                  <div className="flex items-center gap-2">
                    <Mochi state="idle" outfit={activeOutfit} size={42} badge="dots" onContextMenu={handleMochiContextMenu} />
                    <div className="flex flex-col overflow-hidden">
                      <span className="text-xs font-bold text-white">Daily Tasks</span>
                      <span className="text-[10px] text-rose-400 font-semibold">{pendingTasksCount} pending</span>
                    </div>
                  </div>

                  {/* Task Filter Pills */}
                  <div className="flex items-center gap-1 p-1 rounded-xl bg-white/5 border border-white/5">
                    <button
                      onClick={() => setTaskFilter('all')}
                      className={`flex-1 py-1 text-[10px] font-medium rounded-lg transition cursor-pointer ${
                        taskFilter === 'all' ? 'bg-white/20 text-white' : 'text-neutral-400 hover:text-white'
                      }`}
                    >
                      All ({tasks.length})
                    </button>
                    <button
                      onClick={() => setTaskFilter('pending')}
                      className={`flex-1 py-1 text-[10px] font-medium rounded-lg transition cursor-pointer ${
                        taskFilter === 'pending' ? 'bg-white/20 text-white' : 'text-neutral-400 hover:text-white'
                      }`}
                    >
                      Pending
                    </button>
                    <button
                      onClick={() => setTaskFilter('completed')}
                      className={`flex-1 py-1 text-[10px] font-medium rounded-lg transition cursor-pointer ${
                        taskFilter === 'completed' ? 'bg-white/20 text-white' : 'text-neutral-400 hover:text-white'
                      }`}
                    >
                      Done
                    </button>
                  </div>
                </div>

                <div className="flex flex-col gap-1.5 pt-2 border-t border-white/5">
                  <button
                    onClick={() => { onOpenTasks(); sounds.playClick(); }}
                    className="flex items-center justify-between w-full text-[10px] text-neutral-300 hover:text-white px-2 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 transition cursor-pointer"
                  >
                    <span>Full Drawer</span>
                    <ExternalLink className="w-3 h-3 text-neutral-400" />
                  </button>
                  <button
                    onClick={() => { setActiveTab('overview'); sounds.playClick(); }}
                    className="text-[10px] text-neutral-400 hover:text-neutral-200 py-1 text-center cursor-pointer"
                  >
                    ← Back to Overview
                  </button>
                </div>
              </div>

              {/* Right Column: Full Proposal Box + Task Checklist */}
              <div className="flex-1 flex flex-col gap-2 p-3 rounded-2xl bg-[#141518] border border-white/8 overflow-hidden">
                
                {/* 1. Full unclipped Task Proposal Box if present */}
                {taskProposal && (
                  <div className="flex flex-col gap-1.5 p-3 rounded-xl bg-gradient-to-r from-blue-950/90 to-indigo-950/80 border border-blue-500/40 animate-in fade-in duration-200 shadow-md">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-[10px] font-bold text-blue-300 uppercase tracking-wide">
                        <Sparkles className="w-3.5 h-3.5 text-blue-400 animate-pulse" />
                        Task Proposal from {taskProposal.sender || 'Teams'}
                      </span>
                      <span className="text-[9px] px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-200 font-mono font-bold">
                        {taskProposal.priority || 'High Priority'}
                      </span>
                    </div>

                    <div className="text-xs font-bold text-white leading-snug">
                      {taskProposal.title}
                    </div>

                    {taskProposal.description && (
                      <div className="text-[11px] text-neutral-300 leading-relaxed max-h-[55px] overflow-y-auto pr-1">
                        {taskProposal.description}
                      </div>
                    )}

                    <div className="flex items-center gap-2 pt-1 border-t border-white/10">
                      <button
                        onClick={onAcceptProposal}
                        className="flex items-center gap-1 px-3 py-1 rounded-full bg-white text-black hover:bg-neutral-200 text-xs font-bold transition cursor-pointer active:scale-95 shadow"
                      >
                        <Check className="w-3.5 h-3.5 stroke-[3]" />
                        <span>Add to Tasks</span>
                      </button>
                      <button
                        onClick={onDismissProposal}
                        className="px-2.5 py-1 rounded-full bg-white/10 hover:bg-white/15 text-neutral-300 text-xs font-medium transition cursor-pointer"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}

                {/* 2. Quick Add Task Form with Timer Selection */}
                <form onSubmit={handleCreateTask} className="flex flex-col gap-1.5 pb-2 border-b border-white/5 flex-shrink-0">
                  <div className="flex items-center gap-1.5">
                    <input
                      type="text"
                      value={newTaskTitle}
                      onChange={(e) => setNewTaskTitle(e.target.value)}
                      placeholder="Type task description & press Enter..."
                      className="flex-1 bg-white/5 border border-white/10 rounded-full px-3 py-1.5 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-white/30"
                    />
                    <button
                      type="submit"
                      disabled={!newTaskTitle.trim() || creatingTask}
                      className="px-3 py-1.5 rounded-full bg-white text-black hover:bg-neutral-200 text-xs font-semibold disabled:opacity-40 transition cursor-pointer flex-shrink-0"
                    >
                      Add Task
                    </button>
                  </div>

                  {/* Timer interval selection on create task */}
                  <div className="flex items-center justify-between px-1 text-[10px]">
                    <span className="flex items-center gap-1 text-neutral-400 font-medium">
                      <Clock className="w-3 h-3 text-amber-400" />
                      Remind every:
                    </span>
                    <div className="flex items-center gap-1">
                      {[2, 5, 15, 30, 60].map((mins) => (
                        <button
                          type="button"
                          key={mins}
                          onClick={() => setNewTaskInterval(mins)}
                          className={`px-2 py-0.5 rounded-full font-medium transition cursor-pointer ${
                            newTaskInterval === mins
                              ? 'bg-amber-400 text-black font-semibold shadow-xs'
                              : 'bg-white/5 text-neutral-400 hover:bg-white/10 hover:text-white'
                          }`}
                        >
                          {mins}m
                        </button>
                      ))}
                    </div>
                  </div>
                </form>

                {/* 3. Scrollable Tasks Checklist */}
                <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-1.5">
                  {filteredTasks.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center py-6 text-neutral-500">
                      <span className="text-xs">No tasks match this filter.</span>
                      <span className="text-[10px] text-neutral-600 mt-1">Add a quick task above or let Teams auto-detect one!</span>
                    </div>
                  ) : (
                    filteredTasks.map((t) => (
                      <div 
                        key={t.id} 
                        className="flex items-center justify-between px-2.5 py-2 rounded-xl bg-white/5 hover:bg-white/10 transition group text-xs border border-white/5"
                      >
                        <div 
                          onClick={() => handleToggleTask(t.id)}
                          className="flex items-center gap-2.5 cursor-pointer overflow-hidden flex-1 mr-2"
                        >
                          <div className={`w-4 h-4 rounded-full border flex items-center justify-center transition-all ${
                            t.status === 'completed' 
                              ? 'bg-emerald-500 border-emerald-500 text-black' 
                              : 'border-white/30 hover:border-white/60'
                          }`}>
                            {t.status === 'completed' && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                          </div>
                          <span className={`truncate text-xs font-medium ${
                            t.status === 'completed' ? 'line-through text-neutral-500' : 'text-neutral-100'
                          }`}>
                            {t.title}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5 flex-shrink-0 relative">
                          {/* Interactive Timer Badge - click to change timer after creation */}
                          <div className="relative">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditingTaskIntervalId(editingTaskIntervalId === t.id ? null : t.id);
                              }}
                              title={`Reminds every ${t.reminder_interval_mins || 30}m. Click to change timer.`}
                              className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-mono transition cursor-pointer border ${
                                editingTaskIntervalId === t.id
                                  ? 'bg-amber-400 text-black border-amber-400 font-semibold'
                                  : 'bg-amber-400/10 hover:bg-amber-400/20 text-amber-300 border-amber-400/20'
                              }`}
                            >
                              <Clock className="w-2.5 h-2.5" />
                              <span>{t.reminder_interval_mins || 30}m</span>
                            </button>

                            {/* Dropdown to adjust timer after creation */}
                            {editingTaskIntervalId === t.id && (
                              <div 
                                className="absolute right-0 bottom-full mb-1.5 z-40 flex items-center gap-1 bg-[#18191e] border border-white/20 rounded-xl p-1 shadow-2xl backdrop-blur-md"
                                onClick={(e) => e.stopPropagation()}
                              >
                                {[2, 5, 15, 30, 60].map((mins) => (
                                  <button
                                    key={mins}
                                    type="button"
                                    onClick={() => {
                                      handleUpdateTaskInterval(t.id, mins);
                                      setEditingTaskIntervalId(null);
                                    }}
                                    className={`px-1.5 py-0.5 text-[9px] rounded-lg font-medium transition cursor-pointer ${
                                      (t.reminder_interval_mins || 30) === mins
                                        ? 'bg-amber-400 text-black font-bold'
                                        : 'text-neutral-300 hover:text-white hover:bg-white/10'
                                    }`}
                                  >
                                    {mins}m
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Quick +5m Extend Button */}
                          <button
                            type="button"
                            onClick={async (e) => {
                              e.stopPropagation();
                              sounds.playClick();
                              await api.extendTask(t.id, 5);
                              onTasksRefresh();
                            }}
                            title="Add +5 minutes to reminder timer"
                            className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-md bg-white/5 hover:bg-amber-400/20 text-neutral-400 hover:text-amber-300 text-[10px] font-mono transition cursor-pointer border border-white/5 hover:border-amber-400/30 active:scale-95"
                          >
                            <Plus className="w-2.5 h-2.5 stroke-[2.5]" />
                            <span>5m</span>
                          </button>

                          {t.source && (
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-neutral-400 font-mono">
                              {t.source.replace('teams_', '')}
                            </span>
                          )}
                          <button
                            onClick={() => handleDeleteTask(t.id)}
                            title="Delete task"
                            className="opacity-0 group-hover:opacity-100 text-neutral-500 hover:text-rose-400 p-1 transition cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>

              </div>
            </div>
          )}

          {/* ─────────────────────────────────────────────────────────────
              TAB 4: COUCOU WARDROBE (Skins & Outfits)
              ───────────────────────────────────────────────────────────── */}
          {activeTab === 'wardrobe' && (() => {
            const displayedOutfitSel: OutfitSelection = hoveredSelection ?? (currentOutfit || 'auto');
            const displayedOutfitLabel = displayedOutfitSel === 'none' 
              ? 'Clean Mochi' 
              : (OUTFIT_LABELS[displayedOutfitSel] || displayedOutfitSel);

            return (
              <div className="flex-1 flex gap-3 overflow-hidden text-left">
                {/* Left Column: Interactive Avatar Display with all names & info */}
                <div className="w-[190px] flex flex-col justify-between p-3 rounded-2xl bg-[#141518] border border-white/8 flex-shrink-0 items-center text-center">
                  {/* Top: Wardrobe Title + 13 Skins Badge */}
                  <div className="flex items-center justify-between w-full pb-1.5 border-b border-white/5 px-0.5">
                    <span className="text-xs font-bold text-white tracking-wide">
                      Wardrobe
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/10 text-neutral-300 font-mono">
                      13 Skins
                    </span>
                  </div>

                  {/* Center: Mochi Avatar preview + Skin Name & Status */}
                  <div className="flex flex-col items-center gap-1.5 py-1">
                    <div className="relative group">
                      <Mochi
                        state="idle"
                        outfit={activeOutfit}
                        size={54}
                        badge="dots"
                        onContextMenu={handleMochiContextMenu}
                      />
                    </div>
                    <div className="flex flex-col items-center max-w-full px-1">
                      <span className="text-xs font-bold text-white capitalize truncate max-w-[170px]" title={displayedOutfitLabel}>
                        {displayedOutfitLabel}
                      </span>
                      <span className="text-[10px] text-amber-300/90 font-medium truncate max-w-[170px]">
                        {hoveredSelection 
                          ? '✨ Previewing Skin' 
                          : (currentOutfit === 'auto' 
                              ? `Auto (${OUTFIT_LABELS[seasonalOutfit(new Date())] || 'Season'})` 
                              : 'Active Outfit')}
                      </span>
                    </div>
                  </div>

                  {/* Bottom: Back to Home Button (No extra text/words) */}
                  <div className="w-full pt-1.5 border-t border-white/5">
                    <button
                      onClick={() => { setActiveTab('overview'); sounds.playClick(); }}
                      className="w-full py-1 text-[11px] font-semibold rounded-xl bg-white/10 hover:bg-white/20 text-neutral-200 hover:text-white transition cursor-pointer flex items-center justify-center gap-1"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                      <span>Back to Home</span>
                    </button>
                  </div>
                </div>

                {/* Right Column: Clean Grid with all 13 skins visible without scrolling */}
                <div className="flex-1 flex overflow-hidden">
                  <WardrobePicker
                    currentOutfit={currentOutfit || 'auto'}
                    onSelectOutfit={(sel) => {
                      onSelectOutfit?.(sel);
                      setPreviewOutfit(null);
                      setHoveredSelection(null);
                    }}
                    onPreviewOutfit={(preview) => {
                      setPreviewOutfit(preview);
                    }}
                    onHoverSelection={(sel) => {
                      setHoveredSelection(sel);
                    }}
                  />
                </div>
              </div>
            );
          })()}
          </>
          )}

        </div>
      )}

    </div>
  );
};

export default CoucouIsland;
