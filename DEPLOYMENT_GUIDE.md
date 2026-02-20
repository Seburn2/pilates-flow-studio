# 🚀 Deployment Guide — Pilates Flow Studio

A complete beginner-friendly guide to getting this app live on Streamlit Community Cloud.

---

## Step 1: Set Up Your GitHub Repository

### Folder Structure

Your GitHub repo should look exactly like this:

```
pilates-flow-studio/
├── app.py                  ← Main Streamlit app
├── pilates_logic.py        ← Workout generator engine
├── requirements.txt        ← Python dependencies
├── README.md               ← (Optional) Description of the project
├── .gitignore              ← Files Git should ignore
└── assets/                 ← (Optional) Exercise images
    ├── footwork_parallel.png
    ├── bridging.png
    └── ...
```

### How to Do It

1. Go to [github.com](https://github.com) and sign in (or create an account).
2. Click the **"+"** button (top right) → **"New repository"**.
3. Name it `pilates-flow-studio`, set it to **Private** (so only you can see it), click **Create**.
4. Upload the three code files (`app.py`, `pilates_logic.py`, `requirements.txt`).
5. (Optional) Create an `assets/` folder and upload any exercise images.

### Create a `.gitignore` File

Add this file to your repo so you don't accidentally upload secrets:

```
# .gitignore
__pycache__/
*.pyc
.env
secrets.toml
*.json
```

---

## Step 2: Create a Google Sheet

1. Go to [Google Sheets](https://sheets.google.com) and create a new spreadsheet.
2. **Rename it** to exactly: `Pilates Flow Studio`
3. The app will auto-create the tabs it needs (`workouts_log`, `exercise_library`), but you can also manually create them:
   - **Tab 1:** `workouts_log` with headers: `Date | User | Theme | Duration | Full_JSON_Data | Rating | Notes`
   - **Tab 2:** `exercise_library` with headers: `Slug | Name | Default_Springs | Cues`
4. **Copy the spreadsheet URL** — you'll need it later. It looks like:
   `https://docs.google.com/spreadsheets/d/SOME_LONG_ID/edit`

---

## Step 3: Get Google Cloud Credentials (Service Account JSON Key)

This lets the app read/write to your Google Sheet. It takes about 5 minutes.

### 3a. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Click the project dropdown (top-left) → **"New Project"**.
3. Name it `pilates-flow-studio` → click **Create**.
4. Make sure the new project is selected in the dropdown.

### 3b. Enable the Required APIs

1. In the left sidebar, go to **"APIs & Services" → "Library"**.
2. Search for and **enable** each of these (click the API, then click "Enable"):
   - **Google Sheets API**
   - **Google Drive API**

### 3c. Create a Service Account

1. Go to **"APIs & Services" → "Credentials"**.
2. Click **"+ Create Credentials" → "Service Account"**.
3. Name it `studio-sheets-bot` → click **Create and Continue**.
4. For "Role", select **Editor** → click **Continue** → click **Done**.

### 3d. Download the JSON Key

1. On the Credentials page, click on the service account you just created (`studio-sheets-bot@...`).
2. Go to the **"Keys"** tab.
3. Click **"Add Key" → "Create New Key" → JSON** → click **Create**.
4. A `.json` file will download. **Keep this file safe** — it's your password!

### 3e. Share the Google Sheet with the Service Account

1. Open the JSON file you downloaded. Find the `"client_email"` field. It looks like:
   `studio-sheets-bot@pilates-flow-studio.iam.gserviceaccount.com`
2. Go to your Google Sheet → click **Share** (top right).
3. Paste that email address → give it **Editor** access → click **Send**.

---

## Step 4: Deploy to Streamlit Community Cloud

### 4a. Connect Your Repo

1. Go to [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
2. Click **"New app"**.
3. Select your `pilates-flow-studio` repo.
4. Set **Main file path** to: `app.py`
5. **Don't click Deploy yet!** — first add your secrets.

### 4b. Add Your Secrets

1. Click **"Advanced settings"** (below the deploy button).
2. In the **"Secrets"** text area, paste the following (replacing values with your actual data):

```toml
# ──────────────────────────────────────────
# Streamlit Secrets — paste this EXACTLY
# (replace the values with your actual data)
# ──────────────────────────────────────────

# Your Google Sheet URL (the whole URL from step 2)
sheet_url = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit"

# (Optional) Anthropic API key for the AI Instructor chat
# Get one at https://console.anthropic.com/
anthropic_api_key = "sk-ant-xxxxx"

# Google Service Account credentials
# Copy-paste the ENTIRE contents of your downloaded JSON key file below,
# but reformat it into TOML like this:
[gcp_service_account]
type = "service_account"
project_id = "pilates-flow-studio"
private_key_id = "your_key_id_here"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_ACTUAL_KEY_HERE\n-----END PRIVATE KEY-----\n"
client_email = "studio-sheets-bot@pilates-flow-studio.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/studio-sheets-bot%40pilates-flow-studio.iam.gserviceaccount.com"
universe_domain = "googleapis.com"
```

**How to convert the JSON key to TOML:**

Your downloaded JSON file looks like this:
```json
{
  "type": "service_account",
  "project_id": "pilates-flow-studio",
  "private_key": "-----BEGIN PRIVATE KEY-----\nABC123...\n-----END PRIVATE KEY-----\n",
  ...
}
```

For the TOML secrets, just put each key-value pair under `[gcp_service_account]` with `=` signs and quotes around string values (as shown above). The `private_key` value must stay as one line with the `\n` characters intact.

### 4c. Deploy!

Click **"Deploy!"** and wait 2-3 minutes. Your app will be live at a URL like:
`https://pilates-flow-studio.streamlit.app`

Send this URL to Alyssa!

---

## Step 5: (Optional) Enable AI Instructor

The "Ask Instructor" chat feature uses the Anthropic API (Claude).

1. Go to [console.anthropic.com](https://console.anthropic.com/).
2. Create an account and add billing (even $5 is plenty — each question costs fractions of a cent).
3. Go to **API Keys** → create a new key.
4. Add it to your Streamlit secrets as `anthropic_api_key = "sk-ant-..."`.

If you skip this step, the app still works perfectly — the chat feature will just show a message asking you to add the key.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Could not connect to Google Sheets" | Double-check your secrets TOML formatting. The `private_key` must have `\n` and be in quotes. |
| "Could not open spreadsheet" | Make sure you shared the sheet with the service account email (Step 3e). |
| App crashes on deploy | Check the Streamlit Cloud logs (click "Manage app" → logs). Usually a missing package in `requirements.txt`. |
| "No module named pilates_logic" | Make sure `pilates_logic.py` is in the root of your repo (same folder as `app.py`). |
| Timer doesn't auto-update | Streamlit's timer is click-to-refresh. It updates each time you interact with the page. For a live ticking timer, you'd need a JS component. |

---

## Updating the App

Any time you push changes to your GitHub repo, Streamlit Cloud will automatically redeploy within ~1 minute. Just edit your files on GitHub and save — done!
