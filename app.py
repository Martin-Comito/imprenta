import streamlit as st
import database as db

st.set_page_config(page_title="Imprenta Cloud", layout="wide", page_icon="☁️")

col_titulo, col_hora = st.columns([3, 1])
with col_titulo:
    st.title("☁️ Gestión de Imprenta")
with col_hora:
    st.metric("Fecha", db.get_hora_argentina().split(" ")[0])

menu = st.sidebar.radio("Menú", ["💰 Lista de Precios", "📝 Nuevo Pedido", "📦 Gestión de Pedidos", "📊 Caja y Movimientos"])

# --- 1. PRECIOS ---
if menu == "💰 Lista de Precios":
    st.header("Lista de Precios")
    col1, col2 = st.columns([1, 2])
    with col1:
        with st.form("nuevo_prod"):
            nombre = st.text_input("Producto")
            cant = st.number_input("Cantidad", 1, step=10, value=1000)
            precio = st.number_input("Precio ($)", 0.0, step=100.0)
            cat = st.selectbox("Categoría", ["Impresión", "Diseño", "Insumos"])
            if st.form_submit_button("Guardar"):
                db.guardar_producto(nombre, cant, precio, cat)
                st.success("Guardado!")
                st.rerun()
    with col2:
        df = db.obtener_productos()
        if not df.empty:
            st.dataframe(df[["nombre", "cantidad", "precio", "categoria"]], use_container_width=True)
            id_borrar = st.number_input("ID a borrar", min_value=0)
            if st.button("Borrar") and id_borrar > 0:
                db.borrar_producto(id_borrar)
                st.rerun()

# --- 2. NUEVO PEDIDO ---
elif menu == "📝 Nuevo Pedido":
    st.header("Cargar Pedido")
    df_prod = db.obtener_productos()
    opciones = {f"{r['nombre']} (x{r['cantidad']})": r['precio'] for i, r in df_prod.iterrows()} if not df_prod.empty else {}
    
    with st.form("pedido"):
        cliente = st.text_input("Cliente")
        prod = st.selectbox("Producto", ["- Personalizado -"] + list(opciones.keys()))
        precio_sug = opciones.get(prod, 0.0)
        desc = st.text_area("Detalles")
        c1, c2 = st.columns(2)
        total = c1.number_input("Total ($)", value=float(precio_sug))
        seña = c2.number_input("Seña ($)")
        
        if st.form_submit_button("Confirmar"):
            if cliente:
                detalle = f"{prod} - {desc}"
                db.crear_pedido_con_seña(cliente, detalle, total, seña)
                st.success("Pedido subido a la nube ☁️")
            else:
                st.error("Falta cliente")

# --- 3. GESTIÓN PEDIDOS ---
elif menu == "📦 Gestión de Pedidos":
    st.header("Control de Trabajos")
    filtro = st.radio("Ver:", ["Todos", "Pendientes", "Entregados"], horizontal=True)
    df = db.obtener_pedidos(filtro)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.divider()
        sel_id = st.selectbox("Seleccionar ID Pedido", df['id'].tolist())
        if sel_id:
            pedido = df[df['id'] == sel_id].iloc[0]
            st.info(f"Cliente: {pedido['cliente']} | Debe: ${pedido['saldo']}")
            c1, c2 = st.columns(2)
            with c1:
                pago = st.number_input("Monto a cobrar", 0.0, float(pedido['saldo']))
                if st.button("Cobrar Saldo") and pago > 0:
                    nuevo_pagado = pedido['pagado'] + pago
                    nuevo_saldo = pedido['total'] - nuevo_pagado
                    db.actualizar_pago_pedido(sel_id, nuevo_pagado, nuevo_saldo)
                    db.registrar_movimiento_caja("Ingreso", "Saldo Final", pago, f"Cobro {pedido['cliente']}", int(sel_id))
                    st.success("Cobrado!")
                    st.rerun()
            with c2:
                nuevo_est = st.selectbox("Estado", ["Pendiente", "Terminado", "Entregado"])
                if st.button("Actualizar Estado"):
                    db.actualizar_estado_pedido(sel_id, nuevo_est)
                    st.rerun()

# --- 4. CAJA ---
elif menu == "📊 Caja y Movimientos":
    st.header("Flujo de Caja")
    periodo = st.radio("Ver:", ["Hoy", "Todo"])
    df = db.obtener_caja()
    
    if not df.empty:
        # Filtro simple en Python
        fecha_hoy = db.get_hora_argentina().split(" ")[0]
        if periodo == "Hoy":
            df = df[df['fecha'].str.contains(fecha_hoy)]
            
        ingresos = df[df['tipo'] == 'Ingreso']['monto'].sum()
        egresos = df[df['tipo'] == 'Egreso']['monto'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ingresos", f"${ingresos:,.2f}")
        c2.metric("Egresos", f"${egresos:,.2f}")
        c3.metric("Balance", f"${ingresos - egresos:,.2f}")
        
        st.dataframe(df, use_container_width=True)
    
    with st.expander("Registrar Gasto Manual"):
        monto = st.number_input("Monto Gasto", 0.0)
        nota = st.text_input("Detalle")
        if st.button("Registrar Salida"):
            db.registrar_movimiento_caja("Egreso", "Gasto General", monto, nota)
            st.rerun()