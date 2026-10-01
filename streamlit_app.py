import streamlit as st
import requests
import pandas as pd
import datetime

st.set_page_config(
    page_title="GESTOR DE GASTOS Y BILLETERAS",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed"
)

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
        padding-top: 0.8rem !important;
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
        font-size: 0.72rem;
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

# 1. OBTENCIÓN ROBUSTA DE DATOS DESDE SHEETS
@st.cache_data(ttl=5)
def cargar_datos_sheets():
    try:
        r = requests.get(APPS_SCRIPT_URL, timeout=10)
        if r.status_code == 200:
            res = r.json()
            return res.get("movimientos", []), res.get("saldosBase", {c: 0.0 for c in CUENTAS})
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
    return [], {"BCP": 1250.0, "Yape": 340.5, "Efectivo": 180.0, "Wardaditos": 500.0}

movimientos, saldos_base = cargar_datos_sheets()

# 2. CÁLCULO DINÁMICO DE SALDOS DE BILLETERAS
saldos_actuales = dict(saldos_base)
for m in movimientos:
    monto = float(m.get("monto", 0))
    cta = m.get("cuenta")
    tipo = m.get("tipo")
    if cta in saldos_actuales:
        if tipo in ["Gasto", "Transferencia Salida"]:
            saldos_actuales[cta] -= monto
        elif tipo in ["Ingreso", "Transferencia Entrada"]:
            saldos_actuales[cta] += monto

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
# ELEMENTO 2: ACCIÓN INMEDIATA (GASTO / INGRESO)
# ==========================================
tab_gasto, tab_ingreso = st.tabs(["➕ REGISTRAR GASTO", "💵 REGISTRAR INGRESO"])

with tab_gasto:
    with st.form("form_gasto", clear_on_submit=True):
        col_m, col_cta = st.columns(2)
        with col_m:
            monto_g = st.number_input("Monto Gasto (S/.)", min_value=0.10, step=1.0, format="%.2f")
        with col_cta:
            cuenta_g = st.selectbox("Cuenta de Salida", options=CUENTAS, index=1)

        desc_g = st.text_input("Descripción", placeholder="¿En qué se gastó?")
        cat_g = st.selectbox("Categoría", options=CATEGORIAS, index=6)

        col_f, col_h = st.columns(2)
        with col_f:
            f_g = st.date_input("Fecha", datetime.date.today(), key="f_gasto")
        with col_h:
            h_g = st.time_input("Hora", datetime.datetime.now().time(), key="h_gasto")

        btn_gasto = st.form_submit_button("💳 Registrar Gasto", use_container_width=True)

        if btn_gasto:
            f_str = f"{f_g.strftime('%Y-%m-%d')} {h_g.strftime('%H:%M:%S')}"
            payload = {
                "accion": "REGISTRAR_GASTO",
                "fechaHora": f_str,
                "cuenta": cuenta_g,
                "categoria": cat_g,
                "descripcion": desc_g if desc_g else cat_g,
                "monto": monto_g
            }
            requests.post(APPS_SCRIPT_URL, json=payload, timeout=8)
            st.cache_data.clear()
            st.success("¡Gasto registrado con éxito!")
            st.rerun()

with tab_ingreso:
    with st.form("form_ingreso", clear_on_submit=True):
        col_mi, col_ctai = st.columns(2)
        with col_mi:
            monto_i = st.number_input("Monto Ingreso (S/.)", min_value=0.10, step=1.0, format="%.2f")
        with col_ctai:
            cuenta_i = st.selectbox("Cuenta de Entrada", options=CUENTAS, index=0)

        desc_i = st.text_input("Concepto de Ingreso", placeholder="Sueldo, abono, venta, etc.")

        col_fi, col_hi = st.columns(2)
        with col_fi:
            f_i = st.date_input("Fecha", datetime.date.today(), key="f_ingreso")
        with col_hi:
            h_i = st.time_input("Hora", datetime.datetime.now().time(), key="h_ingreso")

        btn_ingreso = st.form_submit_button("💰 Abonar Ingreso", use_container_width=True)

        if btn_ingreso:
            f_str_i = f"{f_i.strftime('%Y-%m-%d')} {h_i.strftime('%H:%M:%S')}"
            payload = {
                "accion": "REGISTRAR_INGRESO",
                "fechaHora": f_str_i,
                "cuenta": cuenta_i,
                "categoria": "Ingreso",
                "descripcion": desc_i if desc_i else "Abono directo",
                "monto": monto_i
            }
            requests.post(APPS_SCRIPT_URL, json=payload, timeout=8)
            st.cache_data.clear()
            st.success("¡Ingreso abonado con éxito!")
            st.rerun()

# ==========================================
# ELEMENTO 3: CONTROL DE GASTOS DIARIOS (00:00 A 24:00)
# ==========================================
col_cal, _ = st.columns([1, 1])
with col_cal:
    dia_sel = st.date_input("📅 Ver fecha del calendario:", datetime.date.today(), key="dia_calendario")

dia_sel_str = dia_sel.strftime("%Y-%m-%d")

# Sumatoria estricta 00:00 a 24:00 para la fecha seleccionada
gasto_dia_acumulado = 0.0
for m in movimientos:
    if m.get("tipo") == "Gasto":
        fh_raw = str(m.get("fechaHora", ""))[:10]
        # Soporta formatos YYYY-MM-DD o DD/MM/YYYY
        if dia_sel_str == fh_raw or dia_sel.strftime("%d/%m/%Y") == fh_raw:
            gasto_dia_acumulado += float(m.get("monto", 0))

txt_dia = "HOY HAS GASTADO" if dia_sel == datetime.date.today() else f"GASTO DEL {dia_sel.strftime('%d/%m/%Y')}"

st.markdown(f"""
<div class="metric-hoy">
    <div>
        <div style="font-size:0.75rem; font-weight:700; color:#C2410C;">{txt_dia}</div>
        <div style="font-size:1.7rem; font-weight:800; color:#7C2D12;">S/. {gasto_dia_acumulado:,.2f}</div>
        <div style="font-size:0.68rem; color:#9A3412;">00:00:00 a 23:59:59 hrs</div>
    </div>
    <div style="font-size:1.8rem;">📉</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# ELEMENTO 4: BILLETERAS, EDICIÓN Y TRANSFERENCIAS
# ==========================================
col_w_title, col_w_btn = st.columns([2, 1])
with col_w_title:
    st.markdown("**Billeteras**")
with col_w_btn:
    abrir_modal = st.button("🔄 Transferir", use_container_width=True)

b1, b2 = st.columns(2)
with b1:
    st.metric("BCP", f"S/. {saldos_actuales['BCP']:,.2f}")
    st.metric("Efectivo", f"S/. {saldos_actuales['Efectivo']:,.2f}")
with b2:
    st.metric("Yape", f"S/. {saldos_actuales['Yape']:,.2f}")
    st.metric("Wardaditos", f"S/. {saldos_actuales['Wardaditos']:,.2f}")

# MÓDULO DE TRANSFERENCIA
if abrir_modal:
    with st.form("form_transf_modal"):
        st.subheader("Mover / Transferir Saldo")
        orig = st.selectbox("Billetera Origen", CUENTAS, index=0)
        dest = st.selectbox("Billetera Destino", CUENTAS, index=1)
        m_tr = st.number_input("Monto a Mover (S/.)", min_value=0.10, step=1.0, format="%.2f")
        nota_tr = st.text_input("Nota / Concepto (opcional)")
        
        btn_ejecutar_tr = st.form_submit_button("Confirmar Transferencia", use_container_width=True)

        if btn_ejecutar_tr:
            if orig == dest:
                st.error("Origen y destino no pueden ser iguales.")
            elif m_tr > saldos_actuales[orig]:
                st.error(f"Saldo insuficiente en {orig} (Disp: S/. {saldos_actuales[orig]:,.2f})")
            else:
                payload_tr = {
                    "accion": "TRANSFERENCIA",
                    "fechaHora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cuentaOrigen": orig,
                    "cuentaDestino": dest,
                    "monto": m_tr,
                    "nota": nota_tr
                }
                requests.post(APPS_SCRIPT_URL, json=payload_tr, timeout=8)
                st.cache_data.clear()
                st.success("¡Transferencia completada!")
                st.rerun()

# MÓDULO PARA EDITAR SALDOS BASE MANUALMENTE
with st.expander("✏️ Editar Saldo Base de Billeteras"):
    with st.form("form_editar_saldos"):
        cta_edit = st.selectbox("Selecciona billetera a ajustar:", CUENTAS)
        nuevo_saldo = st.number_input("Nuevo saldo inicial base (S/.)", min_value=0.0, step=10.0, format="%.2f")
        btn_guardar_saldo = st.form_submit_button("Actualizar Saldo en Sheets")
        
        if btn_guardar_saldo:
            payload_ed = {
                "accion": "EDITAR_SALDO_BASE",
                "cuenta": cta_edit,
                "nuevoSaldo": nuevo_saldo
            }
            requests.post(APPS_SCRIPT_URL, json=payload_ed, timeout=8)
            st.cache_data.clear()
            st.success(f"Saldo base de {cta_edit} actualizado a S/. {nuevo_saldo:,.2f}")
            st.rerun()

# ==========================================
# HISTORIAL COMPLETO
# ==========================================
with st.expander("📋 Historial de Movimientos"):
    if movimientos:
        df_hist = pd.DataFrame(movimientos)
        st.dataframe(df_hist.iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.caption("No hay movimientos registrados.")
