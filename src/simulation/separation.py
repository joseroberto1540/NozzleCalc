import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
from src.core.models import NozzleResult

@dataclass
class SimulationInput:
    chamber_pressure: float
    ambient_pressure: float
    gamma: float

@dataclass
class SeparationResult:
    has_separation: bool
    separation_x: Optional[float]
    separation_mach: Optional[float]
    separation_pressure: Optional[float]
    safety_margin: float
    
    # Campos obrigatórios para o diagnóstico
    geometric_warnings: List[str] = field(default_factory=list)
    wall_angles: np.ndarray = field(default_factory=lambda: np.array([]))

    axis_x: np.ndarray = field(default_factory=lambda: np.array([]))
    mach_distribution: np.ndarray = field(default_factory=lambda: np.array([]))
    wall_pressure: np.ndarray = field(default_factory=lambda: np.array([]))
    schmucker_limit: np.ndarray = field(default_factory=lambda: np.array([]))

class FlowSimulation:
    def __init__(self, geometry: NozzleResult, inputs: SimulationInput):
        self.geo = geometry
        self.inputs = inputs
        self.warnings = []

    def run(self) -> SeparationResult:
        # 1. Dados Brutos
        div_x, div_y, area_ratios = self._extract_divergent_section()

        # 2. Análise Geométrica (Onde estava o problema)
        self._analyze_geometry_quality(div_x, div_y)

        # 3. Solver Físico
        mach_profile = self._solve_mach_distribution(area_ratios)
        pressure_profile = self._calculate_pressure_profile(mach_profile)
        
        # 4. Critério de Descolamento
        result = self._analyze_separation(div_x, mach_profile, pressure_profile)
        
        # Injeta avisos
        result.geometric_warnings = self.warnings
        
        # Se houve erro geométrico, invalidamos o resultado visualmente
        if len(self.warnings) > 0:
            result.safety_margin = -1.0 # Força vermelho
            result.has_separation = True
            
        return result

    def _extract_divergent_section(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        throat_idx = np.argmin(self.geo.contour_y)
        throat_radius = self.geo.contour_y[throat_idx]
        throat_area = np.pi * (throat_radius ** 2)

        div_x = self.geo.contour_x[throat_idx:]
        div_y = self.geo.contour_y[throat_idx:]
        
        # Garante que x começa em 0 para facilitar a matemática
        div_x = div_x - div_x[0]
        
        local_areas = np.pi * (div_y ** 2)
        area_ratios = local_areas / throat_area
        
        return div_x, div_y, area_ratios

    def _analyze_geometry_quality(self, x: np.ndarray, y: np.ndarray):
        """
        Analisa a geometria usando vetores de deslocamento físico.
        Impede matematicamente o erro de 180 graus.
        """
        if len(x) < 5: return

        # Detecta escala (m ou mm)
        span = x[-1] - x[0]
        is_meters = span < 1.0
        # Tolerância: Procura um ponto a 0.5mm de distância física
        LOOKAHEAD_DIST = 0.0005 if is_meters else 0.5
        unit = "m" if is_meters else "mm"

        # --- CHECK 1: Saída da Garganta (Throat Exit) ---
        # Encontra o índice do primeiro ponto que está "longe o suficiente" (dx > 0.5mm)
        # Isso ignora qualquer ruído microscópico nos primeiros índices.
        indices_ahead = np.where(x > (x[0] + LOOKAHEAD_DIST))[0]
        
        if len(indices_ahead) > 0:
            idx = indices_ahead[0]
            
            # Cálculo vetorial simples
            dx = x[idx] - x[0] # Sempre positivo por definição
            dy = y[idx] - y[0]
            
            # Como dx > 0, arctan2 está limitado a (-90, 90). 180 é impossível.
            angle = np.degrees(np.arctan2(dy, dx))
            
            print(f"[GEO DEBUG] Throat Angle (at {LOOKAHEAD_DIST}{unit}): {angle:.4f}°")

            # Aumentei a tolerância para 2.0 graus para evitar falsos positivos em tubeiras pequenas
            if abs(angle) > 2.0:
                self.warnings.append(f"CRITICAL: Sharp throat exit ({angle:.1f}°). Flow may detach. Increasing TRF is suggested.")

        # --- CHECK 2: Quinas no corpo (Kinks) ---
        # Percorre a tubeira verificando mudanças de ângulo em intervalos fixos
        # Passo: a cada 2% do comprimento
        step_idx = max(1, len(x) // 50) 
        
        for i in range(0, len(x) - step_idx * 2, step_idx):
            # Pontos: A -> B -> C
            idx_a = i
            idx_b = i + step_idx
            idx_c = i + step_idx * 2
            
            # Vetor 1 (A->B)
            dx1 = x[idx_b] - x[idx_a]
            dy1 = y[idx_b] - y[idx_a]
            ang1 = np.degrees(np.arctan2(dy1, dx1))
            
            # Vetor 2 (B->C)
            dx2 = x[idx_c] - x[idx_b]
            dy2 = y[idx_c] - y[idx_b]
            ang2 = np.degrees(np.arctan2(dy2, dx2))
            
            diff = abs(ang2 - ang1)
            
            # Se a parede dobrar mais que 3 graus de repente
            if diff > 3.0:
                loc = x[idx_b]
                self.warnings.append(f"DISCONTINUITY: Kink of {diff:.1f}° detected at X ≈ {loc:.3f}")
                # Reporta apenas o primeiro erro grave para não poluir
                break 

    def _solve_mach_distribution(self, area_ratios: np.ndarray) -> np.ndarray:
        # Solver rápido usando interpolação para robustez
        # (Newton-Raphson pode falhar com inputs ruins, interpolação nunca falha)
        # Criamos uma tabela pré-calculada de Mach vs AreaRatio
        g = self.inputs.gamma
        
        # Tabela de Mach 1.0 a 10.0
        mach_table = np.linspace(1.0, 10.0, 1000)
        
        # Fórmula da Razão de Área
        term1 = 1 / mach_table**2
        term2 = (2 + (g - 1) * mach_table**2) / (g + 1)
        exp = (g + 1) / (g - 1)
        area_table = np.sqrt(term1 * (term2 ** exp))
        
        # Interpola o Mach real baseado na área da tubeira atual
        return np.interp(area_ratios, area_table, mach_table)

    def _calculate_pressure_profile(self, mach_profile: np.ndarray) -> np.ndarray:
        g = self.inputs.gamma
        base = 1 + (g - 1) / 2 * np.power(mach_profile, 2)
        exponent = -g / (g - 1)
        return self.inputs.chamber_pressure * np.power(base, exponent)

    def _analyze_separation(self, x_coords: np.ndarray, mach: np.ndarray, pressure: np.ndarray) -> SeparationResult:
        # Critério Schmucker (simplificado para robustez)
        term = 1.88 * mach - 1
        term = np.maximum(term, 0.6) # Evita números negativos/zero
        schmucker_ratio = np.power(term, -0.64)
        
        p_limit = self.inputs.ambient_pressure * schmucker_ratio
        
        # Detecta onde P_wall cruza P_limit
        # Usamos argmax para achar o primeiro True
        sep_mask = pressure < p_limit
        has_separation = np.any(sep_mask)
        
        sep_x = None
        sep_p = None
        
        if has_separation:
            idx = np.argmax(sep_mask) # Primeiro índice onde ocorre
            sep_x = x_coords[idx]
            sep_p = pressure[idx]

        # Margem de segurança
        if len(pressure) > 0:
            # Pega o ponto mais crítico (menor margem)
            margins = (pressure - p_limit) / (pressure + 1e-9)
            min_margin = np.min(margins)
        else:
            min_margin = 0.0

        return SeparationResult(
            has_separation=has_separation,
            separation_x=sep_x,
            separation_mach=None,
            separation_pressure=sep_p,
            safety_margin=min_margin,
            axis_x=x_coords,
            mach_distribution=mach,
            wall_pressure=pressure,
            schmucker_limit=p_limit
        )