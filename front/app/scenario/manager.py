import threading
import traceback
import time
from app.services.scenario_service import get_scenario

class ScenarioManager:
    def __init__(self):
        self._lock = threading.Lock()
        # Serialize Heavy Simulations: Only 1 at a time to prevent OOM
        self._sim_semaphore = threading.Semaphore(1)
        self.sessions = {}

    def _ensure_session(self, session_id):
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "status": "idle",
                "message": "",
                "progress": 0,
                "data": None,
                "error": None,
                "thread": None
            }

    def get_status(self, session_id):
        with self._lock:
            self._ensure_session(session_id)
            s = self.sessions[session_id]
            return {
                "status": s["status"],
                "message": s["message"],
                "progress": s["progress"],
                "error": str(s["error"]) if s["error"] else None
            }

    def get_data(self, session_id):
        with self._lock:
            return self.sessions.get(session_id, {}).get("data")

    def start_simulation(self, session_id, lau, radius, transport_modes_params):
        with self._lock:
            self._ensure_session(session_id)
            state = self.sessions[session_id]
            
            if state["status"] == "loading":
                return
            
            state["status"] = "loading"
            state["message"] = "Waiting for slot..."
            state["progress"] = 1
            state["data"] = None
            state["error"] = None
            
            thread = threading.Thread(
                target=self._run_simulation, 
                args=(session_id, lau, radius, transport_modes_params)
            )
            state["thread"] = thread
            thread.daemon = True
            thread.start()

    def _run_simulation(self, session_id, lau, radius, params):
        print(f"[MANAGER] Request for {session_id} | LAU={lau} R={radius}")
        
        # Acquire Semaphore: block if busy
        # storage, network, or high load might delay this, so we give a generous timeout
        has_slot = self._sim_semaphore.acquire(timeout=600) # 10m timeout wait
        if not has_slot:
            with self._lock:
                if session_id in self.sessions:
                    self.sessions[session_id]["status"] = "error"
                    self.sessions[session_id]["error"] = "Server busy (timeout)"
                    self.sessions[session_id]["message"] = "Server busy (timeout)"
            return

        try:
            print(f"[MANAGER] Starting simulation for {session_id}")
            self.update_progress(session_id, 10, "Preparing spatial data...")
            print("[MANAGER] Progress 10%")
            self.update_progress(session_id, 25, "Running heavy spatial models...")
            print("[MANAGER] Progress 25% - Calling get_scenario")
            
            # This call is SHARED cache. If another user calculated this LAU/Rad,
            # it will return instantly here and save computation time.
            data = get_scenario(
                local_admin_unit_id=lau,
                radius=radius,
                transport_modes_params=params
            )
            
            self.update_progress(session_id, 90, "Finalizing results...")
            
            with self._lock:
                state = self.sessions[session_id]
                state["data"] = data
                state["status"] = "ready"
                state["progress"] = 100
                state["message"] = "Simulation complete!"
            print("[MANAGER] Simulation COMPLETE")
                
        except Exception as e:
            with self._lock:
                state = self.sessions[session_id]
                state["status"] = "error"
                state["error"] = e
                state["message"] = f"Error: {str(e)}"
                traceback.print_exc()
        finally:
            self._sim_semaphore.release()

    def update_progress(self, session_id, val, msg):
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id]["progress"] = val
                self.sessions[session_id]["message"] = msg

manager = ScenarioManager()
