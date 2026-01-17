import subprocess

def check_clipboard():
    print("--- Clipboard Targets ---")
    try:
        # Get the list of available targets (formats) in the clipboard
        targets = subprocess.check_output(["xclip", "-selection", "clipboard", "-t", "TARGETS", "-o"], text=True)
        print(targets)
    except subprocess.CalledProcessError:
        print("Error reading targets (clipboard might be empty)")
        return

    # Check if text/uri-list is present (used for files)
    if "text/uri-list" in targets:
        print("\n--- text/uri-list Content ---")
        try:
            content = subprocess.check_output(["xclip", "-selection", "clipboard", "-t", "text/uri-list", "-o"], text=True)
            print(f"Raw content: {repr(content)}")
            
            # Verify if the file exists
            for line in content.splitlines():
                path = line.replace("file://", "").strip()
                import os
                if os.path.exists(path):
                    print(f"File exists: {path}")
                else:
                    print(f"File NOT found: {path}")
                    
        except subprocess.CalledProcessError:
            print("Error reading text/uri-list")
    else:
        print("\nNo text/uri-list found in clipboard.")

if __name__ == "__main__":
    check_clipboard()
