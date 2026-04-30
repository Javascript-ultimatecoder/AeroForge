from ai.vision import detect_plane

def analyze_design(file_bytes, filename: str, mode: str):
    vision = detect_plane(file_bytes)
    baseline = {
        'name': filename,
        'mode': mode,
        'wingspan_mm': 190.0 + min(30, vision.get('contours', 0) * 0.8),
        'wing_angle_deg': 4.0,
        'center_of_mass_pct': 0.33,
        'camber_mm': 0.6,
    }
    return {'vision': vision, 'baseline_design': baseline}
