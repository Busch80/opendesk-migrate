# End-User Guide

This guide is for the M365 end-user who is migrating to openDesk via
the `opendesk-migrate` tool operated by KPX.

## What is happening

KPX is migrating your company email, calendar, contacts, and OneDrive
files from Microsoft 365 to an open-source alternative called **openDesk**.
This is a one-time move, performed per tenant (company).

## What you need to do

### Step 1 — Sign into Microsoft for one-time consent

1. KPX sends you an email with a link to the migration web app.
2. Open the link — you will see a screen asking for permission.
3. Sign in with your normal Microsoft 365 email address and password.
4. **One** popup asks you to grant read access to your mail, calendar,
   contacts, and OneDrive — review and click **Accept**.

That's it. After this:
- Your data continues to live in Microsoft 365 until the cutover date.
- KPX copies it to openDesk in the background.
- On the cutover day, your inbox moves over (you'll see a notice).

### Step 2 — Keep using Microsoft until cutover

Until the cutover date, use Outlook / your normal email client as today.

### Step 3 — On cutover day

- Your MX record points to openDesk instead of Microsoft.
- Log in to the openDesk portal at `https://portal.<your-company-domain>`.
- Your old mail, calendar, contacts and OneDrive files are already there.

## FAQ

**Why do you need this access?**
The migration reads your data to copy it to openDesk. It does not modify or
delete anything in M365 until the cutover day.

**Can I revoke this access?**
Yes. In Microsoft 365 → Account → Privacy → App permissions, you can
remove the migration app at any time. If you do, KPX will re-ask before the
cutover.

**Where does my data go?**
To openDesk servers located in Switzerland (KPX infrastructure). Data does
not leave Switzerland.

**Is this GDPR-compliant?**
Yes — see `docs/COMPLIANCE.md` for full details.

**Can I keep some email locally?**
KPX can configure per-folder exclusions. Ask your IT administrator.

## Contact

KPX service desk: [email protected]
Security questions: [email protected]
