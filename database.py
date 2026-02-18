import os
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import pytz

# --- TUS CREDENCIALES ---
URL = "https://itklmazfrabrdgcvddfe.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml0a2xtYXpmcmFicmRnY3ZkZGZlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgxNjk3OTcsImV4cCI6MjA4Mzc0NTc5N30.Cgg2JwuWItnt_JbqtnXNxOs5mAtWTrxsvEhoRkLNk_g"

# Iniciamos la conexión a la nube
supabase: Client = create_client(URL, KEY)

ZONA_HORARIA = pytz.timezone('America/Argentina/Buenos_Aires')

def get_hora_argentina():
    return datetime.now(ZONA_HORARIA).strftime("%Y-%m-%d %H:%M:%S")

# --- FUNCIONES DE PRODUCTOS ---
def obtener_productos():
    try:
        response = supabase.table('productos').select("*").order('nombre').execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        return pd.DataFrame()

def guardar_producto(nombre, cantidad, precio, categoria):
    datos = {"nombre": nombre, "cantidad": cantidad, "precio": precio, "categoria": categoria}
    supabase.table('productos').insert(datos).execute()

def borrar_producto(id_producto):
    supabase.table('productos').delete().eq('id', id_producto).execute()

# --- FUNCIONES DE PEDIDOS ---
def obtener_pedidos(estado_filtro=None):
    query = supabase.table('pedidos').select("*").order('id', desc=True)
    if estado_filtro == "Pendientes":
        query = query.neq('estado', 'Entregado')
    elif estado_filtro == "Entregados":
        query = query.eq('estado', 'Entregado')
    response = query.execute()
    return pd.DataFrame(response.data)

def crear_pedido_con_seña(cliente, descripcion, total, seña):
    fecha_hoy = get_hora_argentina()
    saldo = total - seña
    datos_pedido = {
        "cliente": cliente,
        "descripcion": descripcion,
        "fecha_creacion": fecha_hoy,
        "total": total,
        "pagado": seña,
        "saldo": saldo,
        "estado": "Pendiente"
    }
    # Insertar pedido y obtener respuesta para sacar el ID
    res = supabase.table('pedidos').insert(datos_pedido).execute()
    
    if seña > 0 and res.data:
        id_pedido = res.data[0]['id']
        registrar_movimiento_caja("Ingreso", "Seña", seña, f"Seña de {cliente}", id_pedido)

def actualizar_pago_pedido(id_pedido, nuevo_pagado, nuevo_saldo):
    supabase.table('pedidos').update({"pagado": nuevo_pagado, "saldo": nuevo_saldo}).eq('id', id_pedido).execute()

def actualizar_estado_pedido(id_pedido, nuevo_estado):
    supabase.table('pedidos').update({"estado": nuevo_estado}).eq('id', id_pedido).execute()

# --- FUNCIONES DE CAJA ---
def obtener_caja():
    response = supabase.table('caja').select("*").order('id', desc=True).execute()
    return pd.DataFrame(response.data)

def registrar_movimiento_caja(tipo, categoria, monto, nota, pedido_id=None):
    fecha_hoy = get_hora_argentina()
    datos = {
        "fecha": fecha_hoy, 
        "tipo": tipo, 
        "categoria": categoria, 
        "monto": monto, 
        "nota": nota, 
        "pedido_id": pedido_id
    }
    supabase.table('caja').insert(datos).execute()