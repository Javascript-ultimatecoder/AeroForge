import random
from core.physics import simulate

POP = 30
GEN = 50

def mutate(d):
    d = d.copy()
    d['wingspan_mm'] += random.uniform(-6, 6)
    d['camber_mm'] += random.uniform(-0.2, 0.2)
    d['wing_angle_deg'] += random.uniform(-0.7, 0.7)
    d['center_of_mass_pct'] = min(0.5, max(0.1, d['center_of_mass_pct'] + random.uniform(-0.02, 0.02)))
    return d

def crossover(a, b):
    return {k: (a[k] + b[k]) / 2 if isinstance(a[k], float) else a[k] for k in a}

def optimize_design(base):
    population = [mutate(base) for _ in range(POP)]
    history = []
    scored = []
    for _ in range(GEN):
        scored = [(p, simulate(p)) for p in population]
        scored.sort(key=lambda x: x[1]['total_score'], reverse=True)
        best = scored[0]
        history.append(best)
        survivors = [p for p, _ in scored[:10]]
        new_pop = survivors.copy()
        while len(new_pop) < POP:
            a, b = random.sample(survivors, 2)
            new_pop.append(mutate(crossover(a, b)))
        population = new_pop
    best_design, best_metrics = scored[0]
    return {'best_design': best_design, 'best_metrics': best_metrics, 'history': [{'metrics': m} for _, m in history]}
