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
            return res.get("movimientos", []), res.get("saldosBase", {c: 0.0 for c in CUENTAS})
    except Exception as e:
        st.error(f"Error de conexión con Sheets: {e}")
    return [], {c: 0.0 for c in CUENTAS}

movimientos, saldos_base = cargar_datos_sheets()

# Sobrescribir en sesión si hubo un ajuste manual reciente
if "saldos_override" not in st.session_state:
    st.session_state["saldos_override"] = {}

# 2. CÁLCULO DE SALDOS
saldos_actuales = dict(saldos_base)

for c in CUENTAS:
    if c in st.session_state["saldos_override"]:
        saldos_actuales[c] = st.session_state["saldos_override"][c]
    else:
        # Si no fue ajustado manualmente en esta sesión, calcular con los movimientos
        delta = 0.0
        for m in movimientos:
            cta = str(m.get("cuenta", "")).strip()
            if cta == c:
                monto = float(m.get("monto", 0))
                tipo = str(m.get("tipo", "")).strip()
                if tipo in ["Gasto", "Transferencia Salida"]:
                    delta -= monto
                elif tipo in ["Ingreso", "Transferencia Entrada"]:
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
# ELEMENTO 2: FORMULARIO PRINCIPAL
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
            # Limpiar override para que recalcule con el nuevo gasto
            st.session_state["saldos_override"].pop(cuenta_g, None)
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
            st.session_state["saldos_override"].pop(cuenta_i, None)
            with st.spinner("Abonando en Sheets..."):
                requests.post(APPS_SCRIPT_URL, json=payload, timeout=8)
                time.sleep(1)
            st.rerun()

# ==========================================
# ELEMENTO 3: GASTO ACUMULADO HOY HASTA EL MOMENTO
# ==========================================
def parsear_fecha_flexible(val_str):
    s = str(val_str).strip()
    if not s or s.upper() in ["NONE", "NAN"]:
        return None
    s = s.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(s[:len(fmt)], fmt).date()
        except:
            pass
    partes = s[:10].replace("-", "/").split("/")
    if len(partes) == 3:
        try:
            if len(partes[0]) == 4:
                return datetime.date(int(partes[0]), int(partes[1]), int(partes[2]))
            elif len(partes[2]) == 4:
                return datetime.date(int(partes[2]), int(partes[1]), int(partes[0]))
        except:
            pass
    return None

hoy = datetime.date.today()
ahora_hora = datetime.datetime.now().strftime("%H:%M")

gasto_hoy_acumulado = 0.0
for m in movimientos:
    if str(m.get("tipo", "")).strip().lower() == "gasto":
        f_mov = parsear_fecha_flexible(m.get("fechaHora"))
        if f_mov == hoy:
            gasto_hoy_acumulado += float(m.get("monto", 0))

st.markdown(f"""
<div class="metric-hoy">
    <div>
        <div style="font-size:0.75rem; font-weight:700; color:#C2410C;">HOY HAS GASTADO</div>
        <div style="font-size:1.75rem; font-weight:800; color:#7C2D12;">S/. {gasto_hoy_acumulado:,.2f}</div>
        <div style="font-size:0.68rem; color:#9A3412;">Gasto acumulado hasta el momento ({ahora_hora} hrs)</div>
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
                st.session_state["saldos_override"].pop(orig, None)
                st.session_state["saldos_override"].pop(dest, None)
                with st.spinner("Procesando transferencia..."):
                    requests.post(APPS_SCRIPT_URL, json=payload_tr, timeout=8)
                    time.sleep(1)
                st.rerun()

# MÓDULO PARA EDITAR SALDO
with st.expander("✏️ Editar Saldo Base de Billeteras"):
    with st.form("form_editar_saldos"):
        cta_edit = st.selectbox("Selecciona billetera a ajustar:", CUENTAS)
        nuevo_saldo = st.number_input("Nuevo saldo actual (S/.)", min_value=0.0, step=10.0, format="%.2f")
        btn_guardar_saldo = st.form_submit_button("Actualizar Saldo en Sheets")
        
        if btn_guardar_saldo:
            # 1. Guardar inmediatamente en la sesión de la app
            st.session_state["saldos_override"][cta_edit] = float(nuevo_saldo)
            
            # 2. Enviar a Google Sheets
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
