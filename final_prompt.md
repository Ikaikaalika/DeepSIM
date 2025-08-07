You are to build a complete AI-powered chemical process simulation platform that emulates and improves upon Aspen Plus. The system must include:

───────────────────────────────────────
🌐 1. Web-Based GUI (Frontend)
───────────────────────────────────────

Framework: React.js with React Flow.

✔ Users can:
  - Drag and drop unit operations (e.g., pump, reactor, distillation column, heater)
  - Connect streams between units visually
  - Edit parameters of each unit via a right-side property panel
  - View simulation results (stream table, plots, unit data)
  - Open a chat interface with an LLM assistant (DeepSeek R1) to build, edit, simulate, or analyze the process

Diagram requirements:
  - Snap-to-grid layout
  - Zoom, pan, undo/redo
  - Highlight errors in simulation (e.g., unconnected units)

───────────────────────────────────────
⚡ 2. LLM Integration (DeepSeek R1 on Thunder Compute)
───────────────────────────────────────

Use **Thunder Compute** to:
  - Host inference endpoint for real-time LLM responses
  - Run LoRA or QLoRA fine-tuning on a private, provisioned node

✔ LLM Tasks:
  - Interpret user instructions (e.g., “Add a distillation column after the reactor”)
  - Generate JSON graph updates (e.g., new units, stream routing)
  - Explain simulation results, errors, or optimization ideas
  - Perform CoT reasoning to answer "why" or "how to improve" questions

Integration:
  - Deploy LLM inference endpoint on Thunder with `vLLM`, `text-generation-inference`, or similar
  - Fine-tune with PEFT + DeepSeek using Thunder training node
  - Backend calls Thunder API (via FastAPI route) to send prompt + receive JSON output

Example JSON Response from LLM:
```json
{
  "action": "add_unit",
  "type": "Reactor",
  "id": "R1",
  "inlet": "S2",
  "outlet": "S3",
  "parameters": {
    "conversion": 0.85,
    "temperature": 350,
    "pressure": 1
  }
}

───────────────────────────────────────
⚙️ 3. Backend Simulation Engine (IDAES + Pyomo)
───────────────────────────────────────

Framework: Python 3.10+, FastAPI

Simulation Engine: IDAES (MIT license)

Responsibilities:
	•	Convert process graph JSON into a Pyomo/IDAES simulation model
	•	Solve flowsheet (steady-state) using IPOPT
	•	Return simulation results per unit and stream (T, P, flow, composition, conversion, etc.)
	•	Handle infeasibility gracefully with error messages and suggestions

Optional: plug in surrogate models in the future (e.g., ML-based distillation column)

───────────────────────────────────────
🧠 4. State Management and Synchronization
───────────────────────────────────────

Maintain central graph_state.json (or SQLite) that tracks:
	•	All unit ops, connections, stream data, and parameters
	•	Updated by GUI or LLM actions
	•	Always synced between:
	•	Diagram
	•	LLM agent
	•	Simulation engine

Simulation is triggered on-demand (manual button or LLM-confirmed updates)

───────────────────────────────────────
🧱 5. File & Project Structure

ai_process_sim/
│
├── backend/
│   ├── main.py              # FastAPI server
│   ├── graph_state.py       # Graph data manager
│   ├── idaes_engine.py      # IDAES model runner
│   ├── llm_client.py        # Sends prompt to Thunder inference API
│   ├── database.sqlite      # Store user flowsheets
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.js
│   │   ├── FlowsheetCanvas.js  # React Flow diagram
│   │   ├── ChatPanel.js        # LLM UI
│   │   ├── PropertiesPanel.js  # Sidebar for unit config
│   │   └── ResultsPanel.js     # Simulation output
│
├── llm_finetune/
│   ├── train_deepseek_thunder.py  # LoRA/QLoRA fine-tuning script (uses Thunder GPU)
│   ├── dataset.jsonl              # Training pairs: text ↔ flowsheet JSON
│   └── tokenizer_config.json
│
├── shared/
│   ├── flowsheet_schema.json      # Standard schema for units and streams
│   └── prompts/
│       ├── text_to_graph.json
│       ├── edit_unit.json
│       └── interpret_results.json

───────────────────────────────────────
📚 6. LLM Training Details (on Thunder)

Model: DeepSeek R1 7B (or 33B if Thunder node supports)

Training Method: LoRA or QLoRA via peft or trl

Data:
	•	Paired examples: natural language ↔ structured JSON flowsheets
	•	Includes design tasks, edit instructions, simulation explanations

Finetune Steps:
	•	Upload dataset to Thunder
	•	Use transformers + peft to fine-tune for 3–5 epochs
	•	Save adapter weights, load them on Thunder inference node
	•	Expose as /inference endpoint (or via HuggingFace text-generation-inference)

───────────────────────────────────────
📤 7. Output + Export

✔ Export options:
	•	Diagram as SVG/PNG
	•	Simulation results as CSV or Excel
	•	Full flowsheet as JSON
	•	Generate a simulation report using LLM (“Write a design report”)

───────────────────────────────────────
💬 8. Example Chat Flows

“Build a methanol production flowsheet with syngas and a distillation column”

	•	LLM creates full graph
	•	Renders diagram
	•	Sends to IDAES
	•	Simulation runs, results shown in stream table

“Why is the purity low?”

	•	LLM examines results
	•	Suggests changes (e.g., increase stages or reflux)

“Set the column pressure to 2 atm and simulate again”

	•	Parameter updated
	•	Simulation re-run
	•	Results returned

───────────────────────────────────────
✅ Goals
	•	Provide Aspen-like interface with added LLM interaction
	•	Full simulation and editing through GUI or language
	•	All LLM inference and training must run on Thunder Compute
	•	Ready for commercial deployment (MIT-licensed stack, React + Python)

 vercel cli, thunder compute cli, and aws cli are all installed