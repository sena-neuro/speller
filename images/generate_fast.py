import os
os.environ["NUMBA_THREADING_LAYER"] = "workqueue"

import argparse
import json
import math
import time
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from numba import njit, prange

# ==========================================
# 0. CONSTANTS & MAPPINGS
# ==========================================

KEYS = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "space",
    "dot",
    "comma",
    "question",
    "backspace",
    "clear",
]

KEY_MAPPING = {
    "space": "􁁺",
    "dot": ".",
    "comma": ",",
    "colon": ":",
    "question": "?",
    "backspace": "􁂈",
    "clear": "􁝀",
}

# ==========================================
# 1. PHYSICAL CONFIGURATION
# ==========================================


class MonitorConfig:
    def __init__(self, distance_cm, width_cm, resolution_x_px):
        self.distance = distance_cm
        self.width = width_cm
        self.res_x = resolution_x_px
        self.px_per_cm = self.res_x / self.width
        self.ppd = self.distance * math.tan(math.radians(1)) * self.px_per_cm

    def deg2px(self, deg):
        return int(round(deg * self.ppd))

    def deg2px_float(self, deg):
        return deg * self.ppd


MONITOR = MonitorConfig(distance_cm=60, width_cm=53, resolution_x_px=1920)
OUTPUT_ROOT = Path() / "images"
DB_PATH = OUTPUT_ROOT / "stimuli_db.json"

# ==========================================
# 2. OPTIMIZED MATH (NUMBA JIT)
# ==========================================


@njit(fastmath=True, parallel=True)
def lab2rgb_fast(l_layer, a_layer, b_layer):
    h, w = l_layer.shape
    rgb_out = np.empty((h, w, 3), dtype=np.uint8)

    inv_116 = 1.0 / 116.0
    inv_500 = 1.0 / 500.0
    inv_200 = 1.0 / 200.0

    for i in prange(h):
        for j in range(w):
            L = l_layer[i, j]
            A = a_layer[i, j]
            B = b_layer[i, j]

            y = (L + 16.0) * inv_116
            x = A * inv_500 + y
            z = y - B * inv_200

            if x > 0.2068965517:
                x_xyz = (x * x * x) * 0.95047
            else:
                x_xyz = ((x - 0.1379310345) / 7.787) * 0.95047

            if y > 0.2068965517:
                y_xyz = (y * y * y) * 1.00000
            else:
                y_xyz = ((y - 0.1379310345) / 7.787) * 1.00000

            if z > 0.2068965517:
                z_xyz = (z * z * z) * 1.08883
            else:
                z_xyz = ((z - 0.1379310345) / 7.787) * 1.08883

            r_lin = x_xyz * 3.2406 + y_xyz * -1.5372 + z_xyz * -0.4986
            g_lin = x_xyz * -0.9689 + y_xyz * 1.8758 + z_xyz * 0.0415
            b_lin = x_xyz * 0.0557 + y_xyz * -0.2040 + z_xyz * 1.0570

            if r_lin > 0.0031308:
                r = 1.055 * (r_lin ** (1.0 / 2.4)) - 0.055
            else:
                r = 12.92 * r_lin

            if g_lin > 0.0031308:
                g = 1.055 * (g_lin ** (1.0 / 2.4)) - 0.055
            else:
                g = 12.92 * g_lin

            if b_lin > 0.0031308:
                b = 1.055 * (b_lin ** (1.0 / 2.4)) - 0.055
            else:
                b = 12.92 * b_lin

            if r < 0.0:
                r = 0.0
            elif r > 1.0:
                r = 1.0
            if g < 0.0:
                g = 0.0
            elif g > 1.0:
                g = 1.0
            if b < 0.0:
                b = 0.0
            elif b > 1.0:
                b = 1.0

            rgb_out[i, j, 0] = int(r * 255.0)
            rgb_out[i, j, 1] = int(g * 255.0)
            rgb_out[i, j, 2] = int(b * 255.0)

    return rgb_out


@njit(fastmath=True)
def generate_gabor_patch_fast(
    size_px, theta, lamda, gamma, contrast, phi, r_plateau, r_cutoff
):
    half_w = size_px // 2
    out = np.zeros((size_px, size_px), dtype=np.float64)
    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    two_pi_lambda = 2.0 * np.pi / lamda

    for i in range(size_px):
        y = i - half_w
        for j in range(size_px):
            x = j - half_w
            x_theta = x * cos_theta + y * sin_theta
            y_theta = -x * sin_theta + y * cos_theta
            radius = np.sqrt(x_theta**2 + (gamma * y_theta) ** 2)

            env_val = 0.0
            if radius <= r_plateau:
                env_val = 1.0
            elif radius < r_cutoff:
                if r_cutoff > r_plateau:
                    fade_progress = (radius - r_plateau) / (r_cutoff - r_plateau)
                    env_val = 0.5 * (1.0 + np.cos(np.pi * fade_progress))

            if env_val > 0.0:
                carrier = np.cos(two_pi_lambda * x_theta + phi)
                out[i, j] = env_val * carrier * contrast
    return out


def generate_layout_data(n_patches, img_size_px, patch_radius_px, min_dist_px):
    positions = []
    max_attempts = 50000
    min_xy = patch_radius_px
    max_xy = img_size_px - patch_radius_px
    rng = np.random.default_rng()

    for _ in range(max_attempts):
        if len(positions) >= n_patches:
            break
        cand_x = rng.uniform(min_xy, max_xy)
        cand_y = rng.uniform(min_xy, max_xy)
        collision = False
        if positions:
            pos_arr = np.array(positions)
            dists = np.sqrt(
                (pos_arr[:, 0] - cand_x) ** 2 + (pos_arr[:, 1] - cand_y) ** 2
            )
            if np.any(dists < min_dist_px):
                collision = True

        if not collision:
            positions.append((cand_x, cand_y))

    actual_n = len(positions)
    layout_data = []
    if actual_n > 0:
        thetas = np.linspace(0, np.pi, actual_n, endpoint=False)
        step = np.pi / actual_n
        jitter = rng.uniform(-step / 4, step / 4, size=actual_n)
        thetas += jitter
        rng.shuffle(thetas)
        for i in range(actual_n):
            layout_data.append(
                {
                    "x": float(positions[i][0]),
                    "y": float(positions[i][1]),
                    "theta": float(thetas[i]),
                }
            )
    return layout_data, actual_n


# ==========================================
# 3. DATABASE MANAGEMENT (PURE JSON - NO PANDAS)
# ==========================================


class StimuliDB:
    def __init__(self, path):
        self.path = path

    def load_data(self):
        if not self.path.exists():
            return []
        with open(self.path, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def save_entry(self, entry_dict):
        data = self.load_data()
        data.append(entry_dict)
        with open(self.path, "w") as f:
            json.dump(data, f, indent=4)

    def get_layouts(self, query=None, latest_only=False):
        data = self.load_data()
        if not data:
            raise ValueError("Database is empty.")

        # Filter Logic
        results = []
        if query:
            # Simple Python eval to replace Pandas query
            # We flatten the dict for the eval context
            for item in data:
                flat_ctx = item.copy()
                if "params" in flat_ctx:
                    flat_ctx.update(flat_ctx.pop("params"))
                if "structure_results" in flat_ctx:
                    flat_ctx.update(flat_ctx.pop("structure_results"))

                try:
                    # ALLOWS: "n_patches_actual == 8"
                    if eval(query, {"__builtins__": None}, flat_ctx):
                        results.append(item)
                except Exception:
                    pass
        else:
            results = data

        if not results:
            print(f"No layouts found.")
            return []

        # Sort by timestamp (assuming text sort works for ISO dates)
        results.sort(key=lambda x: x["timestamp"])

        if latest_only:
            return [results[-1]]

        print(f"Found {len(results)} matching layouts.")
        return results


# ==========================================
# 4. ACTIONS
# ==========================================


def action_layout(args):
    print("--- GENERATING LAYOUT ---")
    img_size_px = MONITOR.deg2px(args.image_size_deg)
    r_cutoff_px = MONITOR.deg2px_float(args.r_cutoff_deg)
    min_dist_px = MONITOR.deg2px_float(args.min_dist_deg)

    layout_data, count = generate_layout_data(
        args.n_patches, img_size_px, r_cutoff_px, min_dist_px
    )

    entry = {
        "id": f"layout_{uuid.uuid4().hex[:8]}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "params": {
            "n_patches_requested": args.n_patches,
            "n_patches_actual": count,
            "image_size_deg": args.image_size_deg,
            "image_size_px": img_size_px,
            "layout_r_cutoff_deg": args.r_cutoff_deg,
            "layout_min_dist_deg": args.min_dist_deg,
        },
        "structure_results": {
            "count": count,
            "img_size_px": img_size_px,
        },
        "patches": layout_data,
    }

    db = StimuliDB(DB_PATH)
    db.save_entry(entry)
    print(f"Saved Layout ID: {entry['id']} with {count} patches.")


def save_image_task(img, path):
    img.save(path, compress_level=1)


def action_render(args):
    print("--- RENDERING BATCH (Optimized Numba + No Pandas) ---")
    db = StimuliDB(DB_PATH)

    if args.query:
        layouts = db.get_layouts(query=args.query)
    elif args.latest:
        layouts = db.get_layouts(latest_only=True)
    else:
        # Default: Match latest entry params
        all_data = db.load_data()
        if not all_data:
            return
        all_data.sort(key=lambda x: x["timestamp"])
        latest = all_data[-1]

        # Filter by params of latest
        layouts = []
        for item in all_data:
            if item.get("params") == latest.get("params"):
                layouts.append(item)

    if not layouts:
        return

    r_plateau_px = MONITOR.deg2px_float(args.r_plateau_deg)
    r_cutoff_px = MONITOR.deg2px_float(args.r_cutoff_deg)
    lambda_px = MONITOR.deg2px_float(args.lambda_deg)

    gamma_scale = 1.0 / min(args.gamma, 1.0)
    max_radius_px = r_cutoff_px * gamma_scale
    patch_box_px = int(math.ceil(max_radius_px * 2.2))
    if patch_box_px % 2 != 0:
        patch_box_px += 1

    out_dir = OUTPUT_ROOT / "grating"
    out_dir.mkdir(parents=True, exist_ok=True)

    meta = {k: v for k, v in vars(args).items() if k != "command"}
    with open(out_dir / "render_params.json", "w") as f:
        json.dump(meta, f, indent=4)

    font_px = MONITOR.deg2px(args.font_size_deg)
    try:
        font = ImageFont.truetype("SF-Pro-Display-Semibold.otf", font_px)
    except:
        font = ImageFont.load_default()
    debug_font = ImageFont.load_default()

    print("Compiling JIT functions...")
    # Pre-warm
    _ = lab2rgb_fast(np.ones((10, 10)) * 50.0, np.zeros((10, 10)), np.zeros((10, 10)))
    _ = generate_gabor_patch_fast(32, 0.0, 10.0, 1.0, 1.0, 0.0, 5.0, 10.0)
    print("Compilation complete.")

    io_pool = ThreadPoolExecutor(max_workers=4)
    t0 = time.time()
    total_imgs = 0

    for layout_idx, layout in enumerate(layouts, start=1):
        patches = layout["patches"]
        img_size_px = layout["structure_results"]["img_size_px"]

        # A. Background
        canvas_l = np.full((img_size_px, img_size_px), 50.0, dtype="float64")
        canvas_a = np.zeros((img_size_px, img_size_px), dtype="float64")
        canvas_b = np.zeros((img_size_px, img_size_px), dtype="float64")
        l_diff = args.lab_l - 50.0

        for p in patches:
            cx, cy, theta = p["x"], p["y"], p["theta"]
            gabor_signal = generate_gabor_patch_fast(
                patch_box_px,
                theta,
                lambda_px,
                args.gamma,
                args.contrast,
                args.phase,
                r_plateau_px,
                r_cutoff_px,
            )
            x_tl = int(cx - patch_box_px // 2)
            y_tl = int(cy - patch_box_px // 2)
            h, w = gabor_signal.shape
            x_end, y_end = x_tl + w, y_tl + h

            g_y0, g_y1 = 0, h
            g_x0, g_x1 = 0, w
            c_y0, c_y1 = y_tl, y_end
            c_x0, c_x1 = x_tl, x_end

            if c_y0 < 0:
                g_y0 += -c_y0
                c_y0 = 0
            if c_x0 < 0:
                g_x0 += -c_x0
                c_x0 = 0
            if c_y1 > img_size_px:
                g_y1 -= c_y1 - img_size_px
                c_y1 = img_size_px
            if c_x1 > img_size_px:
                g_x1 -= c_x1 - img_size_px
                c_x1 = img_size_px

            if c_y1 > c_y0 and c_x1 > c_x0:
                patch_slice = gabor_signal[g_y0:g_y1, g_x0:g_x1]
                canvas_l[c_y0:c_y1, c_x0:c_x1] += patch_slice * l_diff
                canvas_a[c_y0:c_y1, c_x0:c_x1] += patch_slice * args.lab_a
                canvas_b[c_y0:c_y1, c_x0:c_x1] += patch_slice * args.lab_b

        # B. Convert
        rgb_uint8 = lab2rgb_fast(canvas_l, canvas_a, canvas_b)
        base_img = Image.fromarray(rgb_uint8, mode="RGB")

        # C. Stamp
        for key_name in KEYS:
            display_char = KEY_MAPPING.get(key_name, key_name)
            img_copy = base_img.copy()
            draw = ImageDraw.Draw(img_copy)
            draw.text(
                (img_size_px / 2, img_size_px / 2),
                display_char,
                font=font,
                fill="white",
                anchor="mm",
            )

            if args.debug:
                draw.text(
                    (img_size_px - 10, 10),
                    str(layout_idx),
                    font=debug_font,
                    fill="black",
                    anchor="rt",
                )

            fname = f"{key_name}_grating_{layout_idx}.png"
            io_pool.submit(save_image_task, img_copy, out_dir / fname)
            total_imgs += 1

    io_pool.shutdown(wait=True)
    dt = time.time() - t0
    print(
        f"Batch complete. {total_imgs} images in {dt:.2f}s ({dt/total_imgs*1000:.2f}ms per image)"
    )


def action_solid(args):
    img_size_px = MONITOR.deg2px(args.image_size_deg)
    font_px = MONITOR.deg2px(args.font_size_deg)
    try:
        font = ImageFont.truetype("SF-Pro-Display-Semibold.otf", font_px)
    except:
        font = ImageFont.load_default()

    out_dir = OUTPUT_ROOT / args.color
    out_dir.mkdir(parents=True, exist_ok=True)

    io_pool = ThreadPoolExecutor(max_workers=4)
    for key_name in KEYS:
        img = Image.new("RGB", (img_size_px, img_size_px), color=args.color)
        display_char = KEY_MAPPING.get(key_name, key_name)
        draw = ImageDraw.Draw(img)
        draw.text(
            (img_size_px / 2, img_size_px / 2),
            display_char,
            font=font,
            fill="white",
            anchor="mm",
        )
        fname = f"{key_name}_{args.color}.png"
        io_pool.submit(save_image_task, img, out_dir / fname)
    io_pool.shutdown(wait=True)


def main():
    parser = argparse.ArgumentParser(description="Fast Gabor Stimuli Generator")
    parser.add_argument("--debug", action="store_true", help="Draw index")

    subparsers = parser.add_subparsers(dest="command", required=True)

    p_solid = subparsers.add_parser("solid")
    p_solid.add_argument("--color", type=str, default="gray")
    p_solid.add_argument("--font_size_deg", type=float, default=1.0)
    p_solid.add_argument("--image_size_deg", type=float, default=4.0)

    p_layout = subparsers.add_parser("layout")
    p_layout.add_argument("--n_patches", type=int, default=8)
    p_layout.add_argument("--image_size_deg", type=float, default=4.0)
    p_layout.add_argument("--r_cutoff_deg", type=float, default=0.5)
    p_layout.add_argument("--min_dist_deg", type=float, default=0.9)

    p_render = subparsers.add_parser("render")
    p_render.add_argument("--query", type=str)
    p_render.add_argument("--latest", action="store_true", default=True)

    p_render.add_argument("--font_size_deg", type=float, default=1.0)
    p_render.add_argument("--contrast", type=float, default=0.6)
    p_render.add_argument("--lambda_deg", type=float, default=0.2)
    p_render.add_argument("--gamma", type=float, default=0.6)
    p_render.add_argument("--phase", type=float, default=np.pi / 2)
    p_render.add_argument("--lab_l", type=float, default=100.0)
    p_render.add_argument("--lab_a", type=float, default=0.0)
    p_render.add_argument("--lab_b", type=float, default=0.0)
    p_render.add_argument("--r_plateau_deg", type=float, default=0.15)
    p_render.add_argument("--r_cutoff_deg", type=float, default=0.5)

    args = parser.parse_args()

    if args.command == "layout":
        action_layout(args)
    elif args.command == "render":
        action_render(args)
    elif args.command == "solid":
        action_solid(args)


if __name__ == "__main__":
    main()
