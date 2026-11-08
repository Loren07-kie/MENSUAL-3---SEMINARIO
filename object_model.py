"""Clasificación ImageNet con pesos públicos MobileNetV2 y OpenCV DNN."""
from functools import lru_cache
from pathlib import Path
import threading
import hashlib
import json
import os
import tempfile
import urllib.request

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
INFERENCE_LOCK = threading.Lock()

# Etiquetas de uso frecuente traducidas; se conserva siempre el nombre oficial.
SPANISH = {
 'abacus':'Ábaco', 'academic gown':'Toga académica', 'accordion':'Acordeón',
 'acoustic guitar':'Guitarra acústica', 'airliner':'Avión de pasajeros', 'alarm clock':'Reloj despertador',
 'ambulance':'Ambulancia', 'analog clock':'Reloj analógico', 'apron':'Delantal',
 'ashcan':'Papelera', 'backpack':'Mochila', 'ballpoint':'Lapicero / bolígrafo',
 'banana':'Plátano', 'Band Aid':'Curita', 'banjo':'Banjo', 'barbell':'Barra de pesas',
 'barber chair':'Sillón de barbería', 'baseball':'Pelota de béisbol', 'basketball':'Pelota de básquet',
 'bath towel':'Toalla', 'bathtub':'Bañera', 'beaker':'Vaso de laboratorio',
 'beer bottle':'Botella de cerveza', 'beer glass':'Vaso de cerveza', 'bell pepper':'Pimiento',
 'bench':'Banca', 'bicycle-built-for-two':'Bicicleta tándem', 'binder':'Archivador',
 'binoculars':'Binoculares', 'birdhouse':'Casita para aves', 'blender':'Licuadora',
 'bonnet':'Gorro', 'book jacket':'Portada de libro', 'bookcase':'Librero',
 'bookshop':'Librería', 'bottlecap':'Tapa de botella', 'bow tie':'Corbata de lazo',
 'brass':'Placa de metal', 'brassiere':'Sostén', 'broom':'Escoba', 'bucket':'Balde',
 'buckle':'Hebilla', 'bullet train':'Tren de alta velocidad', 'butcher shop':'Carnicería',
 'cab':'Taxi', 'caldron':'Caldero', 'candle':'Vela', 'can opener':'Abrelatas',
 'car mirror':'Espejo de automóvil', 'car wheel':'Rueda de automóvil', 'cardigan':'Cárdigan',
 'carton':'Caja de cartón', 'cash machine':'Cajero automático', 'cassette':'Casete',
 'cassette player':'Reproductor de casetes', 'cellular telephone':'Teléfono celular',
 'chain':'Cadena', 'chain saw':'Motosierra', 'chest':'Cofre', 'chiffonier':'Cómoda',
 'chime':'Campana', 'china cabinet':'Vitrina', 'Christmas stocking':'Bota navideña',
 'cinema':'Cine', 'cleaver':'Cuchillo de carnicero', 'cliff dwelling':'Vivienda en acantilado',
 'cloak':'Capa', 'clog':'Zueco', 'cocktail shaker':'Coctelera', 'coffee mug':'Taza',
 'coffeepot':'Cafetera', 'coil':'Bobina', 'combination lock':'Candado de combinación',
 'computer keyboard':'Teclado de computadora', 'confectionery':'Dulcería',
 'consomme':'Consomé', 'convertible':'Automóvil convertible', 'corkscrew':'Sacacorchos',
 'cornet':'Corneta', 'cowboy boot':'Bota', 'cowboy hat':'Sombrero', 'cradle':'Cuna',
 'crash helmet':'Casco', 'crate':'Caja de madera', 'crib':'Cuna infantil',
 'Crock Pot':'Olla eléctrica', 'croquet ball':'Pelota de croquet', 'crutch':'Muleta',
 'cup':'Taza / copa', 'desk':'Escritorio', 'desktop computer':'Computadora de escritorio',
 'dial telephone':'Teléfono de disco', 'diaper':'Pañal', 'digital clock':'Reloj digital',
 'digital watch':'Reloj de pulsera digital', 'dining table':'Mesa de comedor',
 'dishrag':'Paño de cocina', 'dishwasher':'Lavavajillas', 'disk brake':'Freno de disco',
 'doormat':'Felpudo', 'drill':'Taladro', 'drum':'Tambor', 'drumstick':'Baqueta',
 'dumbbell':'Mancuerna', 'Dutch oven':'Olla de hierro', 'electric fan':'Ventilador',
 'electric guitar':'Guitarra eléctrica', 'electric locomotive':'Locomotora eléctrica',
 'entertainment center':'Centro de entretenimiento', 'envelope':'Sobre',
 'espresso':'Café espresso', 'espresso maker':'Máquina de café', 'face powder':'Polvo facial',
 'file':'Archivador / carpeta', 'fire engine':'Camión de bomberos', 'fire screen':'Pantalla de chimenea',
 'flagpole':'Asta', 'flute':'Flauta', 'folding chair':'Silla plegable', 'football helmet':'Casco deportivo',
 'forklift':'Montacargas', 'fountain pen':'Pluma estilográfica', 'frying pan':'Sartén',
 'fur coat':'Abrigo', 'garbage truck':'Camión de basura', 'gasmask':'Máscara de gas',
 'gas pump':'Surtidor de combustible', 'goblet':'Copa', 'golf ball':'Pelota de golf',
 'golfcart':'Carrito de golf', 'gondola':'Góndola', 'gong':'Gong', 'gown':'Vestido',
 'grand piano':'Piano de cola', 'Granny Smith':'Manzana verde', 'hair slide':'Pasador de cabello',
 'hair spray':'Laca de cabello', 'half track':'Vehículo semioruga', 'hammer':'Martillo',
 'hamper':'Cesto', 'hand blower':'Secadora de cabello', 'hand-held computer':'Computadora de mano',
 'handkerchief':'Pañuelo', 'hard disc':'Disco duro', 'harmonica':'Armónica', 'harp':'Arpa',
 'hatchet':'Hacha', 'head cabbage':'Repollo', 'holster':'Funda', 'home theater':'Cine en casa',
 'honeycomb':'Panal', 'hook':'Gancho', 'hoopskirt':'Falda', 'horizontal bar':'Barra horizontal',
 'hourglass':'Reloj de arena', 'iPod':'Reproductor de música', 'iron':'Plancha',
 'jack-o\'-lantern':'Calabaza tallada', 'jean':'Jeans', 'jeep':'Todoterreno', 'jersey':'Camiseta',
 'jigsaw puzzle':'Rompecabezas', 'joystick':'Joystick', 'kimono':'Kimono',
 'knee pad':'Rodillera', 'knot':'Nudo', 'ladle':'Cucharón', 'lampshade':'Pantalla de lámpara',
 'laptop':'Laptop / portátil', 'lawn mower':'Cortadora de césped', 'lens cap':'Tapa de lente',
 'letter opener':'Abrecartas', 'library':'Biblioteca', 'lifeboat':'Bote salvavidas',
 'lighter':'Encendedor', 'limousine':'Limusina', 'lipstick':'Lápiz labial',
 'lotion':'Loción', 'loudspeaker':'Parlante', 'loupe':'Lupa', 'lumbermill':'Aserradero',
 'magnetic compass':'Brújula', 'mailbag':'Bolsa de correo', 'mailbox':'Buzón',
 'maillot':'Traje de baño', 'manhole cover':'Tapa de alcantarilla', 'maraca':'Maraca',
 'matchstick':'Fósforo', 'measuring cup':'Taza medidora', 'medicine chest':'Botiquín',
 'microphone':'Micrófono', 'microwave':'Microondas', 'minibus':'Minibús',
 'miniskirt':'Minifalda', 'minivan':'Miniván', 'mitten':'Mitón', 'modem':'Módem',
 'monitor':'Monitor', 'moped':'Ciclomotor', 'mortar':'Mortero', 'mosque':'Mezquita',
 'mountain bike':'Bicicleta de montaña', 'mouse':'Mouse / ratón de computadora',
 'mouse trap':'Trampa para ratones', 'moving van':'Camión de mudanza', 'mower':'Cortadora de césped',
 'mushroom':'Champiñón', 'muzzle':'Bozal', 'nail':'Clavo', 'neck brace':'Collarín',
 'necklace':'Collar', 'nipple':'Tetina', 'notebook':'Computadora portátil',
 'obelisk':'Obelisco', 'oboe':'Oboe', 'ocarina':'Ocarina', 'odometer':'Odómetro',
 'oil filter':'Filtro de aceite', 'orange':'Naranja', 'organ':'Órgano musical',
 'packet':'Paquete', 'padlock':'Candado', 'paintbrush':'Pincel', 'pajama':'Pijama',
 'paper towel':'Papel toalla', 'parachute':'Paracaídas', 'park bench':'Banca de parque',
 'parking meter':'Parquímetro', 'pencil box':'Cartuchera', 'pencil sharpener':'Tajador / sacapuntas',
 'perfume':'Perfume', 'Petri dish':'Placa de Petri', 'photocopier':'Fotocopiadora',
 'pick':'Púa', 'pickelhaube':'Casco militar', 'picket fence':'Cerca', 'pickup':'Camioneta',
 'pier':'Muelle', 'piggy bank':'Alcancía', 'pill bottle':'Frasco de pastillas',
 'pillow':'Almohada', 'ping-pong ball':'Pelota de ping-pong', 'pinwheel':'Molinillo',
 'pitcher':'Jarra', 'plane':'Cepillo de carpintería', 'planetarium':'Planetario',
 'plastic bag':'Bolsa plástica', 'plate':'Plato', 'plate rack':'Escurridor de platos',
 'plow':'Arado', 'plunger':'Desatorador', 'Polaroid camera':'Cámara instantánea',
 'pole':'Poste', 'police van':'Furgón policial', 'poncho':'Poncho', 'pool table':'Mesa de billar',
 'pop bottle':'Botella de gaseosa', 'pot':'Maceta', 'power drill':'Taladro eléctrico',
 'prayer rug':'Alfombra', 'printer':'Impresora', 'projector':'Proyector',
 'puck':'Disco de hockey', 'punching bag':'Saco de boxeo', 'purse':'Cartera',
 'quill':'Pluma de escribir', 'quilt':'Colcha', 'racer':'Automóvil de carreras',
 'racket':'Raqueta', 'radiator':'Radiador', 'radio':'Radio', 'radio telescope':'Radiotelescopio',
 'rain barrel':'Barril', 'recreational vehicle':'Casa rodante', 'reflex camera':'Cámara réflex',
 'refrigerator':'Refrigeradora', 'remote control':'Control remoto', 'restaurant':'Restaurante',
 'revolver':'Revólver', 'rifle':'Rifle', 'rocking chair':'Mecedora',
 'rubber eraser':'Borrador', 'rugby ball':'Pelota de rugby', 'rule':'Regla',
 'running shoe':'Zapatilla', 'safe':'Caja fuerte', 'safety pin':'Imperdible',
 'saltshaker':'Salero', 'sandal':'Sandalia', 'sarong':'Pareo', 'sax':'Saxofón',
 'scabbard':'Vaina', 'scale':'Balanza', 'school bus':'Bus escolar', 'schooner':'Goleta',
 'scoreboard':'Marcador', 'screen':'Pantalla', 'screw':'Tornillo', 'screwdriver':'Destornillador',
 'seat belt':'Cinturón de seguridad', 'sewing machine':'Máquina de coser',
 'shield':'Escudo', 'shoe shop':'Zapatería', 'shopping basket':'Canasta', 'shopping cart':'Carrito de compras',
 'shovel':'Pala', 'shower cap':'Gorro de ducha', 'shower curtain':'Cortina de ducha',
 'ski':'Esquí', 'ski mask':'Pasamontañas', 'sleeping bag':'Bolsa de dormir',
 'slide rule':'Regla de cálculo', 'sliding door':'Puerta corrediza', 'slot':'Tragamonedas',
 'snorkel':'Esnórquel', 'snowmobile':'Moto de nieve', 'snowplow':'Quitanieves',
 'soap dispenser':'Dispensador de jabón', 'soccer ball':'Pelota de fútbol', 'sock':'Media',
 'solar dish':'Panel solar parabólico', 'sombrero':'Sombrero mexicano', 'soup bowl':'Tazón de sopa',
 'space bar':'Barra espaciadora', 'spatula':'Espátula', 'speedboat':'Lancha',
 'spider web':'Telaraña', 'spindle':'Huso', 'sports car':'Auto deportivo',
 'spotlight':'Reflector', 'stage':'Escenario', 'steam locomotive':'Locomotora de vapor',
 'steel arch bridge':'Puente de acero', 'steel drum':'Tambor metálico',
 'stethoscope':'Estetoscopio', 'stole':'Estola', 'stone wall':'Muro de piedra',
 'stopwatch':'Cronómetro', 'stove':'Cocina', 'strainer':'Colador', 'streetcar':'Tranvía',
 'stretcher':'Camilla', 'studio couch':'Sofá', 'stupa':'Estupa', 'submarine':'Submarino',
 'suit':'Traje', 'sunglass':'Lentes oscuros', 'sunglasses':'Lentes de sol',
 'sunscreen':'Protector solar', 'suspension bridge':'Puente colgante', 'swab':'Hisopo',
 'sweatshirt':'Polera', 'swimming trunks':'Short de baño', 'swing':'Columpio',
 'switch':'Interruptor', 'syringe':'Jeringa', 'table lamp':'Lámpara de mesa',
 'tank':'Tanque', 'tape player':'Reproductor de cinta', 'teapot':'Tetera',
 'teddy':'Oso de peluche', 'television':'Televisor', 'tennis ball':'Pelota de tenis',
 'thatch':'Techo de paja', 'thimble':'Dedal', 'thresher':'Trilladora',
 'throne':'Trono', 'tile roof':'Tejado', 'toaster':'Tostadora', 'tobacco shop':'Tabaquería',
 'toilet seat':'Asiento de inodoro', 'torch':'Antorcha', 'totem pole':'Tótem',
 'tow truck':'Grúa', 'toyshop':'Juguetería', 'tractor':'Tractor', 'traffic light':'Semáforo',
 'trailer truck':'Tráiler', 'tray':'Bandeja', 'trench coat':'Gabardina',
 'tricycle':'Triciclo', 'trimaran':'Trimarán', 'tripod':'Trípode', 'triumphal arch':'Arco',
 'trolleybus':'Trolebús', 'trombone':'Trombón', 'tub':'Tina', 'turnstile':'Torniquete',
 'typewriter keyboard':'Máquina de escribir', 'umbrella':'Paraguas',
 'unicycle':'Monociclo', 'upright':'Piano vertical', 'vacuum':'Aspiradora',
 'vase':'Florero', 'vault':'Bóveda', 'velvet':'Terciopelo', 'vending machine':'Máquina expendedora',
 'vestment':'Vestimenta ceremonial', 'viaduct':'Viaducto', 'violin':'Violín',
 'volleyball':'Pelota de vóley', 'waffle iron':'Waflera', 'wall clock':'Reloj de pared',
 'wallet':'Billetera', 'wardrobe':'Armario', 'warplane':'Avión militar',
 'washbasin':'Lavamanos', 'washer':'Lavadora', 'water bottle':'Botella de agua',
 'water jug':'Jarra de agua', 'water tower':'Torre de agua', 'whiskey jug':'Jarra',
 'whistle':'Silbato', 'wig':'Peluca', 'window screen':'Malla de ventana',
 'window shade':'Persiana', 'Windsor tie':'Corbata', 'wine bottle':'Botella de vino',
 'wing':'Ala', 'wok':'Wok', 'wooden spoon':'Cuchara de madera', 'wool':'Lana',
 'worm fence':'Cerca de madera', 'wreck':'Naufragio', 'yawl':'Velero', 'yurt':'Yurta',
 'zucchini':'Zapallito', 'strawberry':'Fresa', 'lemon':'Limón', 'pineapple':'Piña',
 'fig':'Higo', 'pomegranate':'Granada', 'broccoli':'Brócoli', 'cauliflower':'Coliflor',
 'cucumber':'Pepino', 'artichoke':'Alcachofa', 'bell pepper':'Pimiento', 'corn':'Maíz',
 'pizza':'Pizza', 'cheeseburger':'Hamburguesa con queso', 'hotdog':'Hot dog',
 'ice cream':'Helado', 'dough':'Masa', 'pretzel':'Pretzel', 'bagel':'Bagel',
 'French loaf':'Pan francés', 'burrito':'Burrito', 'guacamole':'Guacamole',
 'chocolate sauce':'Salsa de chocolate', 'trifle':'Postre en capas', 'meat loaf':'Pastel de carne',
}


@lru_cache(maxsize=1)
def catalog():
    names = (ROOT / 'models' / 'imagenet_classes.txt').read_text(encoding='utf-8').splitlines()
    if len(names) != 1000:
        raise RuntimeError('El catálogo ImageNet no está completo.')
    return [{'id': i, 'name': SPANISH.get(name, name), 'original': name,
             'group': 'Objetos y alimentos' if i >= 398 and i <= 969 else 'Naturaleza y animales'}
            for i, name in enumerate(names)]


@lru_cache(maxsize=1)
def network():
    path = ROOT / 'models' / 'mobilenetv2-7.onnx'
    manifest = json.loads((ROOT/'models'/'manifest.json').read_text(encoding='utf-8'))
    if not path.exists():
        # Los pesos se descargan una vez por instancia desde su fuente oficial.
        temporary = None
        try:
            with urllib.request.urlopen(manifest['weights_url'], timeout=45) as response:
                with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.part', delete=False) as output:
                    temporary = output.name
                    digest = hashlib.sha256()
                    count = 0
                    while chunk := response.read(256*1024):
                        count += len(chunk)
                        if count > 20*1024*1024:
                            raise RuntimeError('La descarga del modelo supera el tamaño esperado.')
                        digest.update(chunk)
                        output.write(chunk)
            if count != manifest['bytes'] or digest.hexdigest() != manifest['sha256']:
                raise RuntimeError('No se pudo verificar la integridad de los pesos.')
            os.replace(temporary, path)
        except (OSError, ValueError) as exc:
            raise RuntimeError('No se pudieron obtener los pesos oficiales del modelo.') from exc
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)
    elif hashlib.sha256(path.read_bytes()).hexdigest() != manifest['sha256']:
        raise RuntimeError('Los pesos locales no coinciden con su huella de integridad.')
    net = cv2.dnn.readNetFromONNX(str(path))
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return net


def preprocess(image):
    """Resize shorter side to 256, center crop 224, RGB, ImageNet normalization."""
    h, w = image.shape[:2]
    # Recortar primero el cuadrado central evita reservar imágenes enormes
    # para fotografías extremadamente panorámicas. Mismo campo central.
    side = min(h, w)
    y, x = (h-side)//2, (w-side)//2
    resized = cv2.resize(image[y:y+side, x:x+side], (256, 256), interpolation=cv2.INTER_LINEAR)
    crop = resized[16:240, 16:240]
    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).astype(np.float32)/255
    normalized = (rgb-np.array([.485,.456,.406],dtype=np.float32))/np.array([.229,.224,.225],dtype=np.float32)
    return normalized.transpose(2,0,1)[None].copy(), crop


def classify_object(image):
    blob, crop = preprocess(image)
    with INFERENCE_LOCK:
        net = network()
        net.setInput(blob)
        logits = net.forward().ravel()
    if len(logits) != 1000:
        raise RuntimeError('El modelo no devolvió las 1000 categorías esperadas.')
    probabilities = np.exp(logits-logits.max())
    probabilities /= probabilities.sum()
    labels = catalog()
    top = np.argsort(probabilities)[::-1][:5]
    return [{'id': int(i), 'name': labels[i]['name'], 'original': labels[i]['original'],
             'probability': round(float(probabilities[i])*100, 2)} for i in top], crop
