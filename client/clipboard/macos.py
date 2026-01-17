import subprocess

def get_text():
    try:
        return subprocess.check_output(
            ["pbpaste"],
            text=True
        )
    except:
        return None

def set_text(text):
    subprocess.run(
        ["pbcopy"],
        input=text,
        text=True
    )
