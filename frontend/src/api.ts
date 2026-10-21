import type { TaskItem, EODTaskProposal, NewsArticle, AppSettings, ActivityLog, AppSummary, OutlookAttentionItem, ProjectInfo } from './types';

const BASE_URL = 'http://127.0.0.1:8765';

let accumDx = 0;
let accumDy = 0;
let moveRafPending = false;
let moveInFlight = false;
let activeWs: WebSocket | null = null;

export const api = {
  registerWebSocket(ws: WebSocket | null) {
    activeWs = ws;
  },
  async getStatus() {
    const res = await fetch(`${BASE_URL}/api/status`);
    return res.json();
  },

  async getActivities(): Promise<ActivityLog[]> {
    const res = await fetch(`${BASE_URL}/api/activities/today`);
    return res.json();
  },

  async getAppSummary(): Promise<AppSummary[]> {
    const res = await fetch(`${BASE_URL}/api/activities/summary`);
    return res.json();
  },

  async getTasks(): Promise<TaskItem[]> {
    const res = await fetch(`${BASE_URL}/api/tasks`);
    return res.json();
  },

  async createTask(data: { title: string; description?: string; source?: string; reminder_interval_mins?: number }): Promise<{ success: boolean; task_id: number }> {
    const res = await fetch(`${BASE_URL}/api/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return res.json();
  },

  async toggleTask(id: number): Promise<{ success: boolean; status: string }> {
    const res = await fetch(`${BASE_URL}/api/tasks/${id}/toggle`, { method: 'POST' });
    return res.json();
  },

  async updateTaskInterval(id: number, reminder_interval_mins: number): Promise<{ success: boolean; reminder_interval_mins: number }> {
    const res = await fetch(`${BASE_URL}/api/tasks/${id}/interval`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reminder_interval_mins })
    });
    return res.json();
  },

  async extendTask(id: number, mins: number = 5): Promise<{ success: boolean; task_id: number; new_interval_mins: number; extended_mins: number }> {
    const res = await fetch(`${BASE_URL}/api/tasks/${id}/extend`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mins })
    });
    return res.json();
  },

  async deleteTask(id: number): Promise<{ success: boolean }> {
    const res = await fetch(`${BASE_URL}/api/tasks/${id}`, { method: 'DELETE' });
    return res.json();
  },

  async deleteAllTasks(): Promise<{ success: boolean; count: number }> {
    const res = await fetch(`${BASE_URL}/api/tasks`, { method: 'DELETE' });
    return res.json();
  },

  async generateEOD(): Promise<{ tasks: EODTaskProposal[] }> {
    const res = await fetch(`${BASE_URL}/api/eod/generate`, { method: 'POST' });
    return res.json();
  },

  async askChat(
    message: string, 
    fileContext?: { name: string; content: string } | null, 
    model?: string
  ): Promise<{ reply: string; sources?: Array<{ title: string; link: string; snippet?: string }>; citations?: string[]; is_research?: boolean }> {
    const res = await fetch(`${BASE_URL}/api/chat/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message,
        file_name: fileContext?.name,
        file_content: fileContext?.content,
        model
      })
    });
    return res.json();
  },

  async uploadRAGDocument(fileName: string, fileContent: string, fileBase64?: string): Promise<{ success: boolean; doc_ref: string; chunk_count: number }> {
    const res = await fetch(`${BASE_URL}/api/rag/upload`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_name: fileName, file_content: fileContent, file_base64: fileBase64 })
    });
    return res.json();
  },

  async listRAGDocuments(): Promise<{ documents: Array<{ doc_ref: string; title: string; chunk_count: number }> }> {
    const res = await fetch(`${BASE_URL}/api/rag/documents`);
    return res.json();
  },


  async processVoice(query?: string, audioBlob?: Blob): Promise<{ reply: string; action?: string; data?: any }> {
    let audio_base64: string | undefined = undefined;
    if (audioBlob) {
      const buffer = await audioBlob.arrayBuffer();
      let binary = '';
      const bytes = new Uint8Array(buffer);
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      audio_base64 = btoa(binary);
    }
    const res = await fetch(`${BASE_URL}/api/voice/process`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, audio_base64, mime_type: audioBlob?.type || 'audio/webm' })
    });
    return res.json();
  },

  async listenOnce(): Promise<{ success: boolean; text?: string; reply?: string; error?: string }> {
    const res = await fetch(`${BASE_URL}/api/voice/listen-once`, { method: 'POST' });
    return res.json();
  },

  async getProactiveUpdate(): Promise<{ reply: string }> {
    const res = await fetch(`${BASE_URL}/api/assistant/proactive-update`, { method: 'POST' });
    return res.json();
  },

  async pushToDevOps(tasks: EODTaskProposal[], workItemType: string = 'Task'): Promise<{ results: any[] }> {
    const res = await fetch(`${BASE_URL}/api/eod/push-devops`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tasks, work_item_type: workItemType })
    });
    return res.json();
  },

  async getNews(): Promise<{ articles: NewsArticle[] }> {
    const res = await fetch(`${BASE_URL}/api/news`);
    return res.json();
  },

  async getSettings(): Promise<AppSettings> {
    const res = await fetch(`${BASE_URL}/api/settings`);
    return res.json();
  },

  async updateSettings(settings: AppSettings): Promise<{ success: boolean }> {
    const res = await fetch(`${BASE_URL}/api/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ settings })
    });
    return res.json();
  },

  async simulateCallEnd(): Promise<{ success: boolean }> {
    const res = await fetch(`${BASE_URL}/api/teams/simulate-call-end`, { method: 'POST' });
    return res.json();
  },

  async simulateTeamsTask(): Promise<{ success: boolean; task: any }> {
    const res = await fetch(`${BASE_URL}/api/teams/simulate-task`, { method: 'POST' });
    return res.json();
  },

  async analyzeTeamsText(text: string, sender: string = 'Teams', userName: string = 'Dhiraj'): Promise<{ success: boolean; tasks?: any[]; count?: number; message?: string }> {
    const res = await fetch(`${BASE_URL}/api/teams/analyze-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, sender, user_name: userName })
    });
    return res.json();
  },

  async scanTeamsScreen(userName: string = 'Dhiraj'): Promise<{ success: boolean; tasks?: any[]; count?: number; message?: string }> {
    const res = await fetch(`${BASE_URL}/api/teams/scan-screen`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_name: userName })
    });
    return res.json();
  },

  async resizeWindow(width: number, height: number): Promise<{ success: boolean }> {
    try {
      const res = await fetch(`${BASE_URL}/api/window/resize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ width, height })
      });
      return res.json();
    } catch {
      return { success: false };
    }
  },

  async moveWindow(dx: number, dy: number): Promise<{ success: boolean }> {
    accumDx += dx;
    accumDy += dy;
    if (!moveRafPending) {
      moveRafPending = true;
      requestAnimationFrame(async () => {
        moveRafPending = false;
        const sendX = accumDx;
        const sendY = accumDy;
        if (sendX === 0 && sendY === 0) return;
        accumDx = 0;
        accumDy = 0;

        // Try direct ultra-low-latency WebSocket first (<1ms)
        if (activeWs && activeWs.readyState === WebSocket.OPEN) {
          try {
            activeWs.send(JSON.stringify({ type: 'WINDOW_MOVE', dx: sendX, dy: sendY }));
            return;
          } catch {}
        }

        // Guarded HTTP POST fallback: avoid overlapping concurrent requests
        if (!moveInFlight) {
          moveInFlight = true;
          try {
            await fetch(`${BASE_URL}/api/window/move`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ dx: sendX, dy: sendY })
            });
          } catch {} finally {
            moveInFlight = false;
          }
        }
      });
    }
    return { success: true };
  },

  async snapTop(): Promise<{ success: boolean }> {
    if (activeWs && activeWs.readyState === WebSocket.OPEN) {
      try {
        activeWs.send(JSON.stringify({ type: 'WINDOW_SNAP_TOP' }));
        return { success: true };
      } catch {}
    }
    try {
      const res = await fetch(`${BASE_URL}/api/window/snap-top`, { method: 'POST' });
      return res.json();
    } catch {
      return { success: false };
    }
  },

  async quitApp(): Promise<{ success: boolean }> {
    try {
      const res = await fetch(`${BASE_URL}/api/app/quit`, { method: 'POST' });
      return res.json();
    } catch {
      return { success: false };
    }
  },

  async searchWeb(query: string, maxResults: number = 5): Promise<{ results: any[]; formatted: string }> {
    const res = await fetch(`${BASE_URL}/api/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, max_results: maxResults })
    });
    return res.json();
  },

  async analyzeScreen(query: string = "Inspect active screen", focus: string = "general", mode: string = "fullscreen", delay: number = 0): Promise<{ analysis: any }> {
    const res = await fetch(`${BASE_URL}/api/vision/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, focus, mode, delay })
    });
    return res.json();
  },

  async rephraseMessage(incomingText: string, draft: string = "", tone: string = "professional", targetApp: string = "teams"): Promise<{ reply: string; original?: string; explanation: string }> {
    const res = await fetch(`${BASE_URL}/api/assistant/rephrase`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ incoming_text: incomingText, draft, tone, target_app: targetApp })
    });
    return res.json();
  },

  async rephraseScreen(query: string = "rephrase it", draft: string = "", tone: string = "polished"): Promise<{ reply: string; original?: string; explanation?: string; tone?: string; copied_to_clipboard?: boolean }> {
    const res = await fetch(`${BASE_URL}/api/assistant/rephrase-screen`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, draft, tone })
    });
    return res.json();
  },

  async setApprovalQuota(quota: number = 10): Promise<{ success: boolean; remaining_quota: number; message: string }> {
    const res = await fetch(`${BASE_URL}/api/approvals/set-quota`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quota })
    });
    return res.json();
  },

  async approveCurrent(): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/approvals/approve-current`, { method: 'POST' });
    return res.json();
  },

  async getApprovalStatus(): Promise<{ remaining_quota: number; is_monitoring: boolean; total_approved: number }> {
    const res = await fetch(`${BASE_URL}/api/approvals/status`);
    return res.json();
  },

  async copyToClipboard(text: string): Promise<boolean> {
    // 1. First: Call native backend Win32 endpoint (100% reliable in desktop PySide6 app)
    try {
      const res = await fetch(`${BASE_URL}/api/clipboard/copy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const data = await res.json();
      if (data.success) return true;
    } catch {}

    // 2. Browser navigator.clipboard fallback
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch {}

    // 3. Textarea execCommand fallback
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '-9999px';
      textarea.setAttribute('readonly', '');
      document.body.appendChild(textarea);
      textarea.select();
      textarea.setSelectionRange(0, 99999);
      const successful = document.execCommand('copy');
      document.body.removeChild(textarea);
      if (successful) return true;
    } catch {}

    return false;
  },

  async getProjects(): Promise<ProjectInfo[]> {
    const res = await fetch(`${BASE_URL}/api/projects`);
    return res.json();
  },

  async getOutlookAttention(): Promise<OutlookAttentionItem[]> {
    const res = await fetch(`${BASE_URL}/api/outlook/attention`);
    return res.json();
  },

  async dismissOutlookAttention(id: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/outlook/dismiss/${id}`, { method: 'POST' });
    return res.json();
  },

  async syncOutlook(): Promise<any> {
    const res = await fetch(`${BASE_URL}/api/outlook/sync`, { method: 'POST' });
    return res.json();
  }
};
