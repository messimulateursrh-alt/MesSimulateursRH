#!/usr/bin/env python3
"""Génère historique-mises-a-jour.html (page publique « Mises à jour et corrections »).

- Journal : dates datePublished / dateModified lues dans le JSON-LD de chaque page.
- Corrections : liste CORRECTIONS ci-dessous, tenue à la main (une ligne par
  correction de contenu publiée, la plus récente en tête).
- Gabarit : head, en-tête et pied repris de a-propos.html (byte-identiques).
- Met aussi à jour le <lastmod> de la page dans sitemap.xml.
Usage : python3 scripts/generer_historique.py (depuis la racine du site).
"""
import glob, html, json, os, re, sys
from collections import defaultdict

SITE = "https://messimulateursrh.fr"
SLUG = "historique-mises-a-jour"
DATE_PUBLICATION = "2026-10-12"
TITLE = "Mises à jour et corrections du site — MesSimulateursRH.fr"
H1 = "Mises à jour et corrections"
DESC = ("Les corrections publiées sur MesSimulateursRH.fr et la date de dernière "
        "mise à jour de chaque page : ce qui a été rectifié, quand et où.")
EXCLUS = {"404.html", SLUG + ".html"}

# (date ISO, [pages], ce qui était inexact, ce qui a été fait)
CORRECTIONS = [
    ("2026-10-12", ["formation-rupture-conventionnelle"],
     "Une question du quiz datait du 12 juin 2026 la loi qui réduit la durée d'indemnisation chômage après une rupture conventionnelle.",
     "Date corrigée : loi n° 2026-470 du 11 juin 2026, comme dans le reste du module."),
    ("2026-10-04", ["formation-anciennete-preavis", "simulateurs-anciennete-carriere", "simulateurs-rupture-contrat"],
     "Le droit à l'indemnité légale de licenciement (8 mois d'ancienneté) était apprécié à la fin du préavis.",
     "Il s'apprécie à la date d'envoi de la lettre de licenciement ; seul le montant se calcule sur l'ancienneté à la fin du préavis. Texte et cas pratique corrigés."),
    ("2026-09-19", ["droits-chomage"],
     "Une FAQ présentait le différé spécifique d'indemnisation avec l'ancien diviseur de 90.",
     "Remplacé par le diviseur de 2026 (111,8) et les plafonds du différé (150 jours, 75 jours en licenciement économique) ; calcul ajouté au simulateur."),
    ("2026-09-07", ["droits-chomage", "formation-chomage-are"],
     "La durée maximale d'indemnisation chômage était donnée à 27 mois dès 55 ans.",
     "Elle est de 22,5 mois de 55 à 56 ans et de 27 mois à partir de 57 ans (France Travail, Unédic)."),
    ("2026-08-27", ["reforme-rupture-conventionnelle-chomage-2026", "rupture-conventionnelle", "droits-chomage"],
     "La loi réduisant la durée d'indemnisation après une rupture conventionnelle était datée du 12 juin 2026, et l'ancienne durée maximale à 55 ans et plus donnée à 27,5 mois.",
     "Loi du 11 juin 2026 et durée de 27 mois, corrigées sur les trois pages."),
    ("2026-08-24", ["indemnite-depart-retraite"],
     "L'indemnité de mise à la retraite était présentée avec la même exonération d'impôt sur le revenu que l'indemnité de licenciement.",
     "Son plafond d'exonération fiscale est plus bas (5 fois le PASS au lieu de 6) : calcul, texte et FAQ corrigés."),
]

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]

def date_fr(iso):
    a, m, j = iso.split("-")
    j = int(j)
    return f"{'1ᵉʳ' if j == 1 else j} {MOIS[int(m) - 1]} {a}"

def lire_pages():
    pages = {}
    for f in sorted(glob.glob("*.html")):
        if f in EXCLUS:
            continue
        s = open(f, encoding="utf-8").read()
        pub = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})"', s)
        mod = re.search(r'"dateModified":\s*"(\d{4}-\d{2}-\d{2})"', s)
        if not (pub and mod):
            sys.exit(f"Dates JSON-LD absentes : {f}")
        nom = None
        bc = re.search(r'"@type":\s*"BreadcrumbList".*?"itemListElement":\s*(\[.*?\])\s*\}\s*</script>', s, re.S)
        if bc:
            try:
                nom = json.loads(bc.group(1))[-1]["name"]
            except Exception:
                nom = None
        if not nom:
            h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
            nom = html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
        slug = f[:-5]
        if slug.startswith("formation-"):
            nom = "Formation : " + nom
        elif slug.startswith("simulateurs-"):
            nom = "Simulateurs : " + nom
        url = "/" if slug == "index" else slug
        pages[slug] = {"url": url, "nom": "Accueil" if slug == "index" else nom,
                       "pub": pub.group(1), "mod": mod.group(1)}
    return pages

def lien(p):
    return f'<a href="{p["url"]}">{html.escape(p["nom"], quote=False)}</a>'

def bloc_corrections(pages):
    out = ['    <ul class="corrections">']
    for d, slugs, avant, apres in CORRECTIONS:
        for sl in slugs:
            if sl not in pages:
                sys.exit(f"Page inconnue dans CORRECTIONS : {sl}")
        liens = ", ".join(lien(pages[sl]) for sl in slugs)
        out.append(f'      <li><strong>{date_fr(d)}</strong> — {liens}<br>'
                   f'<em>Ce qui était inexact :</em> {html.escape(avant, quote=False)}<br>'
                   f'<em>Correction :</em> {html.escape(apres, quote=False)}</li>')
    out.append('    </ul>')
    return "\n".join(out)

def bloc_journal(pages):
    ev = defaultdict(lambda: {"pub": [], "mod": []})
    for sl, p in pages.items():
        ev[p["pub"]]["pub"].append(p)
        if p["mod"] != p["pub"]:
            ev[p["mod"]]["mod"].append(p)
    lancement = min(p["pub"] for p in pages.values())
    par_mois = defaultdict(list)
    for d in sorted(ev, reverse=True):
        par_mois[d[:7]].append(d)
    out = []
    for m in sorted(par_mois, reverse=True):
        a, mm = m.split("-")
        out.append(f'    <h3>{MOIS[int(mm) - 1].capitalize()} {a}</h3>')
        out.append('    <ul>')
        for d in par_mois[m]:
            e = ev[d]
            morceaux = []
            if e["mod"]:
                morceaux.append("mis à jour : " + ", ".join(lien(p) for p in sorted(e["mod"], key=lambda p: p["nom"])))
            if e["pub"] and d != lancement:
                morceaux.append("publié : " + ", ".join(lien(p) for p in sorted(e["pub"], key=lambda p: p["nom"])))
            if e["pub"] and d == lancement:
                morceaux.append(f'mise en ligne du site avec {len(e["pub"])} pages')
            out.append(f'      <li><strong>{date_fr(d)}</strong> — ' + " ; ".join(morceaux) + '.</li>')
            if e["pub"] and d == lancement:
                out.append('      <li><details><summary>Les pages publiées à l\'ouverture du site</summary><p>'
                           + ", ".join(lien(p) for p in sorted(e["pub"], key=lambda p: p["nom"])) + '.</p></details></li>')
        out.append('    </ul>')
    return "\n".join(out)

def main():
    gabarit = open("a-propos.html", encoding="utf-8").read()
    pages = lire_pages()
    date_mod = max([DATE_PUBLICATION] + [c[0] for c in CORRECTIONS])
    tete = gabarit[:gabarit.index("<title>")]
    head_fin = gabarit[gabarit.index('<link rel="preconnect"'):gabarit.index('<script type="application/ld+json">')]
    pub_ads = gabarit[gabarit.index('    <script async src="https://pagead2'):gabarit.index("<main id=\"main\">")]
    pied = gabarit[gabarit.index("</main>"):]
    favicons = re.search(r'<link rel="icon".*?\n', gabarit).group(0)
    url = f"{SITE}/{SLUG}"
    t, d = html.escape(TITLE), html.escape(DESC)
    meta = (f'<title>{t}</title>\n<meta name="description" content="{d}">\n<!-- SEO-META-START -->\n{favicons}'
            f'<link rel="canonical" href="{url}">\n<meta property="og:type" content="website">\n'
            f'<meta property="og:site_name" content="MesSimulateursRH.fr">\n<meta property="og:title" content="{t}">\n'
            f'<meta property="og:description" content="{d}">\n<meta property="og:url" content="{url}">\n'
            f'<meta property="og:image" content="{SITE}/og-image.png">\n<meta property="og:locale" content="fr_FR">\n'
            f'<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:title" content="{t}">\n'
            f'<meta name="twitter:description" content="{d}">\n<meta name="twitter:image" content="{SITE}/og-image.png">\n'
            f'<meta name="robots" content="index, follow">\n<!-- SEO-META-END -->\n')
    webpage = {"@context": "https://schema.org", "@type": "WebPage", "@id": url + "#webpage",
               "name": H1, "url": url, "inLanguage": "fr-FR", "description": DESC,
               "datePublished": DATE_PUBLICATION, "dateModified": date_mod,
               "author": {"@id": f"{SITE}/a-propos#nathan-penin"},
               "publisher": {"@id": f"{SITE}/#organization"}}
    fil = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Accueil", "item": f"{SITE}/"},
        {"@type": "ListItem", "position": 2, "name": "À propos de MesSimulateursRH.fr", "item": f"{SITE}/a-propos"},
        {"@type": "ListItem", "position": 3, "name": H1, "item": url}]}
    ld = "".join('<script type="application/ld+json">\n' + json.dumps(o, ensure_ascii=False, indent=2) + "\n</script>\n"
                 for o in (webpage, fil))
    corps = f'''<main id="main">
    <nav class="breadcrumb" aria-label="Fil d'Ariane">
      <a href="/">Accueil</a>
      <span class="sep" aria-hidden="true">›</span>
      <a href="a-propos">À propos</a>
      <span class="sep" aria-hidden="true">›</span>
      <span aria-current="page">{H1}</span>
    </nav>
  <section class="hero">
    <h1>{H1}</h1>
    <p>
      Les erreurs corrigées depuis la mise en ligne du site, et la date de la dernière mise à jour de chaque page. Une page de simulateur ou de guide qui change de contenu change aussi de date ; une correction de fond est en plus décrite ci-dessous.
    </p>
    <p class="update-date">Par <a href="a-propos">Nathan Penin</a>, éditeur du site. Dernière mise à jour le {date_fr(date_mod)}. <a href="a-propos">Notre méthode</a>.</p>
  </section>

  <section class="content-section">
    <h2 id="corrections">Corrections publiées</h2>
    <p>
      Sont listées ici les corrections d'une règle, d'un chiffre, d'une date ou d'un calcul qui figuraient en ligne, la plus récente en tête. Les retouches de forme (mise en page, liens, titres) et les corrections purement techniques (un bouton ou un affichage qui ne fonctionnait pas) n'y figurent pas. Chaque correction s'appuie sur au moins deux sources officielles, citées sur la page corrigée.
    </p>
{bloc_corrections(pages)}
    <p>
      Vous avez repéré une erreur ? Écrivez-nous depuis la <a href="contact">page de contact</a> en indiquant la page et les valeurs saisies : après vérification sur les textes officiels, la correction est faite sur la page et ajoutée à cette liste.
    </p>

    <h2 id="methode">Comment le site est tenu à jour</h2>
    <p>
      Le SMIC et le plafond de la Sécurité sociale sont recoupés automatiquement chaque mois avec les données officielles ; tout écart déclenche une vérification manuelle avant modification. Les réformes sont intégrées quand le texte est publié au Journal officiel, jamais avant (voir <a href="actualites#methode-reforme">comment une réforme est traitée</a>). Les barèmes annuels sont mis à jour au 1ᵉʳ janvier, dès la publication des montants officiels. Le détail de la méthode et des sources figure sur la page <a href="a-propos">À propos</a> ; les textes de référence sont rassemblés dans les <a href="ressources-officielles">ressources officielles</a>.
    </p>

    <h2 id="journal">Dernière mise à jour de chaque page</h2>
    <p>
      Chaque page apparaît à la date de sa publication et à celle de sa dernière modification de contenu (les dates précédentes ne sont pas conservées ici). Liste produite automatiquement à partir des dates déclarées par chaque page.
    </p>
{bloc_journal(pages)}

    <div class="related-tools">
      <h3>Aller plus loin</h3>
      <div class="links">
        <a href="a-propos">→ À propos : méthode et sources</a>
        <a href="actualites">→ Actualités du droit du travail</a>
        <a href="ressources-officielles">→ Ressources officielles</a>
        <a href="contact">→ Signaler une erreur</a>
      </div>
    </div>
  </section>

'''
    page = tete + meta + head_fin + ld + pub_ads + corps + pied
    open(SLUG + ".html", "w", encoding="utf-8").write(page)
    sm = open("sitemap.xml", encoding="utf-8").read()
    motif = re.compile(r"(<loc>" + re.escape(url) + r"</loc>\s*<lastmod>)\d{4}-\d{2}-\d{2}(</lastmod>)")
    if motif.search(sm):
        sm = motif.sub(r"\g<1>" + date_mod + r"\g<2>", sm)
        open("sitemap.xml", "w", encoding="utf-8").write(sm)
    else:
        print("Attention : page absente de sitemap.xml")
    print(f"{SLUG}.html écrit : {len(pages)} pages, {len(CORRECTIONS)} corrections, dateModified {date_mod}")

if __name__ == "__main__":
    main()
