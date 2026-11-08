# Nexo Lab · Proyecto Significativo 3

**Ideas que toman forma.** Laboratorio web de inteligencia aplicada que integra las semanas 9, 10, 11 y 12: Machine Learning, Git/GitHub, cámara y manipulación de imágenes con OpenCV.

Estudiante: **Lorena Abigail Coca Ccorpa** · SENATI · 2026.

## Experiencias · versión 2

- **Estudio de visión:** subir, arrastrar o capturar una fotografía; once modos (incluido el original), comparación antes/después, histograma, luminosidad, contraste, nitidez y descarga PNG. Detección de rostros frontales con Haar; no identifica personas ni reconoce emociones.
- **Taller predictivo:** regresión lineal múltiple para estimar costos de impresión 3D a partir de gramos, horas y complejidad. Explicación de aportes, gráfico real/predicho, R² y MAE calculados sobre prueba, CSV de ejemplo y entrenamiento de experimentos independientes con CSV propio.
- **Reconocimiento IA:** lienzo táctil para dibujar dígitos, ejemplos del dataset Digits, clasificación con regresión logística, distribución de probabilidades, entrada 8×8 y matriz de confusión.
- **Reconocer objetos:** MobileNetV2 preentrenada sobre ImageNet, 1000 categorías (incluye más de 100 objetos cotidianos), fotografía o captura de cámara, recorte central, top-5 y catálogo buscable con traducciones frecuentes. Clasifica un contenido principal; no es un detector múltiple ni un sistema de emociones. Pesos ONNX descargados de su fuente oficial y verificados con SHA-256 al primer uso, ejecutados con OpenCV DNN.
- **Apariencia:** logo de imagen y fondo originales generados para el proyecto, títulos de grafiti, animación al desplazarse, movimiento suave y tres temas persistentes: beige, oscuro y blanco. Se respeta `prefers-reduced-motion`.
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
| `GET /api/objects/catalog` | Las 1000 categorías de ImageNet |
| `POST /api/objects` | Imagen multipart `image`, top-5 y recorte de entrada |

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

- Identidad Nexo Lab v2: logo raster `static/logo-graffiti.webp` y collage `static/creative-background.webp`, generados con ImageGen para este proyecto. El antiguo símbolo radial fue retirado. No representa un producto oficial de SENATI.
- Fotografía de robótica: [Unsplash, imagen 1485827404703-89b55fcc595e](https://images.unsplash.com/photo-1485827404703-89b55fcc595e), copia local `static/lab-hero.jpg`.
- Fotografía de montaña: [Unsplash, imagen 1464822759023-fed622ff2c3b](https://images.unsplash.com/photo-1464822759023-fed622ff2c3b), copia local `static/vision-sample.jpg`.
- [Licencia Unsplash](https://unsplash.com/license).
- [Bootstrap](https://getbootstrap.com/docs/5.3/) y [Bootstrap Icons](https://icons.getbootstrap.com/), MIT; cargados desde jsDelivr.
- DM Sans y Manrope, Google Fonts. Si no hay acceso a la red, se utilizan fuentes del sistema.
- [OpenCV](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html), [scikit-learn / Digits](https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html), [Flask](https://flask.palletsprojects.com/).

## Relación con los proyectos anteriores

Se revisó EduShield IA del mensual 2 (alerta de deserción y seguimiento) y los materiales compartidos de las cuatro semanas. Este proyecto amplía la experiencia con procesamiento visual, cámara, comparación interactiva, modelos explicados y experimentación con datos propios. Conserva el enfoque académico y diferencia resultados reales calculados de datos sintéticos de práctica.

## Cuaderno académico

El archivo `notebooks/Nexo_Lab_Proyecto_3.ipynb` está ejecutado e incluye análisis exploratorio, entrenamiento explícito, línea base, validación cruzada de regresión, diagnóstico de residuos, distribución de clases, matriz de confusión y aumento de imágenes de entrenamiento por rotación. También ejecuta MobileNetV2 sobre tres ejemplos y muestra sus errores. Instala `python -m pip install -r requirements-notebook.txt` para repetirlo en Jupyter o VS Code. Sus 21 celdas contienen resultados y gráficos calculados, no inventados.


## Modelo de objetos y recursos v2

Pesos: `models/mobilenetv2-7.onnx`, ONNX Model Zoo, MobileNetV2, Apache 2.0. Se descargan automáticamente al primer reconocimiento si no existen; no se versiona el binario. El tamaño y SHA-256 se verifican contra `models/manifest.json` antes de una sustitución atómica. La primera solicitud de cada instancia nueva puede tardar mientras se descargan 14 MB. Si falla la red, la API devuelve un error 503 explicativo y permite reintentar. Se incluyen la licencia y el README original en `models/`. Las 1000 etiquetas provienen de `pytorch/hub/imagenet_classes.txt`, en el mismo orden ImageNet-1K. Las traducciones son ayudas de interfaz, no nuevas clases. El vocabulario completo es consultable en la aplicación.

La red fue entrenada por sus autores. En Nexo Lab se ejecuta la inferencia; no se afirma haber entrenado un modelo de 1000 clases desde cero. El cuaderno sí entrena la regresión y dos clasificadores de dígitos (base y aumento). El dataset Digits y los costos están insertados en CSV en `data/` y se usan también en el backend.

Preprocesamiento de objetos: recorte cuadrado central previo a resize 256 para limitar memoria en fotos panorámicas, recorte central 224, RGB, escala [0,1], media [0.485,0.456,0.406], desviación [0.229,0.224,0.225], softmax. Solo un objeto principal; no hay cajas, conteos ni inferencia de emociones. Si una clase no existe en ImageNet, el modelo puede proponer una clase incorrecta. Menos del 40% en top-1 se presenta como resultado incierto. Ese umbral es una indicación de interfaz, no un detector calibrado de objetos desconocidos.

Fotografías de ejemplo (copias locales, Unsplash): laptop `photo-1496181133206-80ce9b88a853`, plátanos `photo-1571771894821-ce9b6c11b08e`, café `photo-1495474472287-4d71bcdd2085`. Son ejemplos exploratorios, no un conjunto para informar precisión de ImageNet. La foto de café ilustra una confusión del recorte central; se conservan los resultados reales y no se fuerza una etiqueta.

La cámara solo envía una captura al pulsar el botón y se detiene al salir de la sección, cerrar la captura o poner la página en segundo plano. Las imágenes se procesan en memoria y no se escriben en el servidor. La inferencia DNN se serializa con un lock para compartir con seguridad la red en los dos hilos Gunicorn.

## Cuentas y ficha personal · versión 3

Bienvenida flotante con fotografía de robot, explicación de los laboratorios, registro, inicio de sesión y acceso opcional como visitante. El nombre mostrado en «Hola» y en el perfil viene de la cuenta autenticada, no de un valor fijo ni de una fotografía.

El registro solicita nombre visible, usuario (3–32 letras ASCII, números o guion bajo) y contraseña (10–128 caracteres). No se crean cuentas con contraseñas públicas ni se envían correos. Esta versión no tiene recuperación de contraseña por correo.

Contraseñas con hash scrypt de Werkzeug; consultas parametrizadas; cookies HttpOnly, SameSite=Lax y Secure en Render; CSRF; rotación de sesión al entrar; sesiones revocables en base de datos y caducidad de siete días. Límites persistentes por conexión: 25 intentos de login o 10 registros por 15 minutos. No se incluyen contraseñas ni URLs privadas en GitHub.

Tablas exclusivas: `nexo_lab_users`, `nexo_lab_sessions`, `nexo_lab_auth_limits`. La aplicación no modifica tablas de otros proyectos. Se reutiliza `tecnoforms-history` con autorización del propietario. Su plan gratuito vence el 6 de diciembre de 2026 en Lima: habrá que exportar/migrar o ampliar ese recurso para conservar el servicio después de la fecha; no se contrata ningún plan de pago automáticamente.

Render configura `NEXO_DATABASE_URL` con `fromDatabase` y `NEXO_SECRET_KEY` con `generateValue` desde el Blueprint. Los secretos los resuelve la plataforma. Si no hay URL de Postgres en Render, los registros fallan de forma explícita; no se guardan silenciosamente en disco efímero. En desarrollo local se utiliza `data/accounts.sqlite3`, excluida de Git. Las pruebas usan bases temporales aisladas.

La ficha permite género autoseleccionado y opcional, nombre o alias, cabello, ojos, tono de piel, lentes y notas. Es la misma ficha para cualquier género; no infiere género, edad, etnia, emociones ni características de la fotografía. Sus datos y la fotografía se mantienen solo en memoria del navegador, no se envían a la API y no se guardan automáticamente. La exportación JSON contiene solo los campos escritos y no la foto. Cerrar sesión limpia la ficha. Las cuentas almacenadas en Postgres solo incluyen nombre visible, usuario, hash de contraseña y datos de sesión.

Endpoints: `GET /api/auth/me`, `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`. Los POST requieren el token recibido en `/me` como cabecera `X-CSRF-Token`. No hay listado público de usuarios ni rol de administrador implícito.
