import streamlit as st
import requests
import pandas as pd
import datetime
import plotly.graph_objects as go

st.set_page_config(
    page_title="Gestor de Gastos y Billeteras",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Conector oficial vinculado a tu Google Sheets
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx2dGYUL5di7w76sEsw5AwxgmCVs0Df0BbNKw5WgF2x4hlxIK8KVLbNIEgbfKXdnYnO/exec"

CATEGORIAS = [
    "Salidas CH", "Fiestas", "Salidas familiares", 
    "Comidas familiares", "Gasolina", "Pt", 
    "Comidas", "Pagos Créditos", "Otros"
]

CUENTAS = ["BCP", "Yape", "Efectivo", "Wardaditos"]

st.markdown("""
<style>
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 4rem !important;
        padding-left: 0.6rem !important;
        padding-right: 0.6rem !important;
        max-width: 500px !important;
    }
    .total-banner {
        background: linear-gradient(135deg, #0A2540 0%, #1A365D 100%);
        border-radius: 14px;
        padding: 16px;
        text-align: center;
        color: white;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .total-title {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #90CDF4;
        font-weight: 700;
        margin: 0;
    }
    .total-amount {
        font-size: 2.1rem;
        font-weight: 800;
        margin-top: 4px;
    }
    .metric-hoy {
        background-color: #FFF7ED;
        border: 1px solid #FFEDD5;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

if "saldos_base" not in st.session_state:
    st.session_state["saldos_base"] = {
        "BCP": 1250.00,
        "Yape": 340.50,
        "Efectivo": 180.00,
        "Wardaditos": 500.00
    }

@st.cache_data(ttl=10)
def obtener_movimientos():
    try:
        r = requests.get(APPS_SCRIPT_URL, timeout=8)
        if r.status_code == 200:
            return r.json().get("movimientos", [])
    except Exception as e:
        st.error(f"Error al sincronizar con Google Sheets: {e}")
    return []

movimientos = obtener_movimientos()

# Cálculo dinámico de saldos actuales sumando/restando movimientos
saldos_actuales = dict(st.session_state["saldos_base"])
for m in movimientos:
    monto = float(m.get("monto", 0))
    cuenta = m.get("cuenta")
    tipo = m.get("tipo")
    if cuenta in saldos_actuales:
        if tipo in ["Gasto", "Transferencia Salida"]:
            saldos_actuales[cuenta] -= monto
        elif tipo in ["Ingreso", "Transferencia Entrada"]:
            saldos_actuales[cuenta] += monto

total_general = sum(saldos_actuales.values())

# ==========================================
# ELEMENTO 1: ENCABEZADO SUPERIOR
# ==========================================
st.markdown(f"""
<div class="total-banner">
    <p class="total-title">Total General Disponible</p>
    <div class="total-amount">S/. {total_general:,.2f}</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# ELEMENTO 2: FORMULARIO PRINCIPAL REGISTRAR GASTO
# ==========================================
with st.expander("➕ REGISTRAR GASTO", expanded=True):
    with st.form("form_gasto", clear_on_submit=True):
        col_m, col_cta = st.columns(2)
        with col_m:
            monto = st.number_input("Monto (S/.)", min_value=0.10, step=1.0, format="%.2f")
        with col_cta:
            cuenta = st.selectbox("Cuenta de Salida", options=CUENTAS, index=1) # Yape por defecto

        descripcion = st.text_input("Descripción / Concepto", placeholder="¿En qué se gastó?")
        categoria = st.selectbox("Categoría", options=CATEGORIAS, index=6) # Comidas por defecto

        col_f, col_h = st.columns(2)
        with col_f:
            fecha_reg = st.date_input("Fecha", datetime.date.today())
        with col_h:
            hora_reg = st.time_input("Hora", datetime.datetime.now().time())

        btn_gasto = st.form_submit_button("💳 Registrar Gasto", use_container_width=True)

        if btn_gasto:
            fecha_completa = f"{fecha_reg.strftime('%Y-%m-%d')} {hora_reg.strftime('%H:%M:%S')}"
            payload = {
                "accion": "REGISTRAR_GASTO",
                "fechaHora": fecha_completa,
                "cuenta": cuenta,
                "categoria": categoria,
                "descripcion": descripcion if descripcion else categoria,
                "monto": monto
            }
            try:
                res = requests.post(APPS_SCRIPT_URL, json=payload, timeout=8)
                if res.status_code == 200:
                    st.cache_data.clear()
                    st.success("¡Gasto guardado en Google Sheets con éxito!")
                    st.rerun()
                else:
                    st.error("No se pudo registrar en la hoja.")
            except Exception as e:
                st.error(f"Error al enviar datos: {e}")

# ==========================================
# ELEMENTO 3: MÉTRICAS DEL DÍA (00:00 a 24:00)
# ==========================================
col_sel_dia, _ = st.columns([1, 1])
with col_sel_dia:
    dia_consulta = st.date_input("📅 Ver fecha:", datetime.date.today(), key="filtro_dia")

# Regla de cálculo estricta: Gastos del día calendario seleccionado (00:00:00 a 23:59:59)
gasto_dia_acumulado = 0.0
for m in movimientos:
    if m.get("tipo") == "Gasto":
        f_str = str(m.get("fechaHora", ""))
        try:
            f_fecha = datetime.datetime.strptime(f_str[:10], "%Y-%m-%d").date()
            if f_fecha == dia_consulta:
                gasto_dia_acumulado += float(m.get("monto", 0))
        except:
            pass

texto_dia = "Hoy has gastado" if dia_consulta == datetime.date.today() else f"Gasto del {dia_consulta.strftime('%d/%m/%Y')}"

st.markdown(f"""
<div class="metric-hoy">
    <div>
        <div style="font-size:0.75rem; font-weight:700; color:#C2410C; text-transform:uppercase;">{texto_dia}</div>
        <div style="font-size:1.6rem; font-weight:800; color:#7C2D12;">S/. {gasto_dia_acumulado:,.2f}</div>
        <div style="font-size:0.68rem; color:#9A3412;">00:00:00 a 23:59:59 hrs</div>
    </div>
    <div style="font-size:1.8rem;">📉</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# ELEMENTO 4: BILLETERAS COMPACTAS Y TRANSFERENCIA
# ==========================================
col_header_w, col_btn_tr = st.columns([2, 1])
with col_header_w:
    st.markdown("**Billeteras**")
with col_btn_tr:
    abrir_tr = st.button("🔄 Transferir", use_container_width=True)

b1, b2 = st.columns(2)
with b1:
    st.metric("BCP", f"S/. {saldos_actuales['BCP']:,.2f}")
    st.metric("Efectivo", f"S/. {saldos_actuales['Efectivo']:,.2f}")
with b2:
    st.metric("Yape", f"S/. {saldos_actuales['Yape']:,.2f}")
    st.metric("Wardaditos", f"S/. {saldos_actuales['Wardaditos']:,.2f}")

if abrir_tr:
    with st.form("form_transferencia"):
        st.subheader("Mover / Transferir Saldo")
        c_orig = st.selectbox("Billetera Origen", options=CUENTAS, index=0)
        c_dest = st.selectbox("Billetera Destino", options=CUENTAS, index=1)
        m_transf = st.number_input("Monto a Mover (S/.)", min_value=0.10, step=1.0, format="%.2f")
        nota_transf = st.text_input("Nota / Concepto (opcional)", placeholder="Pase para compras")
        
        btn_confirmar_tr = st.form_submit_button("Confirmar Transferencia", use_container_width=True)

        if btn_confirmar_tr:
            if c_orig == c_dest:
                st.error("Origen y destino no pueden ser iguales.")
            elif m_transf > saldos_actuales[c_orig]:
                st.error(f"Saldo insuficiente en {c_orig} (Disponible: S/. {saldos_actuales[c_orig]:,.2f})")
            else:
                payload_tr = {
                    "accion": "TRANSFERENCIA",
                    "fechaHora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cuentaOrigen": c_orig,
                    "cuentaDestino": c_dest,
                    "monto": m_transf,
                    "nota": nota_transf
                }
                try:
                    res = requests.post(APPS_SCRIPT_URL, json=payload_tr, timeout=8)
                    if res.status_code == 200:
                        st.cache_data.clear()
                        st.success("¡Transferencia registrada en Sheets!")
                        st.rerun()
                    else:
                        st.error("No se pudo registrar la transferencia.")
                except Exception as e:
                    st.error(f"Error al transferir: {e}")

# ==========================================
# RESUMEN DE MOVIMIENTOS RECIENTES
# ==========================================
with st.expander("📋 Ver Últimos Movimientos"):
    if movimientos:
        df_movs = pd.DataFrame(movimientos)
        st.dataframe(df_movs.tail(15).iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.caption("No hay movimientos registrados todavía.")
