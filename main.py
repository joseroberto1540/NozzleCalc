# main.py
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ui.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()