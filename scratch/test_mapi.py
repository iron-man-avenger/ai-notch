import pythoncom
import win32com.client
import sys

def test_outlook():
    print("Testing Outlook MAPI connection...")
    pythoncom.CoInitialize()
    try:
        try:
            ol = win32com.client.GetActiveObject("Outlook.Application")
            print("[1] Connected via GetActiveObject: Outlook is actively running.")
        except Exception as e:
            print("[1] GetActiveObject failed:", e)
            print("[2] Attempting win32com.client.Dispatch...")
            ol = win32com.client.Dispatch("Outlook.Application")
            print("[2] Dispatch succeeded.")

        ns = ol.GetNamespace("MAPI")
        print("MAPI Namespace acquired.")
        print(f"Current User: {getattr(ns, 'CurrentUser', 'Unknown')}")
        print(f"Offline status: {ns.Offline}")
        
        # Check Default Folder 6 (olFolderInbox)
        inbox = ns.GetDefaultFolder(6)
        print(f"Default Inbox Name: {inbox.Name}")
        print(f"Total Inbox Items: {inbox.Items.Count}")
        
        # Fetch 3 latest items
        items = inbox.Items
        items.Sort("[ReceivedTime]", True)
        count = min(3, items.Count)
        print(f"\n--- Latest {count} Emails in Inbox ---")
        for i in range(1, count + 1):
            try:
                item = items.Item(i)
                print(f"[{i}] Subject: {item.Subject}")
                print(f"    From: {getattr(item, 'SenderName', 'Unknown')}")
                print(f"    Received: {getattr(item, 'ReceivedTime', 'Unknown')}")
                print(f"    Unread: {getattr(item, 'UnRead', False)}")
            except Exception as item_err:
                print(f"    Error reading item {i}: {item_err}")
                
        print("\nMAPI TEST SUCCESSFUL!")
    except Exception as e:
        print("\n[MAPI ERROR DETAIL]:", type(e), e)
    finally:
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    test_outlook()
