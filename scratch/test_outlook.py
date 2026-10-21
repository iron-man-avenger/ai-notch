import pythoncom
import win32com.client

try:
    pythoncom.CoInitialize()
    try:
        app = win32com.client.GetActiveObject("Outlook.Application")
        print("Connected via GetActiveObject!")
    except Exception as e1:
        print("GetActiveObject error:", e1)
        app = win32com.client.Dispatch("Outlook.Application")
        print("Connected via Dispatch!")

    ns = app.GetNamespace("MAPI")
    print("MAPI Offline:", ns.Offline)
    print("Accounts count:", ns.Accounts.Count if hasattr(ns, 'Accounts') else 0)
    for acc in ns.Accounts:
        print("Account:", acc.DisplayName, acc.AccountType)
    for folder in ns.Folders:
        print("Root Folder:", folder.Name)
        try:
            for sub in folder.Folders:
                print("  Subfolder:", sub.Name, f"({sub.Items.Count} items)")
        except Exception as fe:
            print("  Subfolder error:", fe)

except Exception as e:
    print("Outlook Error:", e)
finally:
    pythoncom.CoUninitialize()
