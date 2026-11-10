# JobMatch AI — personal Streamlit MVP

Find relevant jobs on selected public Greenhouse and Lever company boards, persist them in Supabase, evaluate fit against an uploaded resume using OpenAI, create a draft ATS-friendly DOCX, and manually approve before opening an application page. No automatic application submissions.

## Requirements

- Python 3.11+
- GitHub repository (private recommended)
- Supabase project
- Streamlit Community Cloud account
- OpenAI API key (optional for job discovery, required for AI matching/tailoring)

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

1. Create a Supabase project, open **SQL Editor**, and execute `schema.sql`.
2. Copy the Supabase Project URL and **service_role** key from project API settings. Treat the key as a secret; never commit it or put it in browser-side code. The app uses it only in server-side Python. The schema enables RLS and defines no public policies.
3. Edit `.streamlit/secrets.toml` to set `APP_PASSWORD`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, and `OPENAI_MODEL`. Never commit this file.
4. Run the app, sign in, click **Scan jobs now**, and upload a DOCX, text-based PDF, or TXT resume. The upload stays in Streamlit session memory; do not treat this as long-term secure resume storage.
5. Select **Evaluate fit**, **Generate tailored resume**, review the output, and download the DOCX. Change status to **approved** and then open the application URL. Submit manually on the employer's site. Mark **applied** after submitting.

## Deploy

1. Push this directory to a **private GitHub repository** (the secrets file is gitignored).
2. In Streamlit Community Cloud, create an app from that repository, branch `main`, main file `app.py`.
3. Paste the contents of your local `.streamlit/secrets.toml` into the deployment's **Advanced settings → Secrets** field. Keep `APP_PASSWORD` strong; this is a simple single-user gate, not enterprise-grade authentication.
4. Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` as **GitHub Actions repository secrets**.
5. Open **Actions → Daily job scan → Run workflow** to verify the scheduled job. It then runs daily at 16:17 UTC (not a fixed Seattle wall-clock time). Scheduled workflows can be delayed or disabled by GitHub; verify runs periodically.

## Search configuration

Edit `config.json` to add or remove company board slugs. The included company slugs are **illustrative starting targets**, not verified active board identifiers; some may return 404 or zero jobs. Confirm each slug against the company's actual Greenhouse or Lever hosted board. Only configured companies are scanned. The MVP is **not a comprehensive search of all available jobs**.

The default title filter looks for operations, transformation, or strategy roles with seniority terms; location filtering covers named Seattle metro locations and remote roles. Unknown salary postings are retained (clearly marked) so promising roles aren't excluded. Salary amounts are interpreted as annual USD when provided by feeds; the app does not currently normalize hourly/other currencies, and some board data can be inconsistent. Review salary and location manually before applying.

## Privacy and limitations

- `APP_PASSWORD` guards access to the Streamlit app, but the app has no individual user accounts or audit logs.
- The Supabase service-role key bypasses RLS; never expose it in a client-side application. For broader deployment, replace this with authenticated users and narrowly scoped RLS policies.
- Resume text is sent to OpenAI when you request matching or tailoring. Avoid including information you do not want processed by the AI provider.
- The generated resume is a **draft**. Its original contact details are copied into a labeled verification section, and the user must check all dates, history, and accomplishments. The AI may omit information or make mistakes.
- No scraping of LinkedIn/Indeed, CAPTCHA bypassing, or automated job applications.
- Daily scan only discovers jobs; it does not run AI ranking or generate resumes without a resume upload. AI actions occur on demand in the app.
- Some employers use other ATS providers. Add adapters for those sources later.
- Salary and remote eligibility can be missing or ambiguous; this MVP favors recall and requires human verification.

## Troubleshooting

- **No jobs:** Verify board slugs, increase company coverage, and inspect GitHub Actions logs for feed errors.
- **Supabase 401/403:** Verify service-role key, URL, and that `schema.sql` ran.
- **OpenAI error:** Verify API key, billing access, and model name; you can still scan jobs without it.
- **PDF blank:** Use a text-based PDF, DOCX, or TXT; scanned-image PDFs need OCR.
- **Job not appearing:** Title/location/salary filters may have excluded it. Adjust `core.py` matching functions.
