# src/ui/app.py
import tkinter as tk
import customtkinter as ctk
import sys
import os
import math
import json
import requests
import random
from packaging import version
import webbrowser
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional
from PIL import Image, ImageTk
import ezdxf
from ezdxf import units

import customtkinter as ctk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D

from src.simulation.separation import FlowSimulation, SimulationInput

# IMPORTAÇÕES LOCAIS
from src.config import CURRENT_VERSION, PROPELLANTS, resource_path
from src.core.solvers.bell_nozzle import BellNozzleSolver
from src.core.solvers.bell_nozzle import BellNozzleSolver
from src.core.solvers.moc_solver import MOCSolver

from src.core.models import NozzleResult

class UnitManager:
    """Gerencia conversões e fatores de escala."""
    
    # Fatores para converter DA unidade X PARA a unidade base do Solver
    # Base Length: mm
    # Base Pressure (Chamber): MPa
    # Base Pressure (Exhaust): atm
    
    CONVERTERS = {
        'length_to_mm': {
            'mm': 1.0, 
            'cm': 10.0, 
            'm': 1000.0,
            'in': 25.4,
            'ft': 304.8  
        },
        'pressure_to_mpa': {
            'MPa': 1.0, 'Pa': 1e-6, 'psi': 0.00689476, 'ksi': 6.89476, 'atm': 0.101325
        },
        'pressure_to_atm': {
            'atm': 1.0, 'Pa': 9.86923e-6, 'MPa': 9.86923, 'psi': 0.068046, 'ksi': 68.046
        }
    }

    @staticmethod
    def convert(value: float, from_unit: str, category: str, reverse: bool = False) -> float:
        """
        category: 'length_to_mm', 'pressure_to_mpa', etc.
        reverse: Se True, converte DA base PARA a unidade de exibição (usado na UI).
        """
        # Proteção contra unidade vazia ou inválida
        if not from_unit or from_unit not in UnitManager.CONVERTERS.get(category, {}):
            return value

        factor = UnitManager.CONVERTERS[category].get(from_unit, 1.0)
        
        if reverse:
            return value / factor
        return value * factor

class ToolTip:
    """
    Cria um tooltip (texto flutuante) para qualquer widget ctk/tk.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.x = self.y = 0

        # Eventos para mostrar/esconder
        self.widget.bind("<Enter>", self.schedule_show)
        self.widget.bind("<Leave>", self.hide_tip)
        self.widget.bind("<ButtonPress>", self.hide_tip)

    def schedule_show(self, event=None):
        self.unschedule()
        # Pequeno delay de 500ms para não ficar piscando se passar o mouse rápido
        self.id = self.widget.after(500, self.show_tip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def show_tip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 35
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True) # Remove barra de título
        tw.wm_geometry(f"+{x}+{y}")
        
        # Estilo do Tooltip (Dark Mode)
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#1A1A1A", fg="#E0E0E0",
                         relief='solid', borderwidth=1,
                         font=("Arial", 9, "normal"))
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        self.unschedule()
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

class App(ctk.CTk):
    VERSION_URL = "https://raw.githubusercontent.com/joseroberto1540/NozzleCalc/main/version.txt"
    RELEASE_API_URL = "https://api.github.com/repos/joseroberto1540/NozzleCalc/releases/latest"

    COLOR_DISABLED_FG = "#1A1A1A"
    COLOR_DISABLED_BORDER = "#333333"
    COLOR_DISABLED_TEXT = "gray"
    
    COLOR_NORMAL_FG = "#343638"
    COLOR_NORMAL_BORDER = "#565B5E"
    COLOR_NORMAL_TEXT = "white"

    def __init__(self):
        super().__init__()
        
        # Mapeia nome -> CLASSE (não instancie aqui com ())
        self.available_solvers = {
            "Adapted Rao Method Solver (Rao)": BellNozzleSolver,
            "Method of Characteristics Solver (MOC)": MOCSolver
        } #easyfind
        
        self.current_solver_name = "Adapted Rao Method Solver (Rao)"
        # Instancia o padrão
        self.calculator = self.available_solvers[self.current_solver_name]()
        self.last_result = None
        self.last_input_ang_cov = -135
        self.current_file_path = None
        
        self.base_xlim = None
        self.base_ylim = None
        self.is_panning = False
        self.pan_start_point = None
        
        try:
            self.iconbitmap(resource_path("icon3.ico"))
        except:
            pass
        try:
            self.app_icon_image = ImageTk.PhotoImage(file=resource_path("icon3.ico"))
            self.wm_iconphoto(True, self.app_icon_image) 
        except Exception:
            pass

        self.title(f"NozzleCalc {CURRENT_VERSION}")
        self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind('<Return>', lambda event: self.run_simulation())
        
        # --- NOVO LAYOUT DE GRID ---
        # Row 0: Menu Bar Global (File, Tools...)
        # Row 1: Conteúdo Principal (Sidebar + Main Area)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Menu Bar não estica
        self.grid_rowconfigure(1, weight=1)  # Conteúdo estica
        
        self.inputs = {}
        
        # --- ESTADO DE PREFERÊNCIAS ---
        # Define as unidades padrão iniciais (Base do Solver)
        self.unit_prefs = {
            'tr': 'mm',   # Throat Radius
            'pc': 'MPa',  # Chamber Pressure
            'pe': 'atm'   # Exhaust Pressure
        }
        
        # Mapeia qual categoria de conversão cada input usa
        self.unit_categories = {
            'tr': 'length_to_mm',
            'pc': 'pressure_to_mpa',
            'pe': 'pressure_to_atm'
        }
        
        # Armazena referências para atualizar textos das labels depois
        self.input_labels: Dict[str, ctk.CTkLabel] = {}

        # 1. Cria a Barra de Menu Global (Topo Absoluto)
        self._create_menubar()
        
        # 2. Cria as áreas principais (deslocadas para Row 1)
        self._create_sidebar()
        self._create_main_area()
        
        self.cursor_vline = None
        self.cursor_hline = None
        self.cursor_text = None
        self.snap_points = {}

        self.sens_data = None
        self.cursor_sens_v = None
        self.cursor_sens_h = None
        self.cursor_sens_text = None
        
        self.after(2000, self.check_for_updates)

        # Atalhos de Teclado (Hotkeys)
        self.bind('<Control-s>', lambda event: self.save_project())
        self.bind('<Control-o>', lambda event: self.open_project())
        self.bind('<Control-r>', lambda event: self.run_simulation())
        self.bind('<Control-e>', lambda event: self.export_csv())

    def _create_menubar(self):
        """
        Cria a barra de menu superior global (File, Tools, etc).
        Estilo flat e minimalista.
        """
        # Frame que ocupa toda a largura (columnspan=2) na row=0
        self.menubar_frame = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="#1e1e1e")
        self.menubar_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        # Configuração comum para botões de menu (parecem texto até passar o mouse)
        menu_btn_config = {
            "width": 50, 
            "height": 28,
            "fg_color": "transparent",
            "hover_color":"#3a3a3a",
            "font": ctk.CTkFont(size=12),
            "anchor": "w"
        }

        # --- BOTÃO FILE ---
        self.btn_menu_file = ctk.CTkButton(self.menubar_frame, text="File", command=self._post_file_menu, **menu_btn_config)
        self.btn_menu_file.pack(side="left", padx=2)

        self.btn_menu_edit = ctk.CTkButton(self.menubar_frame, text="Edit", command=self._post_edit_menu, **menu_btn_config)
        self.btn_menu_edit.pack(side="left", padx=2)

        # --- BOTÃO TOOLS ---
        self.btn_menu_tools = ctk.CTkButton(self.menubar_frame, text="Tools", command=self._post_tools_menu, **menu_btn_config)
        self.btn_menu_tools.pack(side="left", padx=2)

    def _post_edit_menu(self):
        """Menu dropdown para Edit"""
        menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#404040", activeforeground="white", borderwidth=0)
        
        # Opção Preferences
        menu.add_command(label="    Preferences...", command=self.open_preferences)
        
        try:
            x = self.btn_menu_edit.winfo_rootx()
            y = self.btn_menu_edit.winfo_rooty() + self.btn_menu_edit.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _post_file_menu(self):
        """
        Exibe o menu File com o submenu 'Export Geometry' em cascata.
        """
        # Configuração visual do menu (Dark Theme)
        menu_style = {
            "tearoff": 0,
            "bg": "#2b2b2b",
            "fg": "white",
            "activebackground": "#404040",
            "activeforeground": "white",
            "borderwidth": 0,
            "font": ("Segoe UI", 9) # Fonte padrão do sistema fica mais limpa
        }

        # 1. Menu Principal (File)
        menu = tk.Menu(self, **menu_style)
        
        # Itens Principais
        menu.add_command(label="    Open Project...      (Ctrl+O)", command=self.open_project)
        menu.add_command(label="    Save Project           (Ctrl+S)", command=self.save_project)
        menu.add_command(label="    Save As...", command=self.save_project_as)
        menu.add_separator()

        # 2. Submenu de Exportação (O "Menu Lateral")
        export_menu = tk.Menu(menu, **menu_style)
        
        # Adiciona as opções específicas ao submenu
        export_menu.add_command(label="    To DXF (CAD / Fusion 360)...", command=self.export_dxf_only)
        export_menu.add_command(label="    To CSV (Excel / Points)...", command=self.export_csv_only)

        # 3. Anexa o submenu ao menu File usando 'add_cascade'
        menu.add_cascade(label="    Export Geometry", menu=export_menu)

        menu.add_separator()
        menu.add_command(label="    Exit", command=self.on_closing)
        
        # Posicionamento do popup
        try:
            x = self.btn_menu_file.winfo_rootx()
            y = self.btn_menu_file.winfo_rooty() + self.btn_menu_file.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _post_tools_menu(self):
        """Lógica para exibir o menu nativo do Tkinter abaixo do botão Tools"""
        menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white", activebackground="#404040", activeforeground="white", borderwidth=0)
        
        menu.add_command(label="    Flow Properties Table", command=self.open_flow_properties)
        # Futuramente: menu.add_command(label="    Unit Converter", command=...)
        
        try:
            x = self.btn_menu_tools.winfo_rootx()
            y = self.btn_menu_tools.winfo_rooty() + self.btn_menu_tools.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()
    
    def _set_input_state(self, key: str, state: str):
        """Altera visualmente o estado de um input (normal vs disabled)."""
        if key not in self.inputs: return
        
        entry = self.inputs[key]
        entry.configure(state=state)
        
        if state == "disabled":
            entry.configure(fg_color=self.COLOR_DISABLED_FG, 
                            border_color=self.COLOR_DISABLED_BORDER, 
                            text_color=self.COLOR_DISABLED_TEXT)
        else:
            entry.configure(fg_color=self.COLOR_NORMAL_FG, 
                            border_color=self.COLOR_NORMAL_BORDER, 
                            text_color=self.COLOR_NORMAL_TEXT)

    def _setup_sensitivity_plot(self):
        """
        Cria (ou recria) o widget FigureCanvasTkAgg dentro da aba de sensibilidade.
        Isso é necessário porque quando deletamos a aba, o canvas antigo morre.
        """
        # Verifica se a aba existe
        try:
            # Obtém a referência ATUAL do frame da aba (pode ter mudado após delete/insert)
            tab_frame = self.tabview.tab("Sensitivity Analysis")
        except Exception:
            return # Aba não existe, não faz nada

        # 1. Limpeza: Remove widgets antigos se houver (para não empilhar gráficos)
        for widget in tab_frame.winfo_children():
            widget.destroy()

        # 2. Recriação: Cria um NOVO Canvas Tkinter, mas usa a FIGURA MATPLOTLIB EXISTENTE
        # Nota: self.fig_sens é persistente (criado no __init__), então o gráfico antigo reaparece
        self.canvas_sens = FigureCanvasTkAgg(self.fig_sens, master=tab_frame)
        self.canvas_sens.draw() # Força o desenho imediato
        
        # 3. Empacotamento
        self.canvas_sens.get_tk_widget().pack(fill="both", expand=True)
        
        # 4. Reconecta eventos (o canvas antigo levou os eventos com ele)
        self.canvas_sens.mpl_connect('motion_notify_event', self.on_mouse_move_sens)

    def _create_sidebar(self):
        # Mantenha a criação do frame e dos inputs como estava...
        self.sidebar = ctk.CTkScrollableFrame(self, width=300, corner_radius=0)
        self.sidebar.configure(fg_color="transparent")
        self.sidebar.grid(row=1, column=0, sticky="nsew") # <--- ALTERADO PARA ROW 1

        self.lbl_title = ctk.CTkLabel(self.sidebar, text="Input Parameters", 
                                      font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_title.pack(pady=(20, 10), padx=10)
        
        # --- SELEÇÃO DE SOLVER ---
        lbl_solver = ctk.CTkLabel(self.sidebar, text="Solver Algorithm", anchor="w")
        lbl_solver.pack(fill="x", padx=20, pady=(5, 0))

        self.solver_menu = ctk.CTkOptionMenu(self.sidebar, values=list(self.available_solvers.keys()), command=self.change_solver)
        self.solver_menu.set(self.current_solver_name)
        self.solver_menu.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkFrame(self.sidebar, height=2, fg_color="gray30").pack(fill="x", padx=20, pady=5)
        
        # --- INPUTS (Mantenha seus inputs normais aqui) ---
        self._add_input("tr", "Throat Radius", "13.5")
        
        lbl_prop = ctk.CTkLabel(self.sidebar, text="Propellant Preset", anchor="w")
        lbl_prop.pack(fill="x", padx=20, pady=(5, 0))
        self.prop_menu = ctk.CTkOptionMenu(self.sidebar, values=list(PROPELLANTS.keys()), command=self.set_propellant)
        self.prop_menu.set("KNSB (Sorbitol)")
        self.prop_menu.pack(fill="x", padx=20, pady=(0, 5))
        
        self._add_input("k", "Specific Heat Ratio [Cp/Cv]", "1.135")
        self._add_input("pc", "Chamber Pressure", "5.0")
        self._add_input("pe", "Exhaust Pressure", "1.5")
        self._add_input("ang_div", "Divergent Angle (deg)", "15") 
        self._add_input("ang_cov", "Convergent Angle (deg)", "-135")
        self._add_input("len_pct", "Equivalent Lenght [0.6-0.9]", "0.8")
        self._add_input("rounding", "Throat Rounding Factor [TRF]", "2.00")
        
        self.inputs['k'].configure(state="disabled", fg_color="#1A1A1A", border_color="#333333", text_color="gray")

        self.chk_cone_var = ctk.IntVar(value=0)
        self.chk_cone = ctk.CTkCheckBox(self.sidebar, text="Show Conical Ref.",
                                        variable=self.chk_cone_var,
                                        command=self.refresh_plot_only)
        self.chk_cone.pack(pady=(15, 20), padx=20, anchor="w") # Aumentei um pouco o padding final
        
        # --- REMOVIDO: Botões Run e Manual foram deletados daqui ---

    def change_solver(self, choice: str):
        """Troca o solver e ajusta a interface (ativa/desativa inputs)."""
        print(f"--- TROCANDO SOLVER PARA: {choice} ---")
        
        solver_class = self.available_solvers.get(choice)
        
        if solver_class:
            try:
                self.calculator = solver_class()
                self.current_solver_name = choice
                
                # --- LÓGICA DE UI DINÂMICA ---
                is_moc = "Characteristics" in choice
                
                if is_moc:
                    # 1. Desativar inputs inúteis para MOC
                    self._set_input_state("ang_div", "disabled")
                    self._set_input_state("len_pct", "disabled")
                    
                    # 2. Remover aba de Sensibilidade (não faz sentido no MOC pois L é fixo)
                    if "Sensitivity Analysis" in self.tabview._name_list:
                        self.tabview.delete("Sensitivity Analysis")
                        
                else: # Bell Nozzle
                    # 1. Reativar inputs
                    self._set_input_state("ang_div", "normal")
                    self._set_input_state("len_pct", "normal")
                    
                    # 2. Restaurar aba se sumiu
                    if "Sensitivity Analysis" not in self.tabview._name_list:
                        self.tabview.insert(2, "Sensitivity Analysis") 
                        self._setup_sensitivity_plot()

                # Feedback visual
                print(f"UI Atualizada para modo: {'MOC' if is_moc else 'Bell'}")
                
            except Exception as e:
                print(f"ERRO AO INSTANCIAR SOLVER: {e}")
                tk.messagebox.showerror("Error", f"Could not load solver:\n{e}")

    def _add_input(self, key: str, label_base_text: str, default: str):
        frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame.pack(pady=3, padx=20, fill="x")
        
        # Verifica se este input tem unidade configurável
        current_unit = self.unit_prefs.get(key, "")
        display_text = f"{label_base_text} ({current_unit})" if current_unit else label_base_text
        
        lbl = ctk.CTkLabel(frame, text=display_text, anchor="w")
        lbl.pack(fill="x")
        
        # ARMAZENA A REFERÊNCIA DA LABEL E O TEXTO BASE
        self.input_labels[key] = {
            "widget": lbl,
            "base_text": label_base_text
        }
        
        entry = ctk.CTkEntry(frame)
        entry.insert(0, default)
        entry.pack(fill="x")
        self.inputs[key] = entry

    def set_propellant(self, choice):
        k_val = PROPELLANTS.get(choice)
        if k_val is not None:
            self.inputs['k'].configure(state="normal")
            self.inputs['k'].delete(0, tk.END)
            self.inputs['k'].insert(0, f"{k_val:.3f}")
            self.inputs['k'].configure(state="disabled", fg_color="#1A1A1A", border_color="#333333", text_color="gray")
        else:
            self.inputs['k'].configure(state="normal", fg_color="#343638", text_color="white", border_color="#565B5E")
            self.inputs['k'].focus_set()

    def _create_main_area(self) -> None:
        """
        Configura a área principal (Direita), separando a Toolbar do Conteúdo.
        """
        # MUDANÇA AQUI: row=1
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=1, column=1, sticky="nsew", padx=0, pady=0) # <--- ALTERADO PARA ROW 1
        
        # 1. Action Toolbar (Simplificada)
        self._create_action_bar() # Renomeei para ficar claro
        
        # 2. Tabs
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        
        # --- Configuração das Abas (Mantida, apenas organizada) ---
        self.tab_plot = self.tabview.add("2D Visualization")
        self.tab_data = self.tabview.add("Technical Data")
        self.tab_sens = self.tabview.add("Sensitivity Analysis")
        self.tab_sep = self.tabview.add("*Flow Separation")
        self.tab_3d = self.tabview.add("3D View")
        
        # --- INICIALIZAÇÃO DOS PLOTS (Mantida a lógica original) ---
        self._init_plots()

    def _create_action_bar(self) -> None:
        """
        Action Bar Profissional (Logo abaixo do Menu Global).
        Contém apenas as ações operacionais principais.
        """
        toolbar_frame = ctk.CTkFrame(self.main_frame, height=50, corner_radius=5, fg_color="#2B2B2B")
        toolbar_frame.pack(fill="x", side="top", padx=15, pady=(10, 10))
        
        # --- ESQUERDA: AÇÃO PRINCIPAL (COMPUTE) ---
        # Botão Verde Grande e Chamativo
        self.btn_run = ctk.CTkButton(toolbar_frame, text="▶  COMPUTE GEOMETRY", 
                                     command=self.run_simulation,
                                     width=200, height=32,
                                     font=ctk.CTkFont(size=13, weight="bold"),
                                     fg_color="#00C853", hover_color="#00E676",
                                     text_color="white")
        self.btn_run.pack(side="left", padx=10, pady=8)
        ToolTip(self.btn_run, "Run Simulation (Ctrl+R)")

        # --- DIREITA: VISUALIZAÇÃO E AJUDA ---
        # Grupo alinhado à direita
        grp_right = ctk.CTkFrame(toolbar_frame, fg_color="transparent")
        grp_right.pack(side="right", padx=10)

        # Botão Refit (Laranja)
        self.btn_reset_view = ctk.CTkButton(grp_right, text="⟲ Refit View", command=self.reset_view,
                                            width=100, height=28,
                                            font=ctk.CTkFont(size=12),
                                            fg_color="#E67E22", hover_color="#D35400")
        self.btn_reset_view.pack(side="left", padx=5)
        ToolTip(self.btn_reset_view, "Reset Zoom and Pan")

        # Divisor pequeno
        ctk.CTkFrame(grp_right, width=1, height=20, fg_color="#555555").pack(side="left", padx=5)

        # Botão Help (Discreto)
        self.btn_manual = ctk.CTkButton(grp_right, text="📘 Help", command=self.open_manual,
                                        width=70, height=28,
                                        font=ctk.CTkFont(size=12),
                                        fg_color="transparent", border_width=1, border_color="#666",
                                        hover_color="#444", text_color="#DDD")
        self.btn_manual.pack(side="left", padx=5)

    def open_preferences(self):
        """Janela popup para configuração de unidades."""
        win = ctk.CTkToplevel(self)
        win.title("Preferences")
        win.geometry("400x350")
        win.attributes('-topmost', True)
        
        ctk.CTkLabel(win, text="Unit Settings", font=("Arial", 16, "bold")).pack(pady=15)
        
        # Container para os dropdowns
        form = ctk.CTkFrame(win, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=20)
        
        # Dicionário temporário para guardar as escolhas antes de salvar
        temp_vars = {}

        def add_combo(label, key, options):
            row = ctk.CTkFrame(form, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, anchor="w").pack(side="left")
            
            var = ctk.StringVar(value=self.unit_prefs[key])
            temp_vars[key] = var
            
            combo = ctk.CTkOptionMenu(row, variable=var, values=options, width=100)
            combo.pack(side="right")

        # Criação dos campos
        add_combo("Throat Radius (Length):", "tr", ["mm", "cm", "m", "in", "ft"])
        add_combo("Chamber Pressure:", "pc", ["MPa", "Pa", "psi", "ksi", "atm"])
        add_combo("Exhaust Pressure:", "pe", ["atm", "Pa", "MPa", "psi", "ksi"])

        def apply_changes():
            # 1. Recupera valores antigos e novos
            old_prefs = self.unit_prefs.copy()
            new_prefs = {k: v.get() for k, v in temp_vars.items()}
            
            # 2. Atualiza Labels e Converte Valores nos Inputs
            self._update_units_ui(old_prefs, new_prefs)
            
            # 3. Salva estado
            self.unit_prefs = new_prefs
            win.destroy()

        ctk.CTkButton(win, text="Apply & Save", command=apply_changes, fg_color="#27AE60").pack(pady=20)

    def _update_units_ui(self, old_prefs, new_prefs):
        """Atualiza o texto das labels e converte os valores numéricos já digitados."""
        for key, new_unit in new_prefs.items():
            old_unit = old_prefs[key]
            if key not in self.inputs: continue
            
            # A. Atualiza Label
            if key in self.input_labels:
                data = self.input_labels[key]
                data["widget"].configure(text=f"{data['base_text']} ({new_unit})")
            
            # B. Converte Valor no Input (UX Premium)
            # Se mudou de mm para m, o valor 1000 deve virar 1
            if old_unit != new_unit:
                try:
                    current_val_str = self.inputs[key].get()
                    if not current_val_str: continue
                    
                    val = float(current_val_str)
                    category = self.unit_categories[key]
                    
                    # Passo 1: Converte do Antigo para a Base (ex: m -> mm)
                    val_in_base = UnitManager.convert(val, old_unit, category, reverse=False)
                    
                    # Passo 2: Converte da Base para o Novo (ex: mm -> cm)
                    # Para ir da Base -> Display, usamos reverse=True
                    val_new_display = UnitManager.convert(val_in_base, new_unit, category, reverse=True)
                    
                    self.inputs[key].delete(0, tk.END)
                    # Formatação inteligente para evitar 0.0000001
                    self.inputs[key].insert(0, f"{val_new_display:.6g}")
                    
                except ValueError:
                    pass # Se tiver texto inválido, ignora conversão

    def update_pa_unit_pref(self, choice):
        """Salva a preferência de unidade da pressão ambiente."""
        self.unit_prefs['pa'] = choice
    
    def _get_converted_value(self, key: str) -> float:
        """
        Lê o input, verifica a preferência de unidade atual e converte
        para a Unidade Base do Solver (mm, MPa ou atm).
        """
        try:
            raw_val = float(self.inputs[key].get())
            
            # Se o input tem unidade configurada, converte para a Base do Solver
            if key in self.unit_prefs:
                user_unit = self.unit_prefs[key]
                category = self.unit_categories[key]
                # Converte Display -> Base (ex: cm -> mm; Pa -> MPa)
                return UnitManager.convert(raw_val, user_unit, category, reverse=False)
            
            return raw_val
        except ValueError:
            return 0.0 # Ou levantar erro, dependendo de como preferir tratar
    
    def _init_plots(self) -> None:
        """
        Inicializa TODAS as áreas de plotagem (2D, 3D, Separação, Sensibilidade) e a Barra de Status.
        """
        # --- 1. PLOT 2D (Aba: 2D Visualization) ---
        self.fig, self.ax = plt.subplots(figsize=(6, 5), dpi=100)
        self.fig.patch.set_facecolor('#2B2B2B') 
        self.ax.set_facecolor('#2B2B2B')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_plot)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.unit_prefs = {
            'tr': 'mm',   # Throat Radius (Define a unidade de comprimento global)
            'pc': 'MPa',  # Chamber Pressure
            'pe': 'atm',  # Exhaust Pressure (Define a unidade de pressão dos gráficos de saída)
            'pa': 'Pa'    # NOVO: Ambient Pressure (Aba Separação)
        }
        
        # --- 2. BARRA DE STATUS (Rodapé da Aba 2D) ---
        # [CRÍTICO] Esta é a parte que estava faltando/foi apagada e causou o erro.
        self.status_frame = ctk.CTkFrame(self.tab_plot, height=35, corner_radius=0, fg_color="#232323")
        self.status_frame.pack(fill="x", side="bottom", padx=0, pady=0)
        
        self.status_frame.grid_columnconfigure(0, weight=1)
        self.status_frame.grid_columnconfigure(1, weight=1)
        self.status_frame.grid_columnconfigure(2, weight=1)

        # Label 1: Status da Simulação (Convergência)
        self.lbl_status_sim = ctk.CTkLabel(self.status_frame, text="READY", 
                                           font=("Arial", 12, "bold"), text_color="gray")
        self.lbl_status_sim.grid(row=0, column=0, pady=5, sticky="ew")

        # Label 2: Risco / Separação (Onde o erro ocorria)
        self.lbl_status_risk = ctk.CTkLabel(self.status_frame, text="--", 
                                            font=("Arial", 12, "bold"), text_color="gray")
        self.lbl_status_risk.grid(row=0, column=1, pady=5, sticky="ew")

        # Label 3: Eficiência
        self.lbl_status_eff = ctk.CTkLabel(self.status_frame, text="Efficiency: --%", 
                                           font=("Arial", 12, "bold"), text_color="gray")
        self.lbl_status_eff.grid(row=0, column=2, pady=5, sticky="ew")

        # Conexões de eventos do Matplotlib 2D
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)

        # --- 3. ABA DE SEPARAÇÃO (Flow Separation) ---
        # Controles
        self.sep_controls = ctk.CTkFrame(self.tab_sep, height=50, fg_color="transparent")
        self.sep_controls.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(self.sep_controls, text="Ambient Pressure:").pack(side="left", padx=5)
        
        # Input Numérico
        self.entry_pa = ctk.CTkEntry(self.sep_controls, width=100)
        self.entry_pa.insert(0, "101325") 
        self.entry_pa.pack(side="left", padx=5)
        
        # NOVO: Dropdown de Unidade para Pressão Ambiente
        self.combo_pa_unit = ctk.CTkOptionMenu(
            self.sep_controls, 
            values=["Pa", "atm", "psi", "bar", "MPa"],
            width=80,
            command=self.update_pa_unit_pref # Callback para salvar a escolha
        )
        self.combo_pa_unit.set("Pa") # Padrão
        self.combo_pa_unit.pack(side="left", padx=5)
        
        ctk.CTkButton(self.sep_controls, text="🔄 Update Plot", width=100, 
                      command=self.refresh_separation_only, 
                      fg_color="#8E44AD", hover_color="#9B59B6").pack(side="left", padx=10)
        
        self.sep_disclaimer = ctk.CTkLabel(
            self.tab_sep, 
            text="ℹ NOTE: This is a Preliminary Quasi-1D Analysis. A full CFD study is strongly recommended for Flow Separation final verification.\nClick 'Help' to know more about Schmucker Criterion.",
            font=("Arial", 14, "italic"),
            text_color="yellow"
        )
        self.sep_disclaimer.pack(side="bottom", pady=(0, 10))

        # Gráfico de Separação
        self.fig_sep, self.ax_sep = plt.subplots(figsize=(6, 5), dpi=100)
        self.fig_sep.patch.set_facecolor('#2B2B2B')
        self.ax_sep.set_facecolor('#2B2B2B')
        
        self.canvas_sep = FigureCanvasTkAgg(self.fig_sep, master=self.tab_sep)
        self.canvas_sep.get_tk_widget().pack(fill="both", expand=True)

        # --- 4. PLOT 3D (Aba: 3D View) ---
        self.fig_3d = plt.figure(figsize=(6, 5), dpi=100)
        self.fig_3d.patch.set_facecolor('#2B2B2B')
        self.ax_3d = self.fig_3d.add_subplot(111, projection='3d')
        self.ax_3d.set_facecolor('#2B2B2B')
        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, master=self.tab_3d)
        self.canvas_3d.get_tk_widget().pack(fill="both", expand=True)

        # --- 5. SENSIBILIDADE (Aba: Sensitivity Analysis) ---
        self.fig_sens, self.ax_sens = plt.subplots(figsize=(6, 5), dpi=100)
        self.fig_sens.patch.set_facecolor('#2B2B2B') 
        self.ax_sens.set_facecolor('#2B2B2B')
        self._setup_sensitivity_plot() 

        # --- 6. OUTPUT TEXT (Aba: Technical Data) ---
        # Verifica se já existe para não duplicar em recargas (opcional, mas seguro)
        if not hasattr(self, 'txt_output'):
            self.txt_output = ctk.CTkTextbox(self.tab_data, font=("Consolas", 14))
            self.txt_output.pack(fill="both", expand=True, padx=5, pady=5)

    # --- FUNÇÃO QUE FALTAVA (CORREÇÃO DO ERRO) ---
    def reset_view(self):
        if self.base_xlim and self.base_ylim:
            self.ax.set_xlim(self.base_xlim)
            self.ax.set_ylim(self.base_ylim)
            self.canvas.draw()

    def open_flow_properties(self):
        if not self.last_result: return
        res = self.last_result
        k = float(self.inputs['k'].get())
        mach_exit = self.calculator.solve_mach_from_area(res.epsilon, k)
        
        def get_ratios(mach, k):
            if mach == 0: return 1.0, 1.0
            term = 1 + (k - 1) / 2 * mach**2
            t_ratio = 1 / term
            p_ratio = term ** (-k / (k - 1))
            return p_ratio, t_ratio

        p_thr, t_thr = get_ratios(1.0, k)
        p_exit, t_exit = get_ratios(mach_exit, k)

        win = ctk.CTkToplevel(self)
        win.title("Isentropic Flow Properties")
        win.geometry("500x200")
        win.attributes('-topmost', True)

        headers = ["Location", "Mach Number", "Pressure Ratio (P/Pc)", "Temp. Ratio (T/Tc)"]
        for i, h in enumerate(headers):
            ctk.CTkLabel(win, text=h, font=("Arial", 12, "bold")).grid(row=0, column=i, padx=15, pady=10)

        data_rows = [
            ("Chamber", 0.0, 1.0000, 1.0000),
            ("Throat", 1.0, p_thr, t_thr),
            ("Exit", mach_exit, p_exit, t_exit)
        ]
        for r_idx, row in enumerate(data_rows):
            for c_idx, val in enumerate(row):
                txt = val if isinstance(val, str) else f"{val:.4f}"
                ctk.CTkLabel(win, text=txt).grid(row=r_idx+1, column=c_idx, padx=15, pady=5)

    def get_file_types(self):
        return [
            ("NozzleCalc Project", "*.nzl"),
            ("JSON Project (Legacy)", "*.json"),
            ("All Files", "*.*")
        ]

    def open_project(self):
        file_path = filedialog.askopenfilename(filetypes=self.get_file_types())
        if not file_path: return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f: 
                data = json.load(f)
            
            # --- 1. VALIDAÇÃO DE TIPO ---
            if "file_type" in data and data["file_type"] != "nozzle_calc_project":
                raise ValueError("This file is not a valid NozzleCalc project.")

            # --- 2. VALIDAÇÃO DE VERSÃO (NOVO) ---
            file_ver_str = data.get("version", "0.0.0") # Se não tiver versão, assume antiga
            
            # --- 1. RESTAURAÇÃO DE UNIDADES (NOVO) ---
            if "unit_prefs" in data:
                saved_prefs = data["unit_prefs"]
                
                # Atualiza o dicionário interno
                self.unit_prefs.update(saved_prefs)
                
                # Atualiza VISUALMENTE as Labels (ex: muda de "mm" para "m")
                for key, unit in self.unit_prefs.items():
                    if key in self.input_labels:
                        lbl_data = self.input_labels[key]
                        # Atualiza o texto da label usando o texto base + unidade salva
                        lbl_data["widget"].configure(text=f"{lbl_data['base_text']} ({unit})")

            # --- 2. RESTAURAÇÃO DE DADOS ---
            # Restaura Solver
            if "solver" in data:
                saved_solver = data["solver"]
                if saved_solver in self.available_solvers:
                    self.solver_menu.set(saved_solver)
                    self.change_solver(saved_solver)
            
            # Restaura Propelente
            if "propellant" in data:
                self.prop_menu.set(data["propellant"])
                self.set_propellant(data["propellant"])
            
            # Restaura Inputs
            for key, value in data.items():
                if key in self.inputs:
                    entry = self.inputs[key]
                    # Precisamos lidar com estados disabled (como o 'k' do propelente)
                    prev_state = entry.cget("state")
                    
                    if prev_state == "disabled":
                        entry.configure(state="normal")
                        entry.delete(0, tk.END)
                        entry.insert(0, str(value))
                        entry.configure(state="disabled")
                    else:
                        entry.delete(0, tk.END)
                        entry.insert(0, str(value))
            
            # Finalização
            self.current_file_path = file_path
            filename = os.path.basename(file_path)
            self.title(f"NozzleCalc {CURRENT_VERSION} - [{filename}]")
            
            # Executa a simulação automaticamente ao carregar
            self.run_simulation()
            
        except json.JSONDecodeError:
            tk.messagebox.showerror("Error", "File corrupted or invalid format.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            tk.messagebox.showerror("Error", f"Failed to open file:\n{e}")
            

    def save_project(self):
        if self.current_file_path: self._write_to_file(self.current_file_path)
        else: self.save_project_as()

    def save_project_as(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".nzl", 
            filetypes=self.get_file_types()
        )
        if file_path:
            self.current_file_path = file_path
            self._write_to_file(file_path)

    def export_geometry(self) -> None:
        """
        Método Mestre: Abre diálogo de salvamento e direciona para CSV ou DXF
        baseado na extensão escolhida pelo usuário.
        """
        if not self.last_result:
            tk.messagebox.showwarning("Export Warning", "No simulation data available.\nPlease run the simulation first.")
            return
        
        # Diálogo unificado com filtros para CSV e DXF
        file_path = filedialog.asksaveasfilename(
            defaultextension=".dxf",
            filetypes=[
                ("DXF", "*.dxf"),
                ("CSV", "*.csv"),
                ("Text File", "*.txt")
            ],
            title="Export Geometry"
        )
        
        if not file_path:
            return # Usuário cancelou

        try:
            # Roteamento baseado na extensão
            if file_path.lower().endswith('.dxf'):
                self._export_to_dxf(file_path)
            else:
                self._export_to_csv(file_path)
                
        except Exception as e:
            tk.messagebox.showerror("Export Error", f"Failed to export file:\n{e}")

    def export_dxf_only(self):
        """Chamada direta para exportar DXF via menu."""
        if not self.last_result:
            tk.messagebox.showwarning("Export Warning", "Please run the simulation first.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".dxf",
            filetypes=[("DXF (AutoCAD/Fusion)", "*.dxf")],
            title="Export Geometry to DXF"
        )
        if file_path:
            self._export_to_dxf(file_path)

    def export_csv_only(self):
        """Chamada direta para exportar CSV via menu."""
        if not self.last_result:
            tk.messagebox.showwarning("Export Warning", "Please run the simulation first.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV File", "*.csv"), ("Text File", "*.txt")],
            title="Export Geometry to CSV"
        )
        if file_path:
            self._export_to_csv(file_path)

    def _export_to_dxf(self, filename: str) -> None:
        """
        Gera um DXF OTIMIZADO PARA CAD (Fusion 360/SolidWorks).
        - Reduz contagem de pontos (evita travar o sketch).
        - Fecha o polígono (permite 'Revolve' imediato).
        """
        res = self.last_result
        
        # --- 1. CONFIGURAÇÃO DXF ---
        doc = ezdxf.new('R2010') 
        doc.header['$INSUNITS'] = units.MM 
        msp = doc.modelspace()

        # Camada única e limpa para evitar conflitos de importação
        doc.layers.new(name='NOZZLE_PROFILE', dxfattribs={'color': 4}) # Ciano

        # --- 2. OTIMIZAÇÃO DE PONTOS (CRÍTICO PARA FUSION 360) ---
        # Fusion odeia milhares de pontos. Vamos filtrar pontos muito próximos (< 0.05mm)
        raw_x = res.contour_x
        raw_y = res.contour_y
        
        optimized_points = []
        last_x, last_y = -999, -999
        min_dist_sq = 0.05 ** 2  # 0.05mm de resolução mínima (suficiente para usinagem)

        for x, y in zip(raw_x, raw_y):
            # Sempre inclui o primeiro ponto
            if len(optimized_points) == 0:
                optimized_points.append((x, y))
                last_x, last_y = x, y
                continue
            
            # Distância Euclidiana ao quadrado (mais rápido que sqrt)
            dist_sq = (x - last_x)**2 + (y - last_y)**2
            
            # Só adiciona se o ponto estiver longe o suficiente do anterior
            # OU se for o último ponto absoluto da lista
            if dist_sq > min_dist_sq:
                optimized_points.append((x, y))
                last_x, last_y = x, y

        # Garante que o último ponto exato da simulação esteja lá
        final_pt = (raw_x[-1], raw_y[-1])
        if optimized_points[-1] != final_pt:
            optimized_points.append(final_pt)

        print(f"DXF Optimization: Reduced {len(raw_x)} points to {len(optimized_points)} points.")

        # --- 3. FECHAMENTO DO POLÍGONO (CLOSED LOOP) ---
        # Para o Fusion reconhecer como "Profile" (azul claro), precisamos fechar a área.
        # Caminho: Começo(0,r) -> Curva -> Fim(L, r_exit) -> Desce pro Eixo(L, 0) -> Volta pro Início(0,0) -> Sobe(0,r)
        
        # Pega o último ponto da curva
        end_x, end_y = optimized_points[-1]
        start_x, start_y = optimized_points[0]

        # Adiciona pontos para fechar o loop pelo eixo X
        optimized_points.append((end_x, 0.0))    # Desce até o eixo na saída
        optimized_points.append((start_x, 0.0))  # Volta pelo eixo até a entrada
        # O ezdxf fecha automaticamente o ultimo segmento se usarmos flag=1 ou close=True, 
        # mas adicionar explicitamente ajuda alguns parsers.

        # --- 4. DESENHO ---
        # LWPOLYLINE é a entidade mais leve e compatível
        msp.add_lwpolyline(
            optimized_points, 
            dxfattribs={'layer': 'NOZZLE_PROFILE', 'closed': True}
        )
        
        # Opcional: Adicionar uma linha de centro separada em outro layer apenas para referência
        doc.layers.new(name='AXIS_REF', dxfattribs={'color': 1}) # Vermelho
        msp.add_line((start_x - 5, 0), (end_x + 5, 0), dxfattribs={'layer': 'AXIS_REF'})

        # --- 5. SALVAR ---
        try:
            doc.saveas(filename)
            
            tk.messagebox.showinfo("Export Success", 
                                f"DXF exported for Fusion 360!\n\n"
                                f"Reduced points: {len(optimized_points)} (Optimization Active)\n"
                                f"Closed Loop: Yes\n"
                                f"Units: mm")
            
            if sys.platform == 'win32':
                os.startfile(filename)
                
        except PermissionError:
             tk.messagebox.showerror("Export Error", "File is open in another program.\nPlease close it and try again.")

    def _export_to_csv(self, file_path: str) -> None:
        """
        Lógica legada de exportação CSV (Refatorada para método próprio).
        """
        use_dot = messagebox.askyesno(
            "Decimal Format", 
            "Use DOT (.) as decimal separator?\n\n"
            "Yes = International Standard/CAD (13.5)\n"
            "No = BR/Excel Standard (13,5)"
        )
        
        res = self.last_result
        try:
            with open(file_path, 'w') as f:
                col_sep = "," if use_dot else ";"
                f.write(f"X_mm{col_sep}Y_mm{col_sep}Z_mm\n")
                
                for x, y in zip(res.contour_x, res.contour_y):
                    if use_dot:
                        f.write(f"{x:.6f}{col_sep}{y:.6f}{col_sep}0.000000\n")
                    else:
                        x_str = f"{x:.6f}".replace('.', ',')
                        y_str = f"{y:.6f}".replace('.', ',')
                        f.write(f"{x_str}{col_sep}{y_str}{col_sep}0,000000\n")
                        
            tk.messagebox.showinfo("Export Success", "CSV exported successfully!")
            
            if sys.platform == 'win32':
                os.startfile(file_path)
                
        except Exception as e:
            raise e # Repassa o erro para o try/except do export_geometry lidar

    def _write_to_file(self, path):
        try:
            # Pega os valores exatamente como estão na tela (Display Values)
            data = {key: entry.get() for key, entry in self.inputs.items()}
            
            data["propellant"] = self.prop_menu.get()
            data["solver"] = self.current_solver_name
            
            # --- NOVO: SALVA AS UNIDADES ESCOLHIDAS ---
            data["unit_prefs"] = self.unit_prefs

            # Assinatura do arquivo
            data["file_type"] = "nozzle_calc_project"
            data["version"] = CURRENT_VERSION

            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
                
            tk.messagebox.showinfo("Saved", "Project saved successfully!")
            
        except Exception as e:
            tk.messagebox.showerror("Error", str(e))

    def refresh_plot_only(self):
        if self.last_result: self._update_plot(self.last_result, self.last_input_ang_cov)

    def open_manual(self):
        THEORY_URL = "https://github.com/joseroberto1540/NozzleCalc/wiki/User-Manual-and-Geometry-Theory" 
        try:
            webbrowser.open(THEORY_URL)
        except Exception as e:
            tk.messagebox.showerror("Error", f"Could not open:\n{e}")

    def run_simulation(self):
        print(">>> INICIANDO SIMULAÇÃO...")
        
        try:
            # Coleta inputs usando o método centralizado
            try:
                params = {
                    'tr': self._get_converted_value('tr'),           # Retorna sempre mm
                    'k': float(self.inputs['k'].get()),
                    'pc': self._get_converted_value('pc'),           # Retorna sempre MPa
                    'pe': self._get_converted_value('pe'),           # Retorna sempre atm
                    'ang_div': float(self.inputs['ang_div'].get()),
                    'ang_cov': float(self.inputs['ang_cov'].get()),
                    'length_pct': float(self.inputs['len_pct'].get()),
                    'rounding_factor': float(self.inputs['rounding'].get()),
                }
            except ValueError:
                tk.messagebox.showerror("Input Error", "Please check your numbers.")
                return

            # CHAMA O SOLVER ATUAL
            # O Python vai usar automaticamente o método .compute() da classe que estiver em self.calculator
            res = self.calculator.compute(**params)
            
            print("Cálculo finalizado. Atualizando UI...")
            self.last_result = res 
            self.last_input_ang_cov = params['ang_cov']
            
            self._update_text_output(res)
            self._update_plot(res, params['ang_cov'])
            self._update_3d_plot(res)
            self._update_sensitivity_analysis(params)
            self.refresh_separation_only()
            self._flash_refit_button()
            
        except Exception as e:
            import traceback
            traceback.print_exc() # Imprime o erro completo no terminal
            self.txt_output.delete("1.0", "end")
            self.txt_output.insert("end", f"CRITICAL ERROR:\n{str(e)}")
            tk.messagebox.showerror("Simulation Error", str(e))
    
    def _flash_refit_button(self):
        """
        Faz o botão 'Refit View' brilhar temporariamente para sugerir ação.
        """
        # Cores
        original_color = "#E67E22"  # O Laranja original que definimos
        flash_color = "#FFD54F"     # Um Amarelo/Dourado bem claro (Glow)
        
        # 1. Acende (Muda para a cor clara)
        self.btn_reset_view.configure(fg_color=flash_color, text_color="black") # Texto preto para contraste no claro
        
        # 2. Agenda o retorno ao normal após 500ms
        self.after(500, lambda: self.btn_reset_view.configure(fg_color=original_color, text_color="white"))

    def _update_text_output(self, res: NozzleResult):
        self.txt_output.delete("1.0", "end")

        if res.cf_ideal > 0:
            total_eff = (res.cf_est / res.cf_ideal) * 100
        else:
            total_eff = 0.0

        report = (
            "--- SIMULATION RESULTS ---\n\n"
            "GEOMETRY:\n"
            f"Length (L):     {res.length:.4f} mm\n"
            f"Exp. Ratio (ε):   {res.epsilon:.4f}\n"
            f"Throat Radius (Rt):    {res.throat_radius:.4f} mm\n"
            f"Exhaust Radius (Re):    {res.exhaust_radius:.4f} mm\n"
            f"Throat Area (At):    {res.throat_area:.4f} mm²\n"
            f"Exhaust Area (Ae):    {res.exhaust_area:.4f} mm²\n\n"
            
            "PERFORMANCE (ESTIMATED):\n"
            f"Divergence Eff. (λ):   {res.lambda_eff:.4f}\n"
            f"Ideal Thrust Coeff (Cf): {res.cf_ideal:.4f}\n"
            f"Est. Real Cf (λ * 0.98):  {res.cf_est:.4f}\n"
            f"Total Efficiency:    {total_eff:.2f}%\n"
            
            "ANGLES (RAO):\n"
            f"Theta N: {res.angles['theta_n']:.3f}°\n"
            f"Theta E: {res.angles['theta_e']:.3f}°\n\n"
            "CONTROL POINTS:\n"
            f"N: {res.control_points['N']}\n"
            f"Q: {res.control_points['Q']}\n"
            f"E: {res.control_points['E']}\n"
        )
        self.txt_output.insert("end", report)

    def _update_sensitivity_analysis(self, current_params):
        t_title = "Efficiency vs Nozzle Length"
        t_xlabel = "Length Percentage (%)"
        t_ylabel = "Total Efficiency (%)"
        t_legend_curve = "Efficiency Curve"
        t_legend_curr = "Current Design"

        self.ax_sens.clear()
        self.ax_sens.set_aspect('auto') 
        self.ax_sens.grid(True, linestyle='--', alpha=0.3, color='white')
        for spine in self.ax_sens.spines.values(): spine.set_color('white')
        self.ax_sens.tick_params(colors='white')
        self.ax_sens.set_title(t_title, color='white', fontsize=12, weight='bold')
        self.ax_sens.set_xlabel(t_xlabel, color='white')
        self.ax_sens.set_ylabel(t_ylabel, color='white')

        x_vals = []
        y_vals = []
        test_percents = np.linspace(0.60, 1.00, 41) 
        
        for pct in test_percents:
            sim_params = current_params.copy()
            sim_params['length_pct'] = pct
            res = self.calculator.compute(**sim_params)
            
            tr = res.throat_radius
            nx, ny = res.control_points['N']
            qx, qy = res.control_points['Q']
            ex, ey = res.control_points['E']
            g_x, g_y = 0, tr
            
            cond1 = (nx >= g_x) and (ny >= g_y)
            cond2 = (ex >= qx) and (ey >= qy)
            cond3 = (qy >= ny)
            if (ex - nx) != 0:
                slope_ne = (ey - ny) / (ex - nx)
                y_ref_at_q = ny + slope_ne * (qx - nx)
                cond4 = qy >= y_ref_at_q
            else:
                cond4 = False
            
            is_converged = cond1 and cond2 and cond3 and cond4
            
            if is_converged and res.cf_ideal > 0:
                eff = (res.cf_est / res.cf_ideal) * 100
                x_vals.append(pct * 100) 
                y_vals.append(eff)
        
        self.sens_data = (np.array(x_vals), np.array(y_vals))

        if x_vals:
            self.ax_sens.plot(x_vals, y_vals, color='#2ECC71', linewidth=2, label=t_legend_curve)
            current_pct = current_params['length_pct'] * 100
            if self.last_result and self.last_result.cf_ideal > 0:
                curr_eff = (self.last_result.cf_est / self.last_result.cf_ideal) * 100
                self.ax_sens.scatter([current_pct], [curr_eff], color='#E74C3C', s=100, zorder=5, label=t_legend_curr)
                self.ax_sens.annotate(f"L: {current_pct:.1f}%\nEff: {curr_eff:.2f}%", 
                                      (current_pct, curr_eff),
                                      textcoords="offset points", xytext=(0,10), ha='center',
                                      color='white', fontweight='bold', fontsize=9,
                                      bbox=dict(boxstyle="round,pad=0.3", fc="black", ec="none", alpha=0.7))

            self.ax_sens.set_xlim(55, 105)
            min_y = min(y_vals)
            self.ax_sens.set_ylim(min_y - 1.0, 100.5)

        self.ax_sens.legend(loc='lower right', facecolor='#333333', labelcolor='white')
        
        self.cursor_sens_v = self.ax_sens.axvline(x=0, visible=False, color='white', linestyle='--', alpha=0.5)
        self.cursor_sens_h = self.ax_sens.axhline(y=0, visible=False, color='white', linestyle='--', alpha=0.5)
        self.cursor_sens_text = self.ax_sens.text(0, 0, "", visible=False, color="#FFFF00", fontweight="bold",
                                                  bbox=dict(boxstyle="round", fc="black", alpha=0.8))

        self.canvas_sens.draw()

    def _update_3d_plot(self, res: NozzleResult):
        # --- VERSÃO OTIMIZADA E CORRIGIDA ---
        self.ax_3d.clear()
        self.ax_3d.set_axis_off()
        self.ax_3d.set_facecolor('#2B2B2B')

        resolution_step = 5 
        x_subset = res.contour_x[::resolution_step]
        y_subset = res.contour_y[::resolution_step]
        radial_segments = 30 
        theta = np.linspace(0, 2 * np.pi, radial_segments)
        
        x_grid, theta_grid = np.meshgrid(x_subset, theta)
        R_grid, _ = np.meshgrid(y_subset, theta)
        Y_grid = R_grid * np.cos(theta_grid)
        Z_grid = R_grid * np.sin(theta_grid)
        
        self.ax_3d.plot_surface(x_grid, Y_grid, Z_grid, alpha=0.9, color='#00BFFF', 
                                rstride=1, cstride=1, linewidth=0.5, edgecolors='#1A5276', shade=True)

        max_length = res.contour_x.max()
        max_diameter = res.contour_y.max() * 2
        world_size = max(max_length, max_diameter) * 1.2
        half_size = world_size / 2
        mid_x = max_length / 2
        
        self.ax_3d.set_xlim(mid_x - half_size, mid_x + half_size)
        self.ax_3d.set_ylim(-half_size, half_size)
        self.ax_3d.set_zlim(-half_size, half_size)
        self.ax_3d.set_box_aspect((1, 1, 1))
        self.canvas_3d.draw()

    def _update_plot(self, res: NozzleResult, ang_cov: float) -> None:
        """
        Atualiza o plot 2D respeitando as unidades selecionadas.
        CORRIGIDO: Restaura Snap Points e Status Labels.
        """
        # --- 1. CAPTURA ESTADO ANTERIOR ---
        prev_xlim = self.ax.get_xlim()
        prev_ylim = self.ax.get_ylim()
        is_subsequent_run = self.base_xlim is not None

        # --- 2. PREPARAÇÃO DE UNIDADES ---
        len_unit = self.unit_prefs.get('tr', 'mm')
        
        def to_user(val_mm):
            return UnitManager.convert(val_mm, len_unit, 'length_to_mm', reverse=True)

        # Prepara vetores convertidos para plotagem
        x_conv = [to_user(x) for x in res.contour_x]
        y_conv = [to_user(y) for y in res.contour_y]
        tr_conv = to_user(res.throat_radius)

        # --- 3. PLOTAGEM ---
        self.ax.clear()
        
        self.fig.subplots_adjust(top=0.92, bottom=0.10, left=0.10, right=0.95)
        self.ax.grid(True, linestyle='--', alpha=0.2, color='white')
        for spine in self.ax.spines.values(): spine.set_color('#555555')
        self.ax.tick_params(colors='gray', labelsize=9)

        self.ax.set_title(f"Bell Nozzle Profile (ε={res.epsilon:.2f})", color='white', fontsize=11, weight='bold', pad=10)
        self.ax.set_xlabel(f"Axial Length ({len_unit})", color='gray')
        self.ax.set_ylabel(f"Radius ({len_unit})", color='gray')

        # Geometria
        mask = res.contour_x >= 0
        div_x = np.array(x_conv)[mask]
        div_y = np.array(y_conv)[mask]
        
        self.ax.plot(div_x, div_y, color='#00BCD4', linewidth=2.0, label="Nozzle Wall")
        self.ax.plot(div_x, -div_y, color='#00BCD4', linewidth=2.0)
        self.ax.fill_between(div_x, div_y, -div_y, color='#00BCD4', alpha=0.05)

        # Garganta e Convergente
        theta_conv = np.linspace(np.radians(ang_cov), np.radians(-90), 50)
        xc_conv = 0 + (1.5 * tr_conv) * np.cos(theta_conv)
        yc_conv = (1.5 * tr_conv + tr_conv) + (1.5 * tr_conv) * np.sin(theta_conv)
        self.ax.plot(xc_conv, yc_conv, color='#FF5252', linewidth=1.5, label="Throat Region")
        self.ax.plot(xc_conv, -yc_conv, color='#FF5252', linewidth=1.5)

        # Arco Inicial Divergente
        theta_n_deg = res.angles['theta_n']
        theta_div = np.linspace(np.radians(-90), np.radians(theta_n_deg - 90), 50)
        r_div_rel = 0.382 * res.rounding_factor
        xc_div = 0 + (r_div_rel * tr_conv) * np.cos(theta_div)
        yc_div = (r_div_rel * tr_conv + tr_conv) + (r_div_rel * tr_conv) * np.sin(theta_div)
        self.ax.plot(xc_div, yc_div, color='#FF5252', linewidth=1.5)
        self.ax.plot(xc_div, -yc_div, color='#FF5252', linewidth=1.5)

        # Pontos de Controle (Visualização)
        nx, ny = res.control_points['N']
        qx, qy = res.control_points['Q']
        ex, ey = res.control_points['E']
        
        # Converte para unidade do usuário para plotar corretamente
        nx_u, ny_u = to_user(nx), to_user(ny)
        qx_u, qy_u = to_user(qx), to_user(qy)
        ex_u, ey_u = to_user(ex), to_user(ey)
        
        self.ax.plot([nx_u, qx_u, ex_u], [ny_u, qy_u, ey_u], color='gray', linestyle=':', linewidth=1, alpha=0.5)
        self.ax.scatter([nx_u, qx_u, ex_u], [ny_u, qy_u, ey_u], color='#00E676', s=15, zorder=5, label="Control Pts")

        # --- 4. CORREÇÃO 1: SNAP POINTS (Mouse Grudando) ---
        # Precisamos popular o dicionário com as coordenadas convertidas
        self.snap_points = {
            "N (Inflection)": (nx_u, ny_u),
            "Q (Control)": (qx_u, qy_u),
            "E (Exit)": (ex_u, ey_u),
            "G (Throat)": (0, tr_conv)
        }

        # --- 5. CORREÇÃO 2: ATUALIZAÇÃO DA STATUS BAR (UI) ---
        # Lógica de Convergência (Usa dados crus em mm para a lógica matemática)
        g_x, g_y = 0, res.throat_radius
        cond1 = (nx >= g_x) and (ny >= g_y)
        cond2 = (ex >= qx) and (ey >= qy)
        cond3 = (qy >= ny)
        if (ex - nx) != 0:
            slope_ne = (ey - ny) / (ex - nx)
            y_ref_at_q = ny + slope_ne * (qx - nx)
            cond4 = qy >= y_ref_at_q
        else: cond4 = False
        
        is_converged = cond1 and cond2 and cond3 and cond4

        # Atualiza Label Esquerda (Status da Simulação)
        if hasattr(self, 'lbl_status_sim'):
            if is_converged:
                self.lbl_status_sim.configure(text="✔ SIMULATION CONVERGED", text_color="#2ECC71")
            else:
                self.lbl_status_sim.configure(text="✖ DIVERGED / INVALID", text_color="#E74C3C")

        # Atualiza Label Direita (Eficiência)
        if hasattr(self, 'lbl_status_eff'):
            eff_val = (res.cf_est / res.cf_ideal) * 100 if res.cf_ideal > 0 else 0.0
            eff_color = "#2ECC71" if eff_val > 96.0 else ("#F1C40F" if eff_val >= 92.0 else "#E74C3C")
            self.lbl_status_eff.configure(text=f"Efficiency: {eff_val:.2f}%", text_color=eff_color)

        # --- FIM DAS CORREÇÕES ---

        if self.chk_cone_var.get() == 1:
            cone_l = to_user(res.cone_ref_length)
            cone_re = to_user(res.exhaust_radius)
            self.ax.plot([0, cone_l], [tr_conv, cone_re], color='gray', linestyle='--', label="Conical Ref.")
            
        self.cursor_vline = self.ax.axvline(x=0, visible=False, color='white', linestyle='-', linewidth=0.8)
        self.cursor_hline = self.ax.axhline(y=0, visible=False, color='white', linestyle='-', linewidth=0.8)
        self.cursor_text = self.ax.text(0, 0, "", visible=False, color='#00FF00', weight='bold', fontsize=8)

        self.ax.set_aspect('equal')
        self.ax.legend(loc='upper left', facecolor='#2B2B2B', edgecolor='#444', labelcolor='gray', fontsize=8)

        # Info Box
        theta_e_deg = res.angles['theta_e']
        angle_info = (f"INFLECTION & EXIT ANGLES\n"
                      f"θn: {theta_n_deg:.3f}°\n"
                      f"θe: {theta_e_deg:.3f}°")
        
        self.ax.text(0.02, 0.04, angle_info, 
                     transform=self.ax.transAxes,
                     ha='left', va='bottom',
                     color='orange', fontsize=9, fontfamily='monospace', weight='bold',
                     bbox=dict(boxstyle="round,pad=0.4", fc="#2B2B2B", ec="#444", alpha=0.9))

        self.canvas.draw()
        
        self.base_xlim = self.ax.get_xlim()
        self.base_ylim = self.ax.get_ylim()

        if is_subsequent_run:
            self.ax.set_xlim(prev_xlim)
            self.ax.set_ylim(prev_ylim)
            self.canvas.draw()

    def _update_separation_status_ui(self, result):
        """
        Atualiza a label de risco na barra de status principal com base
        nos resultados da análise de separação de Schmucker.
        """
        status_text = ""
        status_color = ""

        # 1. Verifica Avisos Geométricos (Prioridade Máxima)
        if hasattr(result, 'geometric_warnings') and result.geometric_warnings:
            # Verifica se é Quina (Discontinuity) ou Garganta (Critical)
            is_kink = any("DISCONTINUITY" in w for w in result.geometric_warnings)
            is_throat = any("CRITICAL" in w for w in result.geometric_warnings)
            
            if is_kink:
                status_text = "✖ GEOMETRY DISCONTINUITY*"
                status_color = "#E74C3C" # Vermelho
            elif is_throat:
                status_text = "⚠ SHARP THROAT: FLOW MAY DETACH*"
                status_color = "#F1C40F" # Amarelo (Aviso)
            else:
                status_text = "⚠ GEOMETRY WARNING*"
                status_color = "#F1C40F"

        # 2. Verifica Descolamento por Pressão (Física)
        elif result.has_separation:
            status_text = "✖ FLOW SEPARATION DETECTED*"
            status_color = "#E74C3C" # Vermelho

        # 3. Verifica Margem de Segurança (Para ficar amarelo se estiver quase descolando)
        elif result.safety_margin < 0.20: # Menos de 20% de margem
            margin_pct = result.safety_margin * 100
            status_text = f"⚠ LOW STABILITY MARGIN* ({margin_pct:.1f}%)"
            status_color = "#F1C40F" # Amarelo

        # 4. Tudo Verde (Sucesso)
        else:
            margin_pct = result.safety_margin * 100
            status_text = f"✔ FLOW ATTACHED* (Margin: {margin_pct:.0f}%)"
            status_color = "#2ECC71" # Verde Neon

        # Aplica na Label da Aba Principal (Barra de Status)
        # Verifica se a label existe antes de tentar configurar (segurança)
        if hasattr(self, 'lbl_status_risk'):
            self.lbl_status_risk.configure(text=status_text, text_color=status_color)

    def on_scroll(self, event):
        if event.inaxes != self.ax: return
        base_scale = 1.1
        scale_factor = 1/base_scale if event.button == 'up' else base_scale
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata, ydata = event.xdata, event.ydata
        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        self.ax.set_xlim([xdata - new_width * (1-relx), xdata + new_width * relx])
        self.ax.set_ylim([ydata - new_height * (1-rely), ydata + new_height * rely])
        self.canvas.draw()

    def on_press(self, event):
        if event.button == 1 and event.inaxes == self.ax:
            self.is_panning = True
            self.pan_start_point = (event.xdata, event.ydata)
            self.canvas.get_tk_widget().config(cursor="fleur")

    def on_release(self, event):
        self.is_panning = False
        self.pan_start_point = None
        self.canvas.get_tk_widget().config(cursor="arrow")

    def on_mouse_move(self, event):
        if self.is_panning and self.pan_start_point and event.inaxes == self.ax:
            dx = event.xdata - self.pan_start_point[0]
            dy = event.ydata - self.pan_start_point[1]
            self.ax.set_xlim(self.ax.get_xlim() - dx)
            self.ax.set_ylim(self.ax.get_ylim() - dy)
            self.canvas.draw()
            return

        if not event.inaxes or self.cursor_vline is None:
            if self.cursor_vline and self.cursor_vline.get_visible():
                self.cursor_vline.set_visible(False)
                self.cursor_hline.set_visible(False)
                self.cursor_text.set_visible(False)
                self.canvas.draw()
            return

        x, y = event.xdata, event.ydata
        snap_threshold = (self.ax.get_xlim()[1] - self.ax.get_xlim()[0]) * 0.05 
        closest_point = None
        min_dist = float('inf')

        for name, (px, py) in self.snap_points.items():
            dist = math.hypot(x - px, y - py)
            if dist < snap_threshold and dist < min_dist:
                min_dist = dist
                closest_point = (name, px, py)

        if closest_point:
            name, tx, ty = closest_point
            text_str = f"{name}\nX: {tx:.3f}\nY: {ty:.3f}"
            color, style = '#FFFF00', '--'
            dx, dy = tx, ty
        else:
            text_str = f"X: {x:.3f}\nY: {y:.3f}"
            color, style = '#00FF00', '-'
            dx, dy = x, y

        self.cursor_vline.set_xdata([dx])
        self.cursor_hline.set_ydata([dy])
        self.cursor_vline.set_color(color)
        self.cursor_hline.set_color(color)
        self.cursor_vline.set_linestyle(style)
        self.cursor_hline.set_linestyle(style)
        self.cursor_text.set_text(text_str)
        self.cursor_text.set_color(color)
        
        offset_x = (self.ax.get_xlim()[1] - self.ax.get_xlim()[0]) * 0.02
        offset_y = (self.ax.get_ylim()[1] - self.ax.get_ylim()[0]) * 0.02
        self.cursor_text.set_position((dx + offset_x, dy + offset_y))

        self.cursor_vline.set_visible(True)
        self.cursor_hline.set_visible(True)
        self.cursor_text.set_visible(True)
        self.canvas.draw()

    def on_mouse_move_sens(self, event):
        if not event.inaxes == self.ax_sens or self.sens_data is None:
            if self.cursor_sens_v and self.cursor_sens_v.get_visible():
                self.cursor_sens_v.set_visible(False)
                self.cursor_sens_h.set_visible(False)
                self.cursor_sens_text.set_visible(False)
                self.canvas_sens.draw()
            return

        x_mouse = event.xdata
        x_arr, y_arr = self.sens_data
        if len(x_arr) == 0: return

        idx = (np.abs(x_arr - x_mouse)).argmin()
        target_x = x_arr[idx]
        target_y = y_arr[idx]

        self.cursor_sens_v.set_xdata([target_x])
        self.cursor_sens_h.set_ydata([target_y])
        self.cursor_sens_text.set_text(f"L: {target_x:.1f}%\nEff: {target_y:.2f}%")
        self.cursor_sens_text.set_position((target_x, target_y))
        
        self.cursor_sens_v.set_visible(True)
        self.cursor_sens_h.set_visible(True)
        self.cursor_sens_text.set_visible(True)
        self.canvas_sens.draw()

    # --- NOVOS MÉTODOS PARA SIMULAÇÃO DE DESCOLAMENTO ---

    def run_separation_analysis(self):
        """
        Coleta dados, pede a Pressão Ambiente e roda a simulação de Schmucker.
        """
        # 1. Validação: Precisa ter rodado a geometria primeiro
        if not self.last_result:
            tk.messagebox.showwarning("Analysis Error", "Please compute the nozzle geometry first (Green Button).")
            return

        # 2. Input de Usuário: Pressão Ambiente para o teste
        # O padrão é 1 atm (nível do mar) para verificar segurança em testes estáticos
        dialog = ctk.CTkInputDialog(text="Enter Ambient Pressure for Analysis (atm):\n(Sea Level ≈ 1.0)", 
                                    title="Simulation Conditions")
        pa_str = dialog.get_input()
        
        if not pa_str: return # Usuário cancelou

        try:
            # Conversão de Unidades
            pa_atm = float(pa_str)
            pa_pascal = pa_atm * 101325  # atm -> Pa

            # --- CORREÇÃO AQUI ---
            pc_mpa = self._get_converted_value('pc') # Garante que está em MPa
            pc_pascal = pc_mpa * 1e6     # MPa -> Pa
            
            gamma = float(self.inputs['k'].get())

            sim_input = SimulationInput(
                chamber_pressure=pc_pascal,
                ambient_pressure=pa_pascal,
                gamma=gamma
            )

        except ValueError:
            tk.messagebox.showerror("Input Error", "Invalid number format. Use points (.) for decimals.")
            return

        # 3. Execução da Simulação
        try:
            sim_input = SimulationInput(
                chamber_pressure=pc_pascal,
                ambient_pressure=pa_pascal,
                gamma=gamma
            )
            
            # Instancia e roda
            sim = FlowSimulation(self.last_result, sim_input)
            result = sim.run()

            # 4. Exibição dos Resultados
            self._show_separation_window(result, pa_pascal)

        except Exception as e:
            tk.messagebox.showerror("Simulation Failed", f"An error occurred:\n{e}")

    def _show_separation_window(self, result, ambient_pressure_pa):
        """
        Cria uma janela popup dedicada para o gráfico de descolamento.
        """
        # Cria janela Toplevel (independente da principal)
        win = ctk.CTkToplevel(self)
        win.title("Flow Separation Analysis (Schmucker Criterion)")
        win.geometry("900x700")
        
        # Garante que a janela fique no topo
        win.attributes('-topmost', True) 
        # Pequeno hack para permitir foco em outras janelas dps de abrir
        self.after(100, lambda: win.attributes('-topmost', False))

        # Frame de Cabeçalho com Resumo
        header = ctk.CTkFrame(win, fg_color="#2B2B2B", height=60)
        header.pack(fill="x", padx=10, pady=10)
        
        status_color = "#E74C3C" if result.has_separation else "#2ECC71"
        status_text = "⚠️ FLOW SEPARATION DETECTED" if result.has_separation else "✅ FLOW STABLE (FULLY ATTACHED)"
        
        ctk.CTkLabel(header, text=status_text, font=("Arial", 16, "bold"), text_color=status_color).pack(side="left", padx=20)
        
        if not result.has_separation:
             ctk.CTkLabel(header, text=f"Safety Margin: {result.safety_margin*100:.1f}%", 
                          font=("Arial", 14), text_color="white").pack(side="right", padx=20)

        # Área do Gráfico
        plot_frame = ctk.CTkFrame(win, fg_color="white") # Fundo branco para o Matplotlib nativo
        plot_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Geração do Gráfico (usando nossa função modular)
        # Nota: Perguntamos se quer Log Scale se estivermos simulando vácuo (Pa muito baixo)
        use_log = ambient_pressure_pa < 1000 
        fig = plot_separation_analysis(result, ambient_pressure_pa, use_log_scale=use_log)

        # Integração Matplotlib -> Tkinter
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

        # Barra de Ferramentas de Navegação (Zoom, Pan, Save)
        # Isso é essencial para engenharia, permite dar zoom no ponto de choque
        toolbar = NavigationToolbar2Tk(canvas, plot_frame)
        toolbar.update()

    def refresh_separation_only(self):
        if not self.last_result: return

        try:
            # --- 1. PREPARAÇÃO DO INPUT (Convertendo TUDO para SI/Base) ---
            
            # A. Pressão Ambiente: Input do Usuário -> Pascal
            pa_raw = float(self.entry_pa.get())
            pa_unit_user = self.unit_prefs.get('pa', 'Pa')
            # Usa pressure_to_mpa para ir até MPa, depois * 1e6 para Pa
            # Se o usuário escolheu 'atm', convert -> converte para MPa -> converte para Pa
            pa_mpa = UnitManager.convert(pa_raw, pa_unit_user, 'pressure_to_mpa', reverse=False)
            pa_val_si = pa_mpa * 1e6 # Pascal
            
            # B. Pressão da Câmara: Unidade Salva -> Pascal
            pc_mpa = self._get_converted_value('pc') 
            pc_val_si = pc_mpa * 1e6 
            
            gamma = float(self.inputs['k'].get())
            
            # --- 2. CÁLCULO FÍSICO (Sempre em SI) ---
            sim_input = SimulationInput(chamber_pressure=pc_val_si, ambient_pressure=pa_val_si, gamma=gamma)
            sim = FlowSimulation(self.last_result, sim_input)
            result = sim.run()
            
            # --- 3. PREPARAÇÃO DO PLOT (Convertendo SI -> Unidade do Usuário) ---
            
            # Identifica unidades de destino
            len_unit = self.unit_prefs.get('tr', 'mm')  # Comprimento (ex: in)
            press_unit = self.unit_prefs.get('pe', 'atm') # Pressão Y (ex: psi) - Usamos a de Exhaust como referência visual
            
            # Helpers de Conversão de Saída
            def conv_len(val_m): 
                # Metro -> mm (*1000) -> Unidade Usuário (reverse=True)
                val_mm = val_m * 1000
                return UnitManager.convert(val_mm, len_unit, 'length_to_mm', reverse=True)
            
            def conv_press(val_pa):
                # Pascal -> MPa (/1e6) -> Unidade Usuário (reverse=True)
                val_mpa = val_pa / 1e6
                return UnitManager.convert(val_mpa, press_unit, 'pressure_to_mpa', reverse=True)

            # Vetores Convertidos
            x_plot = [conv_len(x) for x in result.axis_x]
            p_wall_plot = [conv_press(p) for p in result.wall_pressure]
            p_limit_plot = [conv_press(p) for p in result.schmucker_limit]
            pa_line_val = conv_press(pa_val_si)

            # --- 4. PLOTAGEM ---
            self.ax_sep.clear()
            self.ax_sep.grid(True, linestyle='--', alpha=0.3, color='white')
            self.ax_sep.tick_params(colors='white')
            
            # Labels com Unidades
            self.ax_sep.set_title("Flow Separation Check", color='white', weight='bold')
            self.ax_sep.set_xlabel(f"Axial Length ({len_unit})", color='white')
            self.ax_sep.set_ylabel(f"Pressure ({press_unit})", color='white')

            self.ax_sep.plot(x_plot, p_wall_plot, label='Wall Pressure', color='#3498DB', linewidth=2)
            self.ax_sep.plot(x_plot, p_limit_plot, label='Separation Limit', color='#E74C3C', linestyle='--', linewidth=2)
            self.ax_sep.axhline(y=pa_line_val, color='gray', linestyle=':', label=f'Ambient ({pa_unit_user})')

            # Log Scale se necessário (Baseado no valor visual plotado)
            # Se estivermos plotando em atm/bar/MPa, valores < 0.01 podem pedir log
            if pa_line_val < 0.01 and press_unit in ['MPa', 'atm', 'bar']: 
                 self.ax_sep.set_yscale('log')
            elif pa_line_val < 1000 and press_unit == 'Pa':
                 self.ax_sep.set_yscale('log')

            # Marcador de Separação (Se houver)
            if result.has_separation and result.separation_x is not None:
                sx_conv = conv_len(result.separation_x)
                sp_conv = conv_press(result.separation_pressure)
                
                self.ax_sep.scatter([sx_conv], [sp_conv], color='#E74C3C', s=100, zorder=10, marker='X')
                self.ax_sep.annotate(f'SEPARATION\nX={sx_conv:.3f}{len_unit}', (sx_conv, sp_conv), 
                                     xytext=(0, 20), textcoords='offset points', ha='center',
                                     color='#E74C3C', weight='bold',
                                     bbox=dict(boxstyle="round,pad=0.2", fc="#2B2B2B", ec="#E74C3C"))
            
            # Legenda e Redraw
            self.ax_sep.legend(facecolor='#2B2B2B', labelcolor='white')
            self.canvas_sep.draw()
            
            # Atualiza Status Bar (A mesma lógica de antes, não muda pois depende do objeto `result` físico)
            self._update_separation_status_ui(result)

        except Exception as e:
            import traceback
            traceback.print_exc()
            tk.messagebox.showerror("Simulation Error", f"Failed to update separation plot:\n{e}")

    def on_closing(self):
        plt.close('all')
        self.quit()
        self.destroy()
        sys.exit(0)

    def check_for_updates(self):
        try:
            api_url = self.RELEASE_API_URL
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_tag = data['tag_name'].replace('v', '').strip()
                if version.parse(latest_tag) > version.parse(CURRENT_VERSION):
                    msg = (f"New version {latest_tag} is available!\n"
                           f"Current version: {CURRENT_VERSION}\n\n"
                           f"Do you want to download it now?")
                    answer = messagebox.askyesno("Update Available", msg)
                    if answer:
                        webbrowser.open(data['html_url'])
                        self.on_closing()
        except Exception:
            pass