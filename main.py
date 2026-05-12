"""
    Cuidador de Criaturas — Tamagotchi
    Realizado por Javier Acedo Caballero
    Programa con uso de Sistema experto, LLM y de PLN

Punto de entrada. Solo orquesta los módulos:
  constantes.py     — dimensiones y colores
  llm_worker.py     — proceso hijo Qwen (debe estar a nivel de módulo para Windows)
  sistema_experto.py — hechos y reglas Experta
  hilos.py          — bucles de hambre, aburrimiento e input
  render.py         — todas las funciones de dibujo con pygame
"""

import collections
import threading
import sys
import os
import math
import multiprocessing as mp

HAMBRE = 100
DAMAGE = 1

# Silenciar warnings de HuggingFace antes de cualquier import de transformers
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"]           = "false"

# Compatibilidad Python 3.10+ con librerías que usan collections.Mapping
if not hasattr(collections, "Mapping"):
    import collections.abc
    collections.Mapping        = collections.abc.Mapping
    collections.MutableMapping = collections.abc.MutableMapping
    collections.Sequence       = collections.abc.Sequence
    collections.Iterable       = collections.abc.Iterable


# ── Worker LLM (nivel de módulo: requerido por multiprocessing en Windows) ──
from llm_worker import llm_worker  # noqa: F401  (necesario para mp.Process)


if __name__ == "__main__":
    mp.freeze_support()  # Windows + PyInstaller

    import pygame
    from constantes import W, H, FPS
    from constantes import (C_BG, C_PANEL, C_BORDER, C_ACCENT, C_ACCENT2,
                            C_TEXT, C_DIM, C_GREEN, C_YELLOW, C_RED, C_INPUT_BG)

    from sistema_experto import (SistemaCuidado, Criatura, retirar_intenciones)
    from hilos import (cargar_modelos, bucle_hambre,
                       bucle_aburrimiento, procesar_input_bg)
    from render import (lerp_color, draw_rounded_rect, draw_creature_scaled,
                        draw_bubble, pantalla_inicio)

    # ── Estado compartido entre hilos ────────────────────────────────
    estado = {
        "vivo":            True,
        "hambre":          HAMBRE,
        "hambre_max":      HAMBRE,
        "nombre":          "???",
        "log":             [],
        "nlp_ready":       False,
        "llm_ready":       False,
        "feed_anim":       0,
        "danger_anim":     0,
        "llm_busy":        False,
        "bubble":          "",
        "bubble_timer":    0,
        "status_msg":      "",
        "status_timer":    0,
        "aburrimiento":    0,
        "aburrimiento_max": 100,
        "jugar_anim":      0,
    }
    lock        = threading.Lock()
    input_queue = []        # textos pendientes de clasificar
    nlp_ref     = [None]    # spaCy model (lista para poder mutarla desde el hilo)
    llm_handles = {}        # req_q, res_q, proc, ready_ev → rellena cargar_modelos

    # ── Helpers de UI (usados por reglas y hilos) ────────────────────
    def log(msg, color=None):
        if color is None:
            color = C_TEXT
        with lock:
            estado["log"].append((msg, color))
            if len(estado["log"]) > 60:
                estado["log"].pop(0)

    def show_bubble(msg, frames=220):
        with lock:
            estado["bubble"]       = msg
            estado["bubble_timer"] = frames

    def show_status(msg, frames=120):
        with lock:
            estado["status_msg"]   = msg
            estado["status_timer"] = frames

    # ── pygame ───────────────────────────────────────────────────────
    pygame.init()
    screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
    pygame.display.set_caption("Cuidador de Criaturas")
    clock  = pygame.time.Clock()

    try:
        font_big = pygame.font.SysFont("couriernew", 52, bold=True)
        font_med = pygame.font.SysFont("couriernew", 22)
        font_sm  = pygame.font.SysFont("couriernew", 16)
    except Exception:
        font_big = pygame.font.SysFont(None, 52)
        font_med = pygame.font.SysFont(None, 22)
        font_sm  = pygame.font.SysFont(None, 16)

    # ── Pantalla de inicio ───────────────────────────────────────────
    crt_name = pantalla_inicio(screen, clock, font_big, font_med, font_sm)
    with lock:
        estado["nombre"] = crt_name

    # ── Motor experto ────────────────────────────────────────────────
    engine = SistemaCuidado(
        estado        = estado,
        lock          = lock,
        show_bubble   = show_bubble,
        show_status   = show_status,
        log_fn        = log,
        llm_req_q_getter = lambda: llm_handles.get("req_q"),
        llm_res_q_getter = lambda: llm_handles.get("res_q"),
    )
    engine.reset()
    engine.declare(Criatura(nombre=crt_name, hambre=HAMBRE,
                            hambre_maxima=HAMBRE, damage=DAMAGE))
    with lock:
        estado["hambre"]     = HAMBRE
        estado["hambre_max"] = HAMBRE

    log(f"Bienvenido! Tu criatura se llama {crt_name}.", C_ACCENT2)

    # ── Hilos de lógica ──────────────────────────────────────────────
    threading.Thread(
        target=cargar_modelos,
        args=(estado, lock, nlp_ref, llm_handles),
        daemon=True,
    ).start()
    threading.Thread(
        target=bucle_hambre,
        args=(engine, estado, lock),
        daemon=True,
    ).start()
    threading.Thread(
        target=bucle_aburrimiento,
        args=(estado, lock, show_bubble),
        daemon=True,
    ).start()
    threading.Thread(
        target=procesar_input_bg,
        args=(engine, estado, lock, input_queue,
              nlp_ref, show_status, retirar_intenciones),
        daemon=True,
    ).start()

    show_bubble(f"¡Hola! Soy {crt_name}", 200)

    # ── Loop principal ───────────────────────────────────────────────
    input_text   = ""
    cursor_vis   = True
    cursor_timer = 0
    running      = True

    while running:
        dt = clock.tick(FPS)
        t  = pygame.time.get_ticks() / 1000

        W, H    = screen.get_size()

        cursor_timer += dt
        if cursor_timer > 500:
            cursor_vis   = not cursor_vis
            cursor_timer = 0

        # Leer estado compartido
        with lock:
            feed_anim    = estado["feed_anim"]
            danger_anim  = estado["danger_anim"]
            if estado["feed_anim"]   > 0: estado["feed_anim"]   -= 1
            if estado["danger_anim"] > 0: estado["danger_anim"] -= 1
            hambre       = estado["hambre"]
            hambre_max   = estado["hambre_max"]
            nombre       = estado["nombre"]
            vivo         = estado["vivo"]
            log_data     = list(estado["log"])
            nlp_ready    = estado["nlp_ready"]
            llm_ready    = estado["llm_ready"]
            llm_busy     = estado["llm_busy"]
            bubble       = estado["bubble"]
            status_msg   = estado["status_msg"]
            aburrimiento     = estado["aburrimiento"]
            aburrimiento_max = estado["aburrimiento_max"]
            jugar_anim       = estado["jugar_anim"]
            if estado["jugar_anim"]   > 0: estado["jugar_anim"]   -= 1
            if estado["bubble_timer"] > 0: estado["bubble_timer"] -= 1
            else:                          estado["bubble"]        = ""
            if estado["status_timer"] > 0: estado["status_timer"] -= 1
            else:                          estado["status_msg"]    = ""

        hambre_ratio = hambre / max(hambre_max, 1)

        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (max(600, event.w), max(400, event.h)), pygame.RESIZABLE)
            if event.type == pygame.KEYDOWN:
                if not vivo:
                    running = False
                    break
                if event.key == pygame.K_RETURN:
                    txt = input_text.strip()
                    if txt:
                        with lock: input_queue.append(txt)
                        input_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.unicode.isprintable() and len(input_text) < 60:
                    input_text += event.unicode

        # ── FONDO ────────────────────────────────────────────────────
        screen.fill(C_BG)
        for gx in range(0, W, 40):
            pygame.draw.line(screen, (25, 20, 45), (gx, 0), (gx, H))
        for gy in range(0, H, 40):
            pygame.draw.line(screen, (25, 20, 45), (0, gy), (W, gy))

        # ── NOMBRE ───────────────────────────────────────────────────
        ns = font_big.render(nombre, True, C_ACCENT)
        screen.blit(ns, ns.get_rect(centerx=W // 2, y=18))

        # ── CRIATURA ─────────────────────────────────────────────────
        cx    = W // 2
        cy    = int(H * 0.46)
        SCALE = max(1.4, min(2.8, H / 280))

        if vivo:
            draw_creature_scaled(screen, cx, cy, t, hambre_ratio,
                                 feed_anim, danger_anim, SCALE)
        else:
            rip = font_big.render("R.I.P.", True, C_DIM)
            screen.blit(rip, rip.get_rect(centerx=cx, centery=cy))

        # ── BOCADILLO ────────────────────────────────────────────────
        if bubble:
            draw_bubble(screen, bubble, cx, cy, SCALE,
                        font_med, C_PANEL, C_BORDER, C_ACCENT)

        # ── BARRA HAMBRE ─────────────────────────────────────────────
        bw  = min(500, int(W * 0.55))
        bh  = 28
        bx  = (W - bw) // 2
        by_ = H - 115

        pygame.draw.rect(screen, C_INPUT_BG, (bx, by_, bw, bh), border_radius=10)
        bar_col = lerp_color(C_RED, C_GREEN, hambre_ratio)
        fw = max(0, int(bw * hambre_ratio))
        if fw:
            pygame.draw.rect(screen, bar_col, (bx, by_, fw, bh), border_radius=10)
        pygame.draw.rect(screen, C_BORDER, (bx, by_, bw, bh), 2, border_radius=10)
        pct_str    = f"HAMBRE  {int(hambre_ratio*100)}%"
        pct_shadow = font_sm.render(pct_str, True, (0, 0, 0))
        pct_label  = font_sm.render(pct_str, True, (255, 255, 255))
        pr = pct_label.get_rect(centerx=bx + bw//2, centery=by_ + bh//2)
        for dx, dy in ((-1,0),(1,0),(0,-1),(0,1)):
            screen.blit(pct_shadow, pr.move(dx, dy))
        screen.blit(pct_label, pr)

        # ── INDICADORES DE ESTADO ────────────────────────────────────
        hambre_pausada = not nlp_ready or not llm_ready or llm_busy
        ind_y = by_ - 22
        if status_msg:
            st_s = font_sm.render(status_msg, True, C_DIM)
            screen.blit(st_s, st_s.get_rect(centerx=W//2, y=ind_y))
            ind_y -= 20
        if hambre_pausada:
            ind_txt = "~ pensando..." if llm_busy else "~ cargando modelos..."
            ind_col = C_YELLOW if llm_busy else C_DIM
            ind_s   = font_sm.render(ind_txt, True, ind_col)
            screen.blit(ind_s, ind_s.get_rect(centerx=W//2, y=ind_y))

        # ── ANILLO DE ABURRIMIENTO ────────────────────────────────────
        abur_ratio = aburrimiento / max(aburrimiento_max, 1)
        ring_r     = 28
        ring_thick = 7
        ring_cx    = bx + bw + 60
        ring_cy    = by_ - ring_r - 20

        ring_col = (lerp_color(C_GREEN, C_YELLOW, abur_ratio * 2)
                    if abur_ratio < 0.5
                    else lerp_color(C_YELLOW, C_RED, (abur_ratio - 0.5) * 2))

        pygame.draw.circle(screen, C_INPUT_BG, (ring_cx, ring_cy), ring_r)
        pygame.draw.circle(screen, C_DIM,      (ring_cx, ring_cy), ring_r, ring_thick)

        if abur_ratio > 0.01:
            arc_rect  = pygame.Rect(ring_cx-ring_r, ring_cy-ring_r, ring_r*2, ring_r*2)
            start_a   = -math.pi / 2
            end_a     = start_a + 2 * math.pi * abur_ratio
            pygame.draw.arc(screen, ring_col, arc_rect, -end_a, -start_a, ring_thick)

        if abur_ratio >= 0.85:
            pulse      = int(abs(math.sin(t * 5)) * 100)
            pulse_surf = pygame.Surface((ring_r*2, ring_r*2), pygame.SRCALPHA)
            pygame.draw.circle(pulse_surf, (*C_RED, pulse),
                               (ring_r, ring_r), ring_r - ring_thick - 1)
            screen.blit(pulse_surf, (ring_cx-ring_r, ring_cy-ring_r))

        icon_str = "Zz" if abur_ratio < 0.5 else ("!!" if abur_ratio < 0.85 else "!!!")
        icon_s   = font_sm.render(icon_str, True, ring_col)
        screen.blit(icon_s, icon_s.get_rect(center=(ring_cx, ring_cy)))
        screen.blit(font_sm.render("ABUR", True, C_DIM),
                    font_sm.render("ABUR", True, C_DIM).get_rect(
                        centerx=ring_cx, y=ring_cy-ring_r-16))
        screen.blit(font_sm.render(f"{int(abur_ratio*100)}%", True, ring_col),
                    font_sm.render(f"{int(abur_ratio*100)}%", True, ring_col).get_rect(
                        centerx=ring_cx, y=ring_cy+ring_r+4))

        if jugar_anim > 0:
            glow_a = int(200 * (jugar_anim / 80))
            glow_r = ring_r + 10
            gs     = pygame.Surface((glow_r*2, glow_r*2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (*C_YELLOW, glow_a), (glow_r, glow_r), glow_r)
            screen.blit(gs, (ring_cx-glow_r, ring_cy-glow_r))

        # ── CAJA DE INPUT ─────────────────────────────────────────────
        input_rect = pygame.Rect(W//2 - min(320, W//2-20),
                                 H - 68,
                                 min(640, W-40), 46)
        draw_rounded_rect(screen, C_INPUT_BG, input_rect, r=10,
                          border=2, border_color=C_ACCENT)
        screen.blit(font_sm.render(">", True, C_ACCENT),
                    (input_rect.x+12, input_rect.y+14))
        disp_text = (input_text + ("|" if cursor_vis else " "))[:52]
        screen.blit(font_med.render(disp_text, True, C_TEXT),
                    (input_rect.x+30, input_rect.y+11))

        # ── GAME OVER OVERLAY ─────────────────────────────────────────
        if not vivo:
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 170))
            screen.blit(ov, (0, 0))
            go1 = font_big.render("GAME  OVER", True, C_RED)
            go2 = font_med.render("Pulsa cualquier tecla para salir", True, C_DIM)
            screen.blit(go1, go1.get_rect(center=(W//2, H//2-30)))
            screen.blit(go2, go2.get_rect(center=(W//2, H//2+30)))

        pygame.display.flip()

    # ── Cierre limpio ─────────────────────────────────────────────────
    req_q = llm_handles.get("req_q")
    proc  = llm_handles.get("proc")
    if req_q is not None:
        try: req_q.put(None)
        except Exception: pass
    if proc is not None and proc.is_alive():
        proc.terminate()

    pygame.quit()
    sys.exit()
