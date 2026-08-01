/* ============================================================
   script.js - Logica del frontend (lo que pasa en el navegador)
   ============================================================
   Este archivo hace tres cosas:
     1. Dibuja la animacion de "lluvia de caracteres" de fondo.
     2. Muestra/oculta las 3 pantallas (login, codigo, buscador).
     3. Llama al backend (app.py) para iniciar sesion en Telegram
        y para enviar/recibir mensajes del bot de canciones.
*/

/* ---------- 1. Animacion de fondo estilo "Matrix" ---------- */
(function dibujarLluviaMatrix() {
  const canvas = document.getElementById("matrix-bg");
  const ctx = canvas.getContext("2d");

  function ajustarTamano() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  ajustarTamano();
  window.addEventListener("resize", ajustarTamano);

  const caracteres = "01ABCDEFGHIJKLMNOPQRSTUVWXYZ$#%&";
  const tamanoFuente = 16;
  let columnas = Math.floor(canvas.width / tamanoFuente);
  let gotas = new Array(columnas).fill(1);

  function dibujarFrame() {
    ctx.fillStyle = "rgba(5, 8, 7, 0.08)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = "#00ff9c";
    ctx.font = tamanoFuente + "px monospace";

    for (let i = 0; i < gotas.length; i++) {
      const letra = caracteres[Math.floor(Math.random() * caracteres.length)];
      ctx.fillText(letra, i * tamanoFuente, gotas[i] * tamanoFuente);

      if (gotas[i] * tamanoFuente > canvas.height && Math.random() > 0.975) {
        gotas[i] = 0;
      }
      gotas[i]++;
    }
  }
  setInterval(dibujarFrame, 50);
})();


/* ---------- 2. Referencias a los elementos de la pagina ---------- */
const pantallaTelefono = document.getElementById("pantalla-telefono");
const pantallaApi = document.getElementById("pantalla-api");
const pantallaCodigo = document.getElementById("pantalla-codigo");
const pantallaBuscar = document.getElementById("pantalla-buscar");

const inputTelefono = document.getElementById("telefono");
const btnContinuar = document.getElementById("btn-continuar");
const errorTelefono = document.getElementById("error-telefono");
const telefonoRecordatorio = document.getElementById("telefono-recordatorio");

const inputApiId = document.getElementById("api_id");
const inputApiHash = document.getElementById("api_hash");
const btnLogin = document.getElementById("btn-login");
const btnVolverTelefono = document.getElementById("btn-volver-telefono");
const errorLogin = document.getElementById("error-login");

const inputCodigo = document.getElementById("codigo");
const inputContrasena = document.getElementById("contrasena");
const labelPassword = document.getElementById("label-password");
const btnVerificar = document.getElementById("btn-verificar");
const errorCodigo = document.getElementById("error-codigo");

const inputMensaje = document.getElementById("mensaje");
const salida = document.getElementById("salida");
const btnLogout = document.getElementById("btn-logout");

function mostrarPantalla(pantalla) {
  [pantallaTelefono, pantallaApi, pantallaCodigo, pantallaBuscar].forEach(p => p.classList.add("oculto"));
  pantalla.classList.remove("oculto");
}

/* Al cargar la pagina, preguntamos al backend si ya hay sesion activa */
window.addEventListener("DOMContentLoaded", async () => {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    if (data.conectado) {
      mostrarPantalla(pantallaBuscar);
      inputMensaje.focus();
    } else {
      mostrarPantalla(pantallaTelefono);
    }
  } catch (e) {
    mostrarPantalla(pantallaTelefono);
  }
});


/* ---------- 3a. Paso 1: solo pedir el telefono ---------- */
btnContinuar.addEventListener("click", () => {
  errorTelefono.textContent = "";
  const telefono = inputTelefono.value.trim();

  if (!telefono) {
    errorTelefono.textContent = "Escribe tu numero de telefono.";
    return;
  }

  telefonoRecordatorio.textContent = telefono;
  mostrarPantalla(pantallaApi);
  inputApiId.focus();
});

btnVolverTelefono.addEventListener("click", () => {
  errorLogin.textContent = "";
  mostrarPantalla(pantallaTelefono);
});

/* ---------- 3b. Paso 2: enviar API_ID / API_HASH (el telefono ya se guardo) ---------- */
btnLogin.addEventListener("click", async () => {
  errorLogin.textContent = "";
  const api_id = inputApiId.value.trim();
  const api_hash = inputApiHash.value.trim();
  const telefono = inputTelefono.value.trim();

  if (!api_id || !api_hash) {
    errorLogin.textContent = "Rellena el API_ID y el API_HASH.";
    return;
  }
  if (!telefono) {
    // Por si el usuario recargo la pagina y perdio el dato, volvemos atras.
    mostrarPantalla(pantallaTelefono);
    return;
  }

  btnLogin.disabled = true;
  btnLogin.textContent = "CONECTANDO...";

  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_id, api_hash, telefono }),
    });
    const data = await res.json();

    if (!data.ok) {
      errorLogin.textContent = data.error || "Error desconocido.";
      return;
    }

    if (data.ya_conectado) {
      mostrarPantalla(pantallaBuscar);
      inputMensaje.focus();
    } else {
      mostrarPantalla(pantallaCodigo);
      inputCodigo.focus();
    }
  } catch (e) {
    errorLogin.textContent = "No se pudo contactar con el servidor.";
  } finally {
    btnLogin.disabled = false;
    btnLogin.textContent = "CONECTAR";
  }
});


/* ---------- 4. Paso 2: enviar codigo (y contrasena 2FA si hace falta) ---------- */
btnVerificar.addEventListener("click", async () => {
  errorCodigo.textContent = "";
  const codigo = inputCodigo.value.trim();
  const contrasena = inputContrasena.value;

  if (!codigo) {
    errorCodigo.textContent = "Escribe el codigo que has recibido.";
    return;
  }

  btnVerificar.disabled = true;
  btnVerificar.textContent = "VERIFICANDO...";

  try {
    const res = await fetch("/api/verificar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ codigo, contrasena }),
    });
    const data = await res.json();

    if (data.necesita_password) {
      labelPassword.classList.remove("oculto");
      errorCodigo.textContent = "Esta cuenta tiene verificacion en dos pasos. Escribe tu contrasena.";
      return;
    }

    if (!data.ok) {
      errorCodigo.textContent = data.error || "Error desconocido.";
      return;
    }

    mostrarPantalla(pantallaBuscar);
    inputMensaje.focus();
  } catch (e) {
    errorCodigo.textContent = "No se pudo contactar con el servidor.";
  } finally {
    btnVerificar.disabled = false;
    btnVerificar.textContent = "VERIFICAR";
  }
});


/* ---------- 5. Buscador: enviar mensaje al bot y mostrar respuesta ---------- */

/*
  Cada busqueda (o cada boton que pulses despues) se dibuja como un
  "turno": un bloque propio con tu mensaje arriba (si lo hay) y la
  respuesta del bot debajo, junto con sus botones si trae. Cada turno
  nuevo se anade DEBAJO del anterior, nunca se mezcla con el de
  antes, para que quede todo ordenado.
*/
function crearTurno(textoUsuario) {
  const turno = document.createElement("div");
  turno.className = "turno";

  if (textoUsuario) {
    const lineaUsuario = document.createElement("div");
    lineaUsuario.className = "linea-usuario";
    lineaUsuario.textContent = "> " + textoUsuario;
    turno.appendChild(lineaUsuario);
  }

  const cuerpoRespuesta = document.createElement("div");
  cuerpoRespuesta.className = "cuerpo-respuesta";
  turno.appendChild(cuerpoRespuesta);

  salida.appendChild(turno);
  salida.scrollTop = salida.scrollHeight;
  return { turno, cuerpoRespuesta };
}

function escribirLineaSistema(contenedor, texto) {
  const linea = document.createElement("div");
  linea.className = "linea-sistema";
  linea.textContent = texto;
  contenedor.appendChild(linea);
  salida.scrollTop = salida.scrollHeight;
  return linea;
}

/*
  Efecto de "escritura tipo hacker", pero por BLOQUES de varios
  caracteres a la vez (no letra a letra) para que los mensajes largos
  no se hagan eternos. Cuanto mas largo es el texto, mayor es el
  bloque que se escribe en cada paso, asi un mensaje de 2000
  caracteres no tarda mucho mas que uno de 200.
*/
function escribirConEfecto(elemento, texto, velocidadMs = 8) {
  return new Promise((resolve) => {
    if (!texto) {
      resolve();
      return;
    }
    // Bloque minimo de 3 caracteres; para textos largos, un bloque
    // proporcional a la longitud (p.ej. un mensaje de 1500
    // caracteres se escribe en unos 100 pasos, no 1500).
    const tamanoBloque = Math.max(3, Math.ceil(texto.length / 150));
    let i = 0;
    elemento.classList.add("cursor-parpadea");
    const intervalo = setInterval(() => {
      i += tamanoBloque;
      elemento.textContent = texto.slice(0, i);
      salida.scrollTop = salida.scrollHeight;
      if (i >= texto.length) {
        elemento.textContent = texto;
        clearInterval(intervalo);
        elemento.classList.remove("cursor-parpadea");
        resolve();
      }
    }, velocidadMs);
  });
}

/*
  Dibuja los botones inline del bot dentro de 'contenedor'. Cada fila
  de Telegram se dibuja como una fila propia, y dentro de la fila los
  botones se apilan uno debajo de otro (mas comodo en movil que
  ponerlos en horizontal). Al pulsar uno, se llama a
  /api/pulsar_boton y el resultado se dibuja como un turno nuevo.
*/
function dibujarBotones(contenedor, filasBotones) {
  if (!filasBotones || filasBotones.length === 0) return;

  const wrapBotones = document.createElement("div");
  wrapBotones.className = "botones-bot";

  filasBotones.forEach((fila) => {
    const filaDiv = document.createElement("div");
    filaDiv.className = "fila-botones";

    fila.forEach((boton) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn-inline-bot";
      btn.textContent = boton.texto;

      btn.addEventListener("click", () => manejarClicBoton(btn, boton));

      filaDiv.appendChild(btn);
    });

    wrapBotones.appendChild(filaDiv);
  });

  contenedor.appendChild(wrapBotones);
  salida.scrollTop = salida.scrollHeight;
}

async function manejarClicBoton(btnPulsado, boton) {
  // Si es un boton tipo "url", es solo un enlace: lo abrimos y ya,
  // sin llamar al backend ni esperar ninguna respuesta.
  if (boton.tipo === "url" && boton.url) {
    window.open(boton.url, "_blank", "noopener");
    return;
  }

  // Desactivamos TODOS los botones de ese mensaje mientras se espera
  // respuesta, para evitar pulsar dos veces o pulsar otro boton del
  // mismo mensaje mientras el anterior aun se esta procesando.
  const wrapBotones = btnPulsado.closest(".botones-bot");
  const todosLosBotones = wrapBotones ? wrapBotones.querySelectorAll("button") : [btnPulsado];
  todosLosBotones.forEach((b) => (b.disabled = true));
  const textoOriginal = btnPulsado.textContent;
  btnPulsado.textContent = "...";

  const { cuerpoRespuesta } = crearTurno(null);
  const lineaEspera = escribirLineaSistema(cuerpoRespuesta, "Consultando...");

  try {
    const res = await fetch("/api/pulsar_boton", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fila: boton.fila, columna: boton.columna }),
    });
    const data = await res.json();
    lineaEspera.remove();

    if (!data.ok) {
      escribirLineaSistema(cuerpoRespuesta, "[ERROR] " + (data.error || "Fallo desconocido"));
      return;
    }

    await mostrarResultadoBot(cuerpoRespuesta, data);
  } catch (e) {
    lineaEspera.remove();
    escribirLineaSistema(cuerpoRespuesta, "[ERROR] No se pudo contactar con el servidor.");
  } finally {
    // Los botones antiguos ya han hecho su funcion (Telegram ha
    // procesado ese callback); si el mensaje trae botones nuevos,
    // apareceran en el turno nuevo. Dejamos estos deshabilitados en
    // vez de reactivarlos, para que quede claro que pertenecen a un
    // paso ya pasado.
    btnPulsado.textContent = textoOriginal;
  }
}

/*
  Muestra en 'cuerpoRespuesta' el resultado que ha devuelto el
  backend (texto, botones y/o archivo), tanto si viene de una
  busqueda normal como de haber pulsado un boton.
*/
async function mostrarResultadoBot(cuerpoRespuesta, data) {
  if (data.respuesta) {
    const lineaRespuesta = document.createElement("div");
    cuerpoRespuesta.appendChild(lineaRespuesta);
    await escribirConEfecto(lineaRespuesta, data.respuesta);
  }

  if (data.archivo_url) {
    // El .html (p.ej. "descargar letra") se abre solo en una pestana
    // nueva, tal y como se pidio.
    window.open(data.archivo_url, "_blank", "noopener");
    escribirLineaSistema(cuerpoRespuesta, "[Se ha abierto un archivo en una pestana nueva]");
  }

  dibujarBotones(cuerpoRespuesta, data.botones);
}

inputMensaje.addEventListener("keydown", async (evento) => {
  if (evento.key !== "Enter") return;

  const mensaje = inputMensaje.value.trim();
  if (!mensaje) return;

  inputMensaje.disabled = true;
  inputMensaje.value = "";

  const { cuerpoRespuesta } = crearTurno(mensaje);
  const lineaEspera = escribirLineaSistema(cuerpoRespuesta, "Consultando...");

  try {
    const res = await fetch("/api/buscar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje }),
    });
    const data = await res.json();
    lineaEspera.remove();

    if (!data.ok) {
      escribirLineaSistema(cuerpoRespuesta, "[ERROR] " + (data.error || "Fallo desconocido"));
      return;
    }

    if (data.breachvip && data.breachvip.length) {
    	mostrarResultadosBreach(cuerpoRespuesta, data.breachvip);
    }

    await mostrarResultadoBot(cuerpoRespuesta, data);
  } catch (e) {
    lineaEspera.remove();
    escribirLineaSistema(cuerpoRespuesta, "[ERROR] No se pudo contactar con el servidor.");
  } finally {
    inputMensaje.disabled = false;
    inputMensaje.focus();
  }
});


/* ---------- 6. Cerrar sesion ---------- */
btnLogout.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  salida.innerHTML = "";
  inputApiId.value = "";
  inputApiHash.value = "";
  inputTelefono.value = "";
  inputCodigo.value = "";
  inputContrasena.value = "";
  labelPassword.classList.add("oculto");
  mostrarPantalla(pantallaTelefono);
});

function mostrarResultadosBreach(cuerpoRespuesta, results) {

    const contenedor = document.createElement("div");
    contenedor.className = "mensaje-bot";

    let html = `
        <div class="breach-titulo">
            🌐 BREACH.VIP
        </div>
    `;

    results.slice(0, 20).forEach(r => {

        html += `<div class="breach-card">`;

        if (r.source)
            html += `<div><strong>Source:</strong> ${r.source}</div>`;

        if (r.categories)
            html += `<div><strong>Categories:</strong> ${
                Array.isArray(r.categories)
                    ? r.categories.join(", ")
                    : r.categories
            }</div>`;

        Object.entries(r).forEach(([k, v]) => {

            if (k === "source" || k === "categories")
                return;

            html += `<div><strong>${k}:</strong> ${v}</div>`;

        });

        html += `</div>`;

    });

    contenedor.innerHTML = html;

    cuerpoRespuesta.appendChild(contenedor);

}