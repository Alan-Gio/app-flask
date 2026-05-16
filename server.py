# Esta es la seccion de librerias
import base64
from flask import Flask, render_template, request, flash, redirect, url_for, session
import os
from config import ConfigVar
import re
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message

# importar libreria de Mysql (MaDB)
from flask_mysqldb import MySQL

app = Flask(__name__)

app.config.from_object(ConfigVar)

mysql = MySQL(app)

mail = Mail(app)

# Función decoradora para proteger rutas que requieren inicio de sesión

def login_requerido(f):
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Por favor, inicia sesión para acceder.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return funcion_decorada

def admin_requerido(f):
    @wraps(f)
    def funcion_decorada(*args, **kwargs):
        # Primero revisamos si inició sesión
        if 'usuario_id' not in session:
            flash("Por favor, inicia sesión para acceder.", "warning")
            return redirect(url_for('login'))
        
        # Luego revisamos si su rol es 'admin'
        if session.get('usuario_rol') != 'admin':
            flash("Acceso denegado. Esta área es solo para administradores.", "danger")
            return redirect(url_for('catalogo')) 
            
        return f(*args, **kwargs)
    return funcion_decorada

#-----TERMINAN Función decoradora para proteger rutas que requieren inicio de sesión-----

@app.route('/')
def index():
    return render_template("index.html")

#-----VALIDACIONES DE DATOS-----

#Regla para validar nombres y apellidos: Solo letras, mayúscula al inicio, puede tener un espacio para segundo nombre o apellido, y longitud entre 1 y 30 caracteres.
regla_nombres = r"^(?=.{1,30}$)([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(\s[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?$"

# Diccionario de reglas de validación para diferentes campos
REGLAS_REGEX = {
    "nombre": regla_nombres,       
    "apellidop": regla_nombres,  
    "apellidom": regla_nombres,    
    "numero": r"^(\(?(\+52)\)?)?(\d){10}$",
    "password": r"^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[@#?!+])(?!\s)[a-zA-Z0-9@#?!+]{8,100}$",
    "correo": r"^[a-zA-Z0-9_.]+@[a-zA-Z0-9-_]+(\.[a-zA-Z]{2,4}){1,2}$",
    "edad": r"^(?=.*[0-9])[0-9]{1,2}$",
    "codigo": r"^(?=.*[0-9])[0-9]{1,20}$",
    "descripcion": r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ][a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s.,:-]{0,500}$",
    "precio": r"^\d{1,10}(\.\d{1,2})?$",
    "nombre_producto": r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-/]{1,100}$"
}

# Función para validar campos según su tipo utilizando las reglas definidas
def validarcampos(valueField, typeField):
    regla = REGLAS_REGEX.get(typeField)
    if regla and valueField:
        return bool(re.match(regla, str(valueField)))
    return False

#-----TERMINA VALIDACIONES DE DATOS-----    

#-----FUNCIONES PARA EL ADMINISTRADOR-----

# TABLA DE USUARIOS (Solo Admin)
@app.route('/tabla')
@admin_requerido
def tabla():
    # 1. Atrapamos el valor del filtro desde la URL
    filtro_rol = request.args.get('rol', 'todos')
    
    listar = mysql.connection.cursor()
    
    # 2. Ajustamos la consulta SQL dependiendo de lo que elija el admin
    if filtro_rol == 'admin':
        listar.execute("SELECT * FROM usuarios WHERE activo_user = 1 AND rol_user = 'admin'")
    elif filtro_rol == 'cliente':
        listar.execute("SELECT * FROM usuarios WHERE activo_user = 1 AND rol_user = 'cliente'")
    else:
        # Si es 'todos', mantenemos tu consulta original
        listar.execute("SELECT * FROM usuarios WHERE activo_user = 1")
        
    usuarios = listar.fetchall()
    listar.close()

    # 3. Tu lógica de mapeo se mantiene intacta
    users = []
    if usuarios:
        for campo in usuarios:
            users.append({
                "id_user": campo[0],
                "name_user": campo[1],
                "apellp_user": campo[2],
                "apellm_user": campo[3],
                "edad_user": campo[4],
                "mail_user": campo[5],
                "contra_user":"<pass>",
                "creacion_user":campo[7],
                "update_user":campo[8],
                "rol_user": campo[10]
            })
    else:
        users = None    
            
    # 4. Enviamos los usuarios filtrados y el 'filtro_actual' a la vista
    return render_template("tabla.html", usuarios=users, filtro_actual=filtro_rol)

# EDITAR USUARIO (Solo Admin)
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@admin_requerido 
def editar(id):
    id_data = str(id)
    sql_usuarios_editar = "SELECT * FROM usuarios WHERE id_user = %s"
    con_user = mysql.connection.cursor()
    con_user.execute(sql_usuarios_editar, (id,))
    res_info = con_user.fetchone()
    info_user = None

    if res_info:
        info_user = {
                "id_user": res_info[0],
                "name_user": res_info[1],
                "apellp_user": res_info[2],
                "apellm_user": res_info[3],
                "edad_user": res_info[4],
                "mail_user": res_info[5],
                "contra_user":"<pass>",
                "creacion_user":res_info[7],
                "update_user":res_info[8],
                "rol_user": res_info[10]
        }
    else:
        flash("No hay informacion del usuario", "warning")

    if request.method == 'POST':
        eNombre = request.form.get('eNombre')
        eApell = request.form.get('eApell')
        eApell2 = request.form.get('eApell2')
        eEdad = request.form.get('eEdad')
        eUsuario = request.form.get('eUsuario')
        eRol = request.form.get('eRol')

        campos = [eNombre, eApell, eApell2, eEdad, eUsuario]
        tipos = ["nombre", "apellidop", "apellidom", "edad", "correo"]

        datos_validos = True

        for valor, tipo in zip(campos, tipos):
            if not valor:  
                flash(f"El campo {tipo} no puede estar vacío.", "danger")
                datos_validos = False
            elif not validarcampos(valor, tipo):  
                flash(f"El formato ingresado en {tipo} no es válido.", "danger")
                datos_validos = False

        if datos_validos:
            insertar = mysql.connection.cursor()
            insertar.execute("SELECT * FROM usuarios WHERE mail_user = %s AND id_user != %s", (eUsuario,id))  
            usuario_existente = insertar.fetchone()
                
            if usuario_existente:
                flash("El correo electrónico ya está registrado. Por favor, utiliza otro.", "danger")
            else:
                insertar.execute("UPDATE usuarios SET name_user = %s, apellp_user = %s, apellm_user = %s, edad_user = %s, mail_user = %s, rol_user = %s WHERE id_user = %s", (eNombre,eApell,eApell2,eEdad,eUsuario,eRol,id))
                mysql.connection.commit()
                flash("Todos los datos se han actualizado correctamente.", "success")
            insertar.close()
            return redirect(url_for('tabla'))

    con_user.close()
    return render_template("editar.html", info_user=info_user) 

# ELIMINAR USUARIO (Solo Admin)
@app.route('/eliminar/<int:id>')
@admin_requerido 
def eliminar(id):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE usuarios SET activo_user = 0 WHERE id_user = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("Usuario eliminado correctamente", "success")
    return redirect(url_for('tabla'))

# AGREGAR PRODUCTOS (Solo Admin)
@app.route('/agregar_productos', methods=['GET', 'POST'])
@admin_requerido 
def agregar_productos():
    if request.method == 'POST':
        pCodigo = request.form.get('p_codig')
        pNombre = request.form.get('p_nombre')
        pDescripcion = request.form.get('p_desc')
        pCategoria = request.form.get('p_cat')
        pPrecio = request.form.get('p_precio')
        pStock = request.form.get('p_stock')
        pImagen = request.files.get('p_img')

        okcodigo = validarcampos(pCodigo, "codigo")
        oknombre = validarcampos(pNombre, "nombre_producto")
        okdescripcion = validarcampos(pDescripcion, "descripcion")
        okcategoria = validarcampos(pCategoria, "nombre_producto") 
        okprecio = validarcampos(pPrecio, "precio")
        okstock = validarcampos(pStock, "edad")

        todosCamposOK = all([okcodigo, oknombre, okdescripcion, okcategoria, okprecio, okstock])

        if pImagen is None or pImagen.filename == '':
            flash("La imagen es obligatoria.", "danger")
        elif todosCamposOK is True:
            imagenBinaria = pImagen.read()
            imagen_base64 = base64.b64encode(imagenBinaria).decode('utf-8')
            try:
                agregarProd = mysql.connection.cursor()                  
                sql_addprod = "INSERT INTO productos (p_cod, p_name, p_desc, p_cat, p_precio, p_stock, p_img) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                agregarProd.execute(sql_addprod, (pCodigo, pNombre, pDescripcion, pCategoria, pPrecio, pStock, imagen_base64))
                mysql.connection.commit()
                agregarProd.close()
                flash("Producto agregado correctamente", "success")
                return redirect(url_for('catalogo'))
            except Exception as e:
                flash("Hubo un problema al guardar en la base de datos", "danger")
                app.logger.error(f"Error al insertar producto. ERROR: {e}") 
    return render_template("agregar_productos.html")  

# TABLA DE PRODUCTOS (Solo Admin)
@app.route('/tabla_productos', methods=['GET'])
@admin_requerido  
def tabla_productos():
    
    filtro_cat = request.args.get('categoria', 'todas')

    listar = mysql.connection.cursor()
    
   
    if filtro_cat != 'todas':
        
        listar.execute("SELECT * FROM productos WHERE p_cat = %s", (filtro_cat,))
    else:
        listar.execute("SELECT * FROM productos")
        
    productos = listar.fetchall()
    listar.close()

    product = []
    if productos:
        for campo in productos:
            product.append({
                "p_id": campo[0],
                "p_cod": campo[1],
                "p_name":campo[2],
                "p_precio": campo[5],
                "p_stock": campo[6],
                "p_estado": campo[10]
            })
    else:
        product = None 

    
    return render_template("tabla_productos.html", productos=product, filtro_actual=filtro_cat)

# DETALLES DE ADMINISTRADOR (Solo Admin)
@app.route('/detalles_admin/<int:id>')
@admin_requerido  
def detalles_admin(id):
    listar = mysql.connection.cursor()
    listar.execute("SELECT * FROM productos WHERE p_id = %s", (id,))
    campo = listar.fetchone()
    listar.close()

    if campo:
        producto_encontrado = {
            "p_id": campo[0],
            "p_codigo": campo[1],
            "p_nombre": campo[2],
            "p_descripcion": campo[3],
            "p_categoria": campo[4],
            "p_precio": campo[5],
            "p_stock": campo[6],
            "p_imagen": campo[7],
        }
    else:
        producto_encontrado = None
    return render_template("detalles_admin.html", producto=producto_encontrado)

# EDITAR PRODUCTO (Solo Admin)
@app.route('/editar_producto/<int:id>', methods=['GET', 'POST'])
@admin_requerido 
def editar_producto(id):
    con_prod = mysql.connection.cursor()

    if request.method == 'POST':
        # 1. Recibes los textos
        eCod = request.form.get('eCod')
        eNombre = request.form.get('eNombre')
        eDesc = request.form.get('eDesc')
        eCat = request.form.get('eCat')
        ePrecio = request.form.get('ePrecio')
        eStock = request.form.get('eStock')
        
        # 2. Recibes el archivo (imagen)
        eImagen = request.files.get('eImg')

        cursor = mysql.connection.cursor()

        try:
            # CAMINO A: El usuario SÍ subió una imagen nueva
            if eImagen and eImagen.filename != '':
                imagenBinaria = eImagen.read()
                imagen_base64 = base64.b64encode(imagenBinaria).decode('utf-8')
                
                sql = """UPDATE productos SET p_cod=%s, p_name=%s, p_desc=%s, 
                         p_cat=%s, p_precio=%s, p_stock=%s, p_img=%s WHERE p_id=%s"""
                cursor.execute(sql, (eCod, eNombre, eDesc, eCat, ePrecio, eStock, imagen_base64, id))
            
            # CAMINO B: El usuario NO subió imagen (solo cambió texto/categoría)
            else:
                # Fíjate que aquí quitamos el 'p_img=%s' para no borrarla
                sql = """UPDATE productos SET p_cod=%s, p_name=%s, p_desc=%s, 
                         p_cat=%s, p_precio=%s, p_stock=%s WHERE p_id=%s"""
                cursor.execute(sql, (eCod, eNombre, eDesc, eCat, ePrecio, eStock, id))

            mysql.connection.commit()
            flash('Producto actualizado correctamente.', 'success')
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al actualizar: {str(e)}', 'danger')
        finally:
            cursor.close()

        return redirect(url_for('tabla_productos'))
 
    con_prod.execute("SELECT * FROM productos WHERE p_id = %s", (id,))
    res_info = con_prod.fetchone()
    con_prod.close()

    info_producto = None

    if res_info:
        info_producto = {
            "p_id": res_info[0],
            "p_cod": res_info[1],
            "p_name": res_info[2],
            "p_desc": res_info[3],
            "p_cat": res_info[4],
            "p_precio": res_info[5],
            "p_stock": res_info[6],
            "p_img": res_info[7]
        }
    else:
        flash("No se encontró el producto.", "warning")
        return redirect(url_for('tabla_productos'))

    return render_template("editar_producto.html", producto=info_producto)

# PANEL DE ADMINISTRADOR: VER TODOS LOS PEDIDOS
@app.route('/admin_pedidos')
@admin_requerido
def admin_pedidos():
    cur = mysql.connection.cursor()
    query = """
        SELECT 
            p.id_pedido,       
            CONCAT(u.name_user, ' ', u.apellp_user),  -- CORREGIDO: Muestra "Nombre Apellido"
            p.fecha_pedido,    
            p.total_pagado,    
            p.estado,          
            p.direccion_envio, 
            GROUP_CONCAT(CONCAT(pr.p_name, ' (', dp.talla, ') x', dp.cantidad) SEPARATOR '<br>') as articulos
        FROM pedidos p
        JOIN usuarios u ON p.id_user = u.id_user
        JOIN detalles_pedido dp ON p.id_pedido = dp.id_pedido
        JOIN productos pr ON dp.p_id = pr.p_id
        GROUP BY p.id_pedido
        ORDER BY p.fecha_pedido DESC
    """
    cur.execute(query)
    pedidos = cur.fetchall()
    cur.close()
    return render_template('admin_pedidos.html', pedidos=pedidos)

# PANEL DE ADMINISTRADOR: ACTUALIZAR ESTADO
@app.route('/actualizar_estado', methods=['POST'])
@admin_requerido
def actualizar_estado():
    id_pedido = request.form.get('id_pedido')
    nuevo_estado = request.form.get('nuevo_estado')
    
    cur = mysql.connection.cursor()
    try:
        
        cur.execute("UPDATE pedidos SET estado = %s WHERE id_pedido = %s", (nuevo_estado, id_pedido))
        mysql.connection.commit()

       
        enviar_notificacion = True
        asunto = ""
        mensaje_texto = ""

        if nuevo_estado == 'Enviado':
            asunto = f"¡Tu pedido #{id_pedido} va en camino! 🚚"
            mensaje_texto = "¡Excelentes noticias! Tu pedido ya se encuentra en manos de la paquetería y pronto llegará a tu destino."
        
        elif nuevo_estado == 'Entregado':
            asunto = f"¡Pedido #{id_pedido} entregado con éxito! ✅"
            mensaje_texto = "Confirmamos que tu pedido ha sido entregado. ¡Esperamos que disfrutes tus jerseys! No olvides etiquetarnos en redes sociales."
        
        elif nuevo_estado == 'Cancelado':
            asunto = f"Actualización de tu pedido #{id_pedido} ❌"
            mensaje_texto = "Te informamos que tu pedido ha sido cancelado. Si tienes dudas sobre el motivo o el reembolso, por favor contáctanos respondiendo a este correo."
        
        else:
            
            enviar_notificacion = False

        
        if enviar_notificacion:
            try:
                cur.execute("""
                    SELECT u.mail_user, u.name_user 
                    FROM usuarios u 
                    JOIN pedidos p ON u.id_user = p.id_user 
                    WHERE p.id_pedido = %s
                """, (id_pedido,))
                cliente = cur.fetchone()

                if cliente:
                    correo_destino = cliente[0]
                    nombre_cliente = cliente[1]

                    msg = Message(
                        subject=asunto,
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[correo_destino]
                    )
                    
                    msg.body = f"""
                    Hola {nombre_cliente},
                    
                    {mensaje_texto}
                    
                    Número de orden: #{id_pedido}
                    Estado actual: {nuevo_estado}
                    
                    ¡Gracias por elegir The MVP Store!
                    """
                    
                    mail.send(msg)
                    print(f"Notificación de {nuevo_estado} enviada a {correo_destino}")    

            except Exception as e_mail:
                print(f"Error al enviar correo de notificación: {e_mail}")

        flash(f"El estado del pedido #{id_pedido} se actualizó a '{nuevo_estado}'", "success")

    except Exception as e:
        mysql.connection.rollback()
        flash("Hubo un error al actualizar el estado.", "danger")
        print(f"Error al actualizar estado: {e}")
    finally:
        cur.close()
        
    return redirect(url_for('admin_pedidos'))

# RUTA PARA DESACTIVAR (BORRADO LÓGICO)
@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE productos SET p_estado = 0 WHERE p_id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("Producto desactivado correctamente", "warning")
    return redirect(url_for('tabla_productos'))

# RUTA PARA RESTAURAR
@app.route('/restaurar_producto/<int:id>')
def restaurar_producto(id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE productos SET p_estado = 1 WHERE p_id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash("¡Producto reactivado!", "success")
    return redirect(url_for('tabla_productos'))

#-----TERMINAN FUNCIONES PARA EL ADMINISTRADOR-----

#-----FUNCIONES DEL USUARIO-----

#TABLA DE USUARIOS (Solo Usuario)
@app.route('/tablausuario')
@login_requerido
def tablausuario():
    id_usuario = session.get('usuario_id')
    cur = mysql.connection.cursor()

    # 1. TRAER INFORMACIÓN DEL USUARIO
    cur.execute("SELECT * FROM usuarios WHERE id_user = %s", (id_usuario,))
    campo = cur.fetchone()

    # 2. TRAER PEDIDOS
    cur.execute("""
        SELECT id_pedido, fecha_pedido, total_pagado, estado 
        FROM pedidos 
        WHERE id_user = %s 
        ORDER BY fecha_pedido DESC
    """, (id_usuario,))
    historial = cur.fetchall()

    cur.close()

    if campo:
        # Mapeo manual para asegurar que el HTML reciba las llaves correctas
        info_usuario = {
            "id_user": campo[0],
            "name_user": campo[1],
            "apellp_user": campo[2],
            "apellm_user": campo[3],
            "edad_user": campo[4],
            "mail_user": campo[5],
            # Ajuste de índices para dirección (asumiendo que son las últimas columnas) [cite: 146, 147]
            "calle": campo[11] if len(campo) > 11 else "",
            "colonia": campo[12] if len(campo) > 12 else "",
            "cp": campo[13] if len(campo) > 13 else "",
            "ciudad": campo[14] if len(campo) > 14 else "",
            "estado": campo[15] if len(campo) > 15 else ""
        }
        return render_template("tablausuario.html", usuario=info_usuario, pedidos=historial)
    else:
        flash("Usuario no encontrado", "danger")
        return redirect(url_for('login'))

# RUTA PARA ACTUALIZAR PERFIL (Solo Usuario)
@app.route('/actualizar_perfil', methods=['POST'])
@login_requerido
def actualizar_perfil():
    id_usuario = session.get('usuario_id')
    accion = request.form.get('accion') 
    cur = mysql.connection.cursor()

    try:
        if accion == 'datos_personales':
            # Recoger datos básicos
            nombre = request.form.get('nombre')
            ap_p = request.form.get('ap_p')
            ap_m = request.form.get('ap_m')
            edad = request.form.get('edad')
            correo = request.form.get('correo')
            
            cur.execute("""
                UPDATE usuarios SET name_user=%s, apellp_user=%s, apellm_user=%s, edad_user=%s, mail_user=%s 
                WHERE id_user=%s
            """, (nombre, ap_p, ap_m, edad, correo, id_usuario))
            flash("Datos personales actualizados", "success")

        elif accion == 'direccion':

            calle = request.form.get('calle')
            colonia = request.form.get('colonia')
            cp = request.form.get('cp')
            ciudad = request.form.get('ciudad')
            estado = request.form.get('estado')
            
            cur.execute("""
                UPDATE usuarios SET calle=%s, colonia=%s, cp=%s, ciudad=%s, estado=%s 
                WHERE id_user=%s
            """, (calle, colonia, cp, ciudad, estado, id_usuario))
            flash("Dirección de envío actualizada", "success")

        elif accion == 'password':

            nueva_pass = request.form.get('nueva_pass')

            pass_encriptada = generate_password_hash(nueva_pass)


            cur.execute("UPDATE usuarios SET contra_user=%s WHERE id_user=%s", (pass_encriptada, id_usuario))
            flash("Contraseña actualizada correctamente", "info")

        mysql.connection.commit()
    except Exception as e:
        mysql.connection.rollback()
        flash(f"Error al actualizar: {str(e)}", "danger")
    finally:
        cur.close()

    return redirect(url_for('tablausuario'))

# RUTA PARA VER DETALLES DE UN PEDIDO (Solo Usuario)
@app.route('/pedido_detalles/<int:id_pedido>')
@login_requerido
def pedido_detalles(id_pedido):
    cur = mysql.connection.cursor()
    try:

        cur.execute("""
            SELECT p.p_name, d.cantidad, d.precio_unitario, d.talla 
            FROM detalles_pedido d
            JOIN productos p ON d.p_id = p.p_id
            WHERE d.id_pedido = %s
        """, (id_pedido,))
        items = cur.fetchall()
        
        if not items:
            return "<p class='text-center text-secondary py-3'>No hay productos registrados en este pedido.</p>"

  
        html = '<ul class="list-group list-group-flush bg-transparent">'
        for item in items:
            nombre_producto = item[0]
            cantidad = item[1]
            precio = item[2]
            talla = item[3] 
            subtotal = cantidad * precio
            
            html += f"""
            <li class="list-group-item bg-transparent text-white border-secondary d-flex justify-content-between align-items-center py-3">
                <div>
                    <h6 class="mb-0 fw-bold text-info">{nombre_producto}</h6>
                    <small class="text-secondary">
                        Talla: <span class="text-white fw-bold">{talla}</span> | 
                        {cantidad} unidad(es) x ${precio:,.2f}
                    </small>
                </div>
                <span class="fw-bold text-success">${subtotal:,.2f}</span>
            </li>
            """
        html += '</ul>'
        return html
        
    except Exception as e:
        print(f"Error en pedido_detalles: {e}")
        return f"<p class='text-danger p-3'>Error al cargar los detalles: {str(e)}</p>"
    finally:
        cur.close()

# RUTA PARA ACTUALIZAR DIRECCIÓN DE ENVÍO (Cualquier usuario logueado)
@app.route('/actualizar_direccion', methods=['POST'])
def actualizar_direccion():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

  
    calle = request.form.get('calle')
    colonia = request.form.get('colonia')
    cp = request.form.get('cp')
    ciudad = request.form.get('ciudad')
    estado = request.form.get('estado')

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            UPDATE usuarios 
            SET calle=%s, colonia=%s, cp=%s, ciudad=%s, estado=%s 
            WHERE id_user=%s
        """, (calle, colonia, cp, ciudad, estado, session['usuario_id']))
        mysql.connection.commit()
        flash("Dirección actualizada correctamente", "success")
    except Exception as e:
        print(f"Error: {e}")
        flash("No se pudo actualizar la dirección", "danger")
    finally:
        cur.close()

    return redirect(url_for('tablausuario'))

# RUTA PARA DESACTIVAR CUENTA (Borrado Lógico)
@app.route('/desactivar_cuenta', methods=['POST'])
def desactivar_cuenta():
    id_usuario = session.get('usuario_id')
    cur = mysql.connection.cursor()
    

    cur.execute("UPDATE usuarios SET activo_user = 0 WHERE id_user = %s", (id_usuario,))
    mysql.connection.commit()
    cur.close()
    
    session.clear() # Cerramos la sesión
    flash("Tu cuenta ha sido desactivada. ¡Esperamos verte pronto!", "info")
    return redirect(url_for('index')) 

# RUTA PARA REACTIVAR CUENTA
@app.route('/confirmar_reactivacion', methods=['POST'])
def confirmar_reactivacion():
   
    id_usuario = session.get('id_reactivar') 
    
    if id_usuario:
        cur = mysql.connection.cursor()
        
        cur.execute("UPDATE usuarios SET activo_user = 1 WHERE id_user = %s", (id_usuario,))
        mysql.connection.commit()
        cur.close()
        
        session.pop('id_reactivar', None)
        flash("¡Bienvenido de vuelta! Tu cuenta ha sido reactivada. Por favor, inicia sesión.", "success")
        
    return redirect(url_for('login'))

#-----TERMINAN FUNCIONES DEL USUARIO-----

#-----FUNCIONES PUBLICAS-----

# FORMULARIO DE REGISTRO 
@app.route('/formulario', methods=['GET', 'POST'])
def formulario():
    inputs = None
    if request.method == "POST":
        cNombre = request.form.get('cNombre')
        cApP = request.form.get('cApell')
        cApM = request.form.get('cApell2')
        cedad = request.form.get('cEdad')
        cemail = request.form.get('cUsuario')
        cpass = request.form.get('cpass')
        cpass2 = request.form.get('cpass2')
        ctyc = request.form.get('cTyc')

        inputs = [cNombre, cApP, cApM, cedad, cemail, cpass]      
        campos = [cNombre, cApP, cApM, cedad, cemail, cpass, ctyc]
        tipos = ["nombre", "apellidop", "apellidom", "edad", "correo", "password"]

        datos_validos = True

        for valor, tipo in zip(campos, tipos):
            if not valor:  
                flash(f"El campo {tipo} no puede estar vacío.", "danger")
                datos_validos = False
            elif not validarcampos(valor, tipo):  
                flash(f"El formato ingresado en {tipo} no es válido.", "danger")
                datos_validos = False
        
        if cpass != cpass2:
            flash("Las contraseñas no coinciden.", "danger")
            datos_validos = False

        if ctyc != "on":
            flash("Debes aceptar los términos y condiciones para continuar.", "danger")
            datos_validos = False
            
        if datos_validos:
            insertar = mysql.connection.cursor()
            insertar.execute("SELECT * FROM usuarios WHERE mail_user = %s", (cemail,))  
            usuario_existente = insertar.fetchone()
                
            if usuario_existente:
                flash("El correo electrónico ya está registrado. Por favor, utiliza otro.", "danger")
            else:
                sql_insert = "INSERT INTO usuarios (name_user, apellp_user, apellm_user, edad_user, mail_user, contra_user, rol_user) VALUES(%s,%s,%s,%s,%s,%s, 'cliente')"
                contra_segura = generate_password_hash(cpass)
                insertar.execute(sql_insert, (cNombre,cApP,cApM,cedad,cemail,contra_segura))
                mysql.connection.commit()
                flash("Todos los datos son correctos. Registro exitoso.", "success")

                insertar.close()

                return redirect(url_for('login'))

            insertar.close()

    return render_template("formulario.html", inputs=inputs)

# CATALOGO DE PRODUCTOS
@app.route('/catalogo', methods=['GET'])
def catalogo():
    
    filtro_cat = request.args.get('categoria', 'todas')
    
    listar = mysql.connection.cursor()
    
    if filtro_cat != 'todas':
       
        listar.execute("SELECT * FROM productos WHERE p_cat = %s AND p_estado = 1", (filtro_cat,))
    else:
      
        listar.execute("SELECT * FROM productos WHERE p_estado = 1")
        
    productos = listar.fetchall()
    listar.close()

    products = []
    if productos:
        for campo in productos:
            products.append({
                "p_id": campo[0],
                "p_codigo": campo[1],
                "p_nombre": campo[2],
                "p_descripcion": campo[3],
                "p_categoria": campo[4],
                "p_precio": campo[5],
                "p_stock": campo[6],
                "p_imagen": campo[7],
            })
    else:
        products = None

    return render_template("catalogo.html", productos=products, filtro_actual=filtro_cat)

# DETALLES DEL PRODUCTO (Publico)
@app.route('/detalles_producto/<int:id>')
@login_requerido
def detalles_producto(id):
    listar = mysql.connection.cursor()
    listar.execute("SELECT * FROM productos WHERE p_id = %s", (id,))
    campo = listar.fetchone()
    listar.close()

    if campo:
        producto_encontrado = {
            "p_id": campo[0],
            "p_codigo": campo[1],
            "p_nombre": campo[2],
            "p_descripcion": campo[3],
            "p_categoria": campo[4],
            "p_precio": campo[5],
            "p_stock": campo[6],
            "p_imagen": campo[7],
        }
    else:
        producto_encontrado = None

    return render_template("detalles_producto.html", producto=producto_encontrado)

#-----TERMINAN FUNCIONES PUBLICAS-----

#-----FUNCIONES DEL CARRITO DE COMPRAS-----

#CARRITO DE COMPRAS
@app.route('/carrito')
def mi_carrito():
    productos_carrito = []
    total_pagar = 0

    if 'carrito' in session and session['carrito']:
        cursor = mysql.connection.cursor()
        
        for llave_compuesta, cantidad in session['carrito'].items():
            # Separamos "5_M" en ID "5" y Talla "M"
            partes = llave_compuesta.split('_')
            producto_id = partes[0]
            talla = partes[1] if len(partes) > 1 else 'Única'
            
            cursor.execute("SELECT * FROM productos WHERE p_id = %s", (producto_id,))
            campo = cursor.fetchone() 
            
            if campo:
                precio = float(campo[5]) 
                subtotal = precio * cantidad
                total_pagar += subtotal
                
                productos_carrito.append({
                    "llave_carrito": llave_compuesta, 
                    "p_id": campo[0],
                    "p_codigo": campo[1],
                    "p_nombre": campo[2],
                    "p_descripcion": campo[3],
                    "p_categoria": campo[4],
                    "p_precio": precio,
                    "p_stock": campo[6],
                    "p_imagen": campo[7],
                    "talla": talla,                   
                    "cantidad": cantidad,   
                    "subtotal": subtotal    
                })
                
        cursor.close()

    return render_template("carrito.html", productos_carrito=productos_carrito, total_pagar=total_pagar)

# RUTA PARA AGREGAR AL CARRITO (Desde el catálogo)
@app.route('/agregar_carrito/<string:id>', methods=['POST'])
def agregar_carrito(id):
    talla = request.form.get('talla')
    
    
    if not talla:
        flash("Por favor, selecciona una talla antes de agregar al carrito.", "warning")
        return redirect(request.referrer or url_for('catalogo'))

    llave_producto = f"{id}_{talla}"

    
    cur = mysql.connection.cursor()
    cur.execute("SELECT p_stock FROM productos WHERE p_id = %s", (id,))
    producto = cur.fetchone()
    cur.close()

    if not producto:
        flash("El producto no existe.", "danger")
        return redirect(url_for('catalogo'))
        
    stock_disponible = producto[0]

    if 'carrito' not in session:
        session['carrito'] = {}
        

    cantidad_actual = session['carrito'].get(llave_producto, 0)


    if cantidad_actual + 1 > stock_disponible:
        flash(f"¡Ups! Solo nos quedan {stock_disponible} piezas en existencia.", "danger")
        return redirect(request.referrer or url_for('catalogo'))
   


    if llave_producto in session['carrito']:
        session['carrito'][llave_producto] += 1
    else:
        session['carrito'][llave_producto] = 1
        
    session.modified = True 
    flash(f'¡Jersey talla {talla} agregado al carrito!', 'success') 
    return redirect(url_for('mi_carrito'))

# RUTA PARA ACTUALIZAR CANTIDADES (Desde la vista del carrito)
@app.route('/actualizar_carrito/<string:accion>/<string:id_llave>')
def actualizar_carrito(accion, id_llave):
    if 'carrito' not in session:
        return redirect(url_for('mi_carrito'))
    
    if id_llave in session['carrito']:
        if accion == 'sumar':

            p_id = id_llave.split('_')[0] 
            
            cur = mysql.connection.cursor()
            cur.execute("SELECT p_stock FROM productos WHERE p_id = %s", (p_id,))
            producto = cur.fetchone()
            cur.close()
            
            stock_disponible = producto[0] if producto else 0
            cantidad_actual = session['carrito'][id_llave]
            
            if cantidad_actual + 1 > stock_disponible:
                flash(f"Límite alcanzado. Solo hay {stock_disponible} en stock.", "warning")
            else:
                session['carrito'][id_llave] += 1
           
        
        elif accion == 'restar':
            if session['carrito'][id_llave] > 1:
                session['carrito'][id_llave] -= 1
            else:
                session['carrito'].pop(id_llave)
        
        elif accion == 'eliminar':
            session['carrito'].pop(id_llave)
            
        session.modified = True
        
    return redirect(url_for('mi_carrito'))

# RUTA FINAL: PROCESAR LA COMPRA
@app.route('/procesar_compra', methods=['POST'])
@login_requerido
def procesar_compra():
    datos = session.get('checkout_datos')
    carrito_dict = session.get('carrito', {})

    if not datos or not carrito_dict:
        flash("Hubo un error o tu carrito está vacío.", "danger")
        return redirect(url_for('mi_carrito'))

    cur = mysql.connection.cursor()
    try:
        total_pagar = 0
        detalles_a_insertar = []

      
        for llave_compuesta, cantidad in carrito_dict.items():
            partes = llave_compuesta.split('_')
            p_id = partes[0]
            talla = partes[1] if len(partes) > 1 else 'Única'

            cur.execute("SELECT p_precio FROM productos WHERE p_id = %s", (p_id,))
            producto = cur.fetchone()

            if producto:
                precio_unitario = float(producto[0])
                total_pagar += precio_unitario * cantidad
                detalles_a_insertar.append((p_id, talla, cantidad, precio_unitario))

        direccion_con_tel = f"{datos['calle']}, Col. {datos['colonia']}, CP: {datos['cp']}, {datos['ciudad']}, {datos['estado']}. Tel: {datos['telefono']}"

        
        sql_pedido = """
            INSERT INTO pedidos (id_user, direccion_envio, total_pagado, estado, fecha_pedido) 
            VALUES (%s, %s, %s, 'Pendiente', NOW())
        """
        cur.execute(sql_pedido, (session['usuario_id'], direccion_con_tel, total_pagar))
        id_pedido_nuevo = cur.lastrowid

        
        sql_detalles = """
            INSERT INTO detalles_pedido (id_pedido, p_id, talla, cantidad, precio_unitario) 
            VALUES (%s, %s, %s, %s, %s)
        """
        sql_stock = "UPDATE productos SET p_stock = p_stock - %s WHERE p_id = %s"

        for p_id, talla, cantidad, precio in detalles_a_insertar:
            cur.execute(sql_detalles, (id_pedido_nuevo, p_id, talla, cantidad, precio))
            cur.execute(sql_stock, (cantidad, p_id))

        
        mysql.connection.commit()


        try:

            cur.execute("SELECT mail_user, name_user FROM usuarios WHERE id_user = %s", (session['usuario_id'],))
            cliente = cur.fetchone()
            
            if cliente:
                correo_destino = cliente[0]
                nombre_cliente = cliente[1]
                
          
                msg = Message(
                    subject=f"Confirmación de Pedido #{id_pedido_nuevo} - Mi Tienda",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[correo_destino]
                )
                
              
                msg.body = f"""
                ¡Hola {nombre_cliente}! 
                
                Gracias por tu compra. Hemos recibido tu pedido exitosamente.
                
                Detalles del Pedido:
                ------------------------------------------
                Número de Orden: #{id_pedido_nuevo}
                Total Pagado: ${total_pagar:.2f}
                Dirección de Envío: {direccion_con_tel}
                ------------------------------------------
                
                Te avisaremos por este medio cuando tu paquete sea enviado.
                
                ¡Gracias por confiar en nosotros!
                """
                
             
                mail.send(msg)
                print(f"Correo enviado exitosamente a {correo_destino}")

        except Exception as e_mail:

            print(f"Error al enviar correo: {str(e_mail)}")
     

  
        session.pop('carrito', None)
        session.pop('checkout_datos', None)

        flash("¡Compra realizada con éxito! Revisa tu correo electrónico.", "success")
        return render_template('compra_exitosa.html', id_pedido=id_pedido_nuevo)

    except Exception as e:
        mysql.connection.rollback()
        print(f"ERROR EN COMPRA: {str(e)}")
        flash("Hubo un problema al procesar tu pedido.", "danger")
        return redirect(url_for('mi_carrito'))
    finally:
        cur.close()

#-----TERMINAN FUNCIONES DEL CARRITO DE COMPRAS-----

#-----FUNCIOENES DE LOGIN-----

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        cemail = request.form.get('cUsuario')
        cpass = request.form.get('cpass')

        if cemail and cpass:
            cursor = mysql.connection.cursor()

            cursor.execute("SELECT * FROM usuarios WHERE mail_user = %s", (cemail,))
            usuario = cursor.fetchone()
            cursor.close()

            if usuario:
               
                if check_password_hash(usuario[6], cpass):
                    
                    estado_usuario = usuario[9] 
                    
                  
                    if estado_usuario == 0:
                        # --- EL USUARIO ESTÁ APAGADO ---
                        session['id_reactivar'] = usuario[0]
                        return render_template('reactivar_cuenta.html', nombre=usuario[1])
                    
                    else:
                  
                        session['usuario_id'] = usuario[0]
                        session['usuario_rol'] = usuario[10] 
                        flash("Inicio de sesión exitoso", "success")
                    
                       
                        if session['usuario_rol'] == 'admin':
                            return redirect(url_for('tabla_productos'))
                        else:
                            return redirect(url_for('index'))
                else:
                    flash("Contraseña incorrecta", "danger")
            else:
                flash("Correo electrónico incorrecto o el usuario no existe", "danger")
        else:
            flash("Por favor, llena todos los campos", "warning")

    return render_template("login.html")

# RUTA PARA CERRAR SESIÓN
@app.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión exitosamente.", "success")
    return redirect(url_for('index'))

#-----TERMINAN FUNCIOENES DE LOGIN-----

# MANEJADOR DE ERRORES (404 Página no encontrada)
@app.errorhandler(404)
def pagina_no_encontrada(e):
   
    return render_template('404.html'), 404

#-----FUNCIONES CHECKOUT-----
@app.route('/checkout')
@login_requerido
def checkout():
    cur = mysql.connection.cursor()
    cur.execute("SELECT calle, colonia, cp, ciudad, estado FROM usuarios WHERE id_user = %s", (session['usuario_id'],))
    user_address = cur.fetchone()
    cur.close()
    return render_template('checkout_direccion.html', user_address=user_address)

#PAGO (Recibe dirección, muestra tarjeta)
@app.route('/checkout/pago', methods=['POST'])
@login_requerido
def checkout_pago():
    session['checkout_datos'] = {
        'calle': request.form.get('calle'),
        'telefono': request.form.get('telefono'),
        'colonia': request.form.get('colonia'),
        'cp': request.form.get('cp'),
        'ciudad': request.form.get('ciudad'),
        'estado': request.form.get('estado')
    }
    return render_template('checkout_pago.html')

#CONFIRMAR (Muestra resumen antes de finalizar)
@app.route('/checkout/confirmar', methods=['POST'])
@login_requerido
def checkout_confirmar():
    carrito_dict = session.get('carrito', {})
    productos_carrito = []
    total_pagar = 0

    cur = mysql.connection.cursor()

    for llave_compuesta, cantidad in carrito_dict.items():
     
        partes = llave_compuesta.split('_')
        p_id = partes[0]
        talla = partes[1] if len(partes) > 1 else 'Única'

        
        cur.execute("SELECT p_name, p_precio FROM productos WHERE p_id = %s", (p_id,))
        producto = cur.fetchone()

        if producto:
            p_nombre = producto[0]
            precio = float(producto[1])
            subtotal = precio * cantidad
            total_pagar += subtotal

            
            productos_carrito.append({
                'p_nombre': f"{p_nombre} (Talla {talla})",
                'cantidad': cantidad,
                'p_precio': precio,
                'subtotal': subtotal
            })

    cur.close()

    return render_template('checkout_confirmar.html', 
                           datos=session.get('checkout_datos'), 
                           total_pagar=total_pagar,
                           carrito=productos_carrito)

#-----TERMINAN FUNCIONES CHECKOUT-----

# Configuracion de la aplicacion
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8088, debug=False)
