#!/usr/bin/env python3
"""Original explanatory graphics for the scoped Alice Guy and Nellie Bly stories.

These are expressly identified as new diagrams, not purported archival objects.
They do not alter narration, download images, synthesize audio, or publish posts.
"""
from pathlib import Path
import argparse

from precise_youtube_assets import Diagram, BG, PANEL, WHITE, MUTED, GOLD, MINT


def alice(folder: Path):
    outputs = {}
    d = Diagram("Γαλλία · 1894", "Η αρχή μιας διαδρομής στον κινηματογράφο")
    d.rect(145, 290, 1310, 565)
    d.text(800, 419, "Άλις Γκι", 92, GOLD, True)
    d.text(800, 539, "Γραμματέας του Λεόν Γκωμόν", 57, WHITE, True)
    d.line(440, 608, 1160, 608, MINT, 5)
    d.text(800, 711, "Δίπλα στις νέες μηχανές", 54, MINT)
    d.text(800, 788, "της κινούμενης εικόνας", 54, MINT)
    d.text(800, 955, "Ένα επαγγελματικό ξεκίνημα κοντά σε ένα νέο μέσο.", 40, WHITE)
    d.footer("Πρωτότυπο χρονολόγιο · τεκμηρίωση: Library of Congress")
    outputs[2] = d.save(folder, "02-france-1894")

    d = Diagram("Η κινούμενη εικόνα αφηγείται", "Πρόσωπα, πλοκή και εναλλαγές σκηνών")
    for x, number, label in [(95, 1, "ΙΔΕΑ"), (635, 2, "ΣΚΗΝΕΣ"), (1175, 3, "ΤΑΙΝΙΑ")]:
        d.rect(x, 340, 330, 345)
        d.circle(x + 165, 427, 47, GOLD)
        d.text(x + 165, 445, number, 45, BG, True)
        d.text(x + 165, 575, label, 49, WHITE, True)
    d.text(530, 538, "→", 95, MINT, True)
    d.text(1070, 538, "→", 95, MINT, True)
    d.text(800, 822, "Από την καταγραφή στην αφήγηση", 65, GOLD, True)
    d.text(800, 925, "Η Άλις Γκι ήταν από τους πρωτοπόρους αυτής της δουλειάς.", 38, WHITE)
    d.footer("Πρωτότυπο σχήμα της αφήγησης · δεν περιέχει καρέ ιστορικής ταινίας")
    outputs[3] = d.save(folder, "03-narrative-film")

    d = Diagram("1912 · A Fool and His Money", "Ένας ανόητος και τα χρήματά του")
    d.rect(125, 270, 1350, 655)
    d.text(800, 402, "Σκηνοθεσία: Άλις Γκι Μπλασέ", 58, GOLD, True)
    d.text(800, 545, "Μία από τις πρώτες", 67, WHITE, True)
    d.text(800, 645, "αφηγηματικές ταινίες", 67, WHITE, True)
    d.text(800, 747, "με αποκλειστικά μαύρους ηθοποιούς", 53, MINT, True)
    d.text(800, 847, "Κωμωδία της εποχής του βωβού κινηματογράφου", 38, MUTED)
    d.footer("Πρωτότυπη καρτέλα ιστορικού γεγονότος · όχι αφίσα ή καρέ της ταινίας")
    outputs[5] = d.save(folder, "05-fool-and-his-money")

    d = Diagram("Η ιστορία ξαναβρίσκει τα τεκμήριά της", "Μαρτυρίες και έρευνα αποκαθιστούν μια δημιουργική διαδρομή")
    rows = [("Η ίδια η δημιουργός", "Αναζήτηση των ταινιών της · απομνημονεύματα"),
            ("Αρχεία και ερευνητές", "Εντοπισμός υλικού · έλεγχος της απόδοσης"),
            ("Διατήρηση και πρόσβαση", "Αποκατάσταση · επιστροφή του έργου στο κοινό")]
    for i, (heading, detail) in enumerate(rows):
        y = 270 + i * 235
        d.rect(115, y, 1370, 197)
        d.text(800, y + 77, heading, 54, GOLD, True)
        d.text(800, y + 145, detail, 39, WHITE)
    d.footer("Πρωτότυπο επεξηγηματικό σχήμα · όχι αναπαραγωγή απομνημονευμάτων")
    outputs[7] = d.save(folder, "07-rediscovering-evidence")
    return outputs


def bly(folder: Path):
    outputs = {}
    d = Diagram("Από το μυθιστόρημα στο πραγματικό ταξίδι", "Ιούλιος Βερν · ο φανταστικός γύρος του κόσμου σε 80 ημέρες")
    d.rect(110, 295, 610, 590)
    d.text(415, 425, "ΦΙΛΕΑΣ ΦΟΓΚ", 52, GOLD, True)
    d.text(415, 610, "80", 150, WHITE, True)
    d.text(415, 710, "ημέρες", 59, WHITE)
    d.text(415, 821, "Μυθιστορηματικός ήρωας", 34, MUTED)
    d.rect(880, 295, 610, 590)
    d.text(1185, 425, "ΝΕΛΙ ΜΠΛΑΪ", 52, GOLD, True)
    d.text(1185, 570, "Μπορεί να γίνει", 48, WHITE)
    d.text(1185, 657, "γρηγορότερα;", 54, MINT, True)
    d.text(1185, 821, "Πραγματική δημοσιογράφος", 34, MUTED)
    d.text(800, 611, "→", 100, MINT, True)
    d.footer("Πρωτότυπο διάγραμμα σύγκρισης · δεν παρουσιάζει ιστορικό εξώφυλλο")
    outputs[2] = d.save(folder, "02-fiction-to-reportage")

    d = Diagram("Ένα ταξίδι με πολλές συνδέσεις", "Η ταχύτητα κάθε μέσου δεν αρκούσε από μόνη της")
    items = [("ΠΛΟΙΟ", "Διάσχιση της θάλασσας"), ("ΛΙΜΑΝΙ", "Έγκαιρη ανταπόκριση"),
             ("ΤΡΕΝΟ", "Συνέχεια στην ξηρά"), ("ΝΕΑ ΣΥΝΔΕΣΗ", "Συντονισμός δρομολογίων")]
    for i, (heading, note) in enumerate(items):
        y = 265 + i * 175
        d.circle(220, y + 64, 48, GOLD)
        d.text(220, y + 82, i + 1, 42, BG, True)
        if i < 3:
            d.line(220, y + 113, 220, y + 173, MINT, 5)
        d.rect(345, y, 1140, 135)
        d.text(615, y + 58, heading, 38, MINT, True)
        d.text(1110, y + 94, note, 34, WHITE)
    d.footer("Πρωτότυπο σχήμα ανταποκρίσεων · όχι ακριβής χάρτης ή πλήρες δρομολόγιο")
    outputs[4] = d.save(folder, "04-transport-connections")

    d = Diagram("Δύο δημοσιογράφοι, αντίθετες κατευθύνσεις", "Η πραγματική διαδρομή έγινε και ανταγωνισμός εντύπων")
    d.rect(110, 285, 1380, 285)
    d.text(490, 389, "Νέλι Μπλάι", 62, GOLD, True)
    d.text(490, 476, "New York World", 45, WHITE)
    d.text(1110, 410, "ΑΝΑΤΟΛΙΚΑ →", 49, MINT, True)
    d.rect(110, 640, 1380, 285)
    d.text(530, 745, "Ελίζαμπεθ Μπίσλαντ", 56, GOLD, True)
    d.text(530, 833, "Cosmopolitan", 45, WHITE)
    d.text(1150, 767, "← ΔΥΤΙΚΑ", 49, MINT, True)
    d.footer("Πρωτότυπο σχήμα των κατευθύνσεων · χωρίς επινοημένες διαδρομές στον χάρτη")
    outputs[5] = d.save(folder, "05-two-journalists")

    d = Diagram("Το ταξίδι έγινε είδηση", "Η ανταπόκριση από τη διαδρομή έφτανε στους αναγνώστες")
    for i, (heading, detail) in enumerate([("ΤΑΞΙΔΙ", "Η ίδια η ρεπόρτερ στον δρόμο"),
                                          ("ΑΝΤΑΠΟΚΡΙΣΕΙΣ", "Νέα από την πορεία της"),
                                          ("ΑΝΑΓΝΩΣΤΕΣ", "Παρακολούθηση της περιπέτειας")]):
        y = 270 + i * 230
        d.rect(170, y, 1260, 185)
        d.text(800, y + 73, heading, 51, GOLD, True)
        d.text(800, y + 140, detail, 44, WHITE)
        if i < 2:
            d.text(800, y + 222, "↓", 43, MINT, True)
    d.footer("Πρωτότυπο διάγραμμα · δεν αναπαράγει ιστορικό πρωτοσέλιδο ή κείμενο")
    outputs[6] = d.save(folder, "06-news-and-readers")

    d = Diagram("25 Ιανουαρίου 1890 · η επιστροφή", "Η Νέλι Μπλάι ολοκληρώνει τον πραγματικό γύρο του κόσμου")
    d.rect(105, 280, 1390, 610)
    d.text(800, 450, "ΠΕΡΙΠΟΥ", 50, MUTED, True)
    d.text(640, 665, "72", 196, GOLD, True)
    d.text(1020, 649, "ημέρες", 74, WHITE, True)
    d.text(800, 814, "Γρηγορότερα από το μυθιστορηματικό όριο των 80 ημερών", 36, MINT)
    d.text(800, 984, "Αναχώρηση: 14 Νοεμβρίου 1889", 45, WHITE)
    d.footer("Πρωτότυπο χρονολόγιο · ο χρόνος δηλώνεται προσεγγιστικά")
    outputs[7] = d.save(folder, "07-seventy-two-days")
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--story", choices=["alice", "bly"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = (alice if args.story == "alice" else bly)(args.output.resolve())
    for scene, path in result.items():
        print(scene, path)
