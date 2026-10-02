import streamlit as st
from streamlit_calendar import calendar
import database as db
from datetime import datetime

# Configuración de página
st.set_page_config(page_title="Control de Reservas - Quinta La Luz y Salón Gema", layout="wide", page_icon="🏰")

# Inicializar Base de Datos
db.init_db()

st.title("🏰 Control de Reservas y Pagos")

# Tarifas Fijas Configurables
PRECIO_MESA_SILLAS = 120.0  # 1 mesa y 10 sillas para ambos locales

# Selección Horizontal del Local (remplaza las pestañas para evitar el bug de renderizado)
local_seleccionado = st.radio(
    "Selecciona el local:",
    ["🌳 Quinta La Luz", "🏛️ Salón Gema"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("---")

def render_salon_view(salon_nombre, cal_key, renta_defecto, hora_extra_precio):
    st.subheader(f"Calendario y Reservas - {salon_nombre}")
    
    # Cargar eventos del local desde la base de datos
    lista_eventos = db.obtener_eventos_por_salon(salon_nombre)
    
    # Formatear eventos para FullCalendar
    calendar_events = []
    for ev in lista_eventos:
        if ev["estado"] == "GREEN":
            color = "#28a745" # Verde (Liquidado)
            titulo = f"🟢 {ev['cliente']} - LIQUIDADO"
        else:
            color = "#dc3545" # Rojo (Pendiente)
            titulo = f"🔴 {ev['cliente']} - Debe: ${ev['saldo_pendiente']:,.2f}"
            
        calendar_events.append({
            "id": str(ev["id"]),
            "title": titulo,
            "start": ev["fecha"],
            "allDay": True,
            "backgroundColor": color,
            "borderColor": color
        })
        
    # Opciones de FullCalendar (Sin botones de vista semanal/diaria)
    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": ""
        },
        "initialView": "dayGridMonth",
        "selectable": True,
        "editable": False,
        "navLinks": True,
        "height": "auto",
    }
    
    # Renderizar el calendario
    calendar(events=calendar_events, options=calendar_options, key=cal_key)
    
    st.markdown("---")
    col1, col2 = st.columns([1, 1])
    
    # --- REGISTRO RÁPIDO DE EVENTOS ---
    with col1:
        st.markdown("### ➕ Registrar Nueva Reserva")
        with st.form(key=f"form_nuevo_{cal_key}"):
            cliente_nombre = st.text_input("Nombre del Cliente*")
            cliente_telefono = st.text_input("Teléfono de Contacto")
            
            fecha_evento = st.date_input("Fecha del Evento", value=datetime.today())
            costo_base = st.number_input("Costo Renta Base ($)*", min_value=0.0, value=float(renta_defecto), step=100.0)
            
            st.markdown("---")
            st.markdown("**Servicios Extras Iniciales**")
            cant_horas = st.number_input(f"Horas Extras (${hora_extra_precio:,.2f} c/u)", min_value=0, step=1)
            cant_mesas = st.number_input(f"Paquetes 1 Mesa / 10 Sillas (${PRECIO_MESA_SILLAS:,.2f} c/u)", min_value=0, step=1)
            
            # Extra Abierto
            extra_concepto = st.text_input("Concepto Extra Personalizado (Ej. Banquete, Mantelería)")
            extra_monto = st.number_input("Monto Extra Personalizado ($)", min_value=0.0, step=50.0)
            
            st.markdown("---")
            anticipo = st.number_input("Anticipo / Primer Pago Recibido ($)", min_value=0.0, step=100.0)
            
            submit = st.form_submit_button("💾 Guardar Reserva")
            
            if submit:
                fecha_str = fecha_evento.strftime("%Y-%m-%d")
                
                # VALIDACIÓN: Comprobar si ya existe un evento agendado para esa fecha en el salón seleccionado
                fechas_ocupadas = [ev["fecha"] for ev in lista_eventos]
                
                if not cliente_nombre or costo_base <= 0:
                    st.error("Por favor completa el nombre del cliente y el costo base.")
                elif fecha_str in fechas_ocupadas:
                    st.error(f"⛔ **¡Fecha no disponible!** Ya existe un evento agendado para **{salon_nombre}** el **{fecha_evento.strftime('%d/%m/%Y')}**.")
                else:
                    extras = []
                    if cant_horas > 0:
                        extras.append((f"{cant_horas} Hora(s) Extra", cant_horas * hora_extra_precio))
                    if cant_mesas > 0:
                        extras.append((f"{cant_mesas} Paq. 1 Mesa / 10 Sillas", cant_mesas * PRECIO_MESA_SILLAS))
                    if extra_concepto and extra_monto > 0:
                        extras.append((extra_concepto, extra_monto))
                        
                    db.crear_evento(
                        salon=salon_nombre,
                        cliente_nombre=cliente_nombre,
                        cliente_telefono=cliente_telefono,
                        fecha_evento=fecha_str,
                        costo_base=costo_base,
                        extras_lista=extras,
                        anticipo=anticipo
                    )
                    st.success(f"¡Reserva registrada con éxito para {cliente_nombre}!")
                    st.rerun()

    # --- DETALLES, REGISTRO DE ABONOS Y ELIMINACIÓN ---
    with col2:
        st.markdown("### 📋 Ver Detalle / Gestionar Evento")
        eventos_dict = {f"{ev['fecha']} - {ev['cliente']} (ID: {ev['id']})": ev['id'] for ev in lista_eventos}
        
        if eventos_dict:
            seleccion = st.selectbox(
                "Selecciona un evento de la lista para gestionar:",
                options=list(eventos_dict.keys()),
                key=f"select_{cal_key}"
            )
            
            ev_id = eventos_dict[seleccion]
            ev_info, extras_info, pagos_info = db.obtener_detalles_evento(ev_id)
            
            # Cálculos
            c_base = ev_info[5]
            tot_extras = sum([m[1] for m in extras_info])
            tot_pagos = sum([p[0] for p in pagos_info])
            g_total = c_base + tot_extras
            s_pendiente = max(0.0, g_total - tot_pagos)
            
            st.info(f"**Cliente:** {ev_info[2]} | **Teléfono:** {ev_info[3] or 'N/A'}\n\n**Fecha:** {ev_info[4]}")
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Total Evento", f"${g_total:,.2f}")
            col_b.metric("Total Abonado", f"${tot_pagos:,.2f}")
            col_c.metric("Saldo Pendiente", f"${s_pendiente:,.2f}", delta_color="inverse")
            
            with st.expander("Ver Desglose de Extras"):
                if extras_info:
                    for conc, mnt in extras_info:
                        st.write(f"- **{conc}:** ${mnt:,.2f}")
                else:
                    st.write("No hay extras agregados.")
                    
            with st.expander("Ver Historial de Abonos"):
                if pagos_info:
                    for mnt, fch, met, conc in pagos_info:
                        st.write(f"- **${mnt:,.2f}** ({met}) el {fch} - *{conc}*")
                else:
                    st.write("Sin pagos registrados.")
                    
            st.markdown("---")
            st.markdown("**Acciones Rápidas**")
            
            # Formulario para Abono
            with st.form(key=f"pago_form_{cal_key}_{ev_id}"):
                monto_pago = st.number_input("Monto a Abonar ($)", min_value=0.0, step=100.0)
                metodo_pago = st.selectbox("Método", ["Efectivo", "Transferencia"])
                concepto_pago = st.text_input("Concepto del pago", value="Abono a cuenta")
                
                btn_pago = st.form_submit_button("💵 Registrar Abono")
                if btn_pago and monto_pago > 0:
                    db.agregar_pago(ev_id, monto_pago, metodo_pago, concepto_pago)
                    st.success("¡Abono registrado correctamente!")
                    st.rerun()

            # Formulario para Extra
            with st.form(key=f"extra_form_{cal_key}_{ev_id}"):
                nuevo_extra_conc = st.text_input("Concepto del nuevo extra (ej. Banquete, Mantelería)")
                nuevo_extra_monto = st.number_input("Monto Extra ($)", min_value=0.0, step=50.0)
                
                btn_extra = st.form_submit_button("✨ Agregar Extra al Evento")
                if btn_extra and nuevo_extra_monto > 0:
                    db.agregar_extra(ev_id, nuevo_extra_conc, nuevo_extra_monto)
                    st.success("¡Extra añadido correctamente!")
                    st.rerun()

            st.markdown("---")
            # Opción de Eliminación con confirmación de doble paso
            with st.expander("⚠️ Zona de Peligro (Eliminar Evento)"):
                st.warning("Esta acción eliminará la reserva, sus extras y su historial de pagos permanentemente.")
                
                # Clave única en session_state para controlar el estado de confirmación de este evento
                confirm_key = f"confirm_del_{cal_key}_{ev_id}"
                
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                if not st.session_state[confirm_key]:
                    # Paso 1: Primer botón para solicitar eliminación
                    if st.button("🗑️ Eliminar Reserva", key=f"btn_init_del_{cal_key}_{ev_id}"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    # Paso 2: Mensaje de alerta y botones de confirmación definitiva
                    st.error("🚨 **¿Estás completamente seguro? Esto no se puede deshacer.**")
                    
                    col_si, col_no = st.columns(2)
                    with col_si:
                        if st.button("⚠️ SÍ, BORRAR DEFINITIVAMENTE", key=f"btn_yes_{cal_key}_{ev_id}", type="primary"):
                            db.eliminar_evento(ev_id)
                            st.session_state[confirm_key] = False
                            st.success("Reserva eliminada con éxito.")
                            st.rerun()
                    with col_no:
                        if st.button("❌ Cancelar", key=f"btn_no_{cal_key}_{ev_id}"):
                            st.session_state[confirm_key] = False
                            st.rerun()
# Renderizar el calendario de acuerdo al botón seleccionado
if local_seleccionado == "🌳 Quinta La Luz":
    render_salon_view(
        salon_nombre="Quinta La Luz", 
        cal_key="cal_quinta_la_luz", 
        renta_defecto=7500.0, 
        hora_extra_precio=1000.0
    )
else:
    render_salon_view(
        salon_nombre="Salón Gema", 
        cal_key="cal_salon_gema", 
        renta_defecto=9000.0, 
        hora_extra_precio=1500.0
    )
