# Revised thesis guide

The 26-page PDF explains the papers and SpecKit, with the approved immune-programme amendment on pages 22–26. It links immutable RC2 sources and the reviewed amendment commit separately. It is explanatory, not scientific execution authority.

Build with Python plus reportlab: `python build_guide.py`. The default font directory is macOS Supplemental Fonts; `THESIS_FONT_DIR` may point to a directory containing Arial.ttf, Arial Bold.ttf, Arial Italic.ttf and Georgia.ttf. Output is beside the builder; temporary review text goes to a generated system temporary directory. PDF metadata may change between builds. The checked deliverable hash is in PDF_VERIFICATION.json.

The original RC2-only guide remains in the parent workspace output directory. No source paper PDF, private dataset or patient-level result is included.
