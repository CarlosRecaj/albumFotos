import os
from PIL import Image, ExifTags, ImageOps
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

# --- AJUSTOS DE L'USUARI ---
# Rutes i configuració visual del document
INPUT_FOLDER = r"Fotos Destacades"       # Carpeta amb les fotos 
OUTPUT_FILE = "album_def2.pdf"
PHOTOS_PER_PAGE = 9           # Quantitat de cel·les per pàgina
MARGIN = 20                   # Marges de seguretat per a la impressió
SPACING = 5                   # Separació entre les imatges de la graella
TEXT_HEIGHT = 20              # Espai vertical reservat per a la data
PAGE_SIZE = A4

def get_photo_datetime(path):
    """
    Intentem extreure la data original de les metadades EXIF.
    És la millor manera de mantenir l'ordre cronològic real.
    Si el fitxer no en té, usem la data de creació del sistema de fitxers.
    """
    try:
        img = Image.open(path)
        exif = getattr(img, "_getexif", lambda: None)()
        if exif:
            for tag, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag, tag)
                if tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
                    try:
                        return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                    except Exception:
                        pass
    except Exception:
        pass

    # Si no hi ha EXIF, el ctime és la data del fitxer 
    ts = os.path.getctime(path)
    return datetime.fromtimestamp(ts)

def make_pdf(photo_infos):
    """
    Genera la graella al PDF ajustant les proporcions de cada foto
    per evitar deformacions i gestionant els salts de pàgina.
    """
    # Càlcul dinàmic de files i columnes segons el total de fotos per pàgina
    cols = int(PHOTOS_PER_PAGE ** 0.5 + 0.5)
    rows = (PHOTOS_PER_PAGE + cols - 1) // cols

    page_w, page_h = PAGE_SIZE
    # Calculem l'espai de treball real restant marges i espais intermedis
    usable_w = page_w - 2 * MARGIN - (cols - 1) * SPACING
    usable_h = page_h - 2 * MARGIN - (rows - 1) * SPACING

    cell_w = usable_w / cols
    cell_h = usable_h / rows

    c = canvas.Canvas(OUTPUT_FILE, pagesize=PAGE_SIZE)

    for i, (photo, dt) in enumerate(photo_infos):
        # Iniciem una pàgina nova quan hem omplert el cup d'imatges
        if i % PHOTOS_PER_PAGE == 0 and i > 0:
            c.showPage()

        pos = i % PHOTOS_PER_PAGE
        col = pos % cols
        row = pos // cols

        # Coordenades de la cel·la actual (sistema de coordenades de ReportLab comença a baix a l'esquerra)
        x = MARGIN + col * (cell_w + SPACING)
        y = page_h - MARGIN - (row + 1) * cell_h - row * SPACING

        try:
            with Image.open(photo) as im:
                # Corregim la rotació segons el sensor de la càmera (EXIF transpose)
                # Sense això, les fotos verticals sovint apareixen horitzontals.
                im = ImageOps.exif_transpose(im)
                iw, ih = im.size
                aspect = iw / ih

                target_w = cell_w
                target_h = cell_h - TEXT_HEIGHT

                # Ajustem la imatge al contenidor mantenint la relació d'aspecte (proporcions)
                if target_w / target_h > aspect:
                    draw_h = target_h
                    draw_w = target_h * aspect
                else:
                    draw_w = target_w
                    draw_h = target_w / aspect

                # Centrat horitzontal dins la cel·la
                img_x = x + (cell_w - draw_w) / 2
                img_y = y + TEXT_HEIGHT 

                # Pintem la imatge processada (no el path) per conservar la correcció d'orientació
                c.drawImage(ImageReader(im), img_x, img_y,
                            width=draw_w, height=draw_h,
                            preserveAspectRatio=True, mask='auto')

            # Afegim la marca temporal a sota de la foto
            date_text = dt.strftime("%Y-%m-%d %H:%M")
            c.setFont("Helvetica", 8)
            text_x = x + cell_w / 2
            text_y = img_y - 10 
            c.drawCentredString(text_x, text_y, date_text)

        except Exception as e:
            print(f"Error processant {photo}: {e}")

    c.save()
    print(f"PDF generat correctament: {OUTPUT_FILE}")

if __name__ == "__main__":
    if not os.path.exists(INPUT_FOLDER):
        print(f"Error: No s'ha trobat el directori {INPUT_FOLDER}")
    else:
        print("Analitzant el directori de fotos...")
        photos = [os.path.join(INPUT_FOLDER, f) for f in os.listdir(INPUT_FOLDER)
                  if f.lower().endswith((".jpg", ".jpeg", ".png"))]

        if not photos:
            print("No s'han trobat imatges vàlides.")
        else:
            # Ordenació per data abans de generar el PDF
            photo_infos = [(p, get_photo_datetime(p)) for p in photos]
            photo_infos.sort(key=lambda x: x[1])

            print(f"Processant {len(photos)} fotos...")
            make_pdf(photo_infos)
            print("Procés finalitzat.")