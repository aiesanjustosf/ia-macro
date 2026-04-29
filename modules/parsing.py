import re

import numpy as np
import pandas as pd

from .extraction import extract_all_lines
from .formatting import normalize_desc, normalize_money

DATE_RE = re.compile(r"\b\d{1,2}/\d{2}/\d{2,4}\b")
MONEY_RE = re.compile(r'(?<!\S)-?(?:\d{1,3}(?:\.\d{3})*|\d+)\s?,\s?\d{2}-?(?!\S)')
HYPH = r"[-\u2010\u2011\u2012\u2013\u2014\u2212]"
ACCOUNT_TOKEN_RE = re.compile(rf"\b\d\s*{HYPH}\s*\d{{3}}\s*{HYPH}\s*\d{{10}}\s*{HYPH}\s*\d\b")
SALDO_ANT_PREFIX = re.compile(r"^SALDO\s+U?LTIMO\s+EXTRACTO\s+AL", re.IGNORECASE)
SALDO_FINAL_PREFIX = re.compile(r"^SALDO\s+FINAL\s+AL\s+D[ÍI]A", re.IGNORECASE)
RE_MACRO_ACC_START = re.compile(r"^CUENTA\s+(.+)$", re.IGNORECASE)
RE_HAS_NRO = re.compile(r"\bN[ROº°\.]*\s*:?\b", re.IGNORECASE)
RE_MACRO_ACC_NRO = re.compile(rf"N[ROº°\.]*\s*:?\s*({ACCOUNT_TOKEN_RE.pattern})", re.IGNORECASE)
PER_PAGE_TITLE_PAT = re.compile(rf"^CUENTA\s+.+N[ROº°\.]*\s*:?\s*({ACCOUNT_TOKEN_RE.pattern})", re.IGNORECASE)
HEADER_ROW_PAT = re.compile(r"^(FECHA\s+DESCRIPC(?:I[ÓO]N|ION)|FECHA\s+CONCEPTO|FECHA\s+DETALLE).*(SALDO|D[ÉE]BITO|CR[ÉE]DITO)", re.IGNORECASE)
NON_MOV_PAT = re.compile(r"(INFORMACI[ÓO]N\s+DE\s+SU/S\s+CUENTA/S|TOTAL\s+RESUMEN\s+OPERATIVO|RESUMEN\s+DEL\s+PER[IÍ]ODO)", re.IGNORECASE)
INFO_HEADER = re.compile(r"INFORMACI[ÓO]N\s+DE\s+SU/S\s+CUENTA/S", re.IGNORECASE)
MACRO_DYC_TOTAL_RE = re.compile(
    r"TOTAL\s+COBRADO\s+DEL\s+IMP\.S/CREDS\.?\s*Y\s+DEBS\.\s*EN\s+CTAS\.\s*BANCARIAS.*?"
    r"((?:\d{1,3}(?:\.\d{3})*|\d+)\s?,\s?\d{2})",
    re.IGNORECASE,
)

HOJA_NRO_RE = re.compile(r"\bHoja\s+Nro\.?:\s*(\d+)\b", re.IGNORECASE)


def macro_extract_all_lines_ordered(file_like):
    """Devuelve las líneas en el orden real del resumen Macro.

    Algunos PDFs de Macro vienen físicamente en orden inverso (Hoja 12, 11, ..., 1).
    Para que el cálculo por delta de saldo sea correcto, primero se reordena por Hoja Nro.
    """
    raw = extract_all_lines(file_like)
    pages = {}
    page_order = []
    for pi, ln in raw:
        if pi not in pages:
            pages[pi] = []
            page_order.append(pi)
        pages[pi].append(ln)

    def page_key(pi):
        joined = " ".join(pages.get(pi, []))
        m = HOJA_NRO_RE.search(joined)
        if m:
            return (0, int(m.group(1)), pi)
        return (1, pi, pi)

    ordered = []
    for pi in sorted(page_order, key=page_key):
        ordered.extend((pi, ln) for ln in pages[pi])
    return ordered


def _normalize_account_token(tok: str) -> str:
    return re.sub(rf"\s*{HYPH}\s*", "-", tok)


def _normalize_title_from_pending(pending_title: str) -> str:
    t = pending_title.upper()
    if "CORRIENTE" in t and "ESPECIAL" in t and ("DOLAR" in t or "DÓLAR" in t):
        return "CUENTA CORRIENTE ESPECIAL EN DOLARES"
    if "CORRIENTE" in t and "ESPECIAL" in t:
        return "CUENTA CORRIENTE ESPECIAL EN PESOS"
    if "CORRIENTE" in t:
        return "CUENTA CORRIENTE BANCARIA"
    if "CAJA DE AHORRO" in t:
        return "CAJA DE AHORRO"
    return "CUENTA"


def macro_extract_account_whitelist(file_like) -> dict:
    info = {}
    all_lines = macro_extract_all_lines_ordered(file_like)
    in_table = False
    last_tipo = None
    for _, ln in all_lines:
        if INFO_HEADER.search(ln):
            in_table = True
            continue
        if in_table:
            m_token = ACCOUNT_TOKEN_RE.search(ln)
            if m_token:
                nro = _normalize_account_token(m_token.group(0))
                u = ln.upper()
                if "CORRIENTE" in u and "ESPECIAL" in u and ("DOLAR" in u or "DÓLAR" in u or "DOLARES" in u or "DÓLARES" in u):
                    tipo = "CUENTA CORRIENTE ESPECIAL EN DOLARES"
                elif "CORRIENTE" in u and "ESPECIAL" in u:
                    tipo = "CUENTA CORRIENTE ESPECIAL EN PESOS"
                elif "CUENTA CORRIENTE BANCARIA" in u:
                    tipo = "CUENTA CORRIENTE BANCARIA"
                else:
                    tipo = last_tipo or "CUENTA"
                info[nro] = {"titulo": tipo}
                last_tipo = tipo
            else:
                if ln.strip().startswith("CUENTA ") and "NRO" in ln.upper():
                    break
    return info


def macro_split_account_blocks(file_like):
    whitelist = macro_extract_account_whitelist(file_like)
    white_set = set(whitelist.keys())
    all_lines = macro_extract_all_lines_ordered(file_like)
    accounts, order = {}, []
    current_nro = None
    pending_title = None
    expect_token_in = 0

    def open_block(nro: str, pi: int, titulo_hint: str | None):
        nonlocal current_nro
        titulo = (whitelist.get(nro, {}) or {}).get("titulo") or (titulo_hint and _normalize_title_from_pending(titulo_hint)) or "CUENTA"
        if nro not in accounts:
            accounts[nro] = {"titulo": titulo, "nro": nro, "lines": [], "pages": [pi, pi], "acc_id": nro}
            order.append(nro)
        else:
            accounts[nro]["pages"][1] = max(accounts[nro]["pages"][1], pi)
            if accounts[nro]["titulo"] == "CUENTA" and titulo != "CUENTA":
                accounts[nro]["titulo"] = titulo
        current_nro = nro

    for pi, ln in all_lines:
        m_title = RE_MACRO_ACC_START.match(ln)
        if m_title:
            pending_title = "CUENTA " + m_title.group(1).strip()
            expect_token_in = 12
            m_same_line = RE_MACRO_ACC_NRO.search(ln) or ACCOUNT_TOKEN_RE.search(ln)
            if m_same_line:
                nro = _normalize_account_token(m_same_line.group(1) if m_same_line.re is RE_MACRO_ACC_NRO else m_same_line.group(0))
                if (not white_set) or (nro in white_set):
                    open_block(nro, pi, pending_title)
                    pending_title = None
                    expect_token_in = 0
            continue

        if pending_title and expect_token_in > 0:
            expect_token_in -= 1
            m_nro = RE_MACRO_ACC_NRO.search(ln)
            if m_nro:
                nro = _normalize_account_token(m_nro.group(1))
                if (not white_set) or (nro in white_set):
                    open_block(nro, pi, pending_title)
                pending_title = None
                expect_token_in = 0
                continue
            m_tok = ACCOUNT_TOKEN_RE.search(ln)
            if m_tok:
                nro = _normalize_account_token(m_tok.group(0))
                if (not white_set) or (nro in white_set):
                    open_block(nro, pi, pending_title)
                pending_title = None
                expect_token_in = 0
                continue
            if RE_HAS_NRO.search(ln):
                expect_token_in = max(expect_token_in, 12)
                continue

        if (not pending_title) and white_set:
            m_fallback = ACCOUNT_TOKEN_RE.search(ln)
            if m_fallback:
                nro = _normalize_account_token(m_fallback.group(0))
                if nro in white_set and current_nro != nro:
                    open_block(nro, pi, None)

        if current_nro is not None:
            acc = accounts[current_nro]
            acc["lines"].append(ln)
            acc["pages"][1] = max(acc["pages"][1], pi)

    blocks = []
    for nro in order:
        acc = accounts[nro]
        acc["pages"] = tuple(acc["pages"])
        blocks.append(acc)
    return blocks


def parse_lines(lines) -> pd.DataFrame:
    rows = []
    seq = 0
    for ln in lines:
        if not ln.strip():
            continue
        if PER_PAGE_TITLE_PAT.search(ln) or HEADER_ROW_PAT.search(ln) or NON_MOV_PAT.search(ln):
            continue
        am = list(MONEY_RE.finditer(ln))
        if len(am) < 2:
            continue
        d = DATE_RE.search(ln)
        if not d or d.end() >= am[0].start():
            continue
        saldo = normalize_money(am[-1].group(0))
        importe = normalize_money(am[-2].group(0))
        first_money = am[0]
        desc = ln[d.end(): first_money.start()].strip()
        seq += 1
        rows.append({
            "fecha": pd.to_datetime(d.group(0), dayfirst=True, errors="coerce"),
            "descripcion": desc,
            "desc_norm": normalize_desc(desc),
            "debito": 0.0,
            "credito": 0.0,
            "importe": importe,
            "saldo": saldo,
            "pagina": 0,
            "orden": seq,
        })
    return pd.DataFrame(rows)


def _only_one_amount(line: str) -> bool:
    return len(list(MONEY_RE.finditer(line))) == 1


def _first_amount_value(line: str) -> float:
    m = MONEY_RE.search(line)
    return normalize_money(m.group(0)) if m else np.nan


def find_saldo_final_from_lines(lines):
    for ln in reversed(lines):
        if SALDO_FINAL_PREFIX.match(ln):
            d = DATE_RE.search(ln)
            if d and _only_one_amount(ln):
                fecha = pd.to_datetime(d.group(0), dayfirst=True, errors="coerce")
                saldo = _first_amount_value(ln)
                if pd.notna(fecha) and not np.isnan(saldo):
                    return fecha, saldo
    for ln in reversed(lines):
        if "SALDO FINAL" in ln.upper() and _only_one_amount(ln):
            saldo = _first_amount_value(ln)
            if not np.isnan(saldo):
                return pd.NaT, saldo
    return pd.NaT, np.nan


def find_saldo_anterior_from_lines(lines):
    for ln in lines:
        if SALDO_ANT_PREFIX.match(ln):
            d = DATE_RE.search(ln)
            if d and _only_one_amount(ln):
                saldo = _first_amount_value(ln)
                if not np.isnan(saldo):
                    return saldo
    for ln in lines:
        U = ln.upper()
        if "SALDO ULTIMO EXTRACTO" in U or "SALDO ÚLTIMO EXTRACTO" in U:
            d = DATE_RE.search(ln)
            if d and _only_one_amount(ln):
                saldo = _first_amount_value(ln)
                if not np.isnan(saldo):
                    return saldo
    return np.nan


def find_macro_dyc_total_from_lines(lines):
    for ln in reversed(lines):
        m = MACRO_DYC_TOTAL_RE.search(ln)
        if m:
            val = normalize_money(m.group(1))
            if not np.isnan(val):
                return val
    return np.nan
