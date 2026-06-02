import httpx

payload = {
    "message": "Please compute my natal chart",
    "session_id": "test_session_1",
    "birth_details": {
        "date": "1986-03-28",
        "time": "21:53",
        "place": "New York, NY",
        "lat": 40.7128,
        "lng": -74.0060,
        "timezone": "America/New_York",
    },
}

with httpx.stream("POST", "http://127.0.0.1:8000/api/chat", json=payload, timeout=120.0) as r:
    print('STATUS', r.status_code)
    for line in r.iter_lines():
        if not line:
            continue
        print(line.decode('utf-8'))
