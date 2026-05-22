import asyncio
import json
import math

from app.services.captcha_generator import CaptchaGenerator
from app.services.security import CaptchaService


async def test_e2e():
    gen = CaptchaGenerator()
    svc = CaptchaService(generator=gen)

    challenge = await svc.create_challenge()
    captcha_id = challenge["captcha_id"]
    puzzle_x = gen._last_puzzle_x if hasattr(gen, "_last_puzzle_x") else None

    print(f"captcha_id: {captcha_id[:8]}...")
    print(f"puzzle_y: {challenge['puzzle_y']}")
    print(f"width: {challenge['width']}, height: {challenge['height']}")
    print(f"puzzle_size: {challenge['puzzle_size']}")

    puzzle_size = challenge["puzzle_size"]
    width = challenge["width"]

    track_max_x = 260 - 44
    slider_x = track_max_x * 0.7
    move_x = (slider_x / track_max_x) * (width - puzzle_size)
    calculated_puzzle_x = round(move_x + puzzle_size / 2)

    print(f"\nSimulated drag: slider_x={slider_x:.1f}")
    print(f"move_x={move_x:.1f}, calculated puzzle_x={calculated_puzzle_x}")

    result = await svc.verify_captcha(captcha_id, calculated_puzzle_x, challenge["puzzle_y"])
    print(f"\nVerification result: {result}")

    challenge2 = await svc.create_challenge()
    captcha_id2 = challenge2["captcha_id"]

    stored = await svc._get_stored_data(captcha_id2) if hasattr(svc, "_get_stored_data") else None

    print(f"\n--- Direct coordinate test ---")
    challenge3 = await svc.create_challenge()
    captcha_id3 = challenge3["captcha_id"]

    for offset in [0, 3, 5, 8, 10]:
        test_x = challenge3["puzzle_y"]
        result = await svc.verify_captcha(captcha_id3, challenge3["puzzle_y"] + offset, challenge3["puzzle_y"])
        print(f"  offset={offset}: {result.get('success', False)} - {result.get('message', '')}")

        if not result.get("success"):
            challenge3 = await svc.create_challenge()
            captcha_id3 = challenge3["captcha_id"]


async def test_exact_match():
    gen = CaptchaGenerator()
    svc = CaptchaService(generator=gen)

    challenge = await svc.create_challenge()
    captcha_id = challenge["captcha_id"]

    stored_data = None
    from app.core.cache import redis_service
    stored_data = await redis_service.get(f"captcha:{captcha_id}")

    if stored_data:
        expected_x = stored_data.get("puzzle_x", 0)
        expected_y = stored_data.get("puzzle_y", 0)
        print(f"Stored puzzle_x={expected_x}, puzzle_y={expected_y}")

        result = await svc.verify_captcha(captcha_id, expected_x, expected_y)
        print(f"Exact match: {result}")

        challenge = await svc.create_challenge()
        captcha_id = challenge["captcha_id"]
        stored_data = await redis_service.get(f"captcha:{captcha_id}")
        expected_x = stored_data.get("puzzle_x", 0)
        expected_y = stored_data.get("puzzle_y", 0)

        for offset in [-10, -8, -5, -3, 0, 3, 5, 8, 10]:
            ch = await svc.create_challenge()
            cid = ch["captcha_id"]
            sd = await redis_service.get(f"captcha:{cid}")
            ex = sd.get("puzzle_x", 0)
            ey = sd.get("puzzle_y", 0)
            r = await svc.verify_captcha(cid, ex + offset, ey)
            print(f"  offset={offset:+d}: success={r.get('success', False)}")
    else:
        print("Could not retrieve stored data")


asyncio.run(test_exact_match())
