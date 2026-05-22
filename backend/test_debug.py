import json
import urllib.request

BASE = "http://localhost:8000/api/v1"

def test_with_debug():
    r = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
    ch = json.loads(r.read())
    cid = ch["captcha_id"]
    py = ch["puzzle_y"]
    ps = ch["puzzle_size"]
    w = ch["width"]

    r2 = urllib.request.urlopen(f"{BASE}/auth/captcha/debug/{cid}")
    answer = json.loads(r2.read())
    expected_x = answer["puzzle_x"]
    expected_y = answer["puzzle_y"]

    print(f"Challenge: width={w}, puzzle_size={ps}, puzzle_y={py}")
    print(f"Answer: puzzle_x={expected_x}, puzzle_y={expected_y}")

    pm = ps // 2 + 22
    tmx = w - 44

    print(f"\nFrontend constants: pieceMargin={pm}, trackMaxX={tmx}")

    move_x = expected_x - ps / 2
    slider_x = (move_x / (w - ps)) * tmx

    move_x_r = (slider_x / tmx) * (w - ps)
    puzzle_x_calc = round(move_x_r + ps / 2)

    print(f"\nFormula: moveX = {move_x:.2f}, sliderX = {slider_x:.2f}")
    print(f"Recalc: moveX = {move_x_r:.2f}, puzzleX = {puzzle_x_calc}")
    print(f"Expected: {expected_x}, Diff: {puzzle_x_calc - expected_x}")

    vd = json.dumps({"captcha_id": cid, "slider_x": puzzle_x_calc, "slider_y": py}).encode()
    req = urllib.request.Request(f"{BASE}/auth/captcha/verify", data=vd, headers={"Content-Type": "application/json"})
    try:
        r3 = urllib.request.urlopen(req)
        res = json.loads(r3.read())
        print(f"\nVerify with formula result: {res}")
    except urllib.error.HTTPError as e:
        print(f"\nVerify error: {e.code} {e.read().decode()}")

    print(f"\n--- Test 10 challenges ---")
    ok = 0
    for i in range(10):
        r4 = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
        ch4 = json.loads(r4.read())
        cid4 = ch4["captcha_id"]
        py4 = ch4["puzzle_y"]
        ps4 = ch4["puzzle_size"]
        w4 = ch4["width"]

        r5 = urllib.request.urlopen(f"{BASE}/auth/captcha/debug/{cid4}")
        ans4 = json.loads(r5.read())
        ex4 = ans4["puzzle_x"]

        tmx4 = w4 - 44
        mx4 = ex4 - ps4 / 2
        sx4 = (mx4 / (w4 - ps4)) * tmx4
        mx4r = (sx4 / tmx4) * (w4 - ps4)
        px4 = round(mx4r + ps4 / 2)

        vd4 = json.dumps({"captcha_id": cid4, "slider_x": px4, "slider_y": py4}).encode()
        req4 = urllib.request.Request(f"{BASE}/auth/captcha/verify", data=vd4, headers={"Content-Type": "application/json"})
        try:
            r6 = urllib.request.urlopen(req4)
            res4 = json.loads(r6.read())
            s = res4.get("success", False)
            if s:
                ok += 1
            print(f"  #{i+1}: expected={ex4}, sent={px4}, diff={px4-ex4} {'OK' if s else 'FAIL'}")
        except urllib.error.HTTPError as e:
            print(f"  #{i+1}: HTTP error {e.code}")

    print(f"\n=== Result: {ok}/10 passed ===")

test_with_debug()
