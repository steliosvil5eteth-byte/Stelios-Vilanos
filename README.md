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
- GitHub Actions: αυτοματισμοί

## Ασφάλεια

Δεν αποθηκεύουμε API keys, passwords ή tokens μέσα στον κώδικα. Χρησιμοποιούμε GitHub Secrets / environment variables.

## Τρέχουσα κατάσταση

Αρχικό στήσιμο του automation framework. Η πρώτη έκδοση λειτουργεί σε `dry-run`, ώστε να μην ανεβαίνει τίποτα κατά λάθος πριν συνδεθούν σωστά οι υπηρεσίες.

## Δομή

- `src/pipeline.py`: βασικός automation runner
- `config/content_plan.example.json`: παράδειγμα πλάνου περιεχομένου
- `.github/workflows/automation-dry-run.yml`: ασφαλές χειροκίνητο test στο GitHub Actions
- `.env.example`: ονόματα μεταβλητών που θα χρειαστούν αργότερα
