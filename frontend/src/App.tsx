import { useState, useEffect } from 'react';
import { CoucouIsland } from './components/CoucouIsland';
import { TeamsCallPrompt } from './components/TeamsCallPrompt';
import { EODModal } from './components/EODModal';
import { TasksDrawer } from './components/TasksDrawer';
import { NewsDrawer } from './components/NewsDrawer';
import { SettingsModal } from './components/SettingsModal';
import type { ActivityInfo, TaskItem, VisionResult, ReplySuggestion } from './types';
import { api } from './api';
import { voice } from './utils/voice';
import { sounds } from './utils/sound';

import { parseOutfit, type OutfitSelection } from './coucou/mochi/wardrobe';

export function App() {
  const [activity, setActivity] = useState<ActivityInfo>({
    app: 'Ready',
    title: 'Connecting to Windows Tracker...',
    duration: 0
  });
  const [inMeeting, setInMeeting] = useState(false);
  const [meetingSubject, setMeetingSubject] = useState('');
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  
  // Coucou Island expanded/compact state & dynamic height
  const [isExpanded, setIsExpanded] = useState(false);
  const [islandHeight, setIslandHeight] = useState(210);

  // Mochi Wardrobe outfit selection (persisted)
  const [currentOutfit, setCurrentOutfit] = useState<OutfitSelection>(() => {
    try {
      const saved = localStorage.getItem('mochi_outfit');
      return parseOutfit(saved);
    } catch {
      return 'auto';
    }
  });

  const [targetTab, setTargetTab] = useState<'overview' | 'chat' | 'tasks' | 'wardrobe' | null>(null);

  // Teams auto-detected task proposal
  const [taskProposal, setTaskProposal] = useState<{
    title: string;
    sender?: string;
    description?: string;
    priority?: string;
  } | null>(null);

  // Proactive task reminder
  const [activeReminder, setActiveReminder] = useState<{
    task: TaskItem;
    title: string;
    message?: string;
  } | null>(null);

  // Screen Vision & Reply Suggestion state
  const [visionResult, setVisionResult] = useState<VisionResult | null>(null);
  const [replySuggestion, setReplySuggestion] = useState<ReplySuggestion | null>(null);
  const [isAnalyzingScreen, setIsAnalyzingScreen] = useState(false);

  // Latest Voice Assistant interaction & Web Research state
  const [latestVoiceData, setLatestVoiceData] = useState<{
    userText?: string;
    replyText?: string;
    action?: string;
    detailedAnswer?: string;
    searchResults?: any[];
  } | null>(null);

  const [activeResearch, setActiveResearch] = useState<{
    status: 'searching' | 'completed';
    query: string;
    userText?: string;
    detailedAnswer?: string;
    spokenReply?: string;
    results?: any[];
  } | null>(null);

  // Modals & Drawers state
  const [showCallPrompt, setShowCallPrompt] = useState(false);
  const [endedCallSubject, setEndedCallSubject] = useState('');
  const [showEOD, setShowEOD] = useState(false);
  const [showTasks, setShowTasks] = useState(false);
  const [showNews, setShowNews] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const isModalOpen = showCallPrompt || showEOD || showTasks || showNews || showSettings;

  // Manage Native Window Height dynamically so it NEVER blocks space below
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    if (isModalOpen) {
      // Modal open: Expand window to show content
      api.resizeWindow(860, 680);
    } else if (isExpanded) {
      // Expanded Coucou Island: provide exact required canvas height (210 or 320)
      api.resizeWindow(680, islandHeight);
    } else {
      // Collapsing: Wait 300ms for the 280ms CSS transition to finish shrinking to 36px
      // before shrinking the native window. Prevents any clipping or stutter!
      timer = setTimeout(() => {
        api.resizeWindow(680, 36);
      }, 300);
    }
    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [isModalOpen, isExpanded, islandHeight]);

  useEffect(() => {
    loadTasks();
    setupWebSocket();
    const interval = setInterval(loadTasks, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadTasks = async () => {
    try {
      const data = await api.getTasks();
      setTasks(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleTriggerVision = async () => {
    setIsAnalyzingScreen(true);
    setVisionResult(null);
    setReplySuggestion(null);
    setIsExpanded(true);
    sounds.playExpand();
    try {
      await api.analyzeScreen();
    } catch (e) {
      console.error('[Vision Analysis Trigger Error]', e);
      setIsAnalyzingScreen(false);
      sounds.playError();
    }
  };

  const setupWebSocket = () => {
    const connect = () => {
      const ws = new WebSocket('ws://127.0.0.1:8765/ws');

      ws.onopen = () => {
        console.log('[WS] Connected to Assistant server');
      };

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'ACTIVITY_TICK') {
            setActivity(payload.data);
          } else if (payload.type === 'TEAMS_CALL_STARTED') {
            setInMeeting(true);
            setMeetingSubject(payload.data.subject);
          } else if (payload.type === 'TEAMS_CALL_ENDED') {
            setInMeeting(false);
            setEndedCallSubject(payload.data.subject);
            setShowCallPrompt(true);
          } else if (payload.type === 'TEAMS_TASK_PROPOSAL') {
            const taskData = payload.data;
            setTaskProposal(taskData);
            // Non-intrusive notification: do not speak over the user
          } else if (payload.type === 'TASK_REMINDER') {
            const reminder = payload.data;
            setActiveReminder(reminder);
            setReplySuggestion(null);
            setVisionResult(null);
            setIsExpanded(true);
            sounds.playNotification();
          } else if (payload.type === 'RESEARCH_STARTED') {
            const d = payload.data;
            setActiveResearch({
              status: 'searching',
              query: d.query,
              userText: d.user_text || d.query
            });
            setLatestVoiceData(prev => ({
              ...prev,
              userText: d.user_text || d.query,
              replyText: `Searching web for "${d.query}"...`,
              action: 'web_search'
            }));
            setIsExpanded(true);
            setTargetTab('chat');
            sounds.playExpand();
          } else if (payload.type === 'RESEARCH_COMPLETED') {
            const d = payload.data;
            setActiveResearch({
              status: 'completed',
              query: d.query,
              userText: d.user_text,
              detailedAnswer: d.detailed_answer,
              spokenReply: d.spoken_reply,
              results: d.results
            });
            setLatestVoiceData({
              userText: d.user_text || d.query,
              replyText: d.spoken_reply || "Here is what I found on the web.",
              action: 'web_search',
              detailedAnswer: d.detailed_answer,
              searchResults: d.results
            });
            setIsExpanded(true);
            setTargetTab('chat');
            if (d.spoken_reply) {
              voice.speak(d.spoken_reply);
            }
          } else if (payload.type === 'JARVIS_VOICE_RESULT') {
            const data = payload.data;
            if (data) {
              setLatestVoiceData({
                userText: data.user_text || '',
                replyText: data.reply || '',
                action: data.action,
                detailedAnswer: data.detailed_answer,
                searchResults: data.search_results
              });
              if (data.action === 'web_search' || data.detailed_answer) {
                setTargetTab('chat');
              }
              if (data.reply) {
                setIsExpanded(true);
                sounds.playExpand();
                voice.speak(data.reply);
              }
            }
            if (data && data.outfit) {
              setCurrentOutfit(data.outfit);
              try { localStorage.setItem('mochi_outfit', data.outfit); } catch {}
            }
            if (data && data.drawer) {
              const d = data.drawer.toLowerCase();
              if (d === 'tasks') setShowTasks(true);
              else if (d === 'wardrobe') { setTargetTab('wardrobe'); setIsExpanded(true); }
              else if (d === 'settings') setShowSettings(true);
              else if (d === 'eod') setShowEOD(true);
              else if (d === 'news') setShowNews(true);
            }
            if (data && (data.action === 'create_task' || data.action === 'complete_task' || data.action === 'delete_task' || data.action === 'delete_all_tasks' || data.action === 'update_task' || data.action === 'summarize_meeting_notes')) {
              loadTasks();
              sounds.playComplete();
            }
          } else if (payload.type === 'SET_OUTFIT') {
            const outfit = payload.data?.outfit;
            if (outfit) {
              setCurrentOutfit(outfit);
              try { localStorage.setItem('mochi_outfit', outfit); } catch {}
            }
          } else if (payload.type === 'OPEN_DRAWER') {
            const d = (payload.data?.drawer || '').toLowerCase();
            if (d === 'tasks') setShowTasks(true);
            else if (d === 'wardrobe') { setTargetTab('wardrobe'); setIsExpanded(true); }
            else if (d === 'settings') setShowSettings(true);
            else if (d === 'eod') setShowEOD(true);
            else if (d === 'news') setShowNews(true);
          } else if (payload.type === 'COLLAPSE_NOTCH') {
            setIsExpanded(false);
          } else if (payload.type === 'TASK_CREATED' || payload.type === 'TASK_UPDATED' || payload.type === 'TASK_DELETED' || payload.type === 'ALL_TASKS_DELETED') {
            loadTasks();
          } else if (payload.type === 'VISION_ANALYSIS_READY') {
            setVisionResult(payload.data);
            setReplySuggestion(null);
            setActiveReminder(null);
            setIsAnalyzingScreen(false);
            setIsExpanded(true);
            sounds.playExpand();
          } else if (payload.type === 'REPLY_SUGGESTION_READY') {
            setReplySuggestion(payload.data);
            setVisionResult(null);
            setActiveReminder(null);
            setIsExpanded(true);
            sounds.playExpand();
          } else if (payload.type === 'TRIGGER_SCREEN_VISION') {
            handleTriggerVision();
          } else if (payload.type === 'TRIGGER_VOICE_TOGGLE') {
            voice.toggleListening();
          } else if (payload.type === 'INITIAL_STATE') {
            if (payload.data.tracker) setActivity(payload.data.tracker);
            setInMeeting(payload.data.in_meeting);
          }
        } catch (e) {
          console.error('[WS Parse Error]', e);
        }
      };

      ws.onclose = () => {
        setTimeout(connect, 3000);
      };
    };

    connect();
  };

  const handleSimulateCall = async () => {
    try {
      await api.simulateCallEnd();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAcceptTaskProposal = async () => {
    if (!taskProposal) return;
    sounds.playClick();
    try {
      await api.createTask({
        title: taskProposal.title,
        description: taskProposal.description || '',
        source: `teams_${taskProposal.sender || 'chat'}`
      });
      setTaskProposal(null);
      loadTasks();
      sounds.playComplete();
      voice.speak("Task added to your list.");
    } catch (err) {
      console.error(err);
    }
  };

  const handleDismissTaskProposal = () => {
    setTaskProposal(null);
    sounds.playClick();
  };

  const pendingCount = tasks.filter(t => t.status === 'pending').length;

  return (
    <div className="w-full h-full bg-transparent p-0 m-0 flex flex-col items-center justify-start select-none font-sans overflow-hidden">
      
      {/* Coucou Style Dynamic Island Notch */}
      <CoucouIsland
        activity={activity}
        inMeeting={inMeeting}
        meetingSubject={meetingSubject}
        pendingTasksCount={pendingCount}
        tasks={tasks}
        onTasksRefresh={loadTasks}
        taskProposal={taskProposal}
        onAcceptProposal={handleAcceptTaskProposal}
        onDismissProposal={handleDismissTaskProposal}
        activeReminder={activeReminder}
        onDismissReminder={() => setActiveReminder(null)}
        isExpanded={isExpanded}
        onExpand={() => setIsExpanded(true)}
        onCollapse={() => setIsExpanded(false)}
        onOpenEOD={() => setShowEOD(true)}
        onOpenTasks={() => setShowTasks(true)}
        onOpenSettings={() => setShowSettings(true)}
        onSimulateCall={handleSimulateCall}
        currentOutfit={currentOutfit}
        onSelectOutfit={(sel) => {
          setCurrentOutfit(sel);
          try {
            localStorage.setItem('mochi_outfit', sel);
          } catch {}
        }}
        onHeightChange={(h) => setIslandHeight(h)}
        targetTab={targetTab}
        visionResult={visionResult}
        replySuggestion={replySuggestion}
        isAnalyzingScreen={isAnalyzingScreen}
        onDismissVision={() => setVisionResult(null)}
        onDismissReply={() => setReplySuggestion(null)}
        onTriggerVision={handleTriggerVision}
        latestVoiceData={latestVoiceData}
        activeResearch={activeResearch}
        onClearResearch={() => setActiveResearch(null)}
        onClearVoiceData={() => setLatestVoiceData(null)}
      />

      {/* Teams Call Follow-up Prompt Modal */}
      {showCallPrompt && (
        <TeamsCallPrompt
          subject={endedCallSubject}
          onClose={() => setShowCallPrompt(false)}
          onTaskCreated={() => {
            loadTasks();
            setShowTasks(true);
          }}
        />
      )}

      {/* End of Day Modal */}
      {showEOD && (
        <EODModal
          onClose={() => setShowEOD(false)}
          onTasksUpdated={loadTasks}
        />
      )}

      {/* Tasks & Follow-up Reminders Drawer */}
      {showTasks && (
        <TasksDrawer
          tasks={tasks}
          onClose={() => setShowTasks(false)}
          onRefresh={loadTasks}
        />
      )}

      {/* News & Tech Radar Drawer */}
      {showNews && (
        <NewsDrawer
          onClose={() => setShowNews(false)}
          activeApp={activity.app}
        />
      )}

      {/* Settings Modal */}
      {showSettings && (
        <SettingsModal
          onClose={() => setShowSettings(false)}
        />
      )}

    </div>
  );
}

export default App;
