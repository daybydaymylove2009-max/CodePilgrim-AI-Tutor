import asyncio
from app.services.captcha_generator import CaptchaGenerator
from app.services.security import CaptchaService

async def test():
    svc = CaptchaService()
    try:
        result = await svc.create_challenge()
        cid = result["captcha_id"][:8]
        bg_len = len(result["background_image"])
        pz_len = len(result["puzzle_image"])
        w = result["width"]
        h = result["height"]
        print(f"captcha_id: {cid}...")
        print(f"bg_len: {bg_len}")
        print(f"pz_len: {pz_len}")
        print(f"size: {w}x{h}")
        print("CaptchaService OK!")
    except Exception as e:
        print(f"FAILED: {type(e).__name__}: {e}")

asyncio.run(test())
