# Nexo Lab · Proyecto Significativo 3

**Ideas que toman forma.** Laboratorio web de inteligencia aplicada que integra las semanas 9, 10, 11 y 12: Machine Learning, Git/GitHub, cámara y manipulación de imágenes con OpenCV.

Estudiante: **Lorena Abigail Coca Ccorpa** · SENATI · 2026.

## Experiencias

- **Estudio de visión:** subir, arrastrar o capturar una fotografía; once modos (incluido el original), comparación antes/después, histograma, luminosidad, contraste, nitidez y descarga PNG. Detección de rostros frontales con Haar; no identifica personas ni reconoce emociones.
- **Taller predictivo:** regresión lineal múltiple para estimar costos de impresión 3D a partir de gramos, horas y complejidad. Explicación de aportes, gráfico real/predicho, R² y MAE calculados sobre prueba, CSV de ejemplo y entrenamiento de experimentos independientes con CSV propio.
- **Reconocimiento IA:** lienzo táctil para dibujar dígitos, ejemplos del dataset Digits, clasificación con regresión logística, distribución de probabilidades, entrada 8×8 y matriz de confusión.
- **Ruta de aprendizaje:** relación explícita entre clases y funciones, arquitectura y documentación oficial.
- **Bitácora:** últimos 100 experimentos en localStorage, exportación JSON y borrado con confirmación. No almacena imágenes.

## Ejecutar en Windows

Se recomienda **Python 3.13** (Render utiliza esa versión).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Abrir http://127.0.0.1:5000. La cámara funciona en localhost o con HTTPS, previa autorización del navegador. Detener con Ctrl+C.

```powershell
python -m unittest discover -s tests -v
node --check static/app.js
```

Gunicorn es el servidor de producción para Linux/Render; en Windows usar `python app.py`.

## Arquitectura

Frontend HTML/Jinja + Bootstrap 5.3.8 + CSS propio + JavaScript → API Flask → OpenCV / NumPy / scikit-learn. Un único servicio web sirve frontend y backend, sin CORS ni claves externas. Los gráficos se dibujan con Canvas, sin depender de una biblioteca remota.

| Ruta | Función |
|---|---|
| `GET /health` | Estado del servidor |
| `POST /api/vision` | Imagen multipart `image`, `filter`, `strength` |
| `GET /api/models` | Métricas de modelos y matriz de confusión |
| `POST /api/predict` | JSON `grams`, `hours`, `complexity` |
| `GET /api/dataset` | CSV sintético reproducible |
| `POST /api/train` | CSV multipart `dataset`, experimento independiente |
| `GET /api/digit-example/0` | Ejemplo del dataset, números del 0 al 9 |
| `POST /api/digits` | Clasificar imagen multipart `image` |

## Datos, evaluación y límites

La regresión utiliza **240 filas sintéticas**, generadas con semilla 42. Fórmula de generación: `8 + .095*gramos + 3.8*horas + .18*complejidad + ruido normal(0,2.5)`. Son **180 registros de entrenamiento y 60 de prueba**. No son ventas ni cotizaciones reales. R² alto refleja la relación lineal de estos datos; no demuestra validez comercial. MAE es error medio global, no intervalo de confianza.

El clasificador utiliza **1797 imágenes Digits** de scikit-learn; separación estratificada con semilla 42: **1347 entrenamiento / 450 prueba**. Se aplica idéntica normalización a entrenamiento, prueba y entradas: corrección de fondo, recorte y centrado en 8×8. StandardScaler y regresión logística se ajustan solamente con entrenamiento. Es un clasificador clásico, no una red neuronal ni un modelo Teachable Machine. Un dibujo libre puede diferir del dataset; los ejemplos tampoco garantizan acierto. La probabilidad del modelo no es una garantía ni una métrica de precisión global.

No se inventan resultados de modelos PyTorch o Teachable Machine. Esas herramientas aparecen como conocimientos de la semana 9; esta implementación utiliza scikit-learn para mantener el despliegue ligero y explicable.

Las métricas se calculan al iniciar el primer experimento y se conservan en memoria. Los modelos se reconstruyen de forma determinista al reiniciar el proceso. El CSV propio se procesa y evalúa en memoria; no reemplaza el modelo compartido ni se conserva después de responder. No se deserializan modelos enviados por usuarios.

Imágenes: JPG/PNG/WebP, máximo 8 MB y 20 MP, reducción a 1600 px por lado, corrección EXIF. Archivos procesados en memoria, sin guardarlos en disco ni registrar su contenido. La detección de rostros puede producir falsos positivos y falsos negativos. Una foto de alta resolución se reduce antes de procesarse. CSV: 20 a 2000 filas, UTF-8, hasta 500 KB, columnas exactas `gramos,horas,complejidad,costo` y validación de valores finitos.

El historial reside en el navegador del visitante; no es una base de datos compartida ni un sistema de cuentas. No introducir información sensible en los experimentos. El prototipo tiene límites de tamaño pero no incorpora una cuota distribuida por usuario.

## Desplegar en Render

Servicio web Python, región Oregon, plan free, rama main.

```text
Build: pip install -r requirements.txt
Start: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120
PYTHON_VERSION=3.13.5
OPENBLAS_NUM_THREADS=1
OMP_NUM_THREADS=1
```

El plan gratuito puede suspenderse por inactividad; el primer acceso puede tardar. No se requiere almacenamiento persistente. `/health` proporciona una comprobación HTTP de salud. El archivo `render.yaml` documenta la configuración reproducible; no crear otro servicio si ya existe el despliegue de este proyecto.

## Recursos y créditos

- Identidad Nexo Lab: símbolo SVG original y diseño propio para el proyecto. No representa un producto oficial de SENATI.
- Fotografía de robótica: [Unsplash, imagen 1485827404703-89b55fcc595e](https://images.unsplash.com/photo-1485827404703-89b55fcc595e), copia local `static/lab-hero.jpg`.
- Fotografía de montaña: [Unsplash, imagen 1464822759023-fed622ff2c3b](https://images.unsplash.com/photo-1464822759023-fed622ff2c3b), copia local `static/vision-sample.jpg`.
- [Licencia Unsplash](https://unsplash.com/license).
- [Bootstrap](https://getbootstrap.com/docs/5.3/) y [Bootstrap Icons](https://icons.getbootstrap.com/), MIT; cargados desde jsDelivr.
- DM Sans y Manrope, Google Fonts. Si no hay acceso a la red, se utilizan fuentes del sistema.
- [OpenCV](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html), [scikit-learn / Digits](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html), [Flask](https://flask.palletsprojects.com/).

## Relación con los proyectos anteriores

Se revisó EduShield IA del mensual 2 (alerta de deserción y seguimiento) y los materiales compartidos de las cuatro semanas. Este proyecto amplía la experiencia con procesamiento visual, cámara, comparación interactiva, modelos explicados y experimentación con datos propios. Conserva el enfoque académico y diferencia resultados reales calculados de datos sintéticos de práctica.
