# Generador d'Àlbums de Fotos PDF

Aquest projecte és un script en Python dissenyat per automatitzar la creació d'àlbums de fotos en format PDF a partir d'un directori d'imatges. Genera graelles fotogràfiques asimètriques, elegants i dinàmiques, i s'encarrega d'ordenar automàticament les imatges cronològicament extraient-ne les metadades EXIF (o la data de creació com a alternativa).

## Funcionalitats Principals

- **Ordenació Cronològica:** Llegeix la data exacta des de l'etiqueta `DateTimeOriginal` amagada dins les metadades EXIF de la fotografia original. Si la imatge no té aquestes dades (per exemple, les descarregades de WhatsApp), empra la data de creació del fitxer per establir l'ordre correcte.
- **Graelles Dinàmiques i Asimètriques:** Pots deixar que l'script triï aleatòriament els dissenys de les pàgines d'un llistat predefinit d'opcions estètiques molt visuals, o pots especificar lliurement quins estils de graella concrets vols utilitzar.
- **Portada Automàtica:** Genera una primera pàgina que actua de portada amb un títol personalitzat i inclou automàticament l'interval de dates de les fotografies introduïdes (ex: *"De 12/03/2023 a 15/04/2023"*).
- **Informació Temporal (Opcional):** Pots triar si vols que sota cada foto (estil *Polaroid*) hi aparegui impresa la data, l'hora, totes dues coses a la vegada o bé deixar-ho en blanc.
- **Disseny Cuidat i Elegant:** Utilitza format A4 amb marges intel·ligents, un fons color crema/gris suau, i quadres fotogràfics amb ombres per simular l'aspecte d'imatges impreses reals, corregint automàticament l'orientació visual d'aquelles fetes en vertical segons els sensors de la càmera.

## Requisits i Instal·lació

Aquest projecte requereix **Python 3** i les següents llibreries:
- `Pillow` (per a l'extracció d'EXIF i manipulació d'imatges)
- `reportlab` (per a la construcció del document PDF)

Pots instal·lar-les fàcilment si tens l'arxiu `requirements.txt`:
```bash
pip install -r requirements.txt
```
*(De forma alternativa: `pip install Pillow reportlab`)*

## Com utilitzar-lo

Per fer-lo funcionar fàcilment i amb les opcions per defecte (buscant les imatges a la carpeta `Fotos` i sense imprimir la data a les cel·les), simplement executa:

```bash
python albumFotos.py
```
Això crearà un arxiu anomenat `album_def.pdf` dins del teu directori.

### Paràmetres (Arguments de Línia de Comandes)

Pots personalitzar gairebé tots els aspectes del document des de la pròpia crida des del terminal usant arguments ("flags"):

- `-i` o `--input`: Especifica el nom o la ruta de la carpeta origen que conté les fotos a processar. (Per defecte: `Fotos`)
- `-o` o `--output`: Indica quin nom vols per a l'arxiu PDF que es crearà. (Per defecte: `album_def.pdf`)
- `-t` o `--title`: Defineix el títol que encapçalarà la portada de l'àlbum. (Per defecte: `"El meu Àlbum de Fotos"`)
- `--show-date`: Activa la inclusió de la data de la fotografia a la part de sota de la cel·la (ex: `14/05/2023`).
- `--show-time`: Activa la inclusió de l'hora exacta sota de la cel·la (ex: `15:30`).
- `--layouts`: Permet forçar l'ús exclusiu de certs estils de graella que prefereixis, passant-los en forma de cadena separada per comes.

### Exemples i Casos d'Ús

**1. Generar l'àlbum imprimint tant la data com l'hora de cada fotografia:**
```bash
python albumFotos.py --show-date --show-time
```

**2. Crear un àlbum des d'una altra carpeta, establint el títol i el nom del document final:**
```bash
python albumFotos.py -i "Vacances_Roma" -o "Roma_2023.pdf" -t "Viatge a Roma 2023"
```

**3. Exemple complert combinant vàries de les opcions i forçant dissenys específics de pàgina:**
```bash
python albumFotos.py -i "Imatges" -o "LaMevaFesta.pdf" -t "Festa d'Aniversari" --show-date --layouts "2x2,3,2-3"
```

### Com funciona el paràmetre de `--layouts`?

Els layouts descriuen l'estructura de la graella de fotos d'una pàgina. Si decideixes establir quins usar amb `--layouts`, cal que utilitzis aquesta nomenclatura (recorrent a les comes per separar múltiples dissenys, els quals s'aniran alternant a l'atzar):

- **XxF**: Crea múltiples files idèntiques amb els mateixos elements. Ex: `2x2` indica 2 files i 2 columnes per fila (4 fotos en total).
- **A-B-C**: Dissenys de files asimètriques indicant la quantitat a cada esglaó. Ex: `2-3` significa que a la 1a fila hi hauran 2 fotos i a la 2a n'hi hauran 3. Si fos `1-2-1` hi hauria una dalt, dos al centre i una abaix.
- **N**: Una sola fila on hi caben `N` fotos. Ex: `3` (1 fila horitzontal on n'hi caben 3).

Exemple vàlid d'arguments: `--layouts "2x2,2-3,1-2-1,3"`
*(Nota: Si queden fotos al final que no arribin a satisfer la capacitat d'una graella completa, el programa disposa d'estructures de suport autogenerades per col·locar-les elegantment al final del document)*
