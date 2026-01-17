import subprocess

def get_text():
    try:
        return subprocess.check_output(
            ["xclip", "-selection", "clipboard", "-o"],
            text=True
        )
    except:
        return None

def set_text(text):
    subprocess.run(
        ["xclip", "-selection", "clipboard"],
        input=text,
        text=True
    )
