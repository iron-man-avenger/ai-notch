import sys
import os
import psutil

try:
    import uiautomation as auto
    print("uiautomation library available")
except ImportError:
    print("uiautomation not installed")

# Let's check Windows UI Automation via ctypes or powershell
import subprocess

ps_script = """
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

$teamsProc = Get-Process -Name "ms-teams", "Teams" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $teamsProc) {
    Write-Output "Teams process not found"
    exit 0
}

Write-Output "Found Teams PID: $($teamsProc.Id)"
$el = [System.Windows.Automation.AutomationElement]::FromHandle($teamsProc.MainWindowHandle)
if (-not $el) {
    Write-Output "Could not get AutomationElement from MainWindowHandle"
    exit 0
}

Write-Output "Window Name: $($el.Current.Name)"
# Find all text or document elements
$condition = [System.Windows.Automation.Condition]::TrueCondition
$children = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants, $condition)
Write-Output "Total descendants: $($children.Count)"
$texts = @()
for ($i = 0; $i -lt [Math]::Min($children.Count, 200); $i++) {
    $child = $children[$i]
    $name = $child.Current.Name
    if ($name -and $name.Length -gt 10 -and $name -notmatch 'Button|Pane|Window|Group') {
        $texts += $name
    }
}
Write-Output "Sample texts found: $($texts.Count)"
$texts | Select-Object -First 10
"""

res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=10)
print(res.stdout)
