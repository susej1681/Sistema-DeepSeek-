import streamlit as st
import pandas as pd
import re
from collections import Counter
from itertools import combinations

st.set_page_config(
    page_title="Granjita Dixie",
    page_icon="🧠",
    layout="centered"
)

GOOGLE_SHEET_ID = "1aP-qP6YXz7HcXuy77GXX4xqMKE3-noLP_jvQflqvE-I"
GOOGLE_SHEET_URL = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/export?format=csv"

SORTEOS_POR_DIA = 12
DIAS_VENTANA_LARGA = 10
DIAS_VENTANA_CORTA = 5
VENTANA_LARGA = SORTEOS_POR_DIA * DIAS_VENTANA_LARGA
VENTANA_CORTA = SORTEOS_POR_DIA * DIAS_VENTANA_CORTA
VENTANA_JALES = 60
DIAS_HISTORIADOR = 15
VENTANA_HISTORIADOR = SORTEOS_POR_DIA * DIAS_HISTORIADOR
DIAS_AUTO_APRENDIZAJE = 30
DIAS_OBSERVACION = 10
DESCARTE_ATRASO = 60

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


def calcular_ritmos(df):
    nums = df["numero"].tolist()
    ritmos = {}
    for num in ANIMALITOS_DICT.keys():
        pos = [i for i, n in enumerate(nums) if n == num]
        if len(pos) >= 2:
            diffs = [pos[k + 1] - pos[k] for k in range(len(pos) - 1)]
            ritmos[num] = sum(diffs) / len(diffs)
        else:
            ritmos[num] = 999
    return ritmos


def agente_matematico(df, pesos=None):
    if df.empty or len(df) < 30:
        return {}
    if pesos is None:
        pesos = {"corta": 0.25, "larga": 0.15, "atraso": 0.25, "ratio": 0.35}

    df_corta = df.tail(VENTANA_CORTA)
    df_larga = df.tail(VENTANA_LARGA)
    freq_corta = Counter(df_corta["numero"].tolist())
    freq_larga = Counter(df_larga["numero"].tolist())

    total = len(df)
    atrasos = {}
    for num in ANIMALITOS_DICT.keys():
        idxs = df[df["numero"] == num].index.tolist()
        atrasos[num] = total - 1 - idxs[-1] if idxs else total

    ritmos = calcular_ritmos(df)

    max_fc = max(freq_corta.values()) if freq_corta else 1
    max_fl = max(freq_larga.values()) if freq_larga else 1
    max_atr = max(atrasos.values()) if atrasos else 1

    scores = {}
    for num in ANIMALITOS_DICT.keys():
        fc = freq_corta.get(num, 0) / max_fc
        fl = freq_larga.get(num, 0) / max_fl
        atr = atrasos.get(num, 0)
        a_norm = atr / max_atr
        r = ritmos.get(num, 999)
        ratio = atr / r if 0 < r < 500 else 0
        ratio_n = min(ratio, 1.5) / 1.5

        score = (fc * pesos["corta"] + fl * pesos["larga"] +
                 a_norm * pesos["atraso"] + ratio_n * pesos["ratio"])

        if atr >= DESCARTE_ATRASO:
            score *= 0.1
        scores[num] = round(score * 100, 2)
    return scores


def agente_transicion(df):
    if df.empty or len(df) < 20:
        return {}
    df_rec = df.tail(VENTANA_JALES + 1)
    nums = df_rec["numero"].tolist()
    if len(nums) < 2:
        return {}
    ultimo = nums[-1]
    conteo = Counter()
    for i in range(len(nums) - 1):
        if nums[i] == ultimo:
            for j in range(i + 1, min(i + 3, len(nums))):
                conteo[nums[j]] += (3 - (j - i))
    if not conteo:
        return {}
    max_c = max(conteo.values())
    return {num: round(v / max_c * 100, 2) for num, v in conteo.items()}


def agente_historiador(df, hora_actual):
    if df.empty or "hora" not in df.columns or not hora_actual:
        return {}
    df_rec = df.tail(VENTANA_HISTORIADOR)
    df_h = df_rec[df_rec["hora"] == hora_actual]
    if len(df_h) < 3:
        return {}
    conteo = Counter(df_h["numero"].tolist())
    max_c = max(conteo.values())
    return {num: round(c / max_c * 100, 2) for num, c in conteo.items()}


def score_combinado(s_mat, s_trans, s_hist, top_n=15):
    top_mat = set([n for n, _ in sorted(s_mat.items(), key=lambda x: x[1], reverse=True)[:top_n]])
    top_trans = set([n for n, _ in sorted(s_trans.items(), key=lambda x: x[1], reverse=True)[:top_n]]) if s_trans else set()
    top_hist = set([n for n, _ in sorted(s_hist.items(), key=lambda x: x[1], reverse=True)[:top_n]]) if s_hist else set()

    resultado = []
    for num in ANIMALITOS_DICT.keys():
        votes = 0
        if num in top_mat: votes += 1
        if num in top_trans: votes += 1
        if num in top_hist: votes += 1

        sm = s_mat.get(num, 0)
        st_ = s_trans.get(num, 0)
        sh = s_hist.get(num, 0)
        base = sm * 0.45 + st_ * 0.30 + sh * 0.25

        if votes == 3: base *= 1.40
        elif votes == 2: base *= 1.15
        elif votes == 1: base *= 0.95

        if base > 0:
            resultado.append({
                "num": num,
                "votes": votes,
                "score": round(base, 2),
                "s_mat": sm,
                "s_trans": st_,
                "s_hist": sh
            })
    resultado.sort(key=lambda x: x["score"], reverse=True)
    return resultado


def contar_repes_hoy(df, fecha_actual):
    df_hoy = df[df["fecha"] == fecha_actual]
    return Counter(df_hoy["numero"].tolist())


def aplicar_techo(candidatos, repes_hoy):
    resultado = []
    for c in candidatos:
        num = c["num"]
        repes = repes_hoy.get(num, 0)
        if repes >= 2: factor = 0.15
        elif repes == 1: factor = 0.65
        else: factor = 1.0
        resultado.append({**c, "repes_hoy": repes, "score_aj": round(c["score"] * factor, 2)})
    resultado.sort(key=lambda x: x["score_aj"], reverse=True)
    return resultado


def detectar_inestabilidad(df, n=4):
    if df.empty or len(df) < n:
        return False
    ultimos = df.tail(n)["numero"].tolist()
    ecos = [ecosistema_de(x) for x in ultimos]
    return len(set(ecos)) == 4


def mapa_calor_horario(df):
    if df.empty or "hora" not in df.columns:
        return {}
    mapa = {}
    df_rec = df.tail(SORTEOS_POR_DIA * 20)
    for hora in df_rec["hora"].unique():
        if not hora or hora.lower() == "hora":
            continue
        df_h = df_rec[df_rec["hora"] == hora]
        if df_h.empty:
            continue
        conteo = Counter(df_h["numero"].tolist())
        mapa[hora] = conteo.most_common(3)
    return mapa


def ecosistema_probable_dia(df):
    if df.empty or len(df) < 30:
        return None, {}
    df_rec = df.tail(VENTANA_LARGA)
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
        scores[eco] = round((f * 0.60 + a * 0.40) * 100, 2)
    top = max(scores.items(), key=lambda x: x[1])
    return top[0], scores


# ═══════════════════════════════════════════════════
# MODO SNIPER — EL EMbUDO 38 → 10 → 1
# ═══════════════════════════════════════════════════
def calcular_diamante(df):
    """Embudo: de 38 → 10 candidatos → 1 diamante con puntaje 0-10."""
    if df.empty:
        return None

    ultima_hora = df["hora"].iloc[-1] if "hora" in df.columns else ""
    fecha_actual = df["fecha"].iloc[-1]

    s_mat = agente_matematico(df)
    s_trans = agente_transicion(df)
    s_hist = agente_historiador(df, ultima_hora)

    cands = score_combinado(s_mat, s_trans, s_hist)
    repes = contar_repes_hoy(df, fecha_actual)
    cands = aplicar_techo(cands, repes)

    # Etapa 1: top 10 candidatos
    top10 = cands[:10]
    if not top10:
        return None

    # Etapa 2: análisis profundo de los 10
    ritmos = calcular_ritmos(df)
    total = len(df)
    atrasos = {}
    for num in ANIMALITOS_DICT.keys():
        idxs = df[df["numero"] == num].index.tolist()
        atrasos[num] = total - 1 - idxs[-1] if idxs else total

    analisis_10 = []
    for c in top10:
        num = c["num"]
        puntos = 0
        razones = []

        atr = atrasos.get(num, 0)
        r = ritmos.get(num, 999)
        ratio = atr / r if 0 < r < 500 else 0

        # Criterio 1: Atraso significativo
        if 5 <= atr <= 40:
            puntos += 2
            razones.append(f"atraso ideal ({atr})")
        elif 40 < atr <= 60:
            puntos += 1
            razones.append(f"atraso alto ({atr})")

        # Criterio 2: Ratio cerca de 1 (maduro)
        if 0.9 <= ratio <= 1.8:
            puntos += 2
            razones.append(f"ratio maduro ({round(ratio,2)})")
        elif 0.6 <= ratio < 0.9 or 1.8 < ratio <= 2.5:
            puntos += 1
            razones.append(f"ratio cerca ({round(ratio,2)})")

        # Criterio 3: Coinciden 2+ agentes
        if c["votes"] >= 2:
            puntos += 2
            razones.append(f"{c['votes']} agentes coinciden")

        # Criterio 4: Ecosistema caliente
        eco = ecosistema_de(num)
        eco_top, _ = ecosistema_probable_dia(df)
        if eco == eco_top:
            puntos += 1
            razones.append(f"{eco} dominante")

        # Criterio 5: Sin repes hoy
        if repes.get(num, 0) == 0:
            puntos += 1
            razones.append("no ha salido hoy")

        # Criterio 6: Jale activo
        if c["s_trans"] >= 60:
            puntos += 1
            razones.append("jale activo")

        # Criterio 7: Historiador fuerte
        if c["s_hist"] >= 60:
            puntos += 1
            razones.append("hora frecuente")

        analisis_10.append({
            "num": num,
            "puntos": puntos,
            "razones": razones,
            "score_base": c["score_aj"],
            "atraso": atr,
            "ritmo": r,
            "ratio": round(ratio, 2),
            "eco": eco
        })

    analisis_10.sort(key=lambda x: (x["puntos"], x["score_base"]), reverse=True)
    diamante = analisis_10[0]

    # Clasificación
    if diamante["puntos"] >= 8:
        nivel = "💎 DIAMANTE PURO"
    elif diamante["puntos"] >= 6:
        nivel = "💎 DIAMANTE"
    elif diamante["puntos"] >= 4:
        nivel = "🟡 JUGADA NORMAL"
    elif diamante["puntos"] >= 2:
        nivel = "🔴 JUGADA DÉBIL"
    else:
        nivel = "⚫ NO JUGAR"

    return {
        "num": diamante["num"],
        "puntos": diamante["puntos"],
        "nivel": nivel,
        "razones": diamante["razones"],
        "top10": analisis_10,
        "fecha": fecha_actual,
        "hora": ultima_hora
    }


def reconstruir_dia(df, fecha_str):
    fecha_obj = pd.to_datetime(fecha_str, format="%d/%m/%Y", errors="coerce")
    if pd.isna(fecha_obj):
        return None
    df_antes = df[df["fecha_dt"] < fecha_obj].reset_index(drop=True)
    df_dia = df[df["fecha_dt"] == fecha_obj].reset_index(drop=True)
    if df_antes.empty or df_dia.empty:
        return None

    aciertos_normal = 0
    aciertos_sniper = 0
    resultados = []

    for idx, row in df_dia.iterrows():
        hora = row["hora"]
        num_real = int(row["numero"])
        df_hasta = pd.concat([df_antes, df_dia.iloc[:idx]], ignore_index=True)

        s_mat = agente_matematico(df_hasta)
        s_trans = agente_transicion(df_hasta)
        s_hist = agente_historiador(df_hasta, hora)

        cands = score_combinado(s_mat, s_trans, s_hist)
        fecha_hoy_str = df_hasta["fecha"].iloc[-1] if not df_hasta.empty else ""
        repes = contar_repes_hoy(df_hasta, fecha_hoy_str)
        cands = aplicar_techo(cands, repes)
        top3 = cands[:3]

        acerto_normal = any(c["num"] == num_real for c in top3)
        if acerto_normal:
            aciertos_normal += 1

        resultados.append({
            "hora": hora,
            "real": num_real,
            "real_nombre": ANIMALITOS_DICT.get(num_real, "?"),
            "top3": [(c["num"], ANIMALITOS_DICT[c["num"]], c["votes"]) for c in top3],
            "acerto": acerto_normal
        })

    # Sniper: un solo diamante por día (se calcula al final del día anterior)
    df_antes_dia = df[df["fecha_dt"] < fecha_obj]
    diamante_previo = None
    if not df_antes_dia.empty:
        # Calcular diamante usando toda la data antes del día
        ultima_hora_prev = df_antes_dia["hora"].iloc[-1] if "hora" in df_antes_dia.columns else ""
        s_mat_p = agente_matematico(df_antes_dia)
        s_trans_p = agente_transicion(df_antes_dia)
        s_hist_p = agente_historiador(df_antes_dia, ultima_hora_prev)
        cands_p = score_combinado(s_mat_p, s_trans_p, s_hist_p)
        if cands_p:
            diamante_previo = cands_p[0]["num"]

    if diamante_previo is not None:
        nums_dia = df_dia["numero"].tolist()
        if diamante_previo in nums_dia:
            aciertos_sniper = 1

    return {
        "fecha": df_dia["fecha"].iloc[0],
        "aciertos_normal": aciertos_normal,
        "aciertos_sniper": aciertos_sniper,
        "diamante": diamante_previo,
        "total": len(df_dia),
        "detalle": resultados
    }


def main():
    st.title("🧠 Granjita Dixie")
    st.caption("Sniper · Embudo 38→10→1 · Auto-aprendizaje · Medidor honesto")

    if st.button("🔄 Recargar datos"):
        st.cache_data.clear()
        st.rerun()

    with st.spinner("Leyendo hoja..."):
        df = cargar_historial()

    if df.empty:
        st.error("No se pudieron cargar datos.")
        return

    st.caption(f"📊 Data: {len(df)} sorteos · {df['fecha'].nunique()} días")

    # ═══════════════════════════════════════
    # DIAMANTE DEL DÍA
    # ═══════════════════════════════════════
    st.markdown("## 💎 DIAMANTE DEL DÍA (Modo Sniper)")
    diamante = calcular_diamante(df)

    if diamante:
        st.markdown(f"## {diamante['nivel']}")
        st.markdown(f"# {fmt_num(diamante['num'])} - {ANIMALITOS_DICT[diamante['num']]}")
        st.markdown(f"**Puntaje: {diamante['puntos']}/10**")
        st.markdown("**Razones:**")
        for r in diamante["razones"]:
            st.write(f"- {r}")

        if diamante["puntos"] < 4:
            st.warning("⚠️ Puntaje bajo. Hoy no hay jugada clara.")

        with st.expander("Ver top 10 candidatos del embudo"):
            for i, a in enumerate(diamante["top10"], 1):
                st.write(f"**#{i} - {fmt_num(a['num'])} {ANIMALITOS_DICT[a['num']]}** — {a['puntos']}/10 pts")
                st.caption(f"Atraso {a['atraso']} · Ratio {a['ratio']} · {a['eco']}")
    else:
        st.warning("Sin datos suficientes para calcular el diamante.")

    st.markdown("---")

    # ═══════════════════════════════════════
    # ECOSISTEMA
    # ═══════════════════════════════════════
    eco_top, eco_scores = ecosistema_probable_dia(df)
    if eco_top:
        st.markdown("## 🌍 ECOSISTEMA PROBABLE HOY")
        st.markdown(f"### 🎯 **{eco_top}**")
        for eco, sc in sorted(eco_scores.items(), key=lambda x: x[1], reverse=True):
            st.write(f"- {eco}: **{sc}%**")
        st.markdown("---")

    # ═══════════════════════════════════════
    # MEDIDOR HONESTO
    # ═══════════════════════════════════════
    st.markdown("## 📊 MEDIDOR HONESTO")
    fechas_unicas = sorted(df["fecha_dt"].dropna().unique())
    ultimas = fechas_unicas[-DIAS_OBSERVACION:] if len(fechas_unicas) >= DIAS_OBSERVACION else fechas_unicas

    resumen = []
    with st.spinner("Reconstruyendo historial..."):
        for fecha in reversed(ultimas):
            f_str = pd.to_datetime(fecha).strftime("%d/%m/%Y")
            r = reconstruir_dia(df, f_str)
            if r:
                resumen.append(r)

    if resumen:
        prom_normal = sum(r["aciertos_normal"] for r in resumen) / len(resumen)
        prom_sniper = sum(r["aciertos_sniper"] for r in resumen) / len(resumen)

        col1, col2 = st.columns(2)
        col1.metric("Modo Normal (3/hora)", f"{prom_normal:.1f}/12")
        col2.metric("Modo Sniper (1/día)", f"{prom_sniper:.1f}/10")

        st.markdown("**Últimos días:**")
        for r in resumen:
            icono_n = "✅" if r["aciertos_normal"] >= 5 else ("🟡" if r["aciertos_normal"] >= 2 else "❌")
            icono_s = "✅" if r["aciertos_sniper"] >= 1 else "❌"
            diam_str = fmt_num(r["diamante"]) + " " + ANIMALITOS_DICT.get(r["diamante"], "?") if r["diamante"] else "?"
            st.write(f"{icono_n} {r['fecha']} · Normal: {r['aciertos_normal']}/12 · {icono_s} Sniper: {r['aciertos_sniper']}/1 (diamante: {diam_str})")

        # Veredicto honesto
        st.markdown("### 🎯 VEREDICTO")
        if len(resumen) >= DIAS_OBSERVACION:
            if prom_normal >= 3 or prom_sniper >= 0.3:
                st.success(f"✅ Hay señal débil. Normal {prom_normal:.1f}/12 · Sniper {prom_sniper:.1f}/día")
            else:
                st.error(f"❌ Sin patrón aprendible. Normal {prom_normal:.1f}/12 · Sniper {prom_sniper:.1f}/día")
        else:
            st.info(f"⏳ Observando... {len(resumen)}/{DIAS_OBSERVACION} días")
    else:
        st.info("Sin datos para reconstruir.")

    st.markdown("---")

    # ═══════════════════════════════════════
    # MAPA DE CALOR
    # ═══════════════════════════════════════
    with st.expander("🔥 Mapa de calor por hora (últimos 20 días)"):
        mapa = mapa_calor_horario(df)
        for hora, tops in list(mapa.items())[:14]:
            linea = " · ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]} ({c}x)" for n, c in tops])
            st.write(f"**{hora}** → {linea}")

    # ═══════════════════════════════════════
    # JALES
    # ═══════════════════════════════════════
    st.markdown("## 🔗 JALES (últimos 60 sorteos)")
    ultimo_num = int(df["numero"].iloc[-1])
    conteo_jal = Counter()
    df_rec_j = df.tail(VENTANA_JALES + 1)
    nums_j = df_rec_j["numero"].tolist()
    for i in range(len(nums_j) - 1):
        if nums_j[i] == ultimo_num:
            for j in range(i + 1, min(i + 3, len(nums_j))):
                conteo_jal[nums_j[j]] += (3 - (j - i))
    if conteo_jal:
        for jale, c in conteo_jal.most_common(5):
            st.write(f"- Después de **{fmt_num(ultimo_num)} {ANIMALITOS_DICT[ultimo_num]}** → **{fmt_num(jale)} {ANIMALITOS_DICT[jale]}** ({c} pts)")
    st.markdown("---")

    # ═══════════════════════════════════════
    # ÚLTIMO RESULTADO
    # ═══════════════════════════════════════
    ultimo = df.iloc[-1]
    st.markdown("## 🎯 ÚLTIMO RESULTADO")
    st.markdown(f"### {fmt_num(int(ultimo['numero']))} - {ultimo['nombre']}")
    st.caption(f"Fecha: {ultimo['fecha']} · Hora: {ultimo.get('hora', '?')}")

    with st.expander("🌍 Ver ecosistemas"):
        for eco, lista in ECOSISTEMAS.items():
            nombres = ", ".join([f"{fmt_num(n)} {ANIMALITOS_DICT[n]}" for n in lista])
            st.markdown(f"**{eco}:** {nombres}")

    with st.expander("📋 Últimos 30 sorteos"):
        cols = ["fecha", "hora", "numero", "nombre"] if "hora" in df.columns else ["fecha", "numero", "nombre"]
        st.dataframe(df.tail(30)[cols], use_container_width=True)


if __name__ == "__main__":
    main()
