#!/usr/bin/env python3
"""Original, auditable explanatory SVGs for the three scoped recovery stories.

These are labeled diagrams, never purported photographs or historical scans.
Calendar positions and numerical claims are computed rather than illustrated
approximately. This module neither changes narration nor publishes anything.
"""
from __future__ import annotations

import calendar
import html
import math
import subprocess
from pathlib import Path

W, H = 1600, 1120
BG, PANEL, WHITE, MUTED = "#0c1726", "#15263a", "#f4f7fb", "#b8c9d8"
GOLD, MINT, RED = "#f6c86b", "#80d8c5", "#ffb4a8"


class Diagram:
    def __init__(self, title: str, subtitle: str = ""):
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
                      f'<rect width="{W}" height="{H}" fill="{BG}"/>']
        self.text(800, 104, title, 64, WHITE, bold=True)
        if subtitle:
            self.text(800, 173, subtitle, 36, MUTED)

    def text(self, x, y, text, size=48, color=WHITE, bold=False, anchor="middle"):
        from PIL import ImageFont
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        available = 2 * min(x-60, W-60-x) if anchor == "middle" else W-60-x
        while size > 24 and ImageFont.truetype(font_path, size).getlength(str(text)) > available:
            size -= 1
        self.parts.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
                          f'font-family="DejaVu Sans" font-size="{size}" '
                          f'font-weight="{"bold" if bold else "normal"}" fill="{color}">{html.escape(str(text))}</text>')

    def rect(self, x, y, w, h, fill=PANEL, radius=24, stroke=None):
        border = f' stroke="{stroke}" stroke-width="3"' if stroke else ""
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"{border}/>')

    def line(self, x1, y1, x2, y2, color=MUTED, width=4):
        self.parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>')

    def circle(self, x, y, r, fill=PANEL, stroke=None, width=4):
        border = f' stroke="{stroke}" stroke-width="{width}"' if stroke else ""
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"{border}/>')

    def footer(self, text="Πρωτότυπο επεξηγηματικό διάγραμμα"):
        self.text(800, 1075, text, 32, MUTED)

    def save(self, folder: Path, name: str):
        folder.mkdir(parents=True, exist_ok=True)
        svg, png = folder / (name + ".svg"), folder / (name + ".png")
        if svg.exists() or png.exists():
            raise FileExistsError(f"Preserve existing diagram: {name}")
        svg.write_text("\n".join(self.parts + ["</svg>"]), encoding="utf-8")
        result = subprocess.run(["inkscape", str(svg), "--export-type=png", f"--export-filename={png}",
                                 "--export-width=1600", "--export-height=1120"], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr)
        from PIL import Image
        with Image.open(png) as im:
            im.load()
            if im.size != (W, H):
                raise RuntimeError("Unexpected diagram raster dimensions")
        return png


def month(d: Diagram, year: int, x: int, width: int = 670, y: int = 250):
    weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(year, 2)
    d.rect(x, y, width, 640)
    d.text(x + width/2, y+90, str(year), 78, GOLD, True)
    d.text(x + width/2, y+154, "ΦΕΒΡΟΥΑΡΙΟΣ", 32, MUTED)
    cw = (width-70)/7
    for col, name in enumerate(["Δε", "Τρ", "Τε", "Πε", "Πα", "Σα", "Κυ"]):
        d.text(x+35+cw*(col+.5), y+225, name, 30, MUTED)
    for row, week in enumerate(weeks):
        for col, day in enumerate(week):
            if not day:
                continue
            cx, cy = x+35+cw*(col+.5), y+298+row*63
            if day == 29:
                d.circle(cx, cy-15, 29, GOLD)
            d.text(cx, cy, day, 38, BG if day==29 else WHITE, day==29)
    d.text(x+width/2, y+598, f"{calendar.monthrange(year,2)[1]} ημέρες", 39, MINT, True)


def gregorian(folder: Path):
    outputs = {}
    d = Diagram("Μια ημέρα κάνει τη διαφορά", "Πραγματικές θέσεις ημερομηνιών στο Γρηγοριανό ημερολόγιο")
    month(d, 2000, 80); month(d, 2100, 850)
    d.text(800, 986, "Και τα δύο διαιρούνται με το 4. Μόνο το ένα με το 400.", 38, GOLD)
    d.footer(); outputs[1] = d.save(folder, "01-two-februaries")

    d = Diagram("Οι εποχές δεν μετρούν ακέραιες ημέρες", "Σχηματική σύγκριση · το πρόσθετο κλάσμα μεγεθύνεται για να φαίνεται")
    d.text(110, 340, "Ημερολόγιο χωρίς διόρθωση", 42, WHITE, anchor="start")
    d.rect(110, 380, 1120, 110, MINT); d.text(670, 453, "365 ημέρες", 50, BG, True)
    d.text(110, 600, "Κύκλος των εποχών · τροπικό έτος", 42, WHITE, anchor="start")
    d.rect(110, 640, 1120, 110, MINT)
    d.rect(1250, 640, 240, 110, GOLD)
    d.text(670, 713, "365 ημέρες", 50, BG, True); d.text(1370, 710, "+κλάσμα", 34, BG, True)
    d.text(800, 886, "≈ 365,2422 ημέρες", 72, GOLD, True)
    d.text(800, 962, "Η μικρή ετήσια διαφορά συσσωρεύεται.", 42, WHITE)
    d.footer("Πρωτότυπο διάγραμμα · προσεγγιστική σημερινή τιμή τροπικού έτους")
    outputs[3] = d.save(folder, "03-seasonal-fraction")

    d = Diagram("Η πρώτη διόρθωση: μία ημέρα στα τέσσερα", "Παράδειγμα κανονικής τετραετίας")
    for i, year in enumerate(range(2001,2005)):
        x=95+i*380; d.rect(x, 315, 340, 365)
        d.text(x+170, 427, str(year), 66, GOLD, True)
        d.text(x+170, 570, "366" if calendar.isleap(year) else "365", 86, MINT, True)
        d.text(x+170, 629, "ημέρες", 34, MUTED)
    d.text(800, 817, "1.461 ÷ 4 = 365,25", 76, GOLD, True)
    d.text(800, 913, "Λίγο περισσότερο από το τροπικό έτος.", 44, WHITE)
    d.footer(); outputs[4] = d.save(folder, "04-four-year-rule")

    d = Diagram("Η εξαίρεση στην εξαίρεση", "Τα έτη των αιώνων χρειάζονται ακριβή διαίρεση με το 400")
    for x, year, result, days, color in [(90,2000,"5",29,MINT),(850,2100,"5,25",28,RED)]:
        d.rect(x, 280, 660, 650)
        d.text(x+330, 409, str(year), 104, GOLD, True)
        d.text(x+330, 552, f"÷ 400 = {result}", 58, WHITE, True)
        d.text(x+330, 679, "Ακέραιο" if year==2000 else "Όχι ακέραιο", 42, color, True)
        d.text(x+330, 821, f"Φεβρουάριος: {days}", 44, color, True)
    d.footer(); outputs[6] = d.save(folder, "06-century-exception")

    d = Diagram("97 δίσεκτα έτη σε έναν κύκλο 400 ετών", "Παράδειγμα: 1601–2000 · υπολογισμένο με τον Γρηγοριανό κανόνα")
    counts = []
    for row, start in enumerate([1601,1701,1801,1901]):
        stop=start+99; count=sum(calendar.isleap(y) for y in range(start,stop+1));counts.append(count)
        yy=275+row*147
        d.text(255, yy+59, f"{start}–{stop}", 39, WHITE)
        for c in range(25):
            fill=MINT if c<count else PANEL
            d.circle(505+c*31, yy+45, 12, fill, None if c<count else RED, 3)
        d.text(1410, yy+65, str(count), 60, MINT, True)
    assert counts == [24,24,24,25] and sum(counts)==97
    d.text(800, 953, "24 + 24 + 24 + 25 = 97", 65, GOLD, True)
    d.footer("Κάθε γεμάτος κύκλος = ένα δίσεκτο έτος · κενός κύκλος = εξαίρεση αιώνα")
    outputs[7] = d.save(folder, "07-97-leap-years")

    d = Diagram("Ο Φεβρουάριος του 2100 έχει 28 ημέρες", "Ο κανόνας 4 / 100 / 400 κρατά τις εποχές κοντά στις ημερομηνίες")
    month(d, 2100, 455, 690, 245)
    d.text(800, 975, "365 + 97 ÷ 400 = 365,2425 ημέρες", 54, GOLD, True)
    d.footer("Μέση διάρκεια του Γρηγοριανού έτους · ακριβής ημερολογιακός υπολογισμός")
    outputs[9] = d.save(folder, "09-2100-closing")
    return outputs


def clock(d: Diagram, x, y, hour, minute=0, radius=175):
    d.circle(x, y, radius, PANEL, MINT, 6)
    for n in range(1, 13):
        a=math.radians(n*30-90)
        d.text(x+radius*.79*math.cos(a), y+radius*.79*math.sin(a)+13, n, 32, MUTED)
    for a, length, width, color in [((hour%12+minute/60)*30-90,.49,10,GOLD),(minute*6-90,.65,7,WHITE)]:
        a=math.radians(a);d.line(x,y,x+radius*length*math.cos(a),y+radius*length*math.sin(a),color,width)
    d.circle(x,y,11,GOLD)


def harrison(folder: Path):
    outputs={}
    d=Diagram("Γεωγραφικό μήκος: ανατολικά ή δυτικά", "Μετράμε γωνία από έναν μεσημβρινό αναφοράς")
    d.circle(800,585,310,PANEL,MINT,5)
    d.line(800,275,800,895,GOLD,5)
    d.parts.append('<ellipse cx="800" cy="585" rx="155" ry="310" fill="none" stroke="#b8c9d8" stroke-width="3"/>')
    d.line(490,585,1110,585,MUTED,3)
    d.text(800,955,"0° · μεσημβρινός αναφοράς",42,GOLD,True)
    d.text(245,550,"ΔΥΤΙΚΑ",54,MINT,True);d.text(1355,550,"ΑΝΑΤΟΛΙΚΑ",48,MINT,True)
    d.text(245,635,"←",100,GOLD,True);d.text(1355,635,"→",100,GOLD,True)
    d.footer("Σχηματική σφαίρα · χωρίς γεωγραφική απεικόνιση ακτών")
    outputs[2]=d.save(folder,"02-longitude-reference")

    d=Diagram("Μία ώρα αντιστοιχεί σε δεκαπέντε μοίρες", "Σύγκριση τοπικών ηλιακών ωρών · απλοποιημένο παράδειγμα")
    d.circle(800,555,252,PANEL,MINT,5)
    for i in range(24):
        a=math.radians(i*15-90)
        d.line(800+220*math.cos(a),555+220*math.sin(a),800+250*math.cos(a),555+250*math.sin(a),GOLD,4)
    d.text(800,552,"360°",112,GOLD,True);d.text(800,642,"24 ώρες",49,WHITE)
    d.text(800,915,"360° ÷ 24 = 15° ανά ώρα",68,MINT,True)
    d.footer("Πρωτότυπο διάγραμμα της σχέσης ηλιακής ώρας και γεωγραφικού μήκους")
    outputs[3]=d.save(folder,"03-fifteen-degrees")

    d=Diagram("Δύο ώρες, μία διαφορά γεωγραφικού μήκους", "Υποθετικό παράδειγμα · συγκρίσιμες τοπικές ηλιακές ώρες")
    clock(d,420,555,14);clock(d,1180,555,12)
    d.text(420,310,"ΤΟΠΟΣ ΑΝΑΦΟΡΑΣ",38,MUTED,True);d.text(1180,310,"ΘΕΣΗ ΤΟΥ ΠΛΟΙΟΥ",38,MUTED,True)
    d.text(420,821,"14:00",74,GOLD,True);d.text(1180,821,"12:00",74,GOLD,True)
    d.text(800,557,"2 ώρες",45,WHITE,True)
    d.text(800,970,"2 × 15° = 30° δυτικά της αναφοράς",57,MINT,True)
    d.footer("Επεξηγηματικό παράδειγμα · όχι αναπαράσταση ιστορικής μέτρησης του H4")
    outputs[4]=d.save(folder,"04-two-comparable-times")

    d=Diagram("Δεκαετίες εξέλιξης των χρονομέτρων", "John Harrison · ξυλουργός και αυτοδίδακτος ωρολογοποιός")
    rows=[("H1","1735","Παρουσίαση στο Λονδίνο"),("H2","1739","Δεύτερο χρονόμετρο"),("H3","1740–1759","Πολυετής ανάπτυξη"),("H4","1759","Ρολόι τύπου τσέπης")]
    for i,(h,year,note) in enumerate(rows):
        y=260+i*170;d.rect(120,y,1360,145)
        d.text(250,y+92,h,66,GOLD,True);d.text(635,y+92,year,51,MINT,True);d.text(1135,y+87,note,32,WHITE)
    d.footer("Πρωτότυπο χρονολόγιο · οι ημερομηνίες δεν δηλώνουν όλες πρώτη θαλάσσια δοκιμή")
    outputs[6]=d.save(folder,"06-development-timeline")

    d=Diagram("Η επιτυχία πέρασε από νέους ελέγχους", "Δοκιμές, διαφωνίες και όροι ανταμοιβής")
    rows=[("1761","Δοκιμή προς την Τζαμάικα"),("1764","Νέα δοκιμή στα Μπαρμπάντος"),("1765","Αξιολόγηση και όροι ανταμοιβής"),("1766","Συνέχιση ελέγχων στο Greenwich")]
    for i,(year,note) in enumerate(rows):
        y=260+i*170;d.circle(235,y+67,55,GOLD);d.text(235,y+80,year,33,BG,True)
        if i<3:d.line(235,y+124,235,y+181,MINT,4)
        d.rect(380,y,1080,138);d.text(920,y+85,note,42,WHITE)
    d.footer("Πρωτότυπο χρονολόγιο · δεν παρουσιάζει την ανταμοιβή ως άμεση ή χωρίς όρους")
    outputs[8]=d.save(folder,"08-tests-and-disputes")
    return outputs


def upca_bits(number: str) -> str:
    if len(number)!=12 or not number.isdigit():
        raise ValueError("UPC-A example must have twelve decimal digits")
    check=(10-(sum(int(x) for x in number[:11:2])*3+sum(int(x) for x in number[1:11:2]))%10)%10
    if check!=int(number[-1]):
        raise ValueError("UPC-A example check digit does not match")
    left=["0001101","0011001","0010011","0111101","0100011","0110001","0101111","0111011","0110111","0001011"]
    right=[x.translate(str.maketrans("01","10")) for x in left]
    result="101"+"".join(left[int(n)] for n in number[:6])+"01010"+"".join(right[int(n)] for n in number[6:])+"101"
    if len(result)!=95:
        raise ValueError("UPC-A symbol must have95 modules excluding quiet zones")
    return result


def barcode(folder: Path):
    outputs={};number="012345678905"
    d=Diagram("26 Ιουνίου 1974", "Η πρώτη εμπορική σάρωση UPC στο συγκεκριμένο ταμείο")
    d.rect(150,290,1300,230)
    d.text(800,392,"MARSH SUPERMARKET",70,GOLD,True)
    d.text(800,463,"Troy, Ohio · Ηνωμένες Πολιτείες",43,WHITE)
    d.rect(150,590,1300,250)
    d.text(800,696,"Μια συσκευασία με τσίχλες",58,WHITE,True)
    d.text(800,783,"Wrigley’s",72,MINT,True)
    d.text(800,964,"Ένα καθημερινό προϊόν · ένα κοινό πρότυπο",44,GOLD)
    d.footer("Πρωτότυπο διάγραμμα ιστορικού ορόσημου · όχι αρχειακή φωτογραφία ή απόδειξη")
    outputs[2]=d.save(folder,"02-1974-milestone")

    d=Diagram("Το ίδιο προϊόν, το ίδιο αναγνωριστικό", "Η κοινή ταυτοποίηση συνδέει διαφορετικά συστήματα")
    for x,t in [(120,"ΚΑΤΑΣΚΕΥΑΣΤΗΣ"),(870,"ΚΑΤΑΣΤΗΜΑ")]:
        d.rect(x,275,610,220);d.text(x+305,376,t,42,GOLD,True);d.text(x+305,451,"Ίδιο προϊόν",45,WHITE)
    d.line(425,505,650,650,MINT,7);d.line(1175,505,950,650,MINT,7)
    d.rect(280,650,1040,260)
    d.text(800,741,"ΚΟΙΝΟΣ ΑΡΙΘΜΟΣ ΠΡΟΪΟΝΤΟΣ",43,MINT,True)
    d.text(800,852,number,78,WHITE,True)
    d.footer("Κωδικός παραδείγματος · δεν αποδίδεται στη συσκευασία του 1974")
    outputs[3]=d.save(folder,"03-common-identifier")

    d=Diagram("Οι γραμμές κωδικοποιούν έναν αριθμό", "Παράδειγμα μοτίβου UPC-A · σκούρες μπάρες και φωτεινά κενά")
    x,y,module=120,325,12
    d.rect(x,y,1360,520,"#ffffff",16)
    bits=upca_bits(number);start=x+110
    for i,bit in enumerate(bits):
        if bit=="1":
            guard=(i<3 or 45<=i<50 or i>=92)
            d.rect(start+i*module,y+55,module,330 if guard else 300,"#101010",0)
    # Number text is deliberately a single explanatory line rather than a
    # claimed retail label. The machine-readable95-module pattern is exact.
    d.text(800,y+465,number,74,"#101010",True)
    d.text(800,960,"Το μοτίβο και ο αριθμός περιγράφουν την ίδια ταυτότητα.",39,MINT)
    d.footer("Αριθμός παραδείγματος · όχι ο κωδικός της ιστορικής συσκευασίας")
    outputs[4]=d.save(folder,"04-upca-pattern")

    d=Diagram("Ο αριθμός οδηγεί στις πληροφορίες", "Συνηθισμένος κωδικός συσκευασμένου προϊόντος · υποθετικό παράδειγμα")
    rows=[("ΤΥΠΩΜΕΝΟΣ ΚΩΔΙΚΟΣ",number,GOLD),("ΒΑΣΗ ΚΑΤΑΣΤΗΜΑΤΟΣ","Αναζήτηση του προϊόντος",MINT),("ΠΛΗΡΟΦΟΡΙΕΣ ΤΑΜΕΙΟΥ","Περιγραφή και τιμή",WHITE)]
    for i,(label,value,color) in enumerate(rows):
        yy=265+i*232;d.rect(180,yy,1240,180)
        d.text(800,yy+60,label,34,MUTED,True);d.text(800,yy+137,value,62,color,True)
        if i<2:d.text(800,yy+225,"↓",48,MINT,True)
    d.footer("Η τιμή ανακτάται από τη βάση · δεν εικονίζονται ειδικοί κώδικες μεταβλητού βάρους")
    outputs[5]=d.save(folder,"05-price-lookup")

    d=Diagram("Η ίδια συσκευασία, νέα τιμή στο σύστημα", "Υποθετικά ποσά για να φανεί ο διαφορετικός ρόλος των δεδομένων")
    d.rect(200,245,1200,215);d.text(800,335,"ΙΔΙΟΣ ΤΥΠΩΜΕΝΟΣ ΚΩΔΙΚΟΣ",37,MUTED,True);d.text(800,421,number,72,GOLD,True)
    for x,title,price,color in [(180,"ΠΡΙΝ","1,20 €",WHITE),(900,"ΜΕΤΑ","1,40 €",MINT)]:
        d.rect(x,565,520,310);d.text(x+260,662,title,41,MUTED,True);d.text(x+260,807,price,96,color,True)
    d.text(800,744,"→",90,GOLD,True)
    d.text(800,987,"Αλλαγή στη βάση του καταστήματος",47,WHITE)
    d.footer("Παράδειγμα · δεν αναφέρεται σε πραγματική τιμή Wrigley’s ή τιμή του 1974")
    outputs[6]=d.save(folder,"06-same-code-new-price")

    d=Diagram("Η πώληση συνδέεται με την καταγραφή", "Σχηματικό παράδειγμα αποθέματος σε ένα κατάστημα")
    d.rect(180,250,1240,190);d.text(800,326,"ΙΔΙΟ ΑΝΑΓΝΩΡΙΣΤΙΚΟ",34,MUTED,True);d.text(800,399,number,69,GOLD,True)
    for x,label,value,color in [(80,"ΑΡΧΙΚΟ ΑΠΟΘΕΜΑ","50",WHITE),(590,"ΠΩΛΗΣΗ","−1",GOLD),(1100,"ΝΕΟ ΑΠΟΘΕΜΑ","49",MINT)]:
        d.rect(x,565,420,300);d.text(x+210,640,label,30,MUTED,True);d.text(x+210,798,value,108,color,True)
    d.text(800,991,"Μία αναγνώριση, συνδεδεμένα δεδομένα",47,WHITE)
    d.footer("Πρωτότυπο διάγραμμα · υποθετικές ποσότητες, όχι ιστορικό αρχείο πωλήσεων")
    outputs[7]=d.save(folder,"07-connected-inventory")
    return outputs


if __name__ == "__main__":
    import argparse, json
    p=argparse.ArgumentParser();p.add_argument("--story",choices=["gregorian","harrison","barcode"],required=True);p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();make={"gregorian":gregorian,"harrison":harrison,"barcode":barcode}[args.story]
    print(json.dumps({k:str(v) for k,v in make(args.output).items()},ensure_ascii=False))
