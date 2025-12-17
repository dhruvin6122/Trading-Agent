from fastapi import FastAPI, HTTPException
import subprocess
import os
import signal
import sys
from typing import Optional
from contextlib import asynccontextmanager

# Global process reference
agent_process: Optional[subprocess.Popen] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Launch Agent automatically
    global agent_process
    try:
        if not agent_process:
            print("AUTO-START: Initializing...")
            # Logs created by main.py/config.py
            
            # Use sys.executable to ensure we use the same python env
            cmd = [sys.executable, "main.py"]
            # Start detached/background
            agent_process = subprocess.Popen(cmd, cwd=os.getcwd())
            print(f"AUTO-START: Agent launched with PID {agent_process.pid}")
    except Exception as e:
        print(f"AUTO-START FAILED: {e}")
        
    yield
    
    # Shutdown: Cleanup
    if agent_process:
        print("SHUTDOWN: Terminating Agent...")
        agent_process.terminate()

app = FastAPI(title="AI Trading Agent Control Panel", lifespan=lifespan)

@app.get("/")
def read_root():
    return {
        "status": "online", 
        "message": "AI Trading Agent API is ready",
        "agent_running": agent_process is not None and agent_process.poll() is None
    }

@app.post("/start")
def start_agent():
    global agent_process
    if agent_process and agent_process.poll() is None:
        return {"status": "error", "message": "Agent is already running"}
    
    # Run main.py as a subprocess
    try:
        # Using python executable from current environment
        cmd = [sys.executable, "main.py"]
        agent_process = subprocess.Popen(cmd, cwd=os.getcwd())
        return {"status": "success", "message": "Agent started", "pid": agent_process.pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop")
def stop_agent():
    global agent_process
    if not agent_process or agent_process.poll() is not None:
        return {"status": "error", "message": "Agent is not running"}
    
    try:
        # Terminate the process
        agent_process.terminate()
        try:
            agent_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            agent_process.kill()
            
        agent_process = None
        return {"status": "success", "message": "Agent stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
def get_status():
    global agent_process
    is_running = agent_process is not None and agent_process.poll() is None
    return {
        "running": is_running,
        "pid": agent_process.pid if is_running else None
    }

@app.get("/logs")
def get_logs(lines: int = 50):
    from config import LOG_FILE
    if not os.path.exists(LOG_FILE):
        return {"logs": []}
    
    try:
        with open(LOG_FILE, "r") as f:
            # Efficiently read last N lines
            all_lines = f.readlines()
            return {"logs": all_lines[-lines:]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading logs: {str(e)}")

@app.get("/stats")
def get_stats():
    from config import LOG_FILE
    if not os.path.exists(LOG_FILE):
        return {"error": "No logs found"}
    
    total_trades = 0
    wins = 0
    losses = 0
    
    try:
        with open(LOG_FILE, "r") as f:
            for line in f:
                if "[TRADE_RESULT]" in line:
                    total_trades += 1
                    # Parse Diff from line: ... Diff=0.12345
                    try:
                        parts = line.split("Diff=")
                        if len(parts) > 1:
                            val = float(parts[1].strip())
                            if val > 0:
                                wins += 1
                            else:
                                losses += 1
                    except:
                        pass
        
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": f"{win_rate:.2f}%"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
