#!/usr/bin/env python3
"""
FitChallenge - Gestor de Base de Datos PostgreSQL (Render MSP) & SQLite
Permite explorar, auditar, ejecutar consultas SQL y gestionar la base de datos
persistente de Render Managed PostgreSQL o el almacenamiento local.
"""

import sys
import os
import re
import json
import csv
import io
import time
from datetime import datetime, date
from decimal import Decimal

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add current dir to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import models

def load_env_file():
    """Carga variables desde archivo .env si existe sin requerir dependencias externas."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip("'").strip('"')
                        if k and k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass

load_env_file()

def json_serializable(val):
    """Convierte tipos de fecha, decimales y bytes a tipos serializables en JSON."""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, bytes):
        return val.decode("utf-8", errors="replace")
    return val

def mask_database_url(url):
    """Oculta la contraseña en la cadena de conexión por seguridad."""
    if not url:
        return "None"
    return re.sub(r':([^@]+)@', ':******@', url)

def parse_url_details(url):
    """Extrae componentes legibles de una URL de conexión de Postgres."""
    if not url:
        return {}
    # Formato: postgresql://user:pass@host:port/dbname
    pattern = r'postgres(?:ql)?://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/(.+)'
    m = re.match(pattern, url.split('?')[0])
    if m:
        user, _, host, port, dbname = m.groups()
        is_render = "render.com" in host or "dpg-" in host
        is_neon = "neon.tech" in host
        provider = "Neon Serverless Postgres" if is_neon else ("Render Managed Postgres" if is_render else "PostgreSQL Cloud")
        return {
            "user": user,
            "host": host,
            "port": int(port or 5432),
            "database": dbname,
            "is_render": is_render,
            "is_neon": is_neon,
            "provider": provider,
            "sslmode": "require" if ("sslmode=require" in url or is_render or is_neon) else "prefer"
        }
    return {"host": "desconocido", "database": "desconocido", "is_render": False, "is_neon": False, "provider": "PostgreSQL"}

def get_connection(custom_url=None):
    """
    Obtiene una conexión directa a PostgreSQL (si hay URL configurada)
    o a SQLite local. Retorna (conn, is_postgres, details).
    """
    target_url = custom_url or models.get_database_url()
    
    if target_url and models.PSYCOPG2_AVAILABLE:
        # Asegurar sslmode=require para Render, Neon y conexiones remotas
        if "sslmode" not in target_url and not target_url.startswith("postgresql://localhost") and "@localhost" not in target_url:
            sep = "&" if "?" in target_url else "?"
            target_url = f"{target_url}{sep}sslmode=require"
            
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(target_url)
        details = parse_url_details(target_url)
        details["masked_url"] = mask_database_url(target_url)
        return conn, True, details

    # SQLite Fallback
    import sqlite3
    db_path = models.DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn, False, {
        "engine": "sqlite",
        "database": os.path.basename(db_path),
        "path": db_path,
        "is_render": False
    }

def get_db_status(custom_url=None):
    """Obtiene el diagnóstico completo del motor de base de datos actual."""
    start_time = time.time()
    try:
        conn, is_postgres, details = get_connection(custom_url)
        ping_ms = round((time.time() - start_time) * 1000, 2)
        
        tables_info = []
        version_str = "Desconocida"
        
        if is_postgres:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version_str = cur.fetchone()[0]
                
                # Obtener tablas con conteo y tamaño
                cur.execute("""
                    SELECT 
                        t.table_name,
                        COALESCE(s.n_live_tup, 0) as estimated_rows,
                        pg_size_pretty(pg_total_relation_size('"' || t.table_name || '"')) as size
                    FROM information_schema.tables t
                    LEFT JOIN pg_stat_user_tables s ON s.relname = t.table_name
                    WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
                    ORDER BY t.table_name;
                """)
                pg_tables = cur.fetchall()
                
                for row in pg_tables:
                    t_name = row[0]
                    # Hacer conteo exacto para tablas de la app
                    try:
                        cur.execute(f'SELECT COUNT(*) FROM "{t_name}";')
                        exact_count = cur.fetchone()[0]
                    except Exception:
                        exact_count = row[1]
                    tables_info.append({
                        "name": t_name,
                        "rows": exact_count,
                        "size": row[2]
                    })
            conn.close()
            
            return {
                "ok": True,
                "engine": "postgresql",
                "is_render": details.get("is_render", False),
                "host": details.get("host"),
                "port": details.get("port", 5432),
                "database": details.get("database"),
                "user": details.get("user"),
                "ssl": details.get("sslmode", "require"),
                "masked_url": details.get("masked_url"),
                "version": version_str,
                "ping_ms": ping_ms,
                "tables_count": len(tables_info),
                "tables": tables_info
            }
        else:
            # SQLite
            import sqlite3
            version_str = f"SQLite {sqlite3.sqlite_version}"
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
            sqlite_tables = [r[0] for r in cur.fetchall()]
            
            for t_name in sqlite_tables:
                cur.execute(f'SELECT COUNT(*) FROM "{t_name}";')
                c = cur.fetchone()[0]
                tables_info.append({
                    "name": t_name,
                    "rows": c,
                    "size": "-"
                })
            conn.close()
            
            return {
                "ok": True,
                "engine": "sqlite",
                "is_render": False,
                "host": "localhost (Almacenamiento Local)",
                "port": "-",
                "database": details.get("database"),
                "user": "sistema",
                "ssl": "N/A",
                "masked_url": details.get("path"),
                "version": version_str,
                "ping_ms": ping_ms,
                "tables_count": len(tables_info),
                "tables": tables_info
            }
            
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "ping_ms": round((time.time() - start_time) * 1000, 2)
        }

def get_tables_schema(custom_url=None):
    """Retorna las columnas, tipos y claves primarias de cada tabla."""
    conn, is_postgres, _ = get_connection(custom_url)
    schemas = {}
    
    try:
        if is_postgres:
            with conn.cursor() as cur:
                # Obtener nombres de tablas
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """)
                tables = [r[0] for r in cur.fetchall()]
                
                for t in tables:
                    # Columnas
                    cur.execute("""
                        SELECT 
                            c.column_name, 
                            c.data_type, 
                            c.is_nullable, 
                            c.column_default
                        FROM information_schema.columns c
                        WHERE c.table_schema = 'public' AND c.table_name = %s
                        ORDER BY c.ordinal_position;
                    """, (t,))
                    cols_data = cur.fetchall()
                    
                    # PKs
                    cur.execute("""
                        SELECT kcu.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name
                          AND tc.table_schema = kcu.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                          AND tc.table_schema = 'public'
                          AND tc.table_name = %s;
                    """, (t,))
                    pks = {r[0] for r in cur.fetchall()}
                    
                    schemas[t] = [
                        {
                            "name": col[0],
                            "type": col[1].upper(),
                            "nullable": col[2] == "YES",
                            "default": str(col[3]) if col[3] is not None else "",
                            "is_pk": col[0] in pks
                        }
                        for col in cols_data
                    ]
        else:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
            tables = [r[0] for r in cur.fetchall()]
            
            for t in tables:
                cur.execute(f'PRAGMA table_info("{t}");')
                cols_data = cur.fetchall()
                schemas[t] = [
                    {
                        "name": col[1],
                        "type": col[2].upper(),
                        "nullable": col[3] == 0,
                        "default": str(col[4]) if col[4] is not None else "",
                        "is_pk": col[5] == 1
                    }
                    for col in cols_data
                ]
    finally:
        conn.close()
        
    return schemas

def get_table_rows(table_name, page=1, per_page=50, search="", order_by=None, direction="ASC", custom_url=None):
    """Retorna filas paginadas con búsqueda segura."""
    conn, is_postgres, _ = get_connection(custom_url)
    
    # Validar tabla existente
    schemas = get_tables_schema(custom_url)
    if table_name not in schemas:
        conn.close()
        raise ValueError(f"La tabla '{table_name}' no existe en la base de datos")
        
    cols = schemas[table_name]
    col_names = [c["name"] for c in cols]
    
    # Sanitizar columna de orden
    if order_by and order_by not in col_names:
        order_by = None
    if direction.upper() not in ["ASC", "DESC"]:
        direction = "ASC"
        
    if not order_by:
        pk_cols = [c["name"] for c in cols if c["is_pk"]]
        order_by = pk_cols[0] if pk_cols else col_names[0]
        
    page = max(1, int(page))
    per_page = max(1, min(200, int(per_page)))
    offset = (page - 1) * per_page
    
    where_clauses = []
    params = []
    
    if search:
        search_terms = []
        for c in cols:
            c_name = c["name"]
            c_type = c["type"].lower()
            if any(t in c_type for t in ["char", "text", "string", "varchar"]):
                if is_postgres:
                    search_terms.append(f'"{c_name}"::text ILIKE %s')
                else:
                    search_terms.append(f'"{c_name}" LIKE ?')
                params.append(f"%{search}%")
        if search_terms:
            where_clauses.append("(" + " OR ".join(search_terms) + ")")
            
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    
    try:
        cur = conn.cursor()
        
        # Conteo total
        count_query = f'SELECT COUNT(*) FROM "{table_name}" {where_sql};'
        cur.execute(count_query, params)
        total_rows = cur.fetchone()[0]
        
        # Filas
        data_query = f'SELECT * FROM "{table_name}" {where_sql} ORDER BY "{order_by}" {direction} LIMIT {per_page} OFFSET {offset};'
        cur.execute(data_query, params)
        
        raw_rows = cur.fetchall()
        rows = []
        for r in raw_rows:
            if hasattr(r, "keys"):
                row_dict = {k: json_serializable(r[k]) for k in r.keys()}
            else:
                row_dict = {col_names[i]: json_serializable(r[i]) for i in range(len(col_names))}
            rows.append(row_dict)
            
        total_pages = max(1, (total_rows + per_page - 1) // per_page)
        
        return {
            "table": table_name,
            "columns": cols,
            "rows": rows,
            "total_rows": total_rows,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "order_by": order_by,
            "direction": direction
        }
    finally:
        conn.close()

def execute_query(sql, custom_url=None, max_rows=500):
    """Ejecuta una consulta SQL arbitraria con diagnóstico de tiempo."""
    if not sql or not sql.strip():
        return {"status": "error", "error": "La consulta SQL no puede estar vacía."}
        
    clean_sql = sql.strip()
    start_time = time.time()
    
    conn, is_postgres, _ = get_connection(custom_url)
    try:
        cur = conn.cursor()
        cur.execute(clean_sql)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        
        # Verificar si retorna filas (SELECT, SHOW, EXPLAIN, RETURNING)
        has_results = cur.description is not None
        
        if has_results:
            columns = [desc[0] for desc in cur.description]
            raw_rows = cur.fetchmany(max_rows)
            rows = []
            for r in raw_rows:
                if hasattr(r, "keys"):
                    rows.append({k: json_serializable(r[k]) for k in r.keys()})
                else:
                    rows.append({columns[i]: json_serializable(r[i]) for i in range(len(columns))})
                    
            conn.commit()
            return {
                "status": "ok",
                "type": "select",
                "duration_ms": duration_ms,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "is_truncated": len(raw_rows) == max_rows
            }
        else:
            rows_affected = cur.rowcount
            conn.commit()
            return {
                "status": "ok",
                "type": "dml",
                "duration_ms": duration_ms,
                "rows_affected": rows_affected,
                "message": f"Consulta ejecutada correctamente. Filas afectadas: {rows_affected}"
            }
    except Exception as e:
        conn.rollback()
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "status": "error",
            "duration_ms": duration_ms,
            "error": str(e)
        }
    finally:
        conn.close()

def export_table(table_name, export_format="json", custom_url=None):
    """Exporta todo el contenido de una tabla a formato JSON o CSV."""
    conn, is_postgres, _ = get_connection(custom_url)
    schemas = get_tables_schema(custom_url)
    if table_name not in schemas:
        conn.close()
        raise ValueError(f"Tabla '{table_name}' no encontrada")
        
    cols = [c["name"] for c in schemas[table_name]]
    try:
        cur = conn.cursor()
        cur.execute(f'SELECT * FROM "{table_name}";')
        raw_rows = cur.fetchall()
        rows = []
        for r in raw_rows:
            if hasattr(r, "keys"):
                rows.append({k: json_serializable(r[k]) for k in r.keys()})
            else:
                rows.append({cols[i]: json_serializable(r[i]) for i in range(len(cols))})
                
        if export_format.lower() == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=cols)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            return output.getvalue(), "text/csv"
        else:
            return json.dumps(rows, indent=2, ensure_ascii=False), "application/json"
    finally:
        conn.close()

def test_connection_url(url):
    """Prueba una URL externa o interna de PostgreSQL y retorna diagnóstico."""
    if not url:
        return {"ok": False, "error": "Debes ingresar una URL de PostgreSQL"}
        
    clean_url = url.strip()
    if clean_url.startswith("postgres://"):
        clean_url = clean_url.replace("postgres://", "postgresql://", 1)
        
    if "sslmode" not in clean_url and ("render.com" in clean_url or "dpg-" in clean_url):
        sep = "&" if "?" in clean_url else "?"
        clean_url = f"{clean_url}{sep}sslmode=require"
        
    start_time = time.time()
    try:
        if not models.PSYCOPG2_AVAILABLE:
            return {"ok": False, "error": "Librería psycopg2 no disponible en el sistema"}
            
        import psycopg2
        conn = psycopg2.connect(clean_url, connect_timeout=8)
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version_str = cur.fetchone()[0]
        conn.close()
        
        latency = round((time.time() - start_time) * 1000, 2)
        details = parse_url_details(clean_url)
        return {
            "ok": True,
            "version": version_str,
            "latency_ms": latency,
            "details": details,
            "normalized_url": clean_url
        }
    except Exception as e:
        latency = round((time.time() - start_time) * 1000, 2)
        err_msg = str(e)
        if "password authentication failed" in err_msg.lower():
            err_msg = "Contraseña o usuario de Render incorrectos."
        elif "could not translate host name" in err_msg.lower():
            err_msg = "No se pudo resolver el host de Render. Verifica el nombre del host."
        elif "connection refused" in err_msg.lower():
            err_msg = "Conexión rechazada. Si estás conectando desde tu PC usa la 'External Database URL' de Render."
        return {
            "ok": False,
            "error": err_msg,
            "latency_ms": latency
        }

def set_runtime_database_url(url):
    """Establece la URL activa para la aplicación en ejecución."""
    if not url:
        models.OVERRIDE_DATABASE_URL = None
        return True, "Restablecido a configuración por defecto"
        
    test = test_connection_url(url)
    if not test.get("ok"):
        return False, test.get("error", "Error de conexión")
        
    models.OVERRIDE_DATABASE_URL = test["normalized_url"]
    
    # Intentar inicializar esquemas en la nueva base de datos
    try:
        models.init_db()
    except Exception as e:
        print("Aviso al inicializar esquemas:", e)
        
    return True, "Conexión a PostgreSQL de Render establecida exitosamente"

# =========================================================================
# CLI COMMAND LINE INTERFACE
# =========================================================================
def run_cli():
    import argparse
    parser = argparse.ArgumentParser(description="Gestor de Base de Datos PostgreSQL de FitChallenge (Render MSP)")
    parser.add_argument("--status", action="store_true", help="Muestra el estado de la conexión y las tablas")
    parser.add_argument("--tables", action="store_true", help="Lista todas las tablas y conteo de filas")
    parser.add_argument("--schema", type=str, metavar="TABLA", help="Muestra el esquema de columnas de una tabla")
    parser.add_argument("--rows", type=str, metavar="TABLA", help="Muestra los registros de una tabla")
    parser.add_argument("--limit", type=int, default=20, help="Límite de filas a mostrar (por defecto 20)")
    parser.add_argument("--query", type=str, help="Ejecuta una consulta SQL personalizada")
    parser.add_argument("--test-url", type=str, metavar="URL", help="Prueba una URL de Render PostgreSQL")
    parser.add_argument("--export", type=str, metavar="TABLA", help="Exporta una tabla a stdout o archivo")
    parser.add_argument("--format", type=str, default="json", choices=["json", "csv"], help="Formato de exportación")
    parser.add_argument("--web", action="store_true", help="Inicia el servidor web dedicado al gestor")
    parser.add_argument("--port", type=int, default=5050, help="Puerto para el servidor web (por defecto 5050)")
    
    args = parser.parse_args()
    
    if args.test_url:
        print(f"\nProbando conexión a: {mask_database_url(args.test_url)} ...")
        res = test_connection_url(args.test_url)
        if res.get("ok"):
            print(f"✅ ¡Conexión EXITOSA en {res['latency_ms']} ms!")
            print(f"🐘 Servidor: {res['version']}")
            print(f"📊 Host: {res['details'].get('host')} | DB: {res['details'].get('database')}")
        else:
            print(f"❌ Falló la conexión: {res.get('error')}")
        return

    if args.status or args.tables:
        st = get_db_status()
        if not st.get("ok"):
            print(f"❌ Error al consultar la base de datos: {st.get('error')}")
            return
            
        print("\n" + "="*65)
        print("  FITCHALLENGE • GESTOR DE BASE DE DATOS POSTGRESQL / RENDER")
        print("="*65)
        print(f" Motor:         {st['engine'].upper()} {'(Render Managed Postgres)' if st['is_render'] else ''}")
        print(f" Servidor:      {st['host']}:{st['port']}")
        print(f" Base de Datos: {st['database']} (Usuario: {st['user']})")
        print(f" SSL:           {st['ssl']}")
        print(f" Latencia:      {st['ping_ms']} ms")
        print(f" Versión:       {st['version'].split(',')[0]}")
        print("-"*65)
        print(f"{'TABLA':<25} {'FILAS':<15} {'TAMAÑO':<15}")
        print("-"*65)
        for t in st["tables"]:
            print(f"{t['name']:<25} {t['rows']:<15} {t['size']:<15}")
        print("="*65 + "\n")
        return

    if args.schema:
        schemas = get_tables_schema()
        if args.schema not in schemas:
            print(f"❌ La tabla '{args.schema}' no existe.")
            return
        print(f"\nEsquema de la tabla: {args.schema}")
        print(f"{'COLUMNA':<25} {'TIPO':<20} {'NULLABLE':<10} {'PK':<5} {'DEFAULT'}")
        print("-" * 75)
        for c in schemas[args.schema]:
            pk_str = "PK" if c["is_pk"] else ""
            null_str = "SÍ" if c["nullable"] else "NO"
            print(f"{c['name']:<25} {c['type']:<20} {null_str:<10} {pk_str:<5} {c['default']}")
        print("\n")
        return

    if args.rows:
        try:
            res = get_table_rows(args.rows, page=1, per_page=args.limit)
            print(f"\nRegistros en {args.rows} (Mostrando {len(res['rows'])} de {res['total_rows']}):")
            print(json.dumps(res["rows"], indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"❌ Error: {e}")
        return

    if args.query:
        print(f"\nEjecutando: {args.query}")
        res = execute_query(args.query)
        if res.get("status") == "ok":
            print(f"✅ Éxito en {res['duration_ms']} ms")
            if res.get("type") == "select":
                print(f"Filas retornadas: {res['row_count']}")
                print(json.dumps(res["rows"], indent=2, ensure_ascii=False))
            else:
                print(res.get("message"))
        else:
            print(f"❌ Error al ejecutar: {res.get('error')}")
        return

    if args.export:
        try:
            content, mime = export_table(args.export, args.format)
            print(content)
        except Exception as e:
            print(f"❌ Error al exportar: {e}")
        return

    if args.web:
        start_standalone_web_server(args.port)
        return

    # Si se ejecuta sin parámetros, mostrar menú interactivo
    interactive_menu()

def interactive_menu():
    print("\n" + "="*60)
    print("  🏋️ FitChallenge • Gestor de Base de Datos PostgreSQL")
    print("="*60)
    st = get_db_status()
    if st.get("ok"):
        engine_label = "🐘 PostgreSQL (Render Managed)" if st["is_render"] else f"🐘 {st['engine'].upper()}"
        print(f"  Conectado a: {engine_label} - DB: {st['database']} ({st['ping_ms']} ms)")
    else:
        print(f"  ⚠️ Error de conexión: {st.get('error')}")
    print("="*60)
    print("1. Ver Estado y Tablas")
    print("2. Ver Esquema de una Tabla")
    print("3. Ver Datos de una Tabla")
    print("4. Ejecutar Consulta SQL")
    print("5. Probar / Cambiar URL de Render PostgreSQL")
    print("6. Iniciar Servidor Web del Gestor")
    print("0. Salir")
    print("="*60)
    
    choice = input("Elige una opción (0-6): ").strip()
    if choice == "1":
        run_cli_with_args(["--status"])
    elif choice == "2":
        tname = input("Nombre de la tabla: ").strip()
        if tname:
            run_cli_with_args(["--schema", tname])
    elif choice == "3":
        tname = input("Nombre de la tabla: ").strip()
        lim = input("Límite de filas [20]: ").strip() or "20"
        if tname:
            run_cli_with_args(["--rows", tname, "--limit", lim])
    elif choice == "4":
        q = input("SQL query: ").strip()
        if q:
            run_cli_with_args(["--query", q])
    elif choice == "5":
        u = input("Pega tu External Database URL de Render (postgresql://...): ").strip()
        if u:
            run_cli_with_args(["--test-url", u])
    elif choice == "6":
        start_standalone_web_server(5050)
    else:
        print("¡Hasta luego!")

def run_cli_with_args(args_list):
    sys.argv = [sys.argv[0]] + args_list
    run_cli()

def start_standalone_web_server(port=5050):
    """Inicia un servidor Flask dedicado al gestor en el puerto especificado."""
    from flask import Flask, jsonify, request, render_template_string
    import webbrowser

    admin_app = Flask("db_manager_standalone")

    @admin_app.route("/")
    def home():
        # Redirigir o renderizar interfaz integrada
        import app as main_app
        with main_app.app.app_context():
            return main_app.admin_db_page()

    print(f"\n🚀 Gestor de Base de Datos ejecutándose en: http://localhost:{port}")
    print(f"Abre tu navegador en: http://localhost:{port}\n")
    try:
        admin_app.run(host="0.0.0.0", port=port, debug=False)
    except Exception as e:
        print("Error al iniciar el servidor web:", e)

if __name__ == "__main__":
    run_cli()
