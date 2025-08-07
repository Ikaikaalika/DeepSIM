"""
Flash Calculations Module
Advanced flash calculations for phase equilibrium
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

from .property_engine import PropertyEngine

logger = logging.getLogger(__name__)

class FlashCalculator:
    """
    Advanced flash calculations for vapor-liquid equilibrium
    """
    
    def __init__(self, property_engine: PropertyEngine):
        self.property_engine = property_engine
        
    def isothermal_flash(self, 
                        components: List[str],
                        z: List[float],      # Feed composition
                        T: float,            # Temperature (K)
                        P: float,            # Pressure (Pa)
                        method: str = 'PENG-ROBINSON') -> Dict:
        """
        Perform isothermal flash calculation (PT flash)
        """
        
        # Use the property engine's flash calculation
        return self.property_engine.flash_calculation(
            components=components,
            z=z,
            T=T,
            P=P,
            method=method
        )
    
    def adiabatic_flash(self,
                       components: List[str], 
                       z: List[float],
                       H: float,            # Enthalpy (J/mol)
                       P: float,            # Pressure (Pa)
                       T_guess: float = 350.0,  # Initial temperature guess
                       method: str = 'PENG-ROBINSON') -> Dict:
        """
        Perform adiabatic flash calculation (PH flash)
        """
        
        try:
            # Iterate to find temperature that matches enthalpy
            T = T_guess
            
            for iteration in range(50):
                # Calculate flash at current temperature
                flash_result = self.isothermal_flash(components, z, T, P, method)
                
                if not flash_result.get('converged', False):
                    break
                
                # Calculate mixture enthalpy
                H_calc = self._calculate_mixture_enthalpy(
                    components, z, T, P, flash_result, method
                )
                
                # Check convergence
                dH = abs(H_calc - H)
                if dH < 100:  # J/mol tolerance
                    flash_result['temperature'] = T
                    flash_result['enthalpy_target'] = H
                    flash_result['enthalpy_calculated'] = H_calc
                    flash_result['adiabatic_converged'] = True
                    flash_result['adiabatic_iterations'] = iteration + 1
                    return flash_result
                
                # Update temperature using derivative approximation
                dT = 1.0  # K
                H_plus = self._calculate_mixture_enthalpy(
                    components, z, T + dT, P, 
                    self.isothermal_flash(components, z, T + dT, P, method), 
                    method
                )
                
                dH_dT = (H_plus - H_calc) / dT
                if abs(dH_dT) > 1e-6:
                    T_new = T + (H - H_calc) / dH_dT
                    T = max(200, min(800, T_new))  # Reasonable bounds
                else:
                    break
            
            # If not converged, return with warning
            flash_result = self.isothermal_flash(components, z, T, P, method)
            flash_result['temperature'] = T
            flash_result['adiabatic_converged'] = False
            flash_result['warning'] = 'Adiabatic flash did not converge'
            return flash_result
            
        except Exception as e:
            logger.error(f"Adiabatic flash failed: {e}")
            return {
                'converged': False,
                'error': str(e),
                'temperature': T_guess,
                'vapor_fraction': 0.5
            }
    
    def pressure_flash(self,
                      components: List[str],
                      z: List[float], 
                      T: float,
                      V: float,             # Specified vapor fraction
                      P_guess: float = 101325,  # Initial pressure guess
                      method: str = 'PENG-ROBINSON') -> Dict:
        """
        Perform flash calculation at specified vapor fraction (TV flash)
        """
        
        try:
            P = P_guess
            
            for iteration in range(50):
                # Calculate flash at current pressure
                flash_result = self.isothermal_flash(components, z, T, P, method)
                
                if not flash_result.get('converged', False):
                    break
                
                V_calc = flash_result.get('vapor_fraction', 0.0)
                
                # Check convergence
                dV = abs(V_calc - V)
                if dV < 0.001:  # Vapor fraction tolerance
                    flash_result['pressure'] = P
                    flash_result['vapor_fraction_target'] = V
                    flash_result['tv_converged'] = True
                    flash_result['tv_iterations'] = iteration + 1
                    return flash_result
                
                # Update pressure using derivative approximation
                dP = P * 0.01  # 1% pressure change
                P_plus = P + dP
                V_plus = self.isothermal_flash(components, z, T, P_plus, method).get('vapor_fraction', 0.0)
                
                dV_dP = (V_plus - V_calc) / dP
                if abs(dV_dP) > 1e-12:
                    P_new = P + (V - V_calc) / dV_dP
                    P = max(1000, min(1e7, P_new))  # Reasonable bounds
                else:
                    break
            
            # If not converged, return with warning
            flash_result = self.isothermal_flash(components, z, T, P, method)
            flash_result['pressure'] = P
            flash_result['tv_converged'] = False
            flash_result['warning'] = 'TV flash did not converge'
            return flash_result
            
        except Exception as e:
            logger.error(f"TV flash failed: {e}")
            return {
                'converged': False,
                'error': str(e),
                'pressure': P_guess,
                'vapor_fraction': V
            }
    
    def _calculate_mixture_enthalpy(self,
                                  components: List[str],
                                  z: List[float],
                                  T: float,
                                  P: float, 
                                  flash_result: Dict,
                                  method: str) -> float:
        """
        Calculate mixture enthalpy from flash result
        """
        
        try:
            vapor_fraction = flash_result.get('vapor_fraction', 0.0)
            
            if vapor_fraction == 0.0:
                # Pure liquid
                props = self.property_engine.calculate_properties(
                    components, z, T, P, method
                )
                return props.get('enthalpy', 0.0)
            
            elif vapor_fraction == 1.0:
                # Pure vapor  
                props = self.property_engine.calculate_properties(
                    components, z, T, P, method
                )
                return props.get('enthalpy', 0.0)
            
            else:
                # Two-phase mixture
                x = flash_result.get('liquid_composition', z)
                y = flash_result.get('vapor_composition', z)
                
                # Calculate liquid enthalpy
                liquid_props = self.property_engine.calculate_properties(
                    components, x, T, P, method
                )
                H_liquid = liquid_props.get('enthalpy', 0.0)
                
                # Calculate vapor enthalpy
                vapor_props = self.property_engine.calculate_properties(
                    components, y, T, P, method
                )
                H_vapor = vapor_props.get('enthalpy', 0.0)
                
                # Mixture enthalpy
                H_mix = (1 - vapor_fraction) * H_liquid + vapor_fraction * H_vapor
                return H_mix
                
        except Exception as e:
            logger.warning(f"Enthalpy calculation failed: {e}")
            return 0.0
    
    def three_phase_flash(self,
                         components: List[str],
                         z: List[float],
                         T: float,
                         P: float,
                         method: str = 'PENG-ROBINSON') -> Dict:
        """
        Three-phase flash calculation (vapor-liquid1-liquid2)
        Simplified implementation for demonstration
        """
        
        try:
            # For simplicity, first try two-phase flash
            two_phase = self.isothermal_flash(components, z, T, P, method)
            
            # Check if liquid phase might split (simplified criterion)
            vapor_frac = two_phase.get('vapor_fraction', 0.0)
            
            if 0.1 < vapor_frac < 0.9:
                # Potential for liquid-liquid split
                # This is a very simplified approach
                
                x = two_phase.get('liquid_composition', z)
                
                # Check for immiscibility (simplified)
                # In a real implementation, this would use activity coefficients
                immiscible = any(abs(x[i] - z[i]) > 0.3 for i in range(len(x)))
                
                if immiscible:
                    # Assume phase split occurs
                    # This is highly simplified and not thermodynamically rigorous
                    
                    return {
                        'converged': True,
                        'phases': 3,
                        'vapor_fraction': vapor_frac,
                        'liquid1_fraction': (1 - vapor_frac) * 0.6,
                        'liquid2_fraction': (1 - vapor_frac) * 0.4,
                        'vapor_composition': two_phase.get('vapor_composition', z),
                        'liquid1_composition': x,
                        'liquid2_composition': [1-xi if xi < 0.5 else xi for xi in x],
                        'note': 'Simplified three-phase calculation'
                    }
            
            # Return two-phase result
            two_phase['phases'] = 2 if 0 < vapor_frac < 1 else 1
            return two_phase
            
        except Exception as e:
            logger.error(f"Three-phase flash failed: {e}")
            return {
                'converged': False,
                'error': str(e),
                'phases': 1
            }