import json
import urllib.request

BASE = "http://localhost:8000/api/v1"

def simulate_frontend():
    print("=" * 60)
    print("SIMULATING FRONTEND CAPTCHA FLOW")
    print("=" * 60)

    r = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
    ch = json.loads(r.read())

    captcha_id = ch["captcha_id"]
    puzzle_y = ch["puzzle_y"]
    puzzle_size = ch["puzzle_size"]
    width = ch["width"]
    height = ch["height"]
    bg_len = len(ch["background_image"])
    pz_len = len(ch["puzzle_image"])

    print(f"\n--- Challenge received ---")
    print(f"  captcha_id: {captcha_id[:12]}...")
    print(f"  bg: {bg_len} chars, pz: {pz_len} chars")
    print(f"  width={width}, height={height}")
    print(f"  puzzle_size={puzzle_size}")
    print(f"  puzzle_y={puzzle_y}")

    piece_margin = puzzle_size // 2 + 22
    print(f"\n--- Frontend constants ---")
    print(f"  pieceMargin = puzzle_size//2 + 22 = {puzzle_size}//2 + 22 = {piece_margin}")

    track_max_x = width - 44
    print(f"  trackMaxX = width - 44 = {width} - 44 = {track_max_x}")
    print(f"  (assuming track width == bg width = {width})")

    print(f"\n--- Brute force: find the correct puzzle_x ---")
    found_x = None
    for test_x in range(40, width - 30, 1):
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
                found_x = test_x
                print(f"  Found correct puzzle_x = {test_x} (puzzle_y = {py2})")
                break
        except:
            pass

    if found_x is None:
        print("  ERROR: Could not find correct position!")
        return

    print(f"\n--- Simulate user dragging slider to correct position ---")
    print(f"  Correct puzzle_x = {found_x}")

    move_x = found_x - puzzle_size / 2
    print(f"  moveX = puzzle_x - puzzle_size/2 = {found_x} - {puzzle_size/2} = {move_x}")

    slider_x = (move_x / (width - puzzle_size)) * track_max_x
    print(f"  sliderX = (moveX / (width - puzzle_size)) * trackMaxX")
    print(f"          = ({move_x} / {width - puzzle_size}) * {track_max_x}")
    print(f"          = {slider_x:.4f}")

    css_left = move_x - piece_margin
    css_top = found_x - puzzle_size // 2 - piece_margin
    print(f"\n  CSS left = moveX - pieceMargin = {move_x} - {piece_margin} = {css_left}")
    print(f"  CSS top  = puzzle_y - puzzle_size//2 - pieceMargin = {puzzle_y} - {puzzle_size//2} - {piece_margin} = {puzzle_y - puzzle_size//2 - piece_margin}")

    img_center_x = css_left + piece_margin
    print(f"  Image center X in bg = left + pieceMargin = {css_left} + {piece_margin} = {img_center_x}")
    print(f"  Expected center X    = puzzle_x = {found_x}")
    print(f"  Match: {abs(img_center_x - found_x) < 1}")

    print(f"\n--- Frontend calculates puzzleX from sliderX ---")
    move_x_recalc = (slider_x / track_max_x) * (width - puzzle_size)
    puzzle_x_recalc = round(move_x_recalc + puzzle_size / 2)
    print(f"  moveX = (sliderX / trackMaxX) * (width - puzzle_size)")
    print(f"       = ({slider_x:.4f} / {track_max_x}) * {width - puzzle_size}")
    print(f"       = {move_x_recalc:.4f}")
    print(f"  puzzleX = round(moveX + puzzle_size/2)")
    print(f"         = round({move_x_recalc:.4f} + {puzzle_size/2})")
    print(f"         = {puzzle_x_recalc}")
    print(f"  Expected puzzle_x = {found_x}")
    print(f"  Difference = {puzzle_x_recalc - found_x}")

    print(f"\n--- Now test with a NEW challenge, simulating exact frontend flow ---")
    r4 = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
    ch4 = json.loads(r4.read())
    cid4 = ch4["captcha_id"]
    py4 = ch4["puzzle_y"]
    ps4 = ch4["puzzle_size"]
    w4 = ch4["width"]

    tmx4 = w4 - 44
    pm4 = ps4 // 2 + 22

    found4 = None
    for tx in range(40, w4 - 30, 1):
        r5 = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
        ch5 = json.loads(r5.read())
        cid5 = ch5["captcha_id"]
        py5 = ch5["puzzle_y"]

        vd = json.dumps({"captcha_id": cid5, "slider_x": tx, "slider_y": py5}).encode()
        req = urllib.request.Request(f"{BASE}/auth/captcha/verify", data=vd, headers={"Content-Type": "application/json"})
        try:
            r6 = urllib.request.urlopen(req)
            res = json.loads(r6.read())
            if res.get("success"):
                found4 = tx
                break
        except:
            pass

    if found4 is None:
        print("  Could not find answer for test 2")
        return

    mx4 = found4 - ps4 / 2
    sx4 = (mx4 / (w4 - ps4)) * tmx4
    mx4r = (sx4 / tmx4) * (w4 - ps4)
    px4r = round(mx4r + ps4 / 2)

    print(f"  Correct puzzle_x = {found4}")
    print(f"  Frontend would send puzzleX = {px4r}")
    print(f"  Difference = {px4r - found4}")

    if px4r == found4:
        print(f"\n  ✅ Formula is CORRECT for this case!")
    else:
        print(f"\n  ❌ Formula has {px4r - found4}px offset!")

    print(f"\n--- Test 5 more challenges ---")
    correct = 0
    for i in range(5):
        r7 = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
        ch7 = json.loads(r7.read())
        cid7 = ch7["captcha_id"]
        py7 = ch7["puzzle_y"]
        ps7 = ch7["puzzle_size"]
        w7 = ch7["width"]
        tmx7 = w7 - 44

        found7 = None
        for tx in range(40, w7 - 30, 1):
            r8 = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
            ch8 = json.loads(r8.read())
            cid8 = ch8["captcha_id"]
            py8 = ch8["puzzle_y"]

            vd = json.dumps({"captcha_id": cid8, "slider_x": tx, "slider_y": py8}).encode()
            req = urllib.request.Request(f"{BASE}/auth/captcha/verify", data=vd, headers={"Content-Type": "application/json"})
            try:
                r9 = urllib.request.urlopen(req)
                res = json.loads(r9.read())
                if res.get("success"):
                    found7 = tx
                    break
            except:
                pass

        if found7 is not None:
            mx7 = found7 - ps7 / 2
            sx7 = (mx7 / (w7 - ps7)) * tmx7
            mx7r = (sx7 / tmx7) * (w7 - ps7)
            px7r = round(mx7r + ps7 / 2)
            match = px7r == found7
            if match:
                correct += 1
            print(f"  Test {i+1}: expected={found7}, frontend_sends={px7r}, diff={px7r-found7} {'✅' if match else '❌'}")
        else:
            print(f"  Test {i+1}: could not find answer")

    print(f"\n=== FINAL RESULT: {correct}/5 formula matches ===")

simulate_frontend()
