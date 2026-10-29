const MAX_BYTES = 10 * 1024 * 1024;

const fileInput = document.querySelector('#file');
const drop = document.querySelector('#drop');
const analyzeButton = document.querySelector('#analyze');
const sampleButton = document.querySelector('#sample');
const retryButton = document.querySelector('#retry');
const errorBox = document.querySelector('#error');
const statusBox = document.querySelector('#status');
const previewWrap = document.querySelector('#preview-wrap');
const preview = document.querySelector('#preview');
const fileMeta = document.querySelector('#file-meta');
const results = document.querySelector('#results');
const emptyNote = document.querySelector('#empty');
const countEl = document.querySelector('#count');
const meanEl = document.querySelector('#mean');
const largestEl = document.querySelector('#largest');
const smallestEl = document.querySelector('#smallest');
const originalImg = document.querySelector('#original');
const overlayImg = document.querySelector('#overlay');
const rowsEl = document.querySelector('#rows');
const csvButton = document.querySelector('#csv');
const pngButton = document.querySelector('#png');

let selectedFile = null;
let previewUrl = null;
let objects = [];
let sortKey = 'id';
let sortDir = 1;

function allowed(file) {
  const type = (file.type || '').toLowerCase();
  const name = (file.name || '').toLowerCase();
  return (
    type === 'image/png' ||
    type === 'image/jpeg' ||
    type === 'image/jpg' ||
    name.endsWith('.png') ||
    name.endsWith('.jpg') ||
    name.endsWith('.jpeg')
  );
}

function showError(message, canRetry) {
  errorBox.textContent = message;
  errorBox.hidden = false;
  retryButton.hidden = !canRetry;
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = '';
  retryButton.hidden = true;
}

function setBusy(busy) {
  statusBox.hidden = !busy;
  analyzeButton.disabled = busy || !selectedFile;
  sampleButton.disabled = busy;
  retryButton.disabled = busy;
  fileInput.disabled = busy;
}

function clearResults() {
  results.hidden = true;
  objects = [];
  rowsEl.replaceChildren();
}

function formatArea(value) {
  if (value === null || value === undefined) return '—';
  const number = Number(value);
  if (Number.isInteger(number)) return number.toLocaleString();
  return number.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function acceptFile(file) {
  clearError();
  clearResults();
  if (!file) return;
  if (!allowed(file)) {
    selectedFile = null;
    analyzeButton.disabled = true;
    previewWrap.hidden = true;
    showError('Upload a PNG or JPEG image.', false);
    return;
  }
  if (file.size > MAX_BYTES) {
    selectedFile = null;
    analyzeButton.disabled = true;
    previewWrap.hidden = true;
    showError('Image must be 10 MB or smaller.', false);
    return;
  }
  selectedFile = file;
  analyzeButton.disabled = false;
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  preview.src = previewUrl;
  originalImg.src = previewUrl;
  previewWrap.hidden = false;
  fileMeta.textContent = file.name;
  preview.onload = () => {
    fileMeta.textContent = `${file.name} · ${preview.naturalHeight}×${preview.naturalWidth}`;
  };
}

async function runAnalysis(file) {
  setBusy(true);
  clearError();
  const form = new FormData();
  form.append('image', file, file.name || 'upload.png');
  try {
    const response = await fetch('/api/analyze', { method: 'POST', body: form });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = body.detail;
      const message = typeof detail === 'string'
        ? detail
        : 'Something went wrong. Try again.';
      throw new Error(message);
    }
    renderResult(body);
  } catch (error) {
    const message = error.message || 'Something went wrong. Try again.';
    showError(message, Boolean(selectedFile));
  } finally {
    setBusy(false);
  }
}

function renderResult(body) {
  const summary = body.summary || {};
  objects = body.objects || [];
  countEl.textContent = String(summary.count ?? 0);
  meanEl.textContent = formatArea(summary.mean_area);
  largestEl.textContent = formatArea(summary.max_area);
  smallestEl.textContent = formatArea(summary.min_area);
  emptyNote.hidden = (summary.count ?? 0) !== 0;
  overlayImg.src = `data:image/png;base64,${body.overlay_png}`;
  if (body.height && body.width) {
    fileMeta.textContent = `${selectedFile ? selectedFile.name : 'image'} · ${body.height}×${body.width}`;
  }
  sortKey = 'id';
  sortDir = 1;
  paintTable();
  results.hidden = false;
}

function sortedObjects() {
  const copy = objects.slice();
  copy.sort((a, b) => {
    const av = sortKey === 'centroid' ? a.centroid_row : a[sortKey];
    const bv = sortKey === 'centroid' ? b.centroid_row : b[sortKey];
    if (av < bv) return -sortDir;
    if (av > bv) return sortDir;
    return 0;
  });
  return copy;
}

function paintTable() {
  rowsEl.replaceChildren();
  document.querySelectorAll('th button').forEach((button) => {
    if (button.dataset.key === sortKey) {
      button.setAttribute('aria-sort', sortDir === 1 ? 'ascending' : 'descending');
    } else {
      button.removeAttribute('aria-sort');
    }
  });
  sortedObjects().forEach((row) => {
    const tr = document.createElement('tr');
    const cells = [
      row.id,
      formatArea(row.area),
      `${row.centroid_row}, ${row.centroid_col}`,
      formatArea(row.perimeter),
    ];
    cells.forEach((value) => {
      const td = document.createElement('td');
      td.textContent = String(value);
      tr.appendChild(td);
    });
    rowsEl.appendChild(tr);
  });
}

function download(filename, href) {
  const link = document.createElement('a');
  link.href = href;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

fileInput.addEventListener('change', () => {
  acceptFile(fileInput.files[0]);
});

['dragenter', 'dragover'].forEach((name) => {
  drop.addEventListener(name, (event) => {
    event.preventDefault();
    drop.classList.add('hot');
  });
});

['dragleave', 'drop'].forEach((name) => {
  drop.addEventListener(name, (event) => {
    event.preventDefault();
    drop.classList.remove('hot');
  });
});

drop.addEventListener('drop', (event) => {
  const file = event.dataTransfer.files[0];
  acceptFile(file);
});

analyzeButton.addEventListener('click', () => {
  if (selectedFile) runAnalysis(selectedFile);
});

retryButton.addEventListener('click', () => {
  if (selectedFile) runAnalysis(selectedFile);
});

sampleButton.addEventListener('click', async () => {
  clearError();
  setBusy(true);
  try {
    const response = await fetch('/api/sample');
    if (!response.ok) throw new Error('Sample image is unavailable. Try again.');
    const blob = await response.blob();
    const file = new File([blob], 'sample-coins.png', { type: 'image/png' });
    acceptFile(file);
    await runAnalysis(file);
  } catch (error) {
    showError(error.message || 'Something went wrong. Try again.', false);
    setBusy(false);
  }
});

document.querySelectorAll('th button').forEach((button) => {
  button.addEventListener('click', () => {
    const key = button.dataset.key;
    if (sortKey === key) sortDir = -sortDir;
    else {
      sortKey = key;
      sortDir = 1;
    }
    paintTable();
  });
});

csvButton.addEventListener('click', () => {
  const lines = ['id,area,centroid_row,centroid_col,perimeter'];
  sortedObjects().forEach((row) => {
    lines.push(
      [row.id, row.area, row.centroid_row, row.centroid_col, row.perimeter].join(',')
    );
  });
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  download('objects.csv', url);
  setTimeout(() => URL.revokeObjectURL(url), 1500);
});

pngButton.addEventListener('click', () => {
  if (overlayImg.src) download('annotated.png', overlayImg.src);
});
