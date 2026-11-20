"""Exportación visual de las seis láminas verificadas del deck editable de Spaces.

Fallback cuando el exportador PDF nativo no tiene fuentes embebibles registradas.
Los objetos editables se conservan en el deck de origen. No reconstruye su contenido.
"""
import argparse
from pathlib import Path

from reportlab.pdfgen import canvas

parser=argparse.ArgumentParser()
parser.add_argument('render_dir',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
target=root/'output/entrega/EP3_Presentacion_EquipoIndividual.pdf'
c=canvas.Canvas(str(target),pagesize=(960,540))
c.setTitle('EP3 Preflop Six Max Presentación')
c.setAuthor('Vicente Hueichapan')
for i in range(1,7):
    image=args.render_dir/f'slide-{i}.png'
    if not image.is_file():raise FileNotFoundError(image)
    c.drawImage(str(image),0,0,width=960,height=540)
    c.showPage()
c.save()
print(target)
