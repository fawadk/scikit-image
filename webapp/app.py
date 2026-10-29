"""Local page for uploading an image and viewing object measurements.

No authentication. Results stay in the response; nothing is stored.
"""

import base64
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image

from webapp.analysis import ImageAnalysisError, analyze_image

MAX_BYTES = 10 * 1024 * 1024
STATIC_DIR = Path(__file__).resolve().parent / 'static'

app = FastAPI(title='Acme image analysis')
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

_sample_png = None


@app.get('/')
def home():
    return FileResponse(STATIC_DIR / 'index.html')


@app.get('/favicon.ico', include_in_schema=False)
def favicon():
    return FileResponse(STATIC_DIR / 'favicon.svg', media_type='image/svg+xml')


@app.get('/api/sample')
def sample_image():
    """Bundled public sample (scikit-image coins). No credentials required."""
    return Response(content=_coins_png(), media_type='image/png')


@app.post('/api/analyze')
async def analyze(image: UploadFile = File(...)):
    """Measure objects in one PNG or JPEG. No credentials required."""
    data = await image.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(
            status_code=413, detail='Image must be 10 MB or smaller.'
        )
    try:
        result = analyze_image(data)
    except ImageAnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        'summary': result['summary'],
        'objects': result['objects'],
        'overlay_png': base64.b64encode(result['overlay_png']).decode('ascii'),
        'width': result['width'],
        'height': result['height'],
    }


def _coins_png():
    global _sample_png
    if _sample_png is None:
        import skimage as ski

        buffer = BytesIO()
        Image.fromarray(ski.data.coins()).save(buffer, format='PNG')
        _sample_png = buffer.getvalue()
    return _sample_png
