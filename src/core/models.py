# src/core/models.py
from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np

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
    lambda_eff: float
    cf_ideal: float
    cf_est: float
    contour_x: np.ndarray 
    contour_y: np.ndarray