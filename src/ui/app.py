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

import customtkinter as ctk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D

# IMPORTAÇÕES LOCAIS
from src.config import CURRENT_VERSION, PROPELLANTS, resource_path
from src.core.solvers.bell_nozzle import BellNozzleSolver # Renomeei para ficar mais explícito
from src.core.models import NozzleResult

class App(ctk.CTk):
    VERSION_URL = "https://raw.githubusercontent.com/joseroberto1540/NozzleCalc/main/version.txt"
    RELEASE_API_URL = "https://api.github.com/repos/joseroberto1540/NozzleCalc/releases/latest"

    def __init__(self):
        super().__init__()
        # Use a variável importada do config
        self.title(f"NozzleCalc {CURRENT_VERSION}") 
        
        # Instancia o solver importado
        self.calculator = BellNozzleSolver()
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
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.inputs = {}
        
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

    def _create_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.lbl_title = ctk.CTkLabel(self.sidebar, text="Input Parameters", 
                                      font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_title.pack(pady=(30, 10), padx=10)
        
        self._add_input("tr", "Throat Radius (mm)", "13.5")
        
        lbl_prop = ctk.CTkLabel(self.sidebar, text="Propellant Preset", anchor="w")
        lbl_prop.pack(fill="x", padx=20, pady=(5, 0))
        
        self.prop_menu = ctk.CTkOptionMenu(self.sidebar, 
                                           values=list(PROPELLANTS.keys()),
                                           command=self.set_propellant)
        self.prop_menu.set("KNSB (Sorbitol)")
        self.prop_menu.pack(fill="x", padx=20, pady=(0, 5))
        
        self._add_input("k", "Specific Heat Ratio (Cp/Cv)", "1.135")
        self._add_input("pc", "Chamber Pressure (MPa)", "5.0")
        self._add_input("pe", "Exhaust Pressure (atm)", "1.5")
        self._add_input("ang_div", "Divergent Angle (deg)", "15") 
        self._add_input("ang_cov", "Convergent Angle (deg)", "-135")
        self._add_input("len_pct", "Length % (0.6-0.9)", "0.8")
        self._add_input("rounding", "Throat Rounding Factor (TRF)", "2.00")
        
        self.inputs['k'].configure(state="disabled", fg_color="#1A1A1A", border_color="#333333", text_color="gray")

        self.chk_cone_var = ctk.IntVar(value=0)
        self.chk_cone = ctk.CTkCheckBox(self.sidebar, text="Show Conical Ref.",
                                        variable=self.chk_cone_var,
                                        command=self.refresh_plot_only)
        self.chk_cone.pack(pady=(15, 0), padx=20, anchor="w")
        
        self.btn_run = ctk.CTkButton(self.sidebar, text="COMPUTE GEOMETRY (ENTER)", 
                                     command=self.run_simulation,
                                     fg_color="#2ECC71", hover_color="#27AE60",
                                     height=40, font=ctk.CTkFont(weight="bold"))
        self.btn_run.pack(pady=(20, 10), padx=20, fill="x")

        self.btn_manual = ctk.CTkButton(self.sidebar, text="📘 Theory Manual",
                                        command=self.open_manual,
                                        fg_color="#34495E", hover_color="#2C3E50",
                                        height=28, font=ctk.CTkFont(size=12))
        self.btn_manual.pack(pady=(0, 20), padx=20, fill="x")

    def _add_input(self, key: str, label_text: str, default: str):
        frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame.pack(pady=3, padx=20, fill="x")
        lbl = ctk.CTkLabel(frame, text=label_text, anchor="w")
        lbl.pack(fill="x")
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

    def _create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        self.top_bar = ctk.CTkFrame(self.main_frame, height=50, corner_radius=0, fg_color=("gray90", "gray20"))
        self.top_bar.pack(side="top", fill="x", padx=0, pady=0)
        
        self.file_tools = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.file_tools.pack(side="left", padx=10, pady=5)
        
        self.btn_open = ctk.CTkButton(self.file_tools, text="Open Project", 
                                      command=self.open_project, width=100, height=28, fg_color="#555555")
        self.btn_open.pack(side="left", padx=2)
        
        self.btn_save = ctk.CTkButton(self.file_tools, text="Save", 
                                      command=self.save_project, width=60, height=28, fg_color="#555555")
        self.btn_save.pack(side="left", padx=2)

        self.btn_save_as = ctk.CTkButton(self.file_tools, text="Save As...", 
                                         command=self.save_project_as, width=80, height=28, fg_color="#555555")
        self.btn_save_as.pack(side="left", padx=2)

        self.right_tools = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.right_tools.pack(side="right", padx=10, pady=5)
        
        self.btn_flow = ctk.CTkButton(self.right_tools, text="Flow Props 📊",
                                      command=self.open_flow_properties, width=100, height=28, 
                                      fg_color="#3498DB", hover_color="#2980B9")
        self.btn_flow.pack(side="left", padx=5)

        self.btn_export = ctk.CTkButton(self.right_tools, text="Export CSV",
                                        command=self.export_csv, width=100, height=28, 
                                        fg_color="#27AE60", hover_color="#2ECC71")
        self.btn_export.pack(side="left", padx=5)
        
        self.btn_reset_view = ctk.CTkButton(self.right_tools, text="Refit View ⟲",
                                            command=self.reset_view, width=100, height=28, fg_color="#E67E22", hover_color="#D35400")
        self.btn_reset_view.pack(side="left", padx=15)
        
        self.tabview = ctk.CTkTabview(self.main_frame)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_plot = self.tabview.add("2D Visualization")
        self.tab_data = self.tabview.add("Technical Data")
        self.tab_sens = self.tabview.add("Sensitivity Analysis")
        self.tab_3d = self.tabview.add("3D View")
        
        # 2D Plot
        self.fig, self.ax = plt.subplots(figsize=(6, 5), dpi=100)
        self.fig.patch.set_facecolor('#2B2B2B') 
        self.ax.set_facecolor('#2B2B2B')
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_plot)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)

        # 3D Plot
        self.fig_3d = plt.figure(figsize=(6, 5), dpi=100)
        self.fig_3d.patch.set_facecolor('#2B2B2B')
        self.ax_3d = self.fig_3d.add_subplot(111, projection='3d')
        self.ax_3d.set_facecolor('#2B2B2B')

        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, master=self.tab_3d)
        self.canvas_3d.get_tk_widget().pack(fill="both", expand=True)

        # Sensitivity Plot
        self.fig_sens, self.ax_sens = plt.subplots(figsize=(6, 5), dpi=100)
        self.fig_sens.patch.set_facecolor('#2B2B2B') 
        self.ax_sens.set_facecolor('#2B2B2B')
        self.canvas_sens = FigureCanvasTkAgg(self.fig_sens, master=self.tab_sens)
        self.canvas_sens.get_tk_widget().pack(fill="both", expand=True)
        self.canvas_sens.mpl_connect('motion_notify_event', self.on_mouse_move_sens)

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
        return [("Nozzle Project Files", "*.json"), ("All Files", "*.*")]

    def open_project(self):
        file_path = filedialog.askopenfilename(filetypes=self.get_file_types())
        if not file_path: return
        try:
            with open(file_path, 'r') as f: data = json.load(f)
            if "propellant" in data:
                self.prop_menu.set(data["propellant"])
                self.set_propellant(data["propellant"])
            for key, value in data.items():
                if key in self.inputs:
                    original_state = self.inputs[key].cget("state")
                    if original_state == "disabled":
                        self.inputs[key].configure(state="normal")
                        self.inputs[key].delete(0, tk.END)
                        self.inputs[key].insert(0, str(value))
                        self.inputs[key].configure(state="disabled")
                    else:
                        self.inputs[key].delete(0, tk.END)
                        self.inputs[key].insert(0, str(value))
            self.current_file_path = file_path
            self.run_simulation()
        except Exception as e: tk.messagebox.showerror("Error", str(e))

    def save_project(self):
        if self.current_file_path: self._write_to_file(self.current_file_path)
        else: self.save_project_as()

    def save_project_as(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=self.get_file_types())
        if file_path:
            self.current_file_path = file_path
            self._write_to_file(file_path)

    def export_csv(self):
        if not self.last_result: return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("CSV File", "*.csv"), ("Text File", "*.txt")], 
            title="Export Nozzle Coordinates"
        )
        
        if file_path:
            use_dot = messagebox.askyesno(
                "Decimal Format", 
                "Use DOT (.) as decimal separator?\n\n"
                "Yes = International Standard/CAD (13.5)\n"
                "No = BR/Excel Standard (13,5)"
            )
            
            try:
                res = self.last_result
                with open(file_path, 'w') as f:
                    col_sep = "," if use_dot else ";"
                    f.write(f"X_mm{col_sep}Y_mm{col_sep}Z_mm\n")
                    
                    for x, y in zip(res.contour_x, res.contour_y):
                        if use_dot:
                            f.write(f"{x/10:.6f}{col_sep}{y/10:.6f}{col_sep}0.000000\n")
                        else:
                            x_str = f"{x/10:.6f}".replace('.', ',')
                            y_str = f"{y/10:.6f}".replace('.', ',')
                            f.write(f"{x_str}{col_sep}{y_str}{col_sep}0,000000\n")
                        
                tk.messagebox.showinfo("NozzleCalc", "Success! Geometry exported successfully!\nReady for CAD import.")
                
                if sys.platform == 'win32':
                    os.startfile(file_path)
                    
            except Exception as e:
                tk.messagebox.showerror("Error", f"Export failed:\n{e}")

    def _write_to_file(self, path):
        try:
            data = {key: entry.get() for key, entry in self.inputs.items()}
            data["propellant"] = self.prop_menu.get()
            with open(path, 'w') as f: json.dump(data, f, indent=4)
            tk.messagebox.showinfo("Saved", "Project saved successfully!")
        except Exception as e: tk.messagebox.showerror("Error", str(e))

    def refresh_plot_only(self):
        if self.last_result: self._update_plot(self.last_result, self.last_input_ang_cov)

    def open_manual(self):
        THEORY_URL = "https://github.com/joseroberto1540/NozzleCalc/wiki" 
        try:
            webbrowser.open(THEORY_URL)
        except Exception as e:
            tk.messagebox.showerror("Error", f"Could not open:\n{e}")

    def run_simulation(self):
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
            self._update_3d_plot(res)
            self._update_sensitivity_analysis(params)
        except ValueError as e:
            self.txt_output.delete("1.0", "end")
            self.txt_output.insert("end", f"CALCULATION ERROR:\n{str(e)}")
        except Exception as e:
            self.txt_output.delete("1.0", "end")
            self.txt_output.insert("end", f"UNEXPECTED ERROR:\n{str(e)}")

    def _update_text_output(self, res: NozzleResult):
        self.txt_output.delete("1.0", "end")

        if res.cf_ideal > 0:
            total_eff = (res.cf_est / res.cf_ideal) * 100
        else:
            total_eff = 0.0

        theta_n = res.angles['theta_n']
        rf = res.rounding_factor
        safe_rf = max(rf, 0.1) 
        severity_index = theta_n / safe_rf
        
        if severity_index < 13.80:
            risk_msg = "LOW (Conservative) - The use of CFDs for analysis is recommended."
        elif severity_index <= 26:
            risk_msg = "MEDIUM (Standard) - The use of CFDs for analysis is recommended."
        else:
            risk_msg = "HIGH (Aggressive) - The use of CFDs for analysis is recommended."

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
            f"Throat Separation Risk: {risk_msg}\n\n"
            
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

    def _update_plot(self, res: NozzleResult, ang_cov: float):
        prev_xlim = self.ax.get_xlim()
        prev_ylim = self.ax.get_ylim()
        is_subsequent_run = self.base_xlim is not None

        self.ax.clear()
        self.fig.subplots_adjust(top=0.80, bottom=0.10, left=0.10, right=0.95)

        tr = res.throat_radius
        nx, ny = res.control_points['N']
        qx, qy = res.control_points['Q']
        ex, ey = res.control_points['E']
        theta_n_deg = res.angles['theta_n']
        theta_e_deg = res.angles['theta_e']

        self.snap_points = {
            "N (Div. Start)": (nx, ny),
            "Q (Control Pt)": (qx, qy),
            "E (Exhaust)": (ex, ey),
            "G (Throat Center)": (0, tr)
        }

        self.ax.grid(True, linestyle='--', alpha=0.3, color='white')
        for spine in self.ax.spines.values(): spine.set_color('white')
        self.ax.tick_params(colors='white')
        
        self.ax.set_title("Bell Nozzle Profile (ε={:.2f})".format(res.epsilon), color='white', fontsize=12, weight='bold')
        self.ax.set_xlabel("Axial Length (mm)", color='white')
        self.ax.set_ylabel("Radius (mm)", color='white')

        g_x, g_y = 0, tr
        cond1 = (nx >= g_x) and (ny >= g_y)
        cond2 = (ex >= qx) and (ey >= qy)
        cond3 = (qy >= ny)
        if (ex - nx) != 0:
            slope_ne = (ey - ny) / (ex - nx)
            y_ref_at_q = ny + slope_ne * (qx - nx)
            cond4 = qy >= y_ref_at_q
        else: cond4 = False

        is_converged = cond1 and cond2 and cond3 and cond4
        
        if res.cf_ideal > 0: eff_val = (res.cf_est / res.cf_ideal) * 100
        else: eff_val = 0.0
        
        rf = res.rounding_factor
        safe_rf = max(rf, 0.1)
        severity = theta_n_deg / safe_rf

        status_text = "SIMULATION CONVERGED" if is_converged else "SIMULATION DIVERGED"
        status_color = "#2ECC71" if is_converged else "#E74C3C"
        
        self.ax.text(0.5, 1.24, status_text, 
                     transform=self.ax.transAxes, ha='center', va='bottom',
                     color='white', weight='bold', fontsize=10,
                     bbox=dict(boxstyle="round,pad=0.4", fc=status_color, ec="none", alpha=0.9))

        if severity < 13.80:
            risk_txt = "THROAT FLOW DISPLACEMENT RISK: LOW"
            risk_bg, risk_fg = "#2ECC71", "white"
        elif severity <= 25:
            risk_txt = "THROAT FLOW DISPLACEMENT RISK: MEDIUM (increase TRF)"
            risk_bg, risk_fg = "#F1C40F", "black"
        else:
            risk_txt = "THROAT FLOW DISPLACEMENT RISK: HIGH (increase TRF)"
            risk_bg, risk_fg = "#E74C3C", "white"
            
        self.ax.text(0.5, 1.18, risk_txt, 
                     transform=self.ax.transAxes, ha='center', va='bottom',
                     color=risk_fg, weight='bold', fontsize=10,
                     bbox=dict(boxstyle="round,pad=0.4", fc=risk_bg, ec="none", alpha=0.9))

        if eff_val > 96.0: eff_bg, eff_fg = "#2ECC71", "white"
        elif eff_val >= 92.0: eff_bg, eff_fg = "#F1C40F", "black"
        else: eff_bg, eff_fg = "#E74C3C", "white"

        self.ax.text(0.5, 1.12, f"EFFICIENCY: {eff_val:.2f}%", 
                     transform=self.ax.transAxes, ha='center', va='bottom',
                     color=eff_fg, weight='bold', fontsize=10,
                     bbox=dict(boxstyle="round,pad=0.4", fc=eff_bg, ec="none", alpha=0.9))

        t_param = np.linspace(0, 1, 100)
        bx = (1 - t_param)**2 * nx + 2 * (1 - t_param) * t_param * qx + t_param**2 * ex
        by = (1 - t_param)**2 * ny + 2 * (1 - t_param) * t_param * qy + t_param**2 * ey
        self.ax.plot(bx, by, color='#00BFFF', linewidth=2.5, label="Bell Profile")
        self.ax.plot(bx, -by, color='#00BFFF', linewidth=2.5)

        theta_conv = np.linspace(np.radians(ang_cov), np.radians(-90), 50)
        xc_conv = 0 + (1.5 * tr) * np.cos(theta_conv)
        yc_conv = (1.5 * tr + tr) + (1.5 * tr) * np.sin(theta_conv)
        self.ax.plot(xc_conv, yc_conv, color='#FF5555', label="Throat")
        self.ax.plot(xc_conv, -yc_conv, color='#FF5555')

        theta_div = np.linspace(np.radians(-90), np.radians(theta_n_deg - 90), 50)
        r_div_rel = 0.382 * res.rounding_factor
        xc_div = 0 + (r_div_rel * tr) * np.cos(theta_div)
        yc_div = (r_div_rel * tr + tr) + (r_div_rel * tr) * np.sin(theta_div)
        self.ax.plot(xc_div, yc_div, color='#FF5555')
        self.ax.plot(xc_div, -yc_div, color='#FF5555')

        if self.chk_cone_var.get() == 1:
            cone_l = res.cone_ref_length
            cone_re = res.exhaust_radius
            angle_label = f"{res.divergent_angle_input:.1f}°"
            label_text = f"Conical Nozzle ({angle_label})"
            self.ax.plot([0, cone_l], [tr, cone_re], color='gray', linestyle='--', linewidth=1.5, alpha=0.7, label=label_text)
            self.ax.scatter([cone_l], [cone_re], color='gray', s=30, marker='x')
            self.snap_points["C (Cone End)"] = (cone_l, cone_re)

        self.ax.plot([nx, qx, ex], [ny, qy, ey], 'g--', alpha=0.6, label="Control Polygon")
        self.ax.scatter([nx, qx, ex], [ny, qy, ey], color='#00FF00', s=40, zorder=5)
        self.ax.scatter([0], [tr], color='orange', s=40, zorder=5, label="Throat Center")

        bbox_style = dict(boxstyle="round,pad=0.3", fc="black", ec="none", alpha=0.7)
        self.ax.text(qx, qy + 0.15*tr, f"Q({qx:.3f}, {qy:.3f})", 
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
        
        self.canvas.draw() 
        self.base_xlim = self.ax.get_xlim()
        self.base_ylim = self.ax.get_ylim()

        if is_subsequent_run:
            self.ax.set_xlim(prev_xlim)
            self.ax.set_ylim(prev_ylim)
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