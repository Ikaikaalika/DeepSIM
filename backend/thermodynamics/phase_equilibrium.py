"""
Phase Equilibrium Calculations
Advanced phase equilibrium methods for process simulation
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

from .component_database import ComponentDatabase

logger = logging.getLogger(__name__)

class PhaseEquilibrium:
    """
    Phase equilibrium calculations using various methods
    """
    
    def __init__(self):
        self.component_db = ComponentDatabase()
        
    def bubble_point(self,
                    components: List[str],
                    x: List[float],        # Liquid composition
                    P: float,              # Pressure (Pa)
                    T_guess: float = 350.0,
                    method: str = 'ANTOINE') -> Dict:
        """
        Calculate bubble point temperature
        """
        
        try:
            T = T_guess
            
            for iteration in range(50):
                # Calculate K-values at current temperature
                K_values = self._calculate_k_values(components, T, P, method)
                
                # Bubble point criterion: sum(x_i * K_i) = 1
                f = sum(x[i] * K_values[i] for i in range(len(components))) - 1.0
                
                if abs(f) < 1e-6:
                    # Calculate vapor composition
                    y = [x[i] * K_values[i] for i in range(len(components))]
                    
                    return {
                        'converged': True,
                        'temperature': T,
                        'pressure': P,
                        'liquid_composition': x,
                        'vapor_composition': y,
                        'K_values': K_values,
                        'iterations': iteration + 1
                    }
                
                # Calculate derivative for Newton-Raphson
                dT = 1.0  # K
                K_values_plus = self._calculate_k_values(components, T + dT, P, method)
                f_plus = sum(x[i] * K_values_plus[i] for i in range(len(components))) - 1.0
                df_dT = (f_plus - f) / dT
                
                if abs(df_dT) > 1e-10:
                    T_new = T - f / df_dT
                    T = max(200, min(800, T_new))  # Reasonable bounds
                else:
                    break
            
            return {
                'converged': False,
                'temperature': T,
                'error': 'Bubble point did not converge'
            }
            
        except Exception as e:
            logger.error(f"Bubble point calculation failed: {e}")
            return {
                'converged': False,
                'error': str(e),
                'temperature': T_guess
            }
    
    def dew_point(self,
                 components: List[str],
                 y: List[float],         # Vapor composition  
                 P: float,               # Pressure (Pa)
                 T_guess: float = 350.0,
                 method: str = 'ANTOINE') -> Dict:
        """
        Calculate dew point temperature
        """
        
        try:
            T = T_guess
            
            for iteration in range(50):
                # Calculate K-values at current temperature
                K_values = self._calculate_k_values(components, T, P, method)
                
                # Dew point criterion: sum(y_i / K_i) = 1
                f = sum(y[i] / max(K_values[i], 1e-10) for i in range(len(components))) - 1.0
                
                if abs(f) < 1e-6:
                    # Calculate liquid composition
                    x = [y[i] / max(K_values[i], 1e-10) for i in range(len(components))]
                    
                    return {
                        'converged': True,
                        'temperature': T,
                        'pressure': P,
                        'liquid_composition': x,
                        'vapor_composition': y,
                        'K_values': K_values,
                        'iterations': iteration + 1
                    }
                
                # Calculate derivative for Newton-Raphson
                dT = 1.0  # K
                K_values_plus = self._calculate_k_values(components, T + dT, P, method)
                f_plus = sum(y[i] / max(K_values_plus[i], 1e-10) for i in range(len(components))) - 1.0
                df_dT = (f_plus - f) / dT
                
                if abs(df_dT) > 1e-10:
                    T_new = T - f / df_dT
                    T = max(200, min(800, T_new))  # Reasonable bounds
                else:
                    break
            
            return {
                'converged': False,
                'temperature': T,
                'error': 'Dew point did not converge'
            }
            
        except Exception as e:
            logger.error(f"Dew point calculation failed: {e}")
            return {
                'converged': False,
                'error': str(e),
                'temperature': T_guess
            }
    
    def bubble_pressure(self,
                       components: List[str],
                       x: List[float],      # Liquid composition
                       T: float,            # Temperature (K)
                       P_guess: float = 101325,
                       method: str = 'ANTOINE') -> Dict:
        """
        Calculate bubble point pressure
        """
        
        try:
            if method == 'ANTOINE':
                # For Antoine equation, pressure calculation is direct
                P_sat_values = []
                
                for comp in components:
                    comp_data = self.component_db.get_component(comp)
                    if comp_data and 'antoine_coefficients' in comp_data:
                        A, B, C = comp_data['antoine_coefficients']
                        # Antoine equation: log10(P_sat) = A - B/(T + C)
                        P_sat = 10**(A - B/(T - 273.15 + C))  # mmHg
                        P_sat_pa = P_sat * 133.322  # Convert to Pa
                        P_sat_values.append(P_sat_pa)
                    else:
                        P_sat_values.append(101325)  # Default
                
                # Bubble pressure: P = sum(x_i * P_sat_i)
                P_bubble = sum(x[i] * P_sat_values[i] for i in range(len(components)))
                
                # Calculate K-values and vapor composition
                K_values = [P_sat_values[i] / P_bubble for i in range(len(components))]
                y = [x[i] * K_values[i] for i in range(len(components))]
                
                return {
                    'converged': True,
                    'temperature': T,
                    'pressure': P_bubble,
                    'liquid_composition': x,
                    'vapor_composition': y,
                    'K_values': K_values,
                    'vapor_pressures': P_sat_values
                }
            else:
                # For other methods, use iterative approach
                P = P_guess
                
                for iteration in range(50):
                    K_values = self._calculate_k_values(components, T, P, method)
                    
                    # Bubble pressure criterion
                    y_sum = sum(x[i] * K_values[i] for i in range(len(components)))
                    
                    if abs(y_sum - 1.0) < 1e-6:
                        y = [x[i] * K_values[i] for i in range(len(components))]
                        
                        return {
                            'converged': True,
                            'temperature': T,
                            'pressure': P,
                            'liquid_composition': x,
                            'vapor_composition': y,
                            'K_values': K_values,
                            'iterations': iteration + 1
                        }
                    
                    # Update pressure
                    P = P * y_sum  # Simple correction
                    P = max(1000, min(1e7, P))  # Bounds
                
                return {
                    'converged': False,
                    'pressure': P,
                    'error': 'Bubble pressure did not converge'
                }
                
        except Exception as e:
            logger.error(f"Bubble pressure calculation failed: {e}")
            return {
                'converged': False,
                'error': str(e),
                'pressure': P_guess
            }
    
    def dew_pressure(self,
                    components: List[str],
                    y: List[float],       # Vapor composition
                    T: float,             # Temperature (K) 
                    P_guess: float = 101325,
                    method: str = 'ANTOINE') -> Dict:
        """
        Calculate dew point pressure
        """
        
        try:
            if method == 'ANTOINE':
                # For Antoine equation, calculate directly
                P_sat_values = []
                
                for comp in components:
                    comp_data = self.component_db.get_component(comp)
                    if comp_data and 'antoine_coefficients' in comp_data:
                        A, B, C = comp_data['antoine_coefficients']
                        P_sat = 10**(A - B/(T - 273.15 + C))  # mmHg
                        P_sat_pa = P_sat * 133.322  # Convert to Pa
                        P_sat_values.append(P_sat_pa)
                    else:
                        P_sat_values.append(101325)  # Default
                
                # Dew pressure: P = 1 / sum(y_i / P_sat_i)
                P_dew = 1.0 / sum(y[i] / P_sat_values[i] for i in range(len(components)))
                
                # Calculate K-values and liquid composition
                K_values = [P_sat_values[i] / P_dew for i in range(len(components))]
                x = [y[i] / K_values[i] for i in range(len(components))]
                
                return {
                    'converged': True,
                    'temperature': T,
                    'pressure': P_dew,
                    'liquid_composition': x,
                    'vapor_composition': y,
                    'K_values': K_values,
                    'vapor_pressures': P_sat_values
                }
            else:
                # Iterative approach for other methods
                P = P_guess
                
                for iteration in range(50):
                    K_values = self._calculate_k_values(components, T, P, method)
                    
                    # Dew pressure criterion
                    x_sum = sum(y[i] / max(K_values[i], 1e-10) for i in range(len(components)))
                    
                    if abs(x_sum - 1.0) < 1e-6:
                        x = [y[i] / max(K_values[i], 1e-10) for i in range(len(components))]
                        
                        return {
                            'converged': True,
                            'temperature': T,
                            'pressure': P,
                            'liquid_composition': x,
                            'vapor_composition': y,
                            'K_values': K_values,
                            'iterations': iteration + 1
                        }
                    
                    # Update pressure
                    P = P / x_sum  # Simple correction
                    P = max(1000, min(1e7, P))  # Bounds
                
                return {
                    'converged': False,
                    'pressure': P,
                    'error': 'Dew pressure did not converge'
                }
                
        except Exception as e:
            logger.error(f"Dew pressure calculation failed: {e}")
            return {
                'converged': False,
                'error': str(e),
                'pressure': P_guess
            }
    
    def _calculate_k_values(self,
                           components: List[str],
                           T: float,
                           P: float,
                           method: str) -> List[float]:
        """
        Calculate K-values using specified method
        """
        
        K_values = []
        
        for comp in components:
            comp_data = self.component_db.get_component(comp)
            
            if method == 'ANTOINE' and comp_data and 'antoine_coefficients' in comp_data:
                A, B, C = comp_data['antoine_coefficients']
                # Antoine equation: log10(P_sat) = A - B/(T + C)
                P_sat = 10**(A - B/(T - 273.15 + C))  # mmHg
                P_sat_pa = P_sat * 133.322  # Convert to Pa
                K = P_sat_pa / P
            
            elif method == 'RIEDEL' and comp_data:
                # Riedel equation (simplified)
                Tc = comp_data.get('critical_temperature', 500)
                Pc = comp_data.get('critical_pressure', 5e6)
                
                # Simplified Riedel correlation
                Tr = T / Tc
                if Tr < 1.0:
                    P_sat = Pc * np.exp(5.37 * (1 + comp_data.get('acentric_factor', 0.1)) * (1 - 1/Tr))
                    K = P_sat / P
                else:
                    K = 1.0  # Above critical temperature
            
            else:
                # Default ideal K-value
                K = 1.0
            
            K_values.append(max(0.001, K))  # Prevent negative/zero K-values
        
        return K_values
    
    def azeotrope_search(self,
                        components: List[str],
                        P: float,
                        T_range: Tuple[float, float] = (250, 450),
                        method: str = 'ANTOINE') -> Dict:
        """
        Search for azeotropic conditions (simplified binary system)
        """
        
        if len(components) != 2:
            return {'error': 'Azeotrope search currently limited to binary systems'}
        
        try:
            azeotropes = []
            T_min, T_max = T_range
            
            # Search over temperature range
            for T in np.linspace(T_min, T_max, 100):
                
                # Calculate K-values
                K_values = self._calculate_k_values(components, T, P, method)
                
                # Check for azeotrope condition: K1 = K2 (for binary)
                if abs(K_values[0] - K_values[1]) < 0.01:
                    
                    # Calculate composition at azeotrope
                    # For binary azeotrope: x1 = y1, x2 = y2
                    # From material balance: x1 + x2 = 1
                    # From equilibrium: y1 = K1*x1, y2 = K2*x2
                    # With y1 = x1, y2 = x2: x1 = K1*x1, x2 = K2*x2
                    
                    if abs(K_values[0] - 1.0) < 0.1:  # Near unity
                        x1 = 1.0 / (1.0 + (K_values[1] - 1.0)/(K_values[0] - 1.0))
                        x1 = max(0, min(1, x1))
                        x2 = 1.0 - x1
                        
                        azeotropes.append({
                            'temperature': T,
                            'pressure': P,
                            'composition': [x1, x2],
                            'K_values': K_values,
                            'type': 'minimum' if T < (T_min + T_max)/2 else 'maximum'
                        })
            
            return {
                'found_azeotropes': len(azeotropes) > 0,
                'azeotropes': azeotropes,
                'search_range': T_range,
                'components': components
            }
            
        except Exception as e:
            logger.error(f"Azeotrope search failed: {e}")
            return {
                'error': str(e),
                'found_azeotropes': False
            }