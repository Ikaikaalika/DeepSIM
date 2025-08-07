"""
Component Database for DeepSim
Provides chemical component data similar to Aspen Plus component database
"""

import json
import os
from typing import Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)

class ComponentDatabase:
    """
    Chemical component database with properties needed for process simulation
    Includes common industrial chemicals with thermodynamic and physical properties
    """
    
    def __init__(self):
        self.components = {}
        self._load_builtin_components()
    
    def _load_builtin_components(self):
        """Load built-in component database"""
        
        # Common industrial chemicals with key properties
        builtin_components = {
            'water': {
                'name': 'Water',
                'formula': 'H2O',
                'cas_number': '7732-18-5',
                'molecular_weight': 18.015,  # g/mol
                'critical_temperature': 647.1,  # K
                'critical_pressure': 22064000,  # Pa
                'critical_volume': 0.056,  # m³/kmol
                'acentric_factor': 0.3449,
                'antoine_coefficients': [8.07131, 1730.63, 233.426],  # A, B, C for mmHg, °C
                'heat_capacity_coefficients': [33.596, -0.01191, 3.0669e-5, -3.502e-8],  # A, B, C, D
                'normal_boiling_point': 373.15,  # K
                'melting_point': 273.15,  # K
                'heat_of_formation': -241826,  # J/mol
                'heat_of_vaporization': 40660,  # J/mol
                'liquid_density_coefficients': [5.459, 0.30542, 647.13, 0.081],  # Rackett equation
                'viscosity_coefficients': [-52.843, 3703.6, 5.866, -5.88e-29, 10]  # Liquid viscosity
            },
            
            'methanol': {
                'name': 'Methanol',
                'formula': 'CH3OH',
                'cas_number': '67-56-1',
                'molecular_weight': 32.042,
                'critical_temperature': 512.5,
                'critical_pressure': 8084000,
                'critical_volume': 0.117,
                'acentric_factor': 0.5625,
                'antoine_coefficients': [8.08097, 1582.271, 239.726],
                'heat_capacity_coefficients': [21.15, 7.092e-2, 2.587e-5, -2.852e-8],
                'normal_boiling_point': 337.7,
                'melting_point': 175.2,
                'heat_of_formation': -200660,
                'heat_of_vaporization': 35210
            },
            
            'ethanol': {
                'name': 'Ethanol',
                'formula': 'C2H5OH',
                'cas_number': '64-17-5',
                'molecular_weight': 46.069,
                'critical_temperature': 513.9,
                'critical_pressure': 6137000,
                'critical_volume': 0.168,
                'acentric_factor': 0.6436,
                'antoine_coefficients': [8.20417, 1642.89, 230.300],
                'heat_capacity_coefficients': [9.014, 0.21379, -8.39e-5, 1.373e-9],
                'normal_boiling_point': 351.4,
                'melting_point': 159.0,
                'heat_of_formation': -234810,
                'heat_of_vaporization': 38560
            },
            
            'methane': {
                'name': 'Methane',
                'formula': 'CH4',
                'cas_number': '74-82-8',
                'molecular_weight': 16.043,
                'critical_temperature': 190.6,
                'critical_pressure': 4599000,
                'critical_volume': 0.0986,
                'acentric_factor': 0.0115,
                'antoine_coefficients': [6.69561, 405.420, 267.777],
                'heat_capacity_coefficients': [19.89, 5.024e-2, 1.269e-5, -1.1e-8],
                'normal_boiling_point': 111.7,
                'melting_point': 90.7,
                'heat_of_formation': -74520,
                'heat_of_vaporization': 8180
            },
            
            'ethane': {
                'name': 'Ethane',
                'formula': 'C2H6',
                'cas_number': '74-84-0',
                'molecular_weight': 30.070,
                'critical_temperature': 305.3,
                'critical_pressure': 4872000,
                'critical_volume': 0.1455,
                'acentric_factor': 0.0995,
                'antoine_coefficients': [6.80266, 656.400, 256.998],
                'heat_capacity_coefficients': [6.900, 0.17266, -6.406e-5, 7.285e-9],
                'normal_boiling_point': 184.6,
                'melting_point': 90.4,
                'heat_of_formation': -83820,
                'heat_of_vaporization': 14690
            },
            
            'propane': {
                'name': 'Propane', 
                'formula': 'C3H8',
                'cas_number': '74-98-6',
                'molecular_weight': 44.097,
                'critical_temperature': 369.8,
                'critical_pressure': 4248000,
                'critical_volume': 0.2,
                'acentric_factor': 0.1521,
                'antoine_coefficients': [6.82973, 803.810, 246.990],
                'heat_capacity_coefficients': [-4.224, 0.30634, -1.586e-4, 3.215e-8],
                'normal_boiling_point': 231.1,
                'melting_point': 85.5,
                'heat_of_formation': -104680,
                'heat_of_vaporization': 18770
            },
            
            'n-butane': {
                'name': 'n-Butane',
                'formula': 'C4H10',
                'cas_number': '106-97-8',
                'molecular_weight': 58.124,
                'critical_temperature': 425.1,
                'critical_pressure': 3796000,
                'critical_volume': 0.255,
                'acentric_factor': 0.2002,
                'antoine_coefficients': [6.83029, 945.910, 240.099],
                'heat_capacity_coefficients': [9.487, 0.3313, -1.108e-4, -2.822e-9],
                'normal_boiling_point': 272.7,
                'melting_point': 134.9,
                'heat_of_formation': -125790,
                'heat_of_vaporization': 22440
            },
            
            'benzene': {
                'name': 'Benzene',
                'formula': 'C6H6',
                'cas_number': '71-43-2',
                'molecular_weight': 78.114,
                'critical_temperature': 562.1,
                'critical_pressure': 4894000,
                'critical_volume': 0.259,
                'acentric_factor': 0.2103,
                'antoine_coefficients': [6.90565, 1211.033, 220.790],
                'heat_capacity_coefficients': [-33.92, 0.4739, -3.017e-4, 7.13e-8],
                'normal_boiling_point': 353.2,
                'melting_point': 278.7,
                'heat_of_formation': 82880,
                'heat_of_vaporization': 30720
            },
            
            'toluene': {
                'name': 'Toluene',
                'formula': 'C7H8',
                'cas_number': '108-88-3',
                'molecular_weight': 92.141,
                'critical_temperature': 591.8,
                'critical_pressure': 4108000,
                'critical_volume': 0.316,
                'acentric_factor': 0.2657,
                'antoine_coefficients': [6.95087, 1342.310, 219.187],
                'heat_capacity_coefficients': [-24.35, 0.5125, -2.765e-4, 4.911e-8],
                'normal_boiling_point': 383.8,
                'melting_point': 178.2,
                'heat_of_formation': 50170,
                'heat_of_vaporization': 33180
            },
            
            'carbon_dioxide': {
                'name': 'Carbon Dioxide',
                'formula': 'CO2',
                'cas_number': '124-38-9',
                'molecular_weight': 44.010,
                'critical_temperature': 304.1,
                'critical_pressure': 7375000,
                'critical_volume': 0.094,
                'acentric_factor': 0.2276,
                'antoine_coefficients': [6.81228, 1301.679, 3.494],
                'heat_capacity_coefficients': [22.26, 5.981e-2, -3.501e-5, 7.469e-9],
                'normal_boiling_point': 194.7,  # Sublimation point
                'melting_point': 216.6,
                'heat_of_formation': -393520,
                'heat_of_vaporization': 25230
            },
            
            'carbon_monoxide': {
                'name': 'Carbon Monoxide',
                'formula': 'CO',
                'cas_number': '630-08-0',
                'molecular_weight': 28.010,
                'critical_temperature': 132.9,
                'critical_pressure': 3499000,
                'critical_volume': 0.093,
                'acentric_factor': 0.0497,
                'antoine_coefficients': [6.24677, 230.170, 260.000],
                'heat_capacity_coefficients': [28.16, 0.00167, 5.372e-6, -2.222e-9],
                'normal_boiling_point': 81.7,
                'melting_point': 68.2,
                'heat_of_formation': -110530,
                'heat_of_vaporization': 6040
            },
            
            'hydrogen': {
                'name': 'Hydrogen',
                'formula': 'H2',
                'cas_number': '1333-74-0',
                'molecular_weight': 2.016,
                'critical_temperature': 33.2,
                'critical_pressure': 1297000,
                'critical_volume': 0.065,
                'acentric_factor': -0.2156,
                'antoine_coefficients': [3.54314, 99.395, 7.726],
                'heat_capacity_coefficients': [27.14, 9.274e-3, -1.381e-5, 7.645e-9],
                'normal_boiling_point': 20.4,
                'melting_point': 14.0,
                'heat_of_formation': 0,
                'heat_of_vaporization': 904
            },
            
            'nitrogen': {
                'name': 'Nitrogen',
                'formula': 'N2',
                'cas_number': '7727-37-9',
                'molecular_weight': 28.014,
                'critical_temperature': 126.2,
                'critical_pressure': 3398000,
                'critical_volume': 0.090,
                'acentric_factor': 0.0377,
                'antoine_coefficients': [6.49457, 255.68, 266.55],
                'heat_capacity_coefficients': [28.98, -1.571e-3, 8.081e-6, -2.873e-9],
                'normal_boiling_point': 77.4,
                'melting_point': 63.2,
                'heat_of_formation': 0,
                'heat_of_vaporization': 5577
            },
            
            'oxygen': {
                'name': 'Oxygen',
                'formula': 'O2',
                'cas_number': '7782-44-7',
                'molecular_weight': 31.999,
                'critical_temperature': 154.6,
                'critical_pressure': 5043000,
                'critical_volume': 0.073,
                'acentric_factor': 0.0222,
                'antoine_coefficients': [6.69147, 319.013, 266.697],
                'heat_capacity_coefficients': [25.48, 1.520e-2, -7.155e-6, 1.312e-9],
                'normal_boiling_point': 90.2,
                'melting_point': 54.4,
                'heat_of_formation': 0,
                'heat_of_vaporization': 6820
            },
            
            'acetone': {
                'name': 'Acetone',
                'formula': 'C3H6O',
                'cas_number': '67-64-1',
                'molecular_weight': 58.080,
                'critical_temperature': 508.2,
                'critical_pressure': 4700000,
                'critical_volume': 0.209,
                'acentric_factor': 0.3071,
                'antoine_coefficients': [7.11714, 1210.595, 229.664],
                'heat_capacity_coefficients': [6.301, 0.2581, -1.516e-4, 3.636e-8],
                'normal_boiling_point': 329.4,
                'melting_point': 178.5,
                'heat_of_formation': -217570,
                'heat_of_vaporization': 29100
            },
            
            'acetic_acid': {
                'name': 'Acetic Acid',
                'formula': 'C2H4O2',
                'cas_number': '64-19-7',
                'molecular_weight': 60.053,
                'critical_temperature': 594.8,
                'critical_pressure': 5786000,
                'critical_volume': 0.171,
                'acentric_factor': 0.4665,
                'antoine_coefficients': [7.38782, 1533.313, 222.309],
                'heat_capacity_coefficients': [6.48, 0.2021, -1.221e-4, 2.867e-8],
                'normal_boiling_point': 391.1,
                'melting_point': 289.8,
                'heat_of_formation': -433440,
                'heat_of_vaporization': 23700
            }
        }
        
        self.components.update(builtin_components)
        logger.info(f"Loaded {len(self.components)} components into database")
    
    def get_component(self, identifier: Union[str, int]) -> Optional[Dict]:
        """
        Get component data by name or CAS number
        
        Args:
            identifier: Component name, formula, or CAS number
            
        Returns:
            Dictionary with component properties or None if not found
        """
        identifier_str = str(identifier).lower().replace('-', '_').replace(' ', '_')
        
        # Direct lookup by key
        if identifier_str in self.components:
            return self.components[identifier_str].copy()
        
        # Search by name, formula, or CAS
        for comp_id, comp_data in self.components.items():
            if (comp_data['name'].lower() == identifier.lower() or
                comp_data['formula'].lower() == identifier.lower() or
                comp_data['cas_number'] == str(identifier)):
                return comp_data.copy()
        
        logger.warning(f"Component '{identifier}' not found in database")
        return None
    
    def search_components(self, query: str) -> List[Dict]:
        """
        Search for components by partial name match
        
        Args:
            query: Search string
            
        Returns:
            List of matching components
        """
        query_lower = query.lower()
        results = []
        
        for comp_id, comp_data in self.components.items():
            if (query_lower in comp_data['name'].lower() or
                query_lower in comp_data['formula'].lower() or
                query_lower in comp_id):
                results.append(comp_data.copy())
        
        return results
    
    def add_component(self, component_id: str, component_data: Dict):
        """
        Add a custom component to the database
        
        Args:
            component_id: Unique identifier for the component
            component_data: Dictionary with component properties
        """
        required_fields = ['name', 'formula', 'molecular_weight']
        
        for field in required_fields:
            if field not in component_data:
                raise ValueError(f"Required field '{field}' missing from component data")
        
        self.components[component_id.lower().replace('-', '_').replace(' ', '_')] = component_data
        logger.info(f"Added component '{component_id}' to database")
    
    def list_components(self) -> List[str]:
        """Get list of all available component names"""
        return [comp_data['name'] for comp_data in self.components.values()]
    
    def get_component_count(self) -> int:
        """Get total number of components in database"""
        return len(self.components)
    
    def export_database(self, filename: str):
        """Export component database to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.components, f, indent=2)
            logger.info(f"Database exported to {filename}")
        except Exception as e:
            logger.error(f"Failed to export database: {e}")
    
    def load_database(self, filename: str):
        """Load component database from JSON file"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    custom_components = json.load(f)
                self.components.update(custom_components)
                logger.info(f"Loaded {len(custom_components)} components from {filename}")
            else:
                logger.warning(f"Database file {filename} not found")
        except Exception as e:
            logger.error(f"Failed to load database: {e}")
    
    def get_similar_components(self, molecular_weight: float, tolerance: float = 5.0) -> List[Dict]:
        """
        Find components with similar molecular weight
        
        Args:
            molecular_weight: Target molecular weight
            tolerance: Tolerance in g/mol
            
        Returns:
            List of similar components
        """
        results = []
        
        for comp_data in self.components.values():
            if abs(comp_data['molecular_weight'] - molecular_weight) <= tolerance:
                results.append(comp_data.copy())
        
        return sorted(results, key=lambda x: abs(x['molecular_weight'] - molecular_weight))
    
    def validate_component_data(self, component_data: Dict) -> List[str]:
        """
        Validate component data for completeness and consistency
        
        Args:
            component_data: Component data dictionary
            
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        required_fields = ['name', 'formula', 'molecular_weight']
        for field in required_fields:
            if field not in component_data:
                warnings.append(f"Missing required field: {field}")
        
        recommended_fields = [
            'critical_temperature', 'critical_pressure', 'critical_volume',
            'acentric_factor', 'antoine_coefficients', 'normal_boiling_point'
        ]
        
        for field in recommended_fields:
            if field not in component_data:
                warnings.append(f"Missing recommended field: {field}")
        
        # Check ranges
        if 'molecular_weight' in component_data:
            if component_data['molecular_weight'] <= 0:
                warnings.append("Molecular weight must be positive")
        
        if 'critical_temperature' in component_data:
            if component_data['critical_temperature'] <= 0:
                warnings.append("Critical temperature must be positive")
        
        return warnings