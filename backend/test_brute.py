import json
import urllib.request

base = "http://localhost:8000/api/v1"

r = urllib.request.urlopen(f"{base}/auth/captcha/challenge")
challenge = json.loads(r.read())

captcha_id = challenge["captcha_id"]
puzzle_size = challenge["puzzle_size"]
width = challenge["width"]
puzzle_y = challenge["puzzle_y"]

print(f"Challenge: {width}x{challenge['height']}, puzzle_size={puzzle_size}, puzzle_y={puzzle_y}")

track_max_x = width - 44

for pct in [0.3, 0.5, 0.7]:
    r2 = urllib.request.urlopen(f"{base}/auth/captcha/challenge")
    ch2 = json.loads(r2.read())
    cid2 = ch2["captcha_id"]
    py2 = ch2["puzzle_y"]
    ps2 = ch2["puzzle_size"]
    w2 = ch2["width"]

    slider = track_max_x * pct
    move_x = (slider / track_max_x) * (w2 - ps2)
    px = round(move_x + ps2 / 2)

    vd = json.dumps({"captcha_id": cid2, "slider_x": px, "slider_y": py2}).encode()
    req = urllib.request.Request(f"{base}/auth/captcha/verify", data=vd, headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req)
        result = json.loads(r.read())
        print(f"  slider={slider:.0f}px ({pct*100:.0f}%) -> puzzle_x={px}: {result.get('success', False)}")
    except urllib.error.HTTPError as e:
        print(f"  Error: {e.code}")

print("\n--- Brute force: try all positions ---")
r3 = urllib.request.urlopen(f"{base}/auth/captcha/challenge")
ch3 = json.loads(r3.read())
cid3 = ch3["captcha_id"]
py3 = ch3["puzzle_y"]

for test_x in range(50, 300, 10):
    r4 = urllib.request.urlopen(f"{base}/auth/captcha/challenge")
    ch4 = json.loads(r4.read())
    cid4 = ch4["captcha_id"]
    py4 = ch4["puzzle_y"]

    vd = json.dumps({"captcha_id": cid4, "slider_x": test_x, "slider_y": py4}).encode()
    req = urllib.request.Request(f"{base}/auth/captcha/verify", data=vd, headers={"Content-Type": "application/json"})
    try:
        r = urllib.request.urlopen(req)
        result = json.loads(r.read())
        if result.get("success"):
            print(f"  SUCCESS at puzzle_x={test_x}!")
            break
    except urllib.error.HTTPError:
        pass
else:
    print("  No success found in range 50-290")
