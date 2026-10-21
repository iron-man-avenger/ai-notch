export interface ActivityInfo {
  app: string;
  raw_app?: string;
  title: string;
  duration: number;
  session_duration?: number;
}

export interface ActivityLog {
  app_name: string;
  window_title: string;
  total_seconds: number;
  last_seen?: string;
}

export interface AppSummary {
  app_name: string;
  total_seconds: number;
}

export interface TaskItem {
  id: number;
  title: string;
  description: string;
  source: 'manual' | 'teams_call' | 'eod_gemini' | string;
  status: 'pending' | 'completed';
  reminder_interval_mins: number;
  devops_id?: string;
  created_at: string;
}

export interface TaskProposalItem {
  title: string;
  description?: string;
  project?: string;
  priority?: string;
  sender?: string;
  source?: string;
}

export interface TaskProposalData {
  title: string;
  description?: string;
  priority?: string;
  sender?: string;
  project?: string;
  tasks?: TaskProposalItem[];
}

export interface EODTaskProposal {
  title: string;
  description: string;
  tags: string[];
  time_spent: string;
  selected?: boolean;
}

export interface NewsArticle {
  title: string;
  url: string;
  source: string;
  description: string;
  published_at: string;
  tag: string;
}

export interface AppSettings {
  gemini_api_key?: string;
  groq_api_key?: string;
  azure_org?: string;
  azure_project?: string;
  azure_pat?: string;
  azure_item_type?: string;
}

export interface VisionResult {
  summary?: string;
  diagnosis?: string;
  suggested_action?: string;
  suggested_reply?: string;
  detected_input?: string;
  active_app?: string;
  captured_at?: string;
  thumbnail_b64?: string;
  inspection_mode?: string;
}

export interface ReplySuggestion {
  reply: string;
  original?: string;
  explanation?: string;
  tone?: string;
  copied_to_clipboard?: boolean;
}

export interface OutlookAttentionItem {
  id: string;
  sender: string;
  subject: string;
  preview: string;
  created?: string;
  needs_attention?: boolean;
  urgency?: 'high' | 'medium' | 'low';
  project?: string;
  reason?: string;
  summary?: string;
  suggested_reply?: string;
  is_task?: boolean;
  task_title?: string;
  task_description?: string;
  task_priority?: string;
}

export interface ProjectInfo {
  id: string;
  name: string;
  folder: string;
  claude_md: string;
  exists: boolean;
  content_length: number;
  keywords: string[];
}


