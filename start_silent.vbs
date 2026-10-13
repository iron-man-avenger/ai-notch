Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "c:\Users\Paperchase\OneDrive - Paperchase Accountancy\Documents\AI-personal-assistant"
WshShell.Run "pythonw.exe main.py", 0, False
