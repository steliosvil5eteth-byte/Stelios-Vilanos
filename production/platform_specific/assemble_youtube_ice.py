#!/usr/bin/env python3
"""Assemble reviewed photographic and precise schematic assets for one story.

This is a source inventory, not final audio approval or publication permission.
All three splash-photo candidates are excluded: they show falling cubes, not
an equilibrium flotation measurement. Revisited opening imagery is explicit.
"""
from pathlib import Path
import copy
import hashlib
import html
import json
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'production_20261009_platform_specific/recovery/youtube-01'


def clean(value):
    return html.unescape(re.sub('<[^>]+>', '', value)).strip()


def main():
    job = next(j for j in json.loads((ROOT / 'production_20261009_platform_specific/manifest.json').read_text())['jobs'] if j['id'] == '2026-10-09-youtube-01')
    script = BASE / 'script.txt'
    script.write_text(job['script'] + '\n')
    records = json.loads((BASE / 'selected_commons_metadata.json').read_text()) + json.loads((BASE / 'selected_commons_metadata_second.json').read_text())
    metadata = {r['title']: r['imageinfo'][0] for r in records}
    def photo(scene, title, filename, label, creator_display, context, kind='photograph'):
        info = metadata[title]
        ext = info['extmetadata']
        path = BASE / 'photos' / filename
        with Image.open(path) as im:
            size = list(im.size)
        return {'scene': scene, 'paragraph_index': scene, 'asset_label': label, 'context_label': label, 'source_title': title, 'source_page_url': info['descriptionurl'], 'media_url': info['thumburl'], 'creator': clean(ext['Artist']['value']), 'creator_display': creator_display, 'license': clean(ext['LicenseShortName']['value']), 'license_url': ext['LicenseUrl']['value'], 'historical_context': context, 'kind': kind, 'not_a_photograph': kind != 'photograph', 'layout': 'contain', 'crop_focus': [.5,.5], 'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size, 'dimensions_px': size}
    original_diagrams = json.loads((BASE / 'diagrams/diagram_metadata.json').read_text())
    def diagram(scene, index, label):
        item = copy.deepcopy(original_diagrams[index])
        item.update(scene=scene, paragraph_index=scene, asset_label=label, context_label=label, layout='contain', crop_focus=[.5,.5], creator_display='Ιστορίες που μας αγγίζουν', historical_context='Πρωτότυπο επεξηγηματικό σχήμα· όχι φωτογραφία ή μέτρηση', licensing_scope='Original contribution to the final CC BY-SA 4.0 adaptation; standalone image not externally released')
        return item
    opening = photo(1, 'File:Ice cubes on water.jpg', 'ice-cubes-water.jpg', 'Πραγματικός πάγος σε νερό · φωτογραφία 2014', 'Cleiton Andrade', 'Φωτογραφία 17/11/2014· όχι μέτρηση της αναλογίας βύθισης')
    closer = copy.deepcopy(opening)
    closer.update(scene=5, paragraph_index=5, asset_label='Το όριο ανάμεσα στον πάγο και το νερό', context_label='Το ίδιο ποτήρι · πιο κοντινή θέαση', layout='cover', crop_focus=[.5,.55], source_reuse_reason='Return to the same verified glass with a closer composition to connect the density explanation to its visible waterline; not an additional photograph or calibrated buoyancy experiment.')
    closing = copy.deepcopy(opening)
    closing.update(scene=9, paragraph_index=9, asset_label='Από το παγάκι στη ζωή μιας λίμνης', context_label='Επιστροφή στο αρχικό ποτήρι', source_reuse_reason='The canonical final scene explicitly returns to the opening glass to resolve the same question and deliver the complete CTA; no repeated narration or added padding.')
    assets = [opening,
              diagram(2, 0, 'Πυκνότητα: ίδια μάζα σε διαφορετικό όγκο'),
              photo(3, 'File:2006-01-14 Surface waves.jpg', 'water-surface.jpg', 'Επιφάνεια υγρού νερού · φωτογραφία 2006', 'Roger McLassus / DemonDeLuxe', 'Πραγματικά κύματα μετά από διαταραχή με ραβδί· όχι φωτογραφία μορίων'),
              photo(4, 'File:Ice Ih Crystal Lattice.png', 'ice-lattice.png', 'Επιστημονικό σχήμα της δομής του πάγου Ih', 'Psiĥedelisto / Dbuckingham42', 'Δημοσιευμένο επιστημονικό διάγραμμα· όχι μικροσκοπική φωτογραφία', 'scientific_diagram'),
              closer,
              diagram(6, 1, 'Περίπου 4°C: μέγιστη πυκνότητα νερού'),
              photo(7, 'File:Partly frozen Green Lake Seattle 2008.jpg', 'frozen-lake.jpg', 'Μερικώς παγωμένη Green Lake · Σιάτλ, 2008', 'Steve Voght', 'Πραγματική φωτογραφία 21/12/2008· μακρινές ανθρώπινες μορφές χωρίς αναγνωρίσιμα χαρακτηριστικά προσώπου'),
              diagram(8, 2, 'Σχηματική τομή: νερό κάτω από τον πάγο'),
              closing]
    inventory = {'schema_version':1, 'job_id':job['id'], 'story_id':job['story_id'], 'title':job['title'], 'platform':'youtube', 'brand_id':7076410, 'script_path':str(script), 'script_sha256':hashlib.sha256(job['script'].encode()).hexdigest(), 'script_file_sha256':hashlib.sha256(script.read_bytes()).hexdigest(), 'assets':assets, 'source_review':'ACTUAL_SOURCE_PHOTOS_AND_DIAGRAMS_VISUALLY_INSPECTED', 'source_research':job['sources'], 'source_review_notes':{'photographic_sources':3, 'licensed_scientific_diagram_sources':1, 'original_precision_diagrams':3, 'unique_source_files':7, 'intentional_within_story_returns':[5,9], 'splash_candidates_excluded':True, 'no_new_ai_generated_photographic_claim':True, 'actual_audio_listened':False, 'final_visual_review':False}, 'caption_path':str(BASE/'caption.txt')}
    (BASE/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n')
    credits = ['# Πάγος και νερό — πηγές και άδειες', '', 'Εννέα σκηνές, επτά διαφορετικά αρχεία. Οι σκηνές 5 και 9 επιστρέφουν σκόπιμα στην πραγματική φωτογραφία του αρχικού ποτηριού. Οι τρεις φωτογραφίες πτώσης πάγου δεν χρησιμοποιούνται ως απόδειξη επίπλευσης.', '', '## Επιστημονικές πηγές', '']
    credits += [f'- [{s["publisher"]}: {s["title"]}]({s["url"]})' for s in job['sources']]
    credits += ['', '## Εικόνες ανά σκηνή', '']
    for asset in assets:
        credits += [f'### Σκηνή {asset["scene"]}: {asset["asset_label"]}', '', f'Δημιουργός: {asset["creator"]}. {asset["historical_context"]}.', '', f'Πηγή: {asset["source_page_url"]}', '', f'Άδεια: [{asset["license"]}]({asset["license_url"]}).']
        if asset.get('source_reuse_reason'):
            credits += ['', 'Επιστροφή σε ήδη παρουσιασμένη φωτογραφία, όχι νέο φωτογραφικό τεκμήριο.']
        credits += ['']
    credits += ['## Προσαρμογή', '', 'Προστέθηκαν προσεκτική περικοπή στην κοντινή σκηνή, φόντο από την ίδια εικόνα, επιγραφές, συγχρονισμένοι ελληνικοί υπότιτλοι, συνθετική αφήγηση Νέστορας και πρωτότυπα επεξηγηματικά σχήματα. Η τελική οπτική προσαρμογή διατίθεται με CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/. Τα πρωτότυπα διατηρούν τις παραπάνω άδειες. Δεν δηλώνεται έγκριση από τους δημιουργούς ή τους επιστημονικούς οργανισμούς.', '', 'Τα σχήματα επισημαίνονται ως σχήματα. Οι συμβολικές κουκκίδες της πυκνότητας δεν αναπαριστούν μοριακούς δεσμούς· το θερμόμετρο δεν είναι πραγματική μέτρηση· η τομή δεν περιγράφει όλες τις λίμνες.', '']
    (BASE/'source_attributions.md').write_text('\n'.join(credits))
    caption = ('Γιατί το παγάκι επιπλέει, ενώ τόσα στερεά βυθίζονται; Η εξήγηση συνδέει τη δομή του νερού με τη ζωή κάτω από μια παγωμένη λίμνη.\n\n'
        'Επιστημονικές πηγές: https://www.usgs.gov/water-science-school/science/water-density · https://cordis.europa.eu/article/id/454697-why-does-ice-float\n\n'
        'Πραγματικές φωτογραφίες και σαφώς επισημασμένα επιστημονικά σχήματα. Συνθετική ελληνική αφήγηση με τη φωνή Νέστορας.\n\n'
        'Εικόνες: Cleiton Andrade (CC0), Roger McLassus / DemonDeLuxe (CC BY-SA 3.0), Steve Voght (CC BY-SA 2.0), Psiĥedelisto / Dbuckingham42 (CC BY-SA 4.0). Πρωτότυπα επεξηγηματικά σχήματα: Ιστορίες που μας αγγίζουν. Προστέθηκαν επιγραφές, κοντινή θέαση, υπότιτλοι και αφήγηση. Προσαρμογή: CC BY-SA 4.0 — https://creativecommons.org/licenses/by-sa/4.0/\n\n'
        'Αναλυτικές πηγές και άδειες: https://github.com/steliosvil5eteth-byte/Stelios-Vilanos/blob/main/production_20261009_platform_specific/recovery/youtube-01/source_attributions.md\n\n'
        'Αν σας άρεσε, ακολουθήστε για περισσότερα.\n\n#Νερό #Πάγος #Φυσική #Επιστήμη')
    (BASE/'caption.txt').write_text(caption+'\n')
    print(json.dumps({'inventory':str(BASE/'inventory.json'),'unique_sources':7,'scenes':9,'caption_characters':len(caption),'actual_audio_listened':False},ensure_ascii=False))


if __name__ == '__main__':
    main()
