import pandas as pd
import streamlit as st
import plotly.express as px
import locale
import requests
import io
from datetime import datetime

def main():
    # Establecer el locale en español si está disponible
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except:
        pass

    # Recuperar la clave desde el estado de sesión
    clave_api = st.session_state.get("clave_redcoes", None)

    if not clave_api:
        st.warning("🔒 Acceso restringido. No se detectó una clave válida.")
        st.stop()

    # Funciones para cargar los datos desde cada endpoint
    @st.cache_data(ttl=0 if st.session_state.get("refrescar") else None)
    def cargar_pedidos():
        url = f"https://reddecontadores.com/wp-json/redcoes/v1/pedidos?key={clave_api}"
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data)
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        df['total'] = pd.to_numeric(df['total'], errors='coerce')
        df['fecha_pedido'] = pd.to_datetime(df['fecha_pedido'], errors='coerce')
        df['año'] = df['fecha_pedido'].dt.year
        df['mes_numero'] = df['fecha_pedido'].dt.month
        df['mes'] = df['fecha_pedido'].dt.strftime('%B')
        return df

    @st.cache_data(ttl=0 if st.session_state.get("refrescar") else None)
    def cargar_productos():
        url = f"https://reddecontadores.com/wp-json/redcoes/v1/productos?key={clave_api}"
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data)
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        df['precio_regular'] = pd.to_numeric(df['precio_regular'], errors='coerce')
        return df

    @st.cache_data(ttl=0 if st.session_state.get("refrescar") else None)
    def cargar_miembros():
        url = f"https://reddecontadores.com/wp-json/redcoes/v1/miembros?key={clave_api}"
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data)
        df['subscription_starts'] = pd.to_datetime(df['subscription_starts'], errors='coerce')
        df['año'] = df['subscription_starts'].dt.year
        df['mes_numero'] = df['subscription_starts'].dt.month
        df['mes'] = df['subscription_starts'].dt.strftime('%B')
        df['membership_level'] = df['membership_level'].map({'2': 'miembro', '4': 'no miembro'}).fillna(df['membership_level'])
        return df

    # Crear pestañas
    tab1, tab2, tab3 = st.tabs(["📊 Pedidos", "📦 Productos", "👥 Miembros"])

    with tab1:
        df = cargar_pedidos()
        st.header("📊 Dashboard de Pedidos REDCOES")

        with st.expander("📋 Filtros de pedidos", expanded=True):
            años = df['año'].dropna().sort_values().unique()
            meses = df[['mes', 'mes_numero']].dropna().drop_duplicates().sort_values(by='mes_numero')

            años_seleccionados = st.multiselect("Año(s):", options=años[::-1], default=[max(años)])
            mes_inicio = st.selectbox("Desde el mes:", options=meses['mes'], index=0)
            mes_fin = st.selectbox("Hasta el mes:", options=meses['mes'], index=len(meses) - 1)
            cursos = st.multiselect("Curso:", options=df['producto'].unique(), default=None)
            modalidades = st.multiselect("Modalidad:", options=df['modalidad'].dropna().unique(), default=None)
            afiliaciones = st.multiselect("Tipo de afiliación:", options=df['tipo_de_afiliacion'].dropna().unique(), default=None)
            estados = st.multiselect("Estado:", options=df['estado'].unique(), default=['completed'])

        filtro = df.copy()
        if años_seleccionados:
            filtro = filtro[filtro['año'].isin(años_seleccionados)]
        mes_num_inicio = meses[meses['mes'] == mes_inicio]['mes_numero'].values[0]
        mes_num_fin = meses[meses['mes'] == mes_fin]['mes_numero'].values[0]
        if mes_num_inicio <= mes_num_fin:
            filtro = filtro[(filtro['mes_numero'] >= mes_num_inicio) & (filtro['mes_numero'] <= mes_num_fin)]
        if cursos:
            filtro = filtro[filtro['producto'].isin(cursos)]
        if modalidades:
            filtro = filtro[filtro['modalidad'].isin(modalidades)]
        if afiliaciones:
            filtro = filtro[filtro['tipo_de_afiliacion'].isin(afiliaciones)]
        if estados:
            filtro = filtro[filtro['estado'].isin(estados)]

        col1, col2, col3 = st.columns(3)
        col1.metric("Pedidos", len(filtro))
        col2.metric("Total recaudado", f"$ {filtro['total'].sum():,.2f}")
        col3.metric("Cursos únicos", filtro['producto'].nunique())

        st.subheader("🧑‍🎓 Inscritos por curso")
        cursos_plot = filtro['producto'].value_counts().reset_index()
        cursos_plot.columns = ['Curso', 'Cantidad']
        st.plotly_chart(px.bar(cursos_plot, x='Curso', y='Cantidad', title="Inscritos por curso"))

        st.subheader("📅 Pedidos por fecha")
        fecha_plot = filtro.groupby('fecha_pedido').size().reset_index(name='Cantidad')
        st.plotly_chart(px.line(fecha_plot, x='fecha_pedido', y='Cantidad', title="Pedidos por fecha"))

        st.subheader("🧮 Inscritos por modalidad y afiliación")
        col4, col5 = st.columns(2)
        modalidad_plot = filtro['modalidad'].value_counts().reset_index()
        modalidad_plot.columns = ['Modalidad', 'Cantidad']
        col4.plotly_chart(px.pie(modalidad_plot, names='Modalidad', values='Cantidad', title="Por modalidad"))

        afiliacion_plot = filtro['tipo_de_afiliacion'].value_counts().reset_index()
        afiliacion_plot.columns = ['Afiliación', 'Cantidad']
        col5.plotly_chart(px.pie(afiliacion_plot, names='Afiliación', values='Cantidad', title="Por tipo de afiliación"))

        st.subheader("📋 Detalle de pedidos")
        st.dataframe(filtro.sort_values(by='fecha_pedido', ascending=False))

        if not filtro.empty:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                filtro.to_excel(writer, index=False, sheet_name='Pedidos')
            output.seek(0)
            st.download_button(
                label="📥 Descargar en Excel",
                data=output,
                file_name="pedidos_redcoes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with tab2:
        df = cargar_productos()
        st.header("📦 Dashboard de Productos REDCOES")

        with st.expander("📋 Filtros de productos", expanded=True):
            estados = st.multiselect("Estado:", options=df['estado'].unique(), default=['publish'])
            modalidades = st.multiselect("Modalidad:", options=df['modalidad'].dropna().unique(), default=None)
            afiliaciones = st.multiselect("Tipo de afiliación:", options=df['tipo_afiliacion'].dropna().unique(), default=None)

            productos_unicos = df.groupby('nombre')['id'].min().reset_index().sort_values(by='id', ascending=False)
            opciones_nombre = productos_unicos['nombre'].tolist()

            activar_filtro_rango = st.checkbox("Filtrar por rango de productos", value=False)
            mostrar_unicos = st.checkbox("Mostrar solo productos únicos", value=False)

            if activar_filtro_rango:
                producto_inicio = st.selectbox("Desde producto:", options=opciones_nombre, index=len(opciones_nombre)-1)
                producto_fin = st.selectbox("Hasta producto:", options=opciones_nombre, index=0)
            else:
                producto_inicio = producto_fin = None

        filtro = df.copy()
        if estados:
            filtro = filtro[filtro['estado'].isin(estados)]

        if activar_filtro_rango and producto_inicio and producto_fin:
            id_inicio = df[df['nombre'] == producto_inicio]['id'].min()
            id_fin = df[df['nombre'] == producto_fin]['id'].max()
            id_min, id_max = min(id_inicio, id_fin), max(id_inicio, id_fin)
            filtro = filtro[(filtro['id'] >= id_min) & (filtro['id'] <= id_max)]

        if modalidades:
            filtro = filtro[filtro['modalidad'].isin(modalidades)]
        if afiliaciones:
            filtro = filtro[filtro['tipo_afiliacion'].isin(afiliaciones)]

        col1, col2 = st.columns(2)
        col1.metric("Variaciones filtradas", len(filtro))
        col2.metric("Productos únicos", filtro['nombre'].nunique())

        if mostrar_unicos:
            filtro = filtro.sort_values(by='id', ascending=False).drop_duplicates(subset='nombre')

        st.dataframe(filtro.sort_values(by='id', ascending=False))

        if not filtro.empty:
            st.subheader("📈 Precio regular por variación")
            st.plotly_chart(px.bar(filtro, x='nombre', y='precio_regular', color='modalidad', barmode='group', title="Precios por variación"))

            conteo_estados = filtro['estado'].value_counts().reset_index()
            conteo_estados.columns = ['Estado', 'Cantidad']
            st.plotly_chart(px.pie(conteo_estados, names='Estado', values='Cantidad', title="Distribución por estado"))

    with tab3:
        df = cargar_miembros()
        st.header("👥 Dashboard de Participantes REDCOES")

        with st.expander("📋 Filtros de miembros", expanded=True):
            años = df['año'].dropna().sort_values().unique()
            meses = df[['mes', 'mes_numero']].dropna().drop_duplicates().sort_values(by='mes_numero')

            años_seleccionados = st.multiselect("Año(s):", options=años[::-1], default=list(años[::-1]))
            mes_inicio = st.selectbox("Desde el mes:", options=meses['mes'], index=0)
            mes_fin = st.selectbox("Hasta el mes:", options=meses['mes'], index=len(meses) - 1)
            niveles = st.multiselect("Nivel de membresía:", options=df['membership_level'].dropna().unique(), default=['miembro'])
            estados = st.multiselect("Estado de cuenta:", options=df['account_state'].dropna().unique(), default=None)

        filtro = df.copy()
        if años_seleccionados:
            filtro = filtro[filtro['año'].isin(años_seleccionados)]
        mes_num_inicio = meses[meses['mes'] == mes_inicio]['mes_numero'].values[0]
        mes_num_fin = meses[meses['mes'] == mes_fin]['mes_numero'].values[0]
        if mes_num_inicio <= mes_num_fin:
            filtro = filtro[(filtro['mes_numero'] >= mes_num_inicio) & (filtro['mes_numero'] <= mes_num_fin)]
        if niveles:
            filtro = filtro[filtro['membership_level'].isin(niveles)]
        if estados:
            filtro = filtro[filtro['account_state'].isin(estados)]

        col1, col2 = st.columns(2)
        col1.metric("Miembros filtrados", len(filtro))
        col2.metric("Correos únicos", filtro['email'].nunique())

        if not filtro.empty:
            conteo_niveles = filtro['membership_level'].value_counts().reset_index()
            conteo_niveles.columns = ['Nivel', 'Cantidad']
            st.plotly_chart(px.pie(conteo_niveles, names='Nivel', values='Cantidad', title="Distribución por nivel de membresía"))

            conteo_estado = filtro['account_state'].value_counts().reset_index()
            conteo_estado.columns = ['Estado', 'Cantidad']
            st.plotly_chart(px.pie(conteo_estado, names='Estado', values='Cantidad', title="Estado de la cuenta"))

        st.subheader("📋 Detalle de miembros")
        st.dataframe(filtro.sort_values(by='subscription_starts', ascending=False))

if __name__ == "__main__":
    main()
    st.session_state["refrescar"] = False
