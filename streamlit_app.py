import streamlit as st
import requests
import pandas as pd
import datetime
import time

st.set_page_config(
    page_title="Gestor BCP & Billeteras",
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

# Zona horaria oficial de Perú (UTC-5)
TZ_PERU = datetime.timezone(datetime.timedelta(hours=-5))

# ==========================================
# ESTILOS MÓVIL VERTICAL CON IDENTIFICACIÓN ROJO/VERDE
# ==========================================
st.markdown("""
<style>
    /* Ajuste para pantallas de smartphone vertical */
    .block-container {
        padding-top: 0.6rem !important;
        padding-bottom: 3.5rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        max-width: 480px !important;
        margin: auto !important;
    }
    
    /* Banner Total General */
    .total-banner {
        background: linear-gradient(135deg, #091E3A 0%, #1A365D 100%);
        border-radius: 16px;
        padding: 16px 14px;
        text-align: center;
        color: white;
        margin-bottom: 12px;
        box-shadow: 0 4px 14px rgba(10, 37, 64, 0.2);
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
        font-size: 2.2rem;
        font-weight: 800;
        margin-top: 2px;
        letter-spacing: -0.5px;
    }
    
    /* Métrica Hoy Has Gastado - Alerta Roja */
    .card-gasto-hoy {
        background: #FEF2F2;
        border: 1.5px solid #FCA5A5;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 8px rgba(239, 68, 68, 0.08);
    }
    .card-gasto-hoy .tag {
        font-size: 0.72rem;
        font-weight: 800;
        color: #DC2626;
        letter-spacing: 0.5px;
    }
    .card-gasto-hoy .monto {
        font-size: 1.85rem;
        font-weight: 900;
        color: #B91C1C;
        margin-top: 2px;
    }
    .card-gasto-hoy .sub {
        font-size: 0.68rem;
        color: #991B1B;
        font-weight: 500;
    }

    /* Tarjetas de Billeteras Compactas */
    .wallet-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 10px 12px;
        margin-bottom: 8px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.03);
    }
    .wallet-name {
        font-size: 0.72rem;
        font-weight: 700;
        color: #64748B;
        text-transform: uppercase;
    }
    .wallet-val {
        font-size: 1.25rem;
        font-weight: 800;
        color: #0F172A;
        margin-top: 2px;
    }

    /* Pestañas estilizadas */
    button[data-baseweb="tab"] {
        font-weight: 700 !important;
        font-size: 0.88rem !important;
        border-radius: 8px 8px 0 0 !important;
    }
    
    /* Botón Registrar Gasto (Rojo) */
    div[data-testid="stFormSubmitButton"] button {
        border-radius: 10px !important;
        font-weight: 700 !important;
        height: 44px !important;
    }
    .btn-red button {
        background-color: #DC2626 !important;
        color: white !important;
        border: none !important;
    }
    .btn-green button {
        background-color: #16A34A !important;
        color: white !important;
        border: none !important;
    }

    /* Tarjetas del Historial */
    .hist-item {
        background: white;
        border-radius: 10px;
        padding: 10px 12px;
        margin-bottom: 6px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-left: 5px solid #CBD5E1;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .hist-item.gasto {
        border-left-color: #EF4444;
    }
    .hist-item.ingreso {
        border-left-color: #22C55E;
    }
    .hist-item.transferencia {
        border-left-color: #3B82F6;
    }
    .hist-desc {
        font-size: 0.85rem;
        font-weight: 600;
        color: #1E293B;
    }
    .hist-sub {
        font-size: 0.70rem;
        color: #64748B;
    }
    .hist-monto-gasto {
        font-size: 0.95rem;
        font-weight: 800;
        color: #DC2626;
    }
    .hist-monto-ingreso {
        font-size: 0.95rem;
        font-weight: 800;
        color: #16A34A;
    }
    .hist-monto-tr {
        font-size: 0.95rem;
        font-weight: 800;
        color: #2563EB;
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
# TOTAL GENERAL
# ==========================================
st.markdown(f"""
<div class="total-banner">
    <p class="total-title">Total General Disponible</p>
    <div class="total-amount">S/. {total_general:,.2f}</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# REGISTRO VERTICAL: GASTO (ROJO) / INGRESO (VERDE)
# ==========================================
tab_gasto, tab_ingreso = st.tabs(["🔴 REGISTRAR GASTO", "🟢 REGISTRAR INGRESO"])

ahora_peru = datetime.datetime.now(TZ_PERU)

with tab_gasto:
    with st.form("form_gasto", clear_on_submit=True):
        col_m, col_cta = st.columns(2)
        with col_m:
            monto_g = st.number_input("Monto (S/.)", min_value=0.10, step=1.0, format="%.2f", key="m_gasto")
        with col_cta:
            cuenta_g = st.selectbox("Sale de:", options=CUENTAS, index=1, key="c_gasto")

        desc_g = st.text_input("Descripción", placeholder="¿En qué gastaste?", key="d_gasto")
        cat_g = st.selectbox("Categoría", options=CATEGORIAS, index=6, key="cat_gasto")

        st.markdown('<div class="btn-red">', unsafe_allow_html=True)
        btn_gasto = st.form_submit_button("💸 Confirmar Gasto", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if btn_gasto:
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
            
            with st.spinner("Guardando..."):
                requests.post(APPS_SCRIPT_URL, json=payload, timeout=8)
                time.sleep(1)
            st.rerun()

with tab_ingreso:
    with st.form("form_ingreso", clear_on_submit=True):
        col_mi, col_ctai = st.columns(2)
        with col_mi:
            monto_i = st.number_input("Monto (S/.)", min_value=0.10, step=1.0, format="%.2f", key="m_ingreso")
        with col_ctai:
            cuenta_i = st.selectbox("Entra a:", options=CUENTAS, index=0, key="c_ingreso")

        desc_i = st.text_input("Concepto", placeholder="Sueldo, cobranza, abono...", key="d_ingreso")

        st.markdown('<div class="btn-green">', unsafe_allow_html=True)
        btn_ingreso = st.form_submit_button("💰 Abonar Ingreso", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        if btn_ingreso:
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
            
            with st.spinner("Abonando..."):
                requests.post(APPS_SCRIPT_URL, json=payload, timeout=8)
                time.sleep(1)
            st.rerun()

# ==========================================
# GASTO ACUMULADO HOY (ROJO)
# ==========================================
hora_actual_str = ahora_peru.strftime("%H:%M")

st.markdown(f"""
<div class="card-gasto-hoy">
    <div>
        <div class="tag">HOY HAS GASTADO</div>
        <div class="monto">S/. {gasto_hoy_servidor:,.2f}</div>
        <div class="sub">Acumulado al momento ({hora_actual_str} hrs)</div>
    </div>
    <div style="font-size:2rem;">📉</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# BILLETERAS COMPACTAS (2x2 VERTICAL)
# ==========================================
st.markdown("<p style='font-size:0.85rem; font-weight:700; color:#334155; margin-bottom:6px;'>TUS BILLETERAS</p>", unsafe_allow_html=True)

w1, w2 = st.columns(2)
with w1:
    st.markdown(f"""
    <div class="wallet-card">
        <div class="wallet-name">BCP</div>
        <div class="wallet-val">S/. {saldos_actuales['BCP']:,.2f}</div>
    </div>
    <div class="wallet-card">
        <div class="wallet-name">Efectivo</div>
        <div class="wallet-val">S/. {saldos_actuales['Efectivo']:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)
with w2:
    st.markdown(f"""
    <div class="wallet-card">
        <div class="wallet-name">Yape</div>
        <div class="wallet-val">S/. {saldos_actuales['Yape']:,.2f}</div>
    </div>
    <div class="wallet-card">
        <div class="wallet-name">Wardaditos</div>
        <div class="wallet-val">S/. {saldos_actuales['Wardaditos']:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# TRANSFERENCIA Y EDICIÓN
# ==========================================
with st.expander("🔄 Transferir Saldo entre Cuentas"):
    with st.form("form_transf_modal", clear_on_submit=True):
        col_orig, col_dest = st.columns(2)
        with col_orig:
            orig = st.selectbox("Origen (Sale)", CUENTAS, index=0)
        with col_dest:
            dest = st.selectbox("Destino (Entra)", CUENTAS, index=1)
            
        m_tr = st.number_input("Monto (S/.)", min_value=0.10, step=1.0, format="%.2f")
        nota_tr = st.text_input("Nota / Motivo", placeholder="Opcional")
        
        btn_ejecutar_tr = st.form_submit_button("Mover Dinero", use_container_width=True)

        if btn_ejecutar_tr:
            if orig == dest:
                st.error("Origen y destino no pueden ser iguales.")
            elif m_tr > saldos_actuales[orig]:
                st.error(f"Saldo insuficiente en {orig} (Disp: S/. {saldos_actuales[orig]:,.2f})")
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
                with st.spinner("Transfiriendo..."):
                    requests.post(APPS_SCRIPT_URL, json=payload_tr, timeout=8)
                    time.sleep(1)
                st.success(f"¡Movidos S/. {m_tr:,.2f} de {orig} a {dest}!")
                st.rerun()

with st.expander("✏️️ Ajustar Saldo Base"):
    with st.form("form_editar_saldos", clear_on_submit=True):
        cta_edit = st.selectbox("Billetera a calibrar:", CUENTAS)
        nuevo_saldo = st.number_input("Monto Real Actual (S/.)", min_value=0.0, step=10.0, format="%.2f")
        btn_guardar_saldo = st.form_submit_button("Fijar Saldo en Sheets", use_container_width=True)
        
        if btn_guardar_saldo:
            st.session_state["saldos_override"][cta_edit] = float(nuevo_saldo)
            payload_ed = {
                "accion": "EDITAR_SALDO_BASE",
                "cuenta": cta_edit,
                "nuevoSaldo": nuevo_saldo
            }
            with st.spinner("Actualizando en Sheets..."):
                requests.post(APPS_SCRIPT_URL, json=payload_ed, timeout=8)
                time.sleep(1)
            st.success(f"¡{cta_edit} fijado en S/. {nuevo_saldo:,.2f}!")
            st.rerun()

# ==========================================
# HISTORIAL EN TARJETAS VERTICALES CON COLORES
# ==========================================
with st.expander("📋 Historial de Movimientos Recientes"):
    if movimientos:
        # Tomar los últimos 15 movimientos ordenados del más reciente al más antiguo
        ultimos_movs = list(reversed(movimientos))[:15]
        
        for m in ultimos_movs:
            tipo = str(m.get("tipo", "")).strip()
            cuenta = str(m.get("cuenta", "")).strip()
            categoria = str(m.get("categoria", "")).strip()
            desc = str(m.get("descripcion", "")).strip()
            monto = float(m.get("monto", 0))

            if "Gasto" in tipo:
                clase_css = "gasto"
                signo = "-"
                clase_monto = "hist-monto-gasto"
                icono = "🔴"
            elif "Ingreso" in tipo:
                clase_css = "ingreso"
                signo = "+"
                clase_monto = "hist-monto-ingreso"
                icono = "🟢"
            else:
                clase_css = "transferencia"
                signo = "⇄"
                clase_monto = "hist-monto-tr"
                icono = "🔵"

            st.markdown(f"""
            <div class="hist-item {clase_css}">
                <div>
                    <div class="hist-desc">{icono} {desc}</div>
                    <div class="hist-sub">{cuenta} • {categoria}</div>
                </div>
                <div class="{clase_monto}">{signo} S/. {monto:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.caption("No hay movimientos registrados.")
