# -*- coding: utf-8 -*-
"""
Laver testfakturaerne i tools/invoice/fixtures/ - de filer, harness.mjs
koerer fakturalaeseren (flow/invoice-import/ReadInvoice.ts) paa.

    python3 tools/invoice/make_fixtures.py

KUN NAAR FIXTURES SKAL AENDRES. Filerne er committet, saa testene koerer
uden noget af det her. Den kraever det, der ikke er i requirements.txt:

    pip install reportlab fpdf2 pikepdf pillow
    Chromium (CHROME=sti, ellers Playwrights)

HVORFOR FLERE PDF-GENERATORER
-----------------------------
Hver generator skriver tekst paa sin egen maade, og det er praecis det,
laeseren skal kunne:

    reportlab   standardskrift (Helvetica, WinAnsi), ingen indlejret skrift
    pikepdf     den samme fil med objektstroemme og xref-stroem (PDF 1.5)
    Chromium    indlejrede skrifter (Type0/Identity-H + ToUnicode), to sider
                med gentaget tabelhoved
    TrueType    reportlab med indlejret skrift: egen kodning + ToUnicode,
                tysk layout, EUR-tegn i cellerne
    fpdf2       Unicode-skrift (DejaVu), "2 stk" i een celle
    Courier     ingen kolonneoverskrift - reservelaesningen
    norsk       varen paa to linjer, "1 245,00", leverandoer uden A/S
    scannet     kun et billede - skal give en advarsel, ikke gaet

Firmaerne er opdigtede. Koeberen er Oersted, fordi laeseren skal kunne
kende koeberens navn og CVR-nummer fra leverandoerens.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures")

BUYER = ["Ørsted Bioenergy & Thermal Power A/S", "Kraftværksvej 53", "7000 Fredericia", "CVR 36213728"]


# ---------------------------------------------------------------------------
# 1. reportlab: dansk, Helvetica, rabat og fortsaettelseslinjer
# ---------------------------------------------------------------------------
def da_reportlab(path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(path, pagesize=A4, pageCompression=1)
    c.setTitle("Faktura 2026-10458")
    w, h = A4
    y = h - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Nordisk Lejer & Transmission A/S")
    c.drawRightString(w - 40, y, "FAKTURA")
    c.setFont("Helvetica", 9)
    for i, t in enumerate(["Industrivej 14, 8600 Silkeborg", "Tlf. 86 80 12 34", "CVR-nr. 29847561"]):
        c.drawString(40, y - 16 - 12 * i, t)
    for i, (k, v) in enumerate([("Fakturanr.:", "2026-10458"), ("Fakturadato:", "14-09-2026"),
                                ("Deres ordre:", "4500987123"), ("Kundenr.:", "10233")]):
        c.drawString(360, y - 16 - 12 * i, k)
        c.drawString(450, y - 16 - 12 * i, v)
    y -= 90
    c.drawString(40, y, "Faktureres til:")
    for i, t in enumerate(BUYER):
        c.drawString(40, y - 12 * (i + 1), t)
    c.drawString(300, y, "Leveringsadresse:")
    for i, t in enumerate(["Ørsted, Studstrupværket", "Ny Studstrupvej 21", "8541 Skødstrup"]):
        c.drawString(300, y - 12 * (i + 1), t)
    y -= 90

    cols = [(40, "Nr.", "l"), (110, "Beskrivelse", "l"), (330, "Antal", "r"), (340, "Enhed", "l"),
            (440, "Enhedspris", "r"), (490, "Rabat %", "r"), (555, "Beløb", "r")]

    def row(vals, font="Helvetica", size=9):
        c.setFont(font, size)
        for (x, _h, al), v in zip(cols, vals):
            if not v:
                continue
            if al == "r":
                c.drawRightString(x, y, v)
            else:
                c.drawString(x, y, v)

    row([h_ for _x, h_, _a in cols], "Helvetica-Bold")
    c.line(40, y - 4, 555, y - 4)
    y -= 18
    lines = [
        ["6205-2RSH", "Kugleleje 6205-2RSH/C3 SKF", "10", "STK", "48,50", "10,00", "436,50"],
        [None, "Producent varenr: 6205-2RSH/C3"],
        ["22216-EK", "Tøndelejer 22216 EK, konisk boring", "2", "STK", "1.845,00", "", "3.690,00"],
        [None, "Fabrikat: SKF"],
        ["H316", "Spændehylster H316", "2", "STK", "412,75", "", "825,50"],
        ["FRAGT", "Fragt og ekspedition", "1", "STK", "195,00", "", "195,00"],
    ]
    for ln in lines:
        if ln[0] is None:
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(110, y + 3, ln[1])
            y -= 12
            continue
        row(ln)
        y -= 14
    y -= 10
    c.line(330, y + 8, 555, y + 8)
    for k, v in [("Subtotal ekskl. moms", "5.147,00"), ("Moms 25%", "1.286,75"), ("I alt DKK", "6.433,75")]:
        c.setFont("Helvetica-Bold" if k.startswith("I alt") else "Helvetica", 9)
        c.drawString(340, y, k)
        c.drawRightString(555, y, v)
        y -= 14
    c.setFont("Helvetica", 8)
    c.drawString(40, 60, "Betalingsbetingelser: Netto 30 dage. Bank: Danske Bank A/S, reg.nr. 1234 konto 1234567890")
    c.drawString(40, 48, "Nordisk Lejer & Transmission A/S · Industrivej 14 · 8600 Silkeborg · CVR 29847561")
    c.showPage()
    c.save()


# ---------------------------------------------------------------------------
# HTML-fakturaen til Chromium
# ---------------------------------------------------------------------------
CSS = """
body { font-family: 'Liberation Sans', Arial, sans-serif; font-size: 9pt; color: black; }
table.items { width: 100%; border-collapse: collapse; margin-top: 18px; }
table.items th { text-align: left; border-bottom: 1px solid gray; padding: 4px 6px; }
table.items td { padding: 3px 6px; vertical-align: top; }
.r { text-align: right !important; }
.head { display: flex; justify-content: space-between; }
table.meta td { padding: 1px 8px 1px 0; }
"""


def html_invoice(title, supplier, meta, parties, headers, rows, totals, footer):
    th = "".join(f'<th class="{"r" if r else ""}">{t}</th>' for t, r in headers)
    body = []
    for row_ in rows:
        body.append("<tr>" + "".join(
            f'<td class="{"r" if headers[i][1] else ""}">{v}</td>' for i, v in enumerate(row_)) + "</tr>")
    tot = "".join(f'<tr><td colspan="{len(headers) - 1}" class="r">{k}</td><td class="r">{v}</td></tr>'
                  for k, v in totals)
    meta_html = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in meta)
    parties_html = "".join(f'<div style="width:45%">{"<br>".join(p)}</div>' for p in parties)
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>
<style>{CSS}</style></head><body>
<div class="head"><div><b style="font-size:13pt">{supplier[0]}</b><br>{"<br>".join(supplier[1:])}</div>
<div><b style="font-size:13pt">{title}</b><table class="meta">{meta_html}</table></div></div>
<div class="head" style="margin-top:18px">{parties_html}</div>
<table class="items"><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody><tfoot>{tot}</tfoot></table>
<p style="margin-top:24px; font-size:8pt">{footer}</p>
</body></html>"""


def chrome_bin():
    env = os.environ.get("CHROME")
    if env:
        return env
    for p in ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome", shutil.which("chromium") or "",
              shutil.which("google-chrome") or ""):
        if p and os.path.exists(p):
            return p
    raise SystemExit("Chromium findes ikke - saet CHROME=<sti>")


def en_chrome(path):
    """Engelsk, EUR, 70 linjer over to sider - tabelhovedet gentages."""
    items = [("GSK-%03d" % (i + 1), "Spiral wound gasket DN%d PN40, 316L/graphite" % (25 + 5 * i),
              str((i % 4) + 1), "PCE", "%.2f" % (12.5 + 3.75 * i)) for i in range(70)]
    rows, sub = [], 0.0
    for no, desc, qty, uom, price in items:
        amt = int(qty) * float(price)
        sub += amt
        rows.append([no, desc, qty, uom, "{:,.2f}".format(float(price)), "{:,.2f}".format(amt)])
    html = html_invoice(
        "INVOICE", ["Brightline Industrial Supply Ltd", "Unit 4, Riverside Park", "Leeds LS9 0RD, United Kingdom",
                    "VAT Reg. No: GB123456789"],
        [("Invoice No:", "INV-2026-03317"), ("Invoice Date:", "September 2, 2026"),
         ("Your PO:", "4500991234"), ("Currency:", "EUR")],
        [["<b>Bill to</b>"] + BUYER, ["<b>Ship to</b>", "Ørsted A/S, Herningværket", "Vald. Poulsens Vej 2",
                                      "7400 Herning, Denmark"]],
        [("Item No.", False), ("Description", False), ("Qty", True), ("UoM", False), ("Unit Price", True),
         ("Line Total", True)],
        rows,
        [("Subtotal", "{:,.2f}".format(sub)), ("VAT 0% (reverse charge)", "0.00"),
         ("Total EUR", "{:,.2f}".format(sub))],
        "Payment terms: 30 days net. Barclays Bank PLC, IBAN GB00BARC00000000000000.")
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "invoice.html")
        with open(src, "w", encoding="utf-8") as f:
            f.write(html)
        subprocess.run([chrome_bin(), "--headless=new", "--no-sandbox", "--disable-gpu",
                        "--no-pdf-header-footer", "--print-to-pdf-no-header",
                        "--print-to-pdf=" + path, "file://" + src],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def de_truetype(path):
    """Tysk, EUR-tegn i cellerne, Pos.-kolonne foran varenummeret - med en
    INDLEJRET TrueType-skrift. reportlab koder den som en delmaengde med
    sin egen kodning (koderne er ikke WinAnsi), saa teksten kan kun laeses
    gennem skriftens ToUnicode-tabel."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    pdfmetrics.registerFont(TTFont("LibSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"))
    pdfmetrics.registerFont(TTFont("LibSansB", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"))
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 50
    c.setFont("LibSansB", 13)
    c.drawString(40, y, "Rheinische Dichtungstechnik GmbH")
    c.drawRightString(w - 40, y, "RECHNUNG")
    c.setFont("LibSans", 9)
    for i, t in enumerate(["Industriestraße 7, 50829 Köln", "USt-IdNr.: DE287654321"]):
        c.drawString(40, y - 16 - 12 * i, t)
    for i, (k, v) in enumerate([("Rechnungsnummer:", "RE-26-004711"), ("Rechnungsdatum:", "03.09.2026"),
                                ("Ihre Bestellung:", "4500976543")]):
        c.drawString(350, y - 16 - 12 * i, k)
        c.drawString(450, y - 16 - 12 * i, v)
    y -= 80
    c.drawString(40, y, "Rechnungsadresse")
    c.drawString(300, y, "Lieferadresse")
    for i, t in enumerate(BUYER):
        c.drawString(40, y - 12 * (i + 1), t)
    for i, t in enumerate(["Ørsted, Avedøreværket", "Hammerholmen 50", "2650 Hvidovre"]):
        c.drawString(300, y - 12 * (i + 1), t)
    y -= 80
    cols = [(40, "Pos.", "l"), (75, "Artikel-Nr.", "l"), (140, "Bezeichnung", "l"), (380, "Menge", "r"),
            (390, "ME", "l"), (480, "Einzelpreis", "r"), (555, "Gesamtpreis", "r")]
    rows = [
        ["Pos.", "Artikel-Nr.", "Bezeichnung", "Menge", "ME", "Einzelpreis", "Gesamtpreis"],
        ["10", "RD-4471", "O-Ring 120 x 5 FKM 75", "20", "Stk", "3,85 €", "77,00 €"],
        ["20", "RD-5120", "Radialwellendichtring 60x80x8 NBR", "6", "Stk", "7,40 €", "44,40 €"],
        ["30", "RD-9902", "Flachdichtung DN150 PN16 Graphit", "4", "Stk", "18,25 €", "73,00 €"],
        ["40", "", "Verpackung und Versand", "1", "Psch", "24,50 €", "24,50 €"],
    ]
    for n, r in enumerate(rows):
        c.setFont("LibSansB" if n == 0 else "LibSans", 9)
        for (x, _h, al), v in zip(cols, r):
            if v:
                (c.drawRightString if al == "r" else c.drawString)(x, y, v)
        if n == 0:
            c.line(40, y - 4, 555, y - 4)
        y -= 15
    y -= 8
    for k, v in [("Summe netto", "218,90 €"), ("USt. 0 % (Reverse Charge)", "0,00 €"), ("Gesamtbetrag", "218,90 €")]:
        c.drawString(390, y, k)
        c.drawRightString(555, y, v)
        y -= 13
    c.drawString(40, 60, "Zahlbar innerhalb 30 Tagen ohne Abzug. Sparkasse KölnBonn.")
    c.showPage()
    c.save()


# ---------------------------------------------------------------------------
# 4. fpdf2 med DejaVu: Type0-skrift, "2 stk" i antalskolonnen
# ---------------------------------------------------------------------------
def da_fpdf(path):
    from fpdf import FPDF
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.add_font("DejaVu", "", font)
    pdf.set_font("DejaVu", size=12)
    pdf.cell(0, 7, "Jysk Pumpeservice ApS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", size=9)
    for t in ["Håndværkervej 3, 7400 Herning", "CVR: 31415926"]:
        pdf.cell(0, 5, t, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for k, v in [("Faktura nr.", "88412"), ("Dato:", "22.08.2026"), ("Rekvisition:", "4500912345")]:
        pdf.cell(30, 5, k)
        pdf.cell(0, 5, v, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for t in BUYER:
        pdf.cell(0, 5, t, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    widths = [25, 85, 22, 28, 30]
    heads = ["Varenr.", "Varetekst", "Antal", "Stk.pris", "Beløb DKK"]
    aligns = ["L", "L", "R", "R", "R"]
    for wd, t, a in zip(widths, heads, aligns):
        pdf.cell(wd, 6, t, border="B", align=a)
    pdf.ln()
    rows = [["GP-118", "Akseltætning Grundfos CR 32, 22 mm", "2 stk", "1.249,00", "2.498,00"],
            [None, "Leveres fra fjernlager"],
            ["GP-205", "O-ring sæt EPDM, 48 dele", "1 sæt", "389,00", "389,00"],
            ["MK-9", "Miljøtillæg", "1 stk", "45,00", "45,00"]]
    for r in rows:
        if r[0] is None:
            pdf.cell(widths[0], 5, "")
            pdf.cell(widths[1], 5, r[1])
            pdf.ln()
            continue
        for wd, t, a in zip(widths, r, aligns):
            pdf.cell(wd, 6, t, align=a)
        pdf.ln()
    pdf.ln(4)
    for k, v in [("Varebeløb", "2.932,00"), ("Moms", "733,00"), ("At betale", "3.665,00")]:
        pdf.cell(sum(widths[:4]), 5, k, align="R")
        pdf.cell(widths[4], 5, v, align="R")
        pdf.ln()
    pdf.output(path)


def objstm(src, path):
    import pikepdf
    with pikepdf.open(src) as pdf:
        pdf.save(path, object_stream_mode=pikepdf.ObjectStreamMode.generate, compress_streams=True)


# ---------------------------------------------------------------------------
# 7. Courier uden kolonneoverskrift - reservelaesningen
# ---------------------------------------------------------------------------
def courier_loose(path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4)
    c.setFont("Courier", 9)
    y = A4[1] - 60
    text = [
        "Fyns Maskinservice A/S          Faktura 55012",
        "CVR 26535897                    Dato 01.10.2026",
        "",
        "6316-2Z     Kugleleje 6316-2Z            4 stk     312,00    1.248,00",
        "V-SPA1250   Kileremme SPA 1250           6 stk      38,90      233,40",
        "",
        "                                         I alt ekskl. moms   1.481,40",
    ]
    for t in text:
        c.drawString(40, y, t)
        y -= 12
    c.showPage()
    c.save()


# ---------------------------------------------------------------------------
# 8. norsk: varen paa to linjer, tusindtal med mellemrum, ingen A/S
# ---------------------------------------------------------------------------
def no_twoline(path):
    """Teksten staar over tallene, "1 245,00" er to ord, og leverandoeren
    har ingen selskabsform - navnet maa findes i brevhovedet."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    y = h - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Bergen Pumpeteknikk")
    c.drawRightString(w - 40, y, "FAKTURA")
    c.setFont("Helvetica", 9)
    for i, t in enumerate(["Sandviksveien 120, 5035 Bergen", "Org.nr. 987 654 321 MVA"]):
        c.drawString(40, y - 18 - 12 * i, t)
    for i, (k, v) in enumerate([("Fakturanummer:", "70412"), ("Fakturadato:", "15.09.2026"),
                                ("Deres ref.:", "4500993312"), ("Valuta:", "NOK")]):
        c.drawString(360, y - 18 - 12 * i, k)
        c.drawString(450, y - 18 - 12 * i, v)
    y -= 90
    for i, t in enumerate(BUYER):
        c.drawString(40, y - 12 * i, t)
    c.drawString(300, y, "Leveringsadresse:")
    for i, t in enumerate(["Ørsted, Asnæsværket", "Asnæsvej 16", "4400 Kalundborg"]):
        c.drawString(300, y - 12 * (i + 1), t)
    y -= 70
    cols = [(40, "Art.nr.", "l"), (110, "Beskrivelse", "l"), (360, "Antall", "r"), (370, "Enhet", "l"),
            (470, "Pris", "r"), (555, "Beløp", "r")]
    c.setFont("Helvetica-Bold", 9)
    for x, t, al in cols:
        (c.drawRightString if al == "r" else c.drawString)(x, y, t)
    c.line(40, y - 4, 555, y - 4)
    y -= 18
    c.setFont("Helvetica", 9)
    items = [("100-2045", "Pakningssett for pumpe NK 65-200", "2", "STK", "1 245,00", "2 490,00"),
             ("100-3310", "Mekanisk tetning 35 mm", "1", "STK", "3 870,50", "3 870,50")]
    for no, desc, qty, unit, price, amount in items:
        c.drawString(40, y, no)
        c.drawString(110, y, desc)
        y -= 12
        c.drawRightString(360, y, qty)
        c.drawString(370, y, unit)
        c.drawRightString(470, y, price)
        c.drawRightString(555, y, amount)
        y -= 16
    for k, v in [("Sum eks. mva", "6 360,50"), ("Mva 25 %", "1 590,13"), ("Totalt NOK", "7 950,63")]:
        c.drawString(370, y, k)
        c.drawRightString(555, y, v)
        y -= 13
    c.showPage()
    c.save()


# ---------------------------------------------------------------------------
# 9. scannet: kun et billede af en faktura
# ---------------------------------------------------------------------------
def scanned(path):
    from PIL import Image, ImageDraw
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    img = Image.new("L", (600, 300), 255)
    d = ImageDraw.Draw(img)
    for i, t in enumerate(["FAKTURA 123", "Kugleleje 6205  2 stk  48,50  97,00"]):
        d.text((20, 20 + 30 * i), t, fill=0)
    with tempfile.TemporaryDirectory() as tmp:
        png = os.path.join(tmp, "scan.png")
        img.save(png)
        c = canvas.Canvas(path, pagesize=A4)
        c.drawImage(png, 40, A4[1] - 400, width=500, height=250)
        c.showPage()
        c.save()


def main():
    os.makedirs(OUT, exist_ok=True)
    p = lambda n: os.path.join(OUT, n)
    da_reportlab(p("da_reportlab.pdf"))
    objstm(p("da_reportlab.pdf"), p("da_objstm.pdf"))
    en_chrome(p("en_chrome.pdf"))
    de_truetype(p("de_truetype.pdf"))
    da_fpdf(p("da_fpdf_unicode.pdf"))
    courier_loose(p("da_courier_loose.pdf"))
    no_twoline(p("no_twoline.pdf"))
    scanned(p("scanned.pdf"))
    for f in sorted(os.listdir(OUT)):
        print("%-28s %7d bytes" % (f, os.path.getsize(os.path.join(OUT, f))))


if __name__ == "__main__":
    sys.exit(main())
