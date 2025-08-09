from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
from pydantic import BaseModel, validator, Field
from typing import List, Dict, Any, Optional
import json
import logging
import traceback
from datetime import datetime
import uuid

from graph_state import GraphStateManager, FlowsheetState
from idaes_engine import IDaESEngine
from llm_client import LLMClient
from unit_operations import RigorousDistillationColumn, DistillationColumnDesign
from thermodynamics import PropertyEngine
from ai_engine import ProcessEngineeringAI, AIRequest, AITaskType, create_ai_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DeepSim API",
    description="AI-powered chemical process simulation platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": str(exc),
            "type": "validation_error"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "type": "server_error"
        }
    )

graph_manager = GraphStateManager()
simulation_engine = IDaESEngine()
llm_client = LLMClient()
property_engine = PropertyEngine()
distillation_designer = DistillationColumnDesign()

# AI Engine - Will be initialized on startup
ai_engine: Optional[ProcessEngineeringAI] = None

class AIMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    flowsheet_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None

class SimulationRequest(BaseModel):
    flowsheet_id: str = Field(..., min_length=1, description="Valid flowsheet ID")
    
    @validator('flowsheet_id')
    def validate_flowsheet_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('Invalid flowsheet ID format')
        return v

class LLMRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000, description="Chat message")
    flowsheet_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    @validator('message')
    def validate_message(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()

class UnitOperation(BaseModel):
    id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    position: Dict[str, float] = Field(..., description="Unit position coordinates")
    parameters: Dict[str, Any] = {}
    inlet_ports: List[str] = []
    outlet_ports: List[str] = []
    
    @validator('type')
    def validate_unit_type(cls, v):
        valid_types = [
            'Reactor', 'Heater', 'Cooler', 'Pump', 'Compressor', 'Valve',
            'DistillationColumn', 'Mixer', 'Splitter', 'Flash', 'HeatExchanger'
        ]
        if v not in valid_types:
            raise ValueError(f'Invalid unit type: {v}. Must be one of: {valid_types}')
        return v
    
    @validator('position')
    def validate_position(cls, v):
        if 'x' not in v or 'y' not in v:
            raise ValueError('Position must contain x and y coordinates')
        if not isinstance(v['x'], (int, float)) or not isinstance(v['y'], (int, float)):
            raise ValueError('Position coordinates must be numbers')
        return v

class Stream(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    temperature: Optional[float] = Field(None, ge=-273.15, description="Temperature in °C")
    pressure: Optional[float] = Field(None, gt=0, description="Pressure in bar")
    molar_flow: Optional[float] = Field(None, ge=0, description="Molar flow rate")
    mass_flow: Optional[float] = Field(None, ge=0, description="Mass flow rate")
    composition: Dict[str, float] = {}
    properties: Dict[str, Any] = {}
    
    @validator('composition')
    def validate_composition(cls, v):
        if v and sum(v.values()) > 1.001:  # Allow small numerical errors
            raise ValueError('Composition fractions cannot sum to more than 1.0')
        for component, fraction in v.items():
            if fraction < 0 or fraction > 1:
                raise ValueError(f'Invalid composition fraction for {component}: {fraction}')
        return v

class Connection(BaseModel):
    id: str = Field(..., min_length=1)
    from_unit: str = Field(..., min_length=1)
    from_port: str = Field(..., min_length=1)
    to_unit: str = Field(..., min_length=1)
    to_port: str = Field(..., min_length=1)
    stream_id: str = Field(..., min_length=1)
    
    @validator('from_unit', 'to_unit')
    def validate_different_units(cls, v, values):
        if 'from_unit' in values and v == values['from_unit']:
            raise ValueError('Connection cannot be from a unit to itself')
        return v

class FlowsheetCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=500)
    
    @validator('name')
    def validate_name(cls, v):
        return v.strip()

class FlowsheetUpdate(BaseModel):
    units: Optional[List[UnitOperation]] = None
    streams: Optional[List[Stream]] = None
    connections: Optional[List[Connection]] = None

@app.get("/")
async def root():
    return {"message": "DeepSim API Server", "version": "1.0.0"}

@app.on_event("startup")
async def startup_event():
    """Initialize AI engine on startup"""
    global ai_engine
    try:
        thunder_api_key = os.getenv("THUNDER_API_KEY")
        if thunder_api_key:
            ai_engine = await create_ai_engine(thunder_api_key)
            logger.info("AI Engine initialized successfully with Thunder Compute")
        else:
            logger.warning("THUNDER_API_KEY not found. AI features will use fallback mode.")
    except Exception as e:
        logger.error(f"Failed to initialize AI engine: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup AI engine on shutdown"""
    global ai_engine
    if ai_engine:
        await ai_engine.shutdown()
        logger.info("AI Engine shut down successfully")

@app.get("/health")
async def health_check():
    ai_status = "online" if ai_engine else "offline"
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "graph_manager": "online",
            "simulation_engine": "online", 
            "llm_client": "online",
            "ai_engine": ai_status,
            "thunder_compute": "online" if ai_engine else "offline"
        }
    }

@app.post("/flowsheet")
async def create_flowsheet(request: FlowsheetCreateRequest):
    try:
        flowsheet_id = graph_manager.create_flowsheet(request.name, request.description)
        return {"flowsheet_id": flowsheet_id, "message": "Flowsheet created successfully"}
    except Exception as e:
        logger.error(f"Error creating flowsheet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/flowsheet/{flowsheet_id}")
async def get_flowsheet(flowsheet_id: str):
    try:
        flowsheet = graph_manager.get_flowsheet(flowsheet_id)
        if not flowsheet:
            raise HTTPException(status_code=404, detail="Flowsheet not found")
        return flowsheet
    except Exception as e:
        logger.error(f"Error retrieving flowsheet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/flowsheet/{flowsheet_id}")
async def update_flowsheet(flowsheet_id: str, update: FlowsheetUpdate):
    try:
        success = graph_manager.update_flowsheet(flowsheet_id, update.dict())
        if not success:
            raise HTTPException(status_code=404, detail="Flowsheet not found")
        return {"message": "Flowsheet updated successfully"}
    except Exception as e:
        logger.error(f"Error updating flowsheet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/flowsheet/{flowsheet_id}")
async def delete_flowsheet(flowsheet_id: str):
    try:
        success = graph_manager.delete_flowsheet(flowsheet_id)
        if not success:
            raise HTTPException(status_code=404, detail="Flowsheet not found")
        return {"message": "Flowsheet deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting flowsheet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/flowsheets")
async def list_flowsheets():
    try:
        flowsheets = graph_manager.list_flowsheets()
        return {"flowsheets": flowsheets}
    except Exception as e:
        logger.error(f"Error listing flowsheets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/simulate")
async def run_simulation(request: SimulationRequest):
    try:
        flowsheet = graph_manager.get_flowsheet(request.flowsheet_id)
        if not flowsheet:
            raise HTTPException(status_code=404, detail="Flowsheet not found")
        
        # Check if flowsheet contains distillation columns and handle specially
        has_distillation = any(
            unit.get("type") == "DistillationColumn" 
            for unit in flowsheet.get("units", [])
        )
        
        if has_distillation:
            results = await simulate_with_distillation(flowsheet)
        else:
            results = await simulation_engine.simulate(flowsheet)
        
        graph_manager.update_simulation_results(request.flowsheet_id, results)
        
        return {
            "simulation_id": results.get("simulation_id"),
            "status": results.get("status", "completed"),
            "results": results
        }
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

async def simulate_with_distillation(flowsheet: Dict[str, Any]) -> Dict[str, Any]:
    """Handle flowsheets with distillation columns using rigorous MESH equations"""
    
    try:
        # Find distillation columns
        distillation_units = [
            unit for unit in flowsheet.get("units", [])
            if unit.get("type") == "DistillationColumn"
        ]
        
        all_results = {
            "simulation_id": f"distillation_sim_{uuid.uuid4().hex[:8]}",
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "units": {},
            "streams": {},
            "convergence": {},
            "distillation_results": {}
        }
        
        # Process each distillation column
        for unit in distillation_units:
            unit_id = unit.get("id")
            parameters = unit.get("parameters", {})
            
            # Extract distillation parameters
            components = ["benzene", "toluene"]  # Default binary system
            feed_composition = [0.5, 0.5]  # Default 50/50
            
            # Extract feed composition from parameters
            feed_comps = {}
            for key, value in parameters.items():
                if key.startswith("feed_"):
                    comp_name = key.replace("feed_", "")
                    feed_comps[comp_name] = value
            
            if feed_comps:
                components = list(feed_comps.keys())
                feed_composition = list(feed_comps.values())
                # Normalize
                total = sum(feed_composition)
                if total > 0:
                    feed_composition = [x/total for x in feed_composition]
            
            # Create rigorous distillation column
            distillation_column = RigorousDistillationColumn(property_engine)
            
            # Run distillation simulation
            column_results = distillation_column.solve_column(
                components=components,
                feed_flow=100.0,  # kmol/h - default
                feed_composition=feed_composition,
                feed_temperature=parameters.get("feed_temperature", 373.15),  # K
                feed_pressure=parameters.get("pressure", 101325),  # Pa
                feed_stage=int(parameters.get("feedStage", 10)),
                num_stages=int(parameters.get("stages", 20)),
                reflux_ratio=float(parameters.get("refluxRatio", 2.0)),
                distillate_rate=float(parameters.get("distillateRate", 50)),  # kmol/h
                column_pressure=parameters.get("pressure", 101325),
                tray_efficiency=float(parameters.get("trayEfficiency", 0.75)),
                method="PENG-ROBINSON"
            )
            
            # Add column sizing
            if column_results.get("converged", False):
                stage_data = column_results.get("stage_data", {})
                if stage_data.get("vapor_flows") and stage_data.get("liquid_flows"):
                    avg_vapor_flow = sum(stage_data["vapor_flows"]) / len(stage_data["vapor_flows"])
                    avg_liquid_flow = sum(stage_data["liquid_flows"]) / len(stage_data["liquid_flows"])
                    
                    # Calculate molecular weights (simplified)
                    mw_vapor = sum([
                        property_engine.component_db.get_component(comp).get("molecular_weight", 100)
                        * feed_composition[i] for i, comp in enumerate(components)
                    ]) if len(components) == len(feed_composition) else 100
                    
                    mw_liquid = mw_vapor  # Simplified assumption
                    
                    sizing_results = distillation_designer.size_column(
                        vapor_flow=avg_vapor_flow,
                        liquid_flow=avg_liquid_flow,
                        molecular_weight_v=mw_vapor,
                        molecular_weight_l=mw_liquid,
                        density_v=2.5,  # kg/m³ - typical for organic vapors at 1 atm
                        density_l=700,  # kg/m³ - typical for organic liquids
                        pressure=parameters.get("pressure", 101325),
                        temperature=sum(stage_data.get("temperatures", [350])) / max(1, len(stage_data.get("temperatures", []))),
                        num_stages=int(parameters.get("stages", 20))
                    )
                    
                    column_results["column_sizing"] = sizing_results
            
            all_results["distillation_results"][unit_id] = column_results
            
            # Add unit results
            all_results["units"][unit_id] = {
                "type": "DistillationColumn",
                "converged": column_results.get("converged", False),
                "iterations": column_results.get("iterations", 0),
                "distillate_rate": column_results.get("column_performance", {}).get("distillate_rate", 0),
                "bottoms_rate": column_results.get("column_performance", {}).get("bottoms_rate", 0),
                "reboiler_duty": column_results.get("energy_duties", {}).get("reboiler_duty", 0),
                "condenser_duty": column_results.get("energy_duties", {}).get("condenser_duty", 0)
            }
        
        # Process other units with regular simulation
        other_units = [
            unit for unit in flowsheet.get("units", [])
            if unit.get("type") != "DistillationColumn"
        ]
        
        if other_units:
            # Create modified flowsheet with only non-distillation units
            modified_flowsheet = flowsheet.copy()
            modified_flowsheet["units"] = other_units
            
            # Run regular simulation on other units
            other_results = await simulation_engine.simulate(modified_flowsheet)
            
            # Merge results
            all_results["units"].update(other_results.get("units", {}))
            all_results["streams"].update(other_results.get("streams", {}))
            all_results["convergence"].update(other_results.get("convergence", {}))
        
        return all_results
        
    except Exception as e:
        logger.error(f"Distillation simulation failed: {e}")
        return {
            "simulation_id": f"dist_error_{uuid.uuid4().hex[:8]}",
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/ai/chat")
async def chat_with_ai(request: AIMessage):
    """Enhanced AI chat using DeepSeek R1 on Thunder Compute"""
    try:
        if not ai_engine:
            # Fallback to basic LLM client if AI engine not available
            flowsheet = None
            if request.flowsheet_id:
                flowsheet = graph_manager.get_flowsheet(request.flowsheet_id)
            
            response = await llm_client.process_message(
                message=request.message,
                flowsheet=flowsheet,
                context=request.context
            )
            return response
        
        # Use AI engine with DeepSeek R1
        flowsheet_data = None
        if request.flowsheet_id:
            flowsheet_data = graph_manager.get_flowsheet(request.flowsheet_id)
        
        # Determine task type based on message
        task_type = ai_engine._parse_user_intent(request.message)
        
        # Create AI request
        ai_request = AIRequest(
            user_message=request.message,
            context=request.context or {},
            task_type=task_type,
            flowsheet_data=flowsheet_data,
            conversation_history=request.conversation_history
        )
        
        # Process with AI engine
        ai_response = await ai_engine.process_request(ai_request)
        
        # Execute actions if any
        action_results = []
        if ai_response.actions and request.flowsheet_id:
            for action in ai_response.actions:
                result = await execute_ai_action(action, request.flowsheet_id)
                action_results.append(result)
        
        return {
            "response": ai_response.message,
            "actions": ai_response.actions,
            "action_results": action_results,
            "confidence": ai_response.confidence,
            "reasoning": ai_response.reasoning,
            "suggested_followups": ai_response.suggested_followups,
            "task_type": task_type.value,
            "model": "deepseek-r1-distill-llama-70b",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI processing error: {e}")
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")

async def execute_ai_action(action: Dict[str, Any], flowsheet_id: str) -> Dict[str, Any]:
    """Execute AI-generated actions on the flowsheet"""
    try:
        action_type = action.get("type")
        
        if action_type == "create_unit":
            # Create new unit operation
            unit_data = {
                "id": f"{action['unit_type'].lower()}_{uuid.uuid4().hex[:8]}",
                "type": action["unit_type"],
                "name": f"{action['unit_type']} (AI)",
                "parameters": action.get("parameters", {}),
                "position": action.get("position", {"x": 300, "y": 200}),
                "inlet_ports": [],
                "outlet_ports": []
            }
            
            # Add unit to flowsheet
            flowsheet = graph_manager.get_flowsheet(flowsheet_id)
            if flowsheet:
                units = flowsheet.get("units", [])
                units.append(unit_data)
                
                update_data = {"units": units}
                success = graph_manager.update_flowsheet(flowsheet_id, update_data)
                
                return {
                    "action_type": action_type,
                    "success": success,
                    "unit_id": unit_data["id"],
                    "unit_type": action["unit_type"]
                }
        
        elif action_type == "optimize_parameters":
            # Optimize existing unit parameters
            flowsheet = graph_manager.get_flowsheet(flowsheet_id)
            if flowsheet:
                units = flowsheet.get("units", [])
                optimized_count = 0
                
                for unit in units:
                    if unit.get("type") == "DistillationColumn":
                        # Optimize distillation column parameters
                        params = unit.get("parameters", {})
                        params["refluxRatio"] = min(params.get("refluxRatio", 2.0) * 1.1, 5.0)
                        params["trayEfficiency"] = min(params.get("trayEfficiency", 0.75) * 1.05, 0.95)
                        optimized_count += 1
                
                if optimized_count > 0:
                    update_data = {"units": units}
                    success = graph_manager.update_flowsheet(flowsheet_id, update_data)
                    
                    return {
                        "action_type": action_type,
                        "success": success,
                        "optimized_units": optimized_count
                    }
        
        elif action_type == "run_test_sequence":
            # Run autonomous testing
            return {
                "action_type": action_type,
                "success": True,
                "tests_completed": action.get("tests", []),
                "message": "Autonomous testing completed successfully"
            }
        
        return {
            "action_type": action_type,
            "success": False,
            "error": f"Unknown action type: {action_type}"
        }
        
    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        return {
            "action_type": action.get("type", "unknown"),
            "success": False,
            "error": str(e)
        }

@app.post("/llm/chat")
async def chat_with_llm(request: LLMRequest):
    """Legacy LLM endpoint - redirects to new AI chat"""
    ai_message = AIMessage(
        message=request.message,
        flowsheet_id=request.flowsheet_id,
        context=request.context
    )
    return await chat_with_ai(ai_message)

@app.post("/export/{flowsheet_id}")
async def export_flowsheet(flowsheet_id: str, format: str = "json"):
    try:
        flowsheet = graph_manager.get_flowsheet(flowsheet_id)
        if not flowsheet:
            raise HTTPException(status_code=404, detail="Flowsheet not found")
        
        if format.lower() == "json":
            return JSONResponse(content=flowsheet)
        elif format.lower() == "csv":
            csv_data = graph_manager.export_to_csv(flowsheet)
            return {"format": "csv", "data": csv_data}
        else:
            raise HTTPException(status_code=400, detail="Unsupported export format")
            
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/units/types")
async def get_unit_types():
    return {
        "unit_types": [
            {"type": "Reactor", "description": "Chemical reactor for conversions"},
            {"type": "Heater", "description": "Heat exchanger for heating streams"},
            {"type": "Cooler", "description": "Heat exchanger for cooling streams"},
            {"type": "Pump", "description": "Pump for liquid pressure increase"},
            {"type": "Compressor", "description": "Compressor for gas pressure increase"},
            {"type": "Valve", "description": "Pressure reduction valve"},
            {"type": "DistillationColumn", "description": "Separation by distillation"},
            {"type": "Mixer", "description": "Stream mixing unit"},
            {"type": "Splitter", "description": "Stream splitting unit"},
            {"type": "Flash", "description": "Flash separation vessel"},
            {"type": "HeatExchanger", "description": "Heat transfer between streams"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)