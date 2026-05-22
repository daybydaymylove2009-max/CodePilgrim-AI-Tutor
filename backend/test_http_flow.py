import json
import urllib.request

BASE = "http://localhost:8000/api/v1"

def test_captcha_http():
    print("=== Step 1: Get captcha challenge via HTTP ===")
    r = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
    ch = json.loads(r.read())
    captcha_id = ch["captcha_id"]
    puzzle_y = ch["puzzle_y"]
    puzzle_size = ch["puzzle_size"]
    width = ch["width"]
    height = ch["height"]
    print(f"  captcha_id: {captcha_id[:8]}...")
    print(f"  size: {width}x{height}, puzzle_size={puzzle_size}")
    print(f"  puzzle_y: {puzzle_y}")

    print("\n=== Step 2: Brute force find correct puzzle_x ===")
    print("  Trying all X positions with tolerance check...")
    
    for test_x in range(50, 300, 2):
        r2 = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
        ch2 = json.loads(r2.read())
        cid2 = ch2["captcha_id"]
        py2 = ch2["puzzle_y"]

        vd = json.dumps({"captcha_id": cid2, "slider_x": test_x, "slider_y": py2}).encode()
        req = urllib.request.Request(f"{BASE}/auth/captcha/verify", data=vd, headers={"Content-Type": "application/json"})
        try:
            r3 = urllib.request.urlopen(req)
            res = json.loads(r3.read())
            if res.get("success"):
                print(f"  ✅ SUCCESS at slider_x={test_x}, puzzle_y={py2}")
                
                r4 = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
                ch3 = json.loads(r4.read())
                cid3 = ch3["captcha_id"]
                py3 = ch3["puzzle_y"]
                
                piece_margin = puzzle_size // 2 + 22
                track_max_x = width - 44
                
                move_x = test_x - puzzle_size / 2
                slider_pos = (move_x / (width - puzzle_size)) * track_max_x
                
                move_x_back = (slider_pos / track_max_x) * (width - puzzle_size)
                puzzle_x_back = round(move_x_back + puzzle_size / 2)
                
                print(f"\n  === Reverse engineering the mapping ===")
                print(f"  Correct puzzle_x: {test_x}")
                print(f"  moveX = puzzle_x - puzzle_size/2 = {test_x} - {puzzle_size/2} = {move_x}")
                print(f"  slider_pos = (moveX / (width - puzzle_size)) * trackMaxX = ({move_x:.1f} / {width - puzzle_size}) * {track_max_x} = {slider_pos:.1f}")
                print(f"  Frontend recalc: moveX = (slider / trackMaxX) * (width - puzzle_size) = {move_x_back:.1f}")
                print(f"  Frontend recalc: puzzleX = moveX + puzzle_size/2 = {move_x_back:.1f} + {puzzle_size/2} = {puzzle_x_back}")
                print(f"  Match: {puzzle_x_back == test_x}")
                break
        except urllib.error.HTTPError:
            pass
    else:
        print("  ❌ No success found in range 50-298")

    print("\n=== Step 3: Test exact coordinate mapping ===")
    successes = 0
    failures = 0
    for trial in range(10):
        r5 = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
        ch5 = json.loads(r5.read())
        cid5 = ch5["captcha_id"]
        py5 = ch5["puzzle_y"]
        ps5 = ch5["puzzle_size"]
        w5 = ch5["width"]

        found = False
        for test_x in range(50, w5 - 30, 2):
            r6 = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
            ch6 = json.loads(r6.read())
            cid6 = ch6["captcha_id"]
            py6 = ch6["puzzle_y"]

            vd = json.dumps({"captcha_id": cid6, "slider_x": test_x, "slider_y": py6}).encode()
            req = urllib.request.Request(f"{BASE}/auth/captcha/verify", data=vd, headers={"Content-Type": "application/json"})
            try:
                r7 = urllib.request.urlopen(req)
                res = json.loads(r7.read())
                if res.get("success"):
                    move_x = test_x - ps5 / 2
                    track_max = w5 - 44
                    slider = (move_x / (w5 - ps5)) * track_max
                    
                    move_x_r = (slider / track_max) * (w5 - ps5)
                    px_r = round(move_x_r + ps5 / 2)
                    
                    if px_r == test_x:
                        successes += 1
                        print(f"  Trial {trial+1}: ✅ puzzle_x={test_x}, mapped back={px_r}")
                    else:
                        failures += 1
                        print(f"  Trial {trial+1}: ❌ puzzle_x={test_x}, mapped back={px_r}, diff={px_r-test_x}")
                    found = True
                    break
            except:
                pass
            if found:
                break
        if not found:
            print(f"  Trial {trial+1}: ❌ Could not find correct position")
            failures += 1

    print(f"\n=== Results: {successes} successes, {failures} failures ===")

test_captcha_http()
