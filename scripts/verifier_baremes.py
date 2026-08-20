#!/usr/bin/env python3
"""
Vérifie que le SMIC et le PASS codés en dur dans logique-calculs.txt
correspondent aux valeurs officielles publiées par OpenFisca-France.

Ne modifie jamais le site automatiquement : ce script se contente de
comparer et de signaler un écart éventuel. La décision de mettre à jour
(et la vérification manuelle avant publication) reste entièrement entre
les mains de l'éditeur du site — important pour du contenu YMYL.

Portée volontairement limitée à deux paramètres : le SMIC brut mensuel
et le PASS (mensuel + annuel). Ce sont les deux valeurs les plus citées
sur le site, les plus souvent revalorisées, et les seules à avoir un
équivalent direct et sans ambiguïté dans l'API OpenFisca. Les autres
constantes de BAREME_2026 (taux ARE, coefficients IJ maternité/paternité,
charges patronales moyennes...) ne sont pas des barèmes légaux simples à
vérifier automatiquement (conventions Unédic, taux composites) : elles
doivent continuer à être vérifiées manuellement, par exemple une fois
par an lors de la revue annuelle mentionnée sur la page "À propos".

Source des données officielles : instance publique d'OpenFisca-France
(https://api.fr.openfisca.org). Cette instance est fournie par le projet
OpenFisca à des fins de prototypage, sans garantie de disponibilité
(pas de SLA). En cas d'indisponibilité, le script le signale clairement
au lieu de lever une fausse alerte de désaccord de barème.
"""

import json
import re
import sys
import urllib.request
import urllib.error
from datetime import date, datetime

OPENFISCA_BASE = "https://api.fr.openfisca.org/latest/parameter/"

PARAMS = {
    "smic_brut_mensuel": "marche_travail.salaire_minimum.smic.smic_b_mensuel",
    "pass_mensuel": "prelevements_sociaux.pss.plafond_securite_sociale_mensuel",
    "pass_annuel": "prelevements_sociaux.pss.plafond_securite_sociale_annuel",
}

LOGIQUE_CALCULS_PATH = "logique-calculs.txt"

SITE_KEYS = {
    "smic_brut_mensuel": "SMIC_BRUT_MENSUEL",
    "pass_mensuel": "PASS_MENSUEL",
    "pass_annuel": "PASS_ANNUEL",
}


def fetch_latest_value(param_path):
    """Récupère depuis OpenFisca la valeur la plus récente et déjà en
    vigueur (date <= aujourd'hui) d'un paramètre. Retourne
    (valeur, date_effet) ou lève une exception explicite."""
    url = OPENFISCA_BASE + param_path
    req = urllib.request.Request(url, headers={"User-Agent": "simulateur-rh-verif-baremes/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    values = data.get("values", {})
    if not values:
        raise ValueError(f"Aucune valeur renvoyée par OpenFisca pour {param_path}")

    today = date.today()
    valid_entries = []
    for date_str, value in values.items():
        if value is None:
            continue
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d <= today:
            valid_entries.append((d, value))

    if not valid_entries:
        raise ValueError(f"Aucune valeur en vigueur trouvée pour {param_path}")

    valid_entries.sort(key=lambda t: t[0])
    effective_date, value = valid_entries[-1]
    return value, effective_date


def read_site_values():
    """Extrait les constantes BAREME_2026 codées en dur dans logique-calculs.txt."""
    with open(LOGIQUE_CALCULS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    site_values = {}
    for key, site_key in SITE_KEYS.items():
        m = re.search(rf"{site_key}\s*:\s*([\d.]+)", content)
        if not m:
            raise ValueError(f"Impossible de trouver {site_key} dans {LOGIQUE_CALCULS_PATH}")
        site_values[key] = float(m.group(1))
    return site_values


def main():
    try:
        site_values = read_site_values()
    except (OSError, ValueError) as e:
        print(f"ERREUR_LECTURE_SITE: {e}")
        sys.exit(2)

    officiel = {}
    erreurs_api = []
    for key, param_path in PARAMS.items():
        try:
            value, effective_date = fetch_latest_value(param_path)
            officiel[key] = (value, effective_date)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as e:
            erreurs_api.append(f"- {key} ({param_path}) : {e}")

    if erreurs_api:
        print("VERIFICATION_IMPOSSIBLE")
        print("L'API OpenFisca (instance de prototypage, sans garantie de disponibilité) n'a pas répondu pour :")
        print("\n".join(erreurs_api))
        print("\nAucune conclusion sur les barèmes n'a pu être tirée ce mois-ci. Une vérification manuelle est recommandée.")
        sys.exit(3)

    ecarts = []
    lignes_ok = []
    for key in PARAMS:
        valeur_site = site_values[key]
        valeur_officielle, date_effet = officiel[key]
        valeur_officielle_arrondie = round(valeur_officielle)
        if abs(valeur_site - valeur_officielle_arrondie) > 0.5:
            ecarts.append(
                f"- {SITE_KEYS[key]} : site = {valeur_site:g} € · officiel (en vigueur depuis le {date_effet}) = "
                f"{valeur_officielle_arrondie:g} € (valeur brute OpenFisca : {valeur_officielle})"
            )
        else:
            lignes_ok.append(f"- {SITE_KEYS[key]} : {valeur_site:g} € — à jour (vérifié contre {valeur_officielle_arrondie:g} €, en vigueur depuis le {date_effet})")

    print("=== Vérification barèmes SMIC / PASS — simulateur-rh.fr ===\n")
    print("\n".join(lignes_ok))

    if ecarts:
        print("\nECART_DETECTE")
        print("\n".join(ecarts))
        print(
            "\nÀ faire : vérifier la nouvelle valeur officielle sur une source primaire "
            "(legifrance.gouv.fr, urssaf.fr/taux-baremes), puis mettre à jour l'objet "
            "BAREME_2026 dans logique-calculs.txt si confirmé. Ne pas publier sans "
            "vérification manuelle."
        )
        sys.exit(1)

    print("\nAucun écart détecté. Rien à faire.")
    sys.exit(0)


if __name__ == "__main__":
    main()
