"""Cohérence comptable du marché multi-actifs."""

import tomllib
from pathlib import Path

from marche.multi import MarcheMulti

CONFIG = tomllib.loads((Path(__file__).parent.parent / "config.toml").read_text())


def test_conservation_titres_et_cash_multi_actifs():
    mm = MarcheMulti(CONFIG, graine=1)
    titres = [sum(a.actions for a in m.agents) for m in mm.marches]
    # Le cash des fonds est compté une fois (compte unique), pas une fois par marché.
    cash = sum(a.cash for m in mm.marches for a in m.agents if a.type_nom != "Fonds multi-actifs") \
        + sum(f.cash for f in mm.fonds)
    mm.executer(3000)
    assert [sum(a.actions for a in m.agents) for m in mm.marches] == titres
    cash_fin = sum(a.cash for m in mm.marches for a in m.agents if a.type_nom != "Fonds multi-actifs") \
        + sum(f.cash for f in mm.fonds)
    injections = mm.capital_injecte + sum(m.capital_injecte for m in mm.marches)
    assert abs(cash_fin - cash - injections) < 1e-4


def test_le_cash_du_fonds_est_partage_entre_marches():
    mm = MarcheMulti(CONFIG, graine=2)
    f = mm.fonds[0]
    f.comptes[0].cash -= 100.0
    assert f.comptes[1].cash == f.cash == f.comptes[2].cash
