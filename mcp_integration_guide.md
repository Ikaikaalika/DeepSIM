# DeepSim MCP Integration Guide

DeepSim now implements full Model Context Protocol (MCP) integration, providing standardized AI-tool interaction, persistent context management, and enhanced capabilities for chemical process engineering.

## 🎯 What is MCP?

Model Context Protocol (MCP) is an open standard that enables secure, controlled interaction between AI models and external tools/resources. It provides:

- **Standardized Tool Discovery**: AI can dynamically discover available capabilities
- **Persistent Context Management**: Conversation state maintained across sessions  
- **Resource Access**: Structured access to databases, files, and external systems
- **Security**: Controlled, permission-based tool access
- **Extensibility**: Easy addition of new tools and capabilities

## 🏗️ DeepSim MCP Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DeepSim MCP System                      │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Browser)                                        │
│  ├── Chat Interface                                        │
│  └── Feedback Collection                                   │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Backend                                           │
│  ├── HTTP API Endpoints                                    │
│  ├── MCP Client Integration                                │
│  └── Feedback System                                       │
├─────────────────────────────────────────────────────────────┤
│  MCP Server                                                 │
│  ├── Tool Registry (8 core tools)                         │
│  ├── Resource Management                                   │
│  ├── Context Management                                    │
│  └── Process Engineering Logic                            │
├─────────────────────────────────────────────────────────────┤
│  Core Engines                                              │
│  ├── Rigorous Distillation (MESH)                        │
│  ├── Thermodynamic Properties                             │
│  ├── Process Simulation                                   │
│  └── Optimization Algorithms                              │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 MCP Tools Available

### 1. **create_flowsheet**
Create new chemical process flowsheets
```json
{
    "name": "Benzene Production Process",
    "description": "Catalytic reforming with separation",
    "process_type": "separation"
}
```

### 2. **add_unit_operation**  
Add unit operations to flowsheets
```json
{
    "flowsheet_id": "fs_123",
    "unit_type": "DistillationColumn",
    "unit_name": "Main Fractionator",
    "parameters": {
        "stages": 25,
        "refluxRatio": 3.5,
        "trayEfficiency": 0.85
    }
}
```

### 3. **design_distillation_column**
Rigorous distillation column design with MESH equations
```json
{
    "components": ["benzene", "toluene"],
    "separation_specs": {
        "distillate_purity": 0.99,
        "bottoms_purity": 0.95
    },
    "feed_conditions": {
        "temperature": 368.15,
        "pressure": 101325,
        "composition": {"benzene": 0.6, "toluene": 0.4}
    }
}
```

### 4. **run_simulation**
Execute rigorous process simulations
```json
{
    "flowsheet_id": "fs_123", 
    "simulation_options": {
        "thermodynamic_method": "PENG-ROBINSON",
        "convergence_tolerance": 1e-6,
        "max_iterations": 100
    }
}
```

### 5. **optimize_process**
Multi-objective process optimization
```json
{
    "flowsheet_id": "fs_123",
    "objective": "minimize_energy",
    "constraints": {
        "min_purity": 0.95,
        "max_energy": 5000
    }
}
```

### 6. **analyze_results**
Deep analysis of simulation results
```json
{
    "flowsheet_id": "fs_123",
    "analysis_type": "performance",
    "benchmarks": {"energy_target": 4500}
}
```

### 7. **calculate_properties**
Thermodynamic property calculations
```json
{
    "components": ["benzene", "toluene"],
    "composition": [0.6, 0.4],
    "temperature": 368.15,
    "pressure": 101325,
    "property_type": "density",
    "method": "PENG-ROBINSON"
}
```

### 8. **submit_feedback**
Collect user feedback for AI improvement
```json
{
    "turn_id": "turn_123",
    "conversation_id": "conv_456",
    "feedback_type": "thumbs_up",
    "rating": 5,
    "tags": ["accuracy", "helpfulness"]
}
```

## 📁 MCP Resources

### 1. **deepsim://contexts**
Active conversation contexts and flowsheet states

### 2. **deepsim://component_database**  
Chemical component database with thermodynamic properties

### 3. **deepsim://unit_operations**
Available unit operations library with configurations

### 4. **deepsim://simulation_methods**
Thermodynamic methods and simulation options

### 5. **deepsim://flowsheet/{id}**
Individual flowsheet data and context

### 6. **deepsim://feedback_analytics**
User feedback and performance analytics

## 🚀 Getting Started

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Start the MCP System
```bash
# Option A: Use the automated startup script
python start_mcp_system.py

# Option B: Manual startup
# Terminal 1: Start MCP server
python mcp_server.py

# Terminal 2: Start FastAPI backend  
python main.py
```

### 3. Verify MCP Integration
```bash
# Check system health
curl http://localhost:8000/health

# List available MCP tools
curl http://localhost:8000/mcp/tools

# List available MCP resources
curl http://localhost:8000/mcp/resources
```

### 4. Use the AI Interface
Open `frontend/aspen-ai-interface.html` in your browser and start chatting with the AI. The system will automatically use MCP for enhanced capabilities.

## 💬 Example MCP Conversations

### Design a Distillation Process
**User**: "Design a benzene-toluene separation with 99% purity"

**MCP Actions**:
1. `design_distillation_column` - Creates rigorous MESH design
2. `add_unit_operation` - Adds column to flowsheet
3. `calculate_properties` - Validates thermodynamic data
4. `analyze_results` - Provides performance insights

### Optimize Energy Consumption
**User**: "Minimize energy consumption in my current process"

**MCP Actions**:
1. `run_simulation` - Baseline performance analysis
2. `optimize_process` - Multi-objective optimization
3. `analyze_results` - Compare before/after performance
4. `submit_feedback` - Log optimization success

### Autonomous Testing
**User**: "Run comprehensive testing on this flowsheet"

**MCP Actions**:
1. `run_simulation` - Multiple scenarios
2. `analyze_results` - Performance validation
3. `calculate_properties` - Robustness testing  
4. `optimize_process` - Identify improvements

## 🔄 Context Management

MCP provides persistent context management:

```json
{
    "flowsheet_id": "fs_abc123",
    "conversation_id": "conv_xyz789", 
    "units": [
        {
            "id": "distillationcolumn_1",
            "type": "DistillationColumn",
            "parameters": {...}
        }
    ],
    "streams": [...],
    "last_simulation_results": {...},
    "user_preferences": {...}
}
```

This context is automatically maintained and shared between:
- AI model
- Process simulation engines  
- Optimization algorithms
- Analysis tools

## 📊 Monitoring and Debugging

### Health Checks
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
    "status": "healthy",
    "services": {
        "ai_engine": "online",
        "ai_protocol": "MCP", 
        "mcp_server": "online",
        "thunder_compute": "online"
    }
}
```

### MCP Tool Discovery
```bash
curl http://localhost:8000/mcp/tools
```

### MCP Resource Access
```bash  
curl http://localhost:8000/mcp/resources
```

### Debug Logs
```bash
# View backend logs
tail -f backend/logs/deepsim.log

# View MCP server logs  
python mcp_server.py --log-level DEBUG
```

## 🔧 Configuration

### Environment Variables
```bash
# Enable/disable MCP
USE_MCP=true

# Thunder Compute API
THUNDER_API_KEY=your_key_here

# MCP Server Command (optional)
MCP_SERVER_CMD=python,mcp_server.py
```

### Toggle Between MCP and Direct API
```python
# In main.py
use_mcp: bool = True  # Set to False for direct Thunder Compute API
```

## 🎯 Benefits of MCP Integration

### 1. **Enhanced AI Capabilities**
- Dynamic tool discovery
- Structured context management
- Better error handling and recovery

### 2. **Improved Performance**  
- Persistent context reduces redundant processing
- Efficient resource sharing between tools
- Optimized tool execution workflows

### 3. **Better User Experience**
- More accurate AI responses
- Contextual conversations
- Seamless tool integration

### 4. **Extensibility**
- Easy addition of new tools
- Modular architecture
- Standards-based integration

### 5. **Reliability**
- Automatic failover to direct API
- Health monitoring and recovery
- Robust error handling

## 🛠️ Development and Extension

### Adding New MCP Tools
1. Define tool in `mcp_server.py`
2. Implement handler function
3. Add to client in `mcp_client.py`
4. Update documentation

### Adding New Resources
1. Register resource in `_register_resources()`
2. Implement read handler
3. Update resource discovery
4. Test resource access

### Custom MCP Integrations
The MCP system is designed to be extended with:
- Custom thermodynamic property packages
- Third-party simulation engines
- External databases and APIs
- Advanced optimization algorithms
- Machine learning models

## 🔮 Future Enhancements

- **Streaming Responses**: Real-time tool execution updates
- **Multi-Agent Coordination**: Multiple AI agents working together
- **Advanced Context Sharing**: Cross-conversation context persistence  
- **Tool Composition**: Automatic chaining of related tools
- **Performance Analytics**: Detailed MCP performance monitoring

The MCP integration transforms DeepSim into a truly intelligent process engineering assistant with standardized, extensible, and robust AI-tool interactions.