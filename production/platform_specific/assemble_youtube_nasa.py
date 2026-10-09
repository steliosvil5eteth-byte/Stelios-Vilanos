#!/usr/bin/env python3
"""Assemble Apollo12 and Webb from directly verified NASA photographs."""
from pathlib import Path
import copy, hashlib, json
import assemble_youtube_lunar as art

ROOT=Path(__file__).resolve().parents[2]
RECOVERY=ROOT/'production_20261009_platform_specific/recovery'
POLICY='https://www.nasa.gov/nasa-brand-center/images-and-media/'
APOLLO='https://www.nasa.gov/history/50-years-ago-return-to-the-moon/'
WEBB='https://science.nasa.gov/mission/webb/webbs-mirrors/'

def load_job(number):
    return next(j for j in json.loads((ROOT/'production_20261009_platform_specific/manifest.json').read_text())['jobs'] if j['id']==f'2026-10-09-youtube-{number:02d}')

def photo(base,scene,name,label,context,creator,page):
    receipts=json.loads((base/'photos/download_receipts.json').read_text())
    r=copy.deepcopy(next(x for x in receipts if Path(x['path']).name==name))
    r.update(scene=scene,paragraph_index=scene,asset_label=label,context_label=label,source_title=context,source_page_url=page,creator=creator,creator_display=creator,license='NASA media use',license_url=POLICY,rights_basis='NASA-credited factual educational/informational imagery under NASA media guidelines. No NASA endorsement represented. Third-party-only credited photographs were excluded.',historical_context=context,kind='photograph',not_a_photograph=False,layout='contain',crop_focus=[.5,.5])
    return r

def diagram(base,scene,name,label,context,im,sources):
    art.DIAGRAMS=base/'diagrams'
    r=art.save_diagram(im,name,label,context,sources)
    r.update(scene=scene,paragraph_index=scene)
    return r

def save(job,base,assets,intro,page,notes):
    base.mkdir(parents=True,exist_ok=True)
    (base/'script.txt').write_text(job['script']+'\n')
    unique=len({x['sha256'] for x in assets})
    photos=len({x['sha256'] for x in assets if x['kind']=='photograph'})
    diagrams=len({x['sha256'] for x in assets if x['kind']=='explanatory_diagram'})
    inv={'schema_version':1,'job_id':job['id'],'story_id':job['story_id'],'title':job['title'],'platform':'youtube','brand_id':7076410,'script_path':str(base/'script.txt'),'script_sha256':hashlib.sha256(job['script'].encode()).hexdigest(),'assets':assets,'source_research':job['sources'],'source_review':'PHOTOS_VISUALLY_REVIEWED_DIAGRAM_REVIEW_PENDING','source_review_notes':{'photographic_sources':photos,'original_precision_diagrams':diagrams,'unique_source_files':unique,'actual_audio_listened':False,'final_visual_review':False,'notes':notes},'caption_path':str(base/'caption.txt')}
    (base/'inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2)+'\n')
    creators=list(dict.fromkeys(x['creator'] for x in assets if x['kind']=='photograph'))
    caption=intro+'\n\nΠηγές ιστορίας / επιστήμης: '+' · '.join(s['url'] for s in job['sources'])+'\n\nΠραγματικές φωτογραφίες: '+', '.join(creators)+'. Πηγή φωτογραφιών: '+page+' · Όροι χρήσης: '+POLICY+'\n\n'+notes+f'\n\n{photos} διαφορετικές φωτογραφίες και {diagrams} πρωτότυπα επεξηγηματικά σχήματα. Τα σχήματα δεν είναι φωτογραφίες ή μετρημένα δεδομένα. Δημιουργία σχημάτων: Ιστορίες που μας αγγίζουν, CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/. Προστέθηκαν κάθετη σύνθεση, επιγραφές και υπότιτλοι. Συνθετική ελληνική αφήγηση με τη φωνή Νέστορας.\n\nΑν σας άρεσε, ακολουθήστε για περισσότερα.\n\n'+(' #Apollo12 #Διάστημα #Ιστορία #NASA' if base.name=='youtube-05' else '#Webb #Διάστημα #Φυσική #Επιστήμη')
    caption=caption.replace('1 πρωτότυπα επεξηγηματικά σχήματα','1 πρωτότυπο επεξηγηματικό σχήμα').replace('το1969','το 1969')
    (base/'caption.txt').write_text(caption+'\n')
    lines=['# '+job['title'],'',notes,'',f'{len(assets)} σκηνές, {unique} μοναδικά αρχεία: {photos} φωτογραφίες και {diagrams} επεξηγηματικά σχήματα.','']
    for x in assets:
        lines += [f"## Σκηνή {x['scene']}: {x['asset_label']}",'',x['historical_context'],'',f"Δημιουργός: {x['creator']}. Όροι: {x['license']} — {x['license_url']}",'',f"Πηγή: {x['source_page_url']}",'',f"SHA256: {x['sha256']}",'']
        if x.get('url'): lines += ['Ακριβές αρχείο: '+x['url'],'']
        if x.get('source_reuse_reason'): lines += [x['source_reuse_reason'],'']
    lines += ['## Επιστημονική / ιστορική τεκμηρίωση','']+[s['url'] for s in job['sources']]
    (base/'source_attributions.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'job':job['id'],'unique_sources':unique,'photographs':photos,'diagrams':diagrams,'caption_chars':len(caption),'inventory':str(base/'inventory.json')},ensure_ascii=False))

def apollo():
    job=load_job(5);base=RECOVERY/'youtube-05';sources=[s['url'] for s in job['sources']]
    specs=[(1,'lcc-countdown.jpg','Κέντρο εκτόξευσης · 14 Νοεμβρίου 1969','Αίθουσα ελέγχου εκτόξευσης2 στο Kennedy Space Center κατά την τελική αντίστροφη μέτρηση. Δεν είναι το Mission Control του Χιούστον.'),(2,'lightning.jpg','Κεραυνός στην εξέδρα 39A · 14/11/1969','Πραγματική καταγραφή κεραυνού στην εξέδρα39A λίγο μετά την εκτόξευσηApollo12. Δεν αποτελεί ανακατασκευή ΤΝ.'),(3,'ascent.jpg','Apollo 12 · άνοδος μέσα στη βροχή','Η άνοδος του Apollo12 όπως καταγράφηκε από τον πύργο εκτόξευσης· διακρίνονται σταγόνες στον φακό.'),(4,'griffin-kraft.jpg','Κέντρο ελέγχου · Griffin και Kraft','Ο διευθυντής πτήσης Gerald Griffin καθιστός και ο Christopher Kraft στο Mission Control κατά την εκτόξευση. Η σκηνή δίνει το πλαίσιο του κέντρου ελέγχου· κανείς τους δεν επισημαίνεται ως John Aaron.'),(6,'crew.jpg','Άλαν Μπιν (δεξιά) · πλήρωμα Apollo 12','Επίσημο πορτρέτο πληρώματος: Charles Conrad αριστερά, Richard Gordon στο κέντρο και Alan Bean δεξιά,1969.'),(7,'mcc-coast.jpg','Κέντρο ελέγχου · πορεία προς τη Σελήνη','Mission Control κατά τη διάρκεια τηλεοπτικής μετάδοσης στην πορεία προς τη Σελήνη. Όχι φωτογραφία της στιγμής αλλαγής του διακόπτη.'),(8,'earth-sla.jpg','Γη · μετά την αναχώρηση, 14/11/1969','ΦωτογραφίαApollo12 AS12-50-7326: η Γη και αποχωρισμένο πάνελ προσαρμογέα μετά την αναχώρηση προς τη Σελήνη. Όχι λήψη μέσα από το Mission Control ή από σεληνιακή τροχιά.'),(9,'moon-crescent.jpg','Η Σελήνη από το Apollo 12 · 1969','Η ημισέληνος όπως την είδε το πλήρωμαApollo12 λίγο πριν μπει σε σεληνιακή τροχιά. Ιστορική φωτογραφία, όχι σύγχρονη καταγραφή.')]
    assets=[photo(base,s,n,l,c,'NASA',APOLLO) for s,n,l,c in specs]
    im,d=art.canvas('SCE: επαναφορά των δεδομένων','Επεξηγηματικό σχήμα — όχι πραγματικός πίνακας οργάνων')
    for y,label in [(315,'Σήματα από αισθητήρες'),(570,'SCE · επεξεργασία σήματος'),(930,'Δεδομένα προς το κέντρο ελέγχου')]:
        d.rounded_rectangle((140,y,1140,y+145),radius=24,fill=art.LIGHT,outline='#AACCD9',width=4)
        art.text(d,label,640,y+47,43,bold=True)
    art.arrow(d,(640,475),(640,555));art.arrow(d,(640,805),(640,910))
    art.text(d,'Εφεδρική επιλογή: NORMAL → AUX',640,745,41,fill=art.TEAL,bold=True)
    art.text(d,'Η τηλεμετρία βοήθησε στον έλεγχο των συστημάτων.',640,1155,33)
    assets.append(diagram(base,5,'sce-telemetry.png','SCE και τηλεμετρία · επεξηγηματικό σχήμα','Απλουστευμένη λειτουργική ακολουθία αισθητήρων/SCE/τηλεμετρίας. Η αλλαγή σεAUX αναπαρίσταται ως επιλογή λειτουργίας, όχι ως πραγματική ηλεκτρολογική συνδεσμολογία ή επισκευή όλων των συστημάτων.',im,sources));assets.sort(key=lambda a:a['scene'])
    save(job,base,assets,'Apollo 12: δύο κεραυνοί, αλλοιωμένα δεδομένα και μια κρίσιμη εντολή από το κέντρο ελέγχου.',APOLLO,'Οι λήψεις προέρχονται από το Apollo 12 το1969. Οι Griffin και Kraft επισημαίνονται με τα σωστά ονόματα· δεν παρουσιάζονται ως John Aaron. Το πορτρέτο δείχνει τον Alan Bean δεξιά. Η τηλεμετρία εξηγείται με ένα λειτουργικό σχήμα, όχι με κατασκευασμένο πίνακα οργάνων.')

def webb():
    job=load_job(6);base=RECOVERY/'youtube-06';sources=[s['url'] for s in job['sources']]
    specs=[(1,'primary-mirror.jpg','Webb · κατασκευή στο NASA Goddard','Ο κύριος χρυσός καθρέφτης στο καθαρό δωμάτιο του NASA Goddard, μετά την αφαίρεση των προστατευτικών καλυμμάτων το2016.','NASA / Chris Gunn'),(3,'mirror-overhead.jpg','Κύριος καθρέφτης · θέα από πάνω','Πραγματική άνω όψη με τις δοκούς του δευτερεύοντος καθρέφτη διπλωμένες, πριν εγκατασταθούν τα επιστημονικά όργανα.','NASA / Desiree Stover'),(4,'cryo-inspection.jpg','Τμήμα κατόπτρου · κρυογενική δοκιμή','Μηχανικοί επιθεωρούν τμήμα κατόπτρου στο Marshall Space Flight Center για κρυογενική δοκιμή. Πραγματικό εξάρτημα και διαδικασία.','NASA / MSFC / E. Given'),(5,'flight-segment.jpg','Έλεγχος επιχρυσωμένου τμήματος · Goddard','Τεχνικοί επιθεωρούν ένα από τα δύο πρώτα τμήματα πτήσης στο καθαρό δωμάτιο του Goddard το2012. Η φωτογραφία δεν αποδεικνύει από μόνη της αριθμητική μέτρηση πάχους.','NASA / Chris Gunn'),(9,'chamber-a.jpg','Webb · θάλαμος A, 18/11/2017','Το Webb μέσα στον θάλαμοA του NASA Johnson μετά την ολοκλήρωση των κρυογενικών δοκιμών,18 Νοεμβρίου2017.','NASA / Chris Gunn')]
    assets=[photo(base,s,n,l,c,cr,WEBB) for s,n,l,c,cr in specs]
    im,d=art.canvas('Πέρα από το κόκκινο','Επεξηγηματικό σχήμα — τα εύρη δεν είναι σε κλίμακα')
    for x,label,color in [(95,'Υπεριώδες','#E8E4F6'),(475,'Ορατό','#EEF2F4'),(855,'Υπέρυθρο','#F7E8D7')]:
        d.rounded_rectangle((x,440,x+330,725),radius=26,fill=color)
        art.text(d,label,x+165,480,42,bold=True)
    colors=['#693EA0','#4054B2','#4AABC2','#3D9D65','#DED15C','#D98B42','#B94945']
    for i,c in enumerate(colors):d.rectangle((490+i*43,580,533+i*43,660),fill=c)
    art.arrow(d,(145,885),(1130,885),art.BLUE,8)
    art.text(d,'Προς μεγαλύτερα μήκη κύματος',640,955,44,bold=True)
    art.text(d,'Το υπέρυθρο δεν είναι ορατό στο ανθρώπινο μάτι.',640,1105,36)
    art.text(d,'Τα χρώματα των πεδίων είναι συμβολικά.',640,1170,32)
    assets.append(diagram(base,2,'infrared-spectrum.png','Ορατό και υπέρυθρο · επεξηγηματικό σχήμα','Ορθή σειρά μήκους κύματος UV/ορατό/IR. Συμβολικό πλάτος ζωνών, όχι ποσοστά του φάσματος ή ψευδές ορατό χρώμα υπερύθρου.',im,sources))
    repeat=copy.deepcopy(assets[0]);repeat.update(scene=6,paragraph_index=6,asset_label='Χρυσή επιφάνεια · ανάκλαση υπερύθρου',context_label='Webb · λεπτομέρεια της ίδιας φωτογραφίας',layout='cover',crop_focus=[.5,.66],source_reuse_reason='Deliberate return to a closer view of the same verified mirror photograph after the coating explanation; not an independent photo or a measured ray trace.');assets.append(repeat)
    im,d=art.canvas('Τρία υλικά, διαφορετικοί ρόλοι','Επεξηγηματική τομή — πάχη και χρώματα όχι σε κλίμακα')
    art.arrow(d,(640,285),(640,390),art.BLUE,8);art.text(d,'Φως προς την επιφάνεια',640,230,38)
    layers=[(410,580,'Προστατευτικό γυαλί · SiO₂','#D6EAF3'),(580,725,'Χρυσός · περίπου 100 nm','#E2BC50'),(725,1000,'Βηρύλλιο · ελαφρύ υπόστρωμα','#AEBFCB')]
    for y0,y1,label,color in layers:
        d.rectangle((135,y0,1145,y1),fill=color,outline='white',width=4)
        art.text(d,label,640,(y0+y1)/2-25,43,bold=True)
    art.text(d,'Το προστατευτικό στρώμα βρίσκεται πάνω από τον χρυσό.',640,1100,33)
    art.text(d,'Η μορφή εδώ είναι επίπεδη για να φαίνεται η σειρά.',640,1170,32)
    assets.append(diagram(base,7,'coating-layers.png','Γυαλί, χρυσός, βηρύλλιο · σχηματική τομή','Η σειρά των υλικών ακολουθεί τη NASA: άμορφοSiO2 πάνω από λεπτή επικάλυψη χρυσού σε βηρύλλιο. Το αναφερόμενο τυπικό πάχος100nm αφορά μόνο τον χρυσό. Τα εικονογραφημένα πάχη είναι σχηματικά.',im,sources))
    im,d=art.canvas('Πώς ευθυγραμμίζονται τα τμήματα','Επεξηγηματική οργάνωση — όχι μηχανολογικό σχέδιο')
    for y,title,detail in [(345,'6 μηχανισμοί ανά τμήμα','Ρυθμίζουν τη θέση και τον προσανατολισμό.'),(680,'1 ακόμη κεντρικός μηχανισμός','Ρυθμίζει την καμπυλότητα του τμήματος.')]:
        d.rounded_rectangle((110,y,1170,y+220),radius=26,fill=art.LIGHT,outline='#AACCD9',width=4)
        art.text(d,title,640,y+48,44,bold=True);art.text(d,detail,640,y+133,35)
    art.text(d,'18 τμήματα → ένας ενιαίος κύριος καθρέφτης',640,1030,41,bold=True)
    art.text(d,'Οι διορθώσεις γίνονται με βάση οπτικές μετρήσεις.',640,1150,35)
    assets.append(diagram(base,8,'mirror-adjustment.png','Ευθυγράμμιση τμημάτων · επεξηγηματικό σχήμα','Έξι ενεργοποιητές ανά κύριο τμήμα ελέγχουν τη θέση/προσανατολισμό και επιπλέον κεντρικός τη μορφή/καμπυλότητα. Δεν αναπαριστά φυσική διάταξη εξαρτημάτων ή πλαστή φωτογραφία μηχανισμού.',im,sources))
    assets.sort(key=lambda a:a['scene'])
    save(job,base,assets,'Γιατί οι καθρέφτες του Webb είναι χρυσοί; Η απάντηση συνδέει το υπέρυθρο φως με την επιλογή υλικών.',WEBB,'Οι λήψεις δείχνουν πραγματική κατασκευή, επιθεώρηση και δοκιμές στη Γη. Η σκηνή της ανάκλασης επιστρέφει με κοντινή θέαση στην αρχική φωτογραφία. Το φάσμα, η στρωματική τομή και οι ρόλοι των μηχανισμών δηλώνονται καθαρά ως επεξηγηματικά σχήματα.')

if __name__=='__main__':
    apollo();webb()
