import streamlit as st
import pandas as pd
import re
from collections import Counter

st.set_page_config(
    page_title="Fríos - Cortes 6/7/8/10",
    page_icon="❄️",
    layout="centered"
)

GOOGLE_SHEET_ID = "1aP-qP6YXz7HcXuy77GXX4xqMKE3-noLP_jvQflqvE-I"
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"

VENTANA_FRIOS = 5
ANIMALITOS_DICT = {
    0: "Delfín", 1: "Carnero", 2: "Toro", 3: "Ciempiés", 4: "Alacrán",
    5: "León", 6: "Rana", 7: "Perico", 8: "Ratón", 9: "Águila",
    10: "Tigre", 11: "Gato", 12: "Caballo", 13: "Mono", 14: "Paloma",
    15: "Zorro", 16: "Oso", 17: "Pavo", 18: "Burro", 19: "Chivo",
    20: "Cochino", 21: "Gallo", 22: "Camello", 23: "Cebra", 24: "Iguana",
    25: "Gallina", 26: "Vaca", 27: "Perro", 28: "Zamuro", 29: "Elefante",
    30: "Caimán", 31: "Lapa", 32: "Ardilla", 33: "Pescado", 34: "Venado",
    35: "Jirafa", 36: "Culebra", 100: "Ballena"
}


def fmt_num(n):
    if n == 100: return "00"
    if n == 0: return "0"
    return f"{n:02d}"


@st.cache_data(ttl=120)
def cargar_historial():
    try:
        df_raw = pd.read_csv(GOOGLE_SHEET_URL, header=None)
        filas_enc = []
        for fila in range(len(df_raw)):
            val = str(df_raw.iloc[fila, 0]).strip().lower()
            if val == "hora":
                filas_enc.append(fila)
        registros = []
        for idx, fe in enumerate(filas_enc):
            ff = filas_enc[idx + 1] if idx + 1 < len(filas_enc) else len(df_raw)
            fechas_col = {}
            for col in range(1, len(df_raw.columns)):
                val = str(df_raw.iloc[fe, col]).strip()
                if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', val):
                    try:
                        fd = pd.to_datetime(val, format="%d/%m/%Y", errors="coerce")
                        if pd.notna(fd):
                            fechas_col[col] = fd.strftime("%d/%m/%Y")
                    except:
                        pass
            ff_datos = min(ff, fe + 13)
            for col, fecha in fechas_col.items():
                for fd in range(fe + 1, ff_datos):
                    val = str(df_raw.iloc[fd, col]).strip()
                    if not val or val.lower() == "nan" or val.lower() == "hora":
                        continue
                    m = re.search(r'\((\d+)\)', val)
                    if m:
                        ns = m.group(1)
                        num = 100 if ns == "00" else int(ns)
                        nombre = ANIMALITOS_DICT.get(num, re.sub(r'\s*\(\d+\)', '', val).strip())
                        registros.append({"fecha": fecha, "numero": num, "nombre": nombre})
        df = pd.DataFrame(registros)
        if not df.empty:
            df["fecha_dt"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
            df = df.sort_values(["fecha_dt"], kind="stable").reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["fecha", "numero", "nombre"])


def dias_sin_salir(df_hasta):
    fechas = sorted(df_hasta["fecha_dt"].dropna().unique())
    if not fechas:
        return {n: 999 for n in ANIMALITOS_DICT.keys()}
    ultima = fechas[-1]
    resultado = {}
    for num in ANIMALITOS_DICT.keys():
        df_num = df_hasta[df_hasta["numero"] == num]
        if df_num.empty:
            resultado[num] = 999
        else:
            ult = df_num["fecha_dt"].max()
            resultado[num] = (ultima - ult).days
    return resultado


def get_frios(df_hasta, corte):
    """Fríos excluyendo >= corte días."""
    fechas = sorted(df_hasta["fecha_dt"].dropna().unique())
    if len(fechas) < VENTANA_FRIOS:
        return [], {}

    fechas_ventana = fechas[-VENTANA_FRIOS:]
    df_vent = df_hasta[df_hasta["fecha_dt"].isin(fechas_ventana)]
    conteo = Counter(df_vent["numero"].tolist())

    dias_sin = dias_sin_salir(df_hasta)

    candidatos = [n for n in ANIMALITOS_DICT.keys() if dias_sin[n] < corte]
    candidatos.sort(key=lambda n: (conteo.get(n, 0), n))

    return candidatos, dias_sin


def armar_tripletas(frios, max_tripletas=5):
    if len(frios) < 3:
        return []

    combinaciones = [
        (0, 1, 2),
        (0, 3, 4),
        (1, 5, 6),
        (2, 7, 8),
        (3, 8, 9),
    ]

    tripletas = []
    for c in combinaciones[:max_tripletas]:
        if all(i < len(frios) for i in c):
            tripletas.append([frios[i] for i in c])
    return tripletas


def backtest(df, corte, dias_test=30):
    fechas = sorted(df["fecha_dt"].dropna().unique())
    if len(fechas) < dias_test + 6:
        dias_test = len(fechas) - 6

    fechas_test = fechas[-dias_test:]
    resultados = []
    total_tripletas = 0
    total_pegadas = 0

    for fecha_actual in fechas_test:
        df_hasta = df[df["fecha_dt"] < fecha_actual]
        if len(df_hasta) < 60:
            continue

        df_dia = df[df["fecha_dt"] == fecha_actual]
        if df_dia.empty:
            continue

        frios, _ = get_frios(df_hasta, corte)
        tripletas = armar_tripletas(frios)

        if not tripletas:
            continue

        nums_dia = set(df_dia["numero"].tolist())
        pego_hoy = False

        for trip in tripletas:
            total_tripletas += 1
            if all(n in nums_dia for n in trip):
                total_pegadas += 1
                pego_hoy = True

        resultados.append({"fecha": pd.to_datetime(fecha_actual).strftime("%d/%m/%Y"), "pego": pego_hoy})

    return {
        "total_dias": len(resultados),
        "dias_con_tripleta": sum(1 for r in resultados if r["pego"]),
        "tripletas_pegadas": total_pegadas,
        "resultados": resultados
    }


def mostrar_bt(resultado, nombre):
    st.markdown(f"### {nombre}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Días", resultado["total_dias"])
    col2.metric("Días ✅", resultado["dias_con_tripleta"])
    col3.metric("Tripletas ✅", resultado["tripletas_pegadas"])

    inversion = resultado["total_dias"] * 500
    ganancia = resultado["tripletas_pegadas"] * 5000
    neto = ganancia - inversion

    st.caption(f"Invertido: {inversion:,} · Ganado: {ganancia:,} · **Neto: {neto:+,} Bs**")
    if neto > 0:
        st.success(f"✅ GANANCIA: +{neto:,} Bs")
    elif neto == 0:
        st.warning("🟡 EMPATE")
    else:
        st.error(f"❌ PÉRDIDA: {neto:,} Bs")
    st.markdown("---")


def main():
    st.title("❄️ FRÍOS — 4 CORTES")
    st.caption("Comparamos: excluye 6+ · 7+ · 8+ · 10+ días")

    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Leyendo hoja..."):
        df = cargar_historial()

    if df.empty:
        st.error("Sin datos.")
        return

    st.caption(f"📊 Data: {len(df)} sorteos · {df['fecha'].nunique()} días")

    # ═══════════════════════════════════════
    # TRIPLETAS PARA HOY — CORTE 10
    # ═══════════════════════════════════════
    st.markdown("## 🎯 TRIPLETAS PARA HOY (Corte 10 — Método C actual)")

    frios, dias_sin = get_frios(df, 10)

    if frios:
        st.markdown("### ❄️ Fríos disponibles (excluye 10+ días)")
        for n in frios[:15]:
            st.write(f"**{fmt_num(n)} {ANIMALITOS_DICT[n]}** — {dias_sin[n]} días sin salir")

        st.markdown("---")

        tripletas = armar_tripletas(frios)

        if tripletas:
            st.markdown(f"### 🎲 {len(tripletas)} TRIPLETAS PARA JUGAR")
            for i, trip in enumerate(tripletas, 1):
                nombres = " + ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in trip])
                st.markdown(f"**Tripleta #{i}:** {nombres}")
    st.markdown("---")

    # ═══════════════════════════════════════
    # BACKTEST 30 DÍAS — 4 CORTES
    # ═══════════════════════════════════════
    st.markdown("## 📊 BACKTEST 30 DÍAS — 4 CORTES")

    with st.spinner("Analizando cortes..."):
        res_6 = backtest(df, corte=6, dias_test=30)
        res_7 = backtest(df, corte=7, dias_test=30)
        res_8 = backtest(df, corte=8, dias_test=30)
        res_10 = backtest(df, corte=10, dias_test=30)

    mostrar_bt(res_6, "Corte 6 — excluye 6+ días")
    mostrar_bt(res_7, "Corte 7 — excluye 7+ días")
    mostrar_bt(res_8, "Corte 8 — excluye 8+ días")
    mostrar_bt(res_10, "Corte 10 — excluye 10+ días (Método C)")

    # ═══════════════════════════════════════
    # VEREDICTO
    # ═══════════════════════════════════════
    st.markdown("## 🏆 VEREDICTO")

    variantes = {
        "Corte 6": res_6["tripletas_pegadas"],
        "Corte 7": res_7["tripletas_pegadas"],
        "Corte 8": res_8["tripletas_pegadas"],
        "Corte 10": res_10["tripletas_pegadas"]
    }

    mejor = max(variantes.items(), key=lambda x: x[1])
    st.success(f"✅ MEJOR: **{mejor[0]}** con {mejor[1]} tripletas pegadas")

    for nombre, trips in sorted(variantes.items(), key=lambda x: x[1], reverse=True):
        st.write(f"**{nombre}:** {trips} tripletas")

    st.markdown("---")
    st.caption("Invertido: 500 Bs/día · Ganado: 5.000 Bs por tripleta")


if __name__ == "__main__":
    main()
