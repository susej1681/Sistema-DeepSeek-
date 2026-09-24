import streamlit as st
import pandas as pd
import re
from collections import Counter

st.set_page_config(
    page_title="Test Fríos vs Enjaulados",
    page_icon="❄️",
    layout="centered"
)

GOOGLE_SHEET_ID = "1aP-qP6YXz7HcXuy77GXX4xqMKE3-noLP_jvQflqvE-I"
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"

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


def get_frios(df_hasta, top_n=10, ventana_dias=5):
    """Top N fríos por frecuencia en últimos N días."""
    fechas_unicas = sorted(df_hasta["fecha_dt"].dropna().unique())
    if len(fechas_unicas) < ventana_dias:
        return []
    fechas_ventana = fechas_unicas[-ventana_dias:]
    df_vent = df_hasta[df_hasta["fecha_dt"].isin(fechas_ventana)]
    conteo = Counter(df_vent["numero"].tolist())
    todos = list(ANIMALITOS_DICT.keys())
    ordenados = sorted(todos, key=lambda n: (conteo.get(n, 0), n))
    return ordenados[:top_n]


def get_enjaulados(df_hasta, min_dias=5, max_n=10):
    """Animalitos que llevan X+ días sin salir."""
    fechas_unicas = sorted(df_hasta["fecha_dt"].dropna().unique())
    if len(fechas_unicas) < min_dias:
        return []
    todos = list(ANIMALITOS_DICT.keys())
    dias_sin_salir = {}
    for num in todos:
        df_num = df_hasta[df_hasta["numero"] == num]
        if df_num.empty:
            dias_sin_salir[num] = 999
            continue
        ultima_vez = df_num["fecha_dt"].max()
        dias = (fechas_unicas[-1] - ultima_vez).days
        dias_sin_salir[num] = dias
    # Los que llevan min_dias+ sin salir, ordenados por más días
    candidatos = [(n, d) for n, d in dias_sin_salir.items() if d >= min_dias]
    candidatos.sort(key=lambda x: x[1], reverse=True)
    return [n for n, _ in candidatos[:max_n]]


def generar_5_tripletas(pool):
    """Genera 5 tripletas distintas combinando el pool."""
    if len(pool) < 3:
        return []

    combinaciones = [
        (0, 1, 2),
        (0, 3, 4),
        (1, 5, 6),
        (2, 7, 8),
        (3, 8, 9),
    ]

    tripletas = []
    for c in combinaciones:
        if all(i < len(pool) for i in c):
            tripletas.append([pool[i] for i in c])
    return tripletas


def backtest(df, metodo="frios", dias_test=30):
    """Testea 5 tripletas con el método elegido."""
    fechas_unicas = sorted(df["fecha_dt"].dropna().unique())
    if len(fechas_unicas) < dias_test + 6:
        dias_test = len(fechas_unicas) - 6

    fechas_test = fechas_unicas[-dias_test:]
    resultados = []
    tripletas_pegadas = 0

    for fecha_actual in fechas_test:
        df_hasta = df[df["fecha_dt"] < fecha_actual]
        if len(df_hasta) < 60:
            continue

        df_dia = df[df["fecha_dt"] == fecha_actual]
        if df_dia.empty:
            continue

        if metodo == "frios":
            pool = get_frios(df_hasta, top_n=10, ventana_dias=5)
        else:  # enjaulados
            pool = get_enjaulados(df_hasta, min_dias=5, max_n=10)

        tripletas = generar_5_tripletas(pool)
        if not tripletas:
            continue

        nums_dia = set(df_dia["numero"].tolist())
        pego_hoy = False
        detalle = []

        for i, trip in enumerate(tripletas, 1):
            if all(n in nums_dia for n in trip):
                tripletas_pegadas += 1
                pego_hoy = True
                detalle.append({"num": i, "tripleta": trip, "pego": True})
            else:
                salieron = sum(1 for n in trip if n in nums_dia)
                detalle.append({"num": i, "tripleta": trip, "pego": False, "salieron": salieron})

        resultados.append({
            "fecha": pd.to_datetime(fecha_actual).strftime("%d/%m/%Y"),
            "pego": pego_hoy,
            "detalle": detalle
        })

    return {
        "total_dias": len(resultados),
        "dias_con_tripleta": sum(1 for r in resultados if r["pego"]),
        "tripletas_pegadas": tripletas_pegadas,
        "resultados": resultados
    }


def mostrar_resultados(resultado, titulo, emoji):
    st.markdown(f"## {emoji} {titulo}")

    if not resultado:
        st.warning("Sin datos suficientes.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Días", resultado["total_dias"])
    col2.metric("Días con ✅", resultado["dias_con_tripleta"])
    col3.metric("Tripletas ✅", resultado["tripletas_pegadas"])

    # Rentabilidad
    inversion = resultado["total_dias"] * 500
    ganancia = resultado["tripletas_pegadas"] * 5000
    neto = ganancia - inversion
    pct_dias = resultado["dias_con_tripleta"] / resultado["total_dias"] * 100 if resultado["total_dias"] > 0 else 0

    st.markdown(f"**Días con al menos 1 tripleta: {pct_dias:.1f}%**")

    col1, col2, col3 = st.columns(3)
    col1.metric("Invertido", f"{inversion:,}")
    col2.metric("Ganado", f"{ganancia:,}")
    col3.metric("Neto", f"{neto:+,}")

    if neto > 0:
        st.success(f"✅ GANANCIA en 30 días: +{neto:,} Bs")
    elif neto == 0:
        st.warning("🟡 EMPATE")
    else:
        st.error(f"❌ PÉRDIDA en 30 días: {neto:,} Bs")

    with st.expander("Ver detalle día por día"):
        for r in resultado["resultados"]:
            emoji_d = "✅" if r["pego"] else "❌"
            st.write(f"{emoji_d} **{r['fecha']}**")
            for d in r["detalle"]:
                nombres = " + ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in d["tripleta"]])
                if d["pego"]:
                    st.write(f"   ✅ T#{d['num']}: {nombres}")
                else:
                    st.write(f"   ❌ T#{d['num']}: {nombres} ({d.get('salieron', 0)}/3)")


def main():
    st.title("❄️ FRÍOS vs 🔒 ENJAULADOS")
    st.caption("Comparamos cuál método pega más tripletas")

    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Leyendo hoja..."):
        df = cargar_historial()

    if df.empty:
        st.error("Sin datos.")
        return

    st.caption(f"📊 Data: {len(df)} sorteos · {df['fecha'].nunique()} días")

    # TRIPLETAS PARA HOY - FRÍOS
    st.markdown("## 🎯 TRIPLETAS PARA HOY (basado en FRÍOS)")
    frios = get_frios(df, top_n=10, ventana_dias=5)
    if frios:
        linea = " · ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in frios])
        st.markdown(f"**Top 10 fríos:** {linea}")
        tripletas = generar_5_tripletas(frios)
        for i, trip in enumerate(tripletas, 1):
            nombres = " + ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in trip])
            st.write(f"**T#{i}:** {nombres}")
    st.markdown("---")

    # TRIPLETAS PARA HOY - ENJAULADOS
    st.markdown("## 🎯 TRIPLETAS PARA HOY (basado en ENJAULADOS 5+ días)")
    enj = get_enjaulados(df, min_dias=5, max_n=10)
    if enj:
        linea = " · ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in enj])
        st.markdown(f"**Enjaulados:** {linea}")
        tripletas_enj = generar_5_tripletas(enj)
        for i, trip in enumerate(tripletas_enj, 1):
            nombres = " + ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in trip])
            st.write(f"**T#{i}:** {nombres}")
    else:
        st.info("No hay animalitos enjaulados 5+ días ahora mismo.")
    st.markdown("---")

    # BACKTESTING
    st.markdown("## 📊 BACKTESTING — ÚLTIMOS 30 DÍAS")

    with st.spinner("Analizando fríos..."):
        res_frios = backtest(df, metodo="frios", dias_test=30)

    with st.spinner("Analizando enjaulados..."):
        res_enj = backtest(df, metodo="enjaulados", dias_test=30)

    mostrar_resultados(res_frios, "❄️ MÉTODO FRÍOS", "❄️")
    st.markdown("---")
    mostrar_resultados(res_enj, "🔒 MÉTODO ENJAULADOS", "🔒")
    st.markdown("---")

    # VEREDICTO FINAL
    st.markdown("## 🏆 VEREDICTO")

    if res_frios and res_enj:
        fr = res_frios["tripletas_pegadas"]
        en = res_enj["tripletas_pegadas"]
        if fr > en:
            st.success(f"✅ GANA **FRÍOS** con {fr} tripletas vs {en} enjaulados")
        elif en > fr:
            st.success(f"✅ GANA **ENJAULADOS** con {en} tripletas vs {fr} fríos")
        else:
            st.info(f"🤝 EMPATE — ambos con {fr} tripletas")


if __name__ == "__main__":
    main()
