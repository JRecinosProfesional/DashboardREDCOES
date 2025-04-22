# REDCOES - Dashboard Combinado (Moodle + WordPress)

import streamlit as st
import moodle_dashboard
import wordpress_dashboard
import requests
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configuración inicial
st.set_page_config(page_title="Dashboard General REDCOES", layout="wide")

# Título
st.title("🔐 Acceso al Dashboard General REDCOES")

# Campo de clave sin sugerencias del navegador
clave_ingresada = st.text_input("Ingresa la clave de acceso:", type="password", autocomplete="off")

# Usar endpoint más liviano
url_verificacion = f"https://reddecontadores.com/wp-json/redcoes/v1/verificar?key={clave_ingresada}"

# Validar clave usando el endpoint de verificación
if clave_ingresada:
    try:
        respuesta = requests.get(url_verificacion, timeout=5)
        if respuesta.status_code == 200 and respuesta.json().get("status") == "ok":
            st.success("🔓 Acceso concedido")

            # Guardar clave para dashboards
            st.session_state["clave_redcoes"] = clave_ingresada

            # Inicializar la clave 'refrescar' si no existe
            if "refrescar" not in st.session_state:
                st.session_state["refrescar"] = False

            # Mostrar el botón de refrescar
            if st.button("🔄 Refrescar datos"):
                st.session_state["refrescar"] = True
                st.rerun()  # Recargar la app para que el valor se propague a los dashboards

            # Selector de dashboard
            opcion = st.sidebar.radio("Selecciona el módulo:", ["Moodle", "WordPress"])
            if opcion == "Moodle":
                moodle_dashboard.main()
            elif opcion == "WordPress":
                wordpress_dashboard.main()

        else:
            st.error("❌ Clave incorrecta o acceso denegado.")
    except Exception as e:
        st.error(f"⚠️ Error al validar la clave: {e}")
else:
    st.info("🔐 Por favor, ingresa tu clave para continuar.")
