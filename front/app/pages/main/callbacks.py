"""
callbacks.py
============

Callbacks Dash pour l’application cartographique.

Ce module :
- synchronise les contrôles de rayon (slider ↔ number input) ;
- reconstruit les paramètres de modes de transport à partir de l’UI ;
- exécute le calcul de scénario et régénère la carte Deck.gl + résumé (via Manager asynchrone) ;
- applique des garde-fous UX.
"""

from dash import Input, Output, State, ALL, no_update, ctx
import uuid
import dash_mantine_components as dmc

from app.components.features.study_area_summary import StudyAreaSummary
from app.components.features.map.config import DeckOptions
from app.scenario.manager import manager  # Import the manager
# Note: get_scenario is called inside manager, not here directly anymore

# Utilise map_service si dispo
try:
    from app.services.map_service import get_map_deck_json_from_scn
    USE_MAP_SERVICE = True
except Exception:
    from app.components.features.map.deck_factory import make_deck_json
    USE_MAP_SERVICE = False

UI_TO_INTERNAL = {
    "Walking": "walk",
    "Cycling": "bicycle",
    "Car": "car",
    "Carpooling": "carpool",
    "Public Transport": "public_transport",
}


def _normalize_lau(code: str) -> str:
    s = (code or "").strip().lower()
    if s.startswith("fr-"):
        return s
    if s.isdigit() and len(s) == 5:
        return f"fr-{s}"
    return s or "fr-31555"


def _make_deck_json_from_scn(scn: dict) -> str:
    if USE_MAP_SERVICE:
        return get_map_deck_json_from_scn(scn, DeckOptions())
    return make_deck_json(scn, DeckOptions())


def register_callbacks(app, MAPP: str = "map"):
    """Enregistre l’ensemble des callbacks Dash de la page."""

    # -------------------- CALLBACKS --------------------

    # Unified callback for Launch and Polling
    @app.callback(
        Output(f"{MAPP}-deck-map", "data"),
        Output(f"{MAPP}-deck-map", "key"),
        Output(f"{MAPP}-summary-wrapper", "children"),
        Output(f"{MAPP}-deck-memo", "data"),
        
        # New Outputs for Modal and Interval
        Output("progress-modal", "opened"),
        Output("progress-message", "children"),
        Output("progress-bar", "value"),
        Output("interval-component", "disabled"),

        Input(f"{MAPP}-run-btn", "n_clicks"),
        Input("interval-component", "n_intervals"),
        
        State("session-id", "data"),
        State(f"{MAPP}-radius-slider", "value"), # ONLY Slider now
        State(f"{MAPP}-lau-input", "value"),
        State({"type": "mode-active", "index": ALL}, "checked"),
        State({"type": "mode-active", "index": ALL}, "id"),
        State({"type": "mode-var", "mode": ALL, "var": ALL}, "value"),
        State({"type": "mode-var", "mode": ALL, "var": ALL}, "id"),
        State({"type": "pt-submode", "index": ALL}, "checked"),
        State({"type": "pt-submode", "index": ALL}, "id"),
        State(f"{MAPP}-deck-memo", "data"),
        prevent_initial_call=True,
    )
    def _handle_simulation(
        n_clicks,
        n_intervals,
        sid,
        radius_idx, # Received as 0-4 index
        lau_val,
        active_values,
        active_ids,
        vars_values,
        vars_ids,
        pt_checked_vals,
        pt_checked_ids,
        deck_memo,
    ):
        trigger = ctx.triggered_id
        
        # 1. Start Simulation (Button Click or Initial Load)
        if trigger == f"{MAPP}-run-btn" or trigger is None:
            try:
                # Map 0-4 to real radius values or use absolute value
                radius_map = [15.0, 20.0, 30.0, 40.0, 50.0]
                try:
                    rv = float(radius_idx) if radius_idx is not None else 15.0
                    # If it's a small index (0-4), map it
                    if 0 <= rv < len(radius_map):
                        r = radius_map[int(rv)]
                    else:
                        # Otherwise use as absolute km
                        r = rv
                except:
                    r = 15.0
                
                if not lau_val:
                    # If no city selected, do nothing (keep empty/France view)
                    return (no_update, no_update, no_update, no_update, 
                            False, "", 0, False)
                
                lau_norm = _normalize_lau(lau_val)

                # Reconstruct params (UI -> Internal)
                params = {}
                for aid, val in zip(active_ids or [], active_values or []):
                    label = aid["index"]
                    key = UI_TO_INTERNAL.get(label)
                    if key:
                        params.setdefault(key, {})["active"] = bool(val)

                for vid, val in zip(vars_ids or [], vars_values or []):
                    key = UI_TO_INTERNAL.get(vid["mode"])
                    if not key: continue
                    p = params.setdefault(key, {"active": True})
                    vlabel = (vid["var"] or "").lower()
                    if "time" in vlabel: p["cost_of_time_eur_per_h"] = float(val or 0)
                    elif "distance" in vlabel: p["cost_of_distance_eur_per_km"] = float(val or 0)
                    elif "constant" in vlabel: p["cost_constant"] = float(val or 0)

                if pt_checked_ids and pt_checked_vals:
                    pt_map = {"walk_pt": "pt_walk", "car_pt": "pt_car", "bicycle_pt": "pt_bicycle"}
                    pt_cfg = params.setdefault("public_transport", {"active": True})
                    for pid, checked in zip(pt_checked_ids, pt_checked_vals):
                        alias = pt_map.get(pid["index"])
                        if alias: pt_cfg[alias] = bool(checked)

                # Start Background Thread with session ID
                manager.start_simulation(sid, lau_norm, r, params)
                
                # Open Modal, Enable Interval, Init Progress 5%
                return (no_update, no_update, no_update, no_update, 
                        True, "Initializing...", 5, False)

            except Exception as e:
                return (no_update, no_update, no_update, no_update, 
                        True, f"Error starting: {e}", 0, True)

        # 2. Poll Status (Interval)
        elif trigger == "interval-component":
            st = manager.get_status(sid)
            status_code = st["status"]
            msg = st["message"]
            prog = st["progress"]
            
            if status_code == "loading":
                return (no_update, no_update, no_update, no_update, 
                        True, msg, prog, False)
            
            elif status_code == "ready":
                # Success! Process data
                data = manager.get_data(sid)
                if data:
                    deck_json = _make_deck_json_from_scn(data)
                    summary = StudyAreaSummary(data["zones_gdf"], visible=True, id_prefix=MAPP)
                    
                    lau_norm = _normalize_lau(lau_val or "75101")
                    prev_key = (deck_memo or {}).get("key") or str(uuid.uuid4())
                    prev_lau = (deck_memo or {}).get("lau")
                    new_key = prev_key if prev_lau == lau_norm else str(uuid.uuid4())
                    new_memo = {"key": new_key, "lau": lau_norm}
                    
                    return (deck_json, new_key, summary, new_memo, 
                            False, "Done!", 100, True)
                else:
                    return (no_update, no_update, no_update, no_update, 
                            True, "Error: No data returned", 0, True)

            elif status_code == "error":
                return (no_update, no_update, no_update, no_update, 
                        True, f"Failed: {st.get('error')}", 0, True)
                # Keeping modal open with error message is good. User has to refresh?
                # Actually, adding a Close button to modal would be good, but for now just showing error.
            
        return no_update


    # Keep existing tooltips/ux callbacks
    @app.callback(
        Output({"type": "mode-active", "index": ALL}, "checked"),
        Output({"type": "mode-tip", "index": ALL}, "opened"),
        Input({"type": "mode-active", "index": ALL}, "checked"),
        State({"type": "mode-active", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def _enforce_one_mode(checked_list, ids):
        if not checked_list or not ids:
            return no_update, no_update
        n_checked = sum(bool(v) for v in checked_list)
        triggered = ctx.triggered_id
        if n_checked == 0 and triggered is not None:
            new_checked, new_opened = [], []
            for id_, val in zip(ids, checked_list):
                if id_ == triggered:
                    new_checked.append(True)
                    new_opened.append(True)
                else:
                    new_checked.append(bool(val))
                    new_opened.append(False)
            return new_checked, new_opened
        return [bool(v) for v in checked_list], [False] * len(ids)

    @app.callback(
        Output({"type": "pt-submode", "index": ALL}, "checked"),
        Output({"type": "pt-tip", "index": ALL}, "opened"),
        Input({"type": "pt-submode", "index": ALL}, "checked"),
        State({"type": "pt-submode", "index": ALL}, "id"),
        prevent_initial_call=True,
    )
    def _enforce_one_pt_submode(checked_list, ids):
        if not checked_list or not ids:
            return no_update, no_update
        n_checked = sum(bool(v) for v in checked_list)
        triggered = ctx.triggered_id
        if n_checked == 0 and triggered is not None:
            new_checked, new_opened = [], []
            for id_, val in zip(ids, checked_list):
                if id_ == triggered:
                    new_checked.append(True)
                    new_opened.append(True)
                else:
                    new_checked.append(bool(val))
                    new_opened.append(False)
            return new_checked, new_opened
        return [bool(v) for v in checked_list], [False] * len(ids)
