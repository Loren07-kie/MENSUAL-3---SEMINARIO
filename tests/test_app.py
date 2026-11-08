import base64
import io
import unittest

import cv2
import numpy as np

from app import app, FILTERS


class LabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.image = np.zeros((100, 150, 3), dtype=np.uint8)
        cls.image[:, :75] = (90, 180, 230)
        cls.image[20:80, 50:100] = (20, 40, 160)
        cls.raw = cv2.imencode('.png', cls.image)[1].tobytes()

    def upload(self, data=None, raw=None):
        return self.client.post('/api/vision', data={'image': (io.BytesIO(raw or self.raw), 'test.png'), 'filter': 'original', 'strength': '50', **(data or {})})

    def test_home_and_assets(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Nexo Lab', response.text)
        for path in ['app.js', 'style.css', 'street.css', 'objects.js', 'experience.js', 'logo-graffiti.webp', 'creative-background.webp', 'vision-sample.jpg']:
            with self.subTest(path=path):
                response = self.client.get('/static/' + path)
                self.assertEqual(response.status_code, 200)
                response.close()

    def test_all_filters_and_dimensions(self):
        for key in FILTERS:
            with self.subTest(filter=key):
                response = self.upload({'filter': key})
                self.assertEqual(response.status_code, 200)
                data = response.json
                self.assertEqual((data['width'], data['height']), (150, 100))
                self.assertEqual(sum(data['histogram']), 15000)
                raw = base64.b64decode(data['image'].split(',')[1])
                image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_UNCHANGED)
                self.assertEqual(image.shape[:2], (100, 150))

    def test_grayscale_and_negative_are_correct(self):
        data = self.upload({'filter': 'invertir'}).json
        image = cv2.imdecode(np.frombuffer(base64.b64decode(data['image'].split(',')[1]), np.uint8), 1)
        np.testing.assert_array_equal(image, 255-self.image)
        data = self.upload({'filter': 'grises'}).json
        image = cv2.imdecode(np.frombuffer(base64.b64decode(data['image'].split(',')[1]), np.uint8), 0)
        np.testing.assert_array_equal(image, cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY))

    def test_invalid_images_and_filters(self):
        for data in [{'filter': 'invalid'}, {'strength': 'nan'}, {'strength': '101'}]:
            self.assertEqual(self.upload(data).status_code, 400)
        self.assertEqual(self.upload(raw=b'not an image').status_code, 400)
        self.assertEqual(self.client.post('/api/vision').status_code, 400)
        self.assertEqual(self.upload(raw=b'x'*(8*1024*1024+1)).status_code, 400)

    def test_regression_metrics_and_direction(self):
        metrics = self.client.get('/api/models').json
        r = metrics['regression']
        self.assertEqual((r['train'], r['test']), (180, 60))
        self.assertGreater(r['r2'], .9)
        self.assertGreater(r['mae'], 0)
        low = self.client.post('/api/predict', json={'grams': 20, 'hours': 1, 'complexity': 10}).json
        high = self.client.post('/api/predict', json={'grams': 400, 'hours': 15, 'complexity': 90}).json
        self.assertGreater(high['prediction'], low['prediction'])
        self.assertAlmostEqual(sum(high['contributions'])+high['base'], high['prediction'], delta=.03)
        for body in [None, [], {'grams': 'nan', 'hours': 4, 'complexity': 40}, {'grams': 1000, 'hours': 4, 'complexity': 40}]:
            self.assertEqual(self.client.post('/api/predict', json=body).status_code, 400)

    def test_csv_roundtrip_and_validation(self):
        csv = self.client.get('/api/dataset').data
        response = self.client.post('/api/train', data={'dataset': (io.BytesIO(csv), 'data.csv')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['rows'], 240)
        for invalid in [b'a,b\n1,2', b'gramos,horas,complejidad,costo\n10,1,1,10\n', b'gramos,horas,complejidad,costo\nNaN,1,1,10\n']:
            self.assertEqual(self.client.post('/api/train', data={'dataset': (io.BytesIO(invalid), 'bad.csv')}).status_code, 400)

    def test_digits_end_to_end(self):
        correct = 0
        for digit in range(10):
            data = self.client.get('/api/digit-example/'+str(digit)).json
            raw = base64.b64decode(data['image'].split(',')[1])
            response = self.client.post('/api/digits', data={'image': (io.BytesIO(raw), 'digit.png')})
            self.assertEqual(response.status_code, 200)
            correct += response.json['digit'] == digit
            self.assertAlmostEqual(sum(p['value'] for p in response.json['probabilities']), 100, delta=.1)
        self.assertGreaterEqual(correct, 9)
        data = self.client.get('/api/models').json['digits']
        self.assertGreater(data['accuracy'], .9)
        self.assertEqual(sum(map(sum, data['confusion'])), data['test'])
        blank = cv2.imencode('.png', np.full((280, 280, 3), (31, 41, 23), dtype=np.uint8))[1].tobytes()
        self.assertEqual(self.client.post('/api/digits', data={'image': (io.BytesIO(blank), 'blank.png')}).status_code, 400)
        self.assertEqual(self.client.get('/api/digit-example/12').status_code, 400)

    def test_object_catalog_and_real_inference(self):
        from pathlib import Path
        response = self.client.get('/api/objects/catalog')
        self.assertEqual(response.status_code, 200)
        catalog = response.json['classes']
        self.assertEqual(len(catalog), 1000)
        self.assertEqual(len(set(c['id'] for c in catalog)), 1000)
        self.assertGreater(sum(c['group'] == 'Objetos y alimentos' for c in catalog), 100)
        self.assertIn('ballpoint', [c['original'] for c in catalog])
        for sample, expected in [('banana','banana'),('laptop','notebook')]:
            raw = (Path(__file__).resolve().parents[1]/'static'/f'object-{sample}.jpg').read_bytes()
            response = self.client.post('/api/objects', data={'image': (io.BytesIO(raw),sample+'.jpg')})
            self.assertEqual(response.status_code, 200)
            data = response.json
            self.assertEqual(data['total_classes'], 1000)
            self.assertEqual(len(data['predictions']), 5)
            self.assertEqual(data['predictions'][0]['original'], expected)
            self.assertGreater(data['predictions'][0]['probability'], 40)
        self.assertEqual(self.client.post('/api/objects').status_code,400)
        self.assertEqual(self.client.post('/api/objects',data={'image':(io.BytesIO(b'bad'),'bad.png')}).status_code,400)


if __name__ == '__main__':
    unittest.main()
