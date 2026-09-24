import streamlit as st
import pandas as pd
import re
from collections import Counter

st.set_page_config(
    page_title="Fríos - 4 Variantes",
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
    ultima_fecha = fechas[-1]
    resultado = {}
    for num in ANIMALITOS_DICT.keys():
        df_num = df_hasta[df_hasta["numero"] == num]
        if df_num.empty:
            resultado[num] = 999
        else:
            ult = df_num["fecha_dt"].max()
            resultado[num] = (ultima_fecha - ult).days
    return resultado


def get_frios(df_hasta, excluir_desde=None):
    """Fríos puros. Si excluir_desde está definido, quita los que llevan >= ese número de días."""
    fechas = sorted(df_hasta["fecha_dt"].dropna().unique())
    if len(fechas) < VENTANA_FRIOS:
        return []

    fechas_ventana = fechas[-VENTANA_FRIOS:]
    df_vent = df_hasta[df_hasta["fecha_dt"].isin(fechas_ventana)]
    conteo = Counter(df_vent["numero"].tolist())

    dias_sin = dias_sin_salir(df_hasta)

    if excluir_desde:
        candidatos = [n for n in ANIMALITOS_DICT.keys() if dias_sin[n] < excluir_desde]
    else:
        candidatos = list(ANIMALITOS_DICT.keys())

    candidatos.sort(key=lambda n: (conteo.get(n, 0), n))
    return candidatos


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


def backtest(df, excluir_desde=None, dias_test=15):
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

        frios = get_frios(df_hasta, excluir_desde=excluir_desde)
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

        resultados.append({"fecha": pd.to_datetime(fecha_actual).strftime("%d/%m/%Y"), "pego": pego_hoy, "num_t": len(tripletas)})

    return {
        "total_dias": len(resultados),
        "dias_con_tripleta": sum(1 for r in resultados if r["pego"]),
        "tripletas_pegadas": total_pegadas,
        "total_tripletas_jugadas": total_tripletas,
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
    st.title("❄️ FRÍOS — 4 VARIANTES")
    st.caption("Comparamos: sin excluir · excluye 6+ · excluye 10+ · excluye 15+")

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
    # TRIPLETAS PARA HOY — MÉTODO RECOMENDADO (sin excluir)
    # ═══════════════════════════════════════
    st.markdown("## 🎯 TRIPLETAS PARA HOY (método original)")

    frios_hoy = get_frios(df, excluir_desde=None)
    dias_sin = dias_sin_salir(df)

    if frios_hoy:
        st.markdown("### ❄️ Top 15 fríos disponibles")
        for n in frios_hoy[:15]:
            st.write(f"**{fmt_num(n)} {ANIMALITOS_DICT[n]}** — {dias_sin[n]} días sin salir")

        st.markdown("---")
        tripletas = armar_tripletas(frios_hoy)

        if tripletas:
            st.markdown(f"### 🎲 {len(tripletas)} TRIPLETAS")
            for i, trip in enumerate(tripletas, 1):
                nombres = " + ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in trip])
                st.markdown(f"**Tripleta #{i}:** {nombres}")
    st.markdown("---")

    # ═══════════════════════════════════════
    # BACKTEST 15 DÍAS — 4 VARIANTES
    # ═══════════════════════════════════════
    st.markdown("## 📊 BACKTEST 15 DÍAS — 4 VARIANTES")

    with st.spinner("Analizando variantes (15 días)..."):
        res_A = backtest(df, excluir_desde=None, dias_test=15)
        res_B = backtest(df, excluir_desde=6, dias_test=15)
        res_C = backtest(df, excluir_desde=10, dias_test=15)
        res_D = backtest(df, excluir_desde=15, dias_test=15)

    mostrar_bt(res_A, "A) Fríos SIN excluir (original)")
    mostrar_bt(res_B, "B) Fríos excluyendo 6+ días")
    mostrar_bt(res_C, "C) Fríos excluyendo 10+ días")
    mostrar_bt(res_D, "D) Fríos excluyendo 15+ días")

    # ═══════════════════════════════════════
    # BACKTEST 30 DÍAS — COMPARACIÓN
    # ═══════════════════════════════════════
    st.markdown("## 📊 BACKTEST 30 DÍAS — COMPARACIÓN")

    with st.spinner("Analizando variantes (30 días)..."):
        res_A30 = backtest(df, excluir_desde=None, dias_test=30)
        res_B30 = backtest(df, excluir_desde=6, dias_test=30)
        res_C30 = backtest(df, excluir_desde=10, dias_test=30)
        res_D30 = backtest(df, excluir_desde=15, dias_test=30)

    mostrar_bt(res_A30, "A) Fríos SIN excluir (original)")
    mostrar_bt(res_B30, "B) Fríos excluyendo 6+ días")
    mostrar_bt(res_C30, "C) Fríos excluyendo 10+ días")
    mostrar_bt(res_D30, "D) Fríos excluyendo 15+ días")

    # ═══════════════════════════════════════
    # VEREDICTO
    # ═══════════════════════════════════════
    st.markdown("## 🏆 VEREDICTO")

    variantes_15 = {"A) Sin excluir": res_A, "B) Excluye 6+": res_B, "C) Excluye 10+": res_C, "D) Excluye 15+": res_D}
    variantes_30 = {"A) Sin excluir": res_A30, "B) Excluye 6+": res_B30, "C) Excluye 10+": res_C30, "D) Excluye 15+": res_D30}

    mejor_15 = max(variantes_15.items(), key=lambda x: x[1]["tripletas_pegadas"])
    mejor_30 = max(variantes_30.items(), key=lambda x: x[1]["tripletas_pegadas"])

    st.markdown(f"**Mejor en 15 días:** {mejor_15[0]} con {mejor_15[1]['tripletas_pegadas']} tripletas")
    st.markdown(f"**Mejor en 30 días:** {mejor_30[0]} con {mejor_30[1]['tripletas_pegadas']} tripletas")

    st.markdown("---")
    st.caption("Invertido: 500 Bs/día (5 tripletas × 100 Bs) · Ganado: 5.000 Bs por tripleta pegada")


if __name__ == "__main__":
    main()
