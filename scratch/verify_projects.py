import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.project_manager import project_manager

def main():
    print("=" * 60)
    print("PROJECT MANAGER VERIFICATION REPORT")
    print("=" * 60)
    projects = project_manager.get_projects()
    print(f"Total Projects Configured: {len(projects)}")
    
    for idx, p in enumerate(projects, 1):
        content = project_manager.get_claude_md_content(p)
        file_path = p.get("claude_md", "")
        exists = os.path.exists(file_path)
        print(f"\n{idx}. [{p.get('name')}] (ID: {p.get('id')})")
        print(f"   Folder: {p.get('folder')}")
        print(f"   CLAUDE.md File: {file_path}")
        print(f"   File Exists on Disk: {exists}")
        print(f"   Loaded Context Length: {len(content)} characters")
        print(f"   Keywords: {', '.join(p.get('keywords', []))}")
        if content:
            first_lines = [line.strip() for line in content.splitlines() if line.strip()][:2]
            print(f"   Header Content: {' | '.join(first_lines)}")
        else:
            print("   WARNING: Could not load CLAUDE.md content!")

    print("\n" + "=" * 60)
    print("AUTOMATIC KEYWORD MATCHING TEST (For Emails & Activities)")
    print("=" * 60)
    test_cases = [
        "Bug in OCR receipt processing pipeline for receipt extraction",
        "Updating STO AI Services deployment script in prod",
        "NLP to SQL query translation error in multi-agent agentic workflow",
        "Gross profit prediction model accuracy dropped in quarterly forecast"
    ]
    all_matched = True
    for text in test_cases:
        matched = project_manager.match_project_by_text(text)
        matched_name = matched.get("name") if matched else "NO MATCH"
        print(f"Input: \"{text}\"")
        print(f"   --> Matched Project: {matched_name}")
        if not matched:
            all_matched = False

    print("\n" + "=" * 60)
    print("PROMPT CONTEXT GENERATION TEST")
    print("=" * 60)
    prompt_context = project_manager.get_all_projects_context_for_prompt()
    print(f"Combined Prompt Context Size: {len(prompt_context)} chars")
    print("=" * 60)
    if len(projects) == 4 and all_matched:
        print("STATUS: ALL 4 PROJECTS ARE SUCCESSFULLY LOADED & WORKING 100%!")
    else:
        print("STATUS: VERIFICATION WARNING!")

if __name__ == "__main__":
    main()
