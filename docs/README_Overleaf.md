Overleaf template (XeLaTeX) — Quick instructions

Files added:
- `main.tex` : XeLaTeX template configured for Vietnamese via `polyglossia` + `fontspec`.
- `refs.bib` : (not included) Create a BibTeX file named `refs.bib` if you want references.
- `images/` : create this folder and upload images used by the document.

How to use on Overleaf:
1. Create a new project on Overleaf ("Upload Project") and upload the `main.tex` file and any images or `refs.bib` you need.
2. In Overleaf, open the Menu (top-left) and set the TeX engine to XeLaTeX.
3. If you use bibliography with `biblatex` + `biber`, Overleaf will run biber automatically when you compile with XeLaTeX.
4. Compile. If you see font warnings, change the font name in `\setmainfont{}` to one available on Overleaf (e.g., "Times New Roman" usually works).

Local compilation (optional):
- On your machine with TeX Live or MiKTeX installed, compile with XeLaTeX:

```powershell
# from project root
xelatex main.tex
biber main
xelatex main.tex
xelatex main.tex
```

Notes:
- This template intentionally avoids packages requiring shell-escape (e.g., minted) to be Overleaf-friendly.
- For Vietnamese choose XeLaTeX (UTF-8) and set a font that supports Vietnamese diacritics.

If you want, I can:
- Add a sample `refs.bib` with one or two entries.
- Add a `Makefile` or PowerShell script to automate local builds.
- Convert the template to a Beamer presentation or thesis template.