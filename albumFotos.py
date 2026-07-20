import argparse
import random
import logging
import re
from pathlib import Path
from datetime import datetime
from PIL import Image, ExifTags, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor

# Configuració del logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

class AlbumGenerator:
    def __init__(self, input_folder, output_file, title, show_date, show_time, layouts_str=None):
        self.input_folder = Path(input_folder)
        self.output_file = Path(output_file)
        self.title = title
        self.show_date = show_date
        self.show_time = show_time
        
        self.layouts = self._parse_layouts(layouts_str)
        
        # Paràmetres estètics
        self.page_size = A4
        self.margin = 10
        self.spacing = 5
        self.bg_color = HexColor("#F5F5F0")  # Fons crema/gris suau elegant

    def _parse_layouts(self, layouts_str):
        """
        Interpreta una cadena de text com '2x2,2-3,1-2-1' en una llista de tuples.
        Cada tuple representa una graella. Cada element del tuple és el nombre de fotos per fila.
        Ex: (2, 3) -> Fila superior amb 2 fotos, fila inferior amb 3 fotos.
        """
        if not layouts_str:
            # Si no hi ha preferència, barregem estils molt bonics i asimètrics per defecte.
            # (1,) -> 1 foto molt gran
            # (1, 2, 1) -> 1 a dalt, 2 al mig, 1 a baix
            # (2, 3) -> 2 a dalt, 3 a baix (asimètric)
            return [(1,), (2,), (2, 2), (2, 3), (3, 2), (2, 2, 2), (1,2), (2,1)]
        
        res = []
        for l in layouts_str.split(","):
            l = l.strip()
            if not l: continue
            if 'x' in l.lower():
                # '2x2' -> dues files de dues fotos: (2, 2)
                r, c = map(int, l.lower().split('x'))
                res.append(tuple([c] * r))
            elif '-' in l:
                # '2-3' -> fila 1 amb 2 fotos, fila 2 amb 3 fotos: (2, 3)
                res.append(tuple(map(int, l.split('-'))))
            else:
                # Una sola fila: '3' -> (3,)
                res.append((int(l),))
        
        if not res:
            return [(2, 2), (3, 3, 3)]
        return res
        
    def get_photo_datetime(self, path: Path) -> datetime:
        """Extreu la data del nom del fitxer, de les metadades EXIF o bé de la creació del fitxer."""
        # 1. Comprovar si el nom té el format especial: 2006-11-12_12-20-32...
        match = re.search(r'^(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})', path.name)
        if match:
            try:
                y, m, d, H, M, S = map(int, match.groups())
                return datetime(y, m, d, H, M, S)
            except ValueError:
                pass

        # 2. Metadades EXIF
        try:
            with Image.open(path) as img:
                # A albumInicial s'usa _getexif() que retorna totes les etiquetes de forma plana,
                # incloent 'DateTimeOriginal'. img.getexif() no les inclou al primer nivell.
                exif = getattr(img, "_getexif", lambda: None)()
                    
                if exif:
                    for tag, value in exif.items():
                        tag_name = ExifTags.TAGS.get(tag, tag)
                        if tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
                            try:
                                return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                            except ValueError:
                                continue 
        except Exception as e:
            logging.debug(f"Avís: No s'han pogut llegir les metadades EXIF de {path.name} ({e})")

        # Pla B: st_ctime (data de creació a Windows, com fa albumInicial amb getctime)
        return datetime.fromtimestamp(path.stat().st_ctime)

    def draw_background(self, c, w, h):
        """Dibuixa el color de fons sòlid per a tota la pàgina."""
        c.setFillColor(self.bg_color)
        c.rect(0, 0, w, h, stroke=0, fill=1)

    def generate(self):
        if not self.input_folder.is_dir():
            logging.error(f"No s'ha trobat el directori d'origen: {self.input_folder}")
            return

        valid_extensions = {".jpg", ".jpeg", ".png"}
        photos = [p for p in self.input_folder.iterdir() if p.is_file() and p.suffix.lower() in valid_extensions]

        if not photos:
            logging.warning("No s'han trobat imatges vàlides a la carpeta.")
            return

        # Ordenar les fotos per data de més antigues a més recents
        photo_infos = [(p, self.get_photo_datetime(p)) for p in photos]
        photo_infos.sort(key=lambda x: x[1])

        # --- PRE-CÀLCUL DE PÀGINES I GRAELLES ---
        remaining_photos = list(photo_infos)
        pages = []
        
        while remaining_photos:
            # Busquem layouts que tinguin capacitat igual o inferior a les fotos restants
            valid_layouts = [l for l in self.layouts if sum(l) <= len(remaining_photos)]
            
            if not valid_layouts:
                # Si queden menys fotos que la mida d'una graella, creem un disseny especial per les últimes.
                left = len(remaining_photos)
                if left == 1:
                    layout = (1,)
                elif left == 2:
                    layout = (2,)
                elif left == 3:
                    layout = (1, 2)
                elif left == 4:
                    layout = (2, 2)
                else:
                    layout = (2, left - 2)
            else:
                layout = random.choice(valid_layouts)
                
            capacity = sum(layout)
            page_photos = remaining_photos[:capacity]
            remaining_photos = remaining_photos[capacity:]
            pages.append((layout, page_photos))

        # --- INICI DEL PDF ---
        c = canvas.Canvas(str(self.output_file), pagesize=self.page_size)
        page_w, page_h = self.page_size
        
        # --- PORTADA ---
        self.draw_background(c, page_w, page_h)
        c.setFillColor(HexColor("#333333"))
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(page_w / 2, page_h / 2 + 30, self.title)
        
        first_date = photo_infos[0][1].strftime("%d/%m/%Y")
        last_date = photo_infos[-1][1].strftime("%d/%m/%Y")
        c.setFont("Helvetica-Oblique", 18)
        c.setFillColor(HexColor("#666666"))
        
        if first_date == last_date:
            c.drawCentredString(page_w / 2, page_h / 2 - 10, f"{first_date}")
        else:
            c.drawCentredString(page_w / 2, page_h / 2 - 10, f"De {first_date} a {last_date}")
            
        c.showPage() 
        
        # --- PÀGINES DE FOTOS ---
        text_height = 0
        if self.show_date or self.show_time:
            text_height = 20
            
        polaroid_padding = 4
        shadow_offset = 2

        usable_w = page_w - 2 * self.margin
        usable_h = page_h - 2 * self.margin
        
        for layout, page_photos in pages:
            self.draw_background(c, page_w, page_h)
            
            rows = len(layout)
            # L'alçada de cada fila és uniforme per tota la pàgina
            cell_h = (usable_h - (rows - 1) * self.spacing) / rows
            
            photo_index = 0
            
            # Recorrem les files de la graella asimètrica
            for row_idx, cols_in_row in enumerate(layout):
                # L'amplada de les cel·les varia en funció de quantes fotos hi ha a la fila actual
                cell_w = (usable_w - (cols_in_row - 1) * self.spacing) / cols_in_row
                
                for col_idx in range(cols_in_row):
                    if photo_index >= len(page_photos):
                        break
                        
                    photo_path, dt = page_photos[photo_index]
                    
                    x = self.margin + col_idx * (cell_w + self.spacing)
                    y = page_h - self.margin - (row_idx + 1) * cell_h - row_idx * self.spacing

                    try:
                        with Image.open(photo_path) as im:
                            im = ImageOps.exif_transpose(im)
                            img_reader = ImageReader(im)
                            iw, ih = im.size
                            aspect = iw / ih

                            target_w = cell_w - (polaroid_padding * 2)
                            target_h = cell_h - (polaroid_padding * 2) - text_height

                            if target_w / target_h > aspect:
                                draw_h = target_h
                                draw_w = target_h * aspect
                            else:
                                draw_w = target_w
                                draw_h = target_w / aspect
                            
                            frame_w = draw_w + (polaroid_padding * 2)
                            frame_h = draw_h + (polaroid_padding * 2) + text_height
                            
                            frame_x = x + (cell_w - frame_w) / 2
                            frame_y = y + (cell_h - frame_h) / 2
                            
                            c.setFillColor(HexColor("#D0D0D0"))
                            c.rect(frame_x + shadow_offset, frame_y - shadow_offset, frame_w, frame_h, stroke=0, fill=1)
                            
                            c.setFillColor(HexColor("#FFFFFF"))
                            c.rect(frame_x, frame_y, frame_w, frame_h, stroke=0, fill=1)
                            
                            img_x = frame_x + polaroid_padding
                            img_y = frame_y + polaroid_padding + text_height
                            c.drawImage(img_reader, img_x, img_y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')

                        if self.show_date or self.show_time:
                            parts = []
                            if self.show_date:
                                parts.append(dt.strftime("%d/%m/%Y"))
                            if self.show_time:
                                parts.append(dt.strftime("%H:%M"))
                                
                            date_text = " - ".join(parts)
                            c.setFont("Helvetica-Oblique", 9)
                            c.setFillColor(HexColor("#666666"))
                            
                            text_x = frame_x + frame_w / 2
                            text_y = frame_y + (polaroid_padding + text_height) / 2 - 3
                            
                            c.drawCentredString(text_x, text_y, date_text)

                    except Exception as e:
                        logging.error(f"Error processant {photo_path.name}: {e}")

                    photo_index += 1
                    
            c.showPage()
                
        c.save()
        logging.info(f"Tasca finalitzada. PDF generat correctament amb graelles dinàmiques: {self.output_file.absolute()}")


def main():
    parser = argparse.ArgumentParser(description="Generador d'Àlbums de Fotos PDF amb Graelles Asimètriques i Dinàmiques")
    parser.add_argument("-i", "--input", type=str, default="Fotos", help="Carpeta origen de les fotos")
    parser.add_argument("-o", "--output", type=str, default="album_def.pdf", help="Nom del fitxer PDF resultant")
    parser.add_argument("-t", "--title", type=str, default="El meu Àlbum de Fotos", help="Títol de la portada")
    parser.add_argument("--show-date", action="store_true", help="Mostra la data sota cada foto (estil: 14/05/2023)")
    parser.add_argument("--show-time", action="store_true", help="Mostra l'hora sota cada foto (estil: 15:30)")
    parser.add_argument("--layouts", type=str, default="", help="Estils de graella permesos. Ex: '2x2,2-3,1-2-1'. Deixa-ho buit per ús automàtic.")
    
    args = parser.parse_args()

    logging.info(f"Iniciant la generació de l'àlbum '{args.title}' des de '{args.input}'")
    
    generator = AlbumGenerator(
        input_folder=args.input,
        output_file=args.output,
        title=args.title,
        show_date=args.show_date,
        show_time=args.show_time,
        layouts_str=args.layouts
    )
    
    generator.generate()

if __name__ == "__main__":
    main()