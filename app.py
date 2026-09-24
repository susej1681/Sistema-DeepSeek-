import streamlit as st
import pandas as pd
import re
from collections import Counter

st.set_page_config(
    page_title="Test Multi-Variantes",
    page_icon="🧪",
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
                    hora_val = str(df_raw.iloc[fd, 0]).strip()
                    m = re.search(r'\((\d+)\)', val)
                    if m:
                        ns = m.group(1)
                        num = 100 if ns == "00" else int(ns)
                        nombre = ANIMALITOS_DICT.get(num, re.sub(r'\s*\(\d+\)', '', val).strip())
                        registros.append({"fecha": fecha, "hora": hora_val, "numero": num, "nombre": nombre})
        df = pd.DataFrame(registros)
        if not df.empty:
            df["fecha_dt"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
            df = df.sort_values(["fecha_dt"], kind="stable").reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame(columns=["fecha", "hora", "numero", "nombre"])


def test_variante(df, ventana_dias, top_n):
    fechas_unicas = sorted(df["fecha_dt"].dropna().unique())
    if len(fechas_unicas) < ventana_dias + 1:
        return None

    aciertos_cal = 0
    aciertos_fri = 0
    esperado = 0
    total_sorteos = 0
    todos = list(ANIMALITOS_DICT.keys())
    prob = top_n / len(todos)

    for i in range(ventana_dias, len(fechas_unicas)):
        fecha_actual = fechas_unicas[i]
        fecha_ventana = fechas_unicas[i - ventana_dias:i]

        df_ventana = df[df["fecha_dt"].isin(fecha_ventana)]
        df_dia = df[df["fecha_dt"] == fecha_actual]

        if df_ventana.empty or df_dia.empty:
            continue

        conteo = Counter(df_ventana["numero"].tolist())
        ordenados = sorted(todos, key=lambda n: conteo.get(n, 0), reverse=True)
        top_cal = set(ordenados[:top_n])
        top_fri = set(ordenados[-top_n:])

        nums_dia = df_dia["numero"].tolist()
        total_sorteos += len(nums_dia)
        esperado += prob * len(nums_dia)

        for num in nums_dia:
            if num in top_cal:
                aciertos_cal += 1
            if num in top_fri:
                aciertos_fri += 1

    return {
        "cal": aciertos_cal,
        "fri": aciertos_fri,
        "esp": round(esperado, 1),
        "total": total_sorteos,
        "ventana": ventana_dias,
        "top": top_n
    }


def test_por_hora(df, top_n=5):
    """Analiza por cada hora específica."""
    if "hora" not in df.columns:
        return []

    horas = df["hora"].dropna().unique().tolist()
    resultados = []

    for hora in horas:
        if not hora or hora.lower() == "hora":
            continue

        df_hora = df[df["hora"] == hora].reset_index(drop=True)
        if len(df_hora) < 50:
            continue

        aciertos_cal = 0
        aciertos_fri = 0
        esperado = 0
        total = 0
        todos = list(ANIMALITOS_DICT.keys())
        prob = top_n / len(todos)

        for i in range(10, len(df_hora)):
            df_vent = df_hora.iloc[max(0, i - 10):i]
            num_real = int(df_hora.iloc[i]["numero"])

            conteo = Counter(df_vent["numero"].tolist())
            ordenados = sorted(todos, key=lambda n: conteo.get(n, 0), reverse=True)
            top_cal = set(ordenados[:top_n])
            top_fri = set(ordenados[-top_n:])

            total += 1
            esperado += prob
            if num_real in top_cal:
                aciertos_cal += 1
            if num_real in top_fri:
                aciertos_fri += 1

        if total > 0:
            resultados.append({
                "hora": hora,
                "cal": aciertos_cal,
                "fri": aciertos_fri,
                "esp": round(esperado, 1),
                "total": total,
                "cal_pct": round(aciertos_cal / total * 100, 1),
                "fri_pct": round(aciertos_fri / total * 100, 1),
                "esp_pct": round(esperado / total * 100, 1)
            })

    return resultados


def main():
    st.title("🧪 TEST MULTI-VARIANTES")
    st.caption("Buscando el hueco: diferentes ventanas y top N")

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
    # TEST 1-5: Diferentes ventanas y top N
    # ═══════════════════════════════════════
    st.markdown("## 📊 VARIANTES DE VENTANA Y TOP N")

    variantes = [
        (1, 5, "1 día · Top 5"),
        (3, 5, "3 días · Top 5"),
        (5, 5, "5 días · Top 5"),
        (10, 5, "10 días · Top 5"),
        (3, 3, "3 días · Top 3"),
        (3, 10, "3 días · Top 10"),
    ]

    with st.spinner("Analizando variantes..."):
        resultados = []
        for vd, tn, nombre in variantes:
            r = test_variante(df, vd, tn)
            if r:
                r["nombre"] = nombre
                r["dif_cal"] = round(r["cal"] - r["esp"], 1)
                r["dif_fri"] = round(r["fri"] - r["esp"], 1)
                resultados.append(r)

    for r in resultados:
        st.markdown(f"### 📌 {r['nombre']}")
        col1, col2, col3 = st.columns(3)
        col1.metric("🔥 Calientes", f"{r['cal']} ({r['dif_cal']:+.1f})")
        col2.metric("❄️ Fríos", f"{r['fri']} ({r['dif_fri']:+.1f})")
        col3.metric("🎲 Esperado", r['esp'])

        # Veredicto
        dif = r['fri'] - r['cal']
        pct_dif = (dif / r['esp']) * 100 if r['esp'] > 0 else 0
        if pct_dif >= 10:
            st.success(f"✅ Hueco: fríos salen {pct_dif:.1f}% más")
        elif pct_dif >= 5:
            st.info(f"🟡 Tendencia débil: fríos +{pct_dif:.1f}%")
        elif pct_dif <= -10:
            st.warning(f"⚠️ Al revés: calientes salen más")
        else:
            st.write(f"🎲 Sin hueco claro ({pct_dif:+.1f}%)")
        st.markdown("---")

    # ═══════════════════════════════════════
    # TEST 6: POR HORA
    # ═══════════════════════════════════════
    st.markdown("## ⏰ ANÁLISIS POR HORA")
    st.caption("Buscando si hay una hora donde los fríos explotan")

    with st.spinner("Analizando por hora..."):
        res_hora = test_por_hora(df, top_n=5)

    if res_hora:
        # Ordenar por mejor hueco (fri - cal)
        res_hora.sort(key=lambda x: (x['fri'] - x['cal']), reverse=True)

        st.markdown("**Mejores horas (donde los fríos explotan):**")
        for r in res_hora[:5]:
            dif_pct = r['fri_pct'] - r['cal_pct']
            emoji = "✅" if dif_pct >= 5 else ("🟡" if dif_pct >= 2 else "🎲")
            st.write(f"{emoji} **{r['hora']}** — 🔥 Cal {r['cal_pct']}% · ❄️ Fríos {r['fri_pct']}% · 🎲 Esp {r['esp_pct']}%")

        st.markdown("**Peores horas (donde los calientes explotan):**")
        for r in res_hora[-3:]:
            dif_pct = r['fri_pct'] - r['cal_pct']
            st.write(f"⚠️ **{r['hora']}** — 🔥 Cal {r['cal_pct']}% · ❄️ Fríos {r['fri_pct']}% · 🎲 Esp {r['esp_pct']}%")
    else:
        st.warning("No se pudo analizar por hora.")

    st.markdown("---")

    # ═══════════════════════════════════════
    # CONCLUSIÓN
    # ═══════════════════════════════════════
    st.markdown("## 🎯 CONCLUSIÓN")

    mejor = max(resultados, key=lambda x: x['fri'] - x['cal']) if resultados else None
    if mejor:
        dif = mejor['fri'] - mejor['cal']
        pct = (dif / mejor['esp']) * 100 if mejor['esp'] > 0 else 0
        st.markdown(f"**Mejor variante:** {mejor['nombre']}")
        st.markdown(f"**Diferencia:** fríos salen {pct:+.1f}% vs azar")
        if pct >= 10:
            st.success("✅ HAY HUECO — vale la pena investigar más")
        elif pct >= 5:
            st.info("🟡 HUECO DÉBIL — puede servir pero con cuidado")
        else:
            st.warning("❌ SIN HUECO CLARO — el azar manda")


if __name__ == "__main__":
    main()
