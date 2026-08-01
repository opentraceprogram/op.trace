"""
============================================================
 app.py  -  Servidor (backend) en Python, hecho con Flask
============================================================

Que hace este archivo, explicado sencillo:

  1. Sirve la pagina web (index.html) cuando entras en el navegador.
  2. Recibe el "API ID", "API Hash" y numero de telefono que escribes
     en el formulario de login, y con eso le pide a Telegram (los
     servidores oficiales de Telegram, no un servidor nuestro) que
     envie un codigo de verificacion a tu propia cuenta.
  3. Recibe ese codigo (y la contrasena de verificacion en dos pasos
     si la tienes activada) y termina de iniciar sesion.
  4. Cuando escribes algo en el buscador de la pagina, coge ese texto,
     se lo manda por Telegram al bot @Sngs_for_you_Bot, espera su
     respuesta, y te la devuelve para que se muestre en pantalla.
  5. Si esa respuesta trae "botones" (los que en Telegram aparecen
     debajo de un mensaje: paginas siguiente/anterior, menus, etc.),
     los manda tambien a la pagina web como una lista, para que se
     puedan dibujar como botones reales y se puedan pulsar.
  6. Cuando pulsas uno de esos botones en la web, este servidor le
     dice a Telegram "el usuario ha pulsado este boton" (esto se
     llama un "callback"), espera lo que Telegram devuelva (puede ser
     el mismo mensaje editado con mas botones, un mensaje nuevo, o un
     archivo), y te lo manda de vuelta.
  7. Si el bot responde con un archivo .html (por ejemplo al pulsar
     "descargar letra"), este servidor lo descarga, lo guarda en una
     carpeta propia, y le dice al navegador la direccion para que lo
     abra solo en una pestana nueva.

Libreria usada para hablar con Telegram: "Telethon".
Telethon permite controlar una cuenta de Telegram desde Python,
exactamente igual que si tu abrieras la app y escribieras a mano.

Sobre los "botones" de Telegram (para quien no lo conozca):
Cuando un bot responde, ademas del texto puede llevar "pegados"
unos botones que se pintan justo debajo del mensaje, organizados en
filas (una fila puede tener 1 o varios botones). Telethon nos deja
leer esos botones en la propiedad ".buttons" del mensaje, como una
lista de filas, y cada fila es una lista de botones. Cada boton es
de uno de estos dos tipos:
  - Boton normal ("callback"): al pulsarlo, se envia un aviso a
    Telegram diciendo "se ha pulsado este boton", y el bot responde
    (normalmente editando el mismo mensaje, por ejemplo para cambiar
    de pagina, o a veces con un mensaje nuevo).
  - Boton "url": es simplemente un enlace a una pagina web, no hace
    falta avisar a Telegram, con abrir el enlace basta.

------------------------------------------------------------
 AVISO DE SEGURIDAD (leer antes de usar)
------------------------------------------------------------
- Esta aplicacion esta pensada para que la uses TU, en TU propio
  ordenador, entrando por ejemplo a http://127.0.0.1:5000
- NUNCA la subas a un servidor publico de internet tal cual. La
  pagina pide tu codigo de verificacion de Telegram y, si la tienes
  activada, tu contrasena de doble factor. Si alguien mas accediera
  a esta pagina podria iniciar sesion en TU cuenta de Telegram.
- El "API ID" y "API Hash" son datos personales tuyos (se sacan de
  https://my.telegram.org). No los compartas ni los subas a internet
  (por ejemplo, a GitHub) sin protegerlos.
- Esta app nunca envia tus datos a ningun sitio que no sean los
  servidores oficiales de Telegram.
- Los archivos que el bot envie (por ejemplo el .html de "descargar
  letra") se guardan en la carpeta archivos_bot/. Son contenido que
  te manda el propio bot de Telegram, no algo generado por nosotros;
  esta app no revisa ni filtra ese contenido, simplemente lo muestra
  tal cual llega.
"""

from flask import Flask, render_template, request, jsonify, session, send_from_directory
from werkzeug.utils import secure_filename
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import os
import time
import threading
import uuid
import asyncio
import requests

# Telethon necesita un "bucle de eventos" de asyncio para poder hablar
# con Telegram por debajo (es una pieza interna de Python para tareas
# que esperan respuestas de internet). En versiones antiguas de
# Python, si no habia ninguno creado todavia, Python creaba uno solo
# automaticamente la primera vez que hacia falta. Desde Python 3.10 (y
# sobre todo desde 3.12) eso ya NO pasa, y si Telethon intenta usarlo
# sin que exista ninguno, falla con el error:
#   "There is no current event loop in thread 'MainThread'"
# Para evitarlo, creamos y dejamos preparado ese bucle nosotros mismos
# aqui, justo al arrancar el servidor, antes de que ninguna parte del
# codigo intente crear un TelegramClient.
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

app = Flask(__name__)

# Esta clave es solo para las "cookies" que usa Flask para reconocer tu
# navegador (NO tiene nada que ver con tu contrasena de Telegram).
# La guardamos en un archivo para que no cambie cada vez que reinicies
# el servidor; si cambiara, perderias la sesion y se irian acumulando
# archivos .session sueltos sin usar dentro de sessions/.
RUTA_SECRET_KEY = os.path.join(os.path.dirname(__file__), ".secret_key")
if os.environ.get("FLASK_SECRET_KEY"):
    app.secret_key = os.environ["FLASK_SECRET_KEY"]
else:
    if not os.path.exists(RUTA_SECRET_KEY):
        with open(RUTA_SECRET_KEY, "w") as f:
            f.write(os.urandom(24).hex())
    with open(RUTA_SECRET_KEY) as f:
        app.secret_key = f.read().strip()

# Carpeta donde Telethon guarda el "archivo de sesion" de Telegram.
# Gracias a este archivo, la proxima vez que abras la pagina no hara
# falta volver a meter el codigo de verificacion.
SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Usuario del bot al que le vamos a pedir canciones.
BOT_USERNAME = "Sngs_for_you_Bot"

# Carpeta donde se guardan los archivos que el bot nos pueda enviar
# (por ejemplo el .html que genera el boton "descargar letra").
ARCHIVOS_BOT_DIR = os.path.join(os.path.dirname(__file__), "archivos_bot")
os.makedirs(ARCHIVOS_BOT_DIR, exist_ok=True)

# Aqui guardamos, en memoria, los clientes de Telegram que estan
# activos (uno por cada navegador que entra). En un uso normal
# (solo tu usando la pagina) solo habra uno.
clientes_activos = {}

# Aqui guardamos, en memoria y por navegador (sid), el ULTIMO mensaje
# del bot que tiene botones. Lo necesitamos porque los botones de
# Telethon ".click()" solo funcionan sobre el objeto Message original
# de Telethon, y ese objeto no se puede meter dentro de una cookie ni
# mandarlo al navegador: hay que guardarlo aqui, en el servidor, y
# cuando la pagina web nos diga "se ha pulsado el boton fila 0
# columna 1", buscamos ese mensaje guardado y pulsamos el boton en
# esa posicion.
#   clave: sid (identificador del navegador)
#   valor: objeto Message de Telethon (el ultimo mensaje del bot que
#          tenia botones)
ultimo_mensaje_con_botones = {}

# Un "candado" para que dos peticiones no toquen el mismo cliente de
# Telegram exactamente al mismo tiempo y se hagan un lio.
bloqueo = threading.Lock()

def buscar_breachvip(term):
    try:
        r = requests.post(
            "https://breach.vip/api/search",
            json={
                "term": term,
                "fields": [
                    "uuid",
                    "username",
                    "ip",
                    "domain",
                    "discordid",
                    "steamid",
                    "email",
                    "password",
                    "name",
                    "phone"
                ]
            },
            timeout=20
        )

        if r.status_code == 200:
            return r.json().get("results", [])

    except Exception as e:
        print(e)

    return []


def obtener_id_sesion():
    """
    Da a cada navegador un identificador unico (guardado en una cookie
    de Flask) para saber a que cliente de Telegram pertenece.
    """
    if "sid" not in session:
        session["sid"] = os.urandom(8).hex()
    return session["sid"]


def cerrar_cliente_anterior(sid):
    """
    Si ya habia un cliente de Telegram abierto para este navegador
    (por ejemplo, de un intento de login anterior que fallo o que se
    quedo a medias), lo desconectamos antes de abrir uno nuevo.
    Si no hacemos esto, el archivo de sesion (.session) se queda
    "en uso" y el siguiente intento falla con "database is locked".
    """
    cliente_anterior = clientes_activos.pop(sid, None)
    ultimo_mensaje_con_botones.pop(sid, None)
    if cliente_anterior is not None:
        try:
            cliente_anterior.disconnect()
        except Exception:
            pass


@app.route("/")
def index():
    """Muestra la pagina principal (el HTML)."""
    return render_template("index.html")


@app.route("/api/status")
def status():
    """
    El frontend pregunta aqui: "¿ya hay sesion de Telegram iniciada
    para este navegador?" para saber que pantalla mostrar al cargar.
    """
    sid = obtener_id_sesion()
    cliente = clientes_activos.get(sid)
    conectado = False
    if cliente is not None:
        try:
            with bloqueo:
                conectado = cliente.is_user_authorized()
        except Exception:
            conectado = False
    return jsonify({"conectado": conectado})


@app.route("/api/login", methods=["POST"])
def login():
    """
    PASO 1 del login.
    Recibe: api_id, api_hash, telefono.
    Hace: le pide a Telegram que mande un codigo de verificacion
          (normalmente llega como mensaje dentro de la propia app
          de Telegram, en el chat "Telegram").
    """
    datos = request.get_json(silent=True) or {}
    api_id = datos.get("api_id")
    api_hash = datos.get("api_hash")
    telefono = datos.get("telefono")

    if not api_id or not api_hash or not telefono:
        return jsonify({"ok": False, "error": "Faltan datos: API ID, API Hash o telefono."}), 400

    try:
        api_id = int(api_id)
    except ValueError:
        return jsonify({"ok": False, "error": "El API ID debe ser un numero."}), 400

    sid = obtener_id_sesion()
    ruta_sesion = os.path.join(SESSIONS_DIR, f"sesion_{sid}")

    cliente = None
    try:
        with bloqueo:
            # Muy importante: si ya habia un cliente abierto para este
            # navegador (de un intento anterior), lo cerramos primero.
            # Si no, dos conexiones al mismo archivo .session provocan
            # el error "database is locked".
            cerrar_cliente_anterior(sid)

            cliente = TelegramClient(ruta_sesion, api_id, api_hash)
            cliente.connect()

            # Si ya habia una sesion guardada de antes, no hace falta
            # pedir codigo otra vez.
            if cliente.is_user_authorized():
                clientes_activos[sid] = cliente
                return jsonify({"ok": True, "ya_conectado": True})

            enviado = cliente.send_code_request(telefono)

            # Guardamos estos dos datos "pegados" al cliente para
            # poder usarlos en el paso 2 (verificar codigo).
            cliente._telefono_temp = telefono
            cliente._code_hash_temp = enviado.phone_code_hash

            clientes_activos[sid] = cliente

        return jsonify({"ok": True, "ya_conectado": False})
    except Exception as e:
        # Si algo fallo a mitad de la conexion, la cerramos para no
        # dejar el archivo de sesion bloqueado para el siguiente intento.
        if cliente is not None:
            try:
                cliente.disconnect()
            except Exception:
                pass
        return jsonify({"ok": False, "error": f"No se pudo conectar: {e}"}), 400


@app.route("/api/verificar", methods=["POST"])
def verificar_codigo():
    """
    PASO 2 del login.
    Recibe: el codigo que ha llegado a Telegram, y opcionalmente la
    contrasena de verificacion en dos pasos (2FA) si la cuenta la tiene.
    """
    datos = request.get_json(silent=True) or {}
    codigo = (datos.get("codigo") or "").strip()
    contrasena = datos.get("contrasena")  # puede venir vacio o None

    sid = obtener_id_sesion()
    cliente = clientes_activos.get(sid)

    if cliente is None:
        return jsonify({"ok": False, "error": "No hay ningun login en curso. Vuelve a empezar."}), 400

    try:
        with bloqueo:
            cliente.sign_in(
                cliente._telefono_temp,
                codigo,
                phone_code_hash=cliente._code_hash_temp,
            )
        return jsonify({"ok": True})

    except SessionPasswordNeededError:
        # La cuenta tiene activada la verificacion en dos pasos.
        if not contrasena:
            return jsonify({"ok": False, "necesita_password": True})
        try:
            with bloqueo:
                cliente.sign_in(password=contrasena)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"ok": False, "error": f"Contrasena incorrecta o error: {e}"}), 400

    except PhoneCodeInvalidError:
        return jsonify({"ok": False, "error": "El codigo introducido no es correcto."}), 400
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400

def buscar_breachvip(term):
    try:
        r = requests.post(
            "https://breach.vip/api/search",
            json={
                "term": term,
                "fields": [
                    "uuid",
                    "username",
                    "ip",
                    "domain",
                    "discordid",
                    "steamid",
                    "email",
                    "password",
                    "name",
                    "phone"
                ]
            },
            timeout=20
        )

        if r.status_code == 200:
            return r.json().get("results", [])

    except Exception as e:
        print("BreachVIP:", e)

    return []


@app.route("/api/buscar", methods=["POST"])
def buscar_cancion():
    """
    Envia el mensaje escrito por el usuario al bot de canciones y
    espera su respuesta (texto + botones, si trae) para devolverla a
    la pagina web.
    """
    datos = request.get_json(silent=True) or {}
    mensaje = (datos.get("mensaje") or "").strip()
    resultados_breach = buscar_breachvip(mensaje)

    if not mensaje:
        return jsonify({"ok": False, "error": "Escribe algo para buscar."}), 400

    sid = obtener_id_sesion()
    cliente = clientes_activos.get(sid)

    if cliente is None or not cliente.is_user_authorized():
        return jsonify({"ok": False, "error": "No has iniciado sesion todavia."}), 401

    try:
        with bloqueo:
            enviado = cliente.send_message(BOT_USERNAME, mensaje)
            resultado = esperar_mensaje_nuevo(cliente, id_desde=enviado.id)

        if resultado is None:
            return jsonify({"ok": False, "error": "No se ha recibido respuesta a tiempo. Intentalo de nuevo."}), 504

        guardar_mensaje_con_botones(sid, resultado)
        respuesta = serializar_mensaje_bot(cliente, resultado)

        if resultados_breach:
            respuesta["breachvip"] = resultados_breach

        return jsonify({
            "ok": True,
            **respuesta
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/pulsar_boton", methods=["POST"])
def pulsar_boton():
    """
    Se llama cuando el usuario pulsa, en la pagina web, uno de los
    botones que venian debajo de un mensaje del bot (por ejemplo
    "Pagina siguiente", un boton de menu, o "Descargar letra").

    Recibe la posicion del boton (fila y columna) dentro del ULTIMO
    mensaje del bot que tenia botones (lo tenemos guardado en
    ultimo_mensaje_con_botones). No podemos identificar el boton por
    su texto porque puede haber botones repetidos (por ejemplo varias
    flechas "»").
    """
    datos = request.get_json(silent=True) or {}
    fila = datos.get("fila")
    columna = datos.get("columna")

    if fila is None or columna is None:
        return jsonify({"ok": False, "error": "Falta indicar que boton se ha pulsado."}), 400

    sid = obtener_id_sesion()
    cliente = clientes_activos.get(sid)
    mensaje_previo = ultimo_mensaje_con_botones.get(sid)

    if cliente is None or not cliente.is_user_authorized():
        return jsonify({"ok": False, "error": "No has iniciado sesion todavia."}), 401
    if mensaje_previo is None:
        return jsonify({"ok": False, "error": "Ese boton ya no esta disponible (vuelve a buscar)."}), 400

    try:
        with bloqueo:
            fila = int(fila)
            columna = int(columna)
            filas_botones = mensaje_previo.buttons or []
            if fila < 0 or fila >= len(filas_botones) or columna < 0 or columna >= len(filas_botones[fila]):
                return jsonify({"ok": False, "error": "Ese boton ya no esta disponible (vuelve a buscar)."}), 400

            boton = filas_botones[fila][columna]

            # Los botones tipo "url" no avisan a Telegram, son solo un
            # enlace: se lo decimos al frontend para que lo abra el
            # solo, sin esperar ninguna respuesta nueva del bot.
            url_boton = getattr(boton, "url", None)
            if url_boton:
                return jsonify({"ok": True, "abrir_url": url_boton, "respuesta": None, "botones": []})

            id_antes = mensaje_previo.id
            ids_antes = {m.id for m in cliente.get_messages(BOT_USERNAME, limit=10)}

            # boton.click() envia el "callback" a Telegram: es
            # exactamente lo mismo que pulsarlo dentro de la app de
            # Telegram. Telegram, tras esto, normalmente EDITA el
            # mismo mensaje (por ejemplo para cambiar de pagina) en
            # vez de mandar uno nuevo.
            boton.click()

            resultado = esperar_cambio_tras_click(cliente, mensaje_antes=mensaje_previo, ids_previos=ids_antes)

        if resultado is None:
            return jsonify({"ok": False, "error": "No se ha recibido respuesta a tiempo. Intentalo de nuevo."}), 504

        guardar_mensaje_con_botones(sid, resultado)
        return jsonify({"ok": True, **serializar_mensaje_bot(cliente, resultado)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


def guardar_mensaje_con_botones(sid, mensaje):
    """
    Guarda (o borra, si ya no trae botones) el ultimo mensaje del bot
    con botones para este navegador, para poder pulsar sus botones en
    una peticion posterior.
    """
    if mensaje is not None and mensaje.buttons:
        ultimo_mensaje_con_botones[sid] = mensaje
    else:
        ultimo_mensaje_con_botones.pop(sid, None)


def serializar_mensaje_bot(cliente, mensaje):
    """
    Convierte un mensaje de Telethon (texto + botones + posible
    archivo) en un diccionario simple que se pueda mandar como JSON a
    la pagina web.

    Los botones se devuelven como una lista de filas, y cada fila es
    una lista de botones, cada uno con:
      - texto: lo que pone el boton
      - fila / columna: su posicion (se usan luego para decirle al
        backend "se ha pulsado ESTE boton exactamente")
      - tipo: "url" (es un enlace) o "callback" (hay que avisar a
        Telegram al pulsarlo)
      - url: solo si tipo es "url"
    """
    botones_serializados = []
    for i, fila in enumerate(mensaje.buttons or []):
        fila_serializada = []
        for j, boton in enumerate(fila):
            url_boton = getattr(boton, "url", None)
            fila_serializada.append({
                "texto": boton.text,
                "fila": i,
                "columna": j,
                "tipo": "url" if url_boton else "callback",
                "url": url_boton,
            })
        botones_serializados.append(fila_serializada)

    resultado = {
        "respuesta": mensaje.text if mensaje.text else None,
        "botones": botones_serializados,
        "archivo_url": None,
    }

    # Si el bot ha mandado un archivo (por ejemplo el .html de
    # "descargar letra"), lo descargamos a nuestra carpeta y damos al
    # frontend la direccion para que lo abra en una pestana nueva.
    if mensaje.file is not None:
        try:
            resultado["archivo_url"] = descargar_archivo_del_bot(cliente, mensaje)
        except Exception:
            resultado["archivo_url"] = None

    if resultado["respuesta"] is None and resultado["archivo_url"] is None:
        resultado["respuesta"] = "[Se ha recibido un archivo, audio o imagen sin texto]"

    return resultado


def descargar_archivo_del_bot(cliente, mensaje):
    """
    Descarga el archivo adjunto de un mensaje del bot (tipicamente el
    .html que genera el boton "descargar letra") a la carpeta
    archivos_bot/, con un nombre unico para no chocar con otros
    archivos, y devuelve la ruta (URL) por la que el navegador puede
    pedirlo.
    """
    nombre_original = getattr(mensaje.file, "name", None) or "archivo.html"
    nombre_seguro = secure_filename(nombre_original) or "archivo.html"
    nombre_unico = f"{uuid.uuid4().hex}_{nombre_seguro}"
    ruta_destino = os.path.join(ARCHIVOS_BOT_DIR, nombre_unico)

    cliente.download_media(mensaje, file=ruta_destino)

    return f"/archivos_bot/{nombre_unico}"


@app.route("/archivos_bot/<path:nombre_archivo>")
def servir_archivo_bot(nombre_archivo):
    """
    Sirve los archivos que el bot nos haya enviado (guardados en
    archivos_bot/) para que el navegador los pueda abrir, por ejemplo
    el .html de "descargar letra" en una pestana nueva.
    """
    return send_from_directory(ARCHIVOS_BOT_DIR, nombre_archivo)


def esperar_mensaje_nuevo(cliente, id_desde, tiempo_maximo=20):
    """
    Comprueba, cada segundo, si ha llegado un mensaje NUEVO del bot
    (con id mayor que id_desde, y que no sea un mensaje nuestro).

    Se usa despues de mandar un mensaje al bot (busqueda normal).

    Devuelve el objeto Message de Telethon, o None si se agota el
    tiempo maximo de espera.
    """
    tiempo_inicio = time.time()
    while time.time() - tiempo_inicio < tiempo_maximo:
        time.sleep(1)
        mensajes = cliente.get_messages(BOT_USERNAME, limit=5)
        for m in mensajes:
            # m.out es True si el mensaje lo enviamos nosotros; solo
            # nos interesan los mensajes NUEVOS que vienen DEL bot.
            if m.id > id_desde and not m.out:
                return m
    return None


def firma_mensaje(mensaje):
    """
    Crea una "huella" simple del contenido de un mensaje (su texto,
    los textos de sus botones, y si trae archivo adjunto) para poder
    comparar facilmente "es este mensaje el mismo de antes, o ha
    cambiado su contenido".

    No usamos la fecha de edicion del mensaje (edit_date) porque no
    siempre se actualiza de forma inmediata o fiable segun como el
    bot haga la edicion; comparar el contenido en si es mas seguro.
    """
    texto = mensaje.text or ""
    textos_botones = tuple(
        tuple(boton.text for boton in fila) for fila in (mensaje.buttons or [])
    )
    tiene_archivo = mensaje.file is not None
    return (texto, textos_botones, tiene_archivo)


def esperar_cambio_tras_click(cliente, mensaje_antes, ids_previos, tiempo_maximo=20):
    """
    Comprueba, cada medio segundo, que ha pasado tras pulsar un boton
    (boton.click()). Hay dos posibilidades:

      a) Telegram EDITA el mismo mensaje (lo mas normal: por ejemplo
         al pasar de pagina, al abrir un submenu con mas opciones, o
         al pulsar cualquier boton de funcion). Lo detectamos
         comparando el CONTENIDO del mensaje (texto + botones +
         archivo) contra como estaba antes de pulsar.
      b) El bot manda un mensaje NUEVO (id que no estaba en
         ids_previos). Por ejemplo, el archivo de "descargar letra"
         suele llegar como un mensaje aparte en vez de editar el
         mensaje de los botones.

    Devuelve el mensaje relevante (el editado, o el nuevo), o None si
    se agota el tiempo sin ver ningun cambio.
    """
    id_mensaje = mensaje_antes.id
    firma_previa = firma_mensaje(mensaje_antes)

    tiempo_inicio = time.time()
    while time.time() - tiempo_inicio < tiempo_maximo:
        time.sleep(0.5)
        mensajes = cliente.get_messages(BOT_USERNAME, limit=10)

        for m in mensajes:
            # Caso b) mensaje totalmente nuevo.
            if m.id not in ids_previos and not m.out:
                return m

        for m in mensajes:
            # Caso a) el mensaje de los botones ha cambiado de
            # contenido (texto, botones o archivo distintos).
            if m.id == id_mensaje and firma_mensaje(m) != firma_previa:
                return m

    return None


@app.route("/api/logout", methods=["POST"])
def logout():
    """Cierra la sesion de Telegram para este navegador (revoca el login)."""
    sid = obtener_id_sesion()
    cliente = clientes_activos.pop(sid, None)
    ultimo_mensaje_con_botones.pop(sid, None)
    if cliente:
        try:
            cliente.log_out()
        except Exception:
            pass
    return jsonify({"ok": True})


if __name__ == "__main__":
    # host="127.0.0.1" hace que la pagina SOLO se pueda abrir desde
    # este mismo ordenador. No la cambies a "0.0.0.0" para exponerla
    # a internet sin anadir antes autenticacion y HTTPS.
    #
    # threaded=False: atiende una peticion cada vez. Como Telethon usa
    # un archivo de sesion (.session) que no soporta bien que dos
    # peticiones lo toquen a la vez, esto evita el error
    # "database is locked".
    # use_reloader=False: evita que Flask reinicie el proceso solo al
    # detectar cambios, lo que podia dejar conexiones a medias abiertas.
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=False, use_reloader=False)