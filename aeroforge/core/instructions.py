def build_instructions(design: dict) -> list[str]:
    return [
        'Fold sheet in half lengthwise and reopen.',
        'Form nose triangle and lock layers tightly.',
        f"Set wingspan near {design['wingspan_mm']:.1f} mm.",
        f"Tune wing angle to {design['wing_angle_deg']:.2f} deg.",
        f"Tune camber around {design['camber_mm']:.2f} mm.",
    ]
