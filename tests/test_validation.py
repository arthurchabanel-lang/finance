"""Les outils de mesure doivent retrouver des propriétés connues sur des données synthétiques."""

import numpy as np

from marche.validation import asymetrie, exposant_memoire, fonction_levier


def test_exposant_memoire_retrouve_une_loi_de_puissance():
    k = np.arange(1, 31)
    assert abs(exposant_memoire(0.4 * k ** -0.3) - 0.3) < 1e-9


def test_asymetrie_negative_pour_des_krachs():
    rng = np.random.default_rng(0)
    x = rng.normal(size=10000)
    x[::100] -= 8  # quelques chutes brutales
    assert asymetrie(x) < -0.5


def test_levier_detecte_quand_les_baisses_font_monter_la_volatilite():
    rng = np.random.default_rng(1)
    n, sigma, r = 20000, 1.0, []
    for _ in range(n):
        x = sigma * rng.normal()
        r.append(x)
        sigma = np.sqrt(0.1 + 0.8 * sigma ** 2 + 0.1 * (min(x, 0) ** 2) * 2)  # GJR-GARCH
    assert fonction_levier(np.array(r))[0] < -0.05
