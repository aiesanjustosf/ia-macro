import io
from pathlib import Path

import streamlit as st

from modules.extraction import extract_all_lines, text_from_pdf
from modules.parsing import macro_split_account_blocks
from modules.reports import render_account_report

HERE = Path(__file__).parent
LOGO = HERE / "assets" / "logo_aie.png"
FAVICON = HERE / "assets" / "favicon-aie.ico"

st.set_page_config(
    page_title="IA Resumen Bancario – Banco Macro",
    page_icon=str(FAVICON) if FAVICON.exists() else None,
    layout="centered",
)

if LOGO.exists():
    st.image(str(LOGO), width=200)

st.title("IA Resumen Bancario – Banco Macro")
st.caption("Herramienta para uso interno AIE San Justo")

uploaded = st.file_uploader("Subí un PDF del resumen Banco Macro", type=["pdf"])
if uploaded is None:
    st.info("La app no almacena datos. Toda la información se procesa en la sesión actual.")
    st.stop()

data = uploaded.read()
text = text_from_pdf(io.BytesIO(data)).strip()

if not text:
    st.error(
        "No se pudo leer texto del PDF. "
        "Este resumen parece estar escaneado o no tiene texto seleccionable. "
        "Usá un PDF descargado desde home banking."
    )
    st.stop()

if "BANCO MACRO" not in text.upper() and "MACRO" not in text.upper():
    st.warning("El PDF no parece corresponder a Banco Macro. Se intentará procesar igualmente con la lógica Macro.")
else:
    st.success("Detectado: Banco Macro")

blocks = macro_split_account_blocks(io.BytesIO(data))

if not blocks:
    st.warning("No se detectaron encabezados de cuenta Macro. Se intentará procesar todo el PDF como una única cuenta.")
    lines = [line for _, line in extract_all_lines(io.BytesIO(data))]
    render_account_report("CUENTA (PDF completo)", "s/n", "macro-pdf-completo", lines)
else:
    st.caption(f"Información de su/s Cuenta/s: {len(blocks)} cuenta(s) detectada(s).")
    for block in blocks:
        render_account_report(block["titulo"], block["nro"], block["acc_id"], block["lines"])
