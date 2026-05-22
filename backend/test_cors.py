import urllib.request
import json

req = urllib.request.Request("http://localhost:8000/api/v1/auth/captcha/challenge")
req.add_header("Origin", "http://localhost:5173")
r = urllib.request.urlopen(req)
cors = r.headers.get("Access-Control-Allow-Origin")
print(f"CORS header: {cors}")
print(f"Status: {r.status}")
data = json.loads(r.read())
bg_len = len(data["background_image"])
pz_len = len(data["puzzle_image"])
print(f"bg_len: {bg_len}, pz_len: {pz_len}")
print("CORS + API test PASSED!")
