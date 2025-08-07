"""
Thermodynamic Property Engine
Provides industrial-grade property calculations using multiple methods
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

try:
    import thermo
    from thermo import Chemical, Mixture
    THERMO_AVAILABLE = True
except ImportError:
    THERMO_AVAILABLE = False
    logging.warning("thermo library not available. Install with: pip install thermo")

try:
    import CoolProp.CoolProp as CP
    COOLPROP_AVAILABLE = True
except ImportError:
    COOLPROP_AVAILABLE = False
    logging.warning("CoolProp not available. Install with: pip install CoolProp")

from .component_database import ComponentDatabase

logger = logging.getLogger(__name__)

class PropertyEngine:
    """
    Main thermodynamic property calculation engine
    Supports multiple property methods similar to Aspen Plus
    """
    
    def __init__(self):
        self.component_db = ComponentDatabase()
        self.available_methods = self._get_available_methods()
        
    def _get_available_methods(self) -> List[str]:
        """Get list of available thermodynamic methods"""
        methods = ['IDEAL']  # Always available
        
        if THERMO_AVAILABLE:
            methods.extend([
                'PENG-ROBINSON',
                'SRK', 
                'UNIFAC',
                'WILSON',
                'NRTL'
            ])
            
        if COOLPROP_AVAILABLE:
            methods.extend([
                'COOLPROP-PR',
                'COOLPROP-SRK',
                'REFPROP'
            ])
            
        return methods
    
    def calculate_properties(self, 
                           components: List[str],
                           mole_fractions: List[float],
                           temperature: float,  # K
                           pressure: float,     # Pa
                           method: str = 'PENG-ROBINSON') -> Dict:
        """
        Calculate thermodynamic properties for a mixture
        
        Args:
            components: List of component names or CAS numbers
            mole_fractions: Mole fractions (must sum to 1.0)
            temperature: Temperature in Kelvin
            pressure: Pressure in Pascal
            method: Thermodynamic method to use
            
        Returns:
            Dictionary with calculated properties
        """
        
        if method not in self.available_methods:
            logger.warning(f"Method {method} not available. Using IDEAL.")
            method = 'IDEAL'
            
        if abs(sum(mole_fractions) - 1.0) > 1e-6:
            raise ValueError("Mole fractions must sum to 1.0")
            
        try:
            if method == 'IDEAL':
                return self._ideal_properties(components, mole_fractions, temperature, pressure)
            elif method in ['PENG-ROBINSON', 'SRK', 'UNIFAC'] and THERMO_AVAILABLE:
                return self._thermo_properties(components, mole_fractions, temperature, pressure, method)
            elif method.startswith('COOLPROP') and COOLPROP_AVAILABLE:
                return self._coolprop_properties(components, mole_fractions, temperature, pressure, method)
            else:
                logger.warning(f"Falling back to ideal properties for {method}")
                return self._ideal_properties(components, mole_fractions, temperature, pressure)
                
        except Exception as e:
            logger.error(f"Property calculation failed: {e}")
            return self._ideal_properties(components, mole_fractions, temperature, pressure)
    
    def _ideal_properties(self, components: List[str], z: List[float], 
                         T: float, P: float) -> Dict:
        """Calculate ideal gas properties"""
        
        properties = {
            'temperature': T,
            'pressure': P,
            'mole_fractions': z,
            'method': 'IDEAL',
            'phase': 'vapor',  # Assume vapor for ideal
            'vapor_fraction': 1.0
        }
        
        # Get component data
        comp_data = []
        for comp in components:
            data = self.component_db.get_component(comp)
            if data:
                comp_data.append(data)
            else:
                logger.warning(f"Component {comp} not found in database")
                comp_data.append(self._default_component_data(comp))
        
        # Calculate mixture molecular weight
        mw_mix = sum(z[i] * comp_data[i]['molecular_weight'] for i in range(len(components)))
        properties['molecular_weight'] = mw_mix
        
        # Ideal gas density
        R = 8.314  # J/mol/K
        density_molar = P / (R * T)  # mol/m³
        properties['density'] = density_molar * mw_mix / 1000  # kg/m³
        
        # Heat capacity (ideal gas)
        cp_mix = sum(z[i] * self._ideal_cp(comp_data[i], T) for i in range(len(components)))
        properties['heat_capacity'] = cp_mix  # J/mol/K
        
        # Enthalpy (relative to reference)
        h_mix = sum(z[i] * self._ideal_enthalpy(comp_data[i], T) for i in range(len(components)))
        properties['enthalpy'] = h_mix  # J/mol
        
        return properties
    
    def _thermo_properties(self, components: List[str], z: List[float],
                          T: float, P: float, method: str) -> Dict:
        """Calculate properties using thermo library"""
        
        if not THERMO_AVAILABLE:
            return self._ideal_properties(components, z, T, P)
            
        try:
            # Create mixture using thermo
            mixture = Mixture(components, zs=z, T=T, P=P)
            
            properties = {
                'temperature': T,
                'pressure': P,
                'mole_fractions': z,
                'method': method,
                'molecular_weight': mixture.MW,
                'density': mixture.rho,
                'heat_capacity': mixture.Cp,
                'enthalpy': mixture.H,
                'entropy': mixture.S,
                'vapor_fraction': getattr(mixture, 'beta', 1.0)
            }
            
            # Phase determination
            if hasattr(mixture, 'phase'):
                properties['phase'] = mixture.phase
            else:
                properties['phase'] = 'liquid' if mixture.rho > 100 else 'vapor'
                
            # Additional properties if available
            if hasattr(mixture, 'mu'):
                properties['viscosity'] = mixture.mu
            if hasattr(mixture, 'k'):
                properties['thermal_conductivity'] = mixture.k
                
            return properties
            
        except Exception as e:
            logger.error(f"Thermo calculation failed: {e}")
            return self._ideal_properties(components, z, T, P)
    
    def _coolprop_properties(self, components: List[str], z: List[float],
                            T: float, P: float, method: str) -> Dict:
        """Calculate properties using CoolProp"""
        
        if not COOLPROP_AVAILABLE or len(components) > 1:
            return self._thermo_properties(components, z, T, P, 'PENG-ROBINSON')
        
        try:
            comp = components[0]  # CoolProp works best with pure components
            
            # Try to get CoolProp fluid name
            fluid_name = self._get_coolprop_name(comp)
            if not fluid_name:
                return self._thermo_properties(components, z, T, P, 'PENG-ROBINSON')
            
            properties = {
                'temperature': T,
                'pressure': P,
                'mole_fractions': z,
                'method': method,
                'molecular_weight': CP.PropsSI('M', fluid_name),
                'density': CP.PropsSI('D', 'T', T, 'P', P, fluid_name),
                'heat_capacity': CP.PropsSI('C', 'T', T, 'P', P, fluid_name),
                'enthalpy': CP.PropsSI('H', 'T', T, 'P', P, fluid_name),
                'entropy': CP.PropsSI('S', 'T', T, 'P', P, fluid_name),
                'viscosity': CP.PropsSI('V', 'T', T, 'P', P, fluid_name),
                'thermal_conductivity': CP.PropsSI('L', 'T', T, 'P', P, fluid_name)
            }
            
            # Phase determination
            try:
                phase_index = CP.PropsSI('Phase', 'T', T, 'P', P, fluid_name)
                if phase_index == 0:
                    properties['phase'] = 'liquid'
                    properties['vapor_fraction'] = 0.0
                elif phase_index == 6:
                    properties['phase'] = 'vapor'
                    properties['vapor_fraction'] = 1.0
                else:
                    properties['phase'] = 'two_phase'
                    properties['vapor_fraction'] = CP.PropsSI('Q', 'T', T, 'P', P, fluid_name)
            except:
                properties['phase'] = 'unknown'
                properties['vapor_fraction'] = 1.0
                
            return properties
            
        except Exception as e:
            logger.error(f"CoolProp calculation failed: {e}")
            return self._thermo_properties(components, z, T, P, 'PENG-ROBINSON')
    
    def flash_calculation(self, components: List[str], z: List[float],
                         T: float, P: float, method: str = 'PENG-ROBINSON') -> Dict:
        """
        Perform two-phase flash calculation
        Returns vapor and liquid compositions and vapor fraction
        """
        
        try:
            if THERMO_AVAILABLE and method != 'IDEAL':
                mixture = Mixture(components, zs=z, T=T, P=P)
                
                # Check if two-phase
                if hasattr(mixture, 'beta') and 0 < mixture.beta < 1:
                    return {
                        'vapor_fraction': mixture.beta,
                        'vapor_composition': mixture.ys,
                        'liquid_composition': mixture.xs,
                        'K_values': [mixture.ys[i]/mixture.xs[i] for i in range(len(components))],
                        'converged': True
                    }
                else:
                    # Single phase
                    if mixture.rho < 100:  # Vapor
                        return {
                            'vapor_fraction': 1.0,
                            'vapor_composition': z,
                            'liquid_composition': [0.0] * len(components),
                            'K_values': [float('inf')] * len(components),
                            'converged': True
                        }
                    else:  # Liquid
                        return {
                            'vapor_fraction': 0.0,
                            'vapor_composition': [0.0] * len(components),
                            'liquid_composition': z,
                            'K_values': [0.0] * len(components),
                            'converged': True
                        }
            else:
                # Simple ideal flash
                return self._ideal_flash(components, z, T, P)
                
        except Exception as e:
            logger.error(f"Flash calculation failed: {e}")
            return self._ideal_flash(components, z, T, P)
    
    def _ideal_flash(self, components: List[str], z: List[float], T: float, P: float) -> Dict:
        """Simple ideal flash calculation using Antoine equation"""
        
        K_values = []
        for comp in components:
            comp_data = self.component_db.get_component(comp)
            if comp_data and 'antoine_coefficients' in comp_data:
                A, B, C = comp_data['antoine_coefficients']
                # Antoine equation: log10(P_sat) = A - B/(T + C)
                P_sat = 10**(A - B/(T + C))  # mmHg
                P_sat_pa = P_sat * 133.322  # Convert to Pa
                K = P_sat_pa / P
            else:
                K = 1.0  # Default K-value
            K_values.append(K)
        
        # Simple flash calculation
        if all(K > 1.0 for K in K_values):
            # All vapor
            return {
                'vapor_fraction': 1.0,
                'vapor_composition': z,
                'liquid_composition': [0.0] * len(components),
                'K_values': K_values,
                'converged': True
            }
        elif all(K < 1.0 for K in K_values):
            # All liquid
            return {
                'vapor_fraction': 0.0,
                'vapor_composition': [0.0] * len(components),
                'liquid_composition': z,
                'K_values': K_values,
                'converged': True
            }
        else:
            # Two-phase flash using Rachford-Rice equation
            return self._rachford_rice_flash(z, K_values)
    
    def _rachford_rice_flash(self, z: List[float], K: List[float]) -> Dict:
        """Solve Rachford-Rice equation for vapor fraction"""
        
        def rachford_rice(V):
            return sum(z[i] * (K[i] - 1) / (1 + V * (K[i] - 1)) for i in range(len(z)))
        
        # Solve for vapor fraction using bisection
        V_low, V_high = 0.0, 1.0
        for _ in range(50):  # Max iterations
            V_mid = (V_low + V_high) / 2
            f_mid = rachford_rice(V_mid)
            
            if abs(f_mid) < 1e-8:
                break
                
            if f_mid > 0:
                V_low = V_mid
            else:
                V_high = V_mid
        
        V = V_mid
        
        # Calculate phase compositions
        x = [z[i] / (1 + V * (K[i] - 1)) for i in range(len(z))]
        y = [K[i] * x[i] for i in range(len(z))]
        
        return {
            'vapor_fraction': V,
            'vapor_composition': y,
            'liquid_composition': x,
            'K_values': K,
            'converged': abs(rachford_rice(V)) < 1e-6
        }
    
    def _ideal_cp(self, comp_data: Dict, T: float) -> float:
        """Calculate ideal gas heat capacity"""
        if 'heat_capacity_coefficients' in comp_data:
            A, B, C, D = comp_data['heat_capacity_coefficients'][:4]
            return A + B*T + C*T**2 + D*T**3
        else:
            return 29.1  # Default for ideal gas (J/mol/K)
    
    def _ideal_enthalpy(self, comp_data: Dict, T: float) -> float:
        """Calculate ideal gas enthalpy"""
        if 'heat_capacity_coefficients' in comp_data:
            A, B, C, D = comp_data['heat_capacity_coefficients'][:4]
            T_ref = 298.15  # Reference temperature
            return A*(T - T_ref) + B/2*(T**2 - T_ref**2) + C/3*(T**3 - T_ref**3) + D/4*(T**4 - T_ref**4)
        else:
            return 29.1 * (T - 298.15)  # Default
    
    def _get_coolprop_name(self, component: str) -> Optional[str]:
        """Map component name to CoolProp fluid name"""
        coolprop_map = {
            'water': 'Water',
            'methane': 'Methane', 
            'ethane': 'Ethane',
            'propane': 'Propane',
            'n-butane': 'n-Butane',
            'carbon dioxide': 'CarbonDioxide',
            'nitrogen': 'Nitrogen',
            'oxygen': 'Oxygen',
            'hydrogen': 'Hydrogen',
            'methanol': 'Methanol',
            'ethanol': 'Ethanol'
        }
        return coolprop_map.get(component.lower())
    
    def _default_component_data(self, component: str) -> Dict:
        """Provide default data for unknown components"""
        return {
            'name': component,
            'molecular_weight': 100.0,  # g/mol
            'antoine_coefficients': [8.0, 1500.0, 250.0],  # Default Antoine
            'heat_capacity_coefficients': [29.1, 0.0, 0.0, 0.0]  # Ideal gas default
        }