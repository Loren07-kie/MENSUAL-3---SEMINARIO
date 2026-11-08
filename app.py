"""Nexo Lab: visión por computadora y aprendizaje automático reproducible."""
import base64
import csv
import io
import math
import os
import threading
from functools import lru_cache

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request, send_file
from PIL import Image, ImageOps, UnidentifiedImageError
from sklearn.datasets import load_digits
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

app = Flask(__name__)
app.config.update(MAX_CONTENT_LENGTH=9 * 1024 * 1024, MAX_FORM_MEMORY_SIZE=9 * 1024 * 1024)
Image.MAX_IMAGE_PIXELS = 20_000_000
cv2.setNumThreads(1)
LOCK = threading.Lock()
FILTERS = {'original': 'Original', 'grises': 'Escala de grises', 'bordes': 'Bordes Canny',
           'gaussiano': 'Desenfoque', 'sepia': 'Sepia editorial', 'detalle': 'Más detalle',
           'acuarela': 'Acuarela', 'invertir': 'Negativo', 'umbral': 'Blanco y negro',
           'rostros': 'Detectar rostros', 'color': 'Color selectivo'}


@app.get('/')
def index():
    return render_template('index.html')


@app.get('/health')
def health():
    return jsonify(status='ok', application='Nexo Lab', version='1.0.0')


@app.after_request
def headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.errorhandler(413)
def too_large(_error):
    return jsonify(error='El archivo supera el límite de 8 MB. Elige una imagen más pequeña.'), 413


@app.errorhandler(404)
def missing(_error):
    return jsonify(error='Esta ruta no existe.'), 404


def number(data, key, low, high):
    try:
        value = float(data[key])
    except (ValueError, TypeError, KeyError):
        raise ValueError(f'Introduce un valor numérico para {key}.')
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{key} debe estar entre {low} y {high}.')
    return value


def read_image():
    upload = request.files.get('image')
    if upload is None:
        raise ValueError('Primero elige una imagen o toma una fotografía.')
    raw = upload.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('La imagen supera los 8 MB.')
    try:
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in ('JPEG', 'PNG', 'WEBP'):
                raise ValueError('Usa una imagen JPG, PNG o WebP.')
            if im.width * im.height > 20_000_000:
                raise ValueError('La imagen supera los 20 megapíxeles.')
            im = ImageOps.exif_transpose(im).convert('RGB')
            original_size = im.size
            im.thumbnail((1600, 1600))
            rgb = np.asarray(im)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValueError('No pudimos leer esa imagen. Prueba con un JPG o PNG válido.')
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), original_size


def encode(image):
    ok, buffer = cv2.imencode('.png', image)
    if not ok:
        raise ValueError('No se pudo generar la imagen.')
    return 'data:image/png;base64,' + base64.b64encode(buffer).decode()


@app.post('/api/vision')
def vision():
    try:
        image, original_size = read_image()
        selected = request.form.get('filter', 'original')
        if selected not in FILTERS:
            raise ValueError('Elige uno de los filtros disponibles.')
        strength = number(request.form, 'strength', 1, 100)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        result = image.copy()
        faces = None
        if selected == 'grises':
            result = gray
        elif selected == 'bordes':
            result = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), strength, strength * 2.5)
        elif selected == 'gaussiano':
            kernel = int(strength / 4) * 2 + 3
            result = cv2.GaussianBlur(image, (kernel, kernel), 0)
        elif selected == 'sepia':
            result = np.clip(cv2.transform(image, np.array([[.131,.534,.272],[.168,.686,.349],[.189,.769,.393]])), 0, 255).astype(np.uint8)
        elif selected == 'detalle':
            blurred = cv2.GaussianBlur(image, (0, 0), 3)
            result = cv2.addWeighted(image, 1 + strength / 50, blurred, -strength / 50, 0)
        elif selected == 'acuarela':
            result = cv2.stylization(image, sigma_s=60, sigma_r=.1 + strength / 180)
        elif selected == 'invertir':
            result = 255 - image
        elif selected == 'umbral':
            _, result = cv2.threshold(gray, int(strength * 2.55), 255, cv2.THRESH_BINARY)
        elif selected == 'color':
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, np.array([0, int(strength * 2), 30]), np.array([179, 255, 255]))
            result = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            result[mask > 0] = image[mask > 0]
        elif selected == 'rostros':
            cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            found = cascade.detectMultiScale(gray, 1.1, 5, minSize=(35, 35))
            faces = len(found)
            for x, y, w, h in found:
                cv2.rectangle(result, (x, y), (x+w, y+h), (113, 225, 185), 3)
        histogram = cv2.calcHist([gray], [0], None, [32], [0, 256]).ravel().astype(int).tolist()
        return jsonify(image=encode(result), original=encode(image), filter=FILTERS[selected],
                       width=image.shape[1], height=image.shape[0], original_size=original_size,
                       brightness=round(float(gray.mean()), 1), contrast=round(float(gray.std()), 1),
                       sharpness=round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1),
                       faces=faces, histogram=histogram)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@lru_cache(maxsize=1)
def regression_data():
    rng = np.random.default_rng(42)
    x = np.column_stack((rng.uniform(10, 500, 240), rng.uniform(.5, 18, 240), rng.uniform(0, 100, 240)))
    y = 8 + .095*x[:, 0] + 3.8*x[:, 1] + .18*x[:, 2] + rng.normal(0, 2.5, 240)
    return x, y


def fit_regression(x, y):
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=.25, random_state=42)
    model = LinearRegression().fit(x_train, y_train)
    predicted = model.predict(x_test)
    mae = float(mean_absolute_error(y_test, predicted))
    return model, {'r2': round(float(r2_score(y_test, predicted)), 4), 'mae': round(mae, 2),
                   'train': len(x_train), 'test': len(x_test), 'rows': len(x),
                   'coefficients': model.coef_.round(4).tolist(), 'intercept': round(float(model.intercept_), 4),
                   'points': [{'real': round(float(a), 2), 'predicted': round(float(b), 2)} for a,b in zip(y_test, predicted)]}


@lru_cache(maxsize=1)
def regression_model():
    return fit_regression(*regression_data())


@lru_cache(maxsize=1)
def digit_model():
    digits = load_digits()
    features = np.array([digit_features((image * 255 / 16).astype(np.uint8)).ravel() for image in digits.images])
    x_train, x_test, y_train, y_test = train_test_split(features, digits.target, test_size=.25, random_state=42, stratify=digits.target)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1500, C=.1))
    model.fit(x_train, y_train)
    predicted = model.predict(x_test)
    return model, {'accuracy': round(float(accuracy_score(y_test, predicted)), 4),
                   'train': len(x_train), 'test': len(x_test), 'rows': len(digits.data),
                   'confusion': confusion_matrix(y_test, predicted).tolist()}


def digit_features(gray):
    """Misma normalización para el dataset, los ejemplos y el lienzo."""
    border = np.concatenate([gray[0], gray[-1], gray[:, 0], gray[:, -1]])
    if np.median(border) > 128:
        gray = 255 - gray
        border = 255 - border
    gray = np.clip(gray.astype(float) - np.median(border), 0, 255)
    if gray.max() < 40:
        raise ValueError('Dibuja un número grande en el recuadro antes de reconocerlo.')
    gray = (gray * 255 / gray.max()).astype(np.uint8)
    coords = cv2.findNonZero((gray > 35).astype(np.uint8))
    if coords is None:
        raise ValueError('Dibuja un número antes de reconocerlo.')
    x, y, w, h = cv2.boundingRect(coords)
    crop = gray[y:y+h, x:x+w]
    # Digits ocupa la altura del cuadro y deja margen lateral.
    width = max(1, min(6, round(8 * w / h)))
    resized = cv2.resize(crop, (width, 8), interpolation=cv2.INTER_AREA)
    result = np.zeros((8, 8), dtype=float)
    start = (8-width)//2
    result[:, start:start+width] = resized * (16.0 / 255)
    return result


@app.get('/api/models')
def models():
    with LOCK:
        _, reg = regression_model()
        _, digit = digit_model()
    return jsonify(regression=reg, digits=digit)


@app.post('/api/predict')
def predict():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError('Envía los datos del formulario.')
        row = [number(data, 'grams', 10, 500), number(data, 'hours', .5, 18), number(data, 'complexity', 0, 100)]
        model, metrics = regression_model()
        value = float(model.predict([row])[0])
        contributions = [round(float(v*c),2) for v,c in zip(row, model.coef_)]
        return jsonify(prediction=round(value,2), contributions=contributions, base=metrics['intercept'], mae=metrics['mae'],
                       note='Estimación académica con datos sintéticos. No constituye una cotización comercial.')
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@app.get('/api/dataset')
def dataset():
    x, y = regression_data()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['gramos', 'horas', 'complejidad', 'costo'])
    for features, target in zip(x, y):
        writer.writerow([*(round(float(v),3) for v in features), round(float(target),3)])
    return send_file(io.BytesIO(output.getvalue().encode('utf-8-sig')), mimetype='text/csv', as_attachment=True, download_name='nexo_dataset_sintetico.csv')


@app.post('/api/train')
def train():
    try:
        upload = request.files.get('dataset')
        if upload is None:
            raise ValueError('Selecciona un archivo CSV.')
        raw = upload.read(512_001)
        if len(raw) > 512_000:
            raise ValueError('El CSV debe pesar menos de 500 KB.')
        try:
            reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
            if reader.fieldnames != ['gramos', 'horas', 'complejidad', 'costo']:
                raise ValueError('Usa estas columnas y este orden: gramos,horas,complejidad,costo.')
            rows = []
            for row in reader:
                if len(rows) >= 2000:
                    raise ValueError('El máximo es 2000 filas.')
                values = [number(row,'gramos',10,500),number(row,'horas',.5,18),number(row,'complejidad',0,100),number(row,'costo',0,10000)]
                rows.append(values)
        except UnicodeDecodeError:
            raise ValueError('Guarda el archivo CSV con codificación UTF-8.')
        if len(rows) < 20:
            raise ValueError('Necesitamos al menos 20 filas para separar entrenamiento y prueba.')
        array = np.array(rows)
        if np.any(np.std(array, axis=0) < 1e-8):
            raise ValueError('Cada columna necesita variación; revisa los datos del CSV.')
        _, metrics = fit_regression(array[:, :3], array[:, 3])
        metrics['source'] = 'Tu CSV · experimento independiente; no reemplaza el modelo de demostración'
        return jsonify(metrics)
    except (ValueError, csv.Error) as exc:
        return jsonify(error=str(exc)), 400


@app.get('/api/digit-example/<int:digit>')
def digit_example(digit):
    if digit not in range(10):
        return jsonify(error='Elige un dígito entre 0 y 9.'), 400
    digits = load_digits()
    sample = digits.images[np.flatnonzero(digits.target == digit)[0]]
    image = cv2.resize((sample*255/16).astype(np.uint8), (280,280), interpolation=cv2.INTER_NEAREST)
    return jsonify(image=encode(image))


@app.post('/api/digits')
def classify():
    try:
        image, _ = read_image()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        small = digit_features(gray)
        model, metrics = digit_model()
        probabilities = model.predict_proba([small.ravel()])[0]
        order = np.argsort(probabilities)[::-1]
        return jsonify(digit=int(order[0]), confidence=round(float(probabilities[order[0]])*100,1),
                       probabilities=[{'digit':int(i),'value':round(float(probabilities[i])*100,2)} for i in order],
                       preview=encode(cv2.resize((small*255/16).astype(np.uint8),(160,160),interpolation=cv2.INTER_NEAREST)),
                       accuracy=metrics['accuracy'])
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
