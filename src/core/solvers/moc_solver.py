import math
import numpy as np
from src.core.models import NozzleResult

class MOCSolver:
    """
    Solver para Bocal de Comprimento Mínimo (MLN) com Arredondamento de Garganta.
    Gera geometria baseada no Método das Características + Arco Circular.
    """

    def __init__(self):
        self.gamma = 1.4

    def _calculate_epsilon(self, pc: float, pe: float, k: float) -> float:
        pe_mpa = pe / 9.86923
        if pe_mpa >= pc: return 1.0
        termo1 = (2 / (k + 1)) ** (1 / (k - 1))
        termo2 = (pc / pe_mpa) ** (1 / k)
        termo3 = (k + 1) / (k - 1)
        termo4 = 1 - (pe_mpa / pc) ** ((k - 1) / k)
        if termo4 < 0: return 1.0
        return (termo1 * termo2) / math.sqrt(termo3 * termo4)

    def _solve_mach_from_area(self, epsilon: float, k: float) -> float:
        if epsilon <= 1.0: return 1.0
        M = 2.0
        for _ in range(20):
            term1 = (2 / (k + 1)) * (1 + (k - 1) / 2 * M**2)
            exponent = (k + 1) / (2 * (k - 1))
            f = (1 / M) * (term1 ** exponent) - epsilon
            df = (1/M) * exponent * (term1**(exponent-1)) * (2/(k+1)) * (k-1)*M - (1/M**2) * (term1**exponent)
            if abs(f) < 1e-6: return M
            if df == 0: break
            M = M - f / df
        return M

    def prandtl_meyer(self, M: float) -> float:
        if M <= 1.0: return 0.0
        g = self.gamma
        t1 = math.sqrt((g + 1) / (g - 1))
        t2 = math.sqrt(M**2 - 1)
        t3 = math.sqrt((g - 1) / (g + 1))
        return t1 * math.atan(t3 * t2) - math.atan(t2)

    def compute(self, tr: float, k: float, pc: float, pe: float, 
                ang_div: float, ang_cov: float, length_pct: float, rounding_factor: float) -> NozzleResult:
        
        self.gamma = k
        print(f"--- MOC Solver: K={k}, Pc={pc}, Pe={pe} ---")
        
        # 1. Física do Escoamento
        eps = self._calculate_epsilon(pc, pe, k)
        M_exit = self._solve_mach_from_area(eps, k)
        nu_exit = self.prandtl_meyer(M_exit)
        
        # Critério MLN: Theta_max = Nu_exit / 2
        theta_max_rad = nu_exit / 2
        theta_max_deg = math.degrees(theta_max_rad)
        
        # 2. Geometria: Arco da Garganta
        # R_downstream = 0.382 * Rt * Fator
        r_down = tr * 0.382 * (rounding_factor if rounding_factor > 0 else 1.0)
        
        x_points = []
        y_points = []
        
        # Gera o arco de 0 até Theta_max
        steps_arc = 25
        for i in range(steps_arc + 1):
            ang = (i / steps_arc) * theta_max_rad
            # Círculo tangente à garganta: x = R*sin(a), y = Rt + R*(1-cos(a))
            x = r_down * math.sin(ang)
            y = tr + r_down * (1 - math.cos(ang))
            x_points.append(x)
            y_points.append(y)
            
        x_start_moc = x_points[-1]
        y_start_moc = y_points[-1]
        
        # 3. Geometria: Curva de Cancelamento (MOC Kernel Approximation)
        # Comprimento estimado para MLN
        # L = (sqrt(eps)-1)*Rt / tan(theta_max)
        approx_len = ((math.sqrt(eps) - 1) * tr) / math.tan(theta_max_rad)
        
        # Ajuste fino para garantir continuidade
        len_curve = max(approx_len - x_start_moc, approx_len * 0.5)
        
        steps_curve = 100
        curr_x = x_start_moc
        curr_y = y_start_moc
        dx = len_curve / steps_curve
        
        for i in range(1, steps_curve + 1):
            t = i / steps_curve
            # Perfil de ângulo cossenoidal: vai de Theta_max até 0 graus
            theta_loc = theta_max_rad * math.cos(t * math.pi / 2)
            
            dy = math.tan(theta_loc) * dx
            curr_x += dx
            curr_y += dy
            x_points.append(curr_x)
            y_points.append(curr_y)
            
        final_x = np.array(x_points)
        final_y = np.array(y_points)
        
        r_exit_real = final_y[-1]
        l_total = final_x[-1]
        area_exit = math.pi * r_exit_real**2
        area_throat = math.pi * tr**2
        eps_real = area_exit / area_throat
        
        # 4. Cálculo do Ponto 'Q' (Virtual) para evitar crash na UI
        # Q é a interseção da tangente inicial (Theta_max) com a linha de saída (Horizontal)
        # Reta 1: y - y_s = tan(theta_max) * (x - x_s)
        # Reta 2: y = r_exit
        # x_q = x_s + (r_exit - y_s) / tan(theta_max)
        if math.tan(theta_max_rad) > 1e-4:
            xq = x_start_moc + (r_exit_real - y_start_moc) / math.tan(theta_max_rad)
        else:
            xq = l_total / 2
        yq = r_exit_real
        
        print(f"MOC Calculado: L={l_total:.2f}, Eps={eps_real:.2f}, Theta_max={theta_max_deg:.2f}")

        return NozzleResult(
            length=l_total,
            epsilon=eps_real,
            throat_radius=tr,
            exhaust_radius=r_exit_real,
            percent=100.0,
            throat_area=area_throat,
            exhaust_area=area_exit,
            control_points={
                'N': (x_start_moc, y_start_moc), # Fim do arco, início do MOC
                'Q': (xq, yq),                   # Ponto virtual para visualização
                'E': (l_total, r_exit_real)
            },
            angles={'theta_n': theta_max_deg, 'theta_e': 0.0},
            rounding_factor=rounding_factor,
            cone_ref_length=0,
            divergent_angle_input=ang_div,
            lambda_eff=0.992,
            cf_ideal=0.0,
            cf_est=0.0,
            contour_x=final_x,
            contour_y=final_y
        )