import sys
import os
import asyncio

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import webbrowser
import threading
import time
import uvicorn
from core.db import init_db

def start_server():
    from server import app
    print("=" * 60)
    print("[AI Personal Assistant Engine Started]")
    print("[Local API: http://127.0.0.1:8765]")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")

def main():
    init_db()

    # CLI option: run as headless background server
    if "--server-only" in sys.argv:
        start_server()
        return

    # CLI option: open inside regular browser
    if "--browser" in sys.argv:
        t = threading.Thread(target=start_server, daemon=True)
        t.start()
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8765")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Exiting...")
        return

    # Default: Native Windows Desktop Floating Dock (PySide6)
    import dock_app
    dock_app.main()

if __name__ == "__main__":
    main()
