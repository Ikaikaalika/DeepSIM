#!/usr/bin/env python3
"""
DeepSim MCP System Startup Script
Starts both MCP server and FastAPI backend with proper coordination
"""

import asyncio
import subprocess
import signal
import sys
import logging
import time
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPSystemManager:
    """Manages MCP server and FastAPI backend coordination"""
    
    def __init__(self):
        self.mcp_server_process = None
        self.fastapi_process = None
        self.shutdown_event = asyncio.Event()
        
    async def start_mcp_server(self):
        """Start the MCP server"""
        try:
            logger.info("Starting MCP server...")
            
            # Start MCP server as subprocess
            self.mcp_server_process = subprocess.Popen([
                sys.executable, "mcp_server.py"
            ], cwd="backend", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Give server time to initialize
            await asyncio.sleep(2)
            
            if self.mcp_server_process.poll() is None:
                logger.info("MCP server started successfully")
                return True
            else:
                stderr = self.mcp_server_process.stderr.read().decode()
                logger.error(f"MCP server failed to start: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            return False
    
    async def start_fastapi_backend(self):
        """Start FastAPI backend"""
        try:
            logger.info("Starting FastAPI backend...")
            
            # Set environment variable to enable MCP
            env = os.environ.copy()
            env["USE_MCP"] = "true"
            
            self.fastapi_process = subprocess.Popen([
                sys.executable, "main.py"
            ], cwd="backend", env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Give backend time to initialize
            await asyncio.sleep(3)
            
            if self.fastapi_process.poll() is None:
                logger.info("FastAPI backend started successfully")
                return True
            else:
                stderr = self.fastapi_process.stderr.read().decode()
                logger.error(f"FastAPI backend failed to start: {stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to start FastAPI backend: {e}")
            return False
    
    async def health_check(self):
        """Check if both services are healthy"""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                # Check FastAPI health
                async with session.get("http://localhost:8000/health") as resp:
                    if resp.status == 200:
                        health_data = await resp.json()
                        logger.info(f"System health: {health_data}")
                        
                        if health_data.get("services", {}).get("mcp_server") == "online":
                            logger.info("✅ MCP integration is working")
                        else:
                            logger.warning("⚠️ MCP integration not active")
                        
                        return True
                    else:
                        logger.error(f"Health check failed: {resp.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False
    
    async def monitor_processes(self):
        """Monitor both processes and restart if needed"""
        while not self.shutdown_event.is_set():
            try:
                # Check MCP server
                if self.mcp_server_process and self.mcp_server_process.poll() is not None:
                    logger.error("MCP server died, restarting...")
                    await self.start_mcp_server()
                
                # Check FastAPI backend
                if self.fastapi_process and self.fastapi_process.poll() is not None:
                    logger.error("FastAPI backend died, restarting...")
                    await self.start_fastapi_backend()
                
                # Health check every 30 seconds
                await asyncio.sleep(30)
                await self.health_check()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def shutdown(self):
        """Gracefully shutdown both processes"""
        logger.info("Shutting down DeepSim MCP system...")
        
        self.shutdown_event.set()
        
        # Terminate FastAPI backend
        if self.fastapi_process:
            self.fastapi_process.terminate()
            try:
                await asyncio.wait_for(asyncio.create_subprocess_exec(
                    "sleep", "0.1"  # Give process time to terminate
                ), timeout=5)
            except:
                self.fastapi_process.kill()
            logger.info("FastAPI backend stopped")
        
        # Terminate MCP server
        if self.mcp_server_process:
            self.mcp_server_process.terminate()
            try:
                await asyncio.wait_for(asyncio.create_subprocess_exec(
                    "sleep", "0.1"
                ), timeout=5)
            except:
                self.mcp_server_process.kill()
            logger.info("MCP server stopped")
        
        logger.info("DeepSim MCP system shutdown complete")
    
    async def start_system(self):
        """Start the complete MCP system"""
        logger.info("🚀 Starting DeepSim with Model Context Protocol (MCP)")
        
        # Start MCP server first
        if not await self.start_mcp_server():
            logger.error("Failed to start MCP server, exiting...")
            return False
        
        # Start FastAPI backend
        if not await self.start_fastapi_backend():
            logger.error("Failed to start FastAPI backend, exiting...")
            await self.shutdown()
            return False
        
        # Initial health check
        await asyncio.sleep(2)
        if not await self.health_check():
            logger.error("Initial health check failed")
            await self.shutdown()
            return False
        
        logger.info("✅ DeepSim MCP system started successfully!")
        logger.info("📊 FastAPI backend: http://localhost:8000")
        logger.info("🧪 Frontend interface: frontend/aspen-ai-interface.html")
        logger.info("🔧 MCP tools available: /mcp/tools")
        logger.info("📁 MCP resources available: /mcp/resources")
        
        # Start monitoring
        monitor_task = asyncio.create_task(self.monitor_processes())
        
        # Setup signal handlers
        def signal_handler():
            logger.info("Received shutdown signal")
            asyncio.create_task(self.shutdown())
        
        # Wait for shutdown signal
        try:
            await self.shutdown_event.wait()
        finally:
            monitor_task.cancel()
            await self.shutdown()
        
        return True

def main():
    """Main entry point"""
    manager = MCPSystemManager()
    
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(manager.shutdown())
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run the system
        success = asyncio.run(manager.start_system())
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()