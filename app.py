import streamlit as st
import database as db
import pandas as pd
from datetime import datetime, timedelta 

st.set_page_config(page_title="Imprenta Cloud", layout="wide", page_icon="☁️")

# --- CABECERA ---
col_titulo, col_hora = st.columns([3, 1])
with col_titulo:
    st.title("☁️ Gestión de Imprenta")
with col_hora:
    st.metric("Fecha", db.get_hora_argentina().split(" ")[0])

# --- MENÚ LATERAL---
menu = st.sidebar.radio(
    "Menú Principal", 
    ["💰 Lista de Precios", "📝 Nuevo Pedido", "💸 Registrar Gasto", "📦 Gestión de Pedidos", "📊 Caja y Movimientos"]
)

# ==========================================
# 1. LISTA DE PRECIOS
# ==========================================
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

# ==========================================
# 2. NUEVO PEDIDO
# ==========================================
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

# ==========================================
# 3. REGISTRAR GASTO (NUEVO MÓDULO)
# ==========================================
elif menu == "💸 Registrar Gasto":
    st.header("💸 Registrar Salida de Dinero")
    st.info("Ingresá acá cualquier gasto del día (Luz, Insumos, Delivery, etc).")
    
    with st.form("form_gasto"):
        col_cat, col_monto = st.columns(2)
        with col_cat:
            categoria = st.selectbox("Categoría del Gasto", [
                "Insumos (Papel/Tinta)", 
                "Mantenimiento de Máquinas", 
                "Servicios (Luz/Internet)", 
                "Logística/Envíos", 
                "Retiro de Ganancia",
                "Varios"
            ])
        with col_monto:
            monto = st.number_input("Monto gastado ($)", min_value=0.0, step=100.0)
        
        nota = st.text_area("Descripción / Detalle (Opcional)", placeholder="Ej: Compra de 5 resmas A4 Ledesma")
        
        if st.form_submit_button("🔴 Registrar Gasto"):
            if monto > 0:
                db.registrar_movimiento_caja("Egreso", categoria, monto, nota)
                st.success(f"Gasto de ${monto} registrado correctamente.")
            else:
                st.error("El monto tiene que ser mayor a 0.")

# ==========================================
# 4. GESTIÓN PEDIDOS
# ==========================================
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

# ==========================================
# 5. CAJA Y MOVIMIENTOS (MEJORADO)
# ==========================================
elif menu == "📊 Caja y Movimientos":
    st.header("📊 Reporte de Ganancias y Movimientos")

    # --- 1. PREPARACIÓN DE DATOS ---
    df = db.obtener_caja()
    
    if not df.empty:
        # Convertimos la columna de texto a formato Fecha real para poder filtrar
        df['fecha_dt'] = pd.to_datetime(df['fecha'])
        df['fecha_solo'] = df['fecha_dt'].dt.date 

        # --- 2. FILTROS DE FECHA ---
        col_filtro, col_rango = st.columns([1, 2])
        
        with col_filtro:
            opcion_tiempo = st.selectbox(
                "Seleccionar Período:", 
                ["Hoy", "Últimos 7 Días", "Este Mes", "Rango Personalizado"]
            )

        # Definimos las fechas de inicio y fin según la opción
        hoy = datetime.now().date()
        fecha_inicio = hoy
        fecha_fin = hoy

        if opcion_tiempo == "Hoy":
            fecha_inicio = hoy
            fecha_fin = hoy
        elif opcion_tiempo == "Últimos 7 Días":
            fecha_inicio = hoy - timedelta(days=7)
            fecha_fin = hoy
        elif opcion_tiempo == "Este Mes":
            fecha_inicio = hoy.replace(day=1)
            fecha_fin = hoy
        elif opcion_tiempo == "Rango Personalizado":
            with col_rango:
                rango = st.date_input("Elegí las fechas:", [hoy - timedelta(days=30), hoy])
                if len(rango) == 2:
                    fecha_inicio, fecha_fin = rango

        # --- 3. APLICAR FILTRO ---
        # Filtra el DataFrame "df" usando las fechas elegidas
        mask = (df['fecha_solo'] >= fecha_inicio) & (df['fecha_solo'] <= fecha_fin)
        df_filtrado = df.loc[mask]

        # --- 4. CÁLCULOS DEL PERÍODO ---
        if not df_filtrado.empty:
            ingresos = df_filtrado[df_filtrado['tipo'] == 'Ingreso']['monto'].sum()
            egresos = df_filtrado[df_filtrado['tipo'] == 'Egreso']['monto'].sum()
            balance = ingresos - egresos
            
            # --- MOSTRAR MÉTRICAS ARRIBA ---
            st.markdown(f"### 📅 Viendo desde: {fecha_inicio} hasta {fecha_fin}")
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Ingresos (Ventas/Señas)", f"${ingresos:,.2f}")
            kpi2.metric("Gastos (Salidas)", f"${egresos:,.2f}", delta_color="inverse")
            kpi3.metric("Balance Neto", f"${balance:,.2f}", delta=balance)
            
            st.divider()

            # --- TABLA DETALLADA ---
            st.dataframe(
                df_filtrado[["fecha", "tipo", "categoria", "nota", "monto"]],
                use_container_width=True,
                column_config={
                    "monto": st.column_config.NumberColumn("Monto", format="$ %.2f"),
                    "fecha": st.column_config.DatetimeColumn("Fecha y Hora", format="DD/MM/YYYY HH:mm")
                },
                hide_index=True
            )
            
            # --- RESUMEN FINAL ---
            st.success(f"💰 **RESULTADO FINAL DEL PERÍODO:** En estas fechas te quedaron **${balance:,.2f}** de ganancia en el bolsillo.")
            
        else:
            st.info("No hay movimientos registrados en esas fechas.")
            
    else:
        st.info("Aún no hay ningún movimiento en la caja histórica.")

    st.divider()
    
    # Formulario rápido de gasto por si te olvidaste de cargar algo
    with st.expander("Registrar Gasto Rápido (Manual)"):
        c1, c2, c3 = st.columns([2,2,1])
        monto = c1.number_input("Monto Gasto", 0.0)
        nota = c2.text_input("Detalle")
        if c3.button("Cargar Salida"):
            db.registrar_movimiento_caja("Egreso", "Varios", monto, nota)
            st.rerun()
