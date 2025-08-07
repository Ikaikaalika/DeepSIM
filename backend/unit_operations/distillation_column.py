"""
Rigorous Distillation Column Model
Implements MESH equations for tray-by-tray calculations like Aspen Plus
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from scipy.optimize import fsolve
from scipy.linalg import solve

from ..thermodynamics import PropertyEngine

logger = logging.getLogger(__name__)

class RigorousDistillationColumn:
    """
    Rigorous distillation column model using MESH equations
    - Material Balance (M)
    - Equilibrium Relations (E)
    - Summation Equations (S)
    - Heat Balance (H)
    """
    
    def __init__(self, property_engine: PropertyEngine):
        self.property_engine = property_engine
        self.converged = False
        self.iterations = 0
        self.max_iterations = 100
        self.tolerance = 1e-6
        
    def solve_column(self, 
                    components: List[str],
                    feed_flow: float,           # kmol/h
                    feed_composition: List[float],
                    feed_temperature: float,    # K
                    feed_pressure: float,       # Pa
                    feed_stage: int,
                    num_stages: int,
                    reflux_ratio: float,
                    distillate_rate: float,     # kmol/h
                    column_pressure: float = None,  # Pa
                    condenser_type: str = "total",  # "total" or "partial"
                    reboiler_type: str = "kettle",  # "kettle" or "thermosiphon"
                    tray_efficiency: float = 0.75,
                    method: str = "PENG-ROBINSON") -> Dict:
        """
        Solve rigorous distillation column using MESH equations
        """
        
        if column_pressure is None:
            column_pressure = feed_pressure
            
        # Initialize column parameters
        self.components = components
        self.nc = len(components)  # Number of components
        self.ns = num_stages      # Number of stages (including reboiler and condenser)
        self.nf = feed_stage      # Feed stage (1-indexed)
        self.method = method
        
        # Column specifications
        self.feed_flow = feed_flow
        self.feed_composition = np.array(feed_composition)
        self.feed_temperature = feed_temperature
        self.reflux_ratio = reflux_ratio
        self.distillate_rate = distillate_rate
        self.bottoms_rate = feed_flow - distillate_rate
        self.tray_efficiency = tray_efficiency
        
        # Pressure profile (assume constant for now)
        self.pressures = np.full(self.ns, column_pressure)
        
        logger.info(f"Solving {self.ns}-stage column with {self.nc} components")
        logger.info(f"Feed: {feed_flow} kmol/h at stage {feed_stage}")
        logger.info(f"Distillate: {distillate_rate} kmol/h, Reflux ratio: {reflux_ratio}")
        
        try:
            # Initialize profiles
            self._initialize_profiles()
            
            # Solve MESH equations
            solution = self._solve_mesh_equations()
            
            # Calculate additional properties
            results = self._calculate_results(solution)
            
            return results
            
        except Exception as e:
            logger.error(f"Column solution failed: {e}")
            return self._generate_error_result(str(e))
    
    def _initialize_profiles(self):
        """Initialize temperature, composition, and flow profiles"""
        
        # Initialize temperature profile (linear between feed and estimated endpoints)
        self.temperatures = np.linspace(
            self.feed_temperature - 20,  # Lighter at top
            self.feed_temperature + 20,  # Heavier at bottom
            self.ns
        )
        
        # Initialize composition profiles
        # Assume linear distribution from pure light component at top to pure heavy at bottom
        self.liquid_compositions = np.zeros((self.ns, self.nc))
        self.vapor_compositions = np.zeros((self.ns, self.nc))
        
        for stage in range(self.ns):
            # Linear interpolation of compositions
            fraction = stage / (self.ns - 1)
            for comp in range(self.nc):
                if comp == 0:  # Light component - more at top
                    self.liquid_compositions[stage, comp] = 1.0 - 0.8 * fraction
                elif comp == self.nc - 1:  # Heavy component - more at bottom
                    self.liquid_compositions[stage, comp] = 0.8 * fraction
                else:  # Middle components
                    self.liquid_compositions[stage, comp] = 0.2 / max(1, self.nc - 2)
            
            # Normalize
            self.liquid_compositions[stage, :] /= np.sum(self.liquid_compositions[stage, :])
            self.vapor_compositions[stage, :] = self.liquid_compositions[stage, :].copy()
        
        # Initialize liquid and vapor flow rates
        self.liquid_flows = np.full(self.ns, self.feed_flow * 0.7)  # kmol/h
        self.vapor_flows = np.full(self.ns, self.feed_flow * 0.6)   # kmol/h
        
        # Adjust flows for column sections
        self.liquid_flows[0] = self.reflux_ratio * self.distillate_rate  # Reflux
        self.vapor_flows[-1] = self.liquid_flows[-1] + self.bottoms_rate # Reboiler vapor
    
    def _solve_mesh_equations(self) -> Dict:
        """Solve the MESH equations iteratively"""
        
        self.converged = False
        self.iterations = 0
        
        # Pack variables for solver
        initial_guess = self._pack_variables()
        
        logger.info(f"Starting MESH solver with {len(initial_guess)} variables")
        
        try:
            # Solve using Newton-Raphson via fsolve
            solution_vector = fsolve(
                self._mesh_residuals,
                initial_guess,
                xtol=self.tolerance,
                maxfev=self.max_iterations * 10
            )
            
            # Unpack solution
            solution = self._unpack_variables(solution_vector)
            
            # Check convergence
            residuals = self._mesh_residuals(solution_vector)
            max_residual = np.max(np.abs(residuals))
            
            if max_residual < self.tolerance:
                self.converged = True
                logger.info(f"Column converged in {self.iterations} iterations")
                logger.info(f"Maximum residual: {max_residual:.2e}")
            else:
                logger.warning(f"Column did not converge. Max residual: {max_residual:.2e}")
            
            return solution
            
        except Exception as e:
            logger.error(f"MESH solver failed: {e}")
            raise
    
    def _pack_variables(self) -> np.ndarray:
        """Pack all variables into a single vector for the solver"""
        
        variables = []
        
        # Temperatures (ns variables)
        variables.extend(self.temperatures)
        
        # Liquid compositions (ns * nc variables)
        for stage in range(self.ns):
            variables.extend(self.liquid_compositions[stage, :])
        
        # Vapor compositions (ns * nc variables) 
        for stage in range(self.ns):
            variables.extend(self.vapor_compositions[stage, :])
        
        # Liquid flows (ns variables)
        variables.extend(self.liquid_flows)
        
        # Vapor flows (ns variables)
        variables.extend(self.vapor_flows)
        
        return np.array(variables)
    
    def _unpack_variables(self, variables: np.ndarray) -> Dict:
        """Unpack variables from solver vector"""
        
        idx = 0
        
        # Temperatures
        temperatures = variables[idx:idx+self.ns]
        idx += self.ns
        
        # Liquid compositions
        liquid_compositions = np.zeros((self.ns, self.nc))
        for stage in range(self.ns):
            liquid_compositions[stage, :] = variables[idx:idx+self.nc]
            idx += self.nc
        
        # Vapor compositions
        vapor_compositions = np.zeros((self.ns, self.nc))
        for stage in range(self.ns):
            vapor_compositions[stage, :] = variables[idx:idx+self.nc]
            idx += self.nc
        
        # Liquid flows
        liquid_flows = variables[idx:idx+self.ns]
        idx += self.ns
        
        # Vapor flows
        vapor_flows = variables[idx:idx+self.ns]
        
        return {
            'temperatures': temperatures,
            'liquid_compositions': liquid_compositions,
            'vapor_compositions': vapor_compositions,
            'liquid_flows': liquid_flows,
            'vapor_flows': vapor_flows
        }
    
    def _mesh_residuals(self, variables: np.ndarray) -> np.ndarray:
        """Calculate MESH equation residuals"""
        
        self.iterations += 1
        solution = self._unpack_variables(variables)
        
        T = solution['temperatures']
        x = solution['liquid_compositions']
        y = solution['vapor_compositions']
        L = solution['liquid_flows']
        V = solution['vapor_flows']
        
        residuals = []
        
        # Material Balance Equations (M)
        for stage in range(self.ns):
            for comp in range(self.nc):
                # Input flows
                liquid_in = 0.0
                vapor_in = 0.0
                feed_in = 0.0
                
                # Liquid from stage above
                if stage > 0:
                    liquid_in = L[stage-1] * x[stage-1, comp]
                
                # Vapor from stage below
                if stage < self.ns - 1:
                    vapor_in = V[stage+1] * y[stage+1, comp]
                
                # Feed input
                if stage == self.nf - 1:  # Convert to 0-indexed
                    feed_in = self.feed_flow * self.feed_composition[comp]
                
                # Output flows
                liquid_out = L[stage] * x[stage, comp]
                vapor_out = V[stage] * y[stage, comp]
                
                # Distillate and bottoms
                distillate_out = 0.0
                bottoms_out = 0.0
                
                if stage == 0:  # Condenser
                    distillate_out = self.distillate_rate * x[stage, comp]
                
                if stage == self.ns - 1:  # Reboiler
                    bottoms_out = self.bottoms_rate * x[stage, comp]
                
                # Material balance residual
                residual = (liquid_in + vapor_in + feed_in) - (liquid_out + vapor_out + distillate_out + bottoms_out)
                residuals.append(residual)
        
        # Equilibrium Relations (E)
        for stage in range(self.ns):
            for comp in range(self.nc):
                # Get K-values from thermodynamic engine
                try:
                    props = self.property_engine.calculate_properties(
                        components=self.components,
                        mole_fractions=x[stage, :],
                        temperature=T[stage],
                        pressure=self.pressures[stage],
                        method=self.method
                    )
                    
                    # Calculate K-value for this component
                    # For now, use simplified K-value calculation
                    K_value = self._calculate_k_value(comp, T[stage], self.pressures[stage])
                    
                    # Apply tray efficiency
                    K_eff = 1.0 + self.tray_efficiency * (K_value - 1.0)
                    
                    # Equilibrium relation: y = K * x
                    residual = y[stage, comp] - K_eff * x[stage, comp]
                    residuals.append(residual)
                    
                except Exception as e:
                    logger.warning(f"K-value calculation failed for stage {stage}, comp {comp}: {e}")
                    residuals.append(y[stage, comp] - x[stage, comp])  # Fallback
        
        # Summation Equations (S)
        for stage in range(self.ns):
            # Liquid composition sum = 1
            residual_x = np.sum(x[stage, :]) - 1.0
            residuals.append(residual_x)
            
            # Vapor composition sum = 1
            residual_y = np.sum(y[stage, :]) - 1.0
            residuals.append(residual_y)
        
        # Heat Balance Equations (H) - Simplified
        for stage in range(self.ns):
            # For now, use simplified energy balance
            # More rigorous implementation would calculate enthalpies
            
            if stage == 0:  # Condenser
                # Assume total condenser at bubble point
                residual = T[stage] - self._bubble_point(x[stage, :], self.pressures[stage])
            elif stage == self.ns - 1:  # Reboiler
                # Assume reboiler at dew point
                residual = T[stage] - self._dew_point(y[stage, :], self.pressures[stage])
            else:
                # Internal stages - energy balance
                residual = 0.0  # Simplified - assume adiabatic
                
            residuals.append(residual)
        
        return np.array(residuals)
    
    def _calculate_k_value(self, comp_index: int, temperature: float, pressure: float) -> float:
        """Calculate K-value for component using Antoine equation"""
        
        comp_name = self.components[comp_index]
        comp_data = self.property_engine.component_db.get_component(comp_name)
        
        if comp_data and 'antoine_coefficients' in comp_data:
            A, B, C = comp_data['antoine_coefficients']
            # Antoine equation: log10(P_sat) = A - B/(T + C)
            P_sat = 10**(A - B/(temperature - 273.15 + C))  # mmHg
            P_sat_pa = P_sat * 133.322  # Convert to Pa
            K_value = P_sat_pa / pressure
        else:
            # Default K-value if no data available
            K_value = 1.0
            
        return max(0.001, K_value)  # Prevent negative K-values
    
    def _bubble_point(self, x_comp: np.ndarray, pressure: float) -> float:
        """Calculate bubble point temperature"""
        
        # Initial guess
        T = self.feed_temperature
        
        for _ in range(20):  # Max iterations
            K_values = [self._calculate_k_value(i, T, pressure) for i in range(self.nc)]
            f = sum(x_comp[i] * K_values[i] for i in range(self.nc)) - 1.0
            
            if abs(f) < 1e-6:
                break
                
            # Simple derivative approximation
            dT = 1.0
            K_values_plus = [self._calculate_k_value(i, T + dT, pressure) for i in range(self.nc)]
            df_dT = (sum(x_comp[i] * K_values_plus[i] for i in range(self.nc)) - 1.0 - f) / dT
            
            if abs(df_dT) > 1e-10:
                T = T - f / df_dT
            else:
                break
        
        return T
    
    def _dew_point(self, y_comp: np.ndarray, pressure: float) -> float:
        """Calculate dew point temperature"""
        
        # Initial guess
        T = self.feed_temperature
        
        for _ in range(20):  # Max iterations
            K_values = [self._calculate_k_value(i, T, pressure) for i in range(self.nc)]
            f = sum(y_comp[i] / max(K_values[i], 1e-10) for i in range(self.nc)) - 1.0
            
            if abs(f) < 1e-6:
                break
                
            # Simple derivative approximation
            dT = 1.0
            K_values_plus = [self._calculate_k_value(i, T + dT, pressure) for i in range(self.nc)]
            df_dT = (sum(y_comp[i] / max(K_values_plus[i], 1e-10) for i in range(self.nc)) - 1.0 - f) / dT
            
            if abs(df_dT) > 1e-10:
                T = T - f / df_dT
            else:
                break
        
        return T
    
    def _calculate_results(self, solution: Dict) -> Dict:
        """Calculate final results and performance metrics"""
        
        T = solution['temperatures']
        x = solution['liquid_compositions']
        y = solution['vapor_compositions']
        L = solution['liquid_flows']
        V = solution['vapor_flows']
        
        # Calculate separation performance
        distillate_composition = x[0, :]
        bottoms_composition = x[-1, :]
        
        # Recovery calculations
        recoveries = {}
        for i, comp in enumerate(self.components):
            distillate_comp_flow = self.distillate_rate * distillate_composition[i]
            feed_comp_flow = self.feed_flow * self.feed_composition[i]
            if feed_comp_flow > 0:
                recoveries[comp] = distillate_comp_flow / feed_comp_flow
            else:
                recoveries[comp] = 0.0
        
        # Energy requirements (simplified)
        condenser_duty = self._calculate_condenser_duty(V[0], y[0, :], T[0])
        reboiler_duty = self._calculate_reboiler_duty(L[-1], x[-1, :], T[-1])
        
        results = {
            "simulation_id": "distillation_" + str(np.random.randint(1000, 9999)),
            "status": "completed" if self.converged else "failed",
            "converged": self.converged,
            "iterations": self.iterations,
            "column_performance": {
                "stages": self.ns,
                "feed_stage": self.nf,
                "reflux_ratio": self.reflux_ratio,
                "distillate_rate": self.distillate_rate,
                "bottoms_rate": self.bottoms_rate,
                "tray_efficiency": self.tray_efficiency
            },
            "product_compositions": {
                "distillate": {comp: distillate_composition[i] for i, comp in enumerate(self.components)},
                "bottoms": {comp: bottoms_composition[i] for i, comp in enumerate(self.components)}
            },
            "component_recoveries": recoveries,
            "temperature_profile": T.tolist(),
            "energy_duties": {
                "condenser_duty": condenser_duty,  # kW
                "reboiler_duty": reboiler_duty,    # kW
                "net_duty": condenser_duty + reboiler_duty
            },
            "stage_data": {
                "temperatures": T.tolist(),
                "liquid_compositions": x.tolist(),
                "vapor_compositions": y.tolist(),
                "liquid_flows": L.tolist(),
                "vapor_flows": V.tolist()
            },
            "method_used": self.method,
            "thermodynamic_method": self.method
        }
        
        return results
    
    def _calculate_condenser_duty(self, vapor_flow: float, vapor_comp: np.ndarray, temperature: float) -> float:
        """Calculate condenser duty (simplified)"""
        
        # Simplified calculation - use average latent heat
        avg_latent_heat = 35000  # J/mol (typical for organic compounds)
        duty_j_s = vapor_flow * avg_latent_heat / 3600  # J/s (Watts)
        return -duty_j_s / 1000  # kW (negative for heat removal)
    
    def _calculate_reboiler_duty(self, liquid_flow: float, liquid_comp: np.ndarray, temperature: float) -> float:
        """Calculate reboiler duty (simplified)"""
        
        # Simplified calculation - use average latent heat
        avg_latent_heat = 35000  # J/mol (typical for organic compounds)
        vapor_generated = liquid_flow * 0.8  # Assume 80% vaporization
        duty_j_s = vapor_generated * avg_latent_heat / 3600  # J/s (Watts)
        return duty_j_s / 1000  # kW (positive for heat input)
    
    def _generate_error_result(self, error_message: str) -> Dict:
        """Generate error result when simulation fails"""
        
        return {
            "simulation_id": "distillation_error",
            "status": "failed",
            "converged": False,
            "error": error_message,
            "column_performance": {},
            "product_compositions": {},
            "component_recoveries": {},
            "temperature_profile": [],
            "energy_duties": {},
            "stage_data": {}
        }


class DistillationColumnDesign:
    """
    Distillation column sizing and hydraulic calculations
    """
    
    def __init__(self):
        self.tower_diameter = None
        self.tower_height = None
        self.tray_spacing = 0.6  # meters
        
    def size_column(self, 
                   vapor_flow: float,      # kmol/h
                   liquid_flow: float,     # kmol/h
                   molecular_weight_v: float,  # g/mol
                   molecular_weight_l: float,  # g/mol
                   density_v: float,       # kg/m³
                   density_l: float,       # kg/m³
                   pressure: float,        # Pa
                   temperature: float,     # K
                   num_stages: int) -> Dict:
        """
        Size distillation column based on vapor and liquid flows
        """
        
        try:
            # Convert flows to mass basis
            vapor_mass_flow = vapor_flow * molecular_weight_v / 3600  # kg/s
            liquid_mass_flow = liquid_flow * molecular_weight_l / 3600  # kg/s
            
            # Calculate superficial velocity
            # Using Souders-Brown equation for flooding velocity
            C_sb = self._calculate_souders_brown_constant(pressure/1e5)  # Convert Pa to bar
            
            # Flooding velocity
            u_flood = C_sb * np.sqrt((density_l - density_v) / density_v)  # m/s
            
            # Design velocity (typically 70-85% of flooding)
            design_factor = 0.80
            u_design = design_factor * u_flood
            
            # Calculate column diameter
            volumetric_vapor_flow = vapor_mass_flow / density_v  # m³/s
            area_required = volumetric_vapor_flow / u_design  # m²
            diameter = np.sqrt(4 * area_required / np.pi)  # m
            
            # Column height
            height = num_stages * self.tray_spacing  # m
            
            self.tower_diameter = diameter
            self.tower_height = height
            
            # Calculate pressure drop
            pressure_drop_per_tray = self._calculate_pressure_drop(
                vapor_flow, liquid_flow, density_v, density_l, diameter
            )
            total_pressure_drop = pressure_drop_per_tray * num_stages
            
            return {
                "tower_diameter": diameter,
                "tower_height": height,
                "tray_spacing": self.tray_spacing,
                "design_velocity": u_design,
                "flooding_velocity": u_flood,
                "approach_to_flood": design_factor * 100,
                "pressure_drop_per_tray": pressure_drop_per_tray,
                "total_pressure_drop": total_pressure_drop,
                "cross_sectional_area": area_required,
                "volumetric_vapor_flow": volumetric_vapor_flow * 3600  # m³/h
            }
            
        except Exception as e:
            logger.error(f"Column sizing failed: {e}")
            return {
                "error": str(e),
                "tower_diameter": 1.0,  # Default values
                "tower_height": 10.0,
                "tray_spacing": 0.6
            }
    
    def _calculate_souders_brown_constant(self, pressure_bar: float) -> float:
        """Calculate Souders-Brown constant based on pressure"""
        
        if pressure_bar < 0.2:
            return 0.1
        elif pressure_bar < 1.0:
            return 0.08
        elif pressure_bar < 10:
            return 0.06
        else:
            return 0.05
    
    def _calculate_pressure_drop(self, 
                                vapor_flow: float,
                                liquid_flow: float,
                                density_v: float,
                                density_l: float,
                                diameter: float) -> float:
        """Calculate pressure drop per tray (Pa)"""
        
        # Simplified pressure drop calculation
        # Typical tray pressure drop is 0.005 - 0.01 bar (500 - 1000 Pa)
        
        # Base pressure drop
        base_dp = 700  # Pa
        
        # Adjust for vapor velocity
        area = np.pi * (diameter/2)**2
        vapor_velocity = (vapor_flow / 3600) / (density_v * area)
        
        # Pressure drop increases with velocity squared
        velocity_factor = (vapor_velocity / 3.0)**2  # Normalized to 3 m/s
        
        return base_dp * (1 + velocity_factor)