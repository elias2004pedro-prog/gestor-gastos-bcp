import streamlit as st
import requests
import pandas as pd
import datetime
import time

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

# Zona horaria exacta de Perú (UTC-5)
TZ_PERU = datetime.timezone(datetime.timedelta(hours=-5))

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

# 1. CARGA DIRECTA DESDE GOOGLE SHEETS
def cargar_datos_sheets():
    try:
        url_fresca = f"{APPS_SCRIPT_URL}?t={int(time.time() * 1000)}"
        r = requests.get(url_fresca, timeout=8)
        if r.status_code == 200:
            res = r.json()
            return (
                res.get("movimientos", []), 
                res.get("saldosBase", {c: 0.0 for c in CUENTAS}),
                float(res.get("gastoHoy", 0.0))
            )
    except Exception as e:
        st.error(f"Error de conexión con Sheets: {e}")
    return [], {c: 0.0 for c in CUENTAS}, 0.0

movimientos, saldos_base, gasto_hoy_servidor = cargar_datos_sheets()

if "saldos_override" not in st.session_state:
    st.session_state["saldos_override"] = {}

# 2. CÁLCULO DE SALDOS EN VIVO
saldos_actuales = {c: 0.0 for c in CUENTAS}

for c in CUENTAS:
    if c in st.session_state["saldos_override"]:
        saldos_actuales[c] = st.session_state["saldos_override"][c]
    else:
        delta = 0.0
        for m in movimientos:
            cta = str(m.get("cuenta", "")).strip()
            if cta == c:
                monto = float(m.get("monto", 0))
                tipo = str(m.get("tipo", "")).strip().lower()
                if "gasto" in tipo or "salida" in tipo:
                    delta -= monto
                elif "ingreso" in tipo or "entrada" in tipo:
                    delta += monto
        saldos_actuales[c] = saldos_base.get(c, 0.0) + delta

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
# ELEMENTO 2: FORMULARIO PRINCIPAL (SIN SELECTORES DE FECHA/HORA)
# ==========================================
tab_gasto, tab_ingreso = st.tabs(["➕ REGISTRAR GASTO", "💵 REGISTRAR INGRESO"])

ahora_peru = datetime.datetime.now(TZ_PERU)

with tab_gasto:
    with st.form("form_gasto", clear_on_submit=True):
        col_m, col_cta = st.columns(2)
        with col_m:
            monto_g = st.number_input("Monto Gasto (S/.)", min_value=0.10, step=1.0, format="%.2f")
        with col_cta:
            cuenta_g = st.selectbox("Cuenta de Salida", options=CUENTAS, index=1)

        desc_g = st.text_input("Descripción", placeholder="¿En qué se gastó?")
        cat_g = st.selectbox("Categoría", options=CATEGORIAS, index=6)

        btn_gasto = st.form_submit_button("💳 Registrar Gasto", use_container_width=True)

        if btn_gasto:
            # Captura automática de fecha y hora local de Perú para Google Sheets
            f_str = datetime.datetime.now(TZ_PERU).strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                "accion": "REGISTRAR_GASTO",
                "fechaHora": f_str,
                "cuenta": cuenta_g,
                "categoria": cat_g,
                "descripcion": desc_g if desc_g else cat_g,
                "monto": monto_g
            }
            saldos_actuales[cuenta_g] -= monto_g
            st.session_state["saldos_override"][cuenta_g] = saldos_actuales[cuenta_g]
            
            with st.spinner("Guardando en Sheets..."):
                requests.post(APPS_SCRIPT_URL, json=payload, timeout=8)
                time.sleep(1)
            st.rerun()

with tab_ingreso:
    with st.form("form_ingreso", clear_on_submit=True):
        col_mi, col_ctai = st.columns(2)
        with col_mi:
            monto_i = st.number_input("Monto Ingreso (S/.)", min_value=0.10, step=1.0, format="%.2f")
        with col_ctai:
            cuenta_i = st.selectbox("Cuenta de Entrada", options=CUENTAS, index=0)

        desc_i = st.text_input("Concepto de Ingreso", placeholder="Sueldo, abono, etc.")

        btn_ingreso = st.form_submit_button("💰 Abonar Ingreso", use_container_width=True)

        if btn_ingreso:
            # Captura automática de fecha y hora local de Perú para Google Sheets
            f_str_i = datetime.datetime.now(TZ_PERU).strftime("%Y-%m-%d %H:%M:%S")
            payload = {
                "accion": "REGISTRAR_INGRESO",
                "fechaHora": f_str_i,
                "cuenta": cuenta_i,
                "categoria": "Ingreso",
                "descripcion": desc_i if desc_i else "Abono directo",
                "monto": monto_i
            }
            saldos_actuales[cuenta_i] += monto_i
            st.session_state["saldos_override"][cuenta_i] = saldos_actuales[cuenta_i]
            
            with st.spinner("Abonando en Sheets..."):
                requests.post(APPS_SCRIPT_URL, json=payload, timeout=8)
                time.sleep(1)
            st.rerun()

# ==========================================
# ELEMENTO 3: SUMATORIA REAL DE HOY (00:00 A 24:00)
# ==========================================
hora_actual_str = ahora_peru.strftime("%H:%M")

st.markdown(f"""
<div class="metric-hoy">
    <div>
        <div style="font-size:0.75rem; font-weight:700; color:#C2410C;">HOY HAS GASTADO</div>
        <div style="font-size:1.85rem; font-weight:800; color:#7C2D12;">S/. {gasto_hoy_servidor:,.2f}</div>
        <div style="font-size:0.68rem; color:#9A3412;">Gasto acumulado hasta las {hora_actual_str} hrs (00:00 a 24:00)</div>
    </div>
    <div style="font-size:1.8rem;">📉</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# ELEMENTO 4: BILLETERAS COMPACTAS
# ==========================================
st.markdown("**Billeteras**")

b1, b2 = st.columns(2)
with b1:
    st.metric("BCP", f"S/. {saldos_actuales['BCP']:,.2f}")
    st.metric("Efectivo", f"S/. {saldos_actuales['Efectivo']:,.2f}")
with b2:
    st.metric("Yape", f"S/. {saldos_actuales['Yape']:,.2f}")
    st.metric("Wardaditos", f"S/. {saldos_actuales['Wardaditos']:,.2f}")

# MÓDULO INTERACTIVO DE TRANSFERENCIA
with st.expander("🔄 Mover / Transferir Saldo entre Billeteras"):
    with st.form("form_transf_modal", clear_on_submit=True):
        col_orig, col_dest = st.columns(2)
        with col_orig:
            orig = st.selectbox("Origen (Sale)", CUENTAS, index=0)
        with col_dest:
            dest = st.selectbox("Destino (Entra)", CUENTAS, index=1)
            
        m_tr = st.number_input("Monto a Mover (S/.)", min_value=0.10, step=1.0, format="%.2f")
        nota_tr = st.text_input("Nota / Concepto (opcional)", placeholder="Pase para gastos, compras, etc.")
        
        btn_ejecutar_tr = st.form_submit_button("Confirmar Transferencia", use_container_width=True)

        if btn_ejecutar_tr:
            if orig == dest:
                st.error("Origen y destino no pueden ser iguales.")
            elif m_tr > saldos_actuales[orig]:
                st.error(f"Saldo insuficiente en {orig} (Disponible: S/. {saldos_actuales[orig]:,.2f})")
            else:
                saldos_actuales[orig] -= m_tr
                saldos_actuales[dest] += m_tr
                st.session_state["saldos_override"][orig] = saldos_actuales[orig]
                st.session_state["saldos_override"][dest] = saldos_actuales[dest]

                payload_tr = {
                    "accion": "TRANSFERENCIA",
                    "fechaHora": datetime.datetime.now(TZ_PERU).strftime("%Y-%m-%d %H:%M:%S"),
                    "cuentaOrigen": orig,
                    "cuentaDestino": dest,
                    "monto": m_tr,
                    "nota": nota_tr
                }
                with st.spinner("Procesando transferencia..."):
                    requests.post(APPS_SCRIPT_URL, json=payload_tr, timeout=8)
                    time.sleep(1)
                st.success(f"¡Se movieron S/. {m_tr:,.2f} de {orig} a {dest}!")
                st.rerun()

# MÓDULO PARA EDITAR SALDOS BASE MANUALMENTE
with st.expander("✏️ Editar Saldo Base de Billeteras"):
    with st.form("form_editar_saldos", clear_on_submit=True):
        cta_edit = st.selectbox("Selecciona billetera a ajustar:", CUENTAS)
        nuevo_saldo = st.number_input("Nuevo saldo actual (S/.)", min_value=0.0, step=10.0, format="%.2f")
        btn_guardar_saldo = st.form_submit_button("Actualizar Saldo en Sheets")
        
        if btn_guardar_saldo:
            st.session_state["saldos_override"][cta_edit] = float(nuevo_saldo)
            payload_ed = {
                "accion": "EDITAR_SALDO_BASE",
                "cuenta": cta_edit,
                "nuevoSaldo": nuevo_saldo
            }
            with st.spinner("Actualizando saldo en Sheets..."):
                requests.post(APPS_SCRIPT_URL, json=payload_ed, timeout=8)
                time.sleep(1)
            st.success(f"¡{cta_edit} actualizado a S/. {nuevo_saldo:,.2f}!")
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
