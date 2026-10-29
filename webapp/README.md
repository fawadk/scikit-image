# Acme image analysis

A local page for uploading a PNG or JPEG and seeing what is in it.
There is no login. Nothing is saved on the server.

From the repository root, with this checkout of scikit-image already installed:

```bash
pip install -r webapp/requirements.txt
uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. Use **Try a sample** or upload your own image, then **Analyze**.

Tests:

```bash
python -m pytest webapp/tests -q
```
