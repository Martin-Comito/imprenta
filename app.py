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
# 1. LISTA DE PRECIOS (EDITABLE)
# ==========================================
if menu == "💰 Lista de Precios":
    st.header("Gestión de Precios")
    
    # --- A. FORMULARIO PARA AGREGAR NUEVOS ---
    with st.expander("➕ Agregar Nuevo Producto", expanded=False):
        with st.form("nuevo_prod"):
            c1, c2, c3, c4 = st.columns(4)
            nombre = c1.text_input("Producto")
            cant = c2.number_input("Cantidad", 1, step=10, value=1000)
            precio = c3.number_input("Precio ($)", 0.0, step=100.0)
            cat = c4.selectbox("Categoría", ["Impresión", "Diseño", "Insumos"])
            
            if st.form_submit_button("Guardar Nuevo"):
                db.guardar_producto(nombre, cant, precio, cat)
                st.success("Agregado!")
                st.rerun()

    # --- B. TABLA EDITABLE ---
    st.divider()
    st.subheader("📝 Editar Precios Existentes")
    
    df = db.obtener_productos()
    
    if not df.empty:
        # Agrega una columna "Eliminar" falsa para que aparezca el checkbox
        df['Eliminar'] = False
        
        # Ordenamos las columnas para que quede prolijo
        df_editor = df[['id', 'Eliminar', 'nombre', 'cantidad', 'precio', 'categoria']]

        # Mostramos el editor (como un Excel)
        cambios = st.data_editor(
            df_editor,
            column_config={
                "id": st.column_config.NumberColumn(disabled=True), # El ID no se toca
                "Eliminar": st.column_config.CheckboxColumn(help="Tildá para borrar este producto", default=False),
                "precio": st.column_config.NumberColumn(format="$ %.2f"),
                "cantidad": st.column_config.NumberColumn(format="%d u."),
            },
            hide_index=True,
            use_container_width=True,
            key="editor_precios" 
        )

        # Botón para guardar TODOS los cambios (Ediciones y Borrados)
        if st.button("💾 Guardar Cambios en la Tabla"):
            hay_cambios = False
            
            # 1. Detectar Borrados 
            borrados = cambios[cambios['Eliminar'] == True]
            for index, row in borrados.iterrows():
                db.borrar_producto(row['id'])
                hay_cambios = True
            
            # 2. Detectar Ediciones (Actualizamos todo lo que NO se borró)
            # (Esto asegura que si cambiaste el precio, se guarde)
            activos = cambios[cambios['Eliminar'] == False]
            for index, row in activos.iterrows():
                # Compara valores para no actualizar al cuete 
                db.actualizar_producto(row['id'], row['nombre'], row['cantidad'], row['precio'], row['categoria'])
                hay_cambios = True

            if hay_cambios:
                st.success("¡Base de datos actualizada!")
                st.rerun()
            else:
                st.info("No detecté cambios para guardar.")
                
    else:
        st.info("Todavía no hay productos cargados.")

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
# 4. GESTIÓN PEDIDOS (HÍBRIDO: EDICIÓN + ACCIONES)
# ==========================================
elif menu == "📦 Gestión de Pedidos":
    st.header("📋 Control de Trabajos")
    
    # --- 1. FILTROS ---
    col_filtro, col_metricas = st.columns([1, 3])
    with col_filtro:
        filtro = st.radio("Ver:", ["Todos", "Pendientes", "Entregados"], horizontal=True)
    
    df = db.obtener_pedidos(filtro)
    
    if not df.empty:
        # ========================================================
        # SECCIÓN A: TABLA EDITABLE (PARA CORRECCIONES)
        # ========================================================
        with st.expander("📝 Modo Edición (Corregir errores de tipeo o precios)", expanded=False):
            st.caption("Usá esto solo para corregir datos mal cargados. NO registra movimientos en caja.")
            df['Eliminar'] = False
            df_editor = df[['id', 'Eliminar', 'fecha_creacion', 'cliente', 'descripcion', 'total', 'pagado', 'saldo', 'estado']]

            cambios = st.data_editor(
                df_editor,
                column_config={
                    "id": st.column_config.NumberColumn(disabled=True, width="small"),
                    "Eliminar": st.column_config.CheckboxColumn(default=False),
                    "fecha_creacion": st.column_config.TextColumn("Fecha", disabled=True),
                    "total": st.column_config.NumberColumn(format="$ %.2f"),
                    "pagado": st.column_config.NumberColumn(format="$ %.2f"),
                    "saldo": st.column_config.NumberColumn(format="$ %.2f", disabled=True),
                    "estado": st.column_config.SelectboxColumn("Estado", options=["Pendiente", "En Producción", "Terminado", "Entregado"])
                },
                hide_index=True,
                use_container_width=True,
                key="editor_pedidos_hibrido"
            )

            if st.button("💾 Guardar Correcciones de la Tabla"):
                # 1. Borrar
                filas_borrar = cambios[cambios['Eliminar'] == True]
                for index, row in filas_borrar.iterrows():
                    db.borrar_pedido(row['id'])
                
                # 2. Actualizar (Sin tocar la caja, solo corrección de datos)
                filas_activas = cambios[cambios['Eliminar'] == False]
                for index, row in filas_activas.iterrows():
                    # Usamos la función de update simple
                    nuevo_saldo = row['total'] - row['pagado']
                    # Llamada directa a Supabase para actualizar (o usá tu función de db si la tenés)
                    db.actualizar_pedido_desde_tabla(row['id'], row['cliente'], row['descripcion'], row['total'], row['pagado'], row['estado'])
                
                st.success("¡Tabla corregida!")
                st.rerun()

        # ========================================================
        # SECCIÓN B: PANEL DE ACCIONES (COBRAR Y ENTREGAR)
        # ========================================================
        st.divider()
        st.subheader("🚀 Acciones Rápidas (Mueve Caja)")

        # Selección del pedido
        lista_pedidos = df.apply(lambda x: f"#{x['id']} - {x['cliente']} ({x['estado']})", axis=1).tolist()
        seleccion_texto = st.selectbox("Seleccionar Pedido para Gestionar:", lista_pedidos)
        
        if seleccion_texto:
            # Extraer el ID del texto seleccionado 
            id_sel = int(seleccion_texto.split(" - ")[0].replace("#", ""))
            pedido = df[df['id'] == id_sel].iloc[0]

            col_info, col_acciones = st.columns([1, 2])
            
            with col_info:
                st.info(f"""
                **Cliente:** {pedido['cliente']}  
                **Total:** ${pedido['total']:,.2f}  
                **Pagado:** ${pedido['pagado']:,.2f}  
                **DEBE:** :red[${pedido['saldo']:,.2f}]
                """)

            with col_acciones:
                c1, c2 = st.tabs(["💸 COBRAR SALDO", "📦 ENTREGAR"])
                
                # --- PESTAÑA 1: COBRAR ---
                with c1:
                    if pedido['saldo'] > 0:
                        monto_a_cobrar = st.number_input("Monto que paga ahora ($):", min_value=0.0, max_value=float(pedido['saldo']), step=100.0)
                        if st.button("💰 Registrar Pago y Mover Caja"):
                            nuevo_pagado = pedido['pagado'] + monto_a_cobrar
                            nuevo_saldo = pedido['total'] - nuevo_pagado
                            
                            # 1. Actualizar Pedido
                            db.actualizar_pago_pedido(id_sel, nuevo_pagado, nuevo_saldo)
                            
                            # 2. Registrar en Caja
                            db.registrar_movimiento_caja("Ingreso", "Saldo Final", monto_a_cobrar, f"Cobro pedido #{id_sel} - {pedido['cliente']}", id_sel)
                            
                            st.success("¡Pago registrado y caja actualizada!")
                            st.rerun()
                    else:
                        st.success("✅ Este pedido ya está pagado completo.")

                # --- PESTAÑA 2: ENTREGAR ---
                with c2:
                    st.write(f"Estado actual: **{pedido['estado']}**")
                    nuevo_estado = st.selectbox("Cambiar estado a:", ["En Producción", "Terminado", "Entregado"], key="sel_estado_rapido")
                    
                    if st.button("🔄 Actualizar Estado"):
                        db.actualizar_estado_pedido(id_sel, nuevo_estado)
                        st.success(f"Estado cambiado a {nuevo_estado}")
                        st.rerun()

    else:
        st.info("No hay pedidos con este filtro.")
# ==========================================
# 5. CAJA Y MOVIMIENTOS (EDITABLE)
# ==========================================
elif menu == "📊 Caja y Movimientos":
    st.header("📊 Reporte de Ganancias y Movimientos")

    # --- 1. PREPARACIÓN DE DATOS ---
    df = db.obtener_caja()
    
    if not df.empty:
        # Convertimos fechas
        df['fecha_dt'] = pd.to_datetime(df['fecha'])
        df['fecha_solo'] = df['fecha_dt'].dt.date

        # --- 2. FILTROS ---
        col_filtro, col_rango = st.columns([1, 2])
        with col_filtro:
            opcion_tiempo = st.selectbox(
                "Seleccionar Período:", 
                ["Hoy", "Últimos 7 Días", "Este Mes", "Rango Personalizado"]
            )

        # Lógica de fechas (Igual que antes)
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
        mask = (df['fecha_solo'] >= fecha_inicio) & (df['fecha_solo'] <= fecha_fin)
        df_filtrado = df.loc[mask].copy() 

        # --- 4. MOSTRAR MÉTRICAS ---
        if not df_filtrado.empty:
            ingresos = df_filtrado[df_filtrado['tipo'] == 'Ingreso']['monto'].sum()
            egresos = df_filtrado[df_filtrado['tipo'] == 'Egreso']['monto'].sum()
            balance = ingresos - egresos
            
            st.markdown(f"### 📅 Viendo desde: {fecha_inicio} hasta {fecha_fin}")
            kpi1, kpi2, kpi3 = st.columns(3)
            kpi1.metric("Ingresos", f"${ingresos:,.2f}")
            kpi2.metric("Gastos", f"${egresos:,.2f}", delta_color="inverse")
            kpi3.metric("Balance", f"${balance:,.2f}", delta=balance)
            
            st.divider()

            # --- 5. TABLA EDITABLE (ACÁ ESTÁ LA MAGIA) ---
            st.subheader("📝 Editar Movimientos")
            st.warning("⚠️ OJO: Si borrás una Seña de acá, recordá corregir el saldo del Pedido manualmente en la otra pestaña.")
            
            df_filtrado['Eliminar'] = False
            
            # Columnas a mostrar
            df_editor = df_filtrado[['id', 'Eliminar', 'fecha', 'tipo', 'categoria', 'nota', 'monto']]

            cambios = st.data_editor(
                df_editor,
                column_config={
                    "id": st.column_config.NumberColumn(disabled=True, width="small"),
                    "Eliminar": st.column_config.CheckboxColumn(help="Tildá para borrar este movimiento", default=False),
                    "fecha": st.column_config.TextColumn("Fecha (YYYY-MM-DD)", disabled=False),
                    "tipo": st.column_config.SelectboxColumn("Tipo", options=["Ingreso", "Egreso"], required=True),
                    "categoria": st.column_config.SelectboxColumn("Categoría", options=["Seña", "Saldo Final", "Insumos", "Servicios", "Varios"], required=True),
                    "monto": st.column_config.NumberColumn("Monto ($)", format="$ %.2f"),
                    "nota": st.column_config.TextColumn("Detalle")
                },
                hide_index=True,
                use_container_width=True,
                key="editor_caja"
            )

            # --- BOTÓN GUARDAR ---
            if st.button("💾 Guardar Correcciones en Caja"):
                # 1. Borrar
                filas_borrar = cambios[cambios['Eliminar'] == True]
                for index, row in filas_borrar.iterrows():
                    db.borrar_movimiento_caja(row['id'])
                
                # 2. Actualizar
                filas_activas = cambios[cambios['Eliminar'] == False]
                for index, row in filas_activas.iterrows():
                    db.actualizar_movimiento_caja(
                        row['id'], 
                        row['fecha'], 
                        row['tipo'], 
                        row['categoria'], 
                        row['monto'], 
                        row['nota']
                    )
                
                st.success("¡Caja actualizada correctamente!")
                st.rerun()

            st.success(f"💰 **GANANCIA DEL PERÍODO:** ${balance:,.2f}")
            
        else:
            st.info("No hay movimientos en estas fechas.")
    else:
        st.info("La caja está vacía.")

    st.divider()
    
    # Formulario rápido
    with st.expander("Registrar Gasto Rápido (Manual)"):
        c1, c2, c3 = st.columns([2,2,1])
        monto = c1.number_input("Monto Gasto", 0.0)
        nota = c2.text_input("Detalle")
        if c3.button("Cargar Salida"):
            db.registrar_movimiento_caja("Egreso", "Varios", monto, nota)
            st.rerun()
