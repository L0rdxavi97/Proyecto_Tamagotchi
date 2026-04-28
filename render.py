"""
render.py — Funciones de dibujo con pygame.

Contiene:
  - Helpers gráficos: lerp_color(), draw_rounded_rect().
  - draw_creature()        : criatura a escala 1:1.
  - draw_creature_scaled() : criatura con factor de escala.
  - draw_bubble()          : bocadillo de diálogo.
  - pantalla_inicio()      : pantalla de nombre antes del juego.
"""

import math
import sys
import pygame

from constantes import (
    C_BG, C_BORDER, C_ACCENT, C_ACCENT2, C_TEXT, C_DIM,
    C_GREEN, C_YELLOW, C_RED, C_INPUT_BG, FPS
)


# ── Helpers gráficos ─────────────────────────────────────────────────

def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_rounded_rect(surf, color, rect, r=12, border=0, border_color=None):
    pygame.draw.rect(surf, color, rect, border_radius=r)
    if border and border_color:
        pygame.draw.rect(surf, border_color, rect, border, border_radius=r)


# ── Criatura ─────────────────────────────────────────────────────────

def draw_creature(surf, cx, cy, t, hambre_ratio, feed_anim, danger_anim):
    """Dibuja la criatura a escala 1:1."""
    s      = 1.0
    blink  = int(t * 2) % 40 < 2
    bounce = math.sin(t * 3) * 4 * s
    fur_col  = lerp_color((180, 100, 200), (120, 180, 255), hambre_ratio)
    dark_col = lerp_color((80, 30, 100), (40, 80, 160), hambre_ratio)
    by = int(bounce)

    if feed_anim > 0:
        glow = int(255 * (feed_anim / 60))
        for r in range(70, 30, -12):
            a = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(a, (*C_GREEN, int(glow * 0.18)), (r, r), r)
            surf.blit(a, (cx-r, int(cy+bounce)-r))

    if danger_anim > 0:
        pr = int(60 + math.sin(danger_anim * 0.5) * 10)
        a = pygame.Surface((pr*2, pr*2), pygame.SRCALPHA)
        pygame.draw.circle(a, (*C_RED, 40), (pr, pr), pr)
        surf.blit(a, (cx-pr, int(cy+bounce)-pr))

    # Cola
    tail_angle = math.sin(t * 2.5) * 0.6
    tail_ox = cx - 20
    tail_oy = cy + 8 + by
    tail_mid = (tail_ox - 22 + int(8 * math.sin(tail_angle)),
                tail_oy - 18 + int(12 * math.cos(tail_angle)))
    tail_tip = (tail_ox - 38 + int(15 * math.sin(tail_angle + 0.5)),
                tail_oy - 38 + int(18 * math.cos(tail_angle + 0.5)))
    pygame.draw.lines(surf, fur_col, False, [(tail_ox, tail_oy), tail_mid, tail_tip], 5)
    pygame.draw.circle(surf, fur_col, tail_tip, 7)

    # Cuerpo
    bw, bh = 46, 38
    pygame.draw.ellipse(surf, fur_col,
                        pygame.Rect(cx - bw//2, cy - bh//2 + by, bw, bh))

    # Cabeza
    head_r  = 28
    head_cx = cx
    head_cy = cy - 34 + by
    pygame.draw.circle(surf, fur_col, (head_cx, head_cy), head_r)

    # Orejas
    ear_inn = lerp_color(fur_col, (255, 180, 200), 0.5)
    pygame.draw.polygon(surf, fur_col,
        [(cx-22, head_cy-16), (cx-13, head_cy-40), (cx-3, head_cy-16)])
    pygame.draw.polygon(surf, ear_inn,
        [(cx-19, head_cy-18), (cx-13, head_cy-34), (cx-6, head_cy-18)])
    pygame.draw.polygon(surf, fur_col,
        [(cx+3, head_cy-16), (cx+13, head_cy-40), (cx+22, head_cy-16)])
    pygame.draw.polygon(surf, ear_inn,
        [(cx+6, head_cy-18), (cx+13, head_cy-34), (cx+19, head_cy-18)])

    # Ojos
    ey = head_cy + 2
    if not blink:
        for ex in (cx-10, cx+10):
            pygame.draw.circle(surf, (240, 240, 255), (ex, ey), 7)
            pygame.draw.ellipse(surf, (10, 5, 20),
                                pygame.Rect(ex-3, ey-5, 6, 10))
        pygame.draw.circle(surf, (255,255,255), (cx-8, ey-2), 2)
        pygame.draw.circle(surf, (255,255,255), (cx+12, ey-2), 2)
    else:
        pygame.draw.line(surf, dark_col, (cx-16, ey), (cx-4, ey), 2)
        pygame.draw.line(surf, dark_col, (cx+4,  ey), (cx+16, ey), 2)

    # Nariz
    nose_y = head_cy + 10
    pygame.draw.polygon(surf, (255, 120, 160),
        [(cx, nose_y+4), (cx-4, nose_y), (cx+4, nose_y)])

    # Boca según hambre
    my = nose_y + 5
    if hambre_ratio > 0.5:
        pygame.draw.arc(surf, dark_col, (cx-9, my-2, 9, 8),  math.pi, 2*math.pi, 2)
        pygame.draw.arc(surf, dark_col, (cx,   my-2, 9, 8),  math.pi, 2*math.pi, 2)
    elif hambre_ratio > 0.25:
        pygame.draw.line(surf, dark_col, (cx-7, my+2), (cx+7, my+2), 2)
    else:
        pygame.draw.arc(surf, dark_col, (cx-9, my, 9, 7), 0, math.pi, 2)
        pygame.draw.arc(surf, dark_col, (cx,   my, 9, 7), 0, math.pi, 2)

    # Bigotes
    wh_col = (200, 200, 230)
    for sign in (-1, 1):
        for i, ang in enumerate([-0.15, 0.0, 0.15]):
            wx_s = cx + sign * 5
            wx_e = cx + sign * 26
            wy   = nose_y + i * 4 - 3
            pygame.draw.line(surf, wh_col,
                             (wx_s, wy),
                             (wx_e + sign * int(math.sin(t + ang) * 2), wy), 1)

    # Patas
    pygame.draw.ellipse(surf, fur_col, pygame.Rect(cx-26, cy+16+by, 18, 11))
    pygame.draw.ellipse(surf, fur_col, pygame.Rect(cx+8,  cy+16+by, 18, 11))

    # Manos (estilo Rayman)
    arm_swing = math.sin(t * 2.0) * 8
    for sign, arm_swing_sign in ((-1, 1), (1, -1)):
        hx = cx + sign * 46
        hy = cy - 10 + by + int(arm_swing * arm_swing_sign)
        pygame.draw.circle(surf, fur_col, (hx, hy), 11)
        for da in (-0.6, 0.0, 0.6):
            dx = hx + int(10 * math.cos(math.pi * 0.5 + da))
            dy = hy + int(10 * math.sin(math.pi * 0.5 + da)) - 4
            pygame.draw.circle(surf, fur_col, (dx, dy), 5)


def draw_creature_scaled(surf, cx, cy, t, hambre_ratio,
                         feed_anim, danger_anim, scale=1.0):
    """Wrapper que escala la criatura multiplicando todos los offsets."""
    s        = scale
    blink    = int(t * 2) % 40 < 2
    bounce   = math.sin(t * 3) * 4 * s
    fur_col  = lerp_color((180, 100, 200), (120, 180, 255), hambre_ratio)
    dark_col = lerp_color((80, 30, 100), (40, 80, 160), hambre_ratio)
    by       = int(bounce)

    if feed_anim > 0:
        glow = int(255 * (feed_anim / 60))
        for r in range(int(70*s), int(30*s), -max(1, int(12*s))):
            if r <= 0: break
            a = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
            pygame.draw.circle(a, (*C_GREEN, int(glow*0.18)), (r,r), r)
            surf.blit(a, (cx-r, int(cy+bounce)-r))

    if danger_anim > 0:
        pr = int((60 + math.sin(danger_anim*0.5)*10)*s)
        a  = pygame.Surface((pr*2, pr*2), pygame.SRCALPHA)
        pygame.draw.circle(a, (*C_RED, 40), (pr,pr), pr)
        surf.blit(a, (cx-pr, int(cy+bounce)-pr))

    # Cola
    tail_angle = math.sin(t * 2.5) * 0.6
    tail_ox = cx - int(20*s)
    tail_oy = cy + int(8*s) + by
    tail_mid = (tail_ox - int(22*s) + int(8*s * math.sin(tail_angle)),
                tail_oy - int(18*s) + int(12*s * math.cos(tail_angle)))
    tail_tip = (tail_ox - int(38*s) + int(15*s * math.sin(tail_angle + 0.5)),
                tail_oy - int(38*s) + int(18*s * math.cos(tail_angle + 0.5)))
    pygame.draw.lines(surf, fur_col, False,
                      [(tail_ox, tail_oy), tail_mid, tail_tip], max(2, int(5*s)))
    pygame.draw.circle(surf, fur_col, tail_tip, max(3, int(7*s)))

    # Cuerpo
    bw = int(46*s); bh = int(38*s)
    pygame.draw.ellipse(surf, fur_col,
                        pygame.Rect(cx - bw//2, cy - bh//2 + by, bw, bh))

    # Cabeza
    head_r  = max(4, int(28*s))
    head_cx = cx
    head_cy = cy - int(34*s) + by
    pygame.draw.circle(surf, fur_col, (head_cx, head_cy), head_r)

    # Orejas
    ear_inn = lerp_color(fur_col, (255, 180, 200), 0.5)
    pygame.draw.polygon(surf, fur_col,
        [(cx-int(22*s), head_cy-int(16*s)),
         (cx-int(13*s), head_cy-int(40*s)),
         (cx-int(3*s),  head_cy-int(16*s))])
    pygame.draw.polygon(surf, ear_inn,
        [(cx-int(19*s), head_cy-int(18*s)),
         (cx-int(13*s), head_cy-int(34*s)),
         (cx-int(6*s),  head_cy-int(18*s))])
    pygame.draw.polygon(surf, fur_col,
        [(cx+int(3*s),  head_cy-int(16*s)),
         (cx+int(13*s), head_cy-int(40*s)),
         (cx+int(22*s), head_cy-int(16*s))])
    pygame.draw.polygon(surf, ear_inn,
        [(cx+int(6*s),  head_cy-int(18*s)),
         (cx+int(13*s), head_cy-int(34*s)),
         (cx+int(19*s), head_cy-int(18*s))])

    # Ojos
    ey = head_cy + int(2*s)
    er = max(3, int(7*s))
    if not blink:
        for ex in (cx-int(10*s), cx+int(10*s)):
            pygame.draw.circle(surf, (240, 240, 255), (ex, ey), er)
            pygame.draw.ellipse(surf, (10, 5, 20),
                pygame.Rect(ex-max(1,int(3*s)), ey-max(2,int(5*s)),
                            max(2,int(6*s)), max(4,int(10*s))))
        pygame.draw.circle(surf, (255,255,255),
                           (cx-int(8*s), ey-int(2*s)), max(1,int(2*s)))
        pygame.draw.circle(surf, (255,255,255),
                           (cx+int(12*s), ey-int(2*s)), max(1,int(2*s)))
    else:
        pygame.draw.line(surf, dark_col,
                         (cx-int(16*s), ey), (cx-int(4*s), ey), max(1,int(2*s)))
        pygame.draw.line(surf, dark_col,
                         (cx+int(4*s),  ey), (cx+int(16*s), ey), max(1,int(2*s)))

    # Nariz
    nose_y = head_cy + int(10*s)
    ns     = max(2, int(4*s))
    pygame.draw.polygon(surf, (255, 120, 160),
        [(cx, nose_y+ns), (cx-ns, nose_y), (cx+ns, nose_y)])

    # Boca según hambre
    my = nose_y + int(5*s)
    mw = max(3, int(9*s)); mh = max(2, int(8*s))
    if hambre_ratio > 0.5:
        pygame.draw.arc(surf, dark_col,
            (cx-mw, my-int(2*s), mw, mh), math.pi, 2*math.pi, max(1,int(2*s)))
        pygame.draw.arc(surf, dark_col,
            (cx,    my-int(2*s), mw, mh), math.pi, 2*math.pi, max(1,int(2*s)))
    elif hambre_ratio > 0.25:
        pygame.draw.line(surf, dark_col,
            (cx-int(7*s), my+int(2*s)), (cx+int(7*s), my+int(2*s)), max(1,int(2*s)))
    else:
        pygame.draw.arc(surf, dark_col,
            (cx-mw, my, mw, int(7*s)), 0, math.pi, max(1,int(2*s)))
        pygame.draw.arc(surf, dark_col,
            (cx,    my, mw, int(7*s)), 0, math.pi, max(1,int(2*s)))

    # Bigotes
    wh_col = (200, 200, 230)
    for sign in (-1, 1):
        for i, ang in enumerate([-0.15, 0.0, 0.15]):
            wx_s = cx + sign * int(5*s)
            wx_e = cx + sign * int(26*s)
            wy   = nose_y + i * int(4*s) - int(3*s)
            pygame.draw.line(surf, wh_col,
                             (wx_s, wy),
                             (wx_e + sign * int(math.sin(t+ang)*2*s), wy), max(1,1))

    # Patas
    pygame.draw.ellipse(surf, fur_col,
        pygame.Rect(cx-int(26*s), cy+int(16*s)+by, int(18*s), int(11*s)))
    pygame.draw.ellipse(surf, fur_col,
        pygame.Rect(cx+int(8*s),  cy+int(16*s)+by, int(18*s), int(11*s)))

    # Manos (estilo Rayman)
    arm_swing = math.sin(t * 2.0) * int(8*s)
    hand_r    = max(5, int(11*s))
    finger_r  = max(2, int(5*s))
    for sign, swing_sign in ((-1, 1), (1, -1)):
        hx = cx + sign * int(46*s)
        hy = cy - int(10*s) + by + int(arm_swing * swing_sign)
        pygame.draw.circle(surf, fur_col, (hx, hy), hand_r)
        for da in (-0.6, 0.0, 0.6):
            dx = hx + int(hand_r * math.cos(math.pi * 0.5 + da))
            dy = hy + int(hand_r * math.sin(math.pi * 0.5 + da)) - int(4*s)
            pygame.draw.circle(surf, fur_col, (dx, dy), finger_r)


# ── Bocadillo ────────────────────────────────────────────────────────

def draw_bubble(surf, text, cx, creature_y, scale,
                font, bg_col, border_col, text_col):
    """Bocadillo de diálogo sobre la criatura."""
    padding = 14
    max_w   = 320
    words   = text.split()
    lines   = []
    line    = ""
    for w in words:
        test = (line + " " + w).strip()
        if font.size(test)[0] <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)

    line_h = font.get_linesize()
    box_w  = max(font.size(l)[0] for l in lines) + padding * 2
    box_h  = line_h * len(lines) + padding * 2
    tail_h = 14

    body_top = int(creature_y - 52 * scale)
    box_y    = body_top - box_h - tail_h - 10
    box_x    = cx - box_w // 2

    # Sombra
    sh = pygame.Surface((box_w+4, box_h+4), pygame.SRCALPHA)
    sh.fill((0,0,0,0))
    pygame.draw.rect(sh, (0,0,0,80), sh.get_rect(), border_radius=12)
    surf.blit(sh, (box_x-2, box_y+2))

    # Fondo y borde
    pygame.draw.rect(surf, bg_col,    (box_x, box_y, box_w, box_h), border_radius=12)
    pygame.draw.rect(surf, border_col,(box_x, box_y, box_w, box_h), 2, border_radius=12)

    # Cola triangular
    tip_x = cx
    tip_y = box_y + box_h + tail_h
    pygame.draw.polygon(surf, bg_col,
        [(tip_x-10, box_y+box_h), (tip_x+10, box_y+box_h), (tip_x, tip_y)])
    pygame.draw.lines(surf, border_col, False,
        [(tip_x-10, box_y+box_h), (tip_x, tip_y), (tip_x+10, box_y+box_h)], 2)

    # Texto
    for i, l in enumerate(lines):
        ts = font.render(l, True, text_col)
        surf.blit(ts, (box_x + padding, box_y + padding + i * line_h))


# ── Pantalla de inicio ───────────────────────────────────────────────

def pantalla_inicio(screen, clock, font_big, font_med, font_sm):
    """Muestra la pantalla inicial y devuelve el nombre elegido."""
    nombre       = ""
    cursor_vis   = True
    cursor_timer = 0
    W0, H0       = screen.get_size()
    particles    = [(float(i*(W0//20)), float(H0//2),
                     (i%3-1)*0.3, (i%5-2)*0.2) for i in range(20)]

    while True:
        dt            = clock.tick(FPS)
        cursor_timer += dt
        if cursor_timer > 500:
            cursor_vis   = not cursor_vis
            cursor_timer = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (max(600, event.w), max(400, event.h)), pygame.RESIZABLE)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and nombre.strip():
                    return nombre.strip()
                elif event.key == pygame.K_BACKSPACE:
                    nombre = nombre[:-1]
                elif len(nombre) < 18 and event.unicode.isprintable():
                    nombre += event.unicode

        W0, H0 = screen.get_size()
        screen.fill(C_BG)

        for i, (px, py, vx, vy) in enumerate(particles):
            px = (px+vx) % W0; py = (py+vy) % H0
            particles[i] = (px, py, vx, vy)
            pygame.draw.circle(screen, C_BORDER, (int(px), int(py)), 2)

        t  = pygame.time.get_ticks() / 1000
        oy = int(math.sin(t) * 4)
        ts = font_big.render("CRIATURA",        True, C_ACCENT)
        ss = font_med.render("C U I D A D O R", True, C_ACCENT2)
        screen.blit(ts, ts.get_rect(centerx=W0//2, centery=int(H0*0.22)+oy))
        screen.blit(ss, ss.get_rect(centerx=W0//2, centery=int(H0*0.31)))

        draw_creature(screen, W0//2, int(H0*0.52), t, 0.9, 0, 0)

        screen.blit(font_sm.render("Nombre de tu criatura:", True, C_DIM),
                    (W0//2 - 140, int(H0*0.67)))
        box = pygame.Rect(W0//2 - 150, int(H0*0.71), 300, 42)
        draw_rounded_rect(screen, C_INPUT_BG, box, r=8,
                          border=2, border_color=C_ACCENT)
        disp = nombre + ("|" if cursor_vis else " ")
        ns   = font_med.render(disp, True, C_TEXT)
        screen.blit(ns, ns.get_rect(center=box.center))
        hs = font_sm.render("Pulsa Enter para comenzar", True, C_DIM)
        screen.blit(hs, hs.get_rect(centerx=W0//2, centery=int(H0*0.82)))
        pygame.display.flip()
