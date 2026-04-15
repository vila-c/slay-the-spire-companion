import os, sys, subprocess

os.chdir(os.path.dirname(os.path.abspath(__file__)))

subprocess.Popen(
    [sys.executable, "main.py"],
    creationflags=0x08000000,  # CREATE_NO_WINDOW
)
