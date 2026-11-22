# Security Policy

## Supported versions

Only the latest commit on `main` is supported. Older commits and forks are best-effort.

## Reporting a vulnerability

Please **do not** open a public GitHub Issue for security problems (especially anything
involving bot tokens, `.env` contents, database dumps, or personal data).

Use **GitHub Security Advisories** (private vulnerability reporting) for this
repository:

1. Open the repo on GitHub → **Security** → **Advisories** → **New draft security advisory**  
   (or **Report a vulnerability**, if private reporting is enabled for reporters).
2. Describe the issue, impact, and steps to reproduce. Omit secrets; rotate any
   exposed credentials yourself before or while reporting.
3. We will confirm receipt, assess severity, and coordinate a fix and disclosure
   timeline through the advisory thread.

If you cannot use advisories, contact the maintainer via the email on their
[GitHub profile](https://github.com/DigitalJacob) — still without pasting live
secrets into the message body when avoidable.

## Operational notes for operators

- Never commit `.env`, age identity keys, or `*.dump` / `*.dump.age` files.
- Prefer the encrypted backup flow in the README; restore drills should use a
  non-primary database.
- Treat Telegram bot tokens and database credentials as production secrets;
  rotate them if they may have leaked.
