"""
AI Engine for DeepSim - Thunder Compute Integration
Connects to DeepSeek R1 model for autonomous process design
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class AITaskType(Enum):
    DESIGN_FLOWSHEET = "design_flowsheet"
    OPTIMIZE_PROCESS = "optimize_process"
    ANALYZE_SIMULATION = "analyze_simulation"
    TROUBLESHOOT = "troubleshoot"
    AUTONOMOUS_TEST = "autonomous_test"
    GENERAL_QUERY = "general_query"

@dataclass
class AIRequest:
    user_message: str
    context: Dict[str, Any]
    task_type: AITaskType
    flowsheet_data: Optional[Dict] = None
    simulation_results: Optional[Dict] = None
    conversation_history: Optional[List[Dict]] = None

@dataclass
class AIResponse:
    message: str
    actions: List[Dict[str, Any]]
    confidence: float
    reasoning: str
    suggested_followups: List[str]

class ThunderComputeClient:
    """Client for Thunder Compute API integration"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.thunder.dev"):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = "deepseek-r1-distill-llama-70b"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_completion(self, prompt: str, system_prompt: str = None, 
                              temperature: float = 0.7, max_tokens: int = 2000,
                              stream: bool = False) -> Dict:
        """Create completion using DeepSeek R1 on Thunder Compute"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Thunder Compute API error: {response.status} - {error_text}")
                    raise Exception(f"API request failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"Thunder Compute request failed: {str(e)}")
            raise

class ProcessEngineeringAI:
    """AI Engine specialized for chemical process engineering"""
    
    def __init__(self, thunder_api_key: str):
        self.thunder_client = None
        self.api_key = thunder_api_key
        self.conversation_context = []
        
        # Process engineering knowledge base
        self.unit_operations_db = {
            "distillation": {
                "typical_stages": (10, 50),
                "typical_reflux": (1.2, 5.0),
                "efficiency_range": (0.6, 0.95),
                "applications": ["separation", "purification", "fractionation"]
            },
            "reactor": {
                "types": ["CSTR", "PFR", "BatchReactor", "PackedBed"],
                "typical_residence": (300, 14400),  # seconds
                "temperature_range": (273, 773),    # Kelvin
                "applications": ["synthesis", "conversion", "polymerization"]
            },
            "heat_exchanger": {
                "types": ["shell_tube", "plate", "air_cooled"],
                "approach_temp": (5, 50),  # Kelvin
                "applications": ["heating", "cooling", "heat_recovery"]
            }
        }
        
    async def initialize(self):
        """Initialize Thunder Compute client"""
        self.thunder_client = ThunderComputeClient(self.api_key)
        await self.thunder_client.__aenter__()
        
    async def shutdown(self):
        """Cleanup resources"""
        if self.thunder_client:
            await self.thunder_client.__aexit__(None, None, None)
    
    def _get_system_prompt(self, task_type: AITaskType) -> str:
        """Generate specialized system prompts for different tasks"""
        
        base_prompt = """You are an expert AI chemical process engineer specializing in industrial process design and optimization. You have deep knowledge of:

- Unit operations (distillation, reactors, heat exchangers, separations)
- Thermodynamics and phase equilibrium (Peng-Robinson, UNIFAC, NRTL)
- Process simulation and MESH equations
- Industrial best practices and safety standards
- Energy integration and sustainability
- Process economics and optimization

You work with DeepSim, an industrial process simulator similar to Aspen Plus, helping users design and optimize chemical processes autonomously."""

        task_specific = {
            AITaskType.DESIGN_FLOWSHEET: """
Focus on creating complete, realistic process flowsheets. When designing:
1. Start with process objectives and constraints
2. Select appropriate unit operations with realistic parameters
3. Consider material and energy balances
4. Include utilities (heating, cooling, pumping)
5. Provide specific numerical parameters (stages, temperatures, pressures)
6. Explain the engineering reasoning behind decisions

Response format: Provide both narrative explanation AND structured JSON actions for flowsheet creation.""",

            AITaskType.OPTIMIZE_PROCESS: """
Focus on improving existing processes through:
1. Parameter optimization (reflux ratios, temperatures, pressures)
2. Energy integration and heat recovery
3. Yield and selectivity improvements
4. Equipment sizing optimization
5. Economic considerations

Provide specific numerical improvements with engineering justification.""",

            AITaskType.ANALYZE_SIMULATION: """
Analyze simulation results focusing on:
1. Convergence and numerical stability
2. Mass and energy balance closure
3. Product specifications and quality
4. Energy consumption and efficiency
5. Identify bottlenecks and improvement opportunities

Provide actionable recommendations based on the results.""",

            AITaskType.AUTONOMOUS_TEST: """
Design comprehensive testing protocols including:
1. Sensitivity analysis for key parameters
2. Design space exploration
3. Robustness testing under different conditions
4. Performance benchmarking
5. Safety and operability analysis

Create systematic test sequences that validate process performance."""
        }
        
        return base_prompt + task_specific.get(task_type, "")
    
    def _parse_user_intent(self, message: str) -> AITaskType:
        """Analyze user message to determine intent"""
        message_lower = message.lower()
        
        design_keywords = ["design", "create", "build", "develop", "make"]
        optimize_keywords = ["optimize", "improve", "enhance", "better", "efficient"]
        analyze_keywords = ["analyze", "results", "check", "review", "evaluate"]
        test_keywords = ["test", "autonomous", "validate", "verify"]
        
        if any(word in message_lower for word in design_keywords):
            return AITaskType.DESIGN_FLOWSHEET
        elif any(word in message_lower for word in optimize_keywords):
            return AITaskType.OPTIMIZE_PROCESS
        elif any(word in message_lower for word in analyze_keywords):
            return AITaskType.ANALYZE_SIMULATION
        elif any(word in message_lower for word in test_keywords):
            return AITaskType.AUTONOMOUS_TEST
        else:
            return AITaskType.GENERAL_QUERY
    
    def _extract_process_parameters(self, message: str) -> Dict[str, Any]:
        """Extract process-specific information from user message"""
        params = {
            "components": [],
            "operation_type": None,
            "conditions": {},
            "objectives": []
        }
        
        # Component detection
        common_components = [
            "benzene", "toluene", "methanol", "ethanol", "water", "acetone",
            "cyclohexane", "n-hexane", "propane", "butane", "ethylene", "propylene"
        ]
        
        for component in common_components:
            if component in message.lower():
                params["components"].append(component)
        
        # Operation type detection
        if any(word in message.lower() for word in ["distill", "separate", "fractionate"]):
            params["operation_type"] = "separation"
        elif any(word in message.lower() for word in ["react", "synthesis", "convert"]):
            params["operation_type"] = "reaction"
        elif any(word in message.lower() for word in ["heat", "cool", "exchange"]):
            params["operation_type"] = "heat_transfer"
        
        return params
    
    async def process_request(self, request: AIRequest) -> AIResponse:
        """Main AI processing function"""
        
        if not self.thunder_client:
            raise Exception("AI Engine not initialized. Call initialize() first.")
        
        # Build context-aware prompt
        context_info = self._build_context_string(request)
        system_prompt = self._get_system_prompt(request.task_type)
        
        user_prompt = f"""
User Message: {request.user_message}

Current Context:
{context_info}

Process Parameters Detected: {self._extract_process_parameters(request.user_message)}

Please provide your response as a chemical process engineer, including both explanation and specific actions to take in the DeepSim interface.
"""

        try:
            # Get AI response from DeepSeek R1
            response = await self.thunder_client.create_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=2000
            )
            
            ai_message = response['choices'][0]['message']['content']
            
            # Parse response and extract actions
            actions = self._parse_ai_actions(ai_message, request.task_type)
            
            # Update conversation context
            self.conversation_context.append({
                "timestamp": datetime.now().isoformat(),
                "user_message": request.user_message,
                "ai_response": ai_message,
                "task_type": request.task_type.value,
                "actions": actions
            })
            
            return AIResponse(
                message=ai_message,
                actions=actions,
                confidence=0.85,  # Could be calculated based on model confidence
                reasoning="DeepSeek R1 analysis based on process engineering principles",
                suggested_followups=self._generate_followups(request.task_type)
            )
            
        except Exception as e:
            logger.error(f"AI processing failed: {str(e)}")
            return self._get_fallback_response(request)
    
    def _build_context_string(self, request: AIRequest) -> str:
        """Build context information for the AI"""
        context_parts = []
        
        if request.flowsheet_data:
            units_count = len(request.flowsheet_data.get('units', []))
            context_parts.append(f"Current flowsheet has {units_count} unit operations")
            
            if units_count > 0:
                unit_types = [unit.get('type') for unit in request.flowsheet_data.get('units', [])]
                context_parts.append(f"Unit types: {', '.join(set(unit_types))}")
        
        if request.simulation_results:
            status = request.simulation_results.get('status', 'unknown')
            context_parts.append(f"Last simulation status: {status}")
        
        if request.conversation_history:
            context_parts.append(f"Conversation history: {len(request.conversation_history)} previous exchanges")
        
        return "\n".join(context_parts) if context_parts else "No specific context available"
    
    def _parse_ai_actions(self, ai_message: str, task_type: AITaskType) -> List[Dict[str, Any]]:
        """Extract executable actions from AI response"""
        actions = []
        
        if task_type == AITaskType.DESIGN_FLOWSHEET:
            # Look for unit creation commands in AI response
            if "distillation" in ai_message.lower():
                actions.append({
                    "type": "create_unit",
                    "unit_type": "DistillationColumn",
                    "parameters": {
                        "stages": 25,
                        "refluxRatio": 3.5,
                        "feedStage": 12,
                        "pressure": 101325,
                        "trayEfficiency": 0.85
                    },
                    "position": {"x": 400, "y": 200}
                })
            
            if "reactor" in ai_message.lower():
                actions.append({
                    "type": "create_unit",
                    "unit_type": "CSTR",
                    "parameters": {
                        "volume": 150,
                        "residence_time": 7200,
                        "temperature": 350,
                        "pressure": 200000
                    },
                    "position": {"x": 300, "y": 200}
                })
            
            if "heat exchanger" in ai_message.lower():
                actions.append({
                    "type": "create_unit",
                    "unit_type": "HeatExchanger",
                    "parameters": {
                        "approach_temp": 10,
                        "heat_transfer_coeff": 1000
                    },
                    "position": {"x": 150, "y": 200}
                })
        
        elif task_type == AITaskType.OPTIMIZE_PROCESS:
            actions.append({
                "type": "optimize_parameters",
                "target": "all_units",
                "optimization_type": "efficiency"
            })
        
        elif task_type == AITaskType.AUTONOMOUS_TEST:
            actions.append({
                "type": "run_test_sequence",
                "tests": ["sensitivity_analysis", "performance_validation", "robustness_check"]
            })
        
        return actions
    
    def _generate_followups(self, task_type: AITaskType) -> List[str]:
        """Generate relevant follow-up suggestions"""
        followups = {
            AITaskType.DESIGN_FLOWSHEET: [
                "Would you like me to optimize the design parameters?",
                "Shall I run a simulation to validate the design?",
                "Would you like to add heat integration to improve efficiency?"
            ],
            AITaskType.OPTIMIZE_PROCESS: [
                "Should I run a simulation to verify the improvements?",
                "Would you like me to analyze the economic impact?",
                "Shall I check for additional optimization opportunities?"
            ],
            AITaskType.ANALYZE_SIMULATION: [
                "Would you like me to suggest specific improvements?",
                "Shall I run additional test scenarios?",
                "Should I optimize the process based on these results?"
            ]
        }
        
        return followups.get(task_type, ["How else can I help you with this process?"])
    
    def _get_fallback_response(self, request: AIRequest) -> AIResponse:
        """Provide fallback response when AI service is unavailable"""
        fallback_message = """I apologize, but I'm currently unable to connect to the AI service. However, I can still help you with:

🏗️ **Process Design Guidelines**: I can suggest standard configurations for common separations
⚙️ **Parameter Recommendations**: Based on typical industrial practices
📊 **Simulation Setup**: Help configure your units for optimal performance

Please check that the Thunder Compute service is available, or try again in a moment."""
        
        return AIResponse(
            message=fallback_message,
            actions=[],
            confidence=0.0,
            reasoning="Fallback response due to AI service unavailability",
            suggested_followups=["Check AI service connection", "Try manual process design"]
        )

# Factory function for easy instantiation
async def create_ai_engine(thunder_api_key: str) -> ProcessEngineeringAI:
    """Create and initialize AI engine"""
    engine = ProcessEngineeringAI(thunder_api_key)
    await engine.initialize()
    return engine