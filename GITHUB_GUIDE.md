# GitHub for complete beginners — sharing FundRadar

No command line needed. We use the free **GitHub Desktop** app (buttons only).

---

## Part 1 — Set up (do once, ~5 minutes)

1. Go to https://github.com and click **Sign up**. Create a free account
   (username, email, password). Remember the username — your teammate needs it.
2. Go to https://desktop.github.com and click **Download for Windows**. Install it.
3. Open GitHub Desktop. Click **Sign in to GitHub.com** and log in with the
   account you just made. Click **Authorize**.
4. If it asks for your name/email for commits, accept the defaults and continue.

## Part 2 — Put your project on GitHub (do once)

First, a tiny cleanup: open `C:\internship\project` in File Explorer. If you see
a folder called `.git` (it may be hidden — turn on View → Hidden items), delete
it. It's a broken leftover. If you don't see one, skip this.

Now in GitHub Desktop:

5. Click **File → Add local repository**.
6. Click **Choose…** and select your folder `C:\internship\project`. Click **Add**.
7. It will say "this directory does not appear to be a Git repository" with a blue
   link **create a repository**. Click that link.
8. A form appears. Leave the name as is, click **Create repository**.
9. Now you'll see a list of all your files on the left under "Changes". At the
   bottom-left, type a short message in the "Summary" box, e.g. `First version`,
   then click the blue **Commit to main** button. (A "commit" = a saved snapshot.)
10. At the top, click **Publish repository**. In the dialog, UNTICK "Keep this
    code private" only if you want it public — for a class project, leaving it
    private is fine (your teammate and professor can still be invited). Click
    **Publish repository**.

Your project is now on GitHub. To see it online, click **Repository → View on
GitHub** — that opens the web page; the address in your browser (something like
`https://github.com/yourname/project`) is your repo link.

## Part 3 — Add your teammate

11. On that GitHub web page, click **Settings** (top right of the repo).
12. In the left menu click **Collaborators**. You may be asked for your password.
13. Click **Add people**, type your teammate's GitHub username (or email), select
    them, and click **Add**. They'll get an email invite to accept.

Once they accept, they can get the project (see Part 5).

## Part 4 — Saving your changes later (the everyday routine)

Whenever you change files in the project, GitHub Desktop notices automatically.
To save and upload those changes:

14. Open GitHub Desktop. You'll see your changed files under "Changes".
15. Type a short summary of what you changed at the bottom-left.
16. Click **Commit to main**.
17. Click **Push origin** at the top (this uploads it to GitHub).

That's the whole routine: **Commit → Push**. Do it whenever you want to save progress.

Before you start working each time, click **Fetch origin** (top) then **Pull** if
it offers — that pulls in any changes your teammate pushed, so you stay in sync.

## Part 5 — How your teammate gets the project

After accepting your invite, your teammate:

18. Installs GitHub Desktop and signs in (Part 1, steps 2–4).
19. Clicks **File → Clone repository**, picks the `fundradar`/`project` repo from
    the list, chooses a folder on their computer, and clicks **Clone**.

They now have the full project. They use the same **Commit → Push** routine, and
**Fetch/Pull** to get your updates.

---

## Notes
- Your `.env` file and the database file are deliberately not uploaded (they're
  ignored) — each person keeps their own and runs the seed commands once.
- If two of you edit the *same lines* of the *same file*, GitHub Desktop will ask
  you to resolve a "conflict" — to avoid this, agree on who works on what, and
  Pull before you start.
- The repo link (the github.com/... address) is also what you can give your
  professor if she wants to read the code; for the live app she gets the Render
  link instead (see SHARING.md).
