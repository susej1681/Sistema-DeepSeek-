import streamlit as st
import pandas as pd
import re
from collections import Counter
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Granjita Oracle IA",
    page_icon="🧠",
    layout="centered"
)

GOOGLE_SHEET_ID = "1aP-qP6YXz7HcXuy77GXX4xqMKE3-noLP_jvQflqvE-I"
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"

SORTEOS_POR_DIA = 12
DIAS_VENTANA = 10
VENTANA_SORTEOS = SORTEOS_POR_DIA * DIAS_VENTANA
DESCARTE_ATRASO = 60
MODO_OBSERVACION_DIAS = 5
META_ACIERTOS = 5
TOP_AGENTE = 12

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

ECOSISTEMAS = {
    "PLUMAS": [7, 9, 14, 17, 21, 25, 28],
    "DEPREDADORES": [5, 10, 11, 15, 16],
    "CUADRÚPEDOS": [1, 2, 8, 12, 13, 18, 19, 20, 22, 23, 26, 27, 29, 31, 32, 34, 35],
    "RASTREROS": [3, 4, 24, 36],
    "ACUÁTICOS": [100, 0, 6, 30, 33],
}


def fmt_num(n):
    if n == 100: return "00"
    if n == 0: return "0"
    return f"{n:02d}"


def ecosistema_de(num):
    for eco, lista in ECOSISTEMAS.items():
        if num in lista:
            return eco
    return "?"


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
                        registros.append({
                            "fecha": fecha,
                            "hora": hora_val,
                            "numero": num,
                            "nombre": nombre
                        })
        df = pd.DataFrame(registros)
        if not df.empty:
            df["fecha_dt"] = pd.to_datetime(df["fecha"], format="%d/%m/%Y", errors="coerce")
            df = df.sort_values(["fecha_dt"], kind="stable").reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Error cargando: {e}")
        return pd.DataFrame(columns=["fecha", "hora", "numero", "nombre"])


def aprender_jales(df, max_salto=3):
    jales = {n: Counter() for n in ANIMALITOS_DICT.keys()}
    nums = df["numero"].tolist()
    for i in range(len(nums) - 1):
        for j in range(i + 1, min(i + 1 + max_salto, len(nums))):
            jales[nums[i]][nums[j]] += 1
    return jales


def agente_matematico(df, ventana=VENTANA_SORTEOS):
    if df.empty or len(df) < 20:
        return {}
    df_v = df.tail(ventana)
    freq = Counter(df_v["numero"].tolist())
    total = len(df)
    atrasos = {}
    for num in ANIMALITOS_DICT.keys():
        idxs = df[df["numero"] == num].index.tolist()
        atrasos[num] = total - 1 - idxs[-1] if idxs else total
    all_nums = df["numero"].tolist()
    ritmos = {}
    for num in ANIMALITOS_DICT.keys():
        pos = [i for i, n in enumerate(all_nums) if n == num]
        if len(pos) >= 2:
            diffs = [pos[k + 1] - pos[k] for k in range(len(pos) - 1)]
            ritmos[num] = sum(diffs) / len(diffs)
        else:
            ritmos[num] = 999
    max_freq = max(freq.values()) if freq else 1
    max_atr = max(atrasos.values()) if atrasos else 1
    scores = {}
    for num in ANIMALITOS_DICT.keys():
        f = freq.get(num, 0) / max_freq if max_freq else 0
        a = atrasos.get(num, 0) / max_atr if max_atr else 0
        r = ritmos.get(num, 999)
        if 0 < r < 500:
            ratio = atrasos.get(num, 0) / r
        else:
            ratio = 0
        ratio_n = min(ratio, 2) / 2
        if atrasos.get(num, 0) >= DESCARTE_ATRASO:
            scores[num] = 0
        else:
            scores[num] = round((f * 0.30 + a * 0.30 + ratio_n * 0.40) * 100, 2)
    return scores


def agente_transicion(df, jales):
    if df.empty:
        return {}
    ultimo = int(df["numero"].iloc[-1])
    c = jales.get(ultimo, Counter())
    if not c:
        return {}
    max_v = max(c.values())
    return {num: round(v / max_v * 100, 2) for num, v in c.items()}


def agente_historiador(df, hora_actual):
    if df.empty or "hora" not in df.columns or not hora_actual:
        return {}
    df_h = df[df["hora"] == hora_actual].tail(120)
    if df_h.empty:
        df_h = df.tail(60)
    conteo = Counter(df_h["numero"].tolist())
    if not conteo:
        return {}
    max_c = max(conteo.values())
    return {num: round(c / max_c * 100, 2) for num, c in conteo.items()}


def consenso_agentes(s_mat, s_trans, s_hist, top_n=TOP_AGENTE):
    top_mat = set([n for n, _ in sorted(s_mat.items(), key=lambda x: x[1], reverse=True)[:top_n]])
    top_trans = set([n for n, _ in sorted(s_trans.items(), key=lambda x: x[1], reverse=True)[:top_n]]) if s_trans else set()
    top_hist = set([n for n, _ in sorted(s_hist.items(), key=lambda x: x[1], reverse=True)[:top_n]]) if s_hist else set()

    resultado = []
    for num in ANIMALITOS_DICT.keys():
        votes = 0
        if num in top_mat: votes += 1
        if num in top_trans: votes += 1
        if num in top_hist: votes += 1
        if votes >= 2:
            avg = (s_mat.get(num, 0) + s_trans.get(num, 0) + s_hist.get(num, 0)) / 3
            resultado.append({
                "num": num,
                "votes": votes,
                "score": round(avg, 2),
                "s_mat": s_mat.get(num, 0),
                "s_trans": s_trans.get(num, 0),
                "s_hist": s_hist.get(num, 0)
            })
    resultado.sort(key=lambda x: (x["votes"], x["score"]), reverse=True)
    return resultado


def contar_repes_hoy(df, fecha_actual):
    df_hoy = df[df["fecha"] == fecha_actual]
    return Counter(df_hoy["numero"].tolist())


def aplicar_techo_repeticion(candidatos, repes_hoy):
    resultado = []
    for c in candidatos:
        num = c["num"]
        repes = repes_hoy.get(num, 0)
        if repes >= 2:
            factor = 0.05
        elif repes == 1:
            factor = 0.75
        else:
            factor = 1.0
        resultado.append({**c, "repes_hoy": repes, "score_ajustado": round(c["score"] * factor, 2)})
    resultado.sort(key=lambda x: (x["votes"], x["score_ajustado"]), reverse=True)
    return resultado


def detectar_inestabilidad(df, n=3):
    if df.empty or len(df) < n:
        return False
    ultimos = df.tail(n)["numero"].tolist()
    ecos = [ecosistema_de(x) for x in ultimos]
    return len(set(ecos)) >= 3


def mapa_calor_horario(df):
    if df.empty or "hora" not in df.columns:
        return {}
    mapa = {}
    for hora in df["hora"].unique():
        if not hora or hora.lower() == "hora":
            continue
        df_h = df[df["hora"] == hora].tail(60)
        if df_h.empty:
            continue
        conteo = Counter(df_h["numero"].tolist())
        mapa[hora] = conteo.most_common(3)
    return mapa


def ecosistema_probable_dia(df):
    if df.empty or len(df) < 30:
        return None, {}
    df_rec = df.tail(60)
    conteo = Counter([ecosistema_de(n) for n in df_rec["numero"].tolist()])
    total = len(df)
    atrasos = {}
    for eco, lista in ECOSISTEMAS.items():
        pos = [i for i, n in enumerate(df["numero"].tolist()) if n in lista]
        atrasos[eco] = total - 1 - pos[-1] if pos else total
    max_f = max(conteo.values()) if conteo else 1
    max_a = max(atrasos.values()) if atrasos else 1
    scores = {}
    for eco in ECOSISTEMAS.keys():
        f = conteo.get(eco, 0) / max_f
        a = atrasos.get(eco, 0) / max_a
        scores[eco] = round((f * 0.55 + a * 0.45) * 100, 2)
    top = max(scores.items(), key=lambda x: x[1])
    return top[0], scores


def reconstruir_dia(df, fecha_str):
    fecha_obj = pd.to_datetime(fecha_str, format="%d/%m/%Y", errors="coerce")
    if pd.isna(fecha_obj):
        return None
    df_antes = df[df["fecha_dt"] < fecha_obj].reset_index(drop=True)
    df_dia = df[df["fecha_dt"] == fecha_obj].reset_index(drop=True)
    if df_antes.empty or df_dia.empty:
        return None

    jales_base = aprender_jales(df_antes, max_salto=3)
    aciertos = 0
    resultados = []

    for idx, row in df_dia.iterrows():
        hora = row["hora"]
        num_real = int(row["numero"])
        df_hasta = pd.concat([df_antes, df_dia.iloc[:idx]], ignore_index=True)

        s_mat = agente_matematico(df_hasta)
        s_trans = agente_transicion(df_hasta, jales_base)
        s_hist = agente_historiador(df_hasta, hora)

        cands = consenso_agentes(s_mat, s_trans, s_hist)
        fecha_hoy_str = df_hasta["fecha"].iloc[-1] if not df_hasta.empty else ""
        repes = contar_repes_hoy(df_hasta, fecha_hoy_str)
        cands = aplicar_techo_repeticion(cands, repes)

        top3 = cands[:3]
        acerto = any(c["num"] == num_real for c in top3)
        if acerto:
            aciertos += 1
        resultados.append({
            "hora": hora,
            "real": num_real,
            "real_nombre": ANIMALITOS_DICT.get(num_real, "?"),
            "top3": [(c["num"], ANIMALITOS_DICT[c["num"]], c["votes"]) for c in top3],
            "acerto": acerto
        })

    return {
        "fecha": df_dia["fecha"].iloc[0],
        "aciertos": aciertos,
        "total": len(df_dia),
        "detalle": resultados
    }


def calcular_recomendacion_actual(df):
    if df.empty:
        return None
    jales = aprender_jales(df, max_salto=3)
    ultima_hora = df["hora"].iloc[-1] if "hora" in df.columns else ""
    fecha_actual = df["fecha"].iloc[-1]

    s_mat = agente_matematico(df)
    s_trans = agente_transicion(df, jales)
    s_hist = agente_historiador(df, ultima_hora)

    cands = consenso_agentes(s_mat, s_trans, s_hist)
    repes = contar_repes_hoy(df, fecha_actual)
    cands = aplicar_techo_repeticion(cands, repes)

    estable = not detectar_inestabilidad(df)
    if not estable:
        cands = [c for c in cands if c["votes"] == 3]
    return {
        "candidatos": cands[:3],
        "inestable": not estable,
        "ultima_hora": ultima_hora,
        "fecha_actual": fecha_actual
    }


def main():
    st.title("🧠 Granjita Oracle IA")
    st.caption("Red de Agentes · Consenso · Detector de Techo · Ventana 10 días")

    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Leyendo hoja de 7 meses..."):
        df = cargar_historial()

    if df.empty:
        st.error("No se pudieron cargar datos.")
        return

    st.caption(f"📊 Data cargada: {len(df)} sorteos · {df['fecha'].nunique()} días")

    eco_top, eco_scores = ecosistema_probable_dia(df)
    if eco_top:
        st.markdown("## 🌍 ECOSISTEMA PROBABLE HOY")
        st.markdown(f"### 🎯 **{eco_top}**")
        for eco, sc in sorted(eco_scores.items(), key=lambda x: x[1], reverse=True):
            st.write(f"- {eco}: **{sc}%**")
        st.markdown("---")

    rec = calcular_recomendacion_actual(df)
    if rec and rec["candidatos"]:
        st.markdown("## 🎯 PRÓXIMA JUGADA")
        if rec["inestable"]:
            st.error("🚨 Mercado inestable. Solo juega el animal de Fuerza Máxima (🔥🔥🔥).")
        for i, c in enumerate(rec["candidatos"], 1):
            nivel = "🔥🔥🔥" if c["votes"] == 3 else "🔥🔥"
            cargo = ""
            if c.get("repes_hoy", 0) >= 2:
                cargo = " ⚠️ ya repitió 2 veces"
            st.markdown(f"### {nivel} {fmt_num(c['num'])} {ANIMALITOS_DICT[c['num']]}{cargo}")
            st.caption(f"Ecosistema: {ecosistema_de(c['num'])} · Score: {c['score_ajustado']} · Repes hoy: {c.get('repes_hoy', 0)}")
            st.caption(f"🧮 Matemático: {c['s_mat']} · 🔗 Transición: {c['s_trans']} · 📚 Historiador: {c['s_hist']}")
        st.markdown("---")

    st.markdown("## 🔥 MAPA DE CALOR POR HORA")
    mapa = mapa_calor_horario(df)
    if mapa:
        for hora, tops in list(mapa.items())[:14]:
            linea = " · ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]} ({c}x)" for n, c in tops])
            st.write(f"**{hora}** → {linea}")
    st.markdown("---")

    st.markdown("## 📅 HISTORIAL RECONSTRUIDO (últimos 7 días)")
    fechas_unicas = sorted(df["fecha_dt"].dropna().unique())
    ultimas = fechas_unicas[-7:] if len(fechas_unicas) >= 7 else fechas_unicas

    resumen = []
    for fecha in reversed(ultimas):
        f_str = pd.to_datetime(fecha).strftime("%d/%m/%Y")
        r = reconstruir_dia(df, f_str)
        if r:
            resumen.append(r)

    if resumen:
        for r in resumen:
            estado = "✅" if r["aciertos"] >= META_ACIERTOS else "🟡" if r["aciertos"] >= 3 else "❌"
            st.markdown(f"**{estado} {r['fecha']}** → {r['aciertos']}/{r['total']} aciertos")
        with st.expander("Ver detalle del último día"):
            if resumen:
                ult = resumen[0]
                st.markdown(f"**{ult['fecha']}**")
                for d in ult["detalle"]:
                    icono = "✅" if d["acerto"] else "❌"
                    top3_str = " · ".join([f"{fmt_num(n)} {nom}" for n, nom, _ in d["top3"]])
                    st.write(f"{icono} **{d['hora']}** → Real: {fmt_num(d['real'])} {d['real_nombre']} | Rec: {top3_str}")
    else:
        st.info("No hay suficientes datos para reconstruir el historial.")

    st.markdown("---")

    st.markdown("## 🧪 MODO OBSERVACIÓN")
    total_dias_reconstruidos = len(resumen)
    if total_dias_reconstruidos < MODO_OBSERVACION_DIAS:
        st.warning(f"⏳ Faltan {MODO_OBSERVACION_DIAS - total_dias_reconstruidos} días para salir de observación")
    else:
        promedio = sum(r["aciertos"] for r in resumen) / len(resumen)
        if promedio >= META_ACIERTOS:
            st.success(f"✅ Promedio últimos {len(resumen)} días: {promedio:.1f}/12 · MODO JUGABLE")
        else:
            st.warning(f"⚠️ Promedio últimos {len(resumen)} días: {promedio:.1f}/12 · Sigue observando")

    st.markdown("---")

    st.markdown("## 🔗 JALES APRENDIDOS")
    ultimo_num = int(df["numero"].iloc[-1])
    jales_ap = aprender_jales(df, max_salto=3)
    jales_ult = jales_ap.get(ultimo_num, Counter())
    if jales_ult:
        for jale, c in jales_ult.most_common(5):
            st.write(f"- Después de **{fmt_num(ultimo_num)} {ANIMALITOS_DICT[ultimo_num]}** → **{fmt_num(jale)} {ANIMALITOS_DICT[jale]}** ({c} veces)")
    st.markdown("---")

    ultimo = df.iloc[-1]
    st.markdown("## 🎯 ÚLTIMO RESULTADO")
    st.markdown(f"### {fmt_num(int(ultimo['numero']))} - {ultimo['nombre']}")
    st.caption(f"Fecha: {ultimo['fecha']} · Hora: {ultimo.get('hora', '?')}")

    with st.expander("🌍 Ver ecosistemas"):
        for eco, lista in ECOSISTEMAS.items():
            nombres = ", ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in lista])
            st.markdown(f"**{eco}:** {nombres}")

    with st.expander("📋 Ver últimos 30 sorteos"):
        cols = ["fecha", "hora", "numero", "nombre"] if "hora" in df.columns else ["fecha", "numero", "nombre"]
        st.dataframe(df.tail(30)[cols], use_container_width=True)


if __name__ == "__main__":
    main()
