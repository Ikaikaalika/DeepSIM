import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class FlowsheetState(BaseModel):
    id: str
    name: str
    description: str = ""
    units: List[Dict[str, Any]] = []
    streams: List[Dict[str, Any]] = []
    connections: List[Dict[str, Any]] = []
    simulation_results: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

class GraphStateManager:
    def __init__(self, db_path: str = "database.sqlite"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS flowsheets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            data TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS simulation_results (
            id TEXT PRIMARY KEY,
            flowsheet_id TEXT NOT NULL,
            results TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (flowsheet_id) REFERENCES flowsheets (id)
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_flowsheet(self, name: str, description: str = "") -> str:
        flowsheet_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        flowsheet = FlowsheetState(
            id=flowsheet_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO flowsheets (id, name, description, data, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            flowsheet_id,
            name,
            description,
            json.dumps(flowsheet.dict()),
            now,
            now
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created flowsheet: {flowsheet_id}")
        return flowsheet_id
    
    def get_flowsheet(self, flowsheet_id: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT data FROM flowsheets WHERE id = ?
        ''', (flowsheet_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    def update_flowsheet(self, flowsheet_id: str, update_data: Dict[str, Any]) -> bool:
        flowsheet = self.get_flowsheet(flowsheet_id)
        if not flowsheet:
            return False
        
        if "units" in update_data and update_data["units"] is not None:
            flowsheet["units"] = update_data["units"]
        
        if "streams" in update_data and update_data["streams"] is not None:
            flowsheet["streams"] = update_data["streams"]
        
        if "connections" in update_data and update_data["connections"] is not None:
            flowsheet["connections"] = update_data["connections"]
        
        flowsheet["updated_at"] = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE flowsheets SET data = ?, updated_at = ? WHERE id = ?
        ''', (json.dumps(flowsheet), flowsheet["updated_at"], flowsheet_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated flowsheet: {flowsheet_id}")
        return True
    
    def delete_flowsheet(self, flowsheet_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM simulation_results WHERE flowsheet_id = ?', (flowsheet_id,))
        cursor.execute('DELETE FROM flowsheets WHERE id = ?', (flowsheet_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if deleted:
            logger.info(f"Deleted flowsheet: {flowsheet_id}")
        
        return deleted
    
    def list_flowsheets(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, name, description, created_at, updated_at FROM flowsheets
        ORDER BY updated_at DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        flowsheets = []
        for row in results:
            flowsheets.append({
                "id": row[0],
                "name": row[1], 
                "description": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            })
        
        return flowsheets
    
    def update_simulation_results(self, flowsheet_id: str, results: Dict[str, Any]) -> bool:
        flowsheet = self.get_flowsheet(flowsheet_id)
        if not flowsheet:
            return False
        
        flowsheet["simulation_results"] = results
        flowsheet["updated_at"] = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        UPDATE flowsheets SET data = ?, updated_at = ? WHERE id = ?
        ''', (json.dumps(flowsheet), flowsheet["updated_at"], flowsheet_id))
        
        result_id = str(uuid.uuid4())
        cursor.execute('''
        INSERT INTO simulation_results (id, flowsheet_id, results, created_at)
        VALUES (?, ?, ?, ?)
        ''', (result_id, flowsheet_id, json.dumps(results), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Updated simulation results for flowsheet: {flowsheet_id}")
        return True
    
    def add_unit(self, flowsheet_id: str, unit: Dict[str, Any]) -> bool:
        flowsheet = self.get_flowsheet(flowsheet_id)
        if not flowsheet:
            return False
        
        flowsheet["units"].append(unit)
        return self.update_flowsheet(flowsheet_id, {"units": flowsheet["units"]})
    
    def remove_unit(self, flowsheet_id: str, unit_id: str) -> bool:
        flowsheet = self.get_flowsheet(flowsheet_id)
        if not flowsheet:
            return False
        
        flowsheet["units"] = [u for u in flowsheet["units"] if u.get("id") != unit_id]
        flowsheet["connections"] = [c for c in flowsheet["connections"] 
                                  if c.get("from_unit") != unit_id and c.get("to_unit") != unit_id]
        
        return self.update_flowsheet(flowsheet_id, {
            "units": flowsheet["units"],
            "connections": flowsheet["connections"]
        })
    
    def add_connection(self, flowsheet_id: str, connection: Dict[str, Any]) -> bool:
        flowsheet = self.get_flowsheet(flowsheet_id)
        if not flowsheet:
            return False
        
        flowsheet["connections"].append(connection)
        return self.update_flowsheet(flowsheet_id, {"connections": flowsheet["connections"]})
    
    def export_to_csv(self, flowsheet: Dict[str, Any]) -> str:
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["Type", "ID", "Name", "Parameters"])
        
        for unit in flowsheet.get("units", []):
            writer.writerow([
                "Unit",
                unit.get("id", ""),
                unit.get("name", ""),
                json.dumps(unit.get("parameters", {}))
            ])
        
        for stream in flowsheet.get("streams", []):
            writer.writerow([
                "Stream",
                stream.get("id", ""),
                stream.get("name", ""),
                json.dumps({
                    "temperature": stream.get("temperature"),
                    "pressure": stream.get("pressure"),
                    "flow": stream.get("molar_flow"),
                    "composition": stream.get("composition", {})
                })
            ])
        
        return output.getvalue()