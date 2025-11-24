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

import customtkinter as ctk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Configuração de aparência
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- CORREÇÃO DO ÍCONE NA BARRA DE TAREFAS (WINDOWS) ---
try:
    myappid = 'kosmos.nozzlecalc.pro.v3.16'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# --- FUNÇÃO AUXILIAR PARA RECURSOS ---
def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS # type: ignore
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- DADOS DE PROPELENTES (Nome: k) ---
PROPELLANTS = {
    "Custom / Outro": None,
    "KNDX / KNSu (Sugar)": 1.137,
    "KNSB (Sorbitol)": 1.135,
    "Epoxy / KNO3": 1.160,
    "PVC / KNO3": 1.180,
    "Black Powder": 1.210,
    "APCP (Average)": 1.240,
    "Ethanol / LOX": 1.220,
    "Paraffin / N2O": 1.260
}

# --- 0. SISTEMA DE INTERNACIONALIZAÇÃO (i18n) ---
TRANSLATIONS = {
    "en": {
        "sidebar_title": "Input Parameters",
        "lbl_lang": "Language:",
        "btn_open": "Open Project",
        "btn_save": "Save",
        "btn_save_as": "Save As...",
        "btn_run": "COMPUTE GEOMETRY (ENTER)",
        "btn_manual": "📘 Theory Manual",
        "btn_reset_view": "Refit View ⟲",
        "tab_plot": "2D Visualization",
        "tab_data": "Technical Data",
        
        "lbl_prop": "Propellant Preset",
        "lbl_tr": "Throat Radius (mm)",
        "lbl_k": "Specific Heat Ratio (Cp/Cv)",
        "lbl_pc": "Chamber Pressure (MPa)",
        "lbl_pe": "Exhaust Pressure (atm)",
        "lbl_ang_div": "Divergent Angle (deg)",
        "lbl_ang_cov": "Convergent Angle (deg)",
        "lbl_len_pct": "Length % (0.6-0.9)",
        "lbl_rounding": "Throat Rounding Factor",
        "chk_cone": "Show Conical Ref.",
        
        "plot_title": "Bell Nozzle Profile (ε={:.2f})",
        "axis_x": "Axial Length (mm)",
        "axis_y": "Radius (mm)",
        "legend_profile": "Bell Profile",
        "legend_throat": "Throat",
        "legend_control": "Control Polygon",
        "legend_center": "Throat Center",
        "legend_cone": "Conical Nozzle",
        
        "rpt_header": "--- SIMULATION RESULTS ---",
        "rpt_geo": "GEOMETRY",
        "rpt_angles": "ANGLES (RAO)",
        "rpt_ctrl": "CONTROL POINTS",
        "rpt_L": "Length (L)",
        "rpt_Eps": "Exp. Ratio (ε)",
        "rpt_Rt": "Throat Radius (Rt)",
        "rpt_Re": "Exhaust Radius (Re)",
        "rpt_At": "Throat Area (At)",
        "rpt_Ae": "Exhaust Area (Ae)",
        
        "snap_N": "N (Div. Start)",
        "snap_Q": "Q (Control Pt)",
        "snap_E": "E (Exhaust)",
        "snap_G": "G (Throat Center)",
        "snap_cone": "C (Cone End)",
        
        "err_calc": "CALCULATION ERROR",
        "err_unexpected": "UNEXPECTED ERROR",
        "err_pdf": "PDF Manual not found!",
        "msg_saved": "Project saved successfully!",
        "file_type": "Nozzle Project Files",
        "status_conv": "SIMULATION CONVERGED",
        "status_div": "SIMULATION DIVERGED"
    },
    "pt": {
        "sidebar_title": "Parâmetros de Entrada",
        "lbl_lang": "Idioma:",
        "btn_open": "Abrir Projeto",
        "btn_save": "Salvar",
        "btn_save_as": "Salvar Como...",
        "btn_run": "COMPUTAR GEOMETRY (ENTER)",
        "btn_manual": "📘 Manual Teórico",
        "btn_reset_view": "Resetar Vista ⟲",
        "tab_plot": "2D Visualization",
        "tab_data": "Dados Técnicos",
        
        "lbl_prop": "Propelente (Preset)",
        "lbl_tr": "Raio da Garganta (mm)",
        "lbl_k": "Razão de Calor Esp. (Cp/Cv)",
        "lbl_pc": "Pressão da Câmara (MPa)",
        "lbl_pe": "Pressão de Exaustão (atm)",
        "lbl_ang_div": "Ângulo Divergente (graus)",
        "lbl_ang_cov": "Ângulo Convergente (graus)",
        "lbl_len_pct": "% Comprimento (0.6-0.9)",
        "lbl_rounding": "Fator Arred. Garganta",
        "chk_cone": "Mostrar Cone Ref.",
        
        "plot_title": "Perfil Tubeira Bell (ε={:.2f})",
        "axis_x": "Comprimento Axial (mm)",
        "axis_y": "Raio (mm)",
        "legend_profile": "Perfil Bell",
        "legend_throat": "Garganta",
        "legend_control": "Polígono Controle",
        "legend_center": "Centro Garganta",
        "legend_cone": "Tubeira Cônica",
        
        "rpt_header": "--- RESULTADOS DA SIMULAÇÃO ---",
        "rpt_geo": "GEOMETRIA",
        "rpt_angles": "ÂNGULOS (RAO)",
        "rpt_ctrl": "PONTOS DE CONTROLE",
        "rpt_L": "Comprimento (L)",
        "rpt_Eps": "Razão Exp. (ε)",
        "rpt_Rt": "Raio Garganta (Rt)",
        "rpt_Re": "Raio Exaustão (Re)",
        "rpt_At": "Área Garganta (At)",
        "rpt_Ae": "Área Exaustão (Ae)",
        
        "snap_N": "N (Início Div.)",
        "snap_Q": "Q (Ponto Controle)",
        "snap_E": "E (Exaustão)",
        "snap_G": "G (Centro Garganta)",
        "snap_cone": "C (Fim Cone)",
        
        "err_calc": "ERRO DE CÁLCULO",
        "err_unexpected": "ERRO INESPERADO",
        "err_pdf": "Manual PDF não encontrado!",
        "msg_saved": "Projeto salvo com sucesso!",
        "file_type": "Arquivos de Projeto Nozzle",
        "status_conv": "SIMULAÇÃO CONVERGIU",
        "status_div": "SIMULAÇÃO DIVERGIU"
    }
}

# --- 1. CAMADA DE MODELO ---
@dataclass
class NozzleResult:
    length: float
    epsilon: float
    throat_radius: float
    exhaust_radius: float
    percent: float
    throat_area: float
    exhaust_area: float
    control_points: Dict[str, Tuple[float, float]]
    angles: Dict[str, float]
    rounding_factor: float
    cone_ref_length: float
    divergent_angle_input: float

class NozzleCalculator:
    _ARATIO = np.array([4, 5, 10, 20, 30, 40, 50, 100])
    _DATA_MAP = {
        60: {
            'tn': np.array([20.5, 20.5, 16.0, 14.5, 14.0, 13.5, 13.0, 11.2]),
            'te': np.array([26.5, 28.0, 32.0, 35.0, 36.2, 37.1, 35.0, 40.0])
        },
        80: {
            'tn': np.array([21.5, 23.0, 26.3, 28.8, 30.0, 31.0, 31.5, 33.5]),
            'te': np.array([14.0, 13.0, 11.0, 9.0, 8.5, 8.0, 7.5, 7.0])
        },
        90: {
            'tn': np.array([20.0, 21.0, 24.0, 27.0, 28.5, 29.5, 30.2, 32.0]),
            'te': np.array([11.5, 10.5, 8.0, 7.0, 6.5, 6.0, 6.0, 6.0])
        }
    }

    @staticmethod
    def calculate_epsilon(pc: float, pe: float, k: float) -> float:
        pe_mpa = pe / 9.86923
        termo1 = (2 / (k + 1)) ** (1 / (k - 1))
        termo2 = (pc / pe_mpa) ** (1 / k)
        numerador = termo1 * termo2
        termo3 = (k + 1) / (k - 1)
        termo4 = 1 - (pe_mpa / pc) ** ((k - 1) / k)
        if termo4 < 0:
            raise ValueError("Pressão de exaustão inválida (gera raiz negativa).")
        denominador = math.sqrt(termo3 * termo4)
        return numerador / denominador

    @classmethod
    def get_wall_angles(cls, eps: float, tr: float, percent: float, ang_div: float) -> Tuple[float, float, float]:
        possible_percents = [60, 80, 90]
        closest_percent = min(possible_percents, key=lambda x: abs(x - (percent * 100)))
        data = cls._DATA_MAP[closest_percent]
        theta_n = np.interp(eps, cls._ARATIO, data['tn'])
        theta_e = np.interp(eps, cls._ARATIO, data['te'])
        f1 = ((math.sqrt(eps) - 1) * tr) / math.tan(math.radians(ang_div))
        ln = (closest_percent / 100.0) * f1
        return ln, math.radians(theta_n), math.radians(theta_e)

    def compute(self, tr: float, k: float, pc: float, pe: float, 
               ang_div: float, ang_cov: float, length_pct: float, rounding_factor: float) -> NozzleResult:
        
        eps = self.calculate_epsilon(pc, pe, k)
        throat_area = math.pi * (tr ** 2)
        exhaust_area = throat_area * eps
        exhaust_radius = math.sqrt(exhaust_area / math.pi)
        
        bell_length, theta_n_rad, theta_e_rad = self.get_wall_angles(eps, tr, length_pct, ang_div)
        
        # Cálculo de referência usando o ângulo divergente do usuário
        cone_ref_length = (exhaust_radius - tr) / math.tan(math.radians(ang_div))
        
        real_percent = (bell_length / cone_ref_length) * 100 if cone_ref_length else 0
        
        theta_n_deg = math.degrees(theta_n_rad)
        theta_e_deg = math.degrees(theta_e_rad)
        
        r_div_rel = 0.382 * rounding_factor 
        
        angle_rel = math.radians(theta_n_deg - 90)
        nx = r_div_rel * tr * math.cos(angle_rel)
        ny = (r_div_rel * tr * math.sin(angle_rel)) + (tr + r_div_rel * tr)
        ex = bell_length
        ey = exhaust_radius
        m1 = math.tan(theta_n_rad)
        m2 = math.tan(theta_e_rad)
        c1 = ny - m1 * nx
        c2 = ey - m2 * ex
        
        if abs(m1 - m2) < 1e-9:
            qx, qy = (nx + ex)/2, (ny + ey)/2 
        else:
            qx = (c2 - c1) / (m1 - m2)
            qy = (m1 * c2 - m2 * c1) / (m1 - m2)
            
        return NozzleResult(
            length=bell_length,
            epsilon=eps,
            throat_radius=tr,
            exhaust_radius=exhaust_radius,
            percent=real_percent,
            throat_area=throat_area,
            exhaust_area=exhaust_area,
            control_points={'N': (nx, ny), 'Q': (qx, qy), 'E': (ex, ey)},
            angles={'theta_n': theta_n_deg, 'theta_e': theta_e_deg},
            rounding_factor=rounding_factor,
            cone_ref_length=cone_ref_length,
            divergent_angle_input=ang_div
        )

# --- 2. CAMADA DE VIEW (INTERFACE GRÁFICA) ---
class App(ctk.CTk):
    CURRENT_VERSION = "3.2.2" # Atualização Final
    
    VERSION_URL = "https://raw.githubusercontent.com/joseroberto1540/NozzleCalc/main/version.txt"
    RELEASE_URL = "https://github.com/joseroberto1540/NozzleCalc/releases/latest"

    def __init__(self):
        super().__init__()
        self.calculator = NozzleCalculator()
        self.current_lang = "en"
        self.last_result = None
        self.last_input_ang_cov = -135
        self.current_file_path = None
        
        # Variáveis de Zoom/Pan
        self.base_xlim = None
        self.base_ylim = None
        self.is_panning = False
        self.pan_start_point = None
        
        # Título
        self.title(f"NozzleCalc {self.CURRENT_VERSION}")
        self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind('<Return>', lambda event: self.run_simulation())
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.input_labels = {}
        
        self._create_sidebar()
        self._create_main_area()
        
        self.cursor_vline = None
        self.cursor_hline = None
        self.cursor_text = None
        self.snap_points = {}
        
        # --- CORREÇÃO DEFINITIVA DO ÍCONE ---
        # Agendamos para aplicar o ícone 250ms APÓS a janela abrir.
        # Isso garante que o Windows já "acordou" e vai aceitar a imagem.
        self.after(250, self._setup_icon)
        
        self.after(2000, self.check_for_updates)

    def _setup_icon(self):
        """Aplica o ícone com atraso para garantir que o Windows o registre."""
        icon_path = resource_path("icon3.ico")
        
        # Tenta método 1: Bitmap (Ícone da janela canto esquerdo)
        try:
            self.iconbitmap(icon_path)
        except Exception:
            pass
            
        # Tenta método 2: PhotoImage (Ícone da Barra de Tarefas)
        try:
            # Guardamos a referência em self para o Garbage Collector não apagar
            self.app_icon_image = ImageTk.PhotoImage(file=icon_path)
            self.wm_iconphoto(True, self.app_icon_image)
        except Exception:
            pass

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.lbl_title = ctk.CTkLabel(self.sidebar, text=TRANSLATIONS["en"]["sidebar_title"], 
                               font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_title.pack(pady=(30, 10), padx=10)
        
        self.inputs = {}
        self._add_input("tr", "lbl_tr", "13.5")
        
        # Dropdown Propelentes
        lbl_prop = ctk.CTkLabel(self.sidebar, text=TRANSLATIONS["en"]["lbl_prop"], anchor="w")
        lbl_prop.pack(fill="x", padx=20, pady=(5, 0))
        self.input_labels["lbl_prop"] = lbl_prop
        
        self.prop_menu = ctk.CTkOptionMenu(self.sidebar, 
                                           values=list(PROPELLANTS.keys()),
                                           command=self.set_propellant)
        self.prop_menu.set("KNSB (Sorbitol)")
        self.prop_menu.pack(fill="x", padx=20, pady=(0, 5))
        
        # Valor padrão KNSB
        self._add_input("k", "lbl_k", "1.135")
        
        self._add_input("pc", "lbl_pc", "5.0")
        self._add_input("pe", "lbl_pe", "1.5")
        self._add_input("ang_div", "lbl_ang_div", "15") 
        self._add_input("ang_cov", "lbl_ang_cov", "-135")
        self._add_input("len_pct", "lbl_len_pct", "0.8")
        self._add_input("rounding", "lbl_rounding", "1.00")
        
        # Aplica estilo inicial ao k (Bloqueado)
        self.inputs['k'].configure(
            state="disabled",
            fg_color="#1A1A1A",
            border_color="#333333",
            text_color="gray"
        )

        # Checkbox Cone (Atualiza apenas visualização)
        self.chk_cone_var = ctk.IntVar(value=0)
        self.chk_cone = ctk.CTkCheckBox(self.sidebar, text=TRANSLATIONS["en"]["chk_cone"],
                                        variable=self.chk_cone_var,
                                        command=self.refresh_plot_only)
        self.chk_cone.pack(pady=(15, 0), padx=20, anchor="w")
        self.input_labels["chk_cone"] = self.chk_cone
        
        self.btn_run = ctk.CTkButton(self.sidebar, text=TRANSLATIONS["en"]["btn_run"], 
                                   command=self.run_simulation,
                                   fg_color="#2ECC71", hover_color="#27AE60",
                                   height=40, font=ctk.CTkFont(weight="bold"))
        self.btn_run.pack(pady=(20, 10), padx=20, fill="x")

        self.btn_manual = ctk.CTkButton(self.sidebar, text=TRANSLATIONS["en"]["btn_manual"],
                                      command=self.open_manual,
                                      fg_color="#34495E", hover_color="#2C3E50",
                                      height=28, font=ctk.CTkFont(size=12))
        self.btn_manual.pack(pady=(0, 20), padx=20, fill="x")

    def _add_input(self, key: str, translation_key: str, default: str):
        frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame.pack(pady=3, padx=20, fill="x")
        text = TRANSLATIONS[self.current_lang][translation_key]
        lbl = ctk.CTkLabel(frame, text=text, anchor="w")
        lbl.pack(fill="x")
        self.input_labels[translation_key] = lbl 
        entry = ctk.CTkEntry(frame)
        entry.insert(0, default)
        entry.pack(fill="x")
        self.inputs[key] = entry

    def set_propellant(self, choice):
        k_val = PROPELLANTS.get(choice)
        if k_val is not None:
            self.inputs['k'].configure(state="normal")
            self.inputs['k'].delete(0, tk.END)
            # Formata para 3 casas decimais
            self.inputs['k'].insert(0, f"{k_val:.3f}")
            self.inputs['k'].configure(
                state="disabled",
                fg_color="#1A1A1A",           
                border_color="#333333",
                text_color="gray"
            )
        else:
            self.inputs['k'].configure(
                state="normal",
                fg_color="#343638",           
                text_color="white",
                border_color="#565B5E"        
            )
            self.inputs['k'].focus_set()

    def _create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        self.top_bar = ctk.CTkFrame(self.main_frame, height=50, corner_radius=0, fg_color=("gray90", "gray20"))
        self.top_bar.pack(side="top", fill="x", padx=0, pady=0)
        
        self.file_tools = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.file_tools.pack(side="left", padx=10, pady=5)
        
        self.btn_open = ctk.CTkButton(self.file_tools, text=TRANSLATIONS["en"]["btn_open"], 
                                      command=self.open_project, width=100, height=28, fg_color="#555555")
        self.btn_open.pack(side="left", padx=2)
        
        self.btn_save = ctk.CTkButton(self.file_tools, text=TRANSLATIONS["en"]["btn_save"], 
                                      command=self.save_project, width=60, height=28, fg_color="#555555")
        self.btn_save.pack(side="left", padx=2)

        self.btn_save_as = ctk.CTkButton(self.file_tools, text=TRANSLATIONS["en"]["btn_save_as"], 
                                         command=self.save_project_as, width=80, height=28, fg_color="#555555")
        self.btn_save_as.pack(side="left", padx=2)

        self.right_tools = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.right_tools.pack(side="right", padx=10, pady=5)
        
        self.btn_reset_view = ctk.CTkButton(self.right_tools, text=TRANSLATIONS["en"]["btn_reset_view"],
                                            command=self.reset_view, width=100, height=28, fg_color="#E67E22", hover_color="#D35400")
        self.btn_reset_view.pack(side="left", padx=15)

        self.lbl_lang = ctk.CTkLabel(self.right_tools, text=TRANSLATIONS["en"]["lbl_lang"], font=ctk.CTkFont(size=12))
        self.lbl_lang.pack(side="left", padx=5)
        self.lang_menu = ctk.CTkOptionMenu(self.right_tools, width=100, height=28,
                                           values=["English", "Português"],
                                           command=self.change_language)
        self.lang_menu.set("English")
        self.lang_menu.pack(side="left", padx=2)

        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_plot = self.tabview.add(TRANSLATIONS["en"]["tab_plot"])
        self.tab_data = self.tabview.add(TRANSLATIONS["en"]["tab_data"])
        
        self.fig, self.ax = plt.subplots(figsize=(6, 5), dpi=100)
        self.fig.patch.set_facecolor('#2B2B2B') 
        self.ax.set_facecolor('#2B2B2B')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_plot)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)

        self.txt_output = ctk.CTkTextbox(self.tab_data, font=("Consolas", 14))
        self.txt_output.pack(fill="both", expand=True, padx=5, pady=5)

    # --- ZOOM E PAN ---
    def reset_view(self):
        if self.base_xlim and self.base_ylim:
            self.ax.set_xlim(self.base_xlim)
            self.ax.set_ylim(self.base_ylim)
            self.canvas.draw()

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
            text_str = f"{name}\nX: {tx:.2f}\nY: {ty:.2f}"
            color, style = '#FFFF00', '--'
            dx, dy = tx, ty
        else:
            text_str = f"X: {x:.2f}\nY: {y:.2f}"
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

    def get_file_types(self):
        t = TRANSLATIONS[self.current_lang]
        return [(t["file_type"], "*.json"), ("All Files", "*.*")]

    def open_project(self):
        file_path = filedialog.askopenfilename(filetypes=self.get_file_types())
        if not file_path: return
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # 1. Restaura Visual e Lógica do Propelente PRIMEIRO
            if "propellant" in data:
                # Define o texto do dropdown
                self.prop_menu.set(data["propellant"])
                # Aplica a lógica (travar/destravar K e setar cor)
                self.set_propellant(data["propellant"])
            
            # 2. Preenche os valores numéricos (Sobrescreve o K padrão do preset pelo valor salvo)
            for key, value in data.items():
                if key in self.inputs:
                    # Verifica se o campo está travado (ex: K de um preset)
                    original_state = self.inputs[key].cget("state")
                    
                    if original_state == "disabled":
                        # Destrava momentaneamente para injetar o valor salvo
                        self.inputs[key].configure(state="normal")
                        self.inputs[key].delete(0, tk.END)
                        self.inputs[key].insert(0, str(value))
                        self.inputs[key].configure(state="disabled")
                    else:
                        # Campo normal (tr, pc, ou k custom)
                        self.inputs[key].delete(0, tk.END)
                        self.inputs[key].insert(0, str(value))
            
            self.current_file_path = file_path
            self.run_simulation()
        except Exception as e:
            tk.messagebox.showerror("Error", str(e))

    def save_project(self):
        if self.current_file_path: self._write_to_file(self.current_file_path)
        else: self.save_project_as()

    def save_project_as(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=self.get_file_types())
        if file_path:
            self.current_file_path = file_path
            self._write_to_file(file_path)

    def _write_to_file(self, path):
        t = TRANSLATIONS[self.current_lang]
        try:
            data = {key: entry.get() for key, entry in self.inputs.items()}
            
            # --- CORREÇÃO: Salvando a escolha do Dropdown ---
            data["propellant"] = self.prop_menu.get() 
            
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            tk.messagebox.showinfo("Saved", t["msg_saved"])
        except Exception as e:
            tk.messagebox.showerror("Error", str(e))

    def change_language(self, choice):
        self.current_lang = "en" if choice == "English" else "pt"
        t = TRANSLATIONS[self.current_lang]
        self.lbl_title.configure(text=t["sidebar_title"])
        self.btn_run.configure(text=t["btn_run"])
        self.btn_manual.configure(text=t["btn_manual"])
        self.lbl_lang.configure(text=t["lbl_lang"])
        self.btn_open.configure(text=t["btn_open"])
        self.btn_save.configure(text=t["btn_save"])
        self.btn_save_as.configure(text=t["btn_save_as"])
        self.btn_reset_view.configure(text=t["btn_reset_view"])
        self.chk_cone.configure(text=t["chk_cone"])
        self.input_labels["lbl_prop"].configure(text=t["lbl_prop"])
        
        for key, lbl_widget in self.input_labels.items():
            if key in t: lbl_widget.configure(text=t[key])
            
        if self.last_result:
            self._update_text_output(self.last_result)
            self._update_plot(self.last_result, self.last_input_ang_cov)

    def refresh_plot_only(self):
        """Redesenha apenas o gráfico (ex: ao toggle checkbox) sem recalcular física."""
        if self.last_result:
            self._update_plot(self.last_result, self.last_input_ang_cov)

    def open_manual(self):
        pdf_name = "manual.pdf" 
        pdf_path = resource_path(pdf_name)
        if os.path.exists(pdf_path):
            try:
                if sys.platform == 'win32': os.startfile(pdf_path)
                else: webbrowser.open(pdf_path)
            except Exception as e: tk.messagebox.showerror("Error", f"Could not open PDF: {e}")
        else:
            t = TRANSLATIONS[self.current_lang]
            tk.messagebox.showerror("Error", f"{t['err_pdf']}\nPath: {pdf_path}")

    def run_simulation(self):
        t = TRANSLATIONS[self.current_lang]
        try:
            params = {
                'tr': float(self.inputs['tr'].get()),
                'k': float(self.inputs['k'].get()),
                'pc': float(self.inputs['pc'].get()),
                'pe': float(self.inputs['pe'].get()),
                'ang_div': float(self.inputs['ang_div'].get()),
                'ang_cov': float(self.inputs['ang_cov'].get()),
                'length_pct': float(self.inputs['len_pct'].get()),
                'rounding_factor': float(self.inputs['rounding'].get()),
            }
            res = self.calculator.compute(**params)
            self.last_result = res 
            self.last_input_ang_cov = params['ang_cov']
            self._update_text_output(res)
            self._update_plot(res, params['ang_cov'])
        except ValueError as e:
            self.txt_output.delete("1.0", "end")
            self.txt_output.insert("end", f"{t['err_calc']}:\n{str(e)}")
        except Exception as e:
            self.txt_output.delete("1.0", "end")
            self.txt_output.insert("end", f"{t['err_unexpected']}:\n{str(e)}")

    def _update_text_output(self, res: NozzleResult):
        t = TRANSLATIONS[self.current_lang]
        self.txt_output.delete("1.0", "end")
        report = (
            f"{t['rpt_header']}\n\n"
            f"{t['rpt_geo']}:\n"
            f"{t['rpt_L']}:     {res.length:.4f} mm\n"
            f"{t['rpt_Eps']}:   {res.epsilon:.4f}\n"
            f"{t['rpt_Rt']}:    {res.throat_radius:.4f} mm\n"
            f"{t['rpt_Re']}:    {res.exhaust_radius:.4f} mm\n"
            f"{t['rpt_At']}:    {res.throat_area:.4f} mm²\n"
            f"{t['rpt_Ae']}:    {res.exhaust_area:.4f} mm²\n\n"
            f"{t['rpt_angles']}:\n"
            f"Theta N: {res.angles['theta_n']:.3f}°\n"
            f"Theta E: {res.angles['theta_e']:.3f}°\n\n"
            f"{t['rpt_ctrl']}:\n"
            f"N: {res.control_points['N']}\n"
            f"Q: {res.control_points['Q']}\n"
            f"E: {res.control_points['E']}\n"
        )
        self.txt_output.insert("end", report)

    def _update_plot(self, res: NozzleResult, ang_cov: float):
        t = TRANSLATIONS[self.current_lang]
        
        # Guarda zoom atual se não for a primeira vez
        prev_xlim = self.ax.get_xlim()
        prev_ylim = self.ax.get_ylim()
        is_subsequent_run = self.base_xlim is not None

        self.ax.clear()
        
        tr = res.throat_radius
        nx, ny = res.control_points['N']
        qx, qy = res.control_points['Q']
        ex, ey = res.control_points['E']
        theta_n_deg = res.angles['theta_n']
        theta_e_deg = res.angles['theta_e']

        self.snap_points = {
            t["snap_N"]: (nx, ny),
            t["snap_Q"]: (qx, qy),
            t["snap_E"]: (ex, ey),
            t["snap_G"]: (0, tr)
        }

        self.ax.grid(True, linestyle='--', alpha=0.3, color='white')
        for spine in self.ax.spines.values(): spine.set_color('white')
        self.ax.tick_params(colors='white')
        self.ax.set_title(t["plot_title"].format(res.epsilon), color='white', fontsize=12, weight='bold')
        self.ax.set_xlabel(t["axis_x"], color='white')
        self.ax.set_ylabel(t["axis_y"], color='white')

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
        status_text = t["status_conv"] if is_converged else t["status_div"]
        status_color = "#2ECC71" if is_converged else "#E74C3C"
        self.ax.text(0.5, 1.12, status_text, 
                     transform=self.ax.transAxes, ha='center', va='bottom',
                     color='white', weight='bold', fontsize=10,
                     bbox=dict(boxstyle="round,pad=0.5", fc=status_color, ec="none", alpha=0.9))

        t_param = np.linspace(0, 1, 100)
        bx = (1 - t_param)**2 * nx + 2 * (1 - t_param) * t_param * qx + t_param**2 * ex
        by = (1 - t_param)**2 * ny + 2 * (1 - t_param) * t_param * qy + t_param**2 * ey
        self.ax.plot(bx, by, color='#00BFFF', linewidth=2.5, label=t["legend_profile"])
        self.ax.plot(bx, -by, color='#00BFFF', linewidth=2.5)

        theta_conv = np.linspace(np.radians(ang_cov), np.radians(-90), 50)
        xc_conv = 0 + (1.5 * tr) * np.cos(theta_conv)
        yc_conv = (1.5 * tr + tr) + (1.5 * tr) * np.sin(theta_conv)
        self.ax.plot(xc_conv, yc_conv, color='#FF5555', label=t["legend_throat"])
        self.ax.plot(xc_conv, -yc_conv, color='#FF5555')

        theta_div = np.linspace(np.radians(-90), np.radians(theta_n_deg - 90), 50)
        r_div_rel = 0.382 * res.rounding_factor
        xc_div = 0 + (r_div_rel * tr) * np.cos(theta_div)
        yc_div = (r_div_rel * tr + tr) + (r_div_rel * tr) * np.sin(theta_div)
        self.ax.plot(xc_div, yc_div, color='#FF5555')
        self.ax.plot(xc_div, -yc_div, color='#FF5555')

        # --- PLOT DA CÔNICA (Só se o checkbox estiver marcado) ---
        if self.chk_cone_var.get() == 1:
            cone_l = res.cone_ref_length
            cone_re = res.exhaust_radius
            angle_label = f"{res.divergent_angle_input:.1f}°"
            label_text = f"{t['legend_cone']} ({angle_label})"
            
            self.ax.plot([0, cone_l], [tr, cone_re], 
                         color='gray', linestyle='--', linewidth=1.5, alpha=0.7, 
                         label=label_text)
            self.ax.scatter([cone_l], [cone_re], color='gray', s=30, marker='x')
            
            # Adiciona ao snapping
            self.snap_points[t["snap_cone"]] = (cone_l, cone_re)

        self.ax.plot([nx, qx, ex], [ny, qy, ey], 'g--', alpha=0.6, label=t["legend_control"])
        self.ax.scatter([nx, qx, ex], [ny, qy, ey], color='#00FF00', s=40, zorder=5)
        self.ax.scatter([0], [tr], color='orange', s=40, zorder=5, label=t["legend_center"])

        bbox_style = dict(boxstyle="round,pad=0.3", fc="black", ec="none", alpha=0.7)
        self.ax.text(qx, qy + 0.15*tr, f"Q({qx:.1f}, {qy:.1f})", 
                     color='#FFFF00', fontsize=10, ha='center', va='bottom', weight='bold', bbox=bbox_style)
        
        tangent_n_x = nx + tr*0.8 * math.cos(math.radians(theta_n_deg))
        tangent_n_y = ny + tr*0.8 * math.sin(math.radians(theta_n_deg))
        self.ax.plot([nx, tangent_n_x], [ny, tangent_n_y], ':', color='orange')
        self.ax.text(tangent_n_x, tangent_n_y, f"θN={theta_n_deg:.3f}°", 
                     color='orange', fontsize=10, weight='bold', bbox=bbox_style)

        tangent_e_x = ex + tr*0.8 * math.cos(math.radians(theta_e_deg))
        tangent_e_y = ey + tr*0.8 * math.sin(math.radians(theta_e_deg))
        self.ax.plot([ex, tangent_e_x], [ey, tangent_e_y], ':', color='magenta')
        self.ax.text(tangent_e_x, tangent_e_y, f"θE={theta_e_deg:.3f}°", 
                     color='magenta', fontsize=10, weight='bold', bbox=bbox_style)

        self.cursor_vline = self.ax.axvline(x=0, visible=False, color='white', linestyle='-', linewidth=0.8, alpha=0.6)
        self.cursor_hline = self.ax.axhline(y=0, visible=False, color='white', linestyle='-', linewidth=0.8, alpha=0.6)
        self.cursor_text = self.ax.text(0, 0, "", visible=False, color='#00FF00', weight='bold',
                                      bbox=dict(facecolor='black', alpha=0.8, edgecolor='white'))

        self.ax.set_aspect('equal')
        self.ax.legend(loc='upper left', facecolor='#333333', labelcolor='white', framealpha=0.9, fontsize=8)
        
        # Atualiza limites base e restaura zoom se necessário
        self.canvas.draw() 
        self.base_xlim = self.ax.get_xlim()
        self.base_ylim = self.ax.get_ylim()

        if is_subsequent_run:
            self.ax.set_xlim(prev_xlim)
            self.ax.set_ylim(prev_ylim)
            self.canvas.draw()

    def on_closing(self):
        plt.close('all')
        self.quit()
        self.destroy()
        sys.exit(0)

    def check_for_updates(self):
        try:
            url_no_cache = f"{self.VERSION_URL}?dummy={random.randint(1, 100000)}"
            response = requests.get(url_no_cache, timeout=5)
            if response.status_code == 200:
                latest_version = response.text.strip()
                if version.parse(latest_version) > version.parse(self.CURRENT_VERSION):
                    t = TRANSLATIONS[self.current_lang]
                    title = "Update Available" if self.current_lang == "en" else "Atualização Disponível"
                    msg = (f"New version {latest_version} is available!\n"
                           f"Current version: {self.CURRENT_VERSION}\n\n"
                           f"Do you want to download it now?") if self.current_lang == "en" else \
                          (f"Nova versão {latest_version} disponível!\n"
                           f"Sua versão: {self.CURRENT_VERSION}\n\n"
                           f"Deseja baixar agora?")
                    answer = messagebox.askyesno(title, msg)
                    if answer:
                        webbrowser.open(self.RELEASE_URL)
                        self.on_closing()
        except Exception as e:
            pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
