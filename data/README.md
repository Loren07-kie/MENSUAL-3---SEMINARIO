# Datos incluidos con Nexo Lab

- `impresion_3d.csv`: 240 filas sintéticas, cuatro columnas. Semilla 42, generador NumPy, fórmula `8 + .095*gramos + 3.8*horas + .18*complejidad + ruido N(0,2.5)`. No son cotizaciones reales.
- `digits.csv`: las 1797 imágenes Digits incluidas originalmente en `sklearn.datasets.load_digits`, exportadas para que los datos de entrenamiento estén presentes y se puedan inspeccionar sin descargas. Columnas `pixel_0` a `pixel_63`, intensidades 0–16, y `digit` como etiqueta 0–9.
- `examples/digit_0.png` a `digit_9.png`: un ejemplo real de cada clase, ampliado con vecino más cercano para ver los píxeles.

Origen Digits: https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html y UCI Optical Recognition of Handwritten Digits. El cuaderno explica la separación estratificada, la normalización, el entrenamiento y la evaluación.

Las imágenes aumentadas del experimento Jupyter son rotaciones de ±8° derivadas **solo de entrenamiento**. Las imágenes de prueba no se aumentan ni se utilizan para ajustar el modelo. No se presentan estas transformaciones como imágenes generativas.
