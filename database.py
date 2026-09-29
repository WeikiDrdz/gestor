import sqlite3
from datetime import datetime

DB_NAME = "eventos.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tabla de Eventos / Reservas
    c.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salon TEXT NOT NULL,
            cliente_nombre TEXT NOT NULL,
            cliente_telefono TEXT,
            fecha_evento DATE NOT NULL,
            costo_base REAL NOT NULL
        )
    ''')
    
    # Tabla de Servicios Extras
    c.execute('''
        CREATE TABLE IF NOT EXISTS extras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            concepto TEXT NOT NULL,
            monto REAL NOT NULL,
            FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
        )
    ''')
    
    # Tabla de Pagos y Abonos
    c.execute('''
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_id INTEGER NOT NULL,
            monto REAL NOT NULL,
            fecha_pago DATETIME DEFAULT CURRENT_TIMESTAMP,
            metodo TEXT,
            concepto TEXT,
            FOREIGN KEY (evento_id) REFERENCES eventos(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

def crear_evento(salon, cliente_nombre, cliente_telefono, fecha_evento, costo_base, extras_lista, anticipo):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Insertar el evento
    c.execute('''
        INSERT INTO eventos (salon, cliente_nombre, cliente_telefono, fecha_evento, costo_base)
        VALUES (?, ?, ?, ?, ?)
    ''', (salon, cliente_nombre, cliente_telefono, fecha_evento, costo_base))
    evento_id = c.lastrowid
    
    # Insertar los extras
    for concepto, monto in extras_lista:
        c.execute('''
            INSERT INTO extras (evento_id, concepto, monto)
            VALUES (?, ?, ?)
        ''', (evento_id, concepto, monto))
        
    # Insertar el anticipo inicial si es mayor a 0
    if anticipo > 0:
        c.execute('''
            INSERT INTO pagos (evento_id, monto, metodo, concepto)
            VALUES (?, ?, 'Efectivo/Transferencia', 'Anticipo inicial')
        ''', (evento_id, anticipo))
        
    conn.commit()
    conn.close()
    return evento_id

def obtener_eventos_por_salon(salon):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('''
        SELECT id, cliente_nombre, cliente_telefono, fecha_evento, costo_base
        FROM eventos WHERE salon = ?
    ''', (salon,))
    eventos = c.fetchall()
    
    resultado = []
    for ev in eventos:
        ev_id, nombre, tel, fecha, costo_base = ev
        
        # Suma de extras
        c.execute('SELECT COALESCE(SUM(monto), 0) FROM extras WHERE evento_id = ?', (ev_id,))
        total_extras = c.fetchone()[0]
        
        # Suma de pagos
        c.execute('SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE evento_id = ?', (ev_id,))
        total_pagado = c.fetchone()[0]
        
        gran_total = costo_base + total_extras
        saldo_pendiente = gran_total - total_pagado
        
        resultado.append({
            "id": ev_id,
            "cliente": nombre,
            "telefono": tel,
            "fecha": fecha,
            "costo_base": costo_base,
            "total_extras": total_extras,
            "gran_total": gran_total,
            "total_pagado": total_pagado,
            "saldo_pendiente": max(0.0, saldo_pendiente),
            "estado": "GREEN" if saldo_pendiente <= 0 else "RED"
        })
        
    conn.close()
    return resultado

def agregar_pago(evento_id, monto, metodo, concepto):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO pagos (evento_id, monto, metodo, concepto)
        VALUES (?, ?, ?, ?)
    ''', (evento_id, monto, metodo, concepto))
    conn.commit()
    conn.close()

def agregar_extra(evento_id, concepto, monto):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        INSERT INTO extras (evento_id, concepto, monto)
        VALUES (?, ?, ?)
    ''', (evento_id, concepto, monto))
    conn.commit()
    conn.close()

def obtener_detalles_evento(evento_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('SELECT id, salon, cliente_nombre, cliente_telefono, fecha_evento, costo_base FROM eventos WHERE id = ?', (evento_id,))
    ev = c.fetchone()
    
    c.execute('SELECT concepto, monto FROM extras WHERE evento_id = ?', (evento_id,))
    extras = c.fetchall()
    
    c.execute('SELECT monto, fecha_pago, metodo, concepto FROM pagos WHERE evento_id = ?', (evento_id,))
    pagos = c.fetchall()
    
    conn.close()
    return ev, extras, pagos

def eliminar_evento(evento_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Al eliminar el evento, las tablas de pagos y extras vinculadas se borran automáticamente (ON DELETE CASCADE)
    c.execute('DELETE FROM eventos WHERE id = ?', (evento_id,))
    conn.commit()
    conn.close()