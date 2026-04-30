import matplotlib.pyplot as plt
from datetime import datetime
from config import OUTPUT_DIR

def generate_graph(history):
    scores = [h['metrics']['total_score'] for h in history]
    plt.figure(figsize=(6,3))
    plt.plot(scores)
    plt.title('Optimization Score by Generation')
    plt.xlabel('Generation')
    plt.ylabel('Score')
    path = OUTPUT_DIR / f"graph_{datetime.now().timestamp()}.png"
    plt.tight_layout(); plt.savefig(path); plt.close()
    return str(path)
