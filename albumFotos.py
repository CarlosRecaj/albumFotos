import logging
from pathlib import Path
from datetime import datetime
from PIL import Image, ExifTags, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

# --- AJUSTOS DE L'USUARI ---
# Variables generals per fer-ho més fàcil de configurar.
INPUT_FOLDER = Path("Fotos Destacades")       # Carpeta origen de les fotos
OUTPUT_FILE = Path("album_def2.pdf")          # Nom del fitxer PDF resultant
PHOTOS_PER_PAGE = 9                           # Distribució en graella de 3x3 (9 fotos per pàgina)
MARGIN = 20                                   # Marges de seguretat per evitar talls en la impressió
SPACING = 5                                   # Espai de separació estètica entre fotografies
TEXT_HEIGHT = 20                              # Espai vertical reservat per col·locar la data sota cada foto
PAGE_SIZE = A4

# Configuració del logging per disposar de nivells de severitat (INFO, ERROR)
# en comptes d'utilitzar print(), preparant l'script per a possibles execucions en servidors.
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def get_photo_datetime(path: Path) -> datetime:
    """
    Extracció de la data original de les metadades EXIF de la foto.
    Aquest mètode garanteix un ordre cronològic estricte de forma fiable.
    Si la foto no conté EXIF (ex. imatges de WhatsApp), s'utilitza la data de modificació del fitxer com a alternativa.
    """
    try:
        # L'ús del context manager (with) assegura que el fitxer es tanqui correctament en tots els casos.
        # Image.open aplica "lazy loading", carregant només les capçaleres en lloc de tota la memòria de píxels.
        with Image.open(path) as img:
            # S'utilitza getexif() ja que és el mètode oficial a les versions actuals de PIL.
            exif = img.getexif() 
            # Si getexif() falla, es recorre al mètode privat antic per mantenir la retrocompatibilitat.
            if not exif and hasattr(img, '_getexif'):
                exif = getattr(img, "_getexif", lambda: None)()
                
            if exif:
                # S'iteren les etiquetes per buscar la data, utilitzant ExifTags.TAGS per traduir els IDs numèrics.
                for tag, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag, tag)
                    if tag_name in ("DateTimeOriginal", "DateTimeDigitized", "DateTime"):
                        try:
                            # Es converteix la cadena EXIF a un objecte datetime natiu de Python.
                            return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                        except ValueError:
                            # Si el format de la data és invàlid, s'ignora i es continua la cerca.
                            continue 
    except Exception as e:
        # Si hi ha un error no s'atura l'execució si l'imatge està corrompuda, però es deixa rastre al debug per investigar-ho.
        logging.debug(f"Avís: No s'han pogut llegir les metadades EXIF de {path.name} ({e})")

    # Alternativa (Pla B): s'utilitza st_mtime (Data de modificació) del sistema de fitxers. 
    # Es descarta ctime, ja que en sistemes Linux/Mac representa l'últim canvi de metadades i no la creació.
    return datetime.fromtimestamp(path.stat().st_mtime)

def make_pdf(photo_infos: list[tuple[Path, datetime]]):
    """
    Generació de la graella de fotos al document PDF. 
    Es calculen les dimensions dinàmicament per evitar la deformació de les imatges
    i es gestionen automàticament els salts de pàgina.
    """
    # Càlcul de columnes i files de forma automàtica mitjançant l'arrel quadrada del total. 
    # Per a 9 fotos s'obté una graella de 3x3; per a 8 fotos, es calcula la millor distribució deixant forats buits.
    cols = int(PHOTOS_PER_PAGE ** 0.5 + 0.5)
    rows = (PHOTOS_PER_PAGE + cols - 1) // cols

    page_w, page_h = PAGE_SIZE
    
    # Càlcul de l'espai útil per pintar, restant els marges exteriors i l'espai de separació entre les fotos.
    usable_w = page_w - 2 * MARGIN - (cols - 1) * SPACING
    usable_h = page_h - 2 * MARGIN - (rows - 1) * SPACING

    # Divisió de l'espai útil entre el nombre de columnes/files per obtenir les dimensions màximes de cada cel·la.
    cell_w = usable_w / cols
    cell_h = usable_h / rows

    # Inicialització del llenç del document PDF mitjançant ReportLab.
    c = canvas.Canvas(str(OUTPUT_FILE), pagesize=PAGE_SIZE)

    for i, (photo_path, dt) in enumerate(photo_infos):
        # Creació d'una nova pàgina en arribar al límit d'imatges establert per pàgina.
        if i % PHOTOS_PER_PAGE == 0 and i > 0:
            c.showPage()

        # Càlcul de la posició (columna i fila) corresponent a la foto actual dins la graella.
        pos = i % PHOTOS_PER_PAGE
        col = pos % cols
        row = pos // cols

        # ReportLab situa l'origen de coordenades (0,0) a la cantonada inferior esquerra.
        # Es calcula la posició X (esquerra a dreta) i la posició Y (dalt a baix), aplicant marges i separacions.
        x = MARGIN + col * (cell_w + SPACING)
        y = page_h - MARGIN - (row + 1) * cell_h - row * SPACING

        try:
            with Image.open(photo_path) as im:
                # Les fotografies fetes amb dispositius mòbils solen estar rotades només a les metadades (EXIF). 
                # S'aplica exif_transpose per rotar els píxels físicament, evitant que es mostrin de costat al PDF.
                im = ImageOps.exif_transpose(im)
                
                # Conversió de la imatge de PIL a un ImageReader de ReportLab abans del procés de dibuix.
                # Aquesta decisió prevé pèrdues de memòria o càrregues dobles innecessàries al Canvas.
                img_reader = ImageReader(im)
                
                iw, ih = im.size
                aspect = iw / ih

                # Dedicació de l'espai necessari per a la imatge, considerant l'espai reservat a la base per al text.
                target_w = cell_w
                target_h = cell_h - TEXT_HEIGHT

                # Redimensió de la imatge perquè s'ajusti a la cel·la mantenint la relació d'aspecte original (aspect ratio).
                # Es determina si la limitació d'escala ve donada per l'amplada o bé per l'alçada.
                if target_w / target_h > aspect:
                    draw_h = target_h
                    draw_w = target_h * aspect
                else:
                    draw_w = target_w
                    draw_h = target_w / aspect

                # Atès que la foto generalment no ocupa tota la cel·la (per conservar la proporció),
                # se centra horitzontalment sumant la meitat de l'espai restant.
                img_x = x + (cell_w - draw_w) / 2
                img_y = y + TEXT_HEIGHT 

                # Inserció de la fotografia final al document, aplicant les restriccions per evitar deformacions.
                c.drawImage(img_reader, img_x, img_y,
                            width=draw_w, height=draw_h,
                            preserveAspectRatio=True, mask='auto')

            # Formatació de la data i inserció del text centrat a la part inferior de la imatge.
            date_text = dt.strftime("%Y-%m-%d %H:%M")
            c.setFont("Helvetica", 8)
            text_x = x + cell_w / 2
            text_y = img_y - 10 
            c.drawCentredString(text_x, text_y, date_text)

        except Exception as e:
            # En cas de fallada en una imatge específica, es registra l'error sense interrompre la generació de la resta del document.
            logging.error(f"Error processant {photo_path.name}: {e}")

    c.save()
    logging.info(f"PDF generat correctament: {OUTPUT_FILE.absolute()}")

def main():
    # Comprovació inicial de l'existència de la carpeta de les fotos per evitar execucions innecessàries.
    if not INPUT_FOLDER.is_dir():
        logging.error(f"No s'ha trobat el directori {INPUT_FOLDER}")
        return

    logging.info("Analitzant el directori de fotos...")
    
    # Definició d'extensions vàlides en format Set (conjunt). 
    # A Python, la cerca en un Set té una complexitat O(1) (instantània), millorant el rendiment en llistes llargues de fitxers.
    valid_extensions = {".jpg", ".jpeg", ".png"}
    
    # Ús de llistes per comprensió i pathlib.iterdir(), una operació més eficient que os.listdir(), 
    # ja que itera i filtra directament a nivell de sistema operatiu.
    photos = [p for p in INPUT_FOLDER.iterdir() if p.is_file() and p.suffix.lower() in valid_extensions]

    if not photos:
        logging.warning("No s'han trobat imatges vàlides a la carpeta.")
        return

    # Mapeig dels fitxers amb la seva data EXIF corresponent, seguit d'una ordenació cronològica.
    # Aquest pas garanteix que les imatges de l'àlbum es mostrin ordenades de forma ascendent.
    photo_infos = [(p, get_photo_datetime(p)) for p in photos]
    photo_infos.sort(key=lambda x: x[1])

    logging.info(f"Processant {len(photos)} fotos per crear l'àlbum...")
    make_pdf(photo_infos)
    logging.info("Tasca finalitzada. Ja pots gaudir del teu àlbum.")

if __name__ == "__main__":
    main()