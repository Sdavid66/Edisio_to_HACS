import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "edisio"))
from pacing import tx_quiet_remaining as rem

Q, M = 0.5, 3.0   # silence requis / attente maximale (s)

# --- Canal libre : emission immediate ---
assert rem(1000.0, 0.0, 1000.0, Q, M) == 0.0        # jamais rien recu
assert rem(1000.0, 999.0, 1000.0, Q, M) == 0.0      # derniere reception il y a 1 s

# --- Reception recente : attendre la fin du silence requis ---
w = rem(1000.0, 999.9, 1000.0, Q, M); print("RX il y a 0,1 s ->", w)
assert abs(w - 0.4) < 1e-9

# --- Appui telecommande (3 repetitions en ~50 ms) pendant l'attente ---
t, last, start = 1000.02, 1000.0, 1000.02             # ordre demande 20 ms apres la 1re trame
for rx in (1000.016, 1000.048):                      # repetitions suivantes
    last = max(last, rx)
t = 1000.05
w = rem(t, last, start, Q, M); print("apres la 3e repetition ->", w)
assert abs((t + w) - (1000.048 + Q)) < 1e-9          # emission 0,5 s apres la derniere trame

# --- Canal occupe en continu : attente bornee a max_wait ---
w = rem(1002.8, 1002.79, 1000.0, Q, M); print("occupe depuis 2,8 s ->", w)
assert abs(w - 0.2) < 1e-9                           # 0,49 s restant, borne a 0,2 s
assert rem(1003.0, 1002.99, 1000.0, Q, M) == 0.0     # 3 s atteintes : on emet quand meme
print("OK")
