import asyncio
import json
import logging
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        self.thunder_endpoint = os.getenv("THUNDER_ENDPOINT", "")
        self.thunder_api_key = os.getenv("THUNDER_API_KEY", "")
        self.model_name = "deepseek-r1"
        
        if not self.thunder_endpoint:
            logger.warning("Thunder endpoint not configured. LLM will use mock responses.")
    
    async def process_message(
        self, 
        message: str, 
        flowsheet: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        
        if not self.thunder_endpoint:
            return await self._mock_llm_response(message, flowsheet, context)
        
        try:
            return await self._call_thunder_api(message, flowsheet, context)
        except Exception as e:
            logger.error(f"Thunder API call failed: {e}")
            return await self._mock_llm_response(message, flowsheet, context)
    
    async def _call_thunder_api(
        self, 
        message: str, 
        flowsheet: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        
        system_prompt = self._build_system_prompt(flowsheet, context)
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            "max_tokens": 2048,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Authorization": f"Bearer {self.thunder_api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.thunder_endpoint}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            try:
                parsed_response = json.loads(content)
                return parsed_response
            except json.JSONDecodeError:
                return {
                    "action": "text_response",
                    "message": content,
                    "timestamp": datetime.now().isoformat()
                }
    
    def _build_system_prompt(
        self, 
        flowsheet: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        
        base_prompt = """You are an expert chemical process engineer AI assistant for DeepSim, an AI-powered chemical process simulation platform. 

Your role is to help users design, modify, analyze, and optimize chemical processes through natural language interaction.

CAPABILITIES:
1. Create new flowsheets from descriptions
2. Modify existing units and parameters  
3. Add or remove unit operations and connections
4. Analyze simulation results and suggest improvements
5. Explain chemical engineering concepts and processes
6. Troubleshoot process issues

RESPONSE FORMAT:
Always respond with valid JSON containing:
- "action": One of ["create_flowsheet", "update_flowsheet", "analyze_results", "text_response", "error"]
- "message": Human-readable explanation of your response
- Additional fields based on action type

For flowsheet modifications, include:
- "flowsheet_update": Updated units, streams, connections
- "reasoning": Explanation of changes made

For analysis, include:
- "analysis": Technical analysis of the process/results
- "recommendations": List of suggested improvements

UNIT TYPES AVAILABLE:
Reactor, Heater, Cooler, Pump, Compressor, Valve, DistillationColumn, Mixer, Splitter, Flash, HeatExchanger

EXAMPLE UNITS:
- Reactor: conversion, temperature, pressure, reactor_type
- DistillationColumn: stages, reflux_ratio, pressure, feed_stage
- Heater/Cooler: outlet_temperature, heat_duty, pressure_drop
- Pump/Compressor: outlet_pressure, efficiency, pressure_ratio"""

        if flowsheet:
            base_prompt += f"\n\nCURRENT FLOWSHEET:\n{json.dumps(flowsheet, indent=2)}"
        
        if context:
            base_prompt += f"\n\nADDITIONAL CONTEXT:\n{json.dumps(context, indent=2)}"
        
        return base_prompt
    
    async def _mock_llm_response(
        self, 
        message: str, 
        flowsheet: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        
        await asyncio.sleep(0.5)
        
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ["create", "build", "design", "new flowsheet"]):
            return await self._generate_mock_flowsheet(message)
        
        elif any(keyword in message_lower for keyword in ["increase", "decrease", "change", "set", "modify"]):
            return await self._generate_mock_modification(message, flowsheet)
        
        elif any(keyword in message_lower for keyword in ["analyze", "why", "explain", "how", "performance"]):
            return await self._generate_mock_analysis(message, flowsheet, context)
        
        elif any(keyword in message_lower for keyword in ["add", "insert", "include"]):
            return await self._generate_mock_addition(message, flowsheet)
        
        else:
            return {
                "action": "text_response",
                "message": f"I understand you want to work with the process flowsheet. Could you be more specific about what you'd like to do? I can help you create, modify, analyze, or troubleshoot chemical processes.",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _generate_mock_flowsheet(self, message: str) -> Dict[str, Any]:
        if "methanol" in message.lower():
            return {
                "action": "create_flowsheet",
                "message": "I've created a methanol production process with a reactor and distillation column for purification.",
                "flowsheet_update": {
                    "units": [
                        {
                            "id": "R1",
                            "type": "Reactor",
                            "name": "Methanol Reactor",
                            "position": {"x": 200, "y": 300},
                            "parameters": {
                                "temperature": 250,
                                "pressure": 50,
                                "conversion": 0.85,
                                "reactor_type": "CSTR"
                            },
                            "inlet_ports": ["in1"],
                            "outlet_ports": ["out1"]
                        },
                        {
                            "id": "T1", 
                            "type": "DistillationColumn",
                            "name": "Methanol Column",
                            "position": {"x": 400, "y": 300},
                            "parameters": {
                                "stages": 20,
                                "reflux_ratio": 2.5,
                                "pressure": 1,
                                "feed_stage": 10
                            },
                            "inlet_ports": ["feed"],
                            "outlet_ports": ["distillate", "bottoms"]
                        }
                    ],
                    "streams": [
                        {
                            "id": "S1",
                            "name": "Syngas Feed",
                            "temperature": 25,
                            "pressure": 50,
                            "molar_flow": 100,
                            "composition": {"CO": 0.5, "H2": 0.5}
                        },
                        {
                            "id": "S2",
                            "name": "Reactor Outlet",
                            "temperature": 250,
                            "pressure": 50
                        }
                    ],
                    "connections": [
                        {
                            "id": "C1",
                            "from_unit": "Feed",
                            "from_port": "out",
                            "to_unit": "R1", 
                            "to_port": "in1",
                            "stream_id": "S1"
                        },
                        {
                            "id": "C2",
                            "from_unit": "R1",
                            "from_port": "out1",
                            "to_unit": "T1",
                            "to_port": "feed",
                            "stream_id": "S2"
                        }
                    ]
                },
                "reasoning": "Created a basic methanol synthesis process with CO+H2 → CH3OH reaction followed by distillation for product purification.",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "action": "create_flowsheet",
            "message": "I've created a basic chemical process with a reactor and separator.",
            "flowsheet_update": {
                "units": [
                    {
                        "id": "R1",
                        "type": "Reactor",
                        "name": "Main Reactor",
                        "position": {"x": 200, "y": 300},
                        "parameters": {"temperature": 200, "pressure": 2, "conversion": 0.8},
                        "inlet_ports": ["in1"],
                        "outlet_ports": ["out1"]
                    }
                ],
                "streams": [],
                "connections": []
            },
            "reasoning": "Created a basic process template that can be customized based on your specific needs.",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _generate_mock_modification(self, message: str, flowsheet: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not flowsheet:
            return {
                "action": "error",
                "message": "No flowsheet loaded to modify. Please create or load a flowsheet first.",
                "timestamp": datetime.now().isoformat()
            }
        
        units = flowsheet.get("units", [])
        if not units:
            return {
                "action": "error", 
                "message": "No units found in the current flowsheet to modify.",
                "timestamp": datetime.now().isoformat()
            }
        
        target_unit = units[0]
        updated_units = units.copy()
        
        if "temperature" in message.lower():
            if "increase" in message.lower() or "higher" in message.lower():
                new_temp = target_unit.get("parameters", {}).get("temperature", 200) + 50
            else:
                new_temp = target_unit.get("parameters", {}).get("temperature", 200) - 50
            
            updated_units[0]["parameters"]["temperature"] = new_temp
            
            return {
                "action": "update_flowsheet",
                "message": f"Updated {target_unit.get('name', 'unit')} temperature to {new_temp}°C",
                "flowsheet_update": {"units": updated_units},
                "reasoning": f"Modified temperature based on your request to optimize process performance.",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "action": "text_response",
            "message": "I understand you want to modify the process. Could you be more specific about which parameter you'd like to change?",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _generate_mock_analysis(self, message: str, flowsheet: Optional[Dict[str, Any]], context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "action": "analyze_results",
            "message": "Based on the simulation results, here's my analysis of the process performance:",
            "analysis": {
                "performance_summary": "The process is operating within acceptable ranges with good conversion efficiency.",
                "key_metrics": {
                    "overall_conversion": "85%",
                    "energy_efficiency": "Good - heat integration opportunities exist",
                    "separation_efficiency": "Moderate - could be improved with additional stages"
                },
                "potential_issues": [
                    "Reactor temperature may be limiting conversion",
                    "Distillation column reflux ratio could be optimized",
                    "Pressure drops across units should be minimized"
                ]
            },
            "recommendations": [
                "Increase reactor temperature by 20-30°C to improve conversion",
                "Consider increasing distillation column stages for better separation",
                "Implement heat integration between hot and cold streams",
                "Add pressure control to maintain optimal operating conditions"
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    async def _generate_mock_addition(self, message: str, flowsheet: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if "heater" in message.lower():
            new_unit = {
                "id": "H1",
                "type": "Heater", 
                "name": "Feed Heater",
                "position": {"x": 150, "y": 300},
                "parameters": {
                    "outlet_temperature": 200,
                    "pressure_drop": 0.1
                },
                "inlet_ports": ["in1"],
                "outlet_ports": ["out1"]
            }
            
            return {
                "action": "update_flowsheet",
                "message": "I've added a heater to the process for feed preheating.",
                "flowsheet_update": {
                    "units": (flowsheet.get("units", []) if flowsheet else []) + [new_unit]
                },
                "reasoning": "Added heater to improve reaction kinetics by preheating the feed stream.",
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "action": "text_response",
            "message": "I can help you add various unit operations. What type of equipment would you like to add?",
            "timestamp": datetime.now().isoformat()
        }