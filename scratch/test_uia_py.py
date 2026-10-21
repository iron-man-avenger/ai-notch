import uiautomation as auto
import sys

print("Searching for Teams window with uiautomation...")
teams_win = None
for win in auto.GetRootControl().GetChildren():
    name = win.Name
    if "teams" in name.lower():
        print(f"Found Window: '{name}', Class: '{win.ClassName}', Handle: {win.NativeWindowHandle}")
        teams_win = win
        break

if not teams_win:
    # Try finding by control type or process name
    print("Trying WindowControl with search regex...")
    teams_win = auto.WindowControl(searchDepth=2, SubName="Teams")

if teams_win.Exists(maxSearchSeconds=2):
    print("Teams window found! Inspecting controls...")
    # Walk children and collect TextControls or EditControls or DocumentControls
    texts = []
    def walk(ctrl, depth=0):
        if depth > 10 or len(texts) > 50:
            return
        name = ctrl.Name
        if name and len(name) > 15:
            texts.append((ctrl.ControlTypeName, name))
        for child in ctrl.GetChildren():
            walk(child, depth + 1)

    walk(teams_win)
    print(f"Found {len(texts)} text elements:")
    for ttype, text in texts[:15]:
        print(f"[{ttype}] {text[:80]}...")
else:
    print("Could not find Teams window via uiautomation")
