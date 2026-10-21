"""Gera relatorio/relatorio.pdf e apresentacao/slides.pdf (Pandoc -> HTML -> Chrome/Edge headless).

relatorio/relatorio_fonte.md usa {{include caminho}} para reaproveitar os documentos de docs/ e resultados/.
Uso:  python -m scripts.build_pdfs
"""
import re
import shutil
import subprocess
from pathlib import Path

from app.config import ROOT

NAVEGADORES = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
               r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
               "google-chrome", "chromium", "msedge"]
MERMAID = ('<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>'
           '<script>mermaid.initialize({startOnLoad:true, theme:"neutral"});</script>')
INCLUDE = re.compile(r"\{\{include ([^}]+)\}\}")


def navegador() -> str:
    for n in NAVEGADORES:
        if Path(n).exists() or shutil.which(n):
            return n
    raise SystemExit("Chrome/Edge não encontrado")


def imprimir(html: Path, pdf: Path):
    subprocess.run([navegador(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=15000", f"--print-to-pdf={pdf}", html.as_uri()],
                   check=True, capture_output=True)
    print("gerado:", pdf.relative_to(ROOT))


def expandir_includes(fonte: Path) -> str:
    """Insere cada arquivo rebaixando seus títulos em dois níveis (# -> ###)."""
    def inserir(m):
        texto = (fonte.parent / m.group(1)).read_text(encoding="utf-8")
        return re.sub(r"^(#{1,4}) ", lambda h: "#" * min(len(h.group(1)) + 2, 6) + " ", texto, flags=re.M)
    return INCLUDE.sub(inserir, fonte.read_text(encoding="utf-8"))


def relatorio():
    md, html = ROOT / "relatorio" / "relatorio.md", ROOT / "relatorio" / "relatorio.html"
    md.write_text("<!-- gerado por scripts/build_pdfs.py a partir de relatorio_fonte.md; não editar -->\n"
                  + expandir_includes(ROOT / "relatorio" / "relatorio_fonte.md"), encoding="utf-8")
    subprocess.run(["pandoc", str(md), "-f", "gfm", "-t", "html5", "-s", "--metadata", "title=Relatório AV2",
                    "-c", "estilo.css", "-o", str(html)], check=True)
    # blocos ```mermaid viram <pre class="mermaid"> para o mermaid.js renderizar
    t = html.read_text(encoding="utf-8")
    t = t.replace('<pre class="mermaid"><code>', '<pre class="mermaid">').replace(
        '<pre lang="mermaid"><code>', '<pre class="mermaid">')
    t = re.sub(r'(<pre class="mermaid">.*?)</code></pre>', r"\1</pre>", t, flags=re.S)
    t = t.replace("</body>", MERMAID + "</body>")
    html.write_text(t, encoding="utf-8")
    imprimir(html, ROOT / "relatorio" / "relatorio.pdf")


def slides():
    imprimir(ROOT / "apresentacao" / "slides.html", ROOT / "apresentacao" / "slides.pdf")


if __name__ == "__main__":
    relatorio()
    slides()
