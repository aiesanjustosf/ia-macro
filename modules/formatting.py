import re

import numpy as np
import streamlit as st

LONG_INT_RE = re.compile(r"\b\d{6,}\b")


def normalize_money(tok: str) -> float:
    """
    Normaliza importes argentinos, aceptando:
    -2.114.972,30   ó   2.114.972,30-
    """
    if not tok:
        return np.nan
    tok = tok.strip().replace("−", "-")
    neg = tok.endswith("-") or tok.startswith("-")
    tok = tok.strip("-")
    if "," not in tok:
        return np.nan
    main, frac = tok.rsplit(",", 1)
    main = main.replace(".", "").replace(" ", "")
    try:
        val = float(f"{main}.{frac}")
        return -val if neg else val
    except Exception:
        return np.nan


def fmt_ar(n) -> str:
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    return f"{n:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")


def metric_full(label: str, value: str):
    """Alternativa a st.metric para evitar truncado con '...' en valores largos."""
    st.markdown(
        f"""
        <div style="padding:0.15rem 0;">
          <div style="font-size:0.85rem;color:rgba(49,51,63,0.6);margin-bottom:0.15rem;">
            {label}
          </div>
          <div style="
              font-size:1.65rem;
              font-weight:650;
              line-height:1.1;
              white-space:normal;
              overflow-wrap:anywhere;
              letter-spacing:-0.01em;">
            {value}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def normalize_desc(desc: str) -> str:
    if not desc:
        return ""
    u = desc.upper()
    for pref in ("SAN JUS ", "CASA RO ", "CENTRAL ", "GOBERNA ", "GOBERNADOR ", "SANTA FE ", "ROSARIO "):
        if u.startswith(pref):
            u = u[len(pref):]
            break
    u = LONG_INT_RE.sub("", u)
    u = " ".join(u.split())
    return u
