import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

def main():
    # CONFIGURACIÓN INICIAL
    MOODLE_URL = "https://redcoes.edu.sv/aulavirtual/webservice/rest/server.php"
    TOKEN = "54315bf201d534f9989aab54f144ad52"
    HEADERS = {"Content-Type": "application/x-www-form-urlencoded"}

    # FUNCIONES DE API

    def obtener_cursos():
        return requests.post(MOODLE_URL, data={
            "wstoken": TOKEN, "wsfunction": "core_course_get_courses",
            "moodlewsrestformat": "json"
        }, headers=HEADERS).json()

    def obtener_participantes(course_id):
        return requests.post(MOODLE_URL, data={
            "wstoken": TOKEN, "wsfunction": "core_enrol_get_enrolled_users",
            "courseid": course_id, "moodlewsrestformat": "json"
        }, headers=HEADERS).json()

    def obtener_usuarios():
        return requests.post(MOODLE_URL, data={
            "wstoken": TOKEN, "wsfunction": "core_user_get_users",
            "criteria[0][key]": "", "criteria[0][value]": "",
            "moodlewsrestformat": "json"
        }, headers=HEADERS).json()

    def matricular_usuario(course_id, user_ids, role_id=5):
        enrolments = [{"roleid": role_id, "userid": uid, "courseid": course_id} for uid in user_ids]
        data = {"wstoken": TOKEN, "wsfunction": "enrol_manual_enrol_users", "moodlewsrestformat": "json"}
        for i, e in enumerate(enrolments):
            for k, v in e.items():
                data[f"enrolments[{i}][{k}]"] = v
        return requests.post(MOODLE_URL, data=data, headers=HEADERS).json()

    def crear_curso(nombre, corto_nombre, categoria_id):
        return requests.post(MOODLE_URL, data={
            "wstoken": TOKEN, "wsfunction": "core_course_create_courses",
            "courses[0][fullname]": nombre,
            "courses[0][shortname]": corto_nombre,
            "courses[0][categoryid]": categoria_id,
            "moodlewsrestformat": "json"
        }, headers=HEADERS).json()

    def importar_contenido_curso(source_course_id, target_course_id):
        return requests.post(MOODLE_URL, data={
            "wstoken": TOKEN, "wsfunction": "core_course_import_course",
            "importfrom": source_course_id,
            "importto": target_course_id,
            "moodlewsrestformat": "json"
        }, headers=HEADERS).json()

    # UTILIDADES

    def extraer_campo(usr, shortname):
        for campo in usr.get("customfields", []):
            if campo.get("shortname") == shortname:
                return campo.get("value")
        return None

    def limpiar_html(texto):
        if texto:
            return BeautifulSoup(texto, "html.parser").get_text(strip=True)
        return None

    # DASHBOARD
    st.title("🎓 Dashboard de Moodle")

    # CARGA DE DATOS
    if "cursos" not in st.session_state or st.session_state.get("refrescar"):
        st.session_state["cursos"] = obtener_cursos()

    if "usuarios" not in st.session_state or st.session_state.get("refrescar"):
        st.session_state["usuarios"] = obtener_usuarios()

    # Asignar a variables locales
    cursos = st.session_state["cursos"]
    usuarios = st.session_state["usuarios"]

    if not isinstance(cursos, list) or not cursos:
        st.error("❌ No se pudieron cargar los cursos desde Moodle.")
        st.stop()

    # DataFrame de cursos
    cursos_df = pd.DataFrame(cursos)
    cursos_df["Inicio"] = pd.to_datetime(cursos_df["startdate"], unit="s", errors="coerce")
    cursos_df["Cierre"] = pd.to_datetime(cursos_df["enddate"], unit="s", errors="coerce")
    cursos_df = cursos_df.dropna(subset=["Inicio"])
    cursos_df["Año"] = cursos_df["Inicio"].dt.year
    cursos_df["Mes"] = cursos_df["Inicio"].dt.month
    meses_orden = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre']
    cursos_df["MesNombre"] = cursos_df["Inicio"].dt.month.map(lambda m: meses_orden[m - 1])

    # DataFrame de usuarios
    usuarios_df = pd.DataFrame([{
        "ID": u.get("id"),
        "Nombre": u.get("fullname"),
        "Correo": u.get("email"),
        "Ciudad": u.get("city"),
        "País": u.get("country"),
        "Nombres acreditación": extraer_campo(u, "nombrescvpcpa"),
        "Apellidos acreditación": extraer_campo(u, "apellidoscvpcpa"),
        "Tipo acreditación": extraer_campo(u, "tipoinscripcion"),
        "Número acreditación": limpiar_html(extraer_campo(u, "numero"))
    } for u in usuarios.get("users", [])])

    # TABS
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📆 Cursos en Ejecución", 
        "🟡 Cursos por Iniciar",
        "📁 Cursos Finalizados (últimos 25)",
        "📚 Participantes de cursos", 
        "📊 Estadísticas Globales", 
        "👥 Usuarios (Global)"
    ])

    # TAB 1: Cursos en ejecución
    with tab1:
        st.header("📆 Cursos en Ejecución")
        ahora = datetime.now().timestamp()
        en_ejecucion = cursos_df[(cursos_df["startdate"] <= ahora) & (cursos_df["enddate"] > ahora)]

        if not en_ejecucion.empty:
            cursos_activos = []
            for _, curso in en_ejecucion.iterrows():
                participantes = obtener_participantes(curso["id"])
                cursos_activos.append({
                    "ID": curso["id"],
                    "Nombre del Curso": curso["fullname"],
                    "Fecha de Inicio": datetime.fromtimestamp(curso["startdate"]).strftime("%d/%m/%Y"),
                    "Fecha de Finalización": datetime.fromtimestamp(curso["enddate"]).strftime("%d/%m/%Y"),
                    "Cantidad de Participantes": len(participantes)
                })

            df_ejecucion = pd.DataFrame(cursos_activos).sort_values(by="ID", ascending=False)
            st.dataframe(df_ejecucion, use_container_width=True)

        else:
            st.info("No hay cursos en ejecución actualmente.")

    # TAB 2: Cursos por iniciar
    with tab2:
        st.header("🟡 Cursos por Iniciar")
        ahora = datetime.now().timestamp()
        por_iniciar = cursos_df[cursos_df["startdate"] > ahora]

        if not por_iniciar.empty:
            cursos_futuros = []
            for _, curso in por_iniciar.iterrows():
                participantes = obtener_participantes(curso["id"])
                cursos_futuros.append({
                    "ID": curso["id"],
                    "Nombre del Curso": curso["fullname"],
                    "Fecha de Inicio": datetime.fromtimestamp(curso["startdate"]).strftime("%d/%m/%Y"),
                    "Fecha de Finalización": datetime.fromtimestamp(curso["enddate"]).strftime("%d/%m/%Y"),
                    "Cantidad de Participantes": len(participantes)
                })
            st.dataframe(pd.DataFrame(cursos_futuros).sort_values(by="ID", ascending=False), use_container_width=True)
        else:
            st.info("No hay cursos próximos a iniciar.")

    # TAB 3: Cursos Finalizados (últimos 25)
    with tab3:
        st.header("📁 Cursos Finalizados (últimos 25)")
        ahora = datetime.now().timestamp()
        finalizados = cursos_df[cursos_df["enddate"] < ahora].sort_values(by="id", ascending=False).head(25)

        if not finalizados.empty:
            cursos_finalizados = []
            for _, curso in finalizados.iterrows():
                participantes = obtener_participantes(curso["id"])
                cursos_finalizados.append({
                    "ID": curso["id"],
                    "Nombre del Curso": curso["fullname"],
                    "Fecha de Inicio": datetime.fromtimestamp(curso["startdate"]).strftime("%d/%m/%Y"),
                    "Fecha de Finalización": datetime.fromtimestamp(curso["enddate"]).strftime("%d/%m/%Y"),
                    "Cantidad de Participantes": len(participantes)
                })

            df_finalizados = pd.DataFrame(cursos_finalizados)
            st.dataframe(df_finalizados, use_container_width=True)
        else:
            st.info("No hay cursos finalizados.")

    # TAB 4: Participantes de cursos
    with tab4:
        st.header("📚 Lista de Cursos")

        cursos_ordenados = cursos_df.sort_values(by="id", ascending=False)
        curso_seleccionado = st.selectbox("Selecciona un curso", cursos_ordenados["fullname"])
        curso_id = cursos_ordenados[cursos_ordenados["fullname"] == curso_seleccionado]["id"].values[0]
        st.write(f"ID del curso seleccionado: {curso_id}")

        st.subheader("👨‍🏫 Participantes del Curso")
        participantes = obtener_participantes(curso_id)
        datos_participantes = [{
            "ID": p.get("id"),
            "Nombre": p.get("fullname"),
            "Correo": p.get("email"),
            "Nombres acreditación": extraer_campo(p, "nombrescvpcpa"),
            "Apellidos acreditación": extraer_campo(p, "apellidoscvpcpa"),
            "Tipo acreditación": extraer_campo(p, "tipoinscripcion"),
            "Número acreditación": limpiar_html(extraer_campo(p, "numero"))
        } for p in participantes]

        if datos_participantes:
            df_participantes = pd.DataFrame(datos_participantes)
            st.dataframe(df_participantes, use_container_width=True)
        else:
            st.info("Este curso no tiene participantes inscritos aún.")

    # TAB 5: Estadísticas globales
    with tab5:
        st.header("📊 Estadísticas Globales")

        # Orden real de los meses (nombres)
        meses_orden = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        # Selectores
        anios = sorted(cursos_df["Año"].dropna().unique(), reverse=True)
        anio_sel = st.selectbox("Año", anios)
        mes_desde = st.selectbox("Mes desde", meses_orden, index=0)
        mes_hasta = st.selectbox("Mes hasta", meses_orden, index=11)

        idx_inicio = meses_orden.index(mes_desde) + 1
        idx_fin = meses_orden.index(mes_hasta) + 1

        # Filtro de cursos
        df_filtrado = cursos_df[
            (cursos_df["Año"] == anio_sel) & 
            (cursos_df["Mes"].between(idx_inicio, idx_fin))
        ].copy()

        if not df_filtrado.empty:
            # Obtener cantidad de participantes por curso
            df_filtrado["participantes"] = df_filtrado["id"].apply(lambda cid: len(obtener_participantes(cid)))

            # Agrupar por número de mes
            resumen_cursos = df_filtrado.groupby("Mes", observed=True).size().reindex(range(1,13), fill_value=0)
            resumen_part = df_filtrado.groupby("Mes", observed=True)["participantes"].sum().reindex(range(1,13), fill_value=0)

            st.subheader("📅 Cantidad de cursos por mes")
            st.bar_chart(resumen_cursos)

            st.subheader("👥 Participantes por mes")
            st.bar_chart(resumen_part)
        else:
            st.warning("No hay cursos en el periodo seleccionado.")

    # TAB 6: Usuarios
    with tab6:
        st.header("👥 Usuarios creados en Moodle")
        st.dataframe(usuarios_df, use_container_width=True)

if __name__ == "__main__":
    main()
    st.session_state["refrescar"] = False
