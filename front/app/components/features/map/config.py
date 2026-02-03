from dataclasses import dataclass

# ---------- CONSTANTES ----------
CARTO_POSITRON_GL = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
FALLBACK_CENTER = (2.2, 46.2)  # France center (approx)

HEADER_OFFSET_PX = 80
SIDEBAR_WIDTH = 340

# ---------- OPTIONS ----------
@dataclass(frozen=True)
class DeckOptions:
    zoom: float = 5
    pitch: float = 0
    bearing: float = 0
    map_style: str = CARTO_POSITRON_GL
