import re

import pandas as pd

RE_PERCEP_RG2408 = re.compile(r"PERCEPCI[ÓO]N\s+IVA\s+RG\.?\s*2408", re.IGNORECASE)


def clasificar(desc: str, desc_norm: str, deb: float, cre: float) -> str:
    u = (desc or "").upper()
    n = (desc_norm or "").upper()

    if "SALDO ANTERIOR" in u or "SALDO ANTERIOR" in n:
        return "SALDO ANTERIOR"

    # Impuesto a los débitos y créditos bancarios / DyC / Ley 25.413.
    if (
        "LEY 25413" in u or "IMPTRANS" in u or "IMP.S/CREDS" in u or "IMPDBCR 25413" in u or "N/D DBCR 25413" in u or "DYC" in u or
        "LEY 25413" in n or "IMPTRANS" in n or "IMP.S/CREDS" in n or "IMPDBCR 25413" in n or "N/D DBCR 25413" in n or "DYC" in n
    ):
        return "LEY 25.413"

    if "SIRCREB" in u or "SIRCREB" in n:
        return "SIRCREB"

    if RE_PERCEP_RG2408.search(u) or RE_PERCEP_RG2408.search(n):
        return "Percepciones de IVA"

    if (
        "IVA PERC" in u or "IVA PERCEP" in u or "RG3337" in u or
        "IVA PERC" in n or "IVA PERCEP" in n or "RG3337" in n or
        (("RETEN" in u or "RETENC" in u) and ("I.V.A" in u or "IVA" in u) and ("RG.2408" in u or "RG 2408" in u or "RG2408" in u)) or
        (("RETEN" in n or "RETENC" in n) and ("I.V.A" in n or "IVA" in n) and ("RG.2408" in n or "RG 2408" in n or "RG2408" in n))
    ):
        return "Percepciones de IVA"

    if (
        ("RETENCION" in u and "IVA" in u and "PERCEP" in u) or
        ("RETENCION" in n and "IVA" in n and "PERCEP" in n) or
        ("RETEN" in u and "IVA" in u and "PERC" in u) or
        ("RETEN" in n and "IVA" in n and "PERC" in n)
    ):
        return "Percepciones de IVA"

    if (
        "DEBITO FISCAL IVA BASICO" in u or "DEBITO FISCAL IVA BASICO" in n or
        ("I.V.A" in u and "DÉBITO FISCAL" in u) or ("I.V.A" in n and "DEBITO FISCAL" in n)
    ):
        if "10,5" in u or "10,5" in n or "10.5" in u or "10.5" in n:
            return "IVA 10,5% (sobre comisiones)"
        return "IVA 21% (sobre comisiones)"

    if "PLAZO FIJO" in u or "PLAZO FIJO" in n or "P.FIJO" in u or "P.FIJO" in n or "P FIJO" in u or "P FIJO" in n or "PFIJO" in u or "PFIJO" in n:
        if cre and cre != 0:
            return "Acreditación Plazo Fijo"
        if deb and deb != 0:
            return "Débito Plazo Fijo"
        return "Plazo Fijo"

    if (
        "COMIS.TRANSF" in u or "COMIS.TRANSF" in n or "COMIS TRANSF" in u or "COMIS TRANSF" in n or
        "COMISION TRANSFERE" in u or "COMISION TRANSFERE" in n or
        "COMISION TRF" in u or "COMISION TRF" in n or
        "COMIS.COMPENSACION" in u or "COMIS.COMPENSACION" in n or "COMIS COMPENSACION" in u or "COMIS COMPENSACION" in n
    ):
        return "Gastos por comisiones"

    if (
        "MANTENIMIENTO MENSUAL PAQUETE" in u or "MANTENIMIENTO MENSUAL PAQUETE" in n or
        "COMOPREM" in n or "COMVCAUT" in n or "COMTRSIT" in n or "COM.NEGO" in n or "CO.EXCESO" in n or "COM." in n
    ):
        return "Gastos por comisiones"

    if "DB-SNP" in n or "DEB.AUT" in n or "DEB.AUTOM" in n or "SEGUROS" in n or "GTOS SEG" in n:
        return "Débito automático"
    if "DEBITO INMEDIATO" in u or "DEBIN" in u:
        return "Débito automático"

    if ("AFIP" in n or "ARCA" in n) and deb and deb != 0:
        return "Débitos ARCA"
    if "API" in n:
        return "API"

    # Cuotas / débitos de préstamos Macro.
    if (
        "DEB.CUOTA PRESTAMO" in n or "DEB CUOTA PRESTAMO" in n or
        "DEBITO PRESTAMO" in n or "DEBITO PRESTAMOS" in n or
        "DÉBITO PRESTAMO" in n or "DÉBITO PRESTAMOS" in n or
        "DEB PRESTAMO" in n or "DEB PRESTAMOS" in n or
        ("PRESTAMO" in n and ("DEB." in n or "N/D" in n or "DEBITO" in n or "DÉBITO" in n))
    ):
        return "Cuota de préstamo"

    # Acreditaciones de préstamos.
    if (
        "CR.PREST" in n or "CR PREST" in n or
        "CREDITO PRESTAMOS" in n or "CRÉDITO PRÉSTAMOS" in n or
        "CREDITO PRESTAMO" in n or "CRÉDITO PRÉSTAMO" in n or
        "ACREDITACION PRESTAMO" in n or "ACREDITACIÓN PRÉSTAMO" in n or
        "ACREDITACION PRESTAMOS" in n or "ACREDITACIÓN PRÉSTAMOS" in n or
        "ACRED PREST" in n
    ):
        return "Acreditación Préstamos"

    if "CH 48 HS" in n or "CH.48 HS" in n:
        return "Cheques 48 hs"

    if "PAGO COMERC" in n or "CR-CABAL" in n or "CR CABAL" in n or "CR TARJ" in n:
        return "Acreditaciones Tarjetas de Crédito/Débito"

    if "CR-DEPEF" in n or "CR DEPEF" in n or "DEPOSITO EFECTIVO" in n or "DEP.EFECTIVO" in n or "DEP EFECTIVO" in n:
        return "Depósito en Efectivo"

    if ("CR-TRSFE" in n or "TRANSF RECIB" in n or "TRANLINK" in n or "TRANSFERENCIAS RECIBIDAS" in u) and cre and cre != 0:
        return "Transferencia de terceros recibida"
    if ("DB-TRSFE" in n or "TRSFE-ET" in n or "TRSFE-IT" in n) and deb and deb != 0:
        return "Transferencia a terceros realizada"
    if "DTNCTAPR" in n or "ENTRE CTA" in n or "CTA PROPIA" in n:
        return "Transferencia entre cuentas propias"

    if "NEG.CONT" in n or "NEGOCIADOS" in n:
        return "Acreditación de valores"

    if cre and cre != 0:
        return "Crédito"
    if deb and deb != 0:
        return "Débito"
    return "Otros"


def ajustar_macro_iva_105(df: pd.DataFrame) -> pd.DataFrame:
    """
    En Macro, cuando aparece:
    N/D INTER.ADEL.CC C/ACUERD
    DEBITO FISCAL IVA BASICO
    la segunda línea es IVA 10,5% (sobre comisiones).
    """
    if df.empty:
        return df
    df = df.copy()
    u = df["desc_norm"].astype(str).str.upper()
    for i in range(len(df) - 1):
        if "INTER.ADEL.CC" in u.iloc[i] and "C/ACUERD" in u.iloc[i]:
            if "DEBITO FISCAL IVA BASICO" in u.iloc[i + 1]:
                df.at[i + 1, "Clasificación"] = "IVA 10,5% (sobre comisiones)"
    return df
