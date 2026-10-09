#!/usr/bin/env python3
"""Three original, explicitly labeled historical diagrams for Tarpon Springs.

These summarize the unchanged canonical narration. They are not archival images,
technical diving instructions, maps of precise migration routes, or quotations.
"""
from pathlib import Path
import argparse

from precise_youtube_assets import Diagram, BG, PANEL, WHITE, MUTED, GOLD, MINT


def tarpon(folder: Path):
    outputs = {}
    d = Diagram("Η σπογγαλιεία υπήρχε ήδη", "Η νέα τεχνική άλλαξε τον τρόπο της εργασίας")
    d.rect(115, 295, 615, 580)
    d.text(422, 410, "ΑΠΟ ΤΗΝ ΕΠΙΦΑΝΕΙΑ", 36, GOLD, True)
    d.text(422, 566, "Αγκίστρια", 69, WHITE, True)
    d.text(422, 678, "Συλλογή σφουγγαριών", 39, MINT)
    d.text(422, 756, "από τη βάρκα", 43, MINT)
    d.rect(870, 295, 615, 580)
    d.text(1177, 410, "ΚΑΤΑΔΥΣΗ", 43, GOLD, True)
    d.text(1177, 566, "Δύτες", 76, WHITE, True)
    d.text(1177, 678, "Εργασία κοντά", 44, MINT)
    d.text(1177, 756, "στον βυθό", 44, MINT)
    d.text(800, 590, "→", 91, GOLD, True)
    d.text(800, 969, "Η τοπική αλιεία δεν ξεκίνησε με την άφιξη των δυτών.", 41, WHITE)
    d.footer("Πρωτότυπο ιστορικό σχήμα · δεν αποτελεί οδηγίες αλιείας ή κατάδυσης")
    outputs[2] = d.save(folder, "02-hooking-and-diving")

    d = Diagram("1905 · Τζον Κόκορις", "Η κατάδυση για σφουγγάρια φτάνει στο Τάρπον Σπρινγκς")
    d.rect(135, 295, 1330, 565)
    d.text(800, 434, "Εμπειρία από την Ελλάδα", 61, GOLD, True)
    d.text(800, 559, "Δύτες στη συλλογή σφουγγαριών", 54, WHITE, True)
    d.line(375, 625, 1225, 625, MINT, 5)
    d.text(800, 729, "Νέες αφίξεις και νέες δουλειές", 54, MINT)
    d.text(800, 970, "Η τεχνογνωσία ταξιδεύει μαζί με τους ανθρώπους.", 43, WHITE)
    d.footer("Πρωτότυπη καρτέλα ιστορικού γεγονότος · όχι πορτρέτο του Κόκορις")
    outputs[3] = d.save(folder, "03-cocoris-1905")

    d = Diagram("Μια κοινότητα πέρα από την παραγωγή", "Τρεις σταθμοί στην ιστορία της σπογγαλιείας")
    rows = [("1908", "Ανταλλακτήριο σφουγγαριών", "Αποθήκευση και πώληση"),
            ("ΔΕΚΑΕΤΙΑ 1930", "Περίοδος μεγάλης άνθησης", "Η εργασία στηρίζει την οικονομία"),
            ("1939", "Ασθένεια στα σφουγγάρια", "Μείωση της παραγωγής")]
    for i, (date, heading, note) in enumerate(rows):
        y = 255 + i * 240
        d.rect(105, y, 1390, 205)
        d.text(340, y + 111, date, 36 if i == 1 else 62, GOLD, True)
        d.text(1000, y + 80, heading, 43, WHITE, True)
        d.text(1000, y + 148, note, 36, MINT)
    d.footer("Πρωτότυπο χρονολόγιο · ιστορική πινακίδα Τάρπον Σπρινγκς / Duke")
    outputs[7] = d.save(folder, "07-exchange-and-community")
    return outputs


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    for scene, path in tarpon(args.output.resolve()).items():
        print(scene, path)
