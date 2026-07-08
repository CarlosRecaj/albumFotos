import argparse
import logging
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
    def __init__(self, input_folder, output_file, title, show_date, show_time, photos_per_page=9):
        self.input_folder = Path(input_folder)
        self.output_file = Path(output_file)
        self.title = title
        self.show_date = show_date
        self.show_time = show_time
        self.photos_per_page = photos_per_page
        
        # Paràmetres estètics
        self.page_size = A4
        self.margin = 25
        self.spacing = 15
        self.bg_color = HexColor("#F5F5F0")  # Fons crema/gris suau elegant
        
    def get_photo_datetime(self, path: Path) -> datetime:
        """Extreu la data de les metadades EXIF o bé de la modificació del fitxer."""
        try:
            with Image.open(path) as img:
                exif = img.getexif() 
                if not exif and hasattr(img, '_getexif'):
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

        # Pla B: st_mtime
        return datetime.fromtimestamp(path.stat().st_mtime)

    def draw_background(self, c, w, h):
        """Dibuixa el color de fons sòlid per a tota la pàgina."""
        c.setFillColor(self.bg_color)
        c.rect(0, 0, w, h, stroke=0, fill=1)

    def draw_footer(self, c, page_num, w):
        """Afegeix la numeració de pàgina al peu."""
        c.setFont("Helvetica", 10)
        c.setFillColor(HexColor("#888888"))
        c.drawCentredString(w / 2, 15, f"Pàgina {page_num}")

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

        c = canvas.Canvas(str(self.output_file), pagesize=self.page_size)
        page_w, page_h = self.page_size
        
        # --- PORTADA ---
        self.draw_background(c, page_w, page_h)
        c.setFillColor(HexColor("#333333"))
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(page_w / 2, page_h / 2 + 30, self.title)
        
        # Subtítol amb el rang de dates
        first_date = photo_infos[0][1].strftime("%d/%m/%Y")
        last_date = photo_infos[-1][1].strftime("%d/%m/%Y")
        c.setFont("Helvetica-Oblique", 18)
        c.setFillColor(HexColor("#666666"))
        
        if first_date == last_date:
            c.drawCentredString(page_w / 2, page_h / 2 - 10, f"{first_date}")
        else:
            c.drawCentredString(page_w / 2, page_h / 2 - 10, f"De {first_date} a {last_date}")
            
        c.showPage() # Salta a la següent pàgina
        
        # --- PÀGINES DE FOTOS ---
        cols = int(self.photos_per_page ** 0.5 + 0.5)
        rows = (self.photos_per_page + cols - 1) // cols

        usable_w = page_w - 2 * self.margin - (cols - 1) * self.spacing
        usable_h = page_h - 2 * self.margin - (rows - 1) * self.spacing

        cell_w = usable_w / cols
        cell_h = usable_h / rows
        
        # Reserva d'espai per al text i marcs
        text_height = 0
        if self.show_date or self.show_time:
            text_height = 20 # Espai per la data/hora a la base
            
        polaroid_padding = 8
        shadow_offset = 3

        page_num = 1
        
        for i, (photo_path, dt) in enumerate(photo_infos):
            # Si és la primera foto d'una pàgina nova, pintem el fons i el peu
            if i % self.photos_per_page == 0:
                self.draw_background(c, page_w, page_h)
                self.draw_footer(c, page_num, page_w)
                page_num += 1
                
            pos = i % self.photos_per_page
            col = pos % cols
            row = pos // cols

            # Coordenades x, y inferior esquerra de la cel·la
            x = self.margin + col * (cell_w + self.spacing)
            y = page_h - self.margin - (row + 1) * cell_h - row * self.spacing

            try:
                with Image.open(photo_path) as im:
                    im = ImageOps.exif_transpose(im)
                    img_reader = ImageReader(im)
                    iw, ih = im.size
                    aspect = iw / ih

                    # Mida disponible per a la imatge neta (descomptant vores del polaroid i el text)
                    target_w = cell_w - (polaroid_padding * 2)
                    target_h = cell_h - (polaroid_padding * 2) - text_height

                    if target_w / target_h > aspect:
                        draw_h = target_h
                        draw_w = target_h * aspect
                    else:
                        draw_w = target_w
                        draw_h = target_w / aspect
                    
                    # Dimensions totals del marc blanc "Polaroid"
                    frame_w = draw_w + (polaroid_padding * 2)
                    frame_h = draw_h + (polaroid_padding * 2) + text_height
                    
                    # Centrem el marc dins la cel·la
                    frame_x = x + (cell_w - frame_w) / 2
                    frame_y = y + (cell_h - frame_h) / 2
                    
                    # 1. Dibuixar l'ombra
                    c.setFillColor(HexColor("#D0D0D0")) # Gris ombra
                    c.rect(frame_x + shadow_offset, frame_y - shadow_offset, frame_w, frame_h, stroke=0, fill=1)
                    
                    # 2. Dibuixar el marc blanc (Polaroid)
                    c.setFillColor(HexColor("#FFFFFF"))
                    c.rect(frame_x, frame_y, frame_w, frame_h, stroke=0, fill=1)
                    
                    # 3. Dibuixar la imatge a l'interior
                    img_x = frame_x + polaroid_padding
                    img_y = frame_y + polaroid_padding + text_height
                    c.drawImage(img_reader, img_x, img_y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')

                # 4. Text inferior (Data i Hora opcionals)
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
                    # L'altura y per al text es centra en l'espai reservat sota la imatge
                    text_y = frame_y + (polaroid_padding + text_height) / 2 - 3
                    
                    c.drawCentredString(text_x, text_y, date_text)

            except Exception as e:
                logging.error(f"Error processant {photo_path.name}: {e}")

            # Salt de pàgina si la graella està plena i encara queden fotos
            if (i + 1) % self.photos_per_page == 0 and i < len(photo_infos) - 1:
                c.showPage()
                
        c.save()
        logging.info(f"Tasca finalitzada. PDF generat correctament: {self.output_file.absolute()}")


def main():
    parser = argparse.ArgumentParser(description="Generador d'Àlbums de Fotos PDF amb Estil")
    parser.add_argument("-i", "--input", type=str, default="Fotos Destacades", help="Carpeta origen de les fotos")
    parser.add_argument("-o", "--output", type=str, default="album_def2.pdf", help="Nom del fitxer PDF resultant")
    parser.add_argument("-t", "--title", type=str, default="El meu Àlbum de Fotos", help="Títol de la portada")
    parser.add_argument("--show-date", action="store_true", help="Mostra la data sota cada foto (estil: 14/05/2023)")
    parser.add_argument("--show-time", action="store_true", help="Mostra l'hora sota cada foto (estil: 15:30)")
    
    args = parser.parse_args()

    logging.info(f"Iniciant la generació de l'àlbum '{args.title}' des de '{args.input}'")
    
    generator = AlbumGenerator(
        input_folder=args.input,
        output_file=args.output,
        title=args.title,
        show_date=args.show_date,
        show_time=args.show_time
    )
    
    generator.generate()

if __name__ == "__main__":
    main()