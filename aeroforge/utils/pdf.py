from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer
from config import OUTPUT_DIR

def build_pdf(design, metrics, graph):
    path = OUTPUT_DIR / f"report_{metrics['total_score']:.4f}.pdf"
    doc = SimpleDocTemplate(str(path))
    styles = getSampleStyleSheet()
    story = [
        Paragraph('AeroForge v4 Report', styles['Title']), Spacer(1, 10),
        Paragraph(f"Score: {metrics['total_score']:.4f}", styles['BodyText']),
        Paragraph(f"Wingspan: {design['wingspan_mm']:.2f}", styles['BodyText']),
        Paragraph(f"Camber: {design['camber_mm']:.2f}", styles['BodyText']), Spacer(1, 10),
        Image(graph, width=420, height=230),
    ]
    doc.build(story)
    return str(path)
