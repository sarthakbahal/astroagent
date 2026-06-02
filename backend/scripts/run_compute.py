import os, sys
root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root not in sys.path:
    sys.path.insert(0, root)

from backend.services.ephemeris import compute_natal_chart

res = compute_natal_chart(
    date_str="1986-03-28",
    time_str="21:53",
    lat=40.7128,
    lng=-74.0060,
    timezone="America/New_York",
)
import json
print(json.dumps(res, indent=2))
