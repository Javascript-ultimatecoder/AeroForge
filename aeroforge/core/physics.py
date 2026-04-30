import numpy as np

def simulate(d: dict) -> dict:
    rho = 1.225
    v = 8.0
    span = float(d['wingspan_mm'])
    camber = float(d['camber_mm'])
    angle = float(d['wing_angle_deg'])
    balance = float(d['center_of_mass_pct'])

    area = span * 0.0001
    reynolds = (rho * v * (span * 0.001)) / 1.81e-5
    lift_coeff = 0.08 + angle * 0.09 + camber * 0.15
    drag_coeff = 0.02 + angle**2 * 0.006
    lift = 0.5 * rho * v**2 * area * lift_coeff
    drag = 0.5 * rho * v**2 * area * drag_coeff
    stability = max(0.1, 1 - abs(balance - 0.33) * 1.8)
    glide = lift / (drag + 1e-6)
    total = glide * stability * (np.log(reynolds + 1) / 10)
    return {'lift': float(lift), 'drag': float(drag), 'stability': float(stability), 'reynolds': float(reynolds), 'total_score': float(total)}
