import asyncio
import json

from app.services.captcha_generator import CaptchaGenerator
from app.services.security import CaptchaService
from app.core.cache import redis_service


async def test_frontend_mapping():
    gen = CaptchaGenerator()
    svc = CaptchaService(generator=gen)

    challenge = await svc.create_challenge()
    captcha_id = challenge["captcha_id"]
    puzzle_size = challenge["puzzle_size"]
    width = challenge["width"]
    puzzle_y = challenge["puzzle_y"]

    stored = await redis_service.get(f"captcha:{captcha_id}")
    expected_x = stored["puzzle_x"]
    expected_y = stored["puzzle_y"]

    print(f"Expected puzzle_x={expected_x}, puzzle_y={expected_y}")
    print(f"puzzle_size={puzzle_size}, width={width}")

    track_max_x = 260 - 44

    target_slider_x = ((expected_x - puzzle_size / 2) / (width - puzzle_size)) * track_max_x
    print(f"\nTo hit target, slider should be at: {target_slider_x:.1f}")

    for slider_pos in [target_slider_x - 5, target_slider_x, target_slider_x + 5]:
        move_x = (slider_pos / track_max_x) * (width - puzzle_size)
        puzzle_x = round(move_x + puzzle_size / 2)
        diff = puzzle_x - expected_x
        print(f"  slider={slider_pos:.1f} -> move_x={move_x:.1f} -> puzzle_x={puzzle_x} (diff={diff:+d})")

    print(f"\n--- Simulating exact correct drag ---")
    move_x = (target_slider_x / track_max_x) * (width - puzzle_size)
    puzzle_x = round(move_x + puzzle_size / 2)
    result = await svc.verify_captcha(captcha_id, puzzle_x, puzzle_y)
    print(f"Result: {result}")

    if not result.get("success"):
        print("STILL FAILING! Let me check the mapping more carefully...")

        challenge = await svc.create_challenge()
        captcha_id = challenge["captcha_id"]
        stored = await redis_service.get(f"captcha:{captcha_id}")
        expected_x = stored["puzzle_x"]
        expected_y = stored["puzzle_y"]

        result = await svc.verify_captcha(captcha_id, expected_x, expected_y)
        print(f"Direct exact match test: {result}")


asyncio.run(test_frontend_mapping())
