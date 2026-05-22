import urllib.request

for url in ["http://localhost:5173", "http://127.0.0.1:5173", "http://[::1]:5173"]:
    try:
        r = urllib.request.urlopen(url, timeout=3)
        print(f"{url} -> OK (status={r.status})")
    except Exception as e:
        print(f"{url} -> FAILED: {type(e).__name__}: {e}")
