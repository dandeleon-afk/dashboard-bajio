"""
=============================================================
  DASHBOARD: ANÁLISIS DE IMPORTACIONES DE INSUMOS - BAJÍO
=============================================================
Autor:   Tu nombre aquí
Datos:   API DataMéxico / Secretaría de Economía
Deploy:  Streamlit Cloud (streamlit.io)

PASOS PARA EJECUTAR LOCALMENTE:
  1. Instala dependencias:
       pip install streamlit pandas plotly requests
  2. Corre el dashboard:
       streamlit run dashboard_bajio.py
  3. Se abrirá automáticamente en tu navegador.

PASOS PARA SUBIR A STREAMLIT CLOUD:
  1. Sube este archivo + requirements.txt a un repo público en GitHub.
  2. Ve a share.streamlit.io y conecta tu repositorio.
=============================================================
"""

# ── Librerías ──────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json

# ══════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN GENERAL DE LA PÁGINA
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Importaciones Bajío",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Paleta de colores por estado
COLORES_ESTADOS = {
    "Aguascalientes": "#E63946",
    "Guanajuato":     "#457B9D",
    "Querétaro":      "#2A9D8F",
    "San Luis Potosí":"#E9C46A",
}
COLORES_SEQ = ["#E63946","#457B9D","#2A9D8F","#E9C46A","#F4A261","#264653","#A8DADC","#1D3557"]

# ══════════════════════════════════════════════════════════
# 2. CARGA DE DATOS DESDE LA API
#    @st.cache_data guarda los datos en memoria para no
#    volver a descargarlos cada vez que el usuario mueve un filtro.
# ══════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Descargando datos de la API DataMéxico…")
def cargar_datos():
    URL = (
        "https://www.economia.gob.mx/apidatamexico/tesseract/data.jsonrecords"
        "?Chapter+4+Digit=11%2C13%2C14%2C15%2C16%2C17%2C18%2C19%2C20%2C5%2C6%2C7%2C9"
        "&Flow=1"
        "&Month=201503%2C201506%2C201509%2C201512"
        "%2C201603%2C201606%2C201609%2C201612"
        "%2C201703%2C201706%2C201709%2C201712"
        "%2C201803%2C201806%2C201809%2C201812"
        "%2C201903%2C201906%2C201909%2C201912"
        "%2C202003%2C202006%2C202009%2C202012"
        "%2C202103%2C202106%2C202109%2C202112"
        "%2C202203%2C202206%2C202209%2C202212"
        "%2C202303%2C202306%2C202309%2C202312"
        "%2C202403%2C202406%2C202409%2C202412"
        "%2C202503%2C202506%2C202509%2C202512"
        "&State=1%2C11%2C22%2C24"
        "&cube=economy_foreign_trade_ent"
        "&drilldowns=Chapter+4+Digit%2CCountry%2CFlow%2CMonth%2CState%2CYear"
        "&locale=es"
        "&measures=Trade+Value"
    )

    try:
        r = requests.get(URL, timeout=60)
        r.raise_for_status()
        datos = r.json()
        # La API Tesseract puede devolver {"data": [...]} o directamente [...]
        registros = datos.get("data", datos) if isinstance(datos, dict) else datos
        df = pd.DataFrame(registros)
    except Exception as e:
        st.error(f"❌ Error al conectar con la API: {e}")
        return pd.DataFrame()

    if df.empty:
        return df

    # ── Renombrar columnas ─────────────────────────────────
    renombrar = {
        "Chapter 4 Digit":      "capitulo_id",
        "Chapter 4 Digit Name": "capitulo",
        "Country":              "pais_id",
        "Country Name":         "pais",
        "Flow":                 "flujo_id",
        "Flow Name":            "flujo",
        "Month":                "mes_id",
        "Month Name":           "mes_nombre",
        "State":                "estado_id",
        "State Name":           "estado",
        "Year":                 "anio",
        "Trade Value":          "valor_usd",
    }
    df.rename(columns={k: v for k, v in renombrar.items() if k in df.columns}, inplace=True)

    # ── Tipos de datos ─────────────────────────────────────
    if "valor_usd" in df.columns:
        df["valor_usd"] = pd.to_numeric(df["valor_usd"], errors="coerce").fillna(0)
    if "anio" in df.columns:
        df["anio"] = df["anio"].astype(str)
    if "mes_id" in df.columns:
        df["fecha"] = pd.to_datetime(df["mes_id"].astype(str), format="%Y%m", errors="coerce")

    # Mapa de IDs de estado por si la API no devuelve el nombre
    mapa_estados = {"1":"Aguascalientes","11":"Guanajuato","22":"Querétaro","24":"San Luis Potosí"}
    if "estado" not in df.columns and "estado_id" in df.columns:
        df["estado"] = df["estado_id"].astype(str).map(mapa_estados).fillna(df["estado_id"].astype(str))

    return df


# ══════════════════════════════════════════════════════════
# 3. CARGAMOS LOS DATOS
# ══════════════════════════════════════════════════════════
df_raw = cargar_datos()

if df_raw.empty:
    st.warning("⚠️ No se pudieron cargar datos. Revisa la conexión o la URL de la API.")
    st.stop()

# Columna de capítulo (puede venir con nombre o solo con ID)
col_cap = "capitulo" if "capitulo" in df_raw.columns else "capitulo_id"
col_pais = "pais"    if "pais"    in df_raw.columns else "pais_id"

# ══════════════════════════════════════════════════════════
# 4. BARRA LATERAL — FILTROS
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🔍 Filtros")
    st.markdown("---")

    # Años
    if "anio" in df_raw.columns:
        anios = sorted(df_raw["anio"].dropna().unique())
        rango = st.select_slider("Rango de años", options=anios, value=(anios[0], anios[-1]))
    else:
        rango = (None, None)

    # Estados
    if "estado" in df_raw.columns:
        est_opts = sorted(df_raw["estado"].dropna().unique())
        estados_sel = st.multiselect("Estados", options=est_opts, default=est_opts)
    else:
        estados_sel = []

    # Capítulos
    cap_opts = sorted(df_raw[col_cap].dropna().unique())
    caps_sel = st.multiselect("Capítulos arancelarios", options=cap_opts, default=cap_opts)

    st.markdown("---")
    st.caption("Fuente: DataMéxico / SE")
    st.caption("Flujo: Importaciones")
    st.caption("Periodo: 2015 Q1 – 2025 Q4")

# ══════════════════════════════════════════════════════════
# 5. APLICAR FILTROS
# ══════════════════════════════════════════════════════════
df = df_raw.copy()
if rango[0]:
    df = df[df["anio"].between(rango[0], rango[1])]
if estados_sel and "estado" in df.columns:
    df = df[df["estado"].isin(estados_sel)]
if caps_sel:
    df = df[df[col_cap].isin(caps_sel)]

# ══════════════════════════════════════════════════════════
# 6. ENCABEZADO + KPIs
# ══════════════════════════════════════════════════════════
st.title("📦 Importaciones de Insumos — Región Bajío")
st.markdown(
    "Análisis de importaciones en **Aguascalientes · Guanajuato · Querétaro · San Luis Potosí** "
    "(2015–2025). Usa los filtros de la izquierda para explorar."
)

# KPIs
k1, k2, k3, k4 = st.columns(4)
total = df["valor_usd"].sum()
k1.metric("💰 Valor total",
          f"${total/1e9:.2f} B USD" if total >= 1e9 else f"${total/1e6:.1f} M USD")
k2.metric("🌍 Países proveedores", f"{df[col_pais].nunique():,}")
k3.metric("📋 Capítulos",          f"{df[col_cap].nunique():,}")
k4.metric("📊 Registros",          f"{len(df):,}")

st.markdown("---")

# ══════════════════════════════════════════════════════════
# 7. TABS — cada sección en su propia pestaña
#    Esto evita el error "removeChild" al no montar todas
#    las gráficas al mismo tiempo.
# ══════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Evolución Temporal",
    "🌍 Países Proveedores",
    "📋 Capítulos Arancelarios",
    "🗺️ Comparativo Estados",
    "🔎 Datos",
])

# ──────────────────────────────────────────────────────────
# TAB 1: EVOLUCIÓN TEMPORAL
# ──────────────────────────────────────────────────────────
with tab1:
    st.subheader("Evolución de importaciones por año y estado")

    if "anio" in df.columns and "estado" in df.columns:
        df_anual = df.groupby(["anio","estado"], as_index=False)["valor_usd"].sum()

        fig1 = px.line(
            df_anual, x="anio", y="valor_usd", color="estado",
            title="Valor importado por año y estado",
            labels={"anio":"Año","valor_usd":"Valor (USD)","estado":"Estado"},
            color_discrete_map=COLORES_ESTADOS,
            markers=True,
        )
        fig1.update_layout(hovermode="x unified", yaxis_tickformat="$,.0f")
        st.plotly_chart(fig1, use_container_width=True)

    if "fecha" in df.columns and "estado" in df.columns:
        df["trimestre"] = df["fecha"].dt.to_period("Q").astype(str)
        df_trim = df.groupby(["trimestre","estado"], as_index=False)["valor_usd"].sum()

        fig2 = px.bar(
            df_trim, x="trimestre", y="valor_usd", color="estado",
            title="Importaciones trimestrales por estado (apiladas)",
            labels={"trimestre":"Trimestre","valor_usd":"Valor (USD)","estado":"Estado"},
            color_discrete_map=COLORES_ESTADOS,
            barmode="stack",
        )
        fig2.update_layout(yaxis_tickformat="$,.0f", xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)

# ──────────────────────────────────────────────────────────
# TAB 2: PAÍSES PROVEEDORES
# ──────────────────────────────────────────────────────────
with tab2:
    st.subheader("Principales países proveedores de insumos")

    n = st.slider("¿Cuántos países mostrar?", 5, 30, 15, 5, key="sl_paises")

    df_paises = (
        df.groupby(col_pais, as_index=False)["valor_usd"]
        .sum().sort_values("valor_usd", ascending=False).head(n)
    )

    fig3 = px.bar(
        df_paises, x="valor_usd", y=col_pais, orientation="h",
        title=f"Top {n} países por valor importado",
        labels={"valor_usd":"Valor (USD)", col_pais:"País"},
        color="valor_usd", color_continuous_scale="Blues",
    )
    fig3.update_layout(yaxis={"categoryorder":"total ascending"},
                       xaxis_tickformat="$,.0f", coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        fig4 = px.pie(
            df_paises, names=col_pais, values="valor_usd",
            title=f"Participación top {n} países",
            color_discrete_sequence=COLORES_SEQ, hole=0.4,
        )
        fig4.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig4, use_container_width=True)

    with c2:
        if "anio" in df.columns:
            top5 = df_paises[col_pais].head(5).tolist()
            df_t5 = (df[df[col_pais].isin(top5)]
                     .groupby(["anio", col_pais], as_index=False)["valor_usd"].sum())
            fig5 = px.line(
                df_t5, x="anio", y="valor_usd", color=col_pais,
                title="Evolución top 5 países",
                labels={"anio":"Año","valor_usd":"Valor (USD)", col_pais:"País"},
                markers=True, color_discrete_sequence=COLORES_SEQ,
            )
            fig5.update_layout(yaxis_tickformat="$,.0f")
            st.plotly_chart(fig5, use_container_width=True)

# ──────────────────────────────────────────────────────────
# TAB 3: CAPÍTULOS ARANCELARIOS
# ──────────────────────────────────────────────────────────
with tab3:
    st.subheader("Estructura por capítulo arancelario (tipo de insumo)")

    df_caps = (df.groupby(col_cap, as_index=False)["valor_usd"]
               .sum().sort_values("valor_usd", ascending=False))

    c3, c4 = st.columns([3,2])
    with c3:
        fig6 = px.bar(
            df_caps, x=col_cap, y="valor_usd",
            title="Valor total por capítulo",
            labels={col_cap:"Capítulo","valor_usd":"Valor (USD)"},
            color="valor_usd", color_continuous_scale="Viridis",
        )
        fig6.update_layout(xaxis_tickangle=-45, yaxis_tickformat="$,.0f",
                           coloraxis_showscale=False)
        st.plotly_chart(fig6, use_container_width=True)

    with c4:
        fig7 = px.pie(
            df_caps, names=col_cap, values="valor_usd",
            title="Distribución por capítulo",
            color_discrete_sequence=COLORES_SEQ, hole=0.35,
        )
        fig7.update_traces(textposition="inside", textinfo="percent")
        st.plotly_chart(fig7, use_container_width=True)

    # Heatmap capítulo × estado
    if "estado" in df.columns:
        df_heat = (df.groupby([col_cap,"estado"], as_index=False)["valor_usd"]
                   .sum()
                   .pivot(index=col_cap, columns="estado", values="valor_usd")
                   .fillna(0))
        fig8 = px.imshow(
            df_heat,
            title="Mapa de calor: Capítulo vs Estado",
            labels={"color":"Valor (USD)"},
            color_continuous_scale="Blues",
            aspect="auto", text_auto=".2s",
        )
        st.plotly_chart(fig8, use_container_width=True)

# ──────────────────────────────────────────────────────────
# TAB 4: COMPARATIVO ENTRE ESTADOS
# ──────────────────────────────────────────────────────────
with tab4:
    st.subheader("Comparativo de importaciones entre los cuatro estados del Bajío")

    if "estado" in df.columns:
        df_est = (df.groupby("estado", as_index=False)["valor_usd"]
                  .sum().sort_values("valor_usd", ascending=False))

        c5, c6 = st.columns(2)
        with c5:
            fig9 = px.bar(
                df_est, x="estado", y="valor_usd",
                title="Total importado por estado",
                labels={"estado":"Estado","valor_usd":"Valor (USD)"},
                color="estado", color_discrete_map=COLORES_ESTADOS,
            )
            fig9.update_layout(yaxis_tickformat="$,.0f", showlegend=False)
            st.plotly_chart(fig9, use_container_width=True)

        with c6:
            fig10 = px.pie(
                df_est, names="estado", values="valor_usd",
                title="Participación % por estado",
                color="estado", color_discrete_map=COLORES_ESTADOS, hole=0.4,
            )
            fig10.update_traces(textinfo="percent+label")
            st.plotly_chart(fig10, use_container_width=True)

        if "anio" in df.columns:
            df_ea = df.groupby(["anio","estado"], as_index=False)["valor_usd"].sum()
            fig11 = px.area(
                df_ea, x="anio", y="valor_usd", color="estado",
                title="Composición por estado a lo largo del tiempo",
                labels={"anio":"Año","valor_usd":"Valor (USD)","estado":"Estado"},
                color_discrete_map=COLORES_ESTADOS,
            )
            fig11.update_layout(yaxis_tickformat="$,.0f")
            st.plotly_chart(fig11, use_container_width=True)

# ──────────────────────────────────────────────────────────
# TAB 5: TABLA DE DATOS
# ──────────────────────────────────────────────────────────
with tab5:
    st.subheader("Datos filtrados")
    st.dataframe(
        df.sort_values("valor_usd", ascending=False).reset_index(drop=True),
        use_container_width=True, height=450,
    )
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇️ Descargar CSV", data=csv_bytes,
        file_name="importaciones_bajio.csv", mime="text/csv",
    )

# ── Pie de página ──────────────────────────────────────────
st.markdown("---")
st.caption(
    "Fuente: DataMéxico — Secretaría de Economía | "
    "Flujo: Importaciones (Flow=1) | "
    "Estados: Aguascalientes (1) · Guanajuato (11) · Querétaro (22) · San Luis Potosí (24)"
)
