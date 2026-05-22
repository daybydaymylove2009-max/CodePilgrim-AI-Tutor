import urllib.request
import json

try:
    r = urllib.request.urlopen("http://localhost:8000/api/v1/auth/captcha/challenge")
    data = json.loads(r.read().decode())
    cid = data["captcha_id"][:8]
    bg_len = len(data["background_image"])
    pz_len = len(data["puzzle_image"])
    w = data["width"]
    h = data["height"]
    print(f"captcha_id: {cid}...")
    print(f"bg_len: {bg_len}")
    print(f"pz_len: {pz_len}")
    print(f"size: {w}x{h}")
    print("API test PASSED!")
except Exception as e:
    print(f"API test FAILED: {type(e).__name__}: {e}")
