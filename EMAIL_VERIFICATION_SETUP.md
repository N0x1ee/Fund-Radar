# FundRadar — Email Verification (Resend)

New sign-ups must confirm their email before they can log in. This is **off by
default** and turns on automatically once you add a Resend API key — so nothing
breaks until you're ready.

- **No key set** → app behaves as before: sign up logs you straight in, no email.
- **Key set** → sign-up sends a "Verify your email" link; users can't log in
  until they click it. The demo account (`demo@fundradar.com`) is always
  verified, so demos keep working either way.

---

## 1. Get a free Resend API key

1. Go to https://resend.com and sign up (free — 3,000 emails/month).
2. Open **API Keys** → **Create API Key** → copy it (starts with `re_...`).

## 2. Add it to your live site (Render)

1. Open your service at https://dashboard.render.com → **fundradar**.
2. Left menu → **Environment** → **Add Environment Variable**:
   - Key: `RESEND_API_KEY`  Value: your `re_...` key
3. Add one more (so verification links point to your live site):
   - Key: `APP_BASE_URL`  Value: `https://fundradar-ee69.onrender.com`
4. Click **Save changes**. Render redeploys automatically. Verification is now on.

## 3. IMPORTANT — the free sender only emails *you* at first

By default the app sends from Resend's shared test address
`onboarding@resend.dev`. In test mode, Resend **only delivers to the email you
signed up to Resend with**. That's perfect for testing verification yourself,
but other people's sign-ups won't receive the email yet.

To let *anyone* verify (e.g. a professor signing up):

1. In Resend → **Domains** → **Add Domain**, and add a domain you own.
2. Follow Resend's DNS steps to verify it.
3. On Render, add: `EMAIL_FROM` = `FundRadar <noreply@yourdomain.com>`.

No domain? Two fine options for a demo:
- Just use the **demo login** (`demo@fundradar.com` / `demo1234`) — always works.
- Or leave `RESEND_API_KEY` unset so sign-up logs in directly (verification off).

## 4. Testing it

1. With the key set, sign up on the site using **your Resend account email**.
2. You'll see "check your email"; open the email and click **Verify my email**.
3. You'll get a "Email verified" page — now log in normally.
4. If a link expires or is lost, the login screen shows a **Resend email** link.

## Turning it off

Delete the `RESEND_API_KEY` variable on Render and save. Sign-up goes back to
logging users in immediately.

## Running locally (optional)

Add to your `.env`:

```
RESEND_API_KEY=re_your_key
APP_BASE_URL=http://localhost:8000
# EMAIL_FROM=FundRadar <noreply@yourdomain.com>   # only if you verified a domain
```
