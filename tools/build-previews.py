#!/usr/bin/env python3
"""
Hanaya theme — standalone preview builder.

Assembles each Twig page (header + page content + footer) with the compiled
app.css into a single openable HTML file under ./previews/, resolving the
Twig helpers we use to static placeholder values. This lets you preview the
theme page-by-page in a plain browser without a Salla server.

Run:  node node_modules/webpack-cli/bin/cli.js --mode production   (build CSS first)
      python tools/build-previews.py
Open: previews/home.html , previews/bonds.html
"""
import re, pathlib, html as _html

ROOT = pathlib.Path(__file__).resolve().parent.parent
PREV = ROOT / "previews"
PREV.mkdir(exist_ok=True)

CSS = (ROOT / "public/app.css").read_text(encoding="utf-8", errors="ignore")

def asset_uri(path_inside_images):
    # {{ 'images/...'|asset }} -> local file uri under src/assets
    return (ROOT / ("src/assets/" + path_inside_images)).as_uri()

def resolve_includes(s):
    # {% include 'pages.partials.hanaya.bonds-body' %} -> file contents
    def repl(m):
        dotted = m.group(1)
        rel = "src/views/" + dotted.replace(".", "/") + ".twig"
        p = ROOT / rel
        return p.read_text(encoding="utf-8") if p.exists() else ""
    return re.sub(r"\{%\s*include\s*'([^']+)'\s*%\}", repl, s)

def strip_twig(s):
    # resolve includes first so their twig gets processed too
    s = resolve_includes(s)
    # comments
    s = re.sub(r"\{#.*?#\}", "", s, flags=re.S)
    # {{ 'images/...'|asset }}
    s = re.sub(r"\{\{\s*'([^']+)'\s*\|\s*asset\s*\}\}", lambda m: asset_uri(m.group(1)), s)
    # {{ store.url }} and store.url/xxx
    s = re.sub(r"\{\{\s*store\.url\s*\}\}", "#", s)
    s = re.sub(r"\{\{\s*store\.name[^}]*\}\}", "Hanaya", s)
    s = re.sub(r"\{\{\s*store\.contacts\.email[^}]*\}\}", "care@hanaya.sa", s)
    s = re.sub(r"\{\{\s*store\.contacts\.phone[^}]*\}\}", "+966 505 40 50 20", s)
    s = re.sub(r"\{\{\s*store\.description[^}]*\}\}",
               "Jewellery crafted with precision — carrying meaning, and leaving an unforgettable impression.", s)
    s = re.sub(r"\{\{\s*store\.settings\.tax\.number[^}]*\}\}", "300052504300003", s)
    # any remaining {{ ... }} store/theme expression -> blank (preview only)
    s = re.sub(r"\{\{\s*(store|theme|page|user|cart)\.[^}]*\}\}", "", s)
    # {% if ... %}...{% endif %}: keep the first branch, drop {% else %}..., drop tags
    #   (good enough for preview; our conditionals are simple)
    s = re.sub(r"\{%\s*else\s*%\}.*?\{%\s*endif\s*%\}", "", s, flags=re.S)
    s = re.sub(r"\{%\s*if[^%]*%\}", "", s)
    s = re.sub(r"\{%\s*endif\s*%\}", "", s)
    # salla web components -> harmless placeholders so layout still reads
    s = re.sub(r"<salla-localization-modal[^>]*>.*?</salla-localization-modal>",
               "<span>English</span><span style='color:#F4F0E8'>|</span><span>Saudi Riyal</span>", s, flags=re.S)
    s = re.sub(r"<salla-localization-modal[^>]*/?>",
               "<span>English</span><span style='color:#F4F0E8'>|</span><span>Saudi Riyal</span>", s)
    s = re.sub(r"<salla-search[^>]*>.*?</salla-search>", "<span class='sicon-search' aria-hidden='true'>&#9906;</span>", s, flags=re.S)
    s = re.sub(r"<salla-search[^>]*/?>", "<span class='sicon-search' aria-hidden='true'>&#9906;</span>", s)
    s = re.sub(r"<salla-user-menu[^>]*>.*?</salla-user-menu>", "", s, flags=re.S)
    s = re.sub(r"<salla-user-menu[^>]*/?>", "", s)
    s = re.sub(r"<salla-cart-summary[^>]*>.*?</salla-cart-summary>",
               "<span aria-label='bag' style='display:inline-block;width:18px;height:20px;border:1.5px solid #221D17;border-radius:3px'></span>", s, flags=re.S)
    s = re.sub(r"<salla-social[^>]*>.*?</salla-social>", SOCIALS, s, flags=re.S)
    s = re.sub(r"<salla-social[^>]*/?>", SOCIALS, s)
    s = re.sub(r"<salla-payments[^>]*>.*?</salla-payments>", PAYMENTS, s, flags=re.S)
    s = re.sub(r"<salla-payments[^>]*/?>", PAYMENTS, s)
    # any leftover salla-* self-closing/paired -> drop
    s = re.sub(r"<salla-[a-z-]+[^>]*>.*?</salla-[a-z-]+>", "", s, flags=re.S)
    s = re.sub(r"<salla-[a-z-]+[^>]*/?>", "", s)
    # {% hook 'x' %} / {% hook x %}
    s = re.sub(r"\{%\s*hook[^%]*%\}", "", s)
    return s

SOCIALS = ("<div style='display:flex;gap:14px'>"
    + "".join(f"<span style='width:44px;height:44px;border-radius:50%;border:1px solid #C9C2B4;display:inline-flex;align-items:center;justify-content:center;color:#5B554B'>{i}</span>"
              for i in ("in", "@", "f", "X", "w")) + "</div>")
PAYMENTS = ("<div style='display:flex;gap:8px;flex-wrap:wrap'>"
    + "".join(f"<span style='border:1px solid #DBD5C8;background:#fff;padding:7px 13px;font-size:10.5px;letter-spacing:.06em;color:#5B554B'>{p}</span>"
              for p in ("mada", "Visa", "Mastercard", "Apple Pay", "STC Bank")) + "</div>")

def block(tw, name):
    m = re.search(r"\{%\s*block " + name + r"\s*%\}(.*?)\{%\s*endblock\s*%\}", tw, re.S)
    return m.group(1) if m else ""

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def build_page(page_twig_rel, out_name):
    header = strip_twig(read("src/views/components/header/header.twig"))
    footer = strip_twig(read("src/views/components/footer/footer.twig"))
    tw = read(page_twig_rel)
    content = strip_twig(block(tw, "content"))
    scripts = block(tw, "scripts")
    # drop bundled-JS <script> tags (home.js etc.), keep inline scripts (tab switcher)
    scripts = re.sub(r"<script[^>]*\|\s*asset[^>]*>\s*</script>", "", scripts)
    scripts = re.sub(r"<script[^>]*src=[^>]*>\s*</script>", "", scripts)
    scripts = strip_twig(scripts)

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hanaya — {out_name}</title>
<style>{CSS}</style>
<style>body{{margin:0}}.sr-only{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}</style>
</head><body class="theme-raed">
{header}
<main>{content}</main>
{footer}
{scripts}
</body></html>"""
    (PREV / out_name).write_text(doc, encoding="utf-8")
    # report unresolved twig
    left = len(re.findall(r"\{[{%]", doc))
    print(f"  {out_name:14} written  (unresolved twig tokens: {left})")

print("Building standalone previews -> previews/")
build_page("src/views/pages/index.twig", "home.html")
build_page("src/views/pages/bonds.twig", "bonds.html")
print("Open previews/home.html or previews/bonds.html in a browser.")
