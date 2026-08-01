# SNGS Terminal — Buscador de canciones vía Telegram

Página web con estilo "hacker/terminal" que te permite escribir un mensaje,
enviarlo automáticamente al bot de Telegram **@Sngs_for_you_Bot**, y ver su
respuesta en pantalla, sin tener que abrir Telegram tú mismo.

---

## ⚠️ Léeme primero: cómo funciona esto por dentro (importante)

Telegram no tiene ninguna forma de "iniciar sesión con un bot" para hablar
con otro bot desde una web externa. La única manera de conseguir que algo
le escriba a `@Sngs_for_you_Bot` y lea su respuesta es conectarse a Telegram
**como si fueras tú mismo**, usando tu propia cuenta (igual que Telegram Web
o Telegram Desktop). Por eso esta página te pide:

- Tu **API ID** y **API Hash** (dos códigos que se obtienen gratis en
  [my.telegram.org](https://my.telegram.org), son como una "llave" que
  Telegram te da para que tus propios programas puedan usar tu cuenta).
- Tu **número de teléfono**.
- El **código de verificación** que te llegará a la propia app de Telegram.
- Tu **contraseña de verificación en dos pasos**, solo si la tienes activada.

Esto es exactamente la misma información que pedirías si programases tú
mismo un script en Python para automatizar tu cuenta. **No es la contraseña
de tu cuenta de Telegram** (Telegram no usa contraseña normal, solo el
código + opcionalmente esa contraseña de doble factor).

### 🔒 Por qué esto es seguro (si sigues estas reglas) y por qué NO lo es si no las sigues

Esta misma pantalla de login, si estuviera colgada en un servidor de
internet controlado por otra persona, sería **idéntica a una página de
phishing** (roban tu código y entran en tu cuenta). Para que eso nunca
pase con esta aplicación:

1. **Solo úsala en tu propio ordenador**, abriendo `http://127.0.0.1:5000`
   (127.0.0.1 significa "esta misma máquina", nadie más puede acceder a
   esa dirección desde fuera).
2. **No la subas a un hosting público** (Render, Vercel, un VPS, etc.) tal
   y como está. Si algún día quieres hacerlo, habría que añadir antes:
   usuario/contraseña propios de la web, conexión HTTPS, y no compartir
   el enlace con nadie.
3. **No compartas tu API_ID / API_HASH** con nadie, ni los subas a GitHub.
   El archivo `.gitignore` incluido ya evita que las sesiones (carpeta
   `sessions/`) se suban por error.
4. Toda la comunicación con Telegram va directa a los servidores oficiales
   de Telegram. Esta aplicación no envía tus datos a ningún otro sitio.
5. Si quieres revocar el acceso en cualquier momento, hay un botón
   **"CERRAR SESIÓN"** en la propia página, o puedes hacerlo desde
   Telegram: Ajustes → Dispositivos.

---

## 📁 Qué hay en esta carpeta

```
telegram-song-bot/
├── app.py                 → El backend (servidor) en Python/Flask
├── requirements.txt       → Lista de librerías de Python necesarias
├── templates/
│   └── index.html         → El HTML de la página
├── static/
│   ├── style.css          → Los estilos (el aspecto "hacker")
│   └── script.js          → La lógica del navegador (JavaScript)
├── sessions/              → Aquí se guardará tu sesión de Telegram
│                             (se crea sola, no la toques)
├── archivos_bot/          → Archivos que te mande el bot (ej. el .html
│                             de "descargar letra"); se crea sola
└── .gitignore             → Evita subir por error datos sensibles
```

---

## 🚀 Instalación paso a paso

### 1. Instala Python

Si no lo tienes, descárgalo desde [python.org](https://www.python.org/downloads/)
(cualquier versión 3.9 o superior sirve). Durante la instalación en
Windows, marca la casilla **"Add Python to PATH"**.

### 2. Consigue tu API ID y API Hash

1. Entra en [https://my.telegram.org](https://my.telegram.org) e inicia
   sesión con tu número de teléfono (te pedirá un código, es normal, es la
   propia web oficial de Telegram).
2. Ve a **"API development tools"**.
3. Rellena el formulario (puedes poner cualquier nombre, por ejemplo "Mi
   app de canciones") y pulsa crear.
4. Te aparecerán dos datos: **App api_id** y **App api_hash**. Guárdalos,
   los necesitarás al abrir la página.

### 3. Abre una terminal (línea de comandos) en esta carpeta

- **Windows**: abre la carpeta en el Explorador, escribe `cmd` en la barra
  de direcciones y pulsa Enter.
- **Mac**: abre "Terminal" y escribe `cd ` (con un espacio) y arrastra la
  carpeta del proyecto encima, luego Enter.

### 4. Instala las librerías necesarias

Escribe este comando y pulsa Enter:

```bash
pip install -r requirements.txt
```

Esto instala automáticamente **Flask** (para crear la página web) y
**Telethon** (para conectarse a Telegram). Solo hace falta hacerlo una vez.

### 5. Arranca el servidor

```bash
python app.py
```

Verás un mensaje parecido a `Running on http://127.0.0.1:5000`. Eso
significa que ya está funcionando.

### 6. Abre la página

Abre tu navegador (Chrome, Firefox...) y entra en:

```
http://127.0.0.1:5000
```

---

## 🖥️ Cómo se usa

1. **Pantalla de conexión**: escribe tu `API_ID`, `API_HASH` y tu número de
   teléfono con el prefijo del país (ej: `+34600000000`) y pulsa
   **CONECTAR**.
2. **Código de verificación**: revisa tu Telegram (te llegará un mensaje,
   normalmente del chat "Telegram"), escribe el código y pulsa
   **VERIFICAR**. Si tu cuenta tiene activada la verificación en dos pasos,
   te pedirá también esa contraseña.
3. **Buscador**: escribe lo que quieras preguntarle al bot en el campo
   "Buscar" y pulsa Enter. La respuesta del bot aparecerá debajo, con una
   animación de escritura tipo terminal. Cada búsqueda (y cada botón que
   pulses después) se muestra en su propio bloque, uno debajo del otro,
   para que quede todo ordenado.
4. **Botones del bot**: si la respuesta trae botones (paginación, menús,
   "descargar letra", etc.), aparecerán debajo del texto, uno por línea,
   y son pulsables igual que en Telegram. Al pulsar uno, se envía el aviso
   a Telegram y el resultado (más texto, más botones, o un archivo) se
   muestra en un nuevo bloque debajo. Si el botón es un enlace, se abre en
   una pestaña nueva. Si el bot manda un archivo `.html` (por ejemplo al
   pulsar "descargar letra"), se guarda en la carpeta `archivos_bot/` y se
   abre automáticamente en una pestaña nueva.
5. La sesión queda guardada en la carpeta `sessions/`, así que la próxima
   vez que abras la página no tendrás que volver a meter el código.
6. Si quieres desconectar tu cuenta de esta app, pulsa
   **CERRAR SESIÓN**.

---

## 🧩 Cómo está organizado el código (para curiosos)

- **`app.py`** es el "cerebro": recibe lo que escribes en la web, habla con
  Telegram usando la librería Telethon, y devuelve las respuestas. Cada
  función tiene comentarios explicando qué hace.
- **`templates/index.html`** define las tres pantallas de la web (login,
  código, buscador) y qué botones e inputs hay en cada una.
- **`static/script.js`** es lo que se ejecuta en tu navegador: cambia de
  pantalla, llama al backend cuando pulsas los botones, y dibuja la
  animación de fondo tipo "lluvia de caracteres".
- **`static/style.css`** solo define colores, tipografía y animaciones
  (el aspecto visual), no tiene ninguna lógica.

---

## ❓ Problemas comunes

- **"No se pudo conectar"**: revisa que el API_ID y API_HASH sean
  correctos y que el teléfono incluya el prefijo del país con el `+`.
- **"El código introducido no es correcto"**: a veces Telegram tarda unos
  segundos en enviarlo, espera y prueba el código más reciente.
- **"El bot no respondió a tiempo"**: el bot puede tardar más de 20
  segundos según su carga; simplemente vuelve a intentarlo. Esto también
  puede pasar al pulsar un botón si el bot tarda en procesar el "callback".
- **Un botón deja de funcionar / "Ese botón ya no está disponible"**: esto
  pasa si has hecho otra búsqueda o pulsado otro botón más reciente
  mientras tanto; la app solo recuerda los botones del último mensaje. Usa
  siempre los botones del bloque más reciente.
- Si quieres empezar de cero (borrar tu sesión guardada), cierra sesión
  desde la página o borra manualmente los archivos dentro de la carpeta
  `sessions/`.
