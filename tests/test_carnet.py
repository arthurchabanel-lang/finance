"""Tests du carnet d'ordres : les règles de marché doivent être exactes."""

from marche.carnet import ACHAT, VENTE, CarnetOrdres


def test_ordre_limite_reste_au_carnet_sans_contrepartie():
    c = CarnetOrdres()
    ordre, trs = c.ordre_limite(1, ACHAT, 10000, 5, t=0, duree=10)
    assert trs == [] and ordre.quantite == 5
    assert c.meilleur_achat(0).prix == 10000
    assert c.meilleure_vente(0) is None


def test_priorite_prix_puis_temps():
    c = CarnetOrdres()
    c.ordre_limite(1, VENTE, 10010, 5, t=0, duree=10)
    c.ordre_limite(2, VENTE, 10005, 5, t=0, duree=10)  # meilleur prix
    c.ordre_limite(3, VENTE, 10005, 5, t=0, duree=10)  # même prix, arrivé après
    trs = c.ordre_marche(9, ACHAT, 7, t=1)
    assert [(tr.vendeur, tr.prix, tr.quantite) for tr in trs] == [(2, 10005, 5), (3, 10005, 2)]


def test_execution_au_prix_du_carnet_et_reliquat():
    c = CarnetOrdres()
    c.ordre_limite(1, VENTE, 10000, 3, t=0, duree=10)
    ordre, trs = c.ordre_limite(2, ACHAT, 10050, 5, t=0, duree=10)
    assert trs[0].prix == 10000 and trs[0].quantite == 3  # prix de l'ordre déjà présent
    assert ordre.quantite == 2 and c.meilleur_achat(0).prix == 10050


def test_limite_ne_traverse_pas_au_dela_de_son_prix():
    c = CarnetOrdres()
    c.ordre_limite(1, VENTE, 10100, 5, t=0, duree=10)
    ordre, trs = c.ordre_limite(2, ACHAT, 10050, 5, t=0, duree=10)
    assert trs == [] and ordre is not None


def test_ordre_marche_sans_liquidite_est_perdu():
    c = CarnetOrdres()
    c.ordre_limite(1, VENTE, 10000, 2, t=0, duree=10)
    trs = c.ordre_marche(2, ACHAT, 5, t=0)
    assert sum(tr.quantite for tr in trs) == 2
    assert c.meilleure_vente(0) is None and c.meilleur_achat(0) is None


def test_expiration():
    c = CarnetOrdres()
    c.ordre_limite(1, ACHAT, 10000, 5, t=0, duree=3)
    assert c.meilleur_achat(2) is not None
    assert c.meilleur_achat(3) is None


def test_annulation():
    c = CarnetOrdres()
    ordre, _ = c.ordre_limite(1, ACHAT, 10000, 5, t=0, duree=10)
    c.annuler(ordre.id)
    assert c.meilleur_achat(0) is None


def test_pas_d_auto_execution():
    c = CarnetOrdres()
    c.ordre_limite(1, VENTE, 10000, 5, t=0, duree=10)
    trs = c.ordre_marche(1, ACHAT, 5, t=0)
    assert trs == [] and c.meilleure_vente(0) is None
