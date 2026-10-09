#!/usr/bin/env python3
"""Build GPS, photovoltaics and Voyager from checked primary photos and diagrams."""
from pathlib import Path
import copy, hashlib, json, math
import assemble_youtube_lunar as art

ROOT = Path(__file__).resolve().parents[2]
REC = ROOT / 'production_20261009_platform_specific/recovery'
NASA = 'https://www.nasa.gov/nasa-brand-center/images-and-media/'
GPS = 'https://archive.gps.gov/multimedia/images/'
DVIDS = 'https://www.dvidshub.net/about/copyright'
VOYAGER_GALLERY = 'https://science.nasa.gov/gallery/the-making-of-the-voyager-golden-record/'

def job(n):
    return next(j for j in json.loads((ROOT/'production_20261009_platform_specific/manifest.json').read_text())['jobs'] if j['id'] == f'2026-10-09-youtube-{n:02d}')

def photo(base, scene, name, label, context, creator, page, license_name, license_url):
    receipts = json.loads((base/'photos/download_receipts.json').read_text())
    item = copy.deepcopy(next(x for x in receipts if Path(x['path']).name == name))
    assert item.get('status') == 200 and not item.get('error')
    item.update(scene=scene, paragraph_index=scene, asset_label=label, context_label=label,
                historical_context=context, source_title=context, source_page_url=page,
                creator=creator, creator_display=creator, license=license_name,
                license_url=license_url, kind='photograph', not_a_photograph=False,
                layout='contain', crop_focus=[.5,.5],
                rights_basis='Primary provider and photograph-specific rights checked for factual educational use with accurate attribution and no endorsement claim.')
    return item

def diagram(base, scene, filename, title, subtitle, context, draw, sources):
    im, d = art.canvas(title, subtitle)
    draw(d)
    art.DIAGRAMS = base/'diagrams'
    item = art.save_diagram(im, filename, title+' · επεξηγηματικό σχήμα', context, sources)
    item.update(scene=scene, paragraph_index=scene)
    return item

def box(d, y, title, detail='', color=art.LIGHT):
    d.rounded_rectangle((115,y,1165,y+190), radius=26, fill=color, outline='#BCD4DF', width=3)
    art.text(d,title,640,y+37,44,bold=True)
    if detail: art.text(d,detail,640,y+113,34)

def save(n, assets, intro, credits, notes, tags):
    j=job(n); base=REC/f'youtube-{n:02d}'; base.mkdir(parents=True,exist_ok=True)
    assets.sort(key=lambda x:x['scene']); assert [x['scene'] for x in assets] == list(range(1,10))
    (base/'script.txt').write_text(j['script']+'\n')
    inv={'schema_version':1,'job_id':j['id'],'story_id':j['story_id'],'title':j['title'],
         'platform':'youtube','brand_id':7076410,'script_path':str(base/'script.txt'),
         'script_sha256':hashlib.sha256(j['script'].encode()).hexdigest(),'assets':assets,
         'source_research':j['sources'],'caption_path':str(base/'caption.txt'),
         'source_review':'ACTUAL_SOURCE_AND_DIAGRAM_VISUAL_REVIEW_PENDING',
         'source_review_notes':{'notes':notes,'actual_audio_listened':False,'final_visual_review':False}}
    (base/'inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
    caption=intro+'\n\nΠηγές: '+' · '.join(s['url'] for s in j['sources'])+'\n\n'+credits+'\n\n'+notes+'\n\nΠρωτότυπα επεξηγηματικά σχήματα: Ιστορίες που μας αγγίζουν, CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/. Τα σχήματα δεν είναι φωτογραφίες ή μετρημένα δεδομένα. Προσαρμογή μεγέθους και ελληνικές λεζάντες, με διατήρηση ολόκληρης της φωτογραφικής σύνθεσης. Συνθετική ελληνική αφήγηση με τη φωνή Νέστορας.\n\nΑν σας άρεσε, ακολουθήστε για περισσότερα.\n\n'+tags
    (base/'caption.txt').write_text(caption+'\n')
    lines=['# '+j['title'],'',notes,'']
    for x in assets:
        lines += [f"## Σκηνή {x['scene']}: {x['asset_label']}",'',x['historical_context'],'',
                  f"Δημιουργός: {x['creator']}. Άδεια/όροι: {x['license']} — {x['license_url']}",'',
                  'Πηγή: '+x['source_page_url'],'','SHA256: '+x['sha256'],'']
        if x.get('url'): lines += ['Ακριβές αρχείο: '+x['url'],'']
        if x.get('source_reuse_reason'): lines += [x['source_reuse_reason'],'']
    lines += ['## Επιστημονικές και ιστορικές πηγές','']+[s['url'] for s in j['sources']]
    (base/'source_attributions.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'job':j['id'],'scenes':9,'unique':len({x['sha256'] for x in assets}),'caption_chars':len(caption)},ensure_ascii=False))

def gps():
    n=3; base=REC/'youtube-03'; sources=[s['url'] for s in job(n)['sources']]
    assets=[photo(base,1,'gps-launch.jpg','Εκτόξευση GPS IIR(M) · Αύγουστος 2009','Πραγματική εκτόξευση Delta II με τον τελευταίο GPS IIR(M), Αύγουστος 2009. Παρέχει ιστορικό πλαίσιο, όχι φωτογραφία δορυφόρου σε τροχιά.','United States Government',GPS,'Public domain',GPS),
            photo(base,7,'gps-control2020.jpg','Επίγειος έλεγχος GPS · Ιανουάριος 2020','Χειριστές στο κύριο κέντρο ελέγχου GPS, Schriever Air Force Base, Ιανουάριος 2020.','United States Government',GPS,'Public domain',GPS),
            photo(base,9,'gps-control2012.jpg','Κέντρο ελέγχου GPS · Σεπτέμβριος 2012','Πραγματικοί χειριστές στο κύριο κέντρο ελέγχου GPS, Schriever Air Force Base, Σεπτέμβριος 2012. Δεν παρουσιάζεται ως σημερινή λήψη.','United States Government',GPS,'Public domain',GPS)]
    def signal(d):
        box(d,330,'Δορυφόρος','Στέλνει τη θέση και τον χρόνο εκπομπής.')
        art.arrow(d,(640,550),(640,670)); art.text(d,'Διαδρομή του σήματος',920,585,32)
        box(d,700,'Δέκτης','Συγκρίνει τον χρόνο άφιξης.')
        art.text(d,'Χρόνος διαδρομής → εκτίμηση απόστασης',640,1025,41,bold=True)
        art.text(d,'Οι αποκλίσεις των ρολογιών απαιτούν διόρθωση.',640,1130,34)
    assets.append(diagram(base,2,'signal-timing.png','Θέση από τον χρόνο του σήματος','Επεξηγηματική ακολουθία — όχι σε κλίμακα','Η μέτρηση του χρόνου διαδρομής συνδέεται με την εκτίμηση απόστασης. Δεν εμφανίζεται αδιόρθωτος ψευδοχρόνος ως ακριβής φυσική απόσταση.',signal,sources))
    def four(d):
        for x,y,num in [(260,365,1),(1020,365,2),(260,750,3),(1020,750,4)]:
            d.rounded_rectangle((x-85,y-60,x+85,y+60),radius=14,fill='#CCE4EE',outline=art.BLUE,width=4)
            art.text(d,str(num),x,y-34,54,bold=True)
            art.arrow(d,(x+(85 if x<640 else -85),y),(560 if x<640 else 720,610),width=4)
        d.rounded_rectangle((545,560,735,675),radius=18,fill=art.TEAL);art.text(d,'Δέκτης',640,592,36,fill='white',bold=True)
        art.text(d,'Τουλάχιστον 4 δορυφόροι',640,935,48,bold=True)
        art.text(d,'3 συντεταγμένες θέσης + απόκλιση ρολογιού',640,1040,39)
        art.text(d,'Οι θέσεις στο σχήμα είναι συμβολικές.',640,1150,34)
    assets.append(diagram(base,3,'four-satellites.png','Γιατί χρειάζονται τέσσερις;','Συμβολική γεωμετρία — όχι πραγματική διάταξη τροχιών','Τέσσερις ανεξάρτητες μετρήσεις υποστηρίζουν τρεις χωρικές συντεταγμένες και τη μετατόπιση του ρολογιού δέκτη· υπό τις συνήθεις προϋποθέσεις της μεθόδου.',four,sources))
    def speed(d):
        box(d,350,'Επίδραση της κίνησης','Οι δορυφόροι κινούνται με μεγάλη ταχύτητα.')
        art.arrow(d,(640,575),(640,690))
        box(d,740,'Πιο αργός ρυθμός ρολογιού','Η συμβολή της ειδικής σχετικότητας.')
        art.text(d,'Σύγκριση με κατάλληλο επίγειο πλαίσιο αναφοράς.',640,1090,35)
    assets.append(diagram(base,4,'speed-effect.png','Η κίνηση επηρεάζει τον χρόνο','Ποιοτική εξήγηση — χωρίς πλαστές ενδείξεις ρολογιού','Η κινηματική συνεισφορά στον σχετικιστικό χρονισμό των GPS είναι αρνητική ως προς το κατάλληλο επίγειο πλαίσιο. Δεν αναπαριστά ανεξάρτητη φυσική μέτρηση.',speed,sources))
    def gravity(d):
        box(d,350,'Διαφορετικό βαρυτικό δυναμικό','Οι δορυφόροι βρίσκονται ψηλότερα από την επιφάνεια.')
        art.arrow(d,(640,575),(640,690))
        box(d,740,'Πιο γρήγορος ρυθμός ρολογιού','Η συμβολή της γενικής σχετικότητας.')
        art.text(d,'Στις τροχιές GPS αυτή η συνεισφορά υπερισχύει.',640,1090,36)
    assets.append(diagram(base,5,'gravity-effect.png','Η βαρύτητα επηρεάζει τον χρόνο','Ποιοτική εξήγηση — όχι μετρημένη τροχιά','Το υψηλότερο βαρυτικό δυναμικό στις τροχιές GPS δίνει θετική συνεισφορά στον ρυθμό των δορυφορικών ρολογιών, μεγαλύτερη από την αντίθετη κινηματική συνεισφορά.',gravity,sources))
    def combined(d):
        box(d,315,'Κίνηση: πιο αργά','Αρνητική συνεισφορά στον ρυθμό.')
        box(d,570,'Βαρυτικό δυναμικό: πιο γρήγορα','Μεγαλύτερη θετική συνεισφορά στις τροχιές GPS.')
        box(d,850,'Οι συνεισφορές δεν ακυρώνονται','Χρειάζονται σχετικιστικές διορθώσεις.','#DDF1E9')
        art.text(d,'Τα πλαίσια δεν παριστάνουν αριθμητικά μεγέθη.',640,1140,34)
    assets.append(diagram(base,6,'combined-effects.png','Δύο επιδράσεις, ένα αποτέλεσμα','Ποιοτική σύγκριση — χωρίς αριθμητικές αναλογίες','Συνδυασμός των δύο αντίθετων επιδράσεων χωρίς να υπονοούνται αριθμητικές τιμές ή κλίμακες από τα μεγέθη των πλαισίων.',combined,sources))
    def checks(d):
        box(d,320,'Ατμόσφαιρα','Επηρεάζει τη διάδοση του σήματος.')
        box(d,580,'Ρολόγια και τροχιές','Χρειάζονται παρακολούθηση και υπολογισμό.')
        box(d,840,'Συνδυασμός διορθώσεων','Η σχετικότητα είναι ένα μέρος της λύσης.','#DDF1E9')
        art.text(d,'Σχηματική οργάνωση παραγόντων, όχι πλήρης προσομοίωση.',640,1150,31)
    assets.append(diagram(base,8,'multiple-corrections.png','Πολλά επίπεδα ελέγχου','Επεξηγηματική οργάνωση των διορθώσεων','Ο χρονισμός GPS συνδυάζει σχετικότητα, επίγεια παρακολούθηση και επιδράσεις διάδοσης. Δεν αποτελεί πλήρες διάγραμμα πραγματικού εξοπλισμού.',checks,sources))
    save(n,assets,'Η θέση στο GPS εξαρτάται από ακριβή χρονισμό και από δύο σχετικιστικές επιδράσεις που δεν ακυρώνονται μεταξύ τους.',
         'Τρεις πραγματικές φωτογραφίες: United States Government / GPS.gov, δημόσιο κτήμα. Πηγές και άδεια: '+GPS,
         'Οι φωτογραφίες δείχνουν εκτόξευση το 2009 και επίγειο έλεγχο το 2020 και το 2012. Έξι πρωτότυπα σχήματα εξηγούν τη μέθοδο· οι τροχιές, οι χρόνοι και τα μεγέθη δεν προβάλλονται ως μετρημένα δεδομένα. Δεν υποδηλώνεται έγκριση από κρατικό φορέα.', '#GPS #Φυσική #Σχετικότητα #Επιστήμη')

def photovoltaics():
    n=7; base=REC/'youtube-07'; sources=[s['url'] for s in job(n)['sources']]
    usgs='https://www.usgs.gov/media/images/solar-panels'; wide='https://www.dvidshub.net/image/2803011/160818-n-il474-104'; close='https://www.dvidshub.net/image/2803212/160818-n-il474-048'
    assets=[photo(base,1,'solar-colorado.jpg','Φωτοβολταϊκά πλαίσια · Κολοράντο','Πραγματική εγκατάσταση φωτοβολταϊκών στο Κολοράντο, δημοσιευμένη από το USGS. Δεν δηλώνεται ημερομηνία που δεν τεκμηριώνεται.','Jessica K. Robertson / USGS',usgs,'Public domain',usgs),
            photo(base,2,'souda-panels.jpg','Φωτοβολταϊκά στη Σούδα · 18/8/2016','Συντήρηση πραγματικών φωτοβολταϊκών από τον Benjamin Dyer στη Σούδα της Κρήτης, 18 Αυγούστου 2016. Δεν αποτελεί μικροσκοπική φωτογραφία πυριτίου.','Heather Judkins / U.S. Navy',close,'Public domain',DVIDS),
            photo(base,9,'souda-maintenance.jpg','Συντήρηση εγκατάστασης · Σούδα, 2016','Συντήρηση στεγάστρου φωτοβολταϊκών στη Σούδα, 18 Αυγούστου 2016. Πραγματική εγκατάσταση, όχι φωτογραφία πειράματος θερμοκρασίας.','Heather Judkins / U.S. Navy',wide,'Public domain',DVIDS)]
    def carriers(d):
        d.rounded_rectangle((160,440,1120,920),radius=35,fill='#E5EDF2',outline='#A4BDC8',width=4)
        art.text(d,'Ημιαγωγός',640,470,43,bold=True)
        art.arrow(d,(330,280),(525,550),'#D49C28',10);art.text(d,'Φως',320,245,42,bold=True)
        for x,label,color in [(430,'e⁻',art.BLUE),(850,'+', '#BA6B2B')]:
            d.ellipse((x-95,630,x+95,820),fill=color);art.text(d,label,x,679,67,fill='white',bold=True)
        art.text(d,'Ηλεκτρόνιο',430,960,41,bold=True);art.text(d,'Οπή',850,960,41,bold=True)
        art.text(d,'Η οπή είναι απουσία ηλεκτρονίου, όχι πρωτόνιο.',640,1090,34)
        art.text(d,'Συμβολικά χρώματα και μέγεθος φορέων.',640,1160,33)
    assets.append(diagram(base,3,'charge-carriers.png','Το φως δίνει ενέργεια σε φορτία','Επεξηγηματικό σχήμα — όχι μικροσκοπική φωτογραφία','Η απορρόφηση κατάλληλων φωτονίων επιτρέπει τη δημιουργία ζευγών ηλεκτρονίου και οπής. Η οπή ορίζεται σωστά ως απουσία ηλεκτρονίου, όχι ως σωματίδιο πρωτονίου.',carriers,sources))
    def circuit(d):
        d.rounded_rectangle((145,385,670,905),radius=25,fill=art.LIGHT,outline='#ADC5CF',width=4)
        art.text(d,'Κυψέλη',407,600,50,bold=True)
        d.rectangle((145,385,670,430),fill=art.BLUE);d.rectangle((145,860,670,905),fill='#BA6B2B')
        art.text(d,'−',725,375,52,bold=True);art.text(d,'+',725,848,52,bold=True)
        d.line((670,410,1050,410,1050,545),fill=art.INK,width=8);d.line((1050,720,1050,883,670,883),fill=art.INK,width=8)
        d.ellipse((960,545,1140,725),outline=art.INK,width=7);d.line((985,571,1115,699),fill=art.INK,width=5);d.line((1115,571,985,699),fill=art.INK,width=5)
        art.arrow(d,(810,410),(980,410),art.BLUE);art.arrow(d,(980,883),(810,883),art.BLUE)
        art.text(d,'Εξωτερικό',1005,960,34);art.text(d,'φορτίο',1005,1010,34)
        art.text(d,'Βέλη: κίνηση ηλεκτρονίων στο εξωτερικό κύκλωμα.',640,1120,32)
        art.text(d,'Η συμβατική φορά ρεύματος είναι αντίθετη.',640,1180,31)
    assets.append(diagram(base,4,'closed-circuit.png','Τα φορτία χρειάζονται κύκλωμα','Λειτουργικό σχήμα — όχι συνδεσμολογία πραγματικού πάνελ','Σχηματική φωτοβολταϊκή κυψέλη με εξωτερικό φορτίο. Τα βέλη δηλώνουν ροή ηλεκτρονίων από τον αρνητικό προς τον θετικό ακροδέκτη μέσω του εξωτερικού φορτίου, όχι τη συμβατική φορά ρεύματος.',circuit,sources))
    def contacts(d):
        for row in range(3):
            for col in range(3):
                x=230+col*280;y=320+row*245
                d.rectangle((x,y,x+260,y+225),fill='#294A72',outline='white',width=5)
                for k in range(1,9):d.line((x+15,y+k*23,x+245,y+k*23),fill='#BFD1DD',width=3)
                for k in (75,185):d.line((x+k,y+10,x+k,y+215),fill='#E3E9EC',width=8)
        art.text(d,'Λεπτές μεταλλικές γραμμές: συλλογή φορτίων',640,1100,36,bold=True)
        art.text(d,'Συμβολικός αριθμός κυψελών και επαφών.',640,1170,32)
    assets.append(diagram(base,5,'cells-and-contacts.png','Από την κυψέλη στο πλαίσιο','Επεξηγηματικό σχέδιο — όχι φωτογραφία προϊόντος','Ενδεικτικό πλέγμα κυψελών και συλλεκτικών μεταλλικών επαφών. Ο αριθμός9 και η μορφή δεν παρουσιάζονται ως πρότυπο εμπορικού πάνελ.',contacts,sources))
    def inverter(d):
        box(d,310,'Φωτοβολταϊκό: συνεχές ρεύμα','DC', '#E3EFF8')
        art.arrow(d,(640,530),(640,605));box(d,630,'Αντιστροφέας','Μετατρέπει το DC σε AC.')
        art.arrow(d,(640,845),(640,905))
        art.text(d,'Δίκτυο: εναλλασσόμενο ρεύμα (AC)',640,965,43,bold=True)
        art.text(d,'Δεν απεικονίζεται συγκεκριμένο μοντέλο συσκευής.',640,1140,34)
    assets.append(diagram(base,6,'dc-ac-inverter.png','Ο ρόλος του αντιστροφέα','Επεξηγηματική ακολουθία της μετατροπής','Ο αντιστροφέας μετατρέπει το συνεχές ρεύμα του φωτοβολταϊκού σε εναλλασσόμενο για συμβατή χρήση δικτύου. Δεν αναπαριστά ηλεκτρονικό κύκλωμα ή πρόταση εγκατάστασης.',inverter,sources))
    def losses(d):
        for y,title,detail in [(300,'Ανάκλαση','Μέρος του φωτός δεν μπαίνει στην κυψέλη.'),(550,'Μη κατάλληλη απορρόφηση','Δεν αξιοποιούνται όλα τα φωτόνια.'),(800,'Θερμότητα','Μέρος της ενέργειας δεν γίνεται ηλεκτρισμός.')]:box(d,y,title,detail)
        art.text(d,'Ποιοτικοί παράγοντες, χωρίς ποσοστά ή αναλογίες.',640,1130,34)
    assets.append(diagram(base,7,'conversion-losses.png','Γιατί δεν μετατρέπεται όλο το φως;','Σχηματική οργάνωση των απωλειών — όχι δεδομένα','Ανάκλαση, φασματική μη αξιοποίηση και θερμικές απώλειες περιορίζουν τη φωτοβολταϊκή μετατροπή. Δεν αποδίδονται κατασκευασμένα ποσοστά.',losses,sources))
    def heat(d):
        box(d,335,'Υψηλότερη θερμοκρασία','Η ζέστη αλλάζει τη συμπεριφορά του υλικού.','#F7E8D9')
        art.arrow(d,(640,565),(640,670))
        box(d,715,'Μικρότερη τάση σε πολλές κυψέλες','Η απόδοση μπορεί να μειωθεί.','#E6EEF8')
        art.text(d,'Η σύγκριση αφορά ίδιο φωτισμό.',640,1030,40,bold=True)
        art.text(d,'Περισσότερη ζέστη δεν σημαίνει μεγαλύτερη απόδοση.',640,1140,34)
    assets.append(diagram(base,8,'temperature-voltage.png','Η ζέστη δεν είναι η πηγή ενέργειας','Ποιοτική σύγκριση — όχι εργαστηριακή μέτρηση','Για ίδιο φωτισμό, η αύξηση της θερμοκρασίας συνήθως μειώνει την τάση και την απόδοση φωτοβολταϊκών κυψελών. Δεν δίνεται καθολικό ποσοστό ή ψευδής πειραματική καμπύλη.',heat,sources))
    credits='Πραγματικές φωτογραφίες: Jessica K. Robertson / USGS — '+usgs+' (δημόσιο κτήμα). Heather Judkins / U.S. Navy — '+wide+' · '+close+' (δημόσιο κτήμα, όροι: '+DVIDS+'). The appearance of U.S. Department of War (DoW) visual information does not imply or constitute DoW endorsement.'
    save(n,assets,'Η ηλεκτρική παραγωγή ενός φωτοβολταϊκού ξεκινά από την ενέργεια του φωτός, τη δομή της κυψέλης και ένα εξωτερικό κύκλωμα.',credits,
         'Τρεις πραγματικές φωτογραφίες εγκαταστάσεων και έξι πρωτότυπα σχήματα. Οι λήψεις της Σούδας είναι από το 2016 και δείχνουν συντήρηση· δεν παρουσιάζονται ως πείραμα ή σημερινό ρεπορτάζ.', '#Φωτοβολταϊκά #Ενέργεια #Φυσική #Επιστήμη')

def voyager():
    n=10; base=REC/'youtube-10'; sources=[s['url'] for s in job(n)['sources']]
    specs=[(1,'casani-voyager2-1977.jpg','Voyager 2 και John Casani · 4/8/1977','Ο διευθυντής προγράμματος John Casani κρατά σημαία, με τον δίσκο και το κάλυμμα μπροστά και το Voyager2 στο βάθος, Cape Canaveral,4 Αυγούστου1977. Δεν επισημαίνεται ως Carl Sagan.','https://www.nasa.gov/image-article/mementos-of-earth/'),
           (2,'golden-record-cover.jpg','Ο χρυσός δίσκος και το κάλυμμά του','Πραγματική φωτογραφική σύνθεση: προστατευτικό κάλυμμα αριστερά και επιχρυσωμένος δίσκος δεξιά. Η σελίδα NASA πιστώνει NASA/JPL-Caltech.','https://science.nasa.gov/resource/voyager-golden-record/'),
           (3,'session-records1977.jpg','Προετοιμασία δίσκων · 29/6/1977','Πραγματικό στιγμιότυπο προετοιμασίας δίσκων, 29 Ιουνίου 1977, από το αρχείο κατασκευής του χρυσού δίσκου της NASA. Δεν αποδίδεται όνομα στο πρόσωπο χωρίς αρχειακή ταυτοποίηση.','https://science.nasa.gov/image-detail/voyager-recording-session-6-29-77-30885251025-o/'),
           (5,'session-preparation1977.jpg','Κατασκευή δίσκου · 29/6/1977','Διαφορετικό πραγματικό στιγμιότυπο προετοιμασίας/κατασκευής δίσκου, 29 Ιουνίου 1977. Η αρχειακή σελίδα ονομάζεται Recording Session, αλλά το καρέ δείχνει κατασκευή και δεν αποδίδεται συγκεκριμένος καταγραφόμενος ήχος.','https://science.nasa.gov/image-detail/voyager-recording-session-6-29-77-30249865513-o/'),
           (6,'engraved-cover1977.jpg','Οι χαραγμένες οδηγίες · 4/9/1977','Φωτογραφία του πραγματικού καλύμματος με τις συμβολικές οδηγίες,4 Σεπτεμβρίου1977. Διατηρείται ολόκληρο το ιστορικό αντικείμενο.','https://www.nasa.gov/image-article/instructions-for-aliens/'),
           (8,'mounting-record1977.jpg','Τοποθέτηση του χρυσού δίσκου · 1977','Πραγματική τοποθέτηση του δίσκου στο διαστημικό σκάφος το1977, όπως περιγράφεται από τη NASA.','https://science.nasa.gov/image-detail/the-golden-record-30269492703-o/')]
    assets=[photo(base,s,name,label,context,'NASA/JPL-Caltech',page,'NASA media use',NASA) for s,name,label,context,page in specs]
    def contents(d):
        box(d,315,'115 εικόνες','Επιλογές από τη ζωή και τον πολιτισμό της Γης.')
        box(d,575,'Φυσικοί ήχοι και μουσική','Κύματα, άνεμος, ζώα και διαφορετικοί πολιτισμοί.')
        box(d,835,'Χαιρετισμοί σε 55 γλώσσες','Ένα επιλεγμένο πορτρέτο της ανθρωπότητας.','#F6EFDA')
        art.text(d,'Δεν αναπαράγονται εδώ τα ηχητικά ή φωτογραφικά έργα.',640,1155,31)
    assets.append(diagram(base,4,'record-contents.png','Τι περιλαμβάνει ο δίσκος;','Επεξηγηματική σύνοψη του καταγεγραμμένου περιεχομένου','Ακριβείς δημοσιευμένοι αριθμοί NASA115εικόνες και55γλώσσες. Δεν χρησιμοποιούνται χωρίς άδεια οι ξεχωριστές προστατευόμενες φωτογραφίες ή μουσικές ηχογραφήσεις του δίσκου.',contents,sources))
    def destination(d):
        box(d,325,'Ένα μήνυμα από τη Γη','Μεταφέρεται πάνω στα Voyager.')
        art.arrow(d,(640,560),(640,720))
        d.ellipse((515,740,765,990),fill='#E8EDF5',outline='#BBC7D6',width=4);art.text(d,';',640,765,155,bold=True)
        art.text(d,'Υποθετικός παραλήπτης στο μακρινό μέλλον',640,1040,38,bold=True)
        art.text(d,'Δεν είχε προηγηθεί γνωστή επικοινωνία.',640,1150,35)
    assets.append(diagram(base,7,'unknown-destination.png','Ποιος θα μπορούσε να το βρει;','Συμβολική εξήγηση — χωρίς πραγματική επαφή ή διαδρομή','Ο δίσκος προοριζόταν για υποθετικό πολιτισμό που ίσως συναντούσε το σκάφος στο μέλλον. Δεν υπονοείται γνωστός εξωγήινος παραλήπτης ή προηγούμενη επικοινωνία.',destination,sources))
    ending=copy.deepcopy(next(x for x in assets if x['scene']==2));ending.update(scene=9,paragraph_index=9,asset_label='Ένα επιλεγμένο πορτρέτο της Γης',context_label='Επιστροφή στον πραγματικό δίσκο',source_reuse_reason='Deliberate final return to the same physical record and cover photograph, resolving the opening story; not an additional independent photograph.')
    assets.append(ending)
    credits='Έξι πραγματικές φωτογραφίες: NASA/JPL-Caltech. Πηγές: '+VOYAGER_GALLERY+' · https://science.nasa.gov/resource/voyager-golden-record/ · https://www.nasa.gov/image-article/instructions-for-aliens/ · https://www.nasa.gov/image-article/mementos-of-earth/ . Όροι χρήσης: '+NASA
    save(n,assets,'Ο χρυσός δίσκος των Voyager μεταφέρει ένα επιλεγμένο πορτρέτο της Γης: εικόνες, φυσικούς ήχους, μουσική και χαιρετισμούς.',credits,
         'Έξι διαφορετικές φωτογραφίες, δύο πρωτότυπα σχήματα και μία δηλωμένη επιστροφή στον ίδιο δίσκο. Οι άνθρωποι και οι διαδικασίες παρουσιάζονται με τις αρχειακές περιγραφές τους. Δεν αναπαράγονται μουσικές ηχογραφήσεις ή προστατευόμενες εικόνες από τα περιεχόμενα του δίσκου.', '#Voyager #Διάστημα #Ιστορία #NASA')

if __name__ == '__main__':
    gps(); photovoltaics(); voyager()
