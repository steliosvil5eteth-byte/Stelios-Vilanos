# Social Media Automation

Repository για αυτοματοποίηση δημιουργίας, οργάνωσης και δημοσίευσης short-form περιεχομένου.

## Στόχος

Ροή εργασίας:

1. Ιδέα / σενάριο
2. Δημιουργία εικόνας ή βίντεο
3. Αποθήκευση τελικού αρχείου
4. Δημιουργία τίτλου, περιγραφής και hashtags
5. Προγραμματισμός δημοσίευσης
6. Έλεγχος αν δημοσιεύτηκε επιτυχώς
7. Καταγραφή αποτελεσμάτων

## Πλατφόρμες

- TikTok
- Instagram Reels
- Facebook Reels
- YouTube Shorts

## Βασικά εργαλεία

- ChatGPT: ιδέες, σενάρια και orchestration
- HeyGen: AI video
- Canva: εικόνες / γραφικά
- Metricool: scheduling και publishing
- Notion: content planning
- Dropbox / Google Drive: media storage
- GitHub: queue, configuration και ιστορικό

## Τρέχουσα αρχιτεκτονική

Η πρώτη λειτουργική έκδοση χρησιμοποιεί τα ήδη συνδεδεμένα plugins ChatGPT για GitHub, Metricool και HeyGen. Έτσι δεν χρειάζεται να αποθηκεύονται API keys μέσα στο repository.

- `queue/pending.json`: εργασίες που περιμένουν εκτέλεση
- `queue/completed.json`: εργασίες που έχουν ολοκληρωθεί
- `config/integrations.json`: μη ευαίσθητες ρυθμίσεις υπηρεσιών
- `docs/AUTOMATION_RUNNER.md`: κανόνες του runner
- `src/queue_validate.py`: έλεγχος εγκυρότητας queue
- `.github/workflows/automation-dry-run.yml`: αυτόματος έλεγχος χωρίς δημοσίευση

## Ασφάλεια

Δεν αποθηκεύουμε API keys, passwords, cookies ή tokens μέσα στον κώδικα. Η δημοσίευση δεν γίνεται από το GitHub Actions validation workflow. Η πραγματική ενέργεια περνά από τις συνδεδεμένες υπηρεσίες ή, αργότερα, από ασφαλή GitHub Secrets αν επιλεγεί direct API mode.

## Metricool

- Active brand: **Ιστορίες που μας αγγίζουν**
- Brand ID: `7076410`
- Timezone: `Europe/Athens`
- Networks: Facebook, Instagram, TikTok, YouTube
- This is the **only operational brand**. Previous Metricool brands are historical/audit-only and must not be used for new scheduling, publishing or repair.

## Active program

The sole active schedule is **CURRENT_TEN_DAILY** with 10 logical posts per day at 07:00, 09:00, 11:00, 13:00, 15:00, 17:00, 18:30, 20:00, 21:30 and 23:00 Europe/Athens.

Publishing is quality-first: a failed slot is repaired and published later the same day after full QA and a fresh duplicate check. End-of-day target: exactly 10 correct logical posts.

## HeyGen

Η σύνδεση είναι διαθέσιμη, αλλά δεν υπάρχει ακόμη private avatar ή API-ready template στο workspace. Για αυτό τα jobs που ζητούν νέα δημιουργία HeyGen μένουν pending μέχρι να επιλεγεί τρόπος generation/presenter. Jobs με ήδη έτοιμο public media URL μπορούν να πάνε κατευθείαν στο Metricool.

## Κατάσταση

Το repository είναι πλέον έτοιμο να λειτουργήσει ως κεντρική ουρά αυτοματοποίησης. Η queue ξεκινά κενή ώστε να μην δημοσιευτεί τίποτα κατά λάθος.
