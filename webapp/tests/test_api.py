"""HTTP tests for the no-auth image upload page."""

import base64
from io import BytesIO

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from webapp.app import MAX_BYTES, app


@pytest.fixture
def client():
    return TestClient(app)


def _png_bytes(array):
    buffer = BytesIO()
    Image.fromarray(array).save(buffer, format='PNG')
    return buffer.getvalue()


def _two_blobs():
    image = np.zeros((80, 80), dtype=np.uint8)
    image[10:30, 10:30] = 255
    image[50:70, 45:70] = 255
    return image


def test_favicon_is_served(client):
    response = client.get('/favicon.ico')

    assert response.status_code == 200
    assert response.content.startswith(b'<svg') or response.content.startswith(b'\x89PNG')


def test_home_page_is_served_without_credentials(client):
    response = client.get('/')

    assert response.status_code == 200
    text = response.text.lower()
    assert 'acme' in text
    assert 'analyze' in text
    assert 'authorization' not in response.request.headers


def test_static_assets_are_local(client):
    css = client.get('/static/style.css')
    script = client.get('/static/app.js')

    assert css.status_code == 200
    assert 'text/css' in css.headers['content-type']
    assert script.status_code == 200
    assert 'cdn' not in script.text.lower()
    assert 'cdn' not in css.text.lower()


def test_analyze_png_returns_count_and_overlay(client):
    response = client.post(
        '/api/analyze',
        files={'image': ('blobs.png', _png_bytes(_two_blobs()), 'image/png')},
    )

    assert response.status_code == 200
    body = response.json()
    assert body['summary']['count'] == 2
    assert len(body['objects']) == 2
    assert {'id', 'area', 'centroid_row', 'centroid_col', 'perimeter'} <= set(
        body['objects'][0]
    )
    overlay = base64.b64decode(body['overlay_png'])
    assert overlay.startswith(b'\x89PNG')
    assert body['width'] == 80
    assert body['height'] == 80


def test_uniform_image_returns_zero_objects(client):
    blank = _png_bytes(np.zeros((40, 40), dtype=np.uint8))
    response = client.post(
        '/api/analyze',
        files={'image': ('blank.png', blank, 'image/png')},
    )

    assert response.status_code == 200
    assert response.json()['summary']['count'] == 0
    assert response.json()['objects'] == []


def test_text_upload_is_rejected(client):
    response = client.post(
        '/api/analyze',
        files={'image': ('notes.txt', b'not an image', 'text/plain')},
    )

    assert response.status_code == 400
    assert 'PNG or JPEG' in response.json()['detail']


def test_oversize_upload_is_rejected(client):
    payload = b'0' * (MAX_BYTES + 1)
    response = client.post(
        '/api/analyze',
        files={'image': ('big.png', payload, 'image/png')},
    )

    assert response.status_code == 413
    assert '10 MB' in response.json()['detail']


def test_sample_image_is_a_png(client):
    response = client.get('/api/sample')

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('image/png')
    assert response.content.startswith(b'\x89PNG')
    with Image.open(BytesIO(response.content)) as image:
        image.load()
        assert image.format == 'PNG'
        assert image.size[0] > 0 and image.size[1] > 0
