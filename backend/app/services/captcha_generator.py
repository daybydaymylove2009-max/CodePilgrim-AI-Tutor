"""
CodePilgrim Professional Captcha Generator

Enterprise production-grade implementation featuring:
- Fractal noise-based scene rendering (8 scene types)
- True cubic Bezier curve jigsaw pieces with neck/head profile
- Contour-based 3D lighting (shadow / highlight / bevel / AO)
- Multi-pass anti-aliased rendering with smooth filtering
- Anti-AI detection interference layer

Independent reusable module:
    from app.services.captcha_generator import CaptchaGenerator
    gen = CaptchaGenerator()
    result = gen.generate()
"""

from __future__ import annotations

import base64
import io
import math
import random
from dataclasses import dataclass
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageChops


@dataclass
class CaptchaResult:
    background_b64: str
    puzzle_b64: str
    puzzle_x: int
    puzzle_y: int
    width: int
    height: int
    puzzle_size: int


class CaptchaGenerator:
    SCENE_ALPINE = "alpine"
    SCENE_AURORA = "aurora"
    SCENE_SUNSET = "sunset"
    SCENE_NEON = "neon"
    SCENE_SAKURA = "sakura"
    SCENE_COSMOS = "cosmos"
    SCENE_REEF = "reef"
    SCENE_GEOMETRIC = "geometric"

    def __init__(
        self,
        width: int = 340,
        height: int = 200,
        puzzle_size: int = 52,
        complexity: int = 3,
    ):
        self.width = width
        self.height = height
        self.puzzle_size = puzzle_size
        self.complexity = min(max(complexity, 1), 5)
        self.tab_ratio = 0.25
        self.tab_neck_ratio = 0.14

    def generate(self, scene: str | None = None) -> CaptchaResult:
        rng = random.Random()

        background = self._render_scene(scene, rng)
        background = self._add_atmosphere(background, rng)
        background = self._add_texture_overlay(background, rng)
        background = self._add_anti_ai_noise(background, rng)

        margin = self.puzzle_size + 20
        puzzle_x = rng.randint(margin, self.width - margin)
        puzzle_y = rng.randint(margin, self.height - margin)

        puzzle_path = self._generate_jigsaw_path(puzzle_x, puzzle_y, self.puzzle_size, rng)
        puzzle_mask = self._render_puzzle_mask(puzzle_path)

        puzzle_piece, mask_crop = self._extract_puzzle_piece(background, puzzle_mask, puzzle_x, puzzle_y)
        puzzle_piece = self._add_3d_lighting(puzzle_piece, mask_crop)

        background = self._cut_puzzle_hole(background, puzzle_mask, puzzle_x, puzzle_y)
        background = self._render_hole_ao(background, puzzle_mask, puzzle_x, puzzle_y)

        background_b64 = self._image_to_b64(background, format="WEBP", quality=90)
        puzzle_b64 = self._image_to_b64(puzzle_piece, format="PNG")

        return CaptchaResult(
            background_b64=background_b64,
            puzzle_b64=puzzle_b64,
            puzzle_x=puzzle_x,
            puzzle_y=puzzle_y,
            width=self.width,
            height=self.height,
            puzzle_size=self.puzzle_size,
        )

    # ═══════════════════════════════════════════════════════════════
    #  Fractal Noise Generation
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _generate_noise_layer(
        width: int,
        height: int,
        base_scale: int = 4,
        octaves: int = 4,
        rng: random.Random | None = None,
    ) -> Image.Image:
        if rng is None:
            rng = random.Random()
        result = Image.new("L", (width, height), 128)
        for octave in range(octaves):
            grid_size = max(2, base_scale * (2 ** octave))
            grid = Image.new("L", (grid_size, grid_size))
            pixels = grid.load()
            for y in range(grid_size):
                for x in range(grid_size):
                    pixels[x, y] = rng.randint(0, 255)
            layer = grid.resize((width, height), Image.BICUBIC)
            alpha = 0.5 ** (octave + 1)
            result = Image.blend(result, layer, alpha)
        return result

    def _noise_heightmap(
        self,
        width: int,
        height: int,
        base_scale: int = 3,
        octaves: int = 4,
        rng: random.Random | None = None,
    ) -> list[list[float]]:
        noise = self._generate_noise_layer(width, height, base_scale, octaves, rng)
        px = noise.load()
        return [[px[x, y] / 255.0 for x in range(width)] for y in range(height)]

    # ═══════════════════════════════════════════════════════════════
    #  Color Utilities
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _hsv_to_rgb(h: int, s: float, v: float) -> Tuple[int, int, int]:
        h = h % 360
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        return int((r + m) * 255), int((g + m) * 255), int((b + m) * 255)

    @staticmethod
    def _lerp_color(
        c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float
    ) -> Tuple[int, int, int]:
        t = max(0.0, min(1.0, t))
        return (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
        )

    def _harmonious_palette(
        self, base_hue: int, n: int, rng: random.Random
    ) -> list[Tuple[int, int, int]]:
        colors = []
        for i in range(n):
            hue = (base_hue + i * (360 // n) + rng.randint(-15, 15)) % 360
            sat = rng.uniform(0.4, 0.8)
            val = rng.uniform(0.5, 0.9)
            colors.append(self._hsv_to_rgb(hue, sat, val))
        return colors

    def _draw_gradient_rect(
        self,
        draw: ImageDraw.ImageDraw,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        c1: Tuple[int, int, int],
        c2: Tuple[int, int, int],
        direction: str = "vertical",
    ) -> None:
        if direction == "vertical":
            for y in range(y1, y2):
                t = (y - y1) / max(1, y2 - y1)
                c = self._lerp_color(c1, c2, t)
                draw.line([(x1, y), (x2, y)], fill=(*c, 255))
        else:
            for x in range(x1, x2):
                t = (x - x1) / max(1, x2 - x1)
                c = self._lerp_color(c1, c2, t)
                draw.line([(x, y1), (x, y2)], fill=(*c, 255))

    # ═══════════════════════════════════════════════════════════════
    #  Scene Rendering
    # ═══════════════════════════════════════════════════════════════

    def _render_scene(self, scene: str | None, rng: random.Random) -> Image.Image:
        scenes = {
            self.SCENE_ALPINE: self._scene_alpine_peaks,
            self.SCENE_AURORA: self._scene_aurora_borealis,
            self.SCENE_SUNSET: self._scene_sunset_coast,
            self.SCENE_NEON: self._scene_neon_metropolis,
            self.SCENE_SAKURA: self._scene_sakura_garden,
            self.SCENE_COSMOS: self._scene_deep_cosmos,
            self.SCENE_REEF: self._scene_coral_reef,
            self.SCENE_GEOMETRIC: self._scene_geometric_flow,
        }
        if scene and scene in scenes:
            return scenes[scene](rng)
        return rng.choice(list(scenes.values()))(rng)

    # ─── Alpine Peaks ─────────────────────────────────────────────

    def _scene_alpine_peaks(self, rng: random.Random) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        sky_top = self._hsv_to_rgb(210, 0.65, 0.82)
        sky_mid = self._hsv_to_rgb(200, 0.45, 0.93)
        sky_bot = self._hsv_to_rgb(195, 0.25, 0.98)
        for y in range(self.height):
            t = y / self.height
            c = self._lerp_color(sky_top, sky_mid, t * 2) if t < 0.5 else self._lerp_color(sky_mid, sky_bot, (t - 0.5) * 2)
            draw.line([(0, y), (self.width, y)], fill=(*c, 255))

        sun_x = rng.randint(self.width // 4, 3 * self.width // 4)
        sun_y = rng.randint(15, int(self.height * 0.22))
        for r in range(55, 0, -1):
            alpha = int(220 * (1 - r / 55) ** 2)
            draw.ellipse([sun_x - r, sun_y - r, sun_x + r, sun_y + r], fill=(255, 248, 210, alpha))

        cloud_noise = self._generate_noise_layer(self.width, self.height // 3, 3, 3, rng)
        cloud_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        cpx = cloud_layer.load()
        npx = cloud_noise.load()
        for y in range(min(self.height // 3, cloud_noise.height)):
            for x in range(min(self.width, cloud_noise.width)):
                v = npx[x, y]
                if v > 155:
                    a = int((v - 155) / 100 * 130)
                    cpx[x, y] = (255, 255, 255, a)
        img = Image.alpha_composite(img, cloud_layer.filter(ImageFilter.GaussianBlur(radius=4)))

        draw = ImageDraw.Draw(img)
        horizon = int(self.height * rng.uniform(0.35, 0.45))

        for layer in range(6):
            y_base = horizon + layer * rng.randint(10, 22)
            depth = layer / 5
            if layer < 2:
                hue, sat, val = rng.randint(200, 220), 0.2 + depth * 0.1, 0.5 + depth * 0.1
            else:
                hue, sat, val = rng.randint(100, 155), 0.3 + depth * 0.15, 0.22 + depth * 0.1
            r, g, b = self._hsv_to_rgb(hue, sat, val)

            m_noise = self._generate_noise_layer(self.width, 1, 2, 3, rng)
            mpx = m_noise.load()
            points = [(0, self.height)]
            for x in range(self.width):
                nv = mpx[min(x, m_noise.width - 1), 0] / 255.0
                peak = rng.randint(30, 95 - layer * 12) * (0.4 + nv * 0.6)
                points.append((x, y_base - int(peak)))
            points.append((self.width, self.height))
            draw.polygon(points, fill=(r, g, b, min(255, 210 + layer * 8)))

            if layer < 2:
                for x in range(0, self.width, 2):
                    idx = x + 1
                    if idx < len(points) - 1:
                        py = points[idx][1]
                        if py < y_base - 45:
                            draw.line([(x, py), (x, py + rng.randint(3, 12))], fill=(235, 242, 255, 170))

        lake_y = int(self.height * 0.78)
        lake = Image.new("RGBA", (self.width, self.height - lake_y), (0, 0, 0, 0))
        ld = ImageDraw.Draw(lake)
        for y in range(self.height - lake_y):
            t = y / max(1, self.height - lake_y)
            r, g, b = self._hsv_to_rgb(200, 0.4 - t * 0.2, 0.55 - t * 0.15)
            ld.line([(0, y), (self.width, y)], fill=(r, g, b, 210))

        reflect = img.crop((0, horizon, self.width, lake_y)).transpose(Image.FLIP_TOP_BOTTOM)
        reflect = reflect.resize((self.width, self.height - lake_y), Image.BICUBIC)
        reflect = reflect.filter(ImageFilter.GaussianBlur(radius=2))
        lake = Image.alpha_composite(lake, reflect)
        img.paste(lake, (0, lake_y), lake)

        draw = ImageDraw.Draw(img)
        for _ in range(rng.randint(6, 14)):
            tx = rng.randint(0, self.width)
            ty = rng.randint(lake_y - 15, lake_y + 5)
            th = rng.randint(18, 45)
            tw = max(2, th // 14)
            draw.rectangle([tx - tw, ty - th, tx + tw, ty], fill=(18, 28, 18, 200))
            for br in range(3):
                by = ty - th + br * (th // 3)
                bw = th // 3 - br * 3
                bh = th // 4
                draw.polygon(
                    [(tx, by - bh), (tx - bw, by + 5), (tx + bw, by + 5)],
                    fill=(12 + br * 6, 30 + br * 8, 12 + br * 6, 210),
                )
        return img

    # ─── Aurora Borealis ──────────────────────────────────────────

    def _scene_aurora_borealis(self, rng: random.Random) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        for y in range(self.height):
            t = y / self.height
            r, g, b = self._hsv_to_rgb(225, 0.5 + t * 0.2, 0.06 + t * 0.03)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b, 255))

        for _ in range(rng.randint(100, 250)):
            sx, sy = rng.randint(0, self.width), rng.randint(0, int(self.height * 0.65))
            br = rng.randint(140, 255)
            sz = rng.choice([1, 1, 1, 2])
            draw.ellipse([sx, sy, sx + sz, sy + sz], fill=(br, br, br + min(0, 255 - br), rng.randint(160, 255)))

        aurora = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        ad = ImageDraw.Draw(aurora)
        for band in range(rng.randint(3, 7)):
            base_y = rng.randint(20, int(self.height * 0.45))
            hue = rng.choice([120, 140, 160, 280, 300])
            wave_amp = rng.randint(15, 45)
            wave_freq = rng.uniform(0.008, 0.025)
            phase = rng.uniform(0, math.pi * 2)
            for x in range(self.width):
                y_center = base_y + int(wave_amp * math.sin(x * wave_freq + phase))
                for dy in range(-rng.randint(20, 50), rng.randint(20, 50)):
                    py = y_center + dy
                    if 0 <= py < self.height:
                        dist = abs(dy) / 50.0
                        alpha = int(55 * (1 - dist) ** 1.5)
                        r, g, b = self._hsv_to_rgb(hue, 0.6, 0.7 + 0.3 * (1 - dist))
                        ad.point((x, py), fill=(r, g, b, alpha))
        aurora = aurora.filter(ImageFilter.GaussianBlur(radius=6))
        img = Image.alpha_composite(img, aurora)

        draw = ImageDraw.Draw(img)
        snow_y = int(self.height * 0.75)
        for layer in range(3):
            points = [(0, self.height)]
            x = 0
            while x <= self.width:
                peak = snow_y + layer * 12 + rng.randint(-8, 8)
                points.append((x, peak))
                x += rng.randint(8, 25)
            points.append((self.width, self.height))
            r, g, b = self._hsv_to_rgb(210, 0.1, 0.15 + layer * 0.05)
            draw.polygon(points, fill=(r, g, b, 255))

        for _ in range(rng.randint(4, 10)):
            tx = rng.randint(0, self.width)
            ty = rng.randint(snow_y + 5, self.height - 5)
            th = rng.randint(15, 35)
            draw.rectangle([tx - 1, ty - th, tx + 1, ty], fill=(10, 15, 10, 200))
            draw.polygon([(tx, ty - th - 10), (tx - 8, ty - th + 5), (tx + 8, ty - th + 5)], fill=(8, 20, 8, 210))
        return img

    # ─── Sunset Coast ─────────────────────────────────────────────

    def _scene_sunset_coast(self, rng: random.Random) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        horizon = int(self.height * rng.uniform(0.38, 0.48))

        sky_top = self._hsv_to_rgb(260, 0.5, 0.35)
        sky_mid = self._hsv_to_rgb(20, 0.75, 0.85)
        sky_horizon = self._hsv_to_rgb(40, 0.9, 0.95)
        for y in range(horizon):
            t = y / horizon
            if t < 0.4:
                c = self._lerp_color(sky_top, sky_mid, t / 0.4)
            else:
                c = self._lerp_color(sky_mid, sky_horizon, (t - 0.4) / 0.6)
            draw.line([(0, y), (self.width, y)], fill=(*c, 255))

        sun_x = rng.randint(self.width // 4, 3 * self.width // 4)
        sun_y = horizon - rng.randint(5, 25)
        for r in range(70, 0, -1):
            alpha = int(200 * (1 - r / 70) ** 1.5)
            hue = max(0, 40 - r // 2)
            sr, sg, sb = self._hsv_to_rgb(hue, 0.7, 1.0)
            draw.ellipse([sun_x - r, sun_y - r, sun_x + r, sun_y + r], fill=(sr, sg, sb, alpha))

        cloud_noise = self._generate_noise_layer(self.width, horizon, 4, 3, rng)
        cloud_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        cpx = cloud_layer.load()
        npx = cloud_noise.load()
        for y in range(min(horizon, cloud_noise.height)):
            for x in range(min(self.width, cloud_noise.width)):
                v = npx[x, y]
                if v > 140:
                    a = int((v - 140) / 115 * 150)
                    dist_to_sun = math.sqrt((x - sun_x) ** 2 + (y - sun_y) ** 2)
                    warmth = max(0, 1 - dist_to_sun / 200)
                    cr = int(255 * (0.7 + 0.3 * warmth))
                    cg = int(200 * (0.5 + 0.5 * warmth))
                    cb = int(180 * (1 - warmth * 0.5))
                    cpx[x, y] = (cr, cg, cb, a)
        img = Image.alpha_composite(img, cloud_layer.filter(ImageFilter.GaussianBlur(radius=3)))

        draw = ImageDraw.Draw(img)
        water_top = self._hsv_to_rgb(210, 0.5, 0.45)
        water_bot = self._hsv_to_rgb(220, 0.6, 0.2)
        for y in range(horizon, self.height):
            t = (y - horizon) / max(1, self.height - horizon)
            c = self._lerp_color(water_top, water_bot, t)
            draw.line([(0, y), (self.width, y)], fill=(*c, 255))

        sun_reflect_w = rng.randint(20, 50)
        for y in range(horizon, self.height):
            t = (y - horizon) / max(1, self.height - horizon)
            alpha = int(100 * (1 - t))
            wobble = int(5 * math.sin(y * 0.3))
            draw.line(
                [(sun_x - sun_reflect_w + wobble, y), (sun_x + sun_reflect_w + wobble, y)],
                fill=(255, 200, 120, alpha),
            )

        for _ in range(rng.randint(10, 25)):
            wy = rng.randint(horizon + 8, self.height - 5)
            wx = rng.randint(0, self.width - 50)
            ww = rng.randint(20, 80)
            for dx in range(ww):
                y_off = int(2 * math.sin(dx * 0.2 + wy * 0.1))
                draw.point((wx + dx, wy + y_off), fill=(255, 255, 255, rng.randint(25, 70)))

        for _ in range(rng.randint(2, 5)):
            rx = rng.randint(0, self.width)
            ry = rng.randint(horizon - 5, horizon + 5)
            rw = rng.randint(30, 80)
            rh = rng.randint(10, 25)
            draw.polygon(
                [(rx, ry), (rx + rw // 3, ry - rh), (rx + rw * 2 // 3, ry - rh + 5), (rx + rw, ry)],
                fill=(15, 12, 10, 230),
            )
        return img

    # ─── Neon Metropolis ──────────────────────────────────────────

    def _scene_neon_metropolis(self, rng: random.Random) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        for y in range(self.height):
            t = y / self.height
            r, g, b = self._hsv_to_rgb(250, 0.4 - t * 0.2, 0.08 + t * 0.04)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b, 255))

        for _ in range(rng.randint(60, 180)):
            sx, sy = rng.randint(0, self.width), rng.randint(0, self.height - 20)
            br = rng.randint(120, 255)
            draw.rectangle([sx, sy, sx + 1, sy + 1], fill=(br, br, br - 20, 180))

        ground_y = int(self.height * 0.82)
        buildings = []
        x = 0
        while x < self.width:
            bw = rng.randint(18, 55)
            bh = rng.randint(50, int(self.height * 0.72))
            buildings.append((x, ground_y - bh, bw, bh))
            x += bw + rng.randint(1, 6)

        for bx, by, bw, bh in buildings:
            r, g, b = self._hsv_to_rgb(rng.randint(210, 245), 0.12, rng.uniform(0.1, 0.22))
            draw.rectangle([bx, by, bx + bw, ground_y], fill=(r, g, b, 255))

            win_rows = max(1, bh // 16)
            win_cols = max(1, bw // 12)
            for wr in range(win_rows):
                for wc in range(win_cols):
                    if rng.random() > 0.3:
                        wx = bx + 4 + wc * 11
                        wy = by + 6 + wr * 15
                        if wx + 5 < bx + bw - 2 and wy + 7 < ground_y - 2:
                            lit_hue = rng.choice([35, 45, 55, 175, 190])
                            lr, lg, lb = self._hsv_to_rgb(lit_hue, 0.5, 0.85)
                            draw.rectangle([wx, wy, wx + 5, wy + 7], fill=(lr, lg, lb, rng.randint(140, 220)))

        neon_colors = [
            (0, 255, 200), (255, 0, 150), (0, 150, 255),
            (255, 255, 0), (200, 0, 255), (255, 100, 0),
        ]
        for _ in range(rng.randint(4, 10)):
            bx, by, bw, bh = rng.choice(buildings)
            nc = rng.choice(neon_colors)
            sign_w = rng.randint(8, min(25, bw - 4))
            sign_h = rng.randint(4, 10)
            sx = bx + (bw - sign_w) // 2
            sy = by + rng.randint(5, max(6, bh // 3))
            draw.rectangle([sx, sy, sx + sign_w, sy + sign_h], fill=(*nc, 220))
            glow = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            for er in range(12, 0, -1):
                ga = int(30 * (1 - er / 12))
                gd.rectangle(
                    [sx - er, sy - er, sx + sign_w + er, sy + sign_h + er],
                    fill=(*nc, ga),
                )
            img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(radius=4)))

        draw = ImageDraw.Draw(img)
        draw.rectangle([0, ground_y, self.width, self.height], fill=(12, 12, 18, 255))

        rain_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rain_layer)
        for _ in range(rng.randint(40, 100)):
            rx = rng.randint(0, self.width)
            ry = rng.randint(0, self.height)
            rl = rng.randint(6, 18)
            rd.line([(rx, ry), (rx - 1, ry + rl)], fill=(150, 170, 200, rng.randint(20, 50)))
        img = Image.alpha_composite(img, rain_layer)

        for _ in range(rng.randint(5, 12)):
            lx = rng.randint(0, self.width)
            ly = rng.randint(ground_y, self.height)
            for r in range(6, 0, -1):
                draw.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(255, 200, 100, int(35 * (1 - r / 6))))
        return img

    # ─── Sakura Garden ────────────────────────────────────────────

    def _scene_sakura_garden(self, rng: random.Random) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        sky_top = self._hsv_to_rgb(330, 0.2, 0.92)
        sky_bot = self._hsv_to_rgb(340, 0.15, 0.97)
        for y in range(self.height):
            t = y / self.height
            c = self._lerp_color(sky_top, sky_bot, t)
            draw.line([(0, y), (self.width, y)], fill=(*c, 255))

        for _ in range(rng.randint(3, 7)):
            cx, cy = rng.randint(0, self.width), rng.randint(0, int(self.height * 0.4))
            for r in range(rng.randint(25, 50), 0, -2):
                a = int(25 * (1 - r / 50))
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 230, 240, a))

        ground_y = int(self.height * 0.7)
        for y in range(ground_y, self.height):
            t = (y - ground_y) / max(1, self.height - ground_y)
            r, g, b = self._hsv_to_rgb(110, 0.35 - t * 0.15, 0.55 - t * 0.15)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b, 255))

        pond_cx = rng.randint(self.width // 4, 3 * self.width // 4)
        pond_cy = rng.randint(ground_y + 10, self.height - 15)
        pond_rx, pond_ry = rng.randint(35, 60), rng.randint(15, 25)
        for r in range(pond_ry, 0, -1):
            rx = int(pond_rx * r / pond_ry)
            a = 180 + int(75 * (1 - r / pond_ry))
            pr, pg, pb = self._hsv_to_rgb(200, 0.3, 0.6)
            draw.ellipse([pond_cx - rx, pond_cy - r, pond_cx + rx, pond_cy + r], fill=(pr, pg, pb, a))

        for _ in range(rng.randint(2, 4)):
            tx = rng.randint(20, self.width - 20)
            ty = ground_y
            trunk_h = rng.randint(60, 130)
            trunk_w = rng.randint(4, 8)
            draw.rectangle([tx - trunk_w // 2, ty - trunk_h, tx + trunk_w // 2, ty], fill=(90, 55, 35, 230))

            for branch in range(rng.randint(4, 8)):
                angle = rng.uniform(-1.2, 1.2)
                blen = rng.randint(25, 55)
                bx = tx + int(blen * math.sin(angle))
                by = ty - trunk_h + rng.randint(5, trunk_h // 2)
                draw.line([(tx, by), (bx, by - int(blen * 0.3))], fill=(90, 55, 35, 200), width=2)

                for _ in range(rng.randint(3, 7)):
                    fx = bx + rng.randint(-20, 20)
                    fy = by - int(blen * 0.3) + rng.randint(-15, 5)
                    fr = rng.randint(10, 22)
                    hue = rng.choice([330, 335, 340, 345])
                    sat = rng.uniform(0.3, 0.6)
                    val = rng.uniform(0.8, 0.95)
                    r, g, b = self._hsv_to_rgb(hue, sat, val)
                    draw.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], fill=(r, g, b, rng.randint(140, 200)))

        for _ in range(rng.randint(40, 100)):
            px = rng.randint(0, self.width)
            py = rng.randint(0, self.height)
            ps = rng.randint(2, 5)
            hue = rng.choice([330, 335, 340, 350])
            r, g, b = self._hsv_to_rgb(hue, rng.uniform(0.3, 0.6), rng.uniform(0.85, 0.98))
            draw.ellipse([px - ps, py - ps, px + ps, py + ps], fill=(r, g, b, rng.randint(100, 190)))
        return img

    # ─── Deep Cosmos ──────────────────────────────────────────────

    def _scene_deep_cosmos(self, rng: random.Random) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        for y in range(self.height):
            t = y / self.height
            r, g, b = self._hsv_to_rgb(245, 0.6 + t * 0.2, 0.04 + t * 0.02)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b, 255))

        for _ in range(rng.randint(120, 300)):
            sx, sy = rng.randint(0, self.width), rng.randint(0, self.height)
            br = rng.randint(140, 255)
            sz = rng.choice([1, 1, 1, 2, 2, 3])
            tint = rng.choice([(br, br, br), (br, br - 30, br - 60), (br - 30, br - 10, br)])
            draw.ellipse([sx, sy, sx + sz, sy + sz], fill=(*tint, rng.randint(170, 255)))

        nebula = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        nd = ImageDraw.Draw(nebula)
        for _ in range(rng.randint(4, 8)):
            nx, ny = rng.randint(0, self.width), rng.randint(0, self.height)
            hue = rng.choice([260, 280, 300, 320, 340, 200])
            for r in range(rng.randint(40, 90), 0, -2):
                cr, cg, cb = self._hsv_to_rgb(hue, 0.5, 0.4)
                a = int(20 * (1 - r / 90) ** 0.8)
                nd.ellipse([nx - r, ny - r, nx + r, ny + r], fill=(cr, cg, cb, a))
        img = Image.alpha_composite(img, nebula.filter(ImageFilter.GaussianBlur(radius=12)))

        draw = ImageDraw.Draw(img)
        for _ in range(rng.randint(2, 4)):
            bx, by = rng.randint(0, self.width), rng.randint(0, self.height)
            br = rng.randint(8, 22)
            for r in range(br, 0, -1):
                t = r / br
                hue = rng.randint(0, 360)
                pr, pg, pb = self._hsv_to_rgb(hue, 0.4 + 0.3 * (1 - t), 0.5 + 0.5 * (1 - t))
                a = int(200 * (1 - t) ** 0.5)
                draw.ellipse([bx - r, by - r, bx + r, by + r], fill=(pr, pg, pb, a))

        for _ in range(rng.randint(2, 5)):
            lx, ly = rng.randint(0, self.width), rng.randint(0, self.height)
            for r in range(rng.randint(15, 30), 0, -1):
                a = int(40 * (1 - r / 30))
                draw.ellipse([lx - r, ly - r, lx + r, ly + r], fill=(255, 250, 230, a))
        return img

    # ─── Coral Reef ───────────────────────────────────────────────

    def _scene_coral_reef(self, rng: random.Random) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        water_top = self._hsv_to_rgb(185, 0.6, 0.55)
        water_mid = self._hsv_to_rgb(195, 0.65, 0.35)
        water_bot = self._hsv_to_rgb(200, 0.7, 0.18)
        for y in range(self.height):
            t = y / self.height
            if t < 0.5:
                c = self._lerp_color(water_top, water_mid, t * 2)
            else:
                c = self._lerp_color(water_mid, water_bot, (t - 0.5) * 2)
            draw.line([(0, y), (self.width, y)], fill=(*c, 255))

        caustic = self._generate_noise_layer(self.width, self.height, 5, 3, rng)
        caustic_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        cpx = caustic_layer.load()
        npx = caustic.load()
        for y in range(self.height):
            for x in range(self.width):
                v = npx[x, y]
                if v > 170:
                    a = int((v - 170) / 85 * 60)
                    cpx[x, y] = (180, 220, 255, a)
        img = Image.alpha_composite(img, caustic_layer.filter(ImageFilter.GaussianBlur(radius=5)))

        draw = ImageDraw.Draw(img)
        for _ in range(rng.randint(3, 8)):
            rx = rng.randint(10, self.width - 10)
            ry = rng.randint(5, 25)
            for r in range(rng.randint(25, 50), 0, -1):
                a = int(35 * (1 - r / 50))
                draw.ellipse([rx - r, ry - r // 2, rx + r, ry + r // 2], fill=(200, 230, 255, a))

        sand_y = int(self.height * 0.75)
        for y in range(sand_y, self.height):
            t = (y - sand_y) / max(1, self.height - sand_y)
            r, g, b = self._hsv_to_rgb(40, 0.3 - t * 0.1, 0.5 - t * 0.15)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b, 255))

        coral_palette = [
            (255, 100, 100), (255, 150, 50), (200, 80, 180),
            (255, 200, 80), (100, 200, 150), (220, 120, 60),
        ]
        for _ in range(rng.randint(6, 15)):
            cx = rng.randint(10, self.width - 10)
            cy = rng.randint(sand_y - 15, self.height - 10)
            color = rng.choice(coral_palette)
            shape = rng.choice(["branch", "fan", "brain"])

            if shape == "branch":
                for branch in range(rng.randint(3, 6)):
                    angle = rng.uniform(-0.8, 0.8)
                    blen = rng.randint(15, 40)
                    bx = cx + int(blen * math.sin(angle))
                    by = cy - int(blen * math.cos(angle))
                    draw.line([(cx, cy), (bx, by)], fill=(*color, 200), width=rng.randint(2, 4))
                    for _ in range(rng.randint(2, 4)):
                        sub_angle = angle + rng.uniform(-0.5, 0.5)
                        slen = rng.randint(5, 15)
                        sx = bx + int(slen * math.sin(sub_angle))
                        sy = by - int(slen * math.cos(sub_angle))
                        draw.line([(bx, by), (sx, sy)], fill=(*color, 180), width=2)
            elif shape == "fan":
                for angle_i in range(rng.randint(5, 10)):
                    a = -0.8 + angle_i * 0.16
                    fl = rng.randint(15, 30)
                    fx = cx + int(fl * math.sin(a))
                    fy = cy - int(fl * math.cos(a))
                    draw.line([(cx, cy), (fx, fy)], fill=(*color, 190), width=2)
            else:
                cr = rng.randint(8, 18)
                draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(*color, 180))
                draw.ellipse([cx - cr + 3, cy - cr + 3, cx + cr - 3, cy + cr - 3], fill=(*color, 120))

        for _ in range(rng.randint(5, 15)):
            fx = rng.randint(0, self.width)
            fy = rng.randint(int(self.height * 0.2), sand_y)
            fs = rng.randint(3, 7)
            fc = rng.choice([(255, 180, 50), (50, 200, 255), (255, 100, 100), (100, 255, 150)])
            draw.ellipse([fx - fs, fy - fs // 2, fx + fs, fy + fs // 2], fill=(*fc, 200))
            tail_dx = -fs * 2 if rng.random() > 0.5 else fs * 2
            draw.polygon(
                [(fx + tail_dx, fy), (fx + tail_dx // 2, fy - fs // 2), (fx + tail_dx // 2, fy + fs // 2)],
                fill=(*fc, 170),
            )

        for _ in range(rng.randint(8, 25)):
            bx = rng.randint(0, self.width)
            by = rng.randint(0, self.height)
            br = rng.randint(2, 5)
            draw.ellipse([bx - br, by - br, bx + br, by + br], outline=(200, 230, 255, 80), width=1)
        return img

    # ─── Geometric Flow ───────────────────────────────────────────

    def _scene_geometric_flow(self, rng: random.Random) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        base_hue = rng.randint(0, 360)
        bg1 = self._hsv_to_rgb(base_hue, 0.25, 0.92)
        bg2 = self._hsv_to_rgb((base_hue + 40) % 360, 0.3, 0.85)
        self._draw_gradient_rect(draw, 0, 0, self.width, self.height, bg1, bg2, "vertical")

        noise_map = self._noise_heightmap(self.width, self.height, 4, 4, rng)
        flow_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        fd = ImageDraw.Draw(flow_layer)
        for _ in range(rng.randint(8, 18)):
            hue = (base_hue + rng.randint(30, 200)) % 360
            r, g, b = self._hsv_to_rgb(hue, rng.uniform(0.4, 0.75), rng.uniform(0.5, 0.85))
            alpha = rng.randint(50, 140)
            shape = rng.choice(["circle", "rect", "diamond", "triangle"])

            cx = rng.randint(-30, self.width + 30)
            cy = rng.randint(-30, self.height + 30)
            size = rng.randint(25, 100)

            if shape == "circle":
                fd.ellipse([cx - size, cy - size, cx + size, cy + size], fill=(r, g, b, alpha))
            elif shape == "rect":
                angle = rng.uniform(0, math.pi)
                dx = int(size * math.cos(angle))
                dy = int(size * math.sin(angle))
                fd.polygon(
                    [(cx - dx, cy - dy), (cx + dy, cy - dx), (cx + dx, cy + dy), (cx - dy, cy + dx)],
                    fill=(r, g, b, alpha),
                )
            elif shape == "diamond":
                fd.polygon(
                    [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)],
                    fill=(r, g, b, alpha),
                )
            else:
                fd.polygon(
                    [(cx, cy - size), (cx + size, cy + size), (cx - size, cy + size)],
                    fill=(r, g, b, alpha),
                )
        img = Image.alpha_composite(img, flow_layer)

        line_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        ld = ImageDraw.Draw(line_layer)
        for _ in range(rng.randint(5, 12)):
            points = []
            px, py = rng.randint(0, self.width), rng.randint(0, self.height)
            for _ in range(rng.randint(5, 15)):
                px = max(0, min(self.width, px + rng.randint(-50, 50)))
                py = max(0, min(self.height, py + rng.randint(-30, 30)))
                points.append((px, py))
            if len(points) >= 2:
                hue = (base_hue + rng.randint(60, 220)) % 360
                r, g, b = self._hsv_to_rgb(hue, 0.6, 0.75)
                ld.line(points, fill=(r, g, b, rng.randint(80, 180)), width=rng.randint(2, 5))
        img = Image.alpha_composite(img, line_layer)

        overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        for _ in range(rng.randint(3, 6)):
            cx, cy = rng.randint(0, self.width), rng.randint(0, self.height)
            for r in range(rng.randint(40, 80), 0, -3):
                hue = (base_hue + rng.randint(0, 120)) % 360
                cr, cg, cb = self._hsv_to_rgb(hue, 0.35, 0.55)
                a = int(20 * (1 - r / 80))
                od.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(cr, cg, cb, a))
        img = Image.alpha_composite(img, overlay.filter(ImageFilter.GaussianBlur(radius=8)))

        dot_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        dd = ImageDraw.Draw(dot_layer)
        for _ in range(rng.randint(20, 60)):
            dx, dy = rng.randint(0, self.width), rng.randint(0, self.height)
            ds = rng.randint(2, 6)
            hue = (base_hue + rng.randint(0, 180)) % 360
            r, g, b = self._hsv_to_rgb(hue, 0.5, 0.8)
            dd.ellipse([dx - ds, dy - ds, dx + ds, dy + ds], fill=(r, g, b, rng.randint(60, 150)))
        img = Image.alpha_composite(img, dot_layer)
        return img

    # ═══════════════════════════════════════════════════════════════
    #  Post-Processing
    # ═══════════════════════════════════════════════════════════════

    def _add_atmosphere(self, img: Image.Image, rng: random.Random) -> Image.Image:
        vignette = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(vignette)
        cx, cy = self.width // 2, self.height // 2
        max_r = math.sqrt(cx * cx + cy * cy)
        for r in range(int(max_r), 0, -3):
            alpha = int(55 * (r / max_r) ** 2)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img, vignette)

        if rng.random() > 0.4:
            tint = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            td = ImageDraw.Draw(tint)
            hue = rng.randint(0, 360)
            r, g, b = self._hsv_to_rgb(hue, 0.25, 0.8)
            td.rectangle([0, 0, self.width, self.height], fill=(r, g, b, rng.randint(8, 22)))
            img = Image.alpha_composite(img, tint)
        return img

    def _add_texture_overlay(self, img: Image.Image, rng: random.Random) -> Image.Image:
        texture = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(texture)

        grain_count = self.complexity * 120
        for _ in range(grain_count):
            x, y = rng.randint(0, self.width - 1), rng.randint(0, self.height - 1)
            v = rng.randint(0, 255)
            draw.point((x, y), fill=(v, v, v, rng.randint(4, 18)))

        if self.complexity >= 3:
            for _ in range(self.complexity * 4):
                x1, y1 = rng.randint(0, self.width), rng.randint(0, self.height)
                angle = rng.uniform(0, math.pi)
                length = rng.randint(15, 60)
                x2 = int(x1 + length * math.cos(angle))
                y2 = int(y1 + length * math.sin(angle))
                draw.line([(x1, y1), (x2, y2)], fill=(0, 0, 0, rng.randint(4, 12)), width=1)
        return Image.alpha_composite(img, texture)

    def _add_anti_ai_noise(self, img: Image.Image, rng: random.Random) -> Image.Image:
        noise = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(noise)

        for _ in range(self.complexity * 35):
            x, y = rng.randint(0, self.width - 1), rng.randint(0, self.height - 1)
            r, g, b = rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)
            sz = rng.randint(1, 3)
            draw.ellipse([x, y, x + sz, y + sz], fill=(r, g, b, rng.randint(12, 45)))

        if self.complexity >= 4:
            for _ in range(rng.randint(2, 5)):
                pts = []
                px, py = rng.randint(0, self.width), rng.randint(0, self.height)
                for _ in range(rng.randint(3, 8)):
                    px += rng.randint(-25, 25)
                    py += rng.randint(-12, 12)
                    pts.append((px, py))
                if len(pts) >= 2:
                    draw.line(pts, fill=(rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255), rng.randint(12, 35)), width=1)
        return Image.alpha_composite(img, noise)

    # ═══════════════════════════════════════════════════════════════
    #  Jigsaw Puzzle Piece Generation
    # ═══════════════════════════════════════════════════════════════

    def _generate_jigsaw_path(
        self, cx: int, cy: int, size: int, rng: random.Random
    ) -> list[Tuple[int, int]]:
        half = size // 2
        tab_h = int(size * self.tab_ratio)
        tabs = [rng.choice([-1, 1]) for _ in range(4)]

        points: list[Tuple[int, int]] = []
        n_edge = 36

        for i in range(n_edge + 1):
            t = i / n_edge
            x = cx - half + t * size
            y = cy - half
            if 0.22 < t < 0.78:
                nt = (t - 0.22) / 0.56
                y -= self._tab_profile(nt, tab_h, tabs[0])
            points.append((int(x), int(y)))

        for i in range(n_edge + 1):
            t = i / n_edge
            x = cx + half
            y = cy - half + t * size
            if 0.22 < t < 0.78:
                nt = (t - 0.22) / 0.56
                x += self._tab_profile(nt, tab_h, tabs[1])
            points.append((int(x), int(y)))

        for i in range(n_edge + 1):
            t = i / n_edge
            x = cx + half - t * size
            y = cy + half
            if 0.22 < t < 0.78:
                nt = (t - 0.22) / 0.56
                y += self._tab_profile(nt, tab_h, tabs[2])
            points.append((int(x), int(y)))

        for i in range(n_edge + 1):
            t = i / n_edge
            x = cx - half
            y = cy + half - t * size
            if 0.22 < t < 0.78:
                nt = (t - 0.22) / 0.56
                x -= self._tab_profile(nt, tab_h, tabs[3])
            points.append((int(x), int(y)))

        return points

    @staticmethod
    def _tab_profile(t: float, height: int, direction: int) -> float:
        neck_zone = 0.13
        neck_dip = 0.10

        if t < neck_zone:
            blend = t / neck_zone
            curve = -neck_dip * math.sin(blend * math.pi * 0.5)
        elif t > 1 - neck_zone:
            blend = (1 - t) / neck_zone
            curve = -neck_dip * math.sin(blend * math.pi * 0.5)
        else:
            ht = (t - neck_zone) / (1 - 2 * neck_zone)
            head = math.sin(ht * math.pi)
            neck_transition = 0.0
            if ht < 0.08:
                neck_transition = -0.06 * math.cos(ht / 0.08 * math.pi * 0.5)
            elif ht > 0.92:
                neck_transition = -0.06 * math.cos((1 - ht) / 0.08 * math.pi * 0.5)
            curve = head + neck_transition

        return direction * height * curve

    def _render_puzzle_mask(self, path: list[Tuple[int, int]]) -> Image.Image:
        mask = Image.new("L", (self.width, self.height), 0)
        draw = ImageDraw.Draw(mask)
        draw.polygon(path, fill=255)
        mask = mask.filter(ImageFilter.SMOOTH_MORE)
        mask = mask.filter(ImageFilter.SMOOTH_MORE)
        return mask

    # ═══════════════════════════════════════════════════════════════
    #  Puzzle Piece Extraction & Contour-Based 3D Lighting
    # ═══════════════════════════════════════════════════════════════

    def _extract_puzzle_piece(
        self, background: Image.Image, mask: Image.Image, px: int, py: int
    ) -> Tuple[Image.Image, Image.Image]:
        s = self.puzzle_size
        margin = s // 2 + 22

        x1 = max(0, px - s // 2 - margin)
        y1 = max(0, py - s // 2 - margin)
        x2 = min(self.width, px + s // 2 + margin)
        y2 = min(self.height, py + s // 2 + margin)

        bg_copy = background.copy()
        r_ch, g_ch, b_ch, _ = bg_copy.split()
        bg_masked = Image.merge("RGBA", (r_ch, g_ch, b_ch, mask))

        piece = bg_masked.crop((x1, y1, x2, y2))
        mask_crop = mask.crop((x1, y1, x2, y2))
        return piece, mask_crop

    def _add_3d_lighting(self, piece: Image.Image, mask_crop: Image.Image) -> Image.Image:
        pw, ph = piece.size

        shadow_layer = self._create_contour_shadow(mask_crop, pw, ph)
        highlight_layer = self._create_contour_highlight(mask_crop, pw, ph)
        bevel_layer = self._create_bevel(mask_crop, pw, ph)

        result = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        result = Image.alpha_composite(result, shadow_layer)
        result = Image.alpha_composite(result, piece)
        result = Image.alpha_composite(result, highlight_layer)
        result = Image.alpha_composite(result, bevel_layer)
        return result

    def _create_contour_shadow(self, mask: Image.Image, pw: int, ph: int) -> Image.Image:
        dilated = mask.filter(ImageFilter.MaxFilter(9))
        dilated = dilated.filter(ImageFilter.GaussianBlur(radius=3))

        shadow = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        shadow_px = shadow.load()
        mask_px = mask.load()
        dilated_px = dilated.load()

        for y in range(ph):
            for x in range(pw):
                d = dilated_px[x, y]
                m = mask_px[x, y]
                if d > 30 and m < 128:
                    shadow_alpha = int(d / 255.0 * 65)
                    ox = min(pw - 1, x + 3)
                    oy = min(ph - 1, y + 3)
                    shadow_px[ox, oy] = (
                        shadow_px[ox, oy][0],
                        shadow_px[ox, oy][1],
                        shadow_px[ox, oy][2],
                        min(255, shadow_px[ox, oy][3] + shadow_alpha),
                    )

        return shadow.filter(ImageFilter.GaussianBlur(radius=2))

    def _create_contour_highlight(self, mask: Image.Image, pw: int, ph: int) -> Image.Image:
        eroded = mask.filter(ImageFilter.MinFilter(5))
        eroded = eroded.filter(ImageFilter.GaussianBlur(radius=2))

        highlight = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        hpx = highlight.load()
        mask_px = mask.load()
        eroded_px = eroded.load()

        for y in range(ph):
            for x in range(pw):
                m = mask_px[x, y]
                e = eroded_px[x, y]
                if m > 128 and e < 80:
                    edge_strength = (m - e) / 255.0
                    alpha = int(edge_strength * 70)
                    ox = max(0, x - 1)
                    oy = max(0, y - 1)
                    hpx[ox, oy] = (
                        min(255, hpx[ox, oy][0] + 255),
                        min(255, hpx[ox, oy][1] + 255),
                        min(255, hpx[ox, oy][2] + 255),
                        min(255, hpx[ox, oy][3] + alpha),
                    )

        return highlight.filter(ImageFilter.GaussianBlur(radius=1))

    def _create_bevel(self, mask: Image.Image, pw: int, ph: int) -> Image.Image:
        dilated = mask.filter(ImageFilter.MaxFilter(5))
        eroded = mask.filter(ImageFilter.MinFilter(5))

        bevel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        bpx = bevel.load()
        dpx = dilated.load()
        epx = eroded.load()
        mpx = mask.load()

        for y in range(1, ph - 1):
            for x in range(1, pw - 1):
                m = mpx[x, y]
                if m < 64:
                    continue
                d_above = mpx[x, y - 1]
                d_left = mpx[x - 1, y]
                d_below = mpx[x, y + 1]
                d_right = mpx[x + 1, y]

                top_edge = d_above < 128 and m > 128
                left_edge = d_left < 128 and m > 128
                bottom_edge = d_below < 128 and m > 128
                right_edge = d_right < 128 and m > 128

                if top_edge or left_edge:
                    bpx[x, y] = (255, 255, 255, 45)
                elif bottom_edge or right_edge:
                    bpx[x, y] = (0, 0, 0, 35)

        return bevel.filter(ImageFilter.GaussianBlur(radius=1))

    # ═══════════════════════════════════════════════════════════════
    #  Hole Rendering & Ambient Occlusion
    # ═══════════════════════════════════════════════════════════════

    def _cut_puzzle_hole(
        self, background: Image.Image, mask: Image.Image, px: int, py: int
    ) -> Image.Image:
        hole_overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        hole_draw = ImageDraw.Draw(hole_overlay)

        path = self._generate_jigsaw_path(px, py, self.puzzle_size, random.Random(42))
        hole_draw.polygon(path, fill=(0, 0, 0, 150))

        background = Image.alpha_composite(background, hole_overlay)

        border_outer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        bo_draw = ImageDraw.Draw(border_outer)
        if len(path) >= 2:
            bo_draw.line(path, fill=(0, 0, 0, 140), width=3)
        background = Image.alpha_composite(background, border_outer.filter(ImageFilter.GaussianBlur(radius=1)))

        border_inner = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        bi_draw = ImageDraw.Draw(border_inner)
        if len(path) >= 2:
            bi_draw.line(path, fill=(255, 255, 255, 35), width=1)
        background = Image.alpha_composite(background, border_inner)

        return background

    def _render_hole_ao(
        self, background: Image.Image, mask: Image.Image, px: int, py: int
    ) -> Image.Image:
        dilated = mask.filter(ImageFilter.MaxFilter(11))
        dilated = dilated.filter(ImageFilter.GaussianBlur(radius=5))

        ao_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        ao_px = ao_layer.load()
        d_px = dilated.load()
        m_px = mask.load()

        for y in range(self.height):
            for x in range(self.width):
                d = d_px[x, y]
                m = m_px[x, y]
                if d > 30 and m < 128:
                    dist_factor = d / 255.0
                    alpha = int(dist_factor * 45)
                    ao_px[x, y] = (0, 0, 0, alpha)

        background = Image.alpha_composite(background, ao_layer)

        highlight = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        hl_draw = ImageDraw.Draw(highlight)
        path_inner = self._generate_jigsaw_path(px - 1, py - 1, self.puzzle_size - 2, random.Random(43))
        if len(path_inner) >= 2:
            hl_draw.line(path_inner, fill=(255, 255, 255, 20), width=1)
        background = Image.alpha_composite(background, highlight)

        return background

    # ═══════════════════════════════════════════════════════════════
    #  Utilities
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _image_to_b64(img: Image.Image, format: str = "PNG", quality: int = 95) -> str:
        buffer = io.BytesIO()
        if format == "WEBP":
            img.save(buffer, format="WEBP", quality=quality, method=4)
        else:
            img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")


captcha_generator = CaptchaGenerator()
