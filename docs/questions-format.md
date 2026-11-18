# Savollar JSON Formati va Yuklash Qo'llanmasi

Namuna fayl: `scripts/sample_questions.json`

## Maydonlar

- `day_number` (int, majburiy): kun raqami (1..30)
- `title` (str, majburiy): savol sarlavhasi
- `question_type` (str, majburiy): `"practical"` yoki `"quiz"`
- `body_text` (str, majburiy): savol matni (HTML)
- `difficulty` (str, majburiy): `"easy" | "medium" | "hard"`
- `starter_code` (str, ixtiyoriy): boshlang'ich kod (`practical` uchun)
- `sample_tests` (list, `practical` uchun kamida 1 ta): `[{"input": "...", "expected": "..."}]` — ishtirokchiga ko'rinadi
- `hidden_tests` (list, `practical` uchun kamida 1 ta): `[{"input": "...", "expected": "..."}]` — hech qachon ishtirokchiga ko'rinmaydi
- `options` (list[str], `quiz` uchun kamida 2 ta): javob variantlari
- `correct_option` (int, `quiz` uchun majburiy): to'g'ri variant indeksi (`0` dan boshlanadi)
- `reference_solution` (str, `practical` uchun tavsiya etiladi): faqat admin ko'radi va `validate_questions.py` da ishlatiladi

## Yuklash va Tekshirish

```bash
# Dry-run tekshiruv (bazaga yozmasdan)
python scripts/import_questions.py scripts/sample_questions.json --challenge-id <UUID> --dry-run

# Bazaga yuklash
python scripts/import_questions.py scripts/sample_questions.json --challenge-id <UUID>

# Reference yechimlarni runner orqali tekshirish
python scripts/validate_questions.py --file scripts/sample_questions.json --runner-url http://localhost:8080
```
