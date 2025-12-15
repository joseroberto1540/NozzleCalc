class UnitManager:
    """Gerencia conversões e fatores de escala."""
    
    # Fatores para converter DA unidade X PARA a unidade base do Solver
    # Base Length: mm
    # Base Pressure (Chamber): MPa
    # Base Pressure (Exhaust): atm
    
    CONVERTERS = {
        'length_to_mm': {
            'mm': 1.0, 'cm': 10.0, 'm': 1000.0
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
        factor = UnitManager.CONVERTERS[category].get(from_unit, 1.0)
        if reverse:
            return value / factor
        return value * factor