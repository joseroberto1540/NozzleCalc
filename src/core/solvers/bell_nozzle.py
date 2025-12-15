# src/core/solvers/bell_nozzle.py
import math
import numpy as np
from typing import Tuple
from src.core.models import NozzleResult

class BellNozzleSolver:
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
            raise ValueError("Invalid exhaust pressure (negative root).")
        denominador = math.sqrt(termo3 * termo4)
        return numerador / denominador

    @classmethod
    def get_wall_angles(cls, eps: float, tr: float, percent: float, ang_div: float) -> Tuple[float, float, float]:
        tn_60 = np.interp(eps, cls._ARATIO, cls._DATA_MAP[60]['tn'])
        te_60 = np.interp(eps, cls._ARATIO, cls._DATA_MAP[60]['te'])
        tn_80 = np.interp(eps, cls._ARATIO, cls._DATA_MAP[80]['tn'])
        te_80 = np.interp(eps, cls._ARATIO, cls._DATA_MAP[80]['te'])
        tn_90 = np.interp(eps, cls._ARATIO, cls._DATA_MAP[90]['tn'])
        te_90 = np.interp(eps, cls._ARATIO, cls._DATA_MAP[90]['te'])

        x_percents = [0.6, 0.8, 0.9] 
        y_tn = [tn_60, tn_80, tn_90]
        y_te = [te_60, te_80, te_90]

        final_theta_n = np.interp(percent, x_percents, y_tn)
        final_theta_e = np.interp(percent, x_percents, y_te)

        f1 = ((math.sqrt(eps) - 1) * tr) / math.tan(math.radians(ang_div))
        ln = percent * f1
        
        return ln, math.radians(final_theta_n), math.radians(final_theta_e)

    def solve_mach_from_area(self, epsilon: float, k: float) -> float:
        if epsilon <= 1.0: return 1.0
        M = 2.0 
        for _ in range(20):
            term1 = (2 / (k + 1)) * (1 + (k - 1) / 2 * M**2)
            exponent = (k + 1) / (2 * (k - 1))
            f = (1 / M) * (term1 ** exponent) - epsilon
            df = (1/M) * exponent * (term1**(exponent-1)) * (2/(k+1)) * (k-1)*M - (1/M**2) * (term1**exponent)
            if abs(f) < 1e-6: return M
            M = M - f / df
        return M

    def calculate_performance(self, k: float, pc: float, pe: float, theta_e_deg: float, eps: float):
        theta_rad = math.radians(theta_e_deg)
        lam = (1 + math.cos(theta_rad)) / 2
        pe_mpa = pe / 9.86923 
        pratio = pe_mpa / pc
        if pratio >= 1.0: return lam, 0.0, 0.0

        term1 = (2 * k**2) / (k - 1)
        term2 = (2 / (k + 1)) ** ((k + 1) / (k - 1))
        term3 = 1 - (pratio) ** ((k - 1) / k)
        cf_ideal = math.sqrt(term1 * term2 * term3)
        cf_real = cf_ideal * lam * 0.98
        return lam, cf_ideal, cf_real

    def compute(self, tr: float, k: float, pc: float, pe: float, 
               ang_div: float, ang_cov: float, length_pct: float, rounding_factor: float) -> NozzleResult:
        
        eps = self.calculate_epsilon(pc, pe, k)
        throat_area = math.pi * (tr ** 2)
        exhaust_area = throat_area * eps
        exhaust_radius = math.sqrt(exhaust_area / math.pi)
        
        bell_length, theta_n_rad, theta_e_rad = self.get_wall_angles(eps, tr, length_pct, ang_div)
        cone_ref_length = (exhaust_radius - tr) / math.tan(math.radians(ang_div))
        real_percent = (bell_length / cone_ref_length) * 100 if cone_ref_length else 0
        
        theta_n_deg = math.degrees(theta_n_rad)
        theta_e_deg = math.degrees(theta_e_rad)
        
        lam, cf_i, cf_r = self.calculate_performance(k, pc, pe, theta_e_deg, eps)

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
        
        t_param = np.linspace(0, 1, 100)
        
        theta_conv = np.linspace(math.radians(ang_cov), math.radians(-90), 50)
        x_conv = 1.5 * tr * np.cos(theta_conv)
        y_conv = 1.5 * tr * np.sin(theta_conv) + 1.5 * tr + tr
        
        theta_div_arc = np.linspace(math.radians(-90), math.radians(theta_n_deg - 90), 50)
        x_div_arc = r_div_rel * tr * np.cos(theta_div_arc)
        y_div_arc = r_div_rel * tr * np.sin(theta_div_arc) + r_div_rel * tr + tr
        
        bx = (1 - t_param)**2 * nx + 2 * (1 - t_param) * t_param * qx + t_param**2 * ex
        by = (1 - t_param)**2 * ny + 2 * (1 - t_param) * t_param * qy + t_param**2 * ey
        
        final_x = np.concatenate([x_conv, x_div_arc, bx])
        final_y = np.concatenate([y_conv, y_div_arc, by])

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
            divergent_angle_input=ang_div,
            lambda_eff=lam,
            cf_ideal=cf_i,
            cf_est=cf_r,
            contour_x=final_x,
            contour_y=final_y
        )