import threading
import traceback
import time
import gc
from app.services.scenario_service import get_scenario

class ScenarioManager:
    MAX_SESSIONS = 3  # Limit memory usage for idle tabs

    def __init__(self):
        self._lock = threading.Lock()
        # Serialize Heavy Simulations: Only 1 at a time to prevent OOM
        self._sim_semaphore = threading.Semaphore(1)
        self.sessions = {}
        self._session_access_times = {}

    def _ensure_session(self, session_id):
        if session_id not in self.sessions:
            # Cleanup old sessions if we exceed limit
            if len(self.sessions) >= self.MAX_SESSIONS:
                oldest_sid = min(self._session_access_times, key=self._session_access_times.get)
                print(f"[MANAGER] Cleaning up old session data: {oldest_sid}")
                del self.sessions[oldest_sid]
                del self._session_access_times[oldest_sid]
                gc.collect()

            self.sessions[session_id] = {
                "status": "idle",
                "message": "",
                "progress": 0,
                "data": None,
                "error": None,
                "thread": None
            }
        self._session_access_times[session_id] = time.time()

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
            self._session_access_times[session_id] = time.time()
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
            # Clear old data immediately to free memory
            state["data"] = None
            state["error"] = None
            gc.collect()
            
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
        has_slot = self._sim_semaphore.acquire(timeout=600)
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
            self.update_progress(session_id, 25, "Running heavy spatial models...")
            
            data = get_scenario(
                local_admin_unit_id=lau,
                radius=radius,
                transport_modes_params=params
            )
            
            self.update_progress(session_id, 90, "Finalizing results...")
            
            with self._lock:
                if session_id in self.sessions: # Verify session still exists
                    state = self.sessions[session_id]
                    state["data"] = data
                    state["status"] = "ready"
                    state["progress"] = 100
                    state["message"] = "Simulation complete!"
            print("[MANAGER] Simulation COMPLETE")
            gc.collect()
                
        except Exception as e:
            with self._lock:
                if session_id in self.sessions:
                    state = self.sessions[session_id]
                    state["status"] = "error"
                    state["error"] = e
                    state["message"] = f"Error: {str(e)}"
                traceback.print_exc()
        finally:
            self._sim_semaphore.release()
            gc.collect()

    def update_progress(self, session_id, val, msg):
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id]["progress"] = val
                self.sessions[session_id]["message"] = msg

manager = ScenarioManager()
