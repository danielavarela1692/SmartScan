# Automatización de facturas de servicios

Reemplaza la carga manual en Boolfy: recibe la factura (mail, escaneo o carga
manual), extrae los datos del comprobante, y los deja listos para que el
motor de matching (fase 2) resuelva `cuenta_contable` y el alta llame
directamente a nuestra API existente hacia Eiffel (fase 3).

Alcance: sólo facturas de **servicios**. Sin orden de compra ni remitos.

## Qué hay implementado (fase 1 — ingesta y extracción)

- `facturas.ingestion` — trae los PDF: desde una casilla de mail (IMAP) o
  desde una carpeta local, para probar sin depender del mail todavía.
- `facturas.classification` — decide si un PDF tiene texto embebido
  (factura electrónica AFIP) o es una imagen escaneada, mirando si `pypdf`
  puede extraerle texto.
- `facturas.extraction` — dos caminos según la clasificación:
  - `pdf_structured.py`: parsea el texto embebido con regex. Es un punto de
    partida — hay que ajustar los patrones contra facturas reales de los
    proveedores que se vayan a procesar.
  - `ocr_extractor.py`: interfaz para OCR de documentos escaneados. No tiene
    credenciales cargadas — hay que elegir un proveedor (Azure Document
    Intelligence o Google Document AI, ver sección 07 de la especificación)
    y completar `.env`.
- `facturas.models` — el mismo contrato `ServiceExpenseInput` que ya usa
  Boolfy para el alta en Eiffel, para no tener que traducir campos más
  adelante.
- `facturas.pipeline` — encadena todo lo anterior y devuelve un
  `ServiceExpenseInput` parcialmente completo: todo lo que se puede sacar
  del PDF queda lleno; `cuenta_contable` de cada línea queda vacío a
  propósito, porque ese matching es la fase 2.

## Qué falta (fuera de alcance de este commit)

- **Fase 2**: motor de matching (proveedor por CUIT, ítem de compra por
  texto exacto contra el catálogo de Eiffel) y panel de revisión humana.
- **Fase 3**: conectar con nuestra API existente para el alta real —
  bloqueado por dos preguntas todavía sin responder por el programador:
  dónde vive exactamente el CAE (`comprobante_final` vs `comprobante_numero`)
  y cómo se genera `Identifier` sin que Boolfy esté en el medio.
- **Fase 4**: aprendizaje de mapeos manuales y dashboard de KPIs.

## Cómo correrlo

Requiere Python 3.10+ (no está instalado en esta máquina todavía).

```bash
pip install -e ".[dev]"
cp .env.example .env   # completar credenciales de mail / OCR
pytest
python -m facturas.cli run --source manual --path ./inbox
```

`--source manual` lee PDFs de la carpeta `./inbox` — sirve para probar el
pipeline de extracción sin conectar un mail todavía. `--source email` usa
las credenciales IMAP de `.env`.
