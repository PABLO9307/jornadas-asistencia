from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

def crear_fondo():
    ancho, alto = letter
    c = canvas.Canvas("fondo_constancia.pdf", pagesize=letter)
    
    # Borde exterior
    c.setStrokeColor(HexColor('#8B0000'))
    c.setLineWidth(8)
    c.rect(20, 20, ancho - 40, alto - 40)
    
    # Título
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(HexColor('#8B0000'))
    c.drawCentredString(ancho/2, alto - 150, "CONSTANCIA")
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(ancho/2, alto - 185, "DE PARTICIPACIÓN")
    
    # Texto fijo
    c.setFont("Helvetica", 14)
    c.setFillColor(HexColor('#000000'))
    c.drawCentredString(ancho/2, alto - 260, "El comité organizador certifica que")
    
    c.setFont("Helvetica", 14)
    c.drawCentredString(ancho/2, alto - 480, "ha participado en la conferencia:")
    
    # Línea de firma
    c.line(ancho/2 - 150, alto - 650, ancho/2 - 30, alto - 650)
    c.line(ancho/2 + 30, alto - 650, ancho/2 + 150, alto - 650)
    c.setFont("Helvetica", 10)
    c.drawCentredString(ancho/2 - 90, alto - 670, "Coordinación Académica")
    c.drawCentredString(ancho/2 + 90, alto - 670, "Comité Organizador")
    
    c.save()
    print("✅ fondo_constancia.pdf creado")

if __name__ == "__main__":
    crear_fondo()