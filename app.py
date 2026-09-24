import streamlit as st
import pandas as pd
import re
from collections import Counter

st.set_page_config(
    page_title="Granjita Dixie - Test",
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
        st.error(f"Error cargando: {e}")
        return pd.DataFrame(columns=["fecha", "numero", "nombre"])


def test_teoria_calientes_frios(df, ventana_dias=3, top_n=5):
    """Mide si los calientes salen menos que los fríos."""
    if df.empty or len(df) < 100:
        return None

    fechas_unicas = sorted(df["fecha_dt"].dropna().unique())
    if len(fechas_unicas) < ventana_dias + 1:
        return None

    total_sorteos_calientes = 0
    total_sorteos_frios = 0
    aciertos_calientes = 0
    aciertos_frios = 0
    aciertos_esperados_calientes = 0
    aciertos_esperados_frios = 0

    for i in range(ventana_dias, len(fechas_unicas)):
        fecha_actual = fechas_unicas[i]
        fecha_ventana = fechas_unicas[i - ventana_dias:i]

        df_ventana = df[df["fecha_dt"].isin(fecha_ventana)]
        df_dia = df[df["fecha_dt"] == fecha_actual]

        if df_ventana.empty or df_dia.empty:
            continue

        conteo = Counter(df_ventana["numero"].tolist())
        # Para todos los animalitos que existen
        todos = list(ANIMALITOS_DICT.keys())

        # Ordenar por frecuencia
        ordenados = sorted(todos, key=lambda n: conteo.get(n, 0), reverse=True)

        top_calientes = ordenados[:top_n]
        top_frios = ordenados[-top_n:]

        nums_dia = df_dia["numero"].tolist()
        total_sorteos_calientes += len(nums_dia)
        total_sorteos_frios += len(nums_dia)

        for num in nums_dia:
            if num in top_calientes:
                aciertos_calientes += 1
            if num in top_frios:
                aciertos_frios += 1

        # Esperado por azar: (top_n / 38) * len(nums_dia)
        prob_azar = top_n / len(todos)
        aciertos_esperados_calientes += prob_azar * len(nums_dia)
        aciertos_esperados_frios += prob_azar * len(nums_dia)

    return {
        "calientes_reales": aciertos_calientes,
        "calientes_esperados": round(aciertos_esperados_calientes, 1),
        "frios_reales": aciertos_frios,
        "frios_esperados": round(aciertos_esperados_frios, 1),
        "total_sorteos": total_sorteos_calientes,
        "ventana_dias": ventana_dias,
        "top_n": top_n,
    }


def main():
    st.title("🧪 TEST DE LA TEORÍA")
    st.caption("¿Los calientes salen menos? ¿Los fríos salen más?")

    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Leyendo hoja..."):
        df = cargar_historial()

    if df.empty:
        st.error("No se pudieron cargar datos.")
        return

    st.caption(f"📊 Data: {len(df)} sorteos · {df['fecha'].nunique()} días")

    st.markdown("## 📖 ¿QUÉ VAMOS A MEDIR?")
    st.write("""
    Vamos a recorrer TODOS los días del histórico.
    Para cada día:
    - Miramos los **últimos 3 días** antes de ese día.
    - Marcamos los **5 más calientes** (los que más salieron).
    - Marcamos los **5 más fríos** (los que menos salieron).
    - Miramos qué salió ese día.
    - Contamos si salieron los calientes o los fríos.
    
    **Si es azar puro:** calientes y fríos saldrán igual (~13% cada uno).
    **Si tu teoría es cierta:** los fríos saldrán más que los calientes.
    """)

    st.markdown("---")

    with st.spinner("Analizando 199 días..."):
        resultado = test_teoria_calientes_frios(df, ventana_dias=3, top_n=5)

    if not resultado:
        st.error("Datos insuficientes para el test.")
        return

    st.markdown("## 📊 RESULTADOS")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔥 CALIENTES")
        st.metric("Salieron", resultado["calientes_reales"])
        st.metric("Esperado por azar", resultado["calientes_esperados"])
        dif_cal = resultado["calientes_reales"] - resultado["calientes_esperados"]
        st.metric("Diferencia", f"{dif_cal:+.1f}")

    with col2:
        st.markdown("### ❄️ FRÍOS")
        st.metric("Salieron", resultado["frios_reales"])
        st.metric("Esperado por azar", resultado["frios_esperados"])
        dif_fri = resultado["frios_reales"] - resultado["frios_esperados"]
        st.metric("Diferencia", f"{dif_fri:+.1f}")

    st.markdown("---")

    st.markdown("## 🎯 VEREDICTO")

    if resultado["frios_reales"] > resultado["calientes_reales"] * 1.15:
        st.success(f"✅ TU TEORÍA TIENE BASE. Los fríos salieron MÁS ({resultado['frios_reales']}) que los calientes ({resultado['calientes_reales']}).")
    elif resultado["calientes_reales"] > resultado["frios_reales"] * 1.15:
        st.warning(f"⚠️ AL REVÉS. Los calientes salieron MÁS ({resultado['calientes_reales']}) que los fríos ({resultado['frios_reales']}).")
    else:
        st.info(f"🎲 AZAR PURO. Calientes ({resultado['calientes_reales']}) y fríos ({resultado['frios_reales']}) salieron parecido. No hay ventaja.")

    st.markdown("---")
    st.caption(f"Total sorteos analizados: {resultado['total_sorteos']} · Ventana: {resultado['ventana_dias']} días · Top: {resultado['top_n']}")


if __name__ == "__main__":
    main()
