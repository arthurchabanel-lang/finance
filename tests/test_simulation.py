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
    # Jeu à somme nulle en cash, hors capitaux frais apportés par les fonds qui remplacent les faillis.
    assert abs(sum(a.cash for a in m.agents) - cash - m.capital_injecte) < 1e-6


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


def test_prix_non_gele_par_un_carnet_sans_vendeurs():
    from marche.agents import ActeurExterne
    from marche.carnet import ACHAT
    m = Marche(CONFIG, graine=3)
    acheteur = m.ajouter_agent(ActeurExterne())
    m.carnet = type(m.carnet)()  # carnet vide
    m.dernier_prix = 40.0
    m.envoyer_limite(acheteur, ACHAT, 40.5, 10, duree=5)
    assert m.prix_reference() >= 40.5 - 1e-9
