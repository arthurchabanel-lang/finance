"""Lance une simulation et produit le tableau de bord.

Utilisation :
    python lancer.py                      # avec config.toml
    python lancer.py --pas 50000          # plus long
    python lancer.py --graine 7           # autre « univers » aléatoire
    python lancer.py --config autre.toml
"""

from __future__ import annotations

import argparse
import copy
import csv
import time
import tomllib
from pathlib import Path

from marche.analyse import analyser, texte_rapport, verdict_emergence
from marche.graphiques import tableau_de_bord
from marche.simulation import Marche

ICI = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulateur de marché multi-agents")
    parser.add_argument("--config", default=ICI / "config.toml", type=Path)
    parser.add_argument("--pas", type=int, help="nombre de pas (remplace la config)")
    parser.add_argument("--graine", type=int, help="graine aléatoire (remplace la config)")
    parser.add_argument("--sortie", default=ICI / "resultats", type=Path)
    args = parser.parse_args()

    with open(args.config, "rb") as f:
        config = tomllib.load(f)
    n_pas = args.pas or config["simulation"]["nombre_de_pas"]
    graine = args.graine if args.graine is not None else config["simulation"]["graine"]

    marche = Marche(config, graine)
    print(f"🏛️  Ouverture du marché : {len(marche.agents)} agents, "
          f"{n_pas:_} pas, graine {graine}".replace("_", " "))
    debut = time.time()
    marche.executer(n_pas, progression=lambda k, n: print(
        f"\r   séance en cours… {100 * k // n:3d} %  (prix {marche.hist_prix[-1]:8.2f} €)",
        end="", flush=True))
    print(f"\n🔔 Clôture après {time.time() - debut:.1f} s\n")

    rapport = analyser(marche.series())

    print("🧪 Expérience témoin : même marché, sans aucune news…")
    config_temoin = copy.deepcopy(config)
    config_temoin["fondamental"]["proba_news"] = 0.0
    temoin = Marche(config_temoin, graine)
    temoin.executer(n_pas)
    rapport.verdicts.insert(1, verdict_emergence(temoin.series()))
    print()
    texte = texte_rapport(rapport)
    print(texte)

    print("\nPERFORMANCE MOYENNE PAR STRATÉGIE")
    cm = config["marche"]
    initiale = cm["cash_initial"] + cm["actions_initiales"] * cm["prix_initial"]
    for nom, valeurs in marche.hist_richesse.items():
        print(f"   {nom:<18} {100 * (valeurs[-1] / initiale - 1):+7.1f} %")

    args.sortie.mkdir(parents=True, exist_ok=True)
    image = args.sortie / "tableau_de_bord.png"
    tableau_de_bord(marche, rapport, str(image))
    (args.sortie / "rapport.txt").write_text(texte + "\n", encoding="utf-8")
    s = marche.series()
    with open(args.sortie / "series.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["pas", "prix", "valeur_fondamentale", "spread", "volume"])
        for i in range(len(s["prix"])):
            w.writerow([i, f"{s['prix'][i]:.4f}", f"{s['fondamental'][i]:.4f}",
                        f"{s['spread'][i]:.4f}", int(s["volume"][i])])
    print(f"\n📊 Tableau de bord : {image}")
    print(f"📄 Données (Excel) : {args.sortie / 'series.csv'}")


if __name__ == "__main__":
    main()
