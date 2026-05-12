# 🐾 Cuidador de Criaturas — Tamagotchi

> Proyecto del Curso de Especialización en Inteligencia Artificial y Big Data desarrollado por **Javier Acedo Caballero**
>
> Un Tamagotchi moderno con Inteligencia Artificial: sistema experto, modelo de lenguaje local (LLM) y procesamiento del lenguaje natural (PLN).

---

## 📋 Descripción

**Cuidador de Criaturas** es un juego de simulación de mascota virtual inspirado en los Tamagotchi clásicos, pero potenciado con tecnologías de IA. El jugador debe mantener viva y feliz a su criatura interactuando con ella en lenguaje natural a través de un chat integrado en la interfaz gráfica.

La criatura tiene necesidades que evolucionan en tiempo real: puede pasar hambre, aburrirse y morir si no es atendida. El sistema interpreta lo que el usuario escribe (alimentar, jugar, hablar...) y responde de forma inteligente gracias a la combinación de tres tecnologías de IA.

---

## 🧠 Tecnologías de IA utilizadas

| Módulo | Tecnología | Función |
|---|---|---|
| `sistema_experto.py` | **Experta** (Python) | Motor de reglas que gestiona el estado de la criatura |
| `llm_worker.py` | **Qwen** (HuggingFace) | Genera respuestas en lenguaje natural de la criatura |
| `hilos.py` | **spaCy** | Clasifica la intención del usuario (alimentar, jugar, etc.) |

---

## 🗂️ Estructura del proyecto

```
Proyecto_Tamagotchi/
│
├── main.py               # Punto de entrada. Orquesta todos los módulos
├── constantes.py         # Dimensiones de pantalla, colores y FPS
├── render.py             # Funciones de dibujo con pygame (criatura, barras, UI)
├── sistema_experto.py    # Hechos y reglas del sistema experto (Experta)
├── hilos.py              # Bucles de hambre, aburrimiento e input del usuario
├── llm_worker.py         # Proceso hijo que ejecuta el modelo Qwen
└── get-pip.py            # Utilidad de instalación de pip
```

---

## ⚙️ Instalación

### Requisitos previos

- Python **3.11**
- pip

### 1. Clonar el repositorio

```bash
git clone https://github.com/L0rdxavi97/Proyecto_Tamagotchi.git
cd Proyecto_Tamagotchi
```

### 2. Instalar dependencias

```bash
pip install pygame experta spacy transformers torch
```

### 3. Descargar el modelo de spaCy

```bash
py -m spacy download es_core_news_sm
```

> ⚠️ El modelo LLM (Qwen) se descarga automáticamente desde HuggingFace la primera vez que se ejecuta. Requiere conexión a internet y varios GB de espacio en disco.

### 4. Ejecutar

```bash
python main.py
```

---

## 🎮 Cómo jugar

1. Al iniciar, escribe el **nombre** de tu criatura en la pantalla de bienvenida.
2. La criatura aparecerá en pantalla con sus indicadores de estado:
   - **Barra de hambre** — se vacía con el tiempo. Si llega a cero, la criatura muere.
   - **Anillo de aburrimiento** — se llena si no interactúas. Si se desborda, la criatura se queja.
3. Escribe en el **cuadro de chat** para interactuar. Ejemplos:
   - `"dale de comer"` → alimenta a la criatura
   - `"juega con ella"` → reduce el aburrimiento
   - `"¿cómo estás?"` → la criatura responde con el LLM
4. Si la criatura muere, aparece la pantalla de **GAME OVER**. Pulsa cualquier tecla para salir.

---

## 🏗️ Arquitectura

El programa sigue una arquitectura **multihilo** con estado compartido:

```
main.py
 ├── Hilo: cargar_modelos()       → carga spaCy y Qwen en segundo plano
 ├── Hilo: bucle_hambre()         → reduce el hambre periódicamente
 ├── Hilo: bucle_aburrimiento()   → incrementa el aburrimiento con el tiempo
 ├── Hilo: procesar_input_bg()    → clasifica el input del usuario con spaCy
 └── Proceso: llm_worker()        → ejecuta Qwen de forma aislada (multiprocessing)
```

El estado global (`dict`) está protegido por un `threading.Lock` para evitar condiciones de carrera entre hilos.

El **sistema experto** (Experta) se activa con cada acción clasificada y aplica las reglas correspondientes: alimentar, jugar, detectar peligro, etc.

---

## 🖼️ Interfaz

La interfaz está construida con **pygame** y renderizada completamente en `render.py`:

- **Nombre** de la criatura centrado en la parte superior.
- **Criatura animada** que cambia de aspecto según su nivel de hambre y estado de ánimo.
- **Bocadillo de diálogo** con las respuestas generadas por el LLM.
- **Barra de hambre** con gradiente de color (verde → rojo).
- **Anillo de aburrimiento** con animación de pulso cuando está al límite.
- **Caja de input** para escribir comandos en lenguaje natural.
- **Overlay de Game Over** al morir la criatura.

---

## 📦 Dependencias principales

| Librería | Uso |
|---|---|
| `pygame` | Motor gráfico e interfaz de usuario |
| `experta` | Motor de sistema experto (reglas y hechos) |
| `spacy` | Procesamiento del lenguaje natural |
| `transformers` | Carga y ejecución del modelo Qwen (LLM) |
| `torch` | Backend para inferencia del LLM |
| `multiprocessing` | Proceso aislado para el worker del LLM |
| `threading` | Gestión de hilos concurrentes |

---

## 🐛 Notas conocidas

- La primera ejecución puede tardar varios minutos en descargar el modelo Qwen.
- Mientras los modelos se cargan, el hambre está **pausada** para no penalizar al jugador.
- En Windows, el script usa `mp.freeze_support()` para compatibilidad con PyInstaller.
- Se aplica un parche de compatibilidad para `collections.Mapping` en Python 3.10+.

---

## 👤 Autor

**Javier Acedo Caballero**

Proyecto académico que combina sistemas expertos, LLMs y PLN en una aplicación interactiva de entretenimiento.
