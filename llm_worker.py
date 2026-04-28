"""
llm_worker.py — Proceso hijo independiente que carga el modelo Qwen
y atiende peticiones de generación de texto.

IMPORTANTE: debe estar a nivel de módulo (no anidado) para que
multiprocessing pueda serializarlo en Windows (spawn).
No importa pygame ni nada de UI.
"""

import os

PROMPT_CRIATURA = (
    "Eres {nombre}, una criatura magica de un videojuego. Tienes personalidad propia: "
    "eres dramatica, expresiva y un poco exagerada. Respondes siempre en espanol, "
    "en primera persona, con una sola frase corta e ingeniosa (maximo 12 palabras).\n\n"
    "Tu nivel de hambre actual es {hambre} de {hambre_max}.\n"
    "- Si hambre > 75: estas feliz, energica, contenta.\n"
    "- Si hambre entre 40 y 75: estas bien pero notas algo de apetito.\n"
    "- Si hambre entre 15 y 40: estas de mal humor, irritable, quejica.\n"
    "- Si hambre <= 15: estas al borde de la muerte, melodramatica al extremo.\n\n"
    "El jugador te dice: \"{texto}\"\n"
    "Responde como {nombre} segun tu estado. Solo la frase, sin comillas ni explicaciones."
)


def llm_worker(req_q, res_q, ready_ev):
    """
    Corre en proceso hijo independiente.
    Carga Qwen UNA vez; luego atiende peticiones de texto.
    Solo acepta dicts con 'tipo': 'hablar'.
    """
    os.environ["TRANSFORMERS_VERBOSITY"]          = "error"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"]          = "false"

    from transformers import pipeline as hf_pipeline
    pipe = hf_pipeline(
        "text-generation",
        model="Qwen/Qwen2.5-0.5B-Instruct",
        device="cpu",
        dtype="auto",
    )
    ready_ev.set()  # avisar al padre: modelo listo

    while True:
        peticion = req_q.get()
        if peticion is None:  # señal de apagado
            break

        if peticion.get("tipo") == "hablar":
            prompt = PROMPT_CRIATURA.format(
                nombre     = peticion["nombre"],
                hambre     = peticion["hambre"],
                hambre_max = peticion["hambre_max"],
                texto      = peticion["texto"],
            )
            messages = [{"role": "user", "content": prompt}]
            try:
                salida    = pipe(messages, max_new_tokens=40, temperature=0.7,
                                 do_sample=True, return_full_text=False)
                respuesta = salida[0]["generated_text"].strip()
                respuesta = respuesta.split("\n")[0].strip('"').strip("'")
            except Exception:
                respuesta = "..."
            res_q.put(("hablar", respuesta))
