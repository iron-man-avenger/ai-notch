with open("frontend/src/components/CoucouIsland.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update expandedHeight
old_height = "showVisionHub ? 340 :"
new_height = "showVisionHub ? 370 :"
assert old_height in content, "Could not find old_height"
content = content.replace(old_height, new_height, 1)

content = content.replace("visionResult ? 340 :", "visionResult ? 350 :", 1)

# 2. Update handleMouseDown
old_drag = """    // Do NOT drag when clicking buttons, inputs, links or Mochi canvas
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
    window.addEventListener('mouseup', handleMouseUp);"""

new_drag = """    // Do NOT drag when clicking buttons, inputs, links, selects, canvas or explicit no-drag areas
    const target = e.target as HTMLElement;
    if (target.closest('button, input, textarea, a, select, [role="button"], canvas, [data-no-drag]')) {
      return;
    }

    e.preventDefault();
    dragStartRef.current = { x: e.screenX, y: e.screenY };
    isDraggingRef.current = false;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'grabbing';

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!dragStartRef.current) return;
      const dx = moveEvent.screenX - dragStartRef.current.x;
      const dy = moveEvent.screenY - dragStartRef.current.y;

      if (Math.abs(dx) > 1 || Math.abs(dy) > 1) {
        isDraggingRef.current = true;
      }

      if (dx !== 0 || dy !== 0) {
        api.moveWindow(dx, dy);
        dragStartRef.current = { x: moveEvent.screenX, y: moveEvent.screenY };
      }
    };

    const handleMouseUp = () => {
      window.removeEventListener('mousemove', handleMouseMove, { capture: true });
      window.removeEventListener('mouseup', handleMouseUp, { capture: true });
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
      dragStartRef.current = null;
      setTimeout(() => {
        isDraggingRef.current = false;
      }, 100);
    };

    window.addEventListener('mousemove', handleMouseMove, { capture: true });
    window.addEventListener('mouseup', handleMouseUp, { capture: true });"""

# Normalize CRLF in target if needed
if old_drag not in content:
    old_drag_crlf = old_drag.replace("\n", "\r\n")
    assert old_drag_crlf in content, "Could not find old_drag in CoucouIsland.tsx"
    content = content.replace(old_drag_crlf, new_drag.replace("\n", "\r\n"), 1)
else:
    content = content.replace(old_drag, new_drag, 1)

# 3. Update Center Drag Grip in Expanded Header
old_center_grip = """            {/* Notch Center Gap Indicator / Drag Handle or Blinking Yellow Reminder Pill / Blue Outlook Pill */}
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
            ) : outlookAlert ? (
              <button 
                type="button"
                onClick={() => { setActiveTab('overview'); onExpand(); sounds.playClick(); }}
                title={`Outlook Email: ${outlookAlert.sender} - ${outlookAlert.subject}`}
                className="flex items-center gap-1.5 px-3 py-0.5 rounded-full bg-sky-500/20 text-sky-300 border border-sky-400/50 hover:bg-sky-500/30 transition cursor-pointer animate-pulse shadow-md shadow-sky-500/20 flex-shrink-0"
              >
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-80" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-400" />
                </span>
                <span className="text-[10.5px] font-bold tracking-wide">📬 {outlookAlert.project || 'Email Alert'}</span>
              </button>
            ) : (
              <div 
                title="Drag Notch anywhere (Double-click to snap top)"
                className="w-16 h-1 rounded-full bg-white/20 hover:bg-white/40 cursor-grab active:cursor-grabbing transition" 
              />
            )}"""

new_center_grip = """            {/* Notch Center Drag Area: Reminder/Alert Pill + Dedicated Drag Handle */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {activeReminder && (
                <button 
                  type="button"
                  onClick={() => { setActiveTab('overview'); onExpand(); sounds.playClick(); }}
                  title={`Task Reminder: ${activeReminder.title} (Click to open)`}
                  className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/50 hover:bg-amber-400/30 transition cursor-pointer animate-pulse shadow-md shadow-amber-500/20 flex-shrink-0"
                >
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-80" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-400" />
                  </span>
                  <Clock className="w-3 h-3 text-amber-400" />
                  <span className="text-[10px] font-bold tracking-wide">Reminder</span>
                </button>
              )}

              {outlookAlert && (
                <button 
                  type="button"
                  onClick={() => { setActiveTab('overview'); onExpand(); sounds.playClick(); }}
                  title={`Outlook Email: ${outlookAlert.sender} - ${outlookAlert.subject}`}
                  className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-sky-500/20 text-sky-300 border border-sky-400/50 hover:bg-sky-500/30 transition cursor-pointer animate-pulse shadow-md shadow-sky-500/20 flex-shrink-0"
                >
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-80" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-400" />
                  </span>
                  <span className="text-[10px] font-bold tracking-wide">📬 {outlookAlert.project || 'Email Alert'}</span>
                </button>
              )}

              {/* Dedicated Drag Handle with generous hit area */}
              <div 
                title="Drag Island anywhere on desktop (Double-click to snap top-center)"
                className="py-2 px-3 -my-2 flex items-center justify-center cursor-grab active:cursor-grabbing group/grip select-none"
              >
                <div className="w-14 h-1.5 rounded-full bg-white/25 group-hover/grip:bg-white/50 group-active/grip:bg-white/75 transition-colors shadow-xs" />
              </div>
            </div>"""

if old_center_grip not in content:
    old_center_grip_crlf = old_center_grip.replace("\n", "\r\n")
    assert old_center_grip_crlf in content, "Could not find old_center_grip in CoucouIsland.tsx"
    content = content.replace(old_center_grip_crlf, new_center_grip.replace("\n", "\r\n"), 1)
else:
    content = content.replace(old_center_grip, new_center_grip, 1)

# 4. Update Vision Hub body to be scrollable and enhance the 5th button
old_vision_grid = """                      {/* 4 Tool Cards in 2x2 Grid (1-Click Execution with Themed Mini Mochi Avatars) */}
                      <div className="grid grid-cols-2 gap-2 my-auto">"""

new_vision_grid = """                      {/* 5 Tool Cards with Scrollable Area and No-Drag Protection */}
                      <div data-no-drag className="grid grid-cols-2 gap-2 flex-1 overflow-y-auto max-h-[225px] pr-1 py-0.5 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">"""

if old_vision_grid not in content:
    old_vision_grid_crlf = old_vision_grid.replace("\n", "\r\n")
    assert old_vision_grid_crlf in content, "Could not find old_vision_grid in CoucouIsland.tsx"
    content = content.replace(old_vision_grid_crlf, new_vision_grid.replace("\n", "\r\n"), 1)
else:
    content = content.replace(old_vision_grid, new_vision_grid, 1)

# 5. Enhance the 5th button inside Vision Hub
old_btn5 = """                        {/* 5. Scan Teams for Dhiraj's Tasks (Full width, Blue/Indigo gradient) */}
                        <button
                          type="button"
                          onClick={handleScanTeamsForTasks}
                          disabled={isScanningTeams}
                          className="col-span-2 flex items-center justify-between p-2 rounded-xl bg-gradient-to-r from-blue-950/50 via-indigo-950/40 to-cyan-950/50 hover:from-blue-900/60 hover:to-indigo-900/60 border border-blue-500/30 hover:border-blue-400/50 transition cursor-pointer text-left group min-h-[46px] disabled:opacity-60 shadow-xs"
                        >
                          <div className="flex items-center gap-2">
                            <div className="w-6 h-6 rounded-lg bg-blue-500/20 border border-blue-400/40 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                              <Sparkles className="w-3.5 h-3.5 text-blue-300 animate-pulse" />
                            </div>
                            <div className="flex flex-col">
                              <span className="text-[11px] font-bold text-white group-hover:text-blue-200 flex items-center gap-1.5">
                                Scan Teams for Dhiraj's Tasks
                                <span className="text-[8.5px] px-1.5 py-0.2 rounded-full bg-blue-500/30 text-blue-200 border border-blue-400/30 uppercase tracking-wider font-mono">1-Click</span>
                              </span>
                              <span className="text-[9px] text-neutral-400 leading-tight">
                                {isScanningTeams ? 'Inspecting screen with Gemini Vision...' : 'Extract deliverables & action items assigned to you'}
                              </span>
                            </div>
                          </div>
                          <span className="text-[10px] font-semibold text-blue-300 group-hover:translate-x-0.5 transition-transform flex items-center gap-1">
                            {isScanningTeams ? 'Scanning...' : 'Scan →'}
                          </span>
                        </button>"""

new_btn5 = """                        {/* 5. Scan Teams for Dhiraj's Tasks (Full width, Blue/Indigo gradient) */}
                        <button
                          type="button"
                          onClick={handleScanTeamsForTasks}
                          disabled={isScanningTeams}
                          className="col-span-2 flex items-center justify-between p-2.5 rounded-xl bg-gradient-to-r from-blue-950/60 via-indigo-950/50 to-cyan-950/60 hover:from-blue-900/70 hover:to-indigo-900/70 border border-blue-500/40 hover:border-blue-400/60 transition cursor-pointer text-left group min-h-[48px] disabled:opacity-60 shadow-sm"
                        >
                          <div className="flex items-center gap-2.5">
                            <div className="w-7 h-7 rounded-lg bg-blue-500/25 border border-blue-400/50 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform shadow-xs">
                              <Sparkles className="w-4 h-4 text-blue-300 animate-pulse" />
                            </div>
                            <div className="flex flex-col">
                              <span className="text-[11.5px] font-bold text-white group-hover:text-blue-100 flex items-center gap-1.5">
                                Scan Teams for Dhiraj's Tasks
                                <span className="text-[8.5px] px-1.5 py-0.2 rounded-full bg-blue-500/30 text-blue-200 border border-blue-400/30 uppercase tracking-wider font-mono">1-Click</span>
                              </span>
                              <span className="text-[9.5px] text-neutral-300/80 leading-tight">
                                {isScanningTeams ? 'Inspecting screen with Gemini Vision...' : "Extract deliverables & action items assigned to you in Teams"}
                              </span>
                            </div>
                          </div>
                          <span className="text-[10px] font-bold text-blue-300 group-hover:text-blue-100 group-hover:translate-x-0.5 transition-transform flex items-center gap-1 flex-shrink-0 bg-blue-500/20 px-2 py-1 rounded-md border border-blue-400/30">
                            {isScanningTeams ? 'Scanning...' : 'Scan Now →'}
                          </span>
                        </button>"""

if old_btn5 not in content:
    old_btn5_crlf = old_btn5.replace("\n", "\r\n")
    assert old_btn5_crlf in content, "Could not find old_btn5 in CoucouIsland.tsx"
    content = content.replace(old_btn5_crlf, new_btn5.replace("\n", "\r\n"), 1)
else:
    content = content.replace(old_btn5, new_btn5, 1)

with open("frontend/src/components/CoucouIsland.tsx", "w", encoding="utf-8") as f:
    f.write(content)

print("SUCCESS: CoucouIsland.tsx patched successfully!")
