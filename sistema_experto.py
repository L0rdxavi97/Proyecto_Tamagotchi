"""
sistema_experto.py — Hechos y reglas del motor Experta.

Contiene:
  - Criatura  : hecho persistente con el estado de la criatura.
  - Intencion : hecho temporal con la intención del jugador.
  - SistemaCuidado : motor de reglas que reacciona a ambos hechos.
  - Helpers   : get_criatura(), retirar_intenciones().
"""

import random
import threading

from experta import Fact, KnowledgeEngine, Rule, MATCH, TEST


# ── Hechos ───────────────────────────────────────────────────────────

class Criatura(Fact):
    """Estado persistente de la criatura."""
    pass


class Intencion(Fact):
    """
    Hecho temporal con la intención del jugador.
    tipo : 'alimentar' | 'hablar' | 'jugar' | 'salir' | 'desconocido'
    texto: frase original (usada por la regla de hablar)
    """
    pass


# ── Motor ────────────────────────────────────────────────────────────

class SistemaCuidado(KnowledgeEngine):
    """
    Recibe hechos de Criatura e Intencion y ejecuta las acciones
    correspondientes, actualizando el estado compartido.

    Las dependencias de UI (lock, estado, show_bubble, show_status,
    log, _llm_req_q, _llm_res_q) se inyectan al crear la instancia.
    """

    def __init__(self, estado, lock, show_bubble, show_status, log_fn,
                 llm_req_q_getter, llm_res_q_getter):
        super().__init__()
        self._estado          = estado
        self._lock            = lock
        self._show_bubble     = show_bubble
        self._show_status     = show_status
        self._log             = log_fn
        self._llm_req_q       = llm_req_q_getter   # callable → queue actual
        self._llm_res_q       = llm_res_q_getter

    # ── Acciones de intención ────────────────────────────────────────

    @Rule(
        Intencion(tipo="alimentar"),
        Criatura(nombre=MATCH.nombre, hambre=MATCH.hambre,
                 hambre_maxima=MATCH.hambre_maxima, damage=MATCH.damage)
    )
    def accion_alimentar(self, nombre, hambre_maxima, damage):
        """El jugador quiere alimentar: restaurar hambre al máximo."""
        _retirar_una_intencion(self)
        criatura = get_criatura(self)
        if criatura is not None:
            self.retract(criatura)
        self.declare(Criatura(nombre=nombre, hambre=hambre_maxima,
                              hambre_maxima=hambre_maxima, damage=damage))
        with self._lock:
            self._estado["hambre"]      = hambre_maxima
            self._estado["feed_anim"]   = 60
            self._estado["aburrimiento"] = max(0, self._estado["aburrimiento"] - 20)
        self._show_bubble("¡Ñam ñam, delicioso!", 200)

    @Rule(
        Intencion(tipo="hablar", texto=MATCH.texto),
        Criatura(nombre=MATCH.nombre, hambre=MATCH.hambre,
                 hambre_maxima=MATCH.hambre_maxima)
    )
    def accion_hablar(self, texto, nombre, hambre, hambre_maxima):
        """El jugador quiere conversar: pedir respuesta al LLM."""
        _retirar_una_intencion(self)
        with self._lock:
            llm_ok   = self._estado["llm_ready"]
            llm_busy = self._estado["llm_busy"]
        if not llm_ok:
            self._show_status("LLM cargando aún...", 90)
            return
        if llm_busy:
            self._show_status("Dame un momento...", 80)
            return

        with self._lock:
            self._estado["llm_busy"] = True

        self._llm_req_q().put({
            "tipo":       "hablar",
            "texto":      texto,
            "nombre":     nombre,
            "hambre":     hambre,
            "hambre_max": hambre_maxima,
        })
        try:
            resultado = self._llm_res_q().get(timeout=20)
        except Exception:
            resultado = None
            self._show_bubble("...", 100)

        with self._lock:
            self._estado["llm_busy"]    = False
            self._estado["aburrimiento"] = max(0, self._estado["aburrimiento"] - 10)

        if resultado and isinstance(resultado, tuple) and resultado[0] == "hablar":
            self._show_bubble(resultado[1], 240)

    @Rule(Intencion(tipo="salir"))
    def accion_salir(self):
        """El jugador quiere salir: marcar el juego como terminado."""
        _retirar_una_intencion(self)
        with self._lock:
            self._estado["vivo"] = False

    @Rule(
        Intencion(tipo="jugar"),
        Criatura(nombre=MATCH.nombre)
    )
    def accion_jugar(self, nombre):
        """El jugador quiere jugar: resetear aburrimiento al mínimo."""
        _retirar_una_intencion(self)
        with self._lock:
            self._estado["aburrimiento"] = 0
            self._estado["jugar_anim"]   = 80
        frases = [
            "Yupi, por fin me haces caso!",
            "Esto si que me gusta! Mas, mas!",
            "Eso es! Sabia que eras divertido!",
            "Por fin! Me tenias abandonada!",
            "Weee! Esto mola muchisimo!",
        ]
        self._show_bubble(random.choice(frases), 260)
        self._log(f"{nombre} juega contigo. ¡Aburrimiento reseteado!")

    # ── Reglas de estado de la criatura ─────────────────────────────

    @Rule(
        Criatura(nombre=MATCH.nombre, hambre=MATCH.hambre,
                 hambre_maxima=MATCH.hambre_maxima),
        TEST(lambda hambre, hambre_maxima: 0 < hambre <= hambre_maxima * 0.25)
    )
    def alerta_mucha_hambre(self, nombre, hambre):
        """Hambre crítica: avisar al jugador."""
        self._show_bubble("¡Me muero de hambre!", 180)
        with self._lock:
            self._estado["danger_anim"] = 40

    @Rule(
        Criatura(hambre=MATCH.hambre, hambre_maxima=MATCH.hambre_maxima),
        TEST(lambda hambre, hambre_maxima:
             hambre_maxima * 0.25 < hambre <= hambre_maxima * 0.5)
    )
    def alerta_hambre_media(self, hambre):
        """Hambre moderada: queja leve."""
        self._show_status("Tengo un poco de hambre...", 100)

    @Rule(
        Criatura(nombre=MATCH.nombre, hambre=MATCH.hambre,
                 hambre_maxima=MATCH.hambre_maxima, damage=MATCH.damage),
        TEST(lambda hambre: hambre <= 0)
    )
    def criatura_muerta(self, nombre, hambre_maxima, damage):
        """Hambre a cero: game over."""
        with self._lock:
            self._estado["vivo"]   = False
            self._estado["hambre"] = 0


# ── Helpers ──────────────────────────────────────────────────────────

def get_criatura(engine):
    """Devuelve el hecho Criatura activo, o None si no existe."""
    for fact in engine.facts.values():
        if isinstance(fact, Criatura):
            return fact
    return None


def retirar_intenciones(engine):
    """Elimina todos los hechos Intencion pendientes del motor."""
    for f in list(engine.facts.values()):
        if isinstance(f, Intencion):
            engine.retract(f)


def _retirar_una_intencion(engine):
    """Retira la primera Intencion encontrada (uso interno de las reglas)."""
    for f in list(engine.facts.values()):
        if isinstance(f, Intencion):
            engine.retract(f)
            break
