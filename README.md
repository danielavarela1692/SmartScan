# Automatización de facturas de servicios

Reemplaza la carga manual en Boolfy: recibe la factura (mail, escaneo o carga
manual), extrae los datos del comprobante, resuelve a qué ítem de compra de
Eiffel corresponde cada línea, y deja todo listo para que la fase 3 llame
directamente a nuestra API existente hacia Eiffel.

Alcance de esta etapa: sólo facturas de **servicios**. Sin orden de compra ni
remitos — la visión a futuro del producto sí los incluye (ver sección 01 de
la especificación), pero el MVP se mantiene acotado a esto.

## Qué hay implementado

### Fase 1 — ingesta y extracción

- `facturas.ingestion` — trae los PDF: desde una casilla de mail (IMAP) o
  desde una carpeta local, para probar sin depender del mail todavía.
- `facturas.classification` — decide si un PDF tiene texto embebido
  (factura electrónica AFIP) o es una imagen escaneada, mirando si `pypdf`
  puede extraerle texto.
- `facturas.extraction` — dos caminos según la clasificación:
  - `pdf_structured.py`: parsea el texto embebido con regex (encabezado y
    líneas de detalle). Es un punto de partida — hay que ajustar los
    patrones contra facturas reales de cada proveedor nuevo.
  - `ocr_extractor.py`: interfaz para OCR de documentos escaneados. No tiene
    credenciales cargadas — hay que elegir un proveedor (Azure Document
    Intelligence o Google Document AI) y completar `.env`.
- `facturas.models` — el mismo contrato `ServiceExpenseInput` que ya usa
  Boolfy para el alta en Eiffel, para no tener que traducir campos más
  adelante. Confirmado línea por línea contra el código fuente real de esa
  API (ver especificación, sección 08).

### Fase 2 — motor de matching + resolución humana

- `facturas.matching.client` — trae el catálogo de ítems de compra desde la
  API real (`GET /api/Expense/items`, tras loguearse en `/api/Auth/login`),
  o desde un catálogo de prueba local (`fixtures/items_catalog.example.json`)
  mientras no tengamos credenciales propias.
- `facturas.matching.engine` — para cada línea de la factura: primero busca
  si una persona ya resolvió ese mismo texto para ese mismo proveedor antes;
  si no, busca coincidencia exacta de texto contra el catálogo de ese
  proveedor puntual; si tampoco, la deja pendiente de revisión humana.
- `facturas.matching.store` — guarda las elecciones humanas en
  `data/learned_matches.json` (por CUIT + texto de línea), para que la
  próxima vez se resuelvan solas.
- `facturas.pipeline.resolve_concepts` — aplica todo lo anterior sobre el
  `ServiceExpenseInput` ya extraído.

## Qué falta

- **Fase 2**: hoy la revisión humana es por consola (`cli.py match`); falta
  la pantalla real (ver el mockup del panel de revisión en la
  especificación).
- **Fase 3**: conectar el alta real a `POST /api/Expense` — el diseño ya
  está resuelto (ver especificación, sección 04), sólo falta que nos den un
  usuario propio para autenticarnos.
- **Fase 4**: dashboard de KPIs y matching aproximado sobre el histórico.
- **Otros canales de ingesta** (WhatsApp, fotos) y **otros tipos de
  comprobante** (compra de bienes, con descarga de orden de compra y
  seguimiento de remito) quedan fuera de este MVP pero el diseño ya los
  contempla: sumar un canal nuevo es agregar una clase `Source` más: sumar
  un tipo de comprobante nuevo no debería requerir tocar lo que ya funciona.

## Cómo correrlo

```bash
pip install -e ".[dev]"
cp .env.example .env   # completar credenciales de mail / OCR / API
pytest
python -m facturas.cli run --source manual --path ./inbox
```

`--source manual` lee PDFs de la carpeta `./inbox` — sirve para probar el
pipeline de extracción sin conectar un mail todavía. `--source email` usa
las credenciales IMAP de `.env`.

Para además resolver el ítem de compra de cada línea (fase 2):

```bash
python -m facturas.cli match --source manual --path ./inbox --outbox ./outbox
```

Si una línea no tiene coincidencia exacta, el comando te muestra las
opciones de ese proveedor por consola y te pide que elijas una — la próxima
vez que aparezca el mismo texto, ya no pregunta más. El resultado final
(con `cuenta_contable` resuelto en cada línea) queda guardado en
`./outbox/<archivo>.json`, listo para la fase 3.

Sin `EIFFEL_API_BASE_URL` configurado en `.env`, el catálogo de ítems de
compra se lee de `fixtures/items_catalog.example.json` (datos de prueba,
no reales) — útil para probar el mecanismo mientras no tengamos
credenciales propias contra la API real.
