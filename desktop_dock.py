import os
import sys
import time
import threading
import uvicorn
import webview

def start_api_server():
    from server import app
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="warning")

def main():
    # 1. Start FastAPI backend in background thread
    server_thread = threading.Thread(target=start_api_server, daemon=True)
    server_thread.start()
    
    # Wait for server to initialize
    time.sleep(1.5)

    print("[Desktop Dock] Launching floating window...")
    
    # 2. Create Floating Dock Window using Windows Edge WebView2
    # Width 780, Height 550 allows modals and drawers to open smoothly,
    # while the CSS background is transparent so only the dock and active modals are visible!
    window = webview.create_window(
        title="AI Assistant Dock",
        url="http://127.0.0.1:8765",
        width=820,
        height=620,
        resizable=True,
        frameless=True,       # Sleek borderless dock
        on_top=True,          # Always on top of other windows
        transparent=True,     # True transparent glass background
        easy_drag=True        # Windows dragging support
    )
    
    # Start webview event loop
    webview.start(debug=False)

if __name__ == "__main__":
    main()
