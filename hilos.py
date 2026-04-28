"""
hilos.py — Hilos de lógica que corren en segundo plano:

  - cargar_modelos()     : spaCy + proceso LLM.
  - bucle_hambre()       : reduce hambre periódicamente.
  - bucle_aburrimiento() : aumenta aburrimiento y lanza quejas.
  - procesar_input_bg()  : clasifica el texto del jugador y lo
                           inyecta en el motor experto.

También contiene la detección rápida de intención con spaCy
(detectar_rapida) y los conjuntos de palabras clave.
"""

import time
import multiprocessing as mp

from llm_worker      import llm_worker
from sistema_experto import get_criatura, retirar_intenciones, Intencion, Criatura


# ── Conjuntos de palabras clave para spaCy ───────────────────────────

INTENT_ALIMENTAR = {
    "alimentar","comer","curar","sanar","dar",
    "comida","alimento","medicina","pocion",
    "vida","restaurar","recuperar","regenerar",
}
INTENT_SALIR = {
    "salir","terminar","acabar","cerrar","detener",
    "parar","exit","quit","fin","finalizar",
}
INTENT_HABLAR = {
    "hablar","conversar","charlar","preguntar","decir","hola","hey",
    "estar","sentir","como","que","tal","bien","mal","ola",
}
INTENT_JUGAR = {
    "jugar","juega","juego","entretenimiento","entretener","divertir","diversion",
    "actividad","animar","alegrar","interactuar","broma","chiste",
    "baile","bailar","cantar","cancion","reto","desafio",
}

# Mensajes de aburrimiento
_MENSAJES_ABURRIDO = [
    "Estoy tan aburridaaaa...",
    "Hazme caso, por favor!",
    "Oye! Que sigo aqui!",
    "Uaaaah... hay alguien ahi?",
    "Juega conmigo! Ya!",
    "Me voy a dormir de aburrimiento...",
    "Atencion! ATENCION! ATENCIOoOoN!",
    "Me has olvidado?",
    "Soy una criatura, no un cuadro!",
    "Interactua conmigo o me invento un drama!",
]
_MENSAJES_CRITICO = [
    "ESTO ES INTOLERABLE! ABURRIDISIMA!",
    "Llevo una eternidad aqui! JUEGA CONMIGO!",
    "Me niego a ser ignorada! OIGAN!",
    "SOY UNA PRISIONERA DEL ABURRIMIENTO!",
    "Ya esta bien! Exijo entretenimiento YA!",
]


# ── Detección de intención ───────────────────────────────────────────

def detectar_rapida(nlp, texto):
    """Clasifica el texto con spaCy. Devuelve la intención como string."""
    if nlp is None:
        return None
    doc   = nlp(texto.lower())
    lemas = {t.lemma_ for t in doc if not t.is_stop and not t.is_punct}
    if lemas & INTENT_SALIR:     return "salir"
    if lemas & INTENT_ALIMENTAR: return "alimentar"
    if lemas & INTENT_JUGAR:     return "jugar"
    if lemas & INTENT_HABLAR:    return "hablar"
    return "desconocido"


# ── Hilos ────────────────────────────────────────────────────────────

def cargar_modelos(estado, lock, nlp_ref, llm_handles):
    """
    Carga spaCy y lanza el proceso LLM.
    nlp_ref    : lista de 1 elemento [None] → se rellena con el modelo.
    llm_handles: dict con claves 'req_q', 'res_q', 'proc', 'ready_ev'.
    """
    import spacy
    nlp_ref[0] = spacy.load("es_core_news_sm")
    with lock:
        estado["nlp_ready"] = True

    req_q    = mp.Queue()
    res_q    = mp.Queue()
    ready_ev = mp.Event()
    proc     = mp.Process(
        target=llm_worker,
        args=(req_q, res_q, ready_ev),
        daemon=True,
    )
    proc.start()

    llm_handles["req_q"]    = req_q
    llm_handles["res_q"]    = res_q
    llm_handles["proc"]     = proc
    llm_handles["ready_ev"] = ready_ev

    # Esperar sin bloquear pygame
    while not ready_ev.is_set():
        time.sleep(0.5)

    with lock:
        estado["llm_ready"] = True


def bucle_hambre(engine, estado, lock):
    """Tick periódico: reduce hambre y deja que el motor experto reaccione."""
    while True:
        time.sleep(4)
        with lock:
            if not estado["vivo"]:
                break
            if not estado["nlp_ready"] or not estado["llm_ready"] or estado["llm_busy"]:
                continue
            criatura_fact = get_criatura(engine)
            if criatura_fact is None:
                break
            nombre     = criatura_fact["nombre"]
            hambre_max = criatura_fact["hambre_maxima"]
            damage     = int(criatura_fact["damage"])

        hambre_actual = max(0, int(criatura_fact["hambre"]) - damage)
        engine.retract(criatura_fact)
        engine.declare(Criatura(nombre=nombre, hambre=hambre_actual,
                                hambre_maxima=hambre_max, damage=damage))
        engine.run()
        with lock:
            estado["hambre"] = hambre_actual

        if hambre_actual <= 0:
            break


def bucle_aburrimiento(estado, lock, show_bubble):
    """Tick periódico: aumenta aburrimiento y lanza quejas si es alto."""
    import random
    tick = 0
    while True:
        time.sleep(6)
        with lock:
            if not estado["vivo"]:
                break
            if not estado["nlp_ready"] or not estado["llm_ready"] or estado["llm_busy"]:
                continue
            abur     = estado["aburrimiento"]
            abur_max = estado["aburrimiento_max"]

        nuevo = min(abur_max, abur + 3)
        with lock:
            estado["aburrimiento"] = nuevo

        tick  += 1
        ratio  = nuevo / max(abur_max, 1)

        if ratio >= 0.5 and tick % 3 == 0:
            msg = (random.choice(_MENSAJES_CRITICO)
                   if ratio >= 0.85
                   else random.choice(_MENSAJES_ABURRIDO))
            show_bubble(msg, 280)
            with lock:
                estado["danger_anim"] = 30


def procesar_input_bg(engine, estado, lock, input_queue,
                      nlp_ref, show_status, retirar_fn):
    """
    Clasifica la intención del texto con spaCy y declara un hecho
    en el motor experto. Nunca toma decisiones propias.
    """
    while True:
        time.sleep(0.05)
        with lock:
            if not input_queue:
                continue
            nlp_ok = estado["nlp_ready"]

        if not nlp_ok:
            show_status("Modelos cargando, espera...", 80)
            time.sleep(0.5)
            continue

        with lock:
            if not input_queue:
                continue
            texto = input_queue.pop(0)

        intencion = detectar_rapida(nlp_ref[0], texto)
        if intencion == "desconocido":
            intencion = "hablar"

        retirar_fn(engine)
        engine.declare(Intencion(tipo=intencion, texto=texto))
        engine.run()
