def default_tooltip() -> dict:
    return {
        "html": (
            "<div style='font-family:Arial, sans-serif;'>"
            "<b style='font-size:14px;'>Study Area</b><br>"
            "<b>INSEE Unit:</b> {INSEE Unit}<br/>"
            "<b>Zone ID:</b> {Zone ID}<br/><br/>"
            "<b style='font-size:13px;'>Average Mobility</b><br>"
            "Avg. travel time: <b>{Avg. Travel Time (min)}</b> min/day<br>"
            "Total distance traveled: <b>{Total Distance (km/day)}</b> km/day<br>"
            "Accessibility Level: <b>{Accessibility Level}</b><br/><br/>"
            "<b style='font-size:13px;'>Modal Split</b><br>"
            "Car share: <b>{Car Share (%)}</b><br>"
            "Cycling share: <b>{Cycling Share (%)}</b><br>"
            "Walking share: <b>{Walking Share (%)}</b><br>"
            "Public transport share: <b>{Public Transport Share (%)}</b>"
            "</div>"
        ),
        "style": {
            "backgroundColor": "rgba(255,255,255,0.9)",
            "color": "#111",
            "fontSize": "12px",
            "padding": "8px",
            "borderRadius": "6px",
        },
    }
