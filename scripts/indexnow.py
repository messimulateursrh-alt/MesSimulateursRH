#!/usr/bin/env python3
"""IndexNow automatique (point 1.51, 12/10/2026).

Envoie a api.indexnow.org les adresses propres (sans .html) des pages
modifiees par un push, apres avoir attendu que Netlify serve la nouvelle
version. Seules les adresses presentes dans sitemap.xml sont envoyees
(404.html et toute page hors sitemap sont ignorees).

Usage :
  python3 scripts/indexnow.py --base <sha> --head <sha>   # pages modifiees
  python3 scripts/indexnow.py --all                        # tout le sitemap
  ajouter --dry-run pour afficher sans envoyer.
Aucun secret : la cle IndexNow est publique par conception (fichier a la racine).
"""
import argparse, hashlib, json, re, subprocess, sys, time, urllib.request, urllib.error

HOST = "messimulateursrh.fr"
SITE = "https://" + HOST
KEY = "e83325e11c5964a33526d3d5ff47cef4"
ENDPOINT = "https://api.indexnow.org/indexnow"
UA = "messimulateursrh-indexnow/1.0 (+https://github.com)"


def sitemap_urls():
    with open("sitemap.xml", encoding="utf-8") as f:
        return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", f.read())


def url_for(path):
    """index.html -> https://site/ ; page.html -> https://site/page"""
    if not path.endswith(".html") or "/" in path:
        return None
    name = path[:-5]
    return SITE + "/" if name == "index" else SITE + "/" + name


def changed_html(base, head):
    zero = re.fullmatch(r"0+", base or "") is not None
    rng = [head + "~1", head] if (not base or zero) else [base, head]
    out = subprocess.run(["git", "diff", "--name-only", "--diff-filter=AMR", *rng],
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.split() if p.endswith(".html")]


def fetch(url):
    req = urllib.request.Request(url + ("&" if "?" in url else "?") + "nocache=%d" % time.time(),
                                 headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def wait_for_deploy(path, url, max_wait=900, step=30):
    """Attend que la page en ligne soit identique au fichier pousse."""
    with open(path, "rb") as f:
        local = hashlib.sha256(f.read()).hexdigest()
    waited = 0
    while waited <= max_wait:
        try:
            if hashlib.sha256(fetch(url)).hexdigest() == local:
                print(f"Deploiement constate sur {url} apres {waited} s")
                return True
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  ({url} : {e})")
        time.sleep(step)
        waited += step
    print(f"::warning::{url} ne correspond toujours pas au fichier pousse apres {max_wait} s ; envoi quand meme")
    return False


def send(urls, dry):
    payload = {"host": HOST, "key": KEY, "keyLocation": f"{SITE}/{KEY}.txt", "urlList": urls}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if dry:
        print("--dry-run : rien n'est envoye")
        return 0
    req = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow : HTTP {r.status} pour {len(urls)} adresse(s)")
            return 0
    except urllib.error.HTTPError as e:
        print(f"::error::IndexNow : HTTP {e.code} {e.read()[:300]!r}")
        return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base"); ap.add_argument("--head", default="HEAD")
    ap.add_argument("--all", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-wait", action="store_true")
    a = ap.parse_args()

    in_sitemap = set(sitemap_urls())
    if a.all:
        urls, pairs = sorted(in_sitemap), []
    else:
        pairs = [(p, url_for(p)) for p in changed_html(a.base, a.head)]
        pairs = [(p, u) for p, u in pairs if u in in_sitemap]
        urls = [u for _, u in pairs]
    if not urls:
        print("Aucune page du sitemap modifiee : rien a envoyer.")
        return 0
    if pairs and not (a.no_wait or a.dry_run):
        wait_for_deploy(*pairs[0])
    # IndexNow accepte jusqu'a 10 000 adresses par envoi
    return send(urls[:10000], a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
