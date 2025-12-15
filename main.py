# main.py
import sys
import os

# Adiciona o diretório atual ao path para garantir que imports 'src' funcionem
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ui.app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()