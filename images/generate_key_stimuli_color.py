import argparse
import json
import math
import time
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 0. CONSTANTS & MAPPINGS
# ==========================================

KEYS = [
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z",
    "space", "dot", "comma", "question", "backspace", "clear",
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
        # 1 deg = dist * tan(1 deg)
        self.ppd = self.distance * math.tan(math.radians(1)) * self.px_per_cm

    def deg2px(self, deg):
        return int(round(deg * self.ppd))

    def deg2px_float(self, deg):
        return deg * self.ppd

# System Setup
MONITOR = MonitorConfig(distance_cm=60, width_cm=53, resolution_x_px=1920)
OUTPUT_ROOT = Path() / 'images'
DB_PATH = OUTPUT_ROOT / "stimuli_db.json"

# ==========================================
# 2. MATH & GEOMETRY
# ==========================================
def lab2rgb(l_layer, a_layer, b_layer):
    """
    Converts L*a*b* (floats) to sRGB (uint8) using standard D65 illuminant math.
    This avoids Pillow's 8-bit quantization issues.
    """
    # 1. Domain Setup
    y = (l_layer + 16.0) / 116.0
    x = a_layer / 500.0 + y
    z = y - b_layer / 200.0

    # 2. XYZ Calculation (using D65 Ref: 95.047, 100.000, 108.883)
    def ref(t):
        # if t > (6/29) -> t^3, else linear
        mask = t > 0.2068965517
        res = np.zeros_like(t)
        res[mask] = np.power(t[mask], 3.0)
        res[~mask] = (t[~mask] - 0.1379310345) / 7.787
        return res

    x_xyz = ref(x) * 0.95047
    y_xyz = ref(y) * 1.00000
    z_xyz = ref(z) * 1.08883

    # 3. RGB Linear Calculation
    # sRGB D65 Matrix
    r_lin = x_xyz *  3.2406 + y_xyz * -1.5372 + z_xyz * -0.4986
    g_lin = x_xyz * -0.9689 + y_xyz *  1.8758 + z_xyz *  0.0415
    b_lin = x_xyz *  0.0557 + y_xyz * -0.2040 + z_xyz *  1.0570

    # 4. Gamma Correction (sRGB transfer function)
    def gamma(c):
        mask = c > 0.0031308
        res = np.zeros_like(c)
        res[mask] = 1.055 * np.power(c[mask], (1.0 / 2.4)) - 0.055
        res[~mask] = 12.92 * c[~mask]
        return res

    r = gamma(r_lin)
    g = gamma(g_lin)
    b = gamma(b_lin)

    # 5. Clip and Scale
    rgb = np.dstack((r, g, b))
    rgb = np.clip(rgb, 0.0, 1.0)
    return (rgb * 255.0).astype("uint8")

def generate_gabor_patch(size_px, theta, px_params):
    """
    Generates a Grating with a Raised Cosine envelope.
    No sigma is used, only explicit radii.
    """
    lamda = px_params["lambda_px"]
    gamma = px_params["gamma"]
    contrast = px_params["contrast"]
    phi = px_params["phase"]
    
    r_plateau = px_params["r_plateau_px"]
    r_cutoff = px_params["r_cutoff_px"]

    # Grid centered at 0
    half_w = size_px // 2
    y, x = np.meshgrid(
        np.arange(-half_w, size_px - half_w),
        np.arange(-half_w, size_px - half_w)
    )

    # Rotation Matrix
    x_theta = x * np.cos(theta) + y * np.sin(theta)
    y_theta = -x * np.sin(theta) + y * np.cos(theta)

    # 1. Calculate Elliptical Radius (preserves gamma aspect ratio)
    # r is the distance from center, stretched by gamma on the y-axis
    radius = np.sqrt(x_theta**2 + (gamma * y_theta)**2)

    # 2. Compute Raised Cosine Mask
    envelope = np.zeros_like(radius)
    
    # Region A: Center Plateau (Contrast = 1.0)
    mask_plateau = radius <= r_plateau
    envelope[mask_plateau] = 1.0

    # Region B: Cosine Falloff (Transitions from 1.0 to 0.0)
    mask_fade = (radius > r_plateau) & (radius < r_cutoff)
    
    # Map radius to 0..pi range for the cosine function
    if r_cutoff > r_plateau:
        fade_progress = (radius[mask_fade] - r_plateau) / (r_cutoff - r_plateau)
        envelope[mask_fade] = 0.5 * (1 + np.cos(np.pi * fade_progress))
    
    # Region C: Outside is 0.0 by default
    
    # Carrier
    carrier = np.cos(2 * np.pi * x_theta / lamda + phi)
    
    return envelope * carrier * contrast

def generate_layout_data(n_patches, img_size_px, patch_radius_px, min_dist_px):
    """
    Generates random positions (Poisson-like) and stratified orientations.
    """
    positions = []
    max_attempts = 50000
    
    # Bounds (center coordinates)
    # Keep centers away from edge by at least 1 radius
    min_xy = patch_radius_px
    max_xy = img_size_px - patch_radius_px
    
    # 1. Position Sampling
    for _ in range(max_attempts):
        if len(positions) >= n_patches:
            break
            
        cand_x = np.random.uniform(min_xy, max_xy)
        cand_y = np.random.uniform(min_xy, max_xy)
        
        collision = False
        for (ex_x, ex_y) in positions:
            dist = np.sqrt((cand_x - ex_x)**2 + (cand_y - ex_y)**2)
            if dist < min_dist_px:
                collision = True
                break
        
        if not collision:
            positions.append((cand_x, cand_y))
            
    # 2. Orientation Stratification
    actual_n = len(positions)
    if actual_n > 0:
        thetas = np.linspace(0, np.pi, actual_n, endpoint=False)
        step = np.pi / actual_n
        # Jitter +/- 25% of the step
        jitter = np.random.uniform(-step/4, step/4, size=actual_n)
        thetas += jitter
        np.random.shuffle(thetas)
    else:
        thetas = []

    # 3. Combine
    layout_data = []
    for i in range(actual_n):
        layout_data.append({
            "x": float(positions[i][0]),
            "y": float(positions[i][1]),
            "theta": float(thetas[i])
        })
        
    return layout_data, actual_n

# ==========================================
# 3. DATABASE MANAGEMENT (PANDAS)
# ==========================================

class StimuliDB:
    def __init__(self, path):
        self.path = path

    def load_df(self):
        if not self.path.exists():
            return pd.DataFrame()
        with open(self.path, "r") as f:
            data = json.load(f)
        return pd.json_normalize(data)

    def save_entry(self, entry_dict):
        current_data = []
        if self.path.exists():
            with open(self.path, "r") as f:
                try:
                    current_data = json.load(f)
                except json.JSONDecodeError:
                    pass
        current_data.append(entry_dict)
        with open(self.path, "w") as f:
            json.dump(current_data, f, indent=4)

    def get_layouts(self, query=None, latest_only=False):
        df = self.load_df()
        
        if df.empty:
            raise ValueError("Database is empty. Run 'layout' mode first.")

        if query:
            try:
                df_clean = df.rename(columns=lambda x: x.replace("params.", ""))
                result = df_clean.query(query)
            except Exception as e:
                raise ValueError(f"Query Error: {e}")
                
            if result.empty:
                print(f"No layouts found matching: {query}")
                return []
            result = result.sort_values("timestamp")
        else:
            result = df.sort_values("timestamp")

        if latest_only:
            result = result.iloc[[-1]]

        target_ids = result["id"].tolist()
        
        with open(self.path, "r") as f:
            raw_data = json.load(f)
        
        raw_map = {item["id"]: item for item in raw_data}
        
        final_list = []
        for tid in target_ids:
            if tid in raw_map:
                final_list.append(raw_map[tid])
                
        print(f"Found {len(final_list)} matching layouts.")
        return final_list

# ==========================================
# 4. ACTION: LAYOUT
# ==========================================

def action_layout(args):
    print("--- GENERATING LAYOUT ---")
    
    img_size_px = MONITOR.deg2px(args.image_size_deg)
    
    # Use cutoff for spacing logic, even though visualization changes later
    r_cutoff_px = MONITOR.deg2px_float(args.r_cutoff_deg)
    min_dist_px = MONITOR.deg2px_float(args.min_dist_deg)

    print(f"Target: {args.n_patches} patches within {args.image_size_deg} deg")
    print(f"Spacing: Min dist {args.min_dist_deg} deg (Slot size ~{args.r_cutoff_deg} deg)")
    
    layout_data, count = generate_layout_data(
        args.n_patches, 
        img_size_px, 
        r_cutoff_px, # used as radius for border checks
        min_dist_px
    )

    if count < args.n_patches:
        print(f"Warning: Could only fit {count}/{args.n_patches} patches.")
    
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
        "patches": layout_data
    }
    
    db = StimuliDB(DB_PATH)
    db.save_entry(entry)
    print(f"Saved Layout ID: {entry['id']} with {count} patches.")

# ==========================================
# 5. ACTION: RENDER (BATCH)
# ==========================================

def action_render(args):
    print("--- RENDERING BATCH (High Precision CIE Lab) ---")
    db = StimuliDB(DB_PATH)
    
    # 1. LOAD & SELECT
    df = db.load_df()
    if df.empty:
        print("Database is empty.")
        return

    if args.query:
        layouts = db.get_layouts(query=args.query)
    else:
        df = df.sort_values("timestamp")
        latest_entry = df.iloc[-1]
        param_cols = [c for c in df.columns if c.startswith("params.")]
        condition = True
        for col in param_cols:
            condition = condition & (df[col] == latest_entry[col])
        target_ids = df[condition]["id"].tolist()
        
        with open(DB_PATH, "r") as f:
            raw_data = json.load(f)
        layouts = [item for item in raw_data if item["id"] in target_ids]

    if not layouts:
        return
    
    # 2. Setup Params
    r_plateau_px = MONITOR.deg2px_float(args.r_plateau_deg)
    r_cutoff_px = MONITOR.deg2px_float(args.r_cutoff_deg)
    lambda_px = MONITOR.deg2px_float(args.lambda_deg)
    
    # Ensure box is large enough to capture the soft edge
    gamma_scale = 1.0 / min(args.gamma, 1.0)
    max_radius_px = r_cutoff_px * gamma_scale
    patch_box_px = int(math.ceil(max_radius_px * 2.2))
    # Force even number for cleaner center alignment
    if patch_box_px % 2 != 0: patch_box_px += 1
    
        
    out_dir = OUTPUT_ROOT / 'grating' 
    out_dir.mkdir(parents=True, exist_ok=True)
    
    px_params = {
        "lambda_px": lambda_px,
        "lambda_deg": args.lambda_deg,
        "r_plateau_px": r_plateau_px,
        "r_plateau_deg": args.r_plateau_deg,
        "r_cutoff_px": r_cutoff_px,
        "r_cutoff_deg": args.r_cutoff_deg,
        "patch_box_size_px": patch_box_px,
        "gamma": args.gamma,
        "contrast": args.contrast,
        "phase": args.phase,
    }
    
    meta = {k:v for k,v in vars(args).items() if k != "command"}
    meta["calculated_px_params"] = px_params
    
    with open(out_dir / "render_params.json", "w") as f:
        json.dump(meta, f, indent=4)

    font_px = MONITOR.deg2px(args.font_size_deg)
    try:
        font = ImageFont.truetype("SF-Pro-Display-Semibold.otf", font_px)
    except:
        font = ImageFont.load_default()
    debug_font = ImageFont.load_default()

    print(f"Output Directory: {out_dir}")
    print(f"Processing {len(layouts)} layouts...")

    # 4. Batch Loop
    for i, layout in enumerate(layouts, start=1):
        patches = layout["patches"]
        img_size_px = layout["structure_results"]["img_size_px"]
        
        for key_name in KEYS:
            # --- A. Initialize Canvas (Float64 for precision) ---
            # Background fixed: L=50, a=0, b=0 (Neutral Gray)
            canvas_l = np.full((img_size_px, img_size_px), 50.0, dtype="float64")
            canvas_a = np.zeros((img_size_px, img_size_px), dtype="float64")
            canvas_b = np.zeros((img_size_px, img_size_px), dtype="float64")
            
            display_char = KEY_MAPPING.get(key_name, key_name)
            
            # --- B. Draw Patches ---
            for p in patches:
                cx, cy, theta = p["x"], p["y"], p["theta"]
                
                # Generate Gabor signal (approx -1.0 to +1.0)
                gabor_signal = generate_gabor_patch(patch_box_px, theta, px_params)
                
                # Coords
                x_tl = int(cx - patch_box_px // 2)
                y_tl = int(cy - patch_box_px // 2)
                
                # Dimensions needed for slicing
                h, w = gabor_signal.shape
                
                # Canvas Bounds Logic
                x_end = x_tl + w
                y_end = y_tl + h
                
                # Slice indices for Patch (g_) and Canvas (c_)
                g_y0, g_y1 = 0, h
                g_x0, g_x1 = 0, w
                c_y0, c_y1 = y_tl, y_end
                c_x0, c_x1 = x_tl, x_end
                
                # Clipping checks
                if c_y0 < 0: 
                    g_y0 += -c_y0; c_y0 = 0
                if c_x0 < 0: 
                    g_x0 += -c_x0; c_x0 = 0
                if c_y1 > img_size_px: 
                    g_y1 -= (c_y1 - img_size_px); c_y1 = img_size_px
                if c_x1 > img_size_px: 
                    g_x1 -= (c_x1 - img_size_px); c_x1 = img_size_px
                
                # Apply if valid
                if c_y1 > c_y0 and c_x1 > c_x0:
                    patch_slice = gabor_signal[g_y0:g_y1, g_x0:g_x1]
                    
                    # ACCUMULATE SIGNAL
                    # L now modulates around 50.0 by lab_l
                    canvas_l[c_y0:c_y1, c_x0:c_x1] += patch_slice * (args.lab_l - 50)
                    # Color channels modulate as before
                    canvas_a[c_y0:c_y1, c_x0:c_x1] += patch_slice * args.lab_a
                    canvas_b[c_y0:c_y1, c_x0:c_x1] += patch_slice * args.lab_b

            # --- C. Convert Lab -> RGB (High Precision) ---
            rgb_uint8 = lab2rgb(canvas_l, canvas_a, canvas_b)
            img = Image.fromarray(rgb_uint8, mode="RGB")
            
            # --- D. Overlays ---
            draw = ImageDraw.Draw(img)
            draw.text((img_size_px/2, img_size_px/2), display_char, font=font, fill="white", anchor="mm")
            
            if args.debug:
                draw.text((img_size_px - 10, 10), str(i), font=debug_font, fill="black", anchor="rt")

            fname = f"{key_name}_grating_{i}.png"
            img.save(out_dir / fname)
            
    print(f"Batch complete. Generated {len(layouts) * len(KEYS)} images.")


def action_solid(args):
    img_size_px = MONITOR.deg2px(args.image_size_deg)
    font_px = MONITOR.deg2px(args.font_size_deg)
    try:
        font = ImageFont.truetype("SF-Pro-Display-Semibold.otf", font_px)
    except:
        font = ImageFont.load_default()

    out_dir = OUTPUT_ROOT / args.color
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output Directory: {out_dir}")   

    for key_name in KEYS:
        img = Image.new("RGB", (img_size_px, img_size_px), color=args.color)
        display_char = KEY_MAPPING.get(key_name, key_name)
        draw = ImageDraw.Draw(img)
        draw.text((img_size_px/2, img_size_px/2), display_char, font=font, fill="white", anchor="mm")

        fname = f"{key_name}_{args.color}.png"
        img.save(out_dir / fname)


# ==========================================
# 6. MAIN CLI PARSER
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Gabor Patch Stimuli Generator")
    parser.add_argument("--debug", action="store_true", help="Draw index")
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    p_solid = subparsers.add_parser("solid", help="Render solid keys")
    p_solid.add_argument("--color", type=str, default="gray", help="Color of the key background")
    p_solid.add_argument("--font_size_deg", type=float, default=1.0)
    p_solid.add_argument("--image_size_deg", type=float, default=4.0, help="FOV size in degrees")

    # --- LAYOUT COMMAND ---
    p_layout = subparsers.add_parser("layout", help="Generate positions and orientations")
    p_layout.add_argument("--n_patches", type=int, default=8, help="Number of patches")
    p_layout.add_argument("--image_size_deg", type=float, default=4.0, help="FOV size in degrees")
    p_layout.add_argument("--r_cutoff_deg", type=float, default=0.5, help="Outer radius of the patch for layout spacing")
    p_layout.add_argument("--min_dist_deg", type=float, default=0.9, help="Minimum distance between centers")

    # --- RENDER COMMAND ---
    p_render = subparsers.add_parser("render", help="Render images from DB")
    p_render.add_argument("--query", type=str, help="Pandas query (e.g. 'n_patches == 8')")
    p_render.add_argument("--latest", action="store_true", help="Use latest layout (default)")
    
    # Visual Params
    p_render.add_argument("--font_size_deg", type=float, default=1.0)
    p_render.add_argument("--contrast", type=float, default=0.6)
    p_render.add_argument("--lambda_deg", type=float, default=0.2, help="Spatial wavelength (lower freq = higher num)")
    p_render.add_argument("--gamma", type=float, default=0.6, help="Aspect ratio")
    p_render.add_argument("--phase", type=float, default=np.pi/2)
   
    # Color Params (CIE Lab)
    p_render.add_argument("--lab_l", type=float, default=100.0, help="Target L value")
    p_render.add_argument("--lab_a", type=float, default=0.0, help="Target a value")
    p_render.add_argument("--lab_b", type=float, default=0.0, help="Target b value")

    # Radius Params (No more sigma/box size)
    p_render.add_argument("--r_plateau_deg", type=float, default=0.15, help="Radius of full contrast")
    p_render.add_argument("--r_cutoff_deg", type=float, default=0.5, help="Radius of zero contrast / invisible")

    args = parser.parse_args()

    if args.command == "layout":
        action_layout(args)
    elif args.command == "render":
        action_render(args)
    elif args.command == "solid":
        action_solid(args)

if __name__ == "__main__":
    main()
