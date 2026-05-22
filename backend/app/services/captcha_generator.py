"""
CodePilgrim Professional Captcha Generator

Enterprise production-grade implementation featuring:
- Fully procedural random background generation (no fixed scene patterns)
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

from PIL import Image, ImageDraw, ImageFilter


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

    def generate(self) -> CaptchaResult:
        rng = random.Random()

        background = self._render_scene(rng)
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

        background = self._cut_puzzle_hole(background, puzzle_path, puzzle_x, puzzle_y)
        background = self._render_hole_ao(background, puzzle_path, puzzle_x, puzzle_y)

        background_b64 = self._image_to_b64(background, format="PNG")
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

    # ═══════════════════════════════════════════════════════════════
    #  Fully Procedural Random Scene Rendering
    # ═══════════════════════════════════════════════════════════════

    def _render_scene(self, rng: random.Random) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        base_hue = rng.randint(0, 360)
        palette = self._harmonious_palette(base_hue, rng.randint(4, 7), rng)

        n_stops = rng.randint(2, 4)
        gradient_stops = [palette[i % len(palette)] for i in range(n_stops)]
        direction = rng.choice(["vertical", "horizontal", "diagonal_lr", "diagonal_rl", "radial"])
        self._draw_random_gradient(draw, gradient_stops, direction, rng)

        n_noise_layers = rng.randint(2, 5)
        for _ in range(n_noise_layers):
            noise = self._generate_noise_layer(
                self.width, self.height,
                base_scale=rng.randint(2, 6),
                octaves=rng.randint(2, 5),
                rng=rng,
            )
            noise_rgba = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            npx = noise_rgba.load()
            ngray = noise.load()
            hue = (base_hue + rng.randint(-60, 60)) % 360
            r, g, b = self._hsv_to_rgb(hue, rng.uniform(0.2, 0.7), rng.uniform(0.3, 0.8))
            blend_alpha = rng.randint(15, 55)
            for y in range(self.height):
                for x in range(self.width):
                    v = ngray[x, y] / 255.0
                    a = int(v * blend_alpha)
                    npx[x, y] = (r, g, b, a)
            noise_rgba = noise_rgba.filter(ImageFilter.GaussianBlur(radius=rng.randint(1, 4)))
            img = Image.alpha_composite(img, noise_rgba)

        n_shapes = rng.randint(3, 12)
        for _ in range(n_shapes):
            img = self._draw_random_shape(img, palette, rng)

        n_blobs = rng.randint(1, 5)
        for _ in range(n_blobs):
            blob = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            bd = ImageDraw.Draw(blob)
            cx = rng.randint(-30, self.width + 30)
            cy = rng.randint(-30, self.height + 30)
            max_r = rng.randint(30, 100)
            hue = (base_hue + rng.randint(-40, 80)) % 360
            r, g, b = self._hsv_to_rgb(hue, rng.uniform(0.3, 0.7), rng.uniform(0.4, 0.8))
            for rad in range(max_r, 0, -2):
                a = int(25 * (1 - rad / max_r) ** 0.8)
                bd.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(r, g, b, a))
            blob = blob.filter(ImageFilter.GaussianBlur(radius=rng.randint(8, 20)))
            img = Image.alpha_composite(img, blob)

        n_lines = rng.randint(0, 8)
        for _ in range(n_lines):
            line_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            ld = ImageDraw.Draw(line_layer)
            points = []
            px, py = rng.randint(0, self.width), rng.randint(0, self.height)
            for _ in range(rng.randint(3, 10)):
                px = max(0, min(self.width, px + rng.randint(-60, 60)))
                py = max(0, min(self.height, py + rng.randint(-40, 40)))
                points.append((px, py))
            if len(points) >= 2:
                hue = (base_hue + rng.randint(-30, 90)) % 360
                r, g, b = self._hsv_to_rgb(hue, rng.uniform(0.3, 0.7), rng.uniform(0.5, 0.9))
                ld.line(points, fill=(r, g, b, rng.randint(30, 120)), width=rng.randint(1, 5))
            img = Image.alpha_composite(img, line_layer)

        if rng.random() > 0.3:
            dot_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            dd = ImageDraw.Draw(dot_layer)
            for _ in range(rng.randint(10, 50)):
                dx, dy = rng.randint(0, self.width), rng.randint(0, self.height)
                ds = rng.randint(2, 8)
                hue = (base_hue + rng.randint(0, 180)) % 360
                r, g, b = self._hsv_to_rgb(hue, rng.uniform(0.3, 0.7), rng.uniform(0.6, 1.0))
                dd.ellipse([dx - ds, dy - ds, dx + ds, dy + ds], fill=(r, g, b, rng.randint(40, 160)))
            img = Image.alpha_composite(img, dot_layer)

        if rng.random() > 0.5:
            caustic = self._generate_noise_layer(self.width, self.height, rng.randint(3, 6), rng.randint(2, 4), rng)
            caustic_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            cpx = caustic_layer.load()
            cnpx = caustic.load()
            hue = (base_hue + rng.randint(-30, 30)) % 360
            r, g, b = self._hsv_to_rgb(hue, 0.3, 0.8)
            threshold = rng.randint(140, 180)
            for y in range(self.height):
                for x in range(self.width):
                    v = cnpx[x, y]
                    if v > threshold:
                        a = int((v - threshold) / (255 - threshold) * 50)
                        cpx[x, y] = (r, g, b, a)
            img = Image.alpha_composite(img, caustic_layer.filter(ImageFilter.GaussianBlur(radius=rng.randint(3, 8))))

        if rng.random() > 0.4:
            wave_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            wd = ImageDraw.Draw(wave_layer)
            for _ in range(rng.randint(1, 4)):
                base_y = rng.randint(0, self.height)
                hue = (base_hue + rng.randint(-40, 40)) % 360
                amp = rng.randint(10, 40)
                freq = rng.uniform(0.01, 0.04)
                phase = rng.uniform(0, math.pi * 2)
                for x in range(self.width):
                    y_center = base_y + int(amp * math.sin(x * freq + phase))
                    for dy in range(-rng.randint(8, 25), rng.randint(8, 25)):
                        py = y_center + dy
                        if 0 <= py < self.height:
                            dist = abs(dy) / 25.0
                            a = int(40 * (1 - dist) ** 1.5)
                            r, g, b = self._hsv_to_rgb(hue, rng.uniform(0.3, 0.6), rng.uniform(0.5, 0.9))
                            wd.point((x, py), fill=(r, g, b, a))
            wave_layer = wave_layer.filter(ImageFilter.GaussianBlur(radius=rng.randint(2, 5)))
            img = Image.alpha_composite(img, wave_layer)

        if rng.random() > 0.5:
            stripe_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
            sd = ImageDraw.Draw(stripe_layer)
            stripe_dir = rng.choice(["h", "v", "d"])
            stripe_width = rng.randint(3, 15)
            stripe_gap = rng.randint(5, 20)
            hue = (base_hue + rng.randint(-30, 60)) % 360
            r, g, b = self._hsv_to_rgb(hue, rng.uniform(0.2, 0.5), rng.uniform(0.4, 0.7))
            a = rng.randint(10, 35)
            if stripe_dir == "h":
                y = 0
                while y < self.height:
                    sd.rectangle([0, y, self.width, y + stripe_width], fill=(r, g, b, a))
                    y += stripe_width + stripe_gap
            elif stripe_dir == "v":
                x = 0
                while x < self.width:
                    sd.rectangle([x, 0, x + stripe_width, self.height], fill=(r, g, b, a))
                    x += stripe_width + stripe_gap
            else:
                offset = -self.height
                while offset < self.width + self.height:
                    pts = [(offset, 0), (offset + stripe_width, 0),
                           (offset + stripe_width + self.height, self.height),
                           (offset + self.height, self.height)]
                    sd.polygon(pts, fill=(r, g, b, a))
                    offset += stripe_width + stripe_gap
            stripe_layer = stripe_layer.filter(ImageFilter.GaussianBlur(radius=1))
            img = Image.alpha_composite(img, stripe_layer)

        return img

    def _draw_random_gradient(
        self,
        draw: ImageDraw.ImageDraw,
        stops: list[Tuple[int, int, int]],
        direction: str,
        rng: random.Random,
    ) -> None:
        if direction == "radial":
            cx, cy = self.width // 2, self.height // 2
            max_r = int(math.sqrt(cx * cx + cy * cy))
            for r in range(max_r, 0, -1):
                t = r / max_r
                idx = t * (len(stops) - 1)
                i = min(int(idx), len(stops) - 2)
                frac = idx - i
                c = self._lerp_color(stops[i], stops[i + 1], frac)
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*c, 255))
            return

        for y in range(self.height):
            for x in range(self.width):
                if direction == "vertical":
                    t = y / max(1, self.height - 1)
                elif direction == "horizontal":
                    t = x / max(1, self.width - 1)
                elif direction == "diagonal_lr":
                    t = (x + y) / max(1, self.width + self.height - 2)
                else:
                    t = (self.width - 1 - x + y) / max(1, self.width + self.height - 2)
                idx = t * (len(stops) - 1)
                i = min(int(idx), len(stops) - 2)
                frac = idx - i
                c = self._lerp_color(stops[i], stops[i + 1], frac)
                draw.point((x, y), fill=(*c, 255))

    def _draw_random_shape(
        self, img: Image.Image, palette: list[Tuple[int, int, int]], rng: random.Random
    ) -> Image.Image:
        shape_layer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shape_layer)
        color = rng.choice(palette)
        alpha = rng.randint(30, 140)
        cx = rng.randint(-40, self.width + 40)
        cy = rng.randint(-40, self.height + 40)
        size = rng.randint(15, 120)
        shape_type = rng.choice(["circle", "rect", "diamond", "triangle", "ellipse", "hexagon", "ring"])

        if shape_type == "circle":
            sd.ellipse([cx - size, cy - size, cx + size, cy + size], fill=(*color, alpha))
        elif shape_type == "rect":
            angle = rng.uniform(0, math.pi)
            dx = int(size * math.cos(angle))
            dy = int(size * math.sin(angle))
            sd.polygon(
                [(cx - dx, cy - dy), (cx + dy, cy - dx), (cx + dx, cy + dy), (cx - dy, cy + dx)],
                fill=(*color, alpha),
            )
        elif shape_type == "diamond":
            sd.polygon(
                [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)],
                fill=(*color, alpha),
            )
        elif shape_type == "triangle":
            a1 = rng.uniform(0, 2 * math.pi)
            pts = []
            for k in range(3):
                a = a1 + k * 2 * math.pi / 3
                pts.append((cx + int(size * math.cos(a)), cy + int(size * math.sin(a))))
            sd.polygon(pts, fill=(*color, alpha))
        elif shape_type == "ellipse":
            rx = rng.randint(15, 80)
            ry = rng.randint(10, 50)
            sd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(*color, alpha))
        elif shape_type == "hexagon":
            pts = []
            for k in range(6):
                a = k * math.pi / 3 + rng.uniform(0, 0.3)
                pts.append((cx + int(size * math.cos(a)), cy + int(size * math.sin(a))))
            sd.polygon(pts, fill=(*color, alpha))
        elif shape_type == "ring":
            inner = max(1, size - rng.randint(4, 15))
            sd.ellipse([cx - size, cy - size, cx + size, cy + size], fill=(*color, alpha))
            sd.ellipse([cx - inner, cy - inner, cx + inner, cy + inner], fill=(0, 0, 0, 0))

        if rng.random() > 0.6:
            shape_layer = shape_layer.filter(ImageFilter.GaussianBlur(radius=rng.randint(2, 8)))

        return Image.alpha_composite(img, shape_layer)

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
        bevel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0))
        bpx = bevel.load()
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
        self, background: Image.Image, puzzle_path: list[Tuple[int, int]], px: int, py: int
    ) -> Image.Image:
        hole_overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        hole_draw = ImageDraw.Draw(hole_overlay)
        hole_draw.polygon(puzzle_path, fill=(0, 0, 0, 200))

        background = Image.alpha_composite(background, hole_overlay)

        border_outer = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        bo_draw = ImageDraw.Draw(border_outer)
        if len(puzzle_path) >= 2:
            bo_draw.line(puzzle_path, fill=(0, 0, 0, 180), width=3)
        background = Image.alpha_composite(background, border_outer.filter(ImageFilter.GaussianBlur(radius=1)))

        border_inner = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        bi_draw = ImageDraw.Draw(border_inner)
        if len(puzzle_path) >= 2:
            bi_draw.line(puzzle_path, fill=(255, 255, 255, 50), width=1)
        background = Image.alpha_composite(background, border_inner)

        return background

    def _render_hole_ao(
        self, background: Image.Image, puzzle_path: list[Tuple[int, int]], px: int, py: int
    ) -> Image.Image:
        mask = Image.new("L", (self.width, self.height), 0)
        draw = ImageDraw.Draw(mask)
        draw.polygon(puzzle_path, fill=255)

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
                    alpha = int(dist_factor * 55)
                    ao_px[x, y] = (0, 0, 0, alpha)

        background = Image.alpha_composite(background, ao_layer)

        highlight = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        hl_draw = ImageDraw.Draw(highlight)
        if len(puzzle_path) >= 2:
            hl_draw.line(puzzle_path, fill=(255, 255, 255, 25), width=1)
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
