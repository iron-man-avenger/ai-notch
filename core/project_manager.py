import os
import json
import time
from typing import List, Dict, Any, Optional

PROJECTS_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "projects_config.json")

class ProjectManager:
    """
    Manages user projects, monitors their CLAUDE.md files on disk,
    and provides domain context for Outlook emails, EOD reports, and AI chat.
    """
    def __init__(self, config_path: str = PROJECTS_CONFIG_FILE):
        self.config_path = config_path
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get_projects(self) -> List[Dict[str, Any]]:
        """Loads projects from projects_config.json."""
        if not os.path.exists(self.config_path):
            return []
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("projects", [])
        except Exception as e:
            print(f"[ProjectManager Error] Failed to read {self.config_path}: {e}")
            return []

    def get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        for p in self.get_projects():
            if p.get("id") == project_id:
                return p
        return None

    def get_claude_md_content(self, project: Dict[str, Any], max_chars: int = 4000) -> str:
        """
        Reads CLAUDE.md content for a project from disk, with mtime-based caching.
        """
        claude_path = project.get("claude_md")
        if not claude_path or not os.path.exists(claude_path):
            return ""

        try:
            mtime = os.path.getmtime(claude_path)
            cached = self._cache.get(claude_path)
            if cached and cached.get("mtime") == mtime:
                return cached.get("content", "")

            with open(claude_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Truncate to max_chars if extremely large to prevent token blowup
            if len(content) > max_chars:
                content = content[:max_chars] + "\n...[truncated for AI context]..."

            self._cache[claude_path] = {
                "mtime": mtime,
                "content": content
            }
            return content
        except Exception as e:
            print(f"[ProjectManager] Failed reading {claude_path}: {e}")
            return ""

    def match_project_by_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Matches incoming text (email subject/body, active window title, or task text)
        against the registered project keywords and names.
        """
        if not text:
            return None
        text_lower = text.lower()
        projects = self.get_projects()

        # 1. Exact name or folder match
        for p in projects:
            p_name = p.get("name", "").lower()
            p_id = p.get("id", "").lower()
            if p_name and p_name in text_lower:
                return p
            if p_id and p_id in text_lower:
                return p

        # 2. Keyword match
        for p in projects:
            for kw in p.get("keywords", []):
                if kw.lower() in text_lower:
                    return p

        return None

    def get_all_projects_context_for_prompt(self) -> str:
        """
        Generates a concise multi-project overview to inject into LLM system prompts
        (for EOD generation, AI chat, and Outlook triaging).
        """
        projects = self.get_projects()
        if not projects:
            return "No projects currently configured in projects_config.json."

        sections = []
        for p in projects:
            p_name = p.get("name", "Unknown Project")
            p_folder = p.get("folder", "")
            claude_text = self.get_claude_md_content(p, max_chars=1800)
            
            snippet = f"### PROJECT: {p_name} (Path: {p_folder})\n"
            if claude_text:
                snippet += f"**CLAUDE.md Summary & Architecture**:\n{claude_text}\n"
            else:
                snippet += f"Keywords: {', '.join(p.get('keywords', []))}\n"
            sections.append(snippet)

        return "\n\n".join(sections)

project_manager = ProjectManager()
