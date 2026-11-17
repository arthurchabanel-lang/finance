"""Tests de cohérence comptable de la simulation."""

import tomllib
from pathlib import Path

from marche.simulation import Marche

CONFIG = tomllib.loads((Path(__file__).parent.parent / "config.toml").read_text())


def test_conservation_des_titres_et_du_cash():
    m = Marche(CONFIG, graine=0)
    titres = sum(a.actions for a in m.agents)
    cash = sum(a.cash for a in m.agents)
    m.executer(3000)
    assert sum(a.actions for a in m.agents) == titres  # aucun titre créé ni détruit
    assert abs(sum(a.cash for a in m.agents) - cash) < 1e-6  # jeu à somme nulle en cash


def test_positions_respectent_les_limites():
    m = Marche(CONFIG, graine=1)
    m.executer(3000)
    for a in m.agents:
        assert abs(a.actions - a.neutre) <= a.position_max


def test_reproductible():
    a, b = Marche(CONFIG, graine=7), Marche(CONFIG, graine=7)
    a.executer(1000)
    b.executer(1000)
    assert a.hist_prix == b.hist_prix
