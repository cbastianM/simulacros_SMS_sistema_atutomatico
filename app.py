import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="ICFES Grader Pro", layout="wide", initial_sidebar_state="expanded")

# ── Constantes ────────────────────────────────────────────────────────────────

AREA_CODES = ['M', 'L', 'S', 'N', 'I']

AREA_LABEL = {
    'M': '🔢 Matemáticas',
    'L': '📖 Lectura Crítica',
    'S': '🌍 Sociales y Ciudadanas',
    'N': '🔬 Ciencias Naturales',
    'I': '🇬🇧 Inglés',
}

NIVELES = {
    1: {"label": "Nivel 1 —  5 preguntas por materia  (25 en total)",  "n":  5},
    2: {"label": "Nivel 2 — 10 preguntas por materia  (50 en total)",  "n": 10},
    3: {"label": "Nivel 3 — 20 preguntas por materia  (100 en total)", "n": 20},
    4: {"label": "Nivel 4 — 30 preguntas por materia  (150 en total)", "n": 30},
}

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
SIMULACROS_DIR = os.path.join(BASE_DIR, "SIMULACROS")

# ── Helpers ───────────────────────────────────────────────────────────────────

@st.cache_data
def list_simulacros():
    if not os.path.exists(SIMULACROS_DIR):
        return []
    return sorted(f[:-4] for f in os.listdir(SIMULACROS_DIR) if f.endswith('.csv'))

def load_simulacro(name):
    path = os.path.join(SIMULACROS_DIR, f"{name}.csv")
    df   = pd.read_csv(path)
    df.columns = [c.strip().upper() for c in df.columns]
    if 'AREA' not in df.columns:
        st.error(f"Columnas encontradas: {list(df.columns)} — se esperaba AREA")
        st.stop()
    df['AREA']      = df['AREA'].str.strip().str.upper()
    df['RESPUESTA'] = df['RESPUESTA'].str.strip().str.upper()
    return df

def score_class(pct):
    if pct >= 80: return "green",  "🌟 EXCELENTE"
    if pct >= 60: return "yellow", "👍 BUENO"
    return "red", "📚 NECESITA MEJORAR"

def init_respuestas():
    if 'respuestas' not in st.session_state:
        st.session_state['respuestas'] = {}

# ── Título ────────────────────────────────────────────────────────────────────

st.title("📝 Calificador ICFES Pro")

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("⚙️ Configuración")

    simulacros = list_simulacros()
    if not simulacros:
        st.error("No hay simulacros en la carpeta SIMULACROS/")
        st.stop()

    sel_sim = st.selectbox("Simulacro", simulacros)

    nivel = st.radio(
        "Nivel de dificultad",
        options=list(NIVELES.keys()),
        format_func=lambda k: NIVELES[k]["label"],
    )
    n_por_materia = NIVELES[nivel]["n"]

    generar = st.button("🎲 Generar Prueba", use_container_width=True, type="primary")

    # Indicador de progreso si hay prueba activa
    if 'prueba' in st.session_state:
        prueba_sidebar = st.session_state['prueba']
        respuestas_sidebar = st.session_state.get('respuestas', {})
        n_tot = len(prueba_sidebar)
        n_res = len(respuestas_sidebar)
        st.divider()
        st.metric("Progreso", f"{n_res} / {n_tot}", f"{n_res/n_tot*100:.0f}%" if n_tot else "0%")
        pct_prog = n_res / n_tot if n_tot else 0
        st.progress(pct_prog)

# ── Generar prueba ────────────────────────────────────────────────────────────

df_full = load_simulacro(sel_sim)

areas_presentes = df_full['AREA'].unique().tolist()
areas_faltantes = [a for a in AREA_CODES if a not in areas_presentes]
if areas_faltantes:
    st.error(f"El simulacro '{sel_sim}' no tiene las áreas: {', '.join(areas_faltantes)}")
    st.stop()

if generar:
    muestras = []
    avisos   = []
    for a in AREA_CODES:
        pool = df_full[df_full['AREA'] == a]
        n    = min(n_por_materia, len(pool))
        if n < n_por_materia:
            avisos.append(f"**{AREA_LABEL[a]}**: solo hay {len(pool)} preguntas (se tomarán todas)")
        muestra = pool.sample(n, random_state=None).reset_index(drop=True)
        muestras.append(muestra)

    st.session_state['prueba']     = pd.concat(muestras, ignore_index=True)
    st.session_state['respuestas'] = {}   # ← se limpian al generar nueva prueba
    st.session_state['resultado']  = None
    st.session_state['simulacro']  = sel_sim
    st.session_state['nivel']      = nivel
    st.session_state['inicio']     = datetime.now()

    for a in avisos:
        st.warning(a)

# ── Guardia: sin prueba activa ────────────────────────────────────────────────

if 'prueba' not in st.session_state:
    st.info("👈 Configura el nivel y presiona **Generar Prueba** para comenzar.")
    st.stop()

prueba: pd.DataFrame = st.session_state['prueba']
init_respuestas()
respuestas: dict = st.session_state['respuestas']

inicio   = st.session_state.get('inicio', datetime.now())
n_total  = len(prueba)
n_respon = len(respuestas)

# Banner de estado
st.info(
    f"📚 **Simulacro:** {st.session_state['simulacro']}  |  "
    f"🎯 **Nivel:** {st.session_state['nivel']}  |  "
    f"❓ **Preguntas:** {n_total}  |  "
    f"✏️ **Respondidas:** {n_respon}/{n_total}  |  "
    f"🕐 **Inicio:** {inicio.strftime('%H:%M:%S')}"
)

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_q, tab_r, tab_result = st.tabs([
    "📋 Preguntas",
    "✏️ Mis Respuestas",
    "📊 Resultados",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1 — PREGUNTAS (texto plano)
# ─────────────────────────────────────────────────────────────────────────────

with tab_q:
    st.subheader("📋 Preguntas de tu prueba")
    st.caption(
        "Este es el listado de las preguntas que te tocaron. "
        "Resuélvelas en tu cuadernillo y luego registra tus respuestas en la pestaña **✏️ Mis Respuestas**."
    )

    # ── Botón guardar ─────────────────────────────────────────────────────────
    todas_q = pd.DataFrame({
        'Nº':       [i + 1                              for i in range(n_total)],
        'Área':     [AREA_LABEL[prueba.iloc[i]['AREA']]  for i in range(n_total)],
        'Sesión':   [str(prueba.iloc[i]['SESION'])        for i in range(n_total)],
        'Pregunta': [str(prueba.iloc[i]['PREGUNTA'])      for i in range(n_total)],
    })
    ts_q = datetime.now().strftime('%Y%m%d_%H%M%S')
    st.download_button(
        label="💾 Guardar listado de preguntas",
        data=todas_q.to_csv(index=False),
        file_name=f"preguntas_{st.session_state['simulacro']}_N{st.session_state['nivel']}_{ts_q}.csv",
        mime="text/csv",
    )

    st.divider()

    for a in AREA_CODES:
        mask    = prueba['AREA'] == a
        indices = prueba.index[mask].tolist()   # índices 0-based en `prueba`
        if not indices:
            continue

        subset = prueba.loc[indices]
        st.markdown(f"### {AREA_LABEL[a]}")

        tabla_q = pd.DataFrame({
            'Nº':       [i + 1 for i in indices],
            'Sesión':   [str(prueba.loc[i, 'SESION'])    for i in indices],
            'Pregunta': [str(prueba.loc[i, 'PREGUNTA'])  for i in indices],
        })
        st.dataframe(tabla_q, use_container_width=True, hide_index=True)

        st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 — MIS RESPUESTAS
# ─────────────────────────────────────────────────────────────────────────────

with tab_r:
    st.subheader("✏️ Registrar respuestas")

    # ── Paso 1: cargar CSV de preguntas ───────────────────────────────────────
    uploaded = st.file_uploader(
        "📂 Carga el CSV de preguntas (generado en la pestaña **📋 Preguntas**)",
        type="csv",
        key="csv_preguntas",
    )

    if uploaded is None:
        st.info("Sube el CSV de preguntas para comenzar a registrar tus respuestas.")
        n_respon = len(respuestas)
    else:
        # ── Paso 2: construir tabla editable ──────────────────────────────────
        try:
            df_csv = pd.read_csv(uploaded)
            df_csv.columns = [c.strip() for c in df_csv.columns]
        except Exception as e:
            st.error(f"No se pudo leer el CSV: {e}")
            st.stop()

        for col in ['Nº', 'Sesión', 'Pregunta']:
            if col not in df_csv.columns:
                st.error(f"El CSV no tiene la columna **{col}**. ¿Subiste el archivo correcto?")
                st.stop()

        df_csv['Tu Respuesta'] = [
            respuestas.get(int(row['Nº']) - 1, None)
            for _, row in df_csv.iterrows()
        ]

        edited = st.data_editor(
            df_csv,
            column_config={
                c: st.column_config.TextColumn(c, disabled=True)
                for c in df_csv.columns if c != 'Tu Respuesta'
            } | {
                'Tu Respuesta': st.column_config.SelectboxColumn(
                    'Tu Respuesta',
                    options=['A', 'B', 'C', 'D'],
                    required=False,
                    width='medium',
                )
            },
            hide_index=True,
            use_container_width=True,
            height=min(60 + 35 * len(df_csv), 600),
            key='editor_respuestas',
        )

        for _, row in edited.iterrows():
            idx = int(row['Nº']) - 1
            val = row['Tu Respuesta']
            if val and val in ['A', 'B', 'C', 'D']:
                st.session_state['respuestas'][idx] = val
            elif not val and idx in st.session_state['respuestas']:
                del st.session_state['respuestas'][idx]

        respuestas = st.session_state['respuestas']
        n_respon   = len(respuestas)

        st.markdown(f"**Progreso: {n_respon} / {n_total}**")
        st.progress(n_respon / n_total if n_total else 0)

    # ── Botón calificar ───────────────────────────────────────────────────────
    st.divider()
    n_respon  = len(st.session_state.get('respuestas', {}))
    faltantes = n_total - n_respon
    if faltantes > 0:
        st.warning(f"⚠️ Faltan **{faltantes}** respuesta(s) para poder calificar.")

    calificar = st.button(
        "📊 Calificar",
        use_container_width=True,
        type="primary",
        disabled=(faltantes > 0),
        key="btn_calificar",
    )

    if calificar and faltantes == 0:
        fin      = datetime.now()
        duracion = fin - inicio
        minutos  = int(duracion.total_seconds() // 60)
        segundos = int(duracion.total_seconds() % 60)

        respuestas_est = [respuestas[i] for i in range(n_total)]
        respuestas_cor = prueba['RESPUESTA'].tolist()
        correctas_bool = [r == c for r, c in zip(respuestas_est, respuestas_cor)]

        total    = n_total
        aciertos = sum(correctas_bool)
        pct_total = aciertos / total * 100
        css, label = score_class(pct_total)

        # Tabla detalle
        resultados_df = pd.DataFrame({
            'Área':         prueba['AREA'].map(AREA_LABEL),
            'Sesión':       prueba['SESION'].astype(str),
            'Pregunta':     prueba['PREGUNTA'].astype(str),
            'Diste':        respuestas_est,
            'Correcta':     respuestas_cor,
            'Estado':       ['✓' if c else '✗' for c in correctas_bool],
        })

        # Por área
        area_stats = {}
        for a in AREA_CODES:
            mask   = prueba['AREA'] == a
            indices = prueba.index[mask].tolist()
            ok_m   = sum(correctas_bool[i] for i in indices)
            tot_m  = len(indices)
            area_stats[a] = {'ok': ok_m, 'tot': tot_m, 'pct': ok_m/tot_m*100 if tot_m else 0}

        # Guardar en session_state para mostrar en tab resultados
        st.session_state['resultado'] = {
            'total':      total,
            'aciertos':   aciertos,
            'pct':        pct_total,
            'css':        css,
            'label':      label,
            'detalle':    resultados_df,
            'area_stats': area_stats,
            'inicio':     inicio,
            'fin':        fin,
            'minutos':    minutos,
            'segundos':   segundos,
        }
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# TAB 3 — RESULTADOS
# ─────────────────────────────────────────────────────────────────────────────

with tab_result:
    if 'resultado' not in st.session_state or st.session_state['resultado'] is None:
        st.info("Completa todas las respuestas y presiona **📊 Calificar** en la pestaña anterior.")
    else:
        r = st.session_state['resultado']

        # ── Tiempo ────────────────────────────────────────────────────────────
        st.subheader("⏱️ Tiempo")
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("Inicio",   r['inicio'].strftime('%H:%M:%S'))
        tc2.metric("Fin",      r['fin'].strftime('%H:%M:%S'))
        tc3.metric("Duración", f"{r['minutos']}m {r['segundos']}s")

        st.divider()

        # ── Puntaje global ────────────────────────────────────────────────────
        if r['css'] == "green":
            st.success(f"{r['label']} — {r['pct']:.1f}%  ({r['aciertos']}/{r['total']} correctas)")
        elif r['css'] == "yellow":
            st.warning(f"{r['label']} — {r['pct']:.1f}%  ({r['aciertos']}/{r['total']} correctas)")
        else:
            st.error(f"{r['label']} — {r['pct']:.1f}%  ({r['aciertos']}/{r['total']} correctas)")

        # ── Por área ──────────────────────────────────────────────────────────
        st.subheader("📊 Resultados por área")
        cols = st.columns(len(AREA_CODES))
        for i, a in enumerate(AREA_CODES):
            s = r['area_stats'][a]
            cols[i].metric(AREA_LABEL[a], f"{s['ok']}/{s['tot']}", f"{s['pct']:.0f}%")

        # ── Detalle ───────────────────────────────────────────────────────────
        st.subheader("📋 Detalle pregunta a pregunta")

        def color_estado(val):
            return 'color:#0caf00;font-weight:bold' if val == '✓' else 'color:#d32f2f;font-weight:bold'

        st.dataframe(
            r['detalle'].style.map(color_estado, subset=['Estado']),
            use_container_width=True,
            hide_index=True,
        )

        # ── Descargas ─────────────────────────────────────────────────────────
        st.divider()
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        c1, c2 = st.columns(2)

        resumen = pd.DataFrame([{
            'Simulacro':  st.session_state['simulacro'],
            'Nivel':      st.session_state['nivel'],
            'Correctas':  r['aciertos'],
            'Total':      r['total'],
            'Porcentaje': f"{r['pct']:.1f}%",
            'Inicio':     r['inicio'].strftime('%d/%m/%Y %H:%M:%S'),
            'Fin':        r['fin'].strftime('%d/%m/%Y %H:%M:%S'),
            'Duración':   f"{r['minutos']}m {r['segundos']}s",
        }])
        with c1:
            st.download_button(
                "📄 Descargar Resumen",
                resumen.to_csv(index=False),
                f"resumen_{st.session_state['simulacro']}_N{st.session_state['nivel']}_{ts}.csv",
                "text/csv",
            )
        with c2:
            st.download_button(
                "📊 Descargar Detalle",
                r['detalle'].to_csv(index=False),
                f"detalle_{st.session_state['simulacro']}_N{st.session_state['nivel']}_{ts}.csv",
                "text/csv",
            )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption("📁 Simulacros desde SIMULACROS/  ·  columnas requeridas: PREGUNTA, SESION, RESPUESTA, AREA  (M / L / S / N / I)")
