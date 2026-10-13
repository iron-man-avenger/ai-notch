Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Paperchase\OneDrive - Paperchase Accountancy\Documents\AI-personal-assistant"
WshShell.Run "C:\Python314\pythonw.exe main.py", 0, False
