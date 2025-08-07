# DeepSim - AI-Powered Chemical Process Simulation Platform

DeepSim is a modern, web-based chemical process simulation platform that combines the power of traditional process simulation with AI assistance. Built as an alternative to Aspen Plus, it features a React-based GUI with React Flow for process diagrams, FastAPI backend, IDAES simulation engine, and LLM integration for intelligent process design and analysis.

## 🌟 Features

- **Interactive Process Design**: Drag-and-drop unit operations with visual connections
- **AI Assistant**: Chat with DeepSeek R1 LLM to build, modify, and analyze processes
- **Real-time Simulation**: IDAES-powered chemical process simulation engine
- **Modern Web Interface**: React + TypeScript frontend with Tailwind CSS
- **Export Capabilities**: Save flowsheets as JSON, CSV, or generate reports
- **Thunder Compute Integration**: Ready for LLM inference and fine-tuning

## 🏗️ Architecture

```
DeepSim/
├── backend/              # FastAPI server
│   ├── main.py          # API endpoints
│   ├── graph_state.py   # Flowsheet state management
│   ├── idaes_engine.py  # IDAES simulation engine
│   └── llm_client.py    # Thunder Compute LLM integration
├── frontend/            # React TypeScript app
│   └── src/
│       ├── components/  # React components
│       ├── services/    # API client
│       └── types/       # TypeScript types
├── shared/              # Common schemas and prompts
└── llm_finetune/        # LLM training scripts
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm or yarn

### Backend Setup

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Start the FastAPI server:**
   ```bash
   python main.py
   ```
   The API will be available at `http://localhost:8000`

### Frontend Setup

1. **Install Node.js dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Start the React development server:**
   ```bash
   npm start
   ```
   The web app will be available at `http://localhost:3000`

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Thunder Compute Configuration
THUNDER_ENDPOINT=https://your-thunder-endpoint.com
THUNDER_API_KEY=your-api-key

# Database
DATABASE_URL=sqlite:///database.sqlite

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
```

### Frontend Configuration

Create a `.env` file in the frontend directory:

```env
REACT_APP_API_URL=http://localhost:8000
```
