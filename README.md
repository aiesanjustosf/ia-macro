# IA Resumen Bancario – Banco Macro

Herramienta interna AIE San Justo para procesar extractos PDF de Banco Macro.

## Funciones

- Lectura de PDF con texto seleccionable.
- Separación de cuentas Macro.
- Conciliación por saldo.
- Clasificación de movimientos.
- Resumen operativo IVA.
- Control de Ley 25.413 / DyC contra el total informado por el PDF cuando existe.
- Detalle de créditos y préstamos.
- Exportación a Excel y PDF.

## Correcciones incluidas

- `N/D DEBITO PRESTAMOS REC` y variantes quedan clasificadas como `Cuota de préstamo`.
- Variantes de acreditación de préstamos quedan clasificadas como `Acreditación Préstamos`.
- DyC queda unificado dentro de `LEY 25.413` para que entre en el resumen operativo.
- El total de Ley 25.413 / DyC se calcula neteando débitos menos créditos.
- Se agrega control contra `TOTAL COBRADO DEL IMP.S/CREDS. Y DEBS. EN CTAS. BANCARIAS`.

## Estructura

```text
ia-resumen-macro/
├── app.py
├── requirements.txt
├── README.md
├── assets/
│   ├── logo_aie.png
│   └── favicon-aie.ico
└── modules/
    ├── __init__.py
    ├── extraction.py
    ├── parsing.py
    ├── classification.py
    ├── reports.py
    └── formatting.py
```

## Uso local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Assets

Colocar en `assets/`:

- `logo_aie.png`
- `favicon-aie.ico`

La app funciona aunque esos archivos no estén presentes.
