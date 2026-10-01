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

# Sustituye esta URL luego por la de tu Google Apps Script si deseas conexión en la nube
APPS_SCRIPT_URL = "https://script.google.com/macros/s/TU_SCRIPT_ID_AQUI/exec"

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

if "movimientos_locales" not in st.session_state:
    st.session_state["movimientos_locales"] = [
        {"fechaHora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "tipo": "Gasto", "cuenta": "Yape", "categoria": "Comidas", "descripcion": "Menú", "monto": 18.0}
    ]

@st.cache_data(ttl=10)
def obtener_movimientos():
    if "TU_SCRIPT_ID" in APPS_SCRIPT_URL:
        return st.session_state["movimientos_locales"]
    try:
        r = requests.get(APPS_SCRIPT_URL, timeout=8)
        if r.status_code == 200:
            return r.json().get("movimientos", [])
    except:
        pass
    return st.session_state["movimientos_locales"]

movimientos = obtener_movimientos()

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

st.markdown(f"""
<div class="total-banner">
    <p class="total-title">Total General Disponible</p>
    <div class="total-amount">S/. {total_general:,.2f}</div>
</div>
""", unsafe_allow_html=True)

with st.expander("➕ REGISTRAR GASTO", expanded=True):
    with st.form("form_gasto", clear_on_submit=True):
        col_m, col_cta = st.columns(2)
        with col_m:
            monto = st.number_input("Monto (S/.)", min_value=0.10, step=1.0, format="%.2f")
        with col_cta:
            cuenta = st.selectbox("Cuenta de Salida", options=CUENTAS, index=1)

        descripcion = st.text_input("Descripción / Concepto", placeholder="¿En qué se gastó?")
        categoria = st.selectbox("Categoría", options=CATEGORIAS, index=6)

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
            if "TU_SCRIPT_ID" not in APPS_SCRIPT_URL:
                try:
                    requests.post(APPS_SCRIPT_URL, json=payload, timeout=8)
                except Exception as e:
                    st.error(f"Error al conectar con Sheets: {e}")
            else:
                st.session_state["movimientos_locales"].append(payload)
            st.cache_data.clear()
            st.success("¡Gasto registrado correctamente!")
            st.rerun()

col_sel_dia, _ = st.columns([1, 1])
with col_sel_dia:
    dia_consulta = st.date_input("📅 Ver fecha:", datetime.date.today(), key="filtro_dia")

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
                st.error(f"Saldo insuficiente en {c_orig}")
            else:
                payload_tr = {
                    "accion": "TRANSFERENCIA",
                    "fechaHora": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "cuentaOrigen": c_orig,
                    "cuentaDestino": c_dest,
                    "monto": m_transf,
                    "nota": nota_transf
                }
                if "TU_SCRIPT_ID" not in APPS_SCRIPT_URL:
                    try:
                        requests.post(APPS_SCRIPT_URL, json=payload_tr, timeout=8)
                    except Exception as e:
                        st.error(f"Error al registrar en Sheets: {e}")
                else:
                    st.session_state["movimientos_locales"].append({"tipo": "Transferencia Salida", "cuenta": c_orig, "monto": m_transf})
                    st.session_state["movimientos_locales"].append({"tipo": "Transferencia Entrada", "cuenta": c_dest, "monto": m_transf})
                st.cache_data.clear()
                st.success("¡Transferencia realizada!")
                st.rerun()

with st.expander("📋 Ver Últimos Movimientos"):
    if movimientos:
        df_movs = pd.DataFrame(movimientos)
        st.dataframe(df_movs.tail(15).iloc[::-1], use_container_width=True, hide_index=True)
    else:
        st.caption("No hay movimientos registrados.")
