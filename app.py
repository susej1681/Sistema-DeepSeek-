import streamlit as st
import pandas as pd
import re
from collections import Counter

st.set_page_config(
    page_title="Fríos Equilibrados",
    page_icon="❄️",
    layout="centered"
)

GOOGLE_SHEET_ID = "1aP-qP6YXz7HcXuy77GXX4xqMKE3-noLP_jvQflqvE-I"
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"

DIAS_ENJAULADO_EXCLUIR = 6
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
    """Calcula cuántos días lleva cada animalito sin salir."""
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


def get_frios_equilibrados(df_hasta, max_dias_enj=6, ventana_dias=5):
    """Devuelve los fríos puros, excluyendo enjaulados extremos."""
    fechas = sorted(df_hasta["fecha_dt"].dropna().unique())
    if len(fechas) < ventana_dias:
        return []

    fechas_ventana = fechas[-ventana_dias:]
    df_vent = df_hasta[df_hasta["fecha_dt"].isin(fechas_ventana)]
    conteo = Counter(df_vent["numero"].tolist())

    dias_sin = dias_sin_salir(df_hasta)

    # Excluir enjaulados extremos
    candidatos = [n for n in ANIMALITOS_DICT.keys() if dias_sin[n] < max_dias_enj]

    # Ordenar por menos salidas en ventana
    candidatos.sort(key=lambda n: (conteo.get(n, 0), n))

    return candidatos


def armar_tripletas(frios, max_tripletas=5):
    """Arma tripletas de 3 animalitos distintos."""
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


def backtest(df, dias_test=30):
    """Backtest 30 días con Fríos Equilibrados."""
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

        frios = get_frios_equilibrados(df_hasta)
        tripletas = armar_tripletas(frios)

        if not tripletas:
            continue

        nums_dia = set(df_dia["numero"].tolist())
        pego_hoy = False
        detalle = []

        for i, trip in enumerate(tripletas, 1):
            total_tripletas += 1
            if all(n in nums_dia for n in trip):
                total_pegadas += 1
                pego_hoy = True
                detalle.append({"num": i, "tripleta": trip, "pego": True})
            else:
                salieron = sum(1 for n in trip if n in nums_dia)
                detalle.append({"num": i, "tripleta": trip, "pego": False, "salieron": salieron})

        resultados.append({
            "fecha": pd.to_datetime(fecha_actual).strftime("%d/%m/%Y"),
            "pego": pego_hoy,
            "detalle": detalle,
            "num_tripletas": len(tripletas)
        })

    return {
        "total_dias": len(resultados),
        "dias_con_tripleta": sum(1 for r in resultados if r["pego"]),
        "total_tripletas_jugadas": total_tripletas,
        "tripletas_pegadas": total_pegadas,
        "resultados": resultados
    }


def main():
    st.title("❄️ FRÍOS EQUILIBRADOS")
    st.caption("Fríos puros · Sin enjaulados extremos · Tripleta del día")

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
    # TRIPLETAS PARA HOY
    # ═══════════════════════════════════════
    st.markdown("## 🎯 TRIPLETAS PARA HOY")

    frios = get_frios_equilibrados(df)
    dias_sin = dias_sin_salir(df)

    if frios:
        st.markdown("### ❄️ Fríos disponibles (sin enjaulados 6+ días)")

        # Mostrar los primeros 15 con detalle
        for n in frios[:15]:
            dias = dias_sin.get(n, "?")
            st.write(f"**{fmt_num(n)} {ANIMALITOS_DICT[n]}** — lleva {dias} días sin salir")

        st.markdown("---")

        tripletas = armar_tripletas(frios)

        if tripletas:
            st.markdown(f"### 🎲 {len(tripletas)} TRIPLETAS PARA JUGAR")
            for i, trip in enumerate(tripletas, 1):
                nombres = " + ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in trip])
                st.markdown(f"**Tripleta #{i}:** {nombres}")
        else:
            st.warning("No hay suficientes fríos para armar tripletas.")
    else:
        st.warning("No hay fríos disponibles.")

    st.markdown("---")

    # ═══════════════════════════════════════
    # BACKTEST 30 DÍAS
    # ═══════════════════════════════════════
    st.markdown("## 📊 BACKTEST — ÚLTIMOS 30 DÍAS")

    with st.spinner("Analizando 30 días..."):
        resultado = backtest(df, dias_test=30)

    if resultado:
        col1, col2, col3 = st.columns(3)
        col1.metric("Días", resultado["total_dias"])
        col2.metric("Días con ✅", resultado["dias_con_tripleta"])
        col3.metric("Tripletas ✅", resultado["tripletas_pegadas"])

        pct = resultado["dias_con_tripleta"] / resultado["total_dias"] * 100 if resultado["total_dias"] > 0 else 0
        st.markdown(f"**Días con al menos 1 tripleta: {pct:.1f}%**")

        # Rentabilidad (asumiendo 5 tripletas × 100 Bs)
        st.markdown("### 💰 Rentabilidad estimada")
        st.caption("Asumiendo 5 tripletas × 100 Bs = 500 Bs/día")

        inversion = resultado["total_dias"] * 500
        ganancia = resultado["tripletas_pegadas"] * 5000
        neto = ganancia - inversion

        col1, col2, col3 = st.columns(3)
        col1.metric("Invertido", f"{inversion:,}")
        col2.metric("Ganado", f"{ganancia:,}")
        col3.metric("Neto", f"{neto:+,}")

        if neto > 0:
            st.success(f"✅ GANANCIA: +{neto:,} Bs en 30 días")
        elif neto == 0:
            st.warning("🟡 EMPATE técnico")
        else:
            st.error(f"❌ PÉRDIDA: {neto:,} Bs en 30 días")

        with st.expander("Ver detalle día por día"):
            for r in resultado["resultados"]:
                emoji = "✅" if r["pego"] else "❌"
                st.write(f"{emoji} **{r['fecha']}** — {r['num_tripletas']} tripletas")
                for d in r["detalle"]:
                    nombres = " + ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in d["tripleta"]])
                    if d["pego"]:
                        st.write(f"   ✅ T#{d['num']}: {nombres}")
                    else:
                        st.write(f"   ❌ T#{d['num']}: {nombres} ({d.get('salieron', 0)}/3)")

    st.markdown("---")
    st.caption(f"Regla: se excluyen los que llevan {DIAS_ENJAULADO_EXCLUIR}+ días sin salir")


if __name__ == "__main__":
    main()
