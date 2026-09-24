"""Ecoute avant emission (dongle Edisio transparent).

La clef USB Edisio peut se figer (radio muette en reception comme en emission,
puce USB toujours presente) quand on lui fait emettre un ordre pendant qu'elle
recoit une trame radio : par exemple les repetitions d'une telecommande dont
l'appui declenche justement une automatisation. Seule une remise sous tension
de la clef la debloque. Avant chaque ordre, la passerelle attend donc un court
silence radio (aucun octet recu), borne pour ne jamais bloquer une commande.

Module sans dependance a Home Assistant : testable seul (tests/test_pacing.py).
"""
from __future__ import annotations


def tx_quiet_remaining(now: float, last_rx: float, started: float,
                       quiet: float, max_wait: float) -> float:
    """Secondes a attendre encore avant d'emettre (0.0 = emettre maintenant).

    ``now``, ``last_rx`` (dernier octet recu) et ``started`` (debut de l'attente)
    sont des instants ``time.monotonic()``. On veut ``quiet`` s sans reception ;
    si le canal reste occupe, on emet quand meme apres ``max_wait`` s d'attente.
    """
    waited = now - started
    if waited >= max_wait:
        return 0.0
    remaining = quiet - (now - last_rx)
    if remaining <= 0:
        return 0.0
    return min(remaining, max_wait - waited)
