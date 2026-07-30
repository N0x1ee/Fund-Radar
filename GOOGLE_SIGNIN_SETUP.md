# Turning on "Continue with Google" — step by step

FundRadar can let people sign in with their Google account instead of creating
a password. The code is already built and deployed. It stays **switched off**
until you give it one setting: a **Client ID** from Google.

Without that setting the button simply doesn't appear, and normal email/password
login keeps working exactly as before. Nothing can break by not doing this.

Total time: about 5 minutes. It's free and needs no credit card.

---

## Part 1 — Get your Client ID from Google (5 min)

### 1. Open the Google Cloud Console

Go to <https://console.cloud.google.com/> and sign in with any Google account.

### 2. Make a project

At the very top of the page there's a project dropdown (it may say
"Select a project"). Click it → **New Project**.

- **Name:** `FundRadar`
- Click **Create**, wait a few seconds, then make sure the dropdown at the top
  now says **FundRadar**. (If it doesn't, click the dropdown and pick it.)

### 3. Fill in the consent screen

This is the "FundRadar wants to access your Google Account" box users will see.

In the left menu go to **APIs & Services → OAuth consent screen**.

- If it asks for **User Type**, choose **External** → **Create**.
- **App name:** `FundRadar`
- **User support email:** your email
- **Developer contact email:** your email
- Click **Save and Continue** through the "Scopes" and "Test users" steps —
  you don't need to add anything on either.
- On the summary page click **Back to Dashboard**.

> **Important for your demo:** while the app is in **Testing** mode, only Google
> accounts you list as test users can sign in. Two options:
>
> - **Easiest:** on the OAuth consent screen click **Publish app** →
>   **Confirm**. Anyone with a Google account can then sign in. (Google only
>   requires a formal review for sensitive data; basic name/email sign-in does
>   not need one.)
> - **Or:** stay in Testing and add your own and your professor's Google
>   addresses under **Test users → Add users**.
>
> If you skip this, sign-in will fail with "access blocked" for anyone who
> isn't a test user.

### 4. Create the Client ID

Left menu → **APIs & Services → Credentials** →
**+ Create Credentials** → **OAuth client ID**.

- **Application type:** `Web application`
- **Name:** `FundRadar Web`

Now the important part — two lists of addresses. Add **exactly** these:

**Authorised JavaScript origins** (click *+ Add URI* for each):

```
https://fundradar-ee69.onrender.com
http://localhost:8000
http://127.0.0.1:8000
```

**Authorised redirect URIs** — add the same three:

```
https://fundradar-ee69.onrender.com
http://localhost:8000
http://127.0.0.1:8000
```

Rules that trip people up:

- **No trailing slash.** `https://fundradar-ee69.onrender.com/` (with `/`) is
  rejected.
- **`https` for Render, `http` for localhost.** They are not interchangeable.
- If your Render URL is different from the one above, use yours.

Click **Create**.

### 5. Copy the Client ID

A box pops up with **Your Client ID** — a long string ending in
`.apps.googleusercontent.com`. Copy it.

You do **not** need the "Client secret". FundRadar doesn't use one.

---

## Part 2 — Give the Client ID to FundRadar

### On the live site (Render)

1. Go to <https://dashboard.render.com> → your **fundradar** service.
2. Left menu → **Environment**.
3. Click **Add Environment Variable**:
   - **Key:** `GOOGLE_CLIENT_ID`
   - **Value:** paste the Client ID
4. Click **Save Changes**. Render restarts the app automatically (~1 minute).

Open your site, click **Sign in** — the Google button is now there.

### On your own computer (optional)

Open the `.env` file in the project folder and add the line:

```
GOOGLE_CLIENT_ID=paste-your-client-id-here
```

Save, then restart the app:

```
uvicorn app.api.main:app --reload
```

---

## Checking it worked

Visit `https://fundradar-ee69.onrender.com/auth/config` in your browser.

- `{"google_enabled":true,"google_client_id":"...")` → set up correctly.
- `{"google_enabled":false,"google_client_id":""}` → the variable didn't save;
  redo Part 2.

---

## If something goes wrong

| What you see | What it means | Fix |
|---|---|---|
| No Google button at all | No Client ID reached the app | Check `/auth/config` (above); re-add the variable in Render |
| "Access blocked: this app is not verified" or "app is being tested" | The signing-in account isn't a test user | Publish the app, or add that address under **Test users** (step 3) |
| `origin_mismatch` / `redirect_uri_mismatch` | The address you're visiting isn't in Google's list | Add the exact URL to **both** lists in step 4 — no trailing slash, right `http`/`https` |
| Button appears, then "Google sign-in could not be verified" | The token failed server-side checks | Make sure the `GOOGLE_CLIENT_ID` in Render is the *same* Client ID you configured in step 4 |
| Changes don't take effect | Google can take a few minutes | Wait 5 minutes, then hard-refresh (Ctrl+Shift+R) |

---

## What actually happens when someone clicks the button

1. The browser shows Google's account chooser. **FundRadar never sees a Google
   password** — the user types it on Google's own page, if at all.
2. Google hands the browser a short, digitally signed certificate called an
   **ID token**, which states the user's email and name.
3. The browser sends that token to FundRadar's `/auth/google` endpoint.
4. The server asks Google to confirm the signature, then checks three things
   itself: the token was issued **for FundRadar** (not another app), it came
   from Google, and the **email address is verified**.
5. Only then does FundRadar create or find that user and issue its normal
   login cookie — the same one password login uses.

Step 4 matters. Checking the signature alone is not enough: a token that is
genuinely signed by Google but issued for *somebody else's* app would otherwise
be accepted. That check lives in `app/auth/google.py`.

**Signing in with Google on an email you already registered with a password
takes you into that same account**, with your saved bookmarks — you don't get a
second, empty one. That works because Google guarantees the address is verified.
