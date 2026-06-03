import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="ICFES Grader Pro", layout="wide", initial_sidebar_state="expanded")

AREA_CODES = ['M', 'L', 'S', 'N', 'I']

AREA_LABEL = {
    'M': '🔢 Matemáticas',
    'L': '📖 Lectura',
    'S': '🌍 Sociales',
    'N': '🔬 Naturales',
    'I': '🇬🇧 Inglés',
}

NIVELES = {
    1: {"label": "Nivel 1 —  5 preguntas por materia  (25 en total)",  "n":  5},
    2: {"label": "Nivel 2 — 10 preguntas por materia  (50 en total)",  "n": 10},
    3: {"label": "Nivel 3 — 20 preguntas por materia  (100 en total)", "n": 20},
    4: {"label": "Nivel 4 — 30 preguntas por materia  (150 en total)", "n": 30},
}

st.title("📝 Calificador ICFES Pro")

# ── helpers ──────────────────────────────────────────────────────────────────

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
SIMULACROS_DIR = os.path.join(BASE_DIR, "SIMULACROS")

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

# ── sidebar ───────────────────────────────────────────────────────────────────

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
        format_func=lambda k: NIVELES[k]["label"]
    )
    n_por_materia = NIVELES[nivel]["n"]

    generar = st.button("🎲 Generar Prueba", use_container_width=True, type="primary")

# ── generar prueba ────────────────────────────────────────────────────────────

df_full = load_simulacro(sel_sim)

# Verificar que el simulacro tiene todas las áreas requeridas
areas_presentes = df_full['AREA'].unique().tolist()
areas_faltantes = [a for a in AREA_CODES if a not in areas_presentes]
if areas_faltantes:
    st.error(f"El simulacro '{sel_sim}' no tiene las áreas: {', '.join(areas_faltantes)}")
    st.stop()

# Inicializar prueba en session_state
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

    st.session_state['prueba']    = pd.concat(muestras, ignore_index=True)
    st.session_state['resultado'] = None
    st.session_state['simulacro'] = sel_sim
    st.session_state['nivel']     = nivel
    st.session_state['inicio']    = datetime.now()

    if avisos:
        for a in avisos:
            st.warning(a)

# ── mostrar prueba ─────────────────────────────────────────────────────────────

if 'prueba' not in st.session_state:
    st.info("👈 Configura el nivel y presiona **Generar Prueba** para comenzar.")
    st.stop()

prueba: pd.DataFrame = st.session_state['prueba']
prueba.columns = [c.strip().upper() for c in prueba.columns]

inicio = st.session_state.get('inicio', datetime.now())
st.info(f"📚 **Simulacro:** {st.session_state['simulacro']}  |  🎯 **Nivel:** {st.session_state['nivel']}  |  ❓ **Preguntas:** {len(prueba)}  |  🕐 **Inicio:** {inicio.strftime('%H:%M:%S')}")

st.subheader("📋 Ingresa tus respuestas (A / B / C / D)")
st.caption("Puedes editar directamente en la tabla.")

# Construir tabla editable
tabla = pd.DataFrame({
    'Área':         prueba['AREA'].map(AREA_LABEL),
    'Sesión':       prueba['SESION'].astype(str),
    'Pregunta':     prueba['PREGUNTA'].astype(str),
    'Tu Respuesta': [""] * len(prueba),
})

edited = st.data_editor(
    tabla,
    column_config={
        "Área":         st.column_config.TextColumn("Área",     disabled=True),
        "Sesión":       st.column_config.TextColumn("Sesión",   disabled=True),
        "Pregunta":     st.column_config.TextColumn("Pregunta", disabled=True),
        "Tu Respuesta": st.column_config.SelectboxColumn(
            "Tu Respuesta",
            options=["A", "B", "C", "D"],
            required=False,
        ),
    },
    hide_index=True,
    use_container_width=True,
    height=min(60 + 35 * len(prueba), 600),
    key="editor"
)

# ── calificar ──────────────────────────────────────────────────────────────────

st.divider()
col_l, col_c, col_r = st.columns([1, 1, 1])
with col_c:
    calificar = st.button("📊 Calificar", use_container_width=True, type="primary")

if calificar:
    vacias = edited['Tu Respuesta'].isna() | (edited['Tu Respuesta'].str.strip() == "")
    if vacias.any():
        st.warning(f"⚠️ Faltan {vacias.sum()} respuesta(s) por completar.")
    else:
        fin      = datetime.now()
        inicio   = st.session_state.get('inicio', fin)
        duracion = fin - inicio
        minutos  = int(duracion.total_seconds() // 60)
        segundos = int(duracion.total_seconds() % 60)

        respuestas_est = edited['Tu Respuesta'].str.upper().str.strip().values
        respuestas_cor = prueba['RESPUESTA'].values
        correctas_bool = respuestas_est == respuestas_cor

        # Tabla de resultados completa
        resultados_df = pd.DataFrame({
            'Área':     prueba['AREA'].map(AREA_LABEL),
            'Sesión':   prueba['SESION'].astype(str),
            'Pregunta': prueba['PREGUNTA'].astype(str),
            'Diste':    respuestas_est,
            'Correcta': respuestas_cor,
            'Estado':   ['✓' if c else '✗' for c in correctas_bool],
        })

        # ── Score global
        total    = len(prueba)
        aciertos = int(correctas_bool.sum())
        pct_total = aciertos / total * 100
        css, label = score_class(pct_total)

        # Tiempo
        st.subheader("⏱️ Tiempo")
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("Inicio",       inicio.strftime('%H:%M:%S'))
        tc2.metric("Fin",          fin.strftime('%H:%M:%S'))
        tc3.metric("Duración",     f"{minutos}m {segundos}s")

        st.divider()

        if css == "green":
            st.success(f"{label} — {pct_total:.1f}%  ({aciertos}/{total} correctas)")
        elif css == "yellow":
            st.warning(f"{label} — {pct_total:.1f}%  ({aciertos}/{total} correctas)")
        else:
            st.error(f"{label} — {pct_total:.1f}%  ({aciertos}/{total} correctas)")

        # ── Score por área
        st.subheader("📊 Resultados por área")
        cols = st.columns(len(AREA_CODES))
        for i, a in enumerate(AREA_CODES):
            mask  = prueba['AREA'] == a
            tot_m = int(mask.sum())
            ok_m  = int(correctas_bool[mask].sum())
            pct_m = ok_m / tot_m * 100 if tot_m else 0
            cols[i].metric(AREA_LABEL[a], f"{ok_m}/{tot_m}", f"{pct_m:.0f}%")

        # ── Detalle
        st.subheader("📋 Detalle pregunta a pregunta")

        def color_estado(val):
            return 'color:#0caf00;font-weight:bold' if val == '✓' else 'color:#d32f2f;font-weight:bold'

        st.dataframe(
            resultados_df.style.applymap(color_estado, subset=['Estado']),
            use_container_width=True,
            hide_index=True
        )

        # ── Descargar
        st.divider()
        c1, c2 = st.columns(2)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        with c1:
            resumen = pd.DataFrame([{
                'Simulacro':  sel_sim,
                'Nivel':      nivel,
                'Correctas':  aciertos,
                'Total':      total,
                'Porcentaje': f'{pct_total:.1f}%',
                'Inicio':     inicio.strftime('%d/%m/%Y %H:%M:%S'),
                'Fin':        fin.strftime('%d/%m/%Y %H:%M:%S'),
                'Duración':   f'{minutos}m {segundos}s',
            }])
            st.download_button("📄 Descargar Resumen",
                               resumen.to_csv(index=False),
                               f"resumen_{sel_sim}_N{nivel}_{ts}.csv",
                               "text/csv")
        with c2:
            st.download_button("📊 Descargar Detalle",
                               resultados_df.to_csv(index=False),
                               f"detalle_{sel_sim}_N{nivel}_{ts}.csv",
                               "text/csv")

# ── footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption("📁 Simulacros desde SIMULACROS/ · columnas: PREGUNTA, SESION, RESPUESTA, AREA  (M / L / S / N / I)")