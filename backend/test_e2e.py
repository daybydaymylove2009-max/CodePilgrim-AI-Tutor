import json
import urllib.request

base = "http://localhost:8000/api/v1"

r = urllib.request.urlopen(f"{base}/auth/captcha/challenge")
challenge = json.loads(r.read())

captcha_id = challenge["captcha_id"]
puzzle_size = challenge["puzzle_size"]
width = challenge["width"]
puzzle_y = challenge["puzzle_y"]
bg_len = len(challenge["background_image"])
pz_len = len(challenge["puzzle_image"])

print(f"Challenge loaded: {width}x{challenge['height']}, puzzle_size={puzzle_size}")
print(f"bg_len={bg_len}, pz_len={pz_len}")
print(f"puzzle_y={puzzle_y}")

track_max_x = width - 44
target_slider = track_max_x * 0.5
move_x = (target_slider / track_max_x) * (width - puzzle_size)
puzzle_x = round(move_x + puzzle_size / 2)

print(f"\nSimulating slider at {target_slider:.0f}px -> puzzle_x={puzzle_x}")

verify_data = json.dumps({
    "captcha_id": captcha_id,
    "slider_x": puzzle_x,
    "slider_y": puzzle_y,
}).encode()

req = urllib.request.Request(
    f"{base}/auth/captcha/verify",
    data=verify_data,
    headers={"Content-Type": "application/json"},
)
try:
    r = urllib.request.urlopen(req)
    result = json.loads(r.read())
    print(f"Verify result: {result}")
except urllib.error.HTTPError as e:
    print(f"Verify error: {e.code} {e.read().decode()}")

print("\n--- Testing with stored exact coordinates ---")
import asyncio
from app.core.cache import redis_service

async def test_exact():
    r = urllib.request.urlopen(f"{base}/auth/captcha/challenge")
    ch = json.loads(r.read())
    cid = ch["captcha_id"]

    await redis_service._ensure_client()
    stored = await redis_service.get(f"captcha:{cid}")
    if stored:
        ex = stored["puzzle_x"]
        ey = stored["puzzle_y"]
        print(f"Stored: puzzle_x={ex}, puzzle_y={ey}")

        vd = json.dumps({"captcha_id": cid, "slider_x": ex, "slider_y": ey}).encode()
        req = urllib.request.Request(f"{base}/auth/captcha/verify", data=vd, headers={"Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req)
            result = json.loads(r.read())
            print(f"Exact match verify: {result}")
        except urllib.error.HTTPError as e:
            print(f"Error: {e.code} {e.read().decode()}")
    else:
        print("No stored data found")

asyncio.run(test_exact())
