import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.outlook_reader import outlook_reader

def main():
    print("Testing Outlook Reader & AI Triager...")
    raw_emails = outlook_reader.fetch_recent_emails()
    print(f"Total raw Outlook notifications found: {len(raw_emails)}")
    
    attention_items = outlook_reader.process_latest()
    print(f"Total attention items requiring action: {len(attention_items)}")
    
    for idx, item in enumerate(attention_items[:5], 1):
        print(f"\n[{idx}] SENDER: {item.get('sender')}")
        print(f"    SUBJECT: {item.get('subject')}")
        print(f"    PROJECT: {item.get('project')}")
        print(f"    URGENCY: {item.get('urgency')}")
        print(f"    REASON: {item.get('reason')}")
        print(f"    SUMMARY: {item.get('summary')}")
        if item.get('suggested_reply'):
            print(f"    SUGGESTED REPLY: {item.get('suggested_reply')[:120]}...")

if __name__ == "__main__":
    main()
