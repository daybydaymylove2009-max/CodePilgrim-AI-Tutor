"""
CodePilgrim 图形验证码生成器

独立可复用模块，生成复杂随机图形拼图验证码。
支持多种图形模式、干扰元素、拼图块切割。

使用方式：
    from app.services.captcha_generator import CaptchaGenerator

    gen = CaptchaGenerator()
    result = gen.generate()  # 返回 background_b64, puzzle_b64, position
"""

from __future__ import annotations

import base64
import io
import math
import random
from dataclasses import dataclass
from typing import Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont


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
    """
    复杂随机图形拼图验证码生成器.

    特性：
    - 多层随机背景（渐变+几何图形+噪点+纹理）
    - 不规则拼图块（带凸起/凹陷的锯齿边缘）
    - 拼图块阴影和边框
    - 背景缺口遮罩
    - 可配置尺寸、复杂度、干扰强度
    """

    def __init__(
        self,
        width: int = 340,
        height: int = 200,
        puzzle_size: int = 50,
        complexity: int = 3,
        interference: int = 3,
    ):
        self.width = width
        self.height = height
        self.puzzle_size = puzzle_size
        self.complexity = min(max(complexity, 1), 5)
        self.interference = min(max(interference, 1), 5)

    def generate(self) -> CaptchaResult:
        background = self._create_background()
        background = self._add_geometric_shapes(background)
        background = self._add_noise_and_texture(background)
        background = self._add_interference_lines(background)

        puzzle_x = random.randint(self.puzzle_size + 20, self.width - self.puzzle_size - 20)
        puzzle_y = random.randint(self.puzzle_size + 10, self.height - self.puzzle_size - 10)

        puzzle_mask = self._create_puzzle_mask(puzzle_x, puzzle_y)

        puzzle_piece = self._extract_puzzle_piece(background, puzzle_mask, puzzle_x, puzzle_y)

        background = self._cut_hole(background, puzzle_mask, puzzle_x, puzzle_y)

        background = self._add_hole_shadow(background, puzzle_x, puzzle_y)

        background_b64 = self._image_to_b64(background)
        puzzle_b64 = self._image_to_b64(puzzle_piece)

        return CaptchaResult(
            background_b64=background_b64,
            puzzle_b64=puzzle_b64,
            puzzle_x=puzzle_x,
            puzzle_y=puzzle_y,
            width=self.width,
            height=self.height,
            puzzle_size=self.puzzle_size,
        )

    def _create_background(self) -> Image.Image:
        img = Image.new("RGBA", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        base_hue = random.randint(0, 360)
        r1, g1, b1 = self._hsv_to_rgb(base_hue, 0.4, 0.85)
        r2, g2, b2 = self._hsv_to_rgb((base_hue + random.randint(30, 90)) % 360, 0.5, 0.65)

        direction = random.choice(["horizontal", "vertical", "diagonal", "radial"])

        if direction == "horizontal":
            for x in range(self.width):
                ratio = x / self.width
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                draw.line([(x, 0), (x, self.height)], fill=(r, g, b, 255))
        elif direction == "vertical":
            for y in range(self.height):
                ratio = y / self.height
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                draw.line([(0, y), (self.width, y)], fill=(r, g, b, 255))
        elif direction == "diagonal":
            for y in range(self.height):
                for x in range(0, self.width, 2):
                    ratio = (x + y) / (self.width + self.height)
                    r = int(r1 + (r2 - r1) * ratio)
                    g = int(g1 + (g2 - g1) * ratio)
                    b = int(b1 + (b2 - b1) * ratio)
                    draw.point((x, y), fill=(r, g, b, 255))
        else:
            cx, cy = self.width // 2, self.height // 2
            max_dist = math.sqrt(cx * cx + cy * cy)
            for y in range(self.height):
                for x in range(0, self.width, 2):
                    dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                    ratio = min(dist / max_dist, 1.0)
                    r = int(r1 + (r2 - r1) * ratio)
                    g = int(g1 + (g2 - g1) * ratio)
                    b = int(b1 + (b2 - b1) * ratio)
                    draw.point((x, y), fill=(r, g, b, 255))

        return img

    def _add_geometric_shapes(self, img: Image.Image) -> Image.Image:
        draw = ImageDraw.Draw(img)
        shape_count = self.complexity * 4

        for _ in range(shape_count):
            shape_type = random.choice(["circle", "rect", "triangle", "ellipse", "polygon", "arc"])
            hue = random.randint(0, 360)
            r, g, b = self._hsv_to_rgb(hue, random.uniform(0.3, 0.7), random.uniform(0.5, 0.9))
            alpha = random.randint(30, 120)
            color = (r, g, b, alpha)

            x1 = random.randint(-20, self.width)
            y1 = random.randint(-20, self.height)
            x2 = x1 + random.randint(20, 120)
            y2 = y1 + random.randint(20, 120)

            if shape_type == "circle":
                draw.ellipse([x1, y1, x2, y2], fill=color)
            elif shape_type == "rect":
                draw.rectangle([x1, y1, x2, y2], fill=color)
            elif shape_type == "triangle":
                points = [
                    (x1 + (x2 - x1) // 2, y1),
                    (x1, y2),
                    (x2, y2),
                ]
                draw.polygon(points, fill=color)
            elif shape_type == "ellipse":
                draw.ellipse([x1, y1, x1 + 80, y1 + 40], fill=color)
            elif shape_type == "polygon":
                n_sides = random.randint(5, 8)
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                radius = (x2 - x1) // 2
                points = []
                for i in range(n_sides):
                    angle = 2 * math.pi * i / n_sides - math.pi / 2
                    px = cx + int(radius * math.cos(angle))
                    py = cy + int(radius * math.sin(angle))
                    points.append((px, py))
                draw.polygon(points, fill=color)
            elif shape_type == "arc":
                draw.arc([x1, y1, x2, y2], random.randint(0, 180), random.randint(180, 360), fill=color, width=3)

        return img

    def _add_noise_and_texture(self, img: Image.Image) -> Image.Image:
        draw = ImageDraw.Draw(img)
        noise_count = self.interference * 200

        for _ in range(noise_count):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            alpha = random.randint(20, 80)
            draw.point((x, y), fill=(r, g, b, alpha))

        for _ in range(self.interference * 3):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            r = random.randint(0, 255)
            g = random.randint(0, 255)
            b = random.randint(0, 255)
            size = random.randint(1, 4)
            draw.ellipse([x, y, x + size, y + size], fill=(r, g, b, random.randint(40, 100)))

        if self.complexity >= 3:
            for _ in range(self.interference * 2):
                x1 = random.randint(0, self.width)
                y1 = random.randint(0, self.height)
                x2 = x1 + random.randint(-30, 30)
                y2 = y1 + random.randint(-30, 30)
                r = random.randint(100, 255)
                g = random.randint(100, 255)
                b = random.randint(100, 255)
                draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, random.randint(30, 80)), width=1)

        if self.complexity >= 4:
            img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 0.8)))

        return img

    def _add_interference_lines(self, img: Image.Image) -> Image.Image:
        draw = ImageDraw.Draw(img)
        line_count = self.interference * 2

        for _ in range(line_count):
            points = []
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            segments = random.randint(3, 8)
            for _ in range(segments):
                x += random.randint(-40, 40)
                y += random.randint(-20, 20)
                x = max(0, min(x, self.width))
                y = max(0, min(y, self.height))
                points.append((x, y))

            if len(points) >= 2:
                hue = random.randint(0, 360)
                r, g, b = self._hsv_to_rgb(hue, 0.5, 0.8)
                draw.line(points, fill=(r, g, b, random.randint(40, 100)), width=random.randint(1, 3))

        return img

    def _create_puzzle_mask(self, px: int, py: int) -> Image.Image:
        mask = Image.new("L", (self.width, self.height), 0)
        draw = ImageDraw.Draw(mask)

        s = self.puzzle_size
        tab_size = s // 4
        tab_variation = random.randint(-3, 3)

        points = self._generate_puzzle_path(px, py, s, tab_size + tab_variation)

        draw.polygon(points, fill=255)

        mask = mask.filter(ImageFilter.SMOOTH_MORE)

        return mask

    def _generate_puzzle_path(
        self, px: int, py: int, size: int, tab_size: int
    ) -> list[Tuple[int, int]]:
        points = []
        steps = 60

        x_start = px - size // 2
        y_start = py - size // 2
        half = size // 2

        top_tab = random.choice([True, False])
        right_tab = random.choice([True, False])
        bottom_tab = random.choice([True, False])
        left_tab = random.choice([True, False])

        for i in range(steps + 1):
            t = i / steps
            x = x_start + t * size
            y = y_start
            if top_tab and 0.3 < t < 0.7:
                offset = math.sin((t - 0.3) / 0.4 * math.pi) * tab_size
                y -= offset
            points.append((int(x), int(y)))

        for i in range(steps + 1):
            t = i / steps
            x = x_start + size
            y = y_start + t * size
            if right_tab and 0.3 < t < 0.7:
                offset = math.sin((t - 0.3) / 0.4 * math.pi) * tab_size
                x += offset
            points.append((int(x), int(y)))

        for i in range(steps + 1):
            t = i / steps
            x = x_start + size - t * size
            y = y_start + size
            if bottom_tab and 0.3 < t < 0.7:
                offset = math.sin((t - 0.3) / 0.4 * math.pi) * tab_size
                y += offset
            points.append((int(x), int(y)))

        for i in range(steps + 1):
            t = i / steps
            x = x_start
            y = y_start + size - t * size
            if left_tab and 0.3 < t < 0.7:
                offset = math.sin((t - 0.3) / 0.4 * math.pi) * tab_size
                x -= offset
            points.append((int(x), int(y)))

        return points

    def _extract_puzzle_piece(
        self,
        background: Image.Image,
        mask: Image.Image,
        px: int,
        py: int,
    ) -> Image.Image:
        s = self.puzzle_size
        margin = s // 2 + 10

        piece = Image.new("RGBA", (s + margin * 2, s + margin * 2), (0, 0, 0, 0))

        bg_copy = background.copy()
        r, g, b, _ = bg_copy.split()
        alpha = mask
        bg_copy = Image.merge("RGBA", (r, g, b, alpha))

        crop_x1 = max(0, px - s // 2 - margin)
        crop_y1 = max(0, py - s // 2 - margin)
        crop_x2 = min(self.width, px + s // 2 + margin)
        crop_y2 = min(self.height, py + s // 2 + margin)

        cropped = bg_copy.crop((crop_x1, crop_y1, crop_x2, crop_y2))

        piece_w = crop_x2 - crop_x1
        piece_h = crop_y2 - crop_y1
        piece = Image.new("RGBA", (piece_w, piece_h), (0, 0, 0, 0))
        piece.paste(cropped, (0, 0))

        piece = self._add_puzzle_border(piece, px - crop_x1, py - crop_y1, s)

        shadow = Image.new("RGBA", (piece_w, piece_h), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_points = self._generate_puzzle_path(px - crop_x1, py - crop_y1, s, s // 4)
        shadow_offset_points = [(x + 2, y + 2) for x, y in shadow_points]
        shadow_draw.polygon(shadow_offset_points, fill=(0, 0, 0, 60))

        composite = Image.new("RGBA", (piece_w, piece_h), (0, 0, 0, 0))
        composite = Image.alpha_composite(composite, shadow)
        composite = Image.alpha_composite(composite, piece)

        return composite

    def _add_puzzle_border(
        self, piece: Image.Image, cx: int, cy: int, size: int
    ) -> Image.Image:
        draw = ImageDraw.Draw(piece)
        points = self._generate_puzzle_path(cx, cy, size, size // 4)
        if len(points) >= 2:
            draw.line(points, fill=(255, 255, 255, 180), width=2)
        return piece

    def _cut_hole(
        self,
        background: Image.Image,
        mask: Image.Image,
        px: int,
        py: int,
    ) -> Image.Image:
        s = self.puzzle_size
        margin = s // 2 + 10

        hole_overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        hole_draw = ImageDraw.Draw(hole_overlay)

        points = self._generate_puzzle_path(px, py, s, s // 4)
        hole_draw.polygon(points, fill=(0, 0, 0, 160))

        background = Image.alpha_composite(background, hole_overlay)

        border_overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        border_draw = ImageDraw.Draw(border_overlay)
        if len(points) >= 2:
            border_draw.line(points, fill=(0, 0, 0, 100), width=2)
            inner_points = self._generate_puzzle_path(px, py, s - 2, s // 4 - 1)
            if len(inner_points) >= 2:
                border_draw.line(inner_points, fill=(255, 255, 255, 60), width=1)

        background = Image.alpha_composite(background, border_overlay)

        return background

    def _add_hole_shadow(
        self, background: Image.Image, px: int, py: int
    ) -> Image.Image:
        s = self.puzzle_size
        shadow_overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_overlay)

        points = self._generate_puzzle_path(px + 2, py + 2, s, s // 4)
        shadow_draw.polygon(points, fill=(0, 0, 0, 40))

        background = Image.alpha_composite(background, shadow_overlay)
        return background

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
    def _image_to_b64(img: Image.Image) -> str:
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode("utf-8")


captcha_generator = CaptchaGenerator()
