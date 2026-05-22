import json
import urllib.request
import math

BASE = "http://localhost:8000/api/v1"

def test_captcha():
    print("=== Step 1: Get captcha challenge ===")
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

    print("\n=== Step 2: Get stored answer from Redis ===")
    import asyncio
    from app.core.cache import redis_service
    async def get_stored():
        await redis_service._ensure_client()
        return await redis_service.get(f"captcha:{captcha_id}")
    stored = asyncio.run(get_stored())
    if not stored:
        print("  ERROR: No stored data found!")
        return
    expected_x = stored["puzzle_x"]
    expected_y = stored["puzzle_y"]
    print(f"  Expected puzzle_x: {expected_x}")
    print(f"  Expected puzzle_y: {expected_y}")

    print("\n=== Step 3: Simulate frontend coordinate mapping ===")
    piece_margin = puzzle_size // 2 + 22
    print(f"  pieceMargin (backend): {piece_margin}")
    print(f"  puzzle_size // 2: {puzzle_size // 2}")

    track_max_x = width - 44
    print(f"  trackMaxX (slider track width - button): {track_max_x}")

    move_x = expected_x - puzzle_size / 2
    print(f"  moveX (puzzle left edge in bg coords): {move_x}")

    slider_pos = (move_x / (width - puzzle_size)) * track_max_x
    print(f"  Simulated slider position: {slider_pos:.1f}px")

    css_left = move_x - piece_margin
    css_top = expected_y - puzzle_size // 2 - piece_margin
    print(f"  CSS left: {css_left:.1f}")
    print(f"  CSS top: {css_top:.1f}")

    img_center_x = css_left + piece_margin
    img_center_y = css_top + piece_margin
    print(f"  Image center in bg: ({img_center_x:.1f}, {img_center_y:.1f})")
    print(f"  Expected center:    ({expected_x}, {expected_y})")

    print("\n=== Step 4: Frontend calculates puzzleX ===")
    move_x_calc = (slider_pos / track_max_x) * (width - puzzle_size)
    puzzle_x_calc = round(move_x_calc + puzzle_size / 2)
    print(f"  moveX (from slider): {move_x_calc:.1f}")
    print(f"  puzzleX = moveX + puzzle_size/2 = {move_x_calc:.1f} + {puzzle_size/2} = {puzzle_x_calc}")
    print(f"  Expected puzzle_x: {expected_x}")
    print(f"  Difference: {puzzle_x_calc - expected_x}")

    print("\n=== Step 5: Send verification ===")
    verify_data = json.dumps({
        "captcha_id": captcha_id,
        "slider_x": puzzle_x_calc,
        "slider_y": puzzle_y,
    }).encode()
    req = urllib.request.Request(
        f"{BASE}/auth/captcha/verify",
        data=verify_data,
        headers={"Content-Type": "application/json"},
    )
    try:
        r = urllib.request.urlopen(req)
        result = json.loads(r.read())
        print(f"  Result: {result}")
        if result.get("success"):
            print("\n  ✅ VERIFICATION PASSED!")
        else:
            print(f"\n  ❌ VERIFICATION FAILED: {result.get('message')}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  ❌ HTTP Error {e.code}: {body}")

    print("\n=== Step 6: Test with slight offsets ===")
    for offset in [-8, -5, -3, 0, 3, 5, 8]:
        r2 = urllib.request.urlopen(f"{BASE}/auth/captcha/challenge")
        ch2 = json.loads(r2.read())
        cid2 = ch2["captcha_id"]
        py2 = ch2["puzzle_y"]

        stored2 = asyncio.run(get_stored_for(cid2))
        if not stored2:
            continue
        ex2 = stored2["puzzle_x"]

        test_x = ex2 + offset
        vd = json.dumps({"captcha_id": cid2, "slider_x": test_x, "slider_y": py2}).encode()
        req2 = urllib.request.Request(f"{BASE}/auth/captcha/verify", data=vd, headers={"Content-Type": "application/json"})
        try:
            r3 = urllib.request.urlopen(req2)
            res = json.loads(r3.read())
            status = "✅" if res.get("success") else "❌"
            print(f"  offset={offset:+d}: {status}")
        except urllib.error.HTTPError:
            print(f"  offset={offset:+d}: ❌ HTTP error")

async def get_stored_for(cid):
    from app.core.cache import redis_service
    await redis_service._ensure_client()
    return await redis_service.get(f"captcha:{cid}")

test_captcha()
