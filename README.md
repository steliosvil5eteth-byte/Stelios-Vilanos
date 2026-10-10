# Ενεργή οδηγία: διαφορετικά βίντεο ανά πλατφόρμα

Η νεότερη οδηγία της 10/10/2026, με ισχύ από `2026-10-10T16:37:45+03:00`, ορίζει **15 διαφορετικά βίντεο ανά πλατφόρμα/ημέρα, 60 διαφορετικές ιστορίες συνολικά**, στη μάρκα 7076410. Το πρόγραμμα είναι `PLATFORM_SPECIFIC_FIFTEEN_DAILY`. Κάθε ιστορία έχει έναν μόνο προορισμό. Το μοναδικό authoritative αρχείο είναι `config/platform_growth_strategy.json`.

**Κατάσταση: BLOCKED_REQUIRED_HISTORY_AND_ZERO_CREDIT_CAPACITY.** Η παραγωγή και ο προγραμματισμός είναι απενεργοποιημένα. Δεν έχουν δημιουργηθεί ή προγραμματιστεί νέα βίντεο για αυτό το πρόγραμμα. Απαιτούνται επιτυχής εξουσιοδοτημένος fresh έλεγχος ιστορικού, επαλήθευση πραγματικής δωρεάν δυναμικότητας με μηδενικά credits, ελεγμένη νέα διαδρομή εκτέλεσης, και τελικός έλεγχος των ίδιων media.

Τα `CURRENT_TEN_DAILY`, `YOUTUBE_GROWTH_TEN_DAILY` και η προηγούμενη έκδοση `PLATFORM_SPECIFIC_TEN_DAILY` είναι **SUPERSEDED**. Τα ιστορικά κείμενα παρακάτω δεν επιτρέπουν επαναφορά κοινών αναρτήσεων, παλιών sourcepacks ή παλιών παραγωγών. Η ενεργοποίηση του νέου config δεν ενεργοποιεί κάποιο παλιό workflow. Τα legacy Azure jobs έχουν τεθεί σε hold στο τρέχον head· παλιά commits/reruns δεν πρέπει να χρησιμοποιούνται.

Ο dry-run CI και το παλιό `tools/check_rolling_queue.py` δεν πιστοποιούν ετοιμότητα της νέας παραγωγής. Το νέο config περιγράφει πολιτική και στόχο, όχι ολοκληρωμένη υπηρεσία παραγωγής. Δες `production/platform_specific/README.md` για τα gates και τη διαδικασία ελέγχου.

---

## Ιστορικό οδηγιών — ισχύει μόνο όπου δεν συγκρούεται με τα παραπάνω

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
- Connected networks: Facebook, Instagram, TikTok, YouTube. Publishing providers are selected separately by each program.
- This is the **only operational brand**. Previous Metricool brands are historical/audit-only and must not be used for new scheduling, publishing or repair.

## Historical superseded programs

From 2026-10-08, **CURRENT_TEN_DAILY** continues unchanged for Facebook, Instagram and TikTok: ten common logical posts at 07:00, 09:00, 10:00, 11:00, 13:00, 15:00, 17:00, 18:30, 20:00 and 22:00 Europe/Athens, giving 30 provider destinations per normal day. Its authoritative configuration is `config/content_strategy.json`. The 11:00 Zodiac series remains one carousel containing six two-sign comparison units covering all 12 signs exactly once.

YouTube is excluded from the common publishing flow. Its separate **YOUTUBE_GROWTH_TEN_DAILY** strategy is `config/youtube_growth_strategy.json`, with a target of ten original videos per normal day. The selected format is ten original narrated vertical videos, at least 80 seconds each, targeting 80–110 seconds with a maximum of 150 seconds and no filler. The strategy remains disabled until the actual batch is ready and reviewed. Existing common carousel/slideshow adaptations and scripts cannot be relabelled as the new YouTube videos.

Once both programs are active, their normal-day targets are 20 distinct logical items and 40 provider destinations: ten shared posts delivered to three networks, plus ten separate YouTube videos. Each program has its own daily limit of ten. On 2026-10-08, five YouTube videos already published count toward the daily total, so at most five additional new YouTube videos may be created, subject to a fresh live count before each create.

Publishing is quality-first: preserve published history, inspect the exact final files, require PASSED_FINAL_REVIEW, check all history for duplicates, and verify every write by live readback. Cancel only unpublished legacy YouTube destinations; preserve the Facebook, Instagram and TikTok provider records, schedules, copy and media. Missing legacy YouTube adaptations must never trigger repair of the common program.

## HeyGen

Η σύνδεση είναι διαθέσιμη, αλλά δεν υπάρχει ακόμη private avatar ή API-ready template στο workspace. Για αυτό τα jobs που ζητούν νέα δημιουργία HeyGen μένουν pending μέχρι να επιλεγεί τρόπος generation/presenter. Jobs με ήδη έτοιμο public media URL μπορούν να πάνε κατευθείαν στο Metricool.

## Κατάσταση

Το repository είναι πλέον έτοιμο να λειτουργήσει ως κεντρική ουρά αυτοματοποίησης. Η queue ξεκινά κενή ώστε να μην δημοσιευτεί τίποτα κατά λάθος.


