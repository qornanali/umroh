"""Build the offline-capable GitHub Pages site (PWA) from catatan-umroh.html.

Usage: python3 scripts/build_site.py [src.html] [out_dir]
- Inlines Google Fonts as base64 so Arabic text renders offline.
- Wraps the artifact fragment in a full HTML document.
- Adds manifest, icons and a service worker for offline use.
"""
import base64, os, re, shutil, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "catatan-umroh.html")
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "_site")
pwa = os.path.join(ROOT, "pwa")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
KEEP_SUBSETS = {"arabic", "latin", "latin-ext"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=60).read()


html = open(src, encoding="utf-8").read()

# 1. Inline fonts
m = re.search(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/[^"]+)">', html)
css = get(m.group(1).replace("&amp;", "&")).decode()
faces = []
for subset, block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face \{.*?\})", css, re.S):
    if subset not in KEEP_SUBSETS:
        continue
    url = re.search(r"url\((https://[^)]+)\)", block).group(1)
    faces.append(block.replace(url, "data:font/woff2;base64," + base64.b64encode(get(url)).decode()))
html = html.replace(m.group(0), "<style>\n" + "\n".join(faces) + "\n</style>")
html = re.sub(r'<link rel="preconnect"[^>]*>\n?', "", html)
html = html.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")

# 2. Full document + PWA tags
head = (
    '<!doctype html>\n<html lang="id">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<link rel="manifest" href="manifest.webmanifest">\n'
    '<link rel="apple-touch-icon" href="apple-touch-icon.png">\n'
    '<meta name="theme-color" content="#1c5b48">\n'
    '<meta name="apple-mobile-web-app-capable" content="yes">\n'
    '<meta name="mobile-web-app-capable" content="yes">\n'
    '<meta name="apple-mobile-web-app-title" content="Umroh">\n'
    "<style>body{margin:0}[hidden]{display:none!important}img{max-width:100%}"
    ":root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n"
)
i = html.index("</style>", html.index("<style>\n/* Layout")) + len("</style>")
register = '<script>if("serviceWorker" in navigator){addEventListener("load",function(){navigator.serviceWorker.register("sw.js")})}</script>\n'
html = head + html[:i] + "\n</head>\n<body>\n" + html[i:] + "\n" + register + "</body>\n</html>\n"

# 3. Write site
shutil.rmtree(out, ignore_errors=True)
os.makedirs(out)
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html)
for f in ("manifest.webmanifest", "icon-192.png", "icon-512.png", "apple-touch-icon.png"):
    shutil.copy(os.path.join(pwa, f), out)
version = (os.environ.get("GITHUB_SHA") or time.strftime("%Y%m%d%H%M%S"))[:12]
sw = open(os.path.join(pwa, "sw.template.js"), encoding="utf-8").read().replace("__VER__", version)
open(os.path.join(out, "sw.js"), "w", encoding="utf-8").write(sw)
open(os.path.join(out, ".nojekyll"), "w").close()
print(f"Built {out} ({len(faces)} font faces, cache {version})")
