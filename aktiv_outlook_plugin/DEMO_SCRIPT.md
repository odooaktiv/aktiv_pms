# Aktiv for Outlook — client demo script

A ~8 minute recorded walkthrough. Every button name and message below is the
real one from `taskpane.js`, so you can follow it word for word.

---

## Part 1 — Prepare before you press record

Most demo failures happen here, not on camera.

### 1.0 Fix these first — they are in your current test setup

Your working screenshot (lead #59 created — the add-in itself is fine) shows
four things that must change before this is recorded for a client:

| In your setup now | Problem on camera | Do this instead |
|---|---|---|
| Panel header reads `https://0147-103-254-244-46.ngrok-free.app — admin` | A random ngrok address is on screen for the whole video and looks unfinished. The free URL also changes on every ngrok restart, so a re-take needs re-connecting | Demo against a stable HTTPS host — `https://odoo.aktivsoftware.com` or the client's own — so the header reads like a real deployment |
| Connected as **admin** | Says "we tested this as superuser". Also the header shows `admin` in every frame | Create a demo user, e.g. *Sarah Miller, Sales*, and connect as them. It shows the per-user model, which is the security story in Scene 6 |
| You are in **Sent Items**, on a **Teams meeting invite** | The panel reads `From: Anita Tiwari \| Aktiv Software` — your own address. The lead's contact becomes *you*, not a customer. A meeting-invite body is mostly a join link and renders as clutter in the chatter note | Demo from the **Inbox**, on a real-looking customer enquiry (Email A below) |
| Real mailbox — the folder and message list show Kentmaster, staxpayments, HT11126, colleague names | You would be sending one client a video containing another client's data | Use a clean demo mailbox. If you cannot, collapse the folder pane, and never show the message list — open the mail full-screen or in its own window |

Also: you are at **lead #59**, so the demo database has a pile of test leads. In
**Add to existing Lead…** the picker will list all of them for the sender and
look messy. Delete the test records for the address you plan to demo with, and
leave only the 1–2 you seeded in step 1.2.

### 1.1 The environment

| Item | What to use | Why |
|---|---|---|
| Odoo database | A **demo database**, never live or shared staging | Connecting mints a real API key against a real user |
| Odoo URL | **HTTPS**, publicly valid cert (e.g. `https://erp.aktivsoftware.com`) | The panel refuses `http://`, Outlook blocks mixed content |
| Outlook | **Outlook on the web**, Microsoft 365 **work** account | You are on Linux — there is no desktop Outlook. Personal outlook.com accounts often cannot sideload |
| Odoo login | An **internal** user | Portal users are refused with *"Only internal users can connect this add-in."* |

If you demo from a local Odoo over ngrok, visit the ngrok URL once in the same
browser first and click **Visit Site** — otherwise the interstitial page appears
mid-demo. Better: demo against the stage domain so no ngrok banner is ever on
screen.

### 1.2 Seed the data — this is the important one

**Add to existing Lead…** searches Odoo for records matching the sender's email
address. On an empty database the panel will say *"No leads found for
…"*, which kills the best part of the demo.

Before recording, in your demo Odoo:

1. Create a contact, e.g. **Sarah Miller — `sarah.miller@northwind-eng.com`**.
2. Create **1–2 CRM leads** for that contact, and give them different **stages**
   (the picker shows `Name — Stage`, and the stage is what makes two rounds of
   the same conversation distinguishable).
3. Create **1 helpdesk ticket** for the same contact.

### 1.3 Seed the mailbox

Put three emails in the demo inbox, all **from that same address**:

- **Email A** — a new enquiry, with a **PDF attached** (e.g. `requirements.pdf`).
  Plain text or simple HTML body.
- **Email B** — a follow-up in the same thread, no attachment.
- **Email C** — something that reads like a support problem, for the ticket part.

Do **not** use an email with inline images (pasted screenshots). Inline images
are stripped from chatter notes — a known gap — and you do not want that on
camera.

### 1.4 Screen setup

- Chrome, **zoom 110–125%**. The Outlook taskpane is narrow; at 100% the panel
  text is hard to read in a video.
- Close other tabs. Hide the bookmarks bar. Turn off desktop notifications.
- Two windows ready: **Outlook** and **Odoo**, so you can switch fast and show
  the record landing.
- In the add-in, click **Disconnect** first — you want to demo the connect flow
  live, and it proves it takes 20 seconds.
- Do a full silent rehearsal once. Then record.

---

## Part 2 — The script

Narration lines are what you say. **Bold** is what you click.

### Scene 0 — Opening (~45s)

The opening has three jobs, in this order: say who you are and how long this
will take, name **Dan's** problem before you name your product, and tell him
exactly what he is about to see. Keep the sentences short.

*On screen: Outlook inbox, nothing clicked yet. Do not click anything while you
speak — a still screen keeps attention on your voice.*

> "Hi Dan. Anita here, from Aktiv Software. This is a short walkthrough of the
> Outlook add-in we have built for you — about eight minutes, so you can watch
> it in one go.
>
> Here is the problem we set out to solve. Your team works in their inbox.
> Enquiries, support requests, quotes — they all arrive as email. Today someone
> reads the mail, opens Odoo, and types the same information in a second time.
> That takes a few minutes each time, and when the day is busy, it just does not
> get done. The record never gets created.
>
> So we put Odoo inside Outlook. I will show you three things: creating a lead
> or a helpdesk ticket straight from an email, filing follow-up emails onto the
> record that already exists so you do not collect duplicates, and what your IT
> team will want to know about access and security.
>
> Everything you are about to see is the real add-in, running against a real
> Odoo. Nothing here is a mock-up."

**Why this works:** he hears his own daily problem in the first fifteen seconds,
he knows the video has three parts and a fixed length, and "not a mock-up"
removes the doubt that everyone has when watching a vendor video.

**Then transition into the technical part with one line — do not narrate a
menu:**

> "Let me start where your team starts. In the inbox."

### Scene 1 — Connect (~60s)

Open **Email A** → in the ribbon click **Aktiv for Outlook**.

> "The panel opens on the right, inside Outlook. The first time, each user
> connects it to your Odoo once."

*Panel shows: Username, Password, URL, Database Name.*

Fill in the four fields, then **Connect**.

> "Their Odoo username, their password or an API key, the Odoo address, and the
> database name. That is it — no separate portal, no admin setup per user."

*Panel now shows the header line: the server address and the user, with a
**Disconnect** button.*

> "The header always shows which Odoo this mailbox is talking to and as whom.
> And notice what was exchanged — the password is not stored anywhere. Odoo
> issues a scoped API key just for this add-in, and that is the only thing kept.
> Your admin can revoke it at any time from the user's record, without touching
> the person's password."

### Scene 2 — Create a CRM lead from a received email (~90s)

*Still on Email A. Panel shows `From: Sarah Miller <sarah.miller@northwind-eng.com>`.*

> "The panel has already read who this mail is from."

Click **Create CRM Lead**.

*Panel shows: `Lead created (#N).`*

> "Done. Let's look at what actually arrived in Odoo."

Switch to Odoo → open the new lead.

Point at, in this order:

1. **The lead title** — "the email subject became the lead name."
2. **The customer** — "the sender was matched to the existing contact. If the
   sender is new to you, the contact is created automatically, so nothing is
   lost."
3. **The chatter note** — "the full email body is here, formatted, not as raw
   HTML. Note it is logged as an *internal note* — filing an email onto a record
   does not email it back out to that record's followers. Nothing leaves your
   system by accident."
4. **The attachment** — "and the PDF came across with it, attached to the lead
   with its correct file type."

### Scene 3 — Create a helpdesk ticket (~45s)

Back to Outlook → open **Email C** → panel is already connected.

Click **Create Helpdesk Ticket**.

*Panel shows: `Helpdesk ticket created (#N).`*

> "The same email can go to Helpdesk instead. Same one click, same contact
> matching, same attachments — it just lands as a ticket rather than a lead.
> Your sales mail becomes leads, your support mail becomes tickets, and the
> person reading the mail decides which, at the moment they read it."

Switch to Odoo briefly to show the ticket. Keep this short — the client has
already seen the pattern.

### Scene 4 — Add to an existing record (~90s) ← the strongest part

Back to Outlook → open **Email B**, the follow-up from the same sender.

> "Now, the real problem with tools like this: the second email in a
> conversation. If every click creates a new record, after a week you have five
> leads for one customer."

Click **Add to existing Lead…**

*Panel shows `Searching…`, then `Matching leads for sarah.miller@northwind-eng.com — pick one:`
and a list of `Name — Stage` rows.*

> "So instead, the add-in looks up what already exists for this sender, and
> shows you the stage of each so you can tell them apart."

Click the correct lead.

*Panel shows: `Added to <lead name>.`*

Switch to Odoo → open that same lead.

> "The follow-up is filed onto the existing lead as another note, in order, with
> its attachments. One customer, one lead, the whole conversation in one place —
> and no duplicate."

### Scene 5 — Works while writing, not only while reading (~60s)

Back to Outlook → **New email** → **Aktiv for Outlook** on the compose ribbon.

*Panel shows: `No recipient yet — the record will be created without a contact.`*

> "It also works on mail you are writing — outbound, not just inbound."

Type an address into **To**.

*The line changes by itself to `To: <name> <address>`.*

> "It picks up the recipient as you type."

Type a subject, attach a file, then click **Create CRM Lead**.

*Panel shows: `Lead created (#N).`*

> "So if your salesperson sends a proposal out cold, that goes into Odoo as a
> lead too, from the same panel, before the mail is even sent."

*(Optional, only if you want to show the guard rail: click **Create CRM Lead**
with the subject empty first — an inline error appears and nothing is created.)*

### Scene 5b — Send it and file it in one click (~60s) ← lead with this if Dan asked for it

This is the answer to Dan's question about filing and sending in one step. If he
asked for it, **do not bury it here** — move it up next to Scene 4 and say so.

*Still on the draft, with a recipient and a subject.*

> "And when you're replying to a customer, you don't have to file it first and
> then send it. You can do both in one click."

Click **Send & add to Lead…**

*Panel shows the picker, headed `Pick a lead for <addr> — the email is filed onto
it and sent:`*

> "Same list as before — it looks up what's already open for this customer."

Click the correct lead.

*Panel shows `Adding to Odoo…`, then `Added to <name>. Sending…`, and the compose
window closes.*

**Pause. Let it close on camera** — the window closing is the proof.

Switch to Odoo → open that lead → then to Outlook's **Sent Items**.

> "One click. The email is on its way to the customer, and the conversation is
> already on the opportunity — note it says *Sent to*, so whoever picks this up
> next can see it went out, not came in. Nobody has to remember to do the second
> half, because there isn't a second half."

**Then show the new-customer case — it is the one Dan will actually ask about.**

Start a new mail to an address with nothing in Odoo behind it, and click
**Send & create Lead**.

*Panel shows: `Lead created (#N). Sending…` and the window closes.*

> "And when it's someone you've never dealt with, there's nothing to file
> against yet. So the same row creates the lead and sends the mail together.
> Your salesperson writes one email, and the customer exists in Odoo."

*(If you prefer to show it as a rescue rather than a separate button: click
**Send & add to Lead…** on that new address instead. The panel says no leads
were found and offers **Create a new lead and send** right there. Same result,
and it demos better because he watches the tool solve the problem he just saw.)*

**If Dan asks whether it works everywhere, answer honestly:** it needs Outlook
on the web, new Outlook for Windows, or Outlook 2412 and later. On Outlook for
Mac and on older builds the panel says so, and those users file the mail and
press Send as two steps — exactly what they do today, nothing is lost. Do not
say "everywhere". If his team is on Mac or on-premises Exchange, say you will
confirm the options in writing.

### Scene 6 — Security, briefly (~45s)

> "Three things your IT will ask."

1. **Disconnect** — click it. "A user can disconnect at any time."
2. In Odoo: **Settings → Users & Companies → Users → [user] → API Keys** — show
   the key named *Aktiv for Outlook*. "Access is a named key per user. Revoke it
   here and that mailbox is cut off immediately."
3. > "Only internal Odoo users can connect — portal and public accounts are
   > refused. And the email data goes from your Outlook to your Odoo directly.
   > Nothing routes through us."

### Scene 7 — Close (~60s)

The close also has three jobs: repeat the three promises you made at the start
(and *only* those), tell Dan what it costs **him** to get it, and ask for one
small, specific next step. End on the ask — not on "thank you for watching".

*On screen: go back to the Odoo lead you created, with the email note visible.
A finished result on screen while you summarise is stronger than a blank panel.*

> "So, to bring that back to the three things I promised, Dan.
>
> One — an email becomes a lead or a helpdesk ticket in one click, with the
> message, the contact and the attachments already attached. No re-typing.
>
> Two — the follow-ups go onto the record that already exists. One customer, one
> lead, the whole conversation in one place. No duplicates to clean up later.
>
> Three — access is a named key for each user, your admin can revoke it any
> time, and the email goes from your Outlook to your Odoo directly.
>
> What it takes on your side is small. Your Microsoft 365 admin uploads it once,
> and it appears for everyone you choose. Each person then connects it once with
> their own Odoo login — that is the twenty-second step you saw at the start.
> There is nothing for your team to install.
>
> Here is what I would suggest as a next step. Give me one mailbox and one Odoo
> test user, and your team can try it on real email this week — no commitment
> beyond that. If it saves them time, we roll it out to the rest.
>
> If anything is unclear, send me your questions and I will record the answers
> the same way. Thanks Dan."

**Why this works:** the recap uses his words, not feature names. "What it takes
on your side is small" answers the objection he is already forming. And the ask
is one mailbox and one user — small enough to say yes to without a meeting.

**Do not end with:** "let me know if you have any questions" alone. That is not
a next step, and it puts the work on him to invent one.

---

## Part 2.5 — Holding the middle together

The technical scenes are where a demo goes flat, because you start narrating
buttons. Two rules:

**Say the outcome, not the click.** Not *"now I click Create CRM Lead"* — he can
see that. Say *"one click, and that enquiry is now a lead in Odoo"*. Click while
you talk, do not describe clicking.

**Bridge every scene with one sentence** so it feels like one story instead of a
feature list:

| Into | Bridging line |
|---|---|
| Scene 2 (create lead) | "Let me start where your team starts. In the inbox." |
| Scene 3 (ticket) | "Same email, but say this one is a support problem, not a sale." |
| Scene 4 (add to existing) | "Now the part that usually goes wrong with tools like this — the second email." |
| Scene 5 (compose) | "And it is not only for mail you receive." |
| Scene 6 (security) | "Last thing — the three questions your IT team will ask." |

**After each result, pause for two seconds in silence.** Let him read `Lead
created (#N).` on screen. Silence reads as confidence, and it gives you clean
cut points if you edit later.

---

## Part 2.6 — If Dan asks

Answer these honestly and briefly. Guessing on camera, or over-promising, costs
more than saying "let me confirm that".

| Question | Answer |
|---|---|
| "Does it work in desktop Outlook, or only the browser?" | Both — it is a Microsoft 365 add-in, so it runs in Outlook on the web and in desktop Outlook. On older desktop clients, a record created from a *draft you are writing* is created without the attachments. Received mail is unaffected. |
| "What if the sender is not in our Odoo yet?" | The contact is created automatically from the email address and name. Nothing is lost, and nothing is duplicated if they already exist. |
| "Can we bulk-file a whole folder of old emails?" | No — it is one email at a time, from the mail you have open. Bulk import would be a separate piece of work. |
| "Can it send and file at the same time?" | Yes — **Send & add to Lead…** files the email onto an existing record and sends it in one click, and **Send & create Lead** does the same for a customer who isn't in Odoo yet. Needs Outlook on the web, new Outlook for Windows, or Outlook 2412+. On Mac and older builds the panel says so and it stays two steps. |
| "What if the customer isn't in our Odoo yet?" | **Send & create Lead** makes the lead from the email and sends it in the same click. If you go looking for an existing one first, the panel tells you there is none and offers to create it there and then. |
| "What if Odoo is down when I hit that?" | Nothing is sent. It files first on purpose, so a failure leaves your draft intact rather than mailing the customer with no record of it. |
| "Does filing an email notify the customer?" | No. It is posted as an internal note, so followers on that record are not emailed. Nothing goes out of your system by accident. |
| "Can someone see other people's Odoo data through it?" | No. Each user connects with their own Odoo login and gets their own key, so they see exactly what their Odoo permissions allow. |
| "What does it cost / how is it licensed?" | **Do not improvise.** Say: "Commercials I will send you separately in writing." There is no licence enforcement in this build, so anything you say on camera about per-user pricing will not match what the software does. |
| "What about the images inside the email?" | Normal file attachments come across. Images pasted inline in the message body are not carried over yet. |
| "How long to get it live for us?" | The install itself is quick — an upload by your M365 admin and the module on your Odoo. Give a date only after you have checked their Odoo version and that `mail_plugin` is available. |

---

## Part 3 — Do not show these

| Avoid | Why |
|---|---|
| Licensing / subscriptions | Not built in this version. If asked: *"subscription enforcement is a follow-up item"* — do not promise a date on camera |
| An email with pasted inline images | They are stripped from the note; you would be demoing a known gap |
| A portal user login | Refused by design; it looks like a failure |
| An ngrok URL or its warning page | Looks unfinished. Use the stage/production domain |
| Editing `config.js`, the manifest, or any terminal | This is a client demo, not a deployment demo |
| An email with no subject (unless deliberate) | Blocked with an inline error |

If something does go wrong on camera, do not fight it. Stop, cut, restart the
scene. A clean second take is faster than explaining an error.

---

## Part 4 — Recording it

Your session is X11 on display `:1`, screen 1920x1080. `ffmpeg` is installed.

### Screen + microphone

```bash
cd ~/Videos 2>/dev/null || cd ~
ffmpeg -video_size 1920x1080 -framerate 30 -f x11grab -i :1 \
       -f pulse -i default \
       -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
       -c:a aac -b:a 128k \
       aktiv_outlook_demo.mp4
```

Press **`q`** in that terminal to stop. Wait ~3 seconds after starting before
you speak, and hold ~2 seconds at the end before stopping — it gives you room to
trim.

### Screen only, no voice

Drop the two `-f pulse -i default` and `-c:a aac -b:a 128k` lines. Record the
picture first and add narration later if you are not confident speaking live.

### Just the browser window, not the whole desktop

```bash
xwininfo   # click the Chrome window; note Width, Height, and Corner X,Y
ffmpeg -video_size <W>x<H> -framerate 30 -f x11grab -i :1+<X>,<Y> \
       -f pulse -i default \
       -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p \
       -c:a aac -b:a 128k aktiv_outlook_demo.mp4
```

Use even numbers for `<W>` and `<H>` — H.264 requires it.

### Prefer buttons to commands

`kazam` is installed: launch it, choose **Screencast**, pick full screen or an
area, and set it to capture the microphone. Same result, no terminal.

### Check your microphone before the real take

```bash
ffmpeg -f pulse -i default -t 5 mictest.wav && ffplay -autoexit mictest.wav
```

Recording ten minutes with a dead mic is the single most common way to lose an
afternoon.

### After recording

```bash
# Trim: keep from 00:00:04 to 00:08:30
ffmpeg -i aktiv_outlook_demo.mp4 -ss 00:00:04 -to 00:08:30 -c copy demo_trimmed.mp4

# Shrink for email/Teams (usually 3-5x smaller, still sharp)
ffmpeg -i demo_trimmed.mp4 -vcodec libx264 -crf 28 -preset slow \
       -acodec aac -b:a 96k demo_final.mp4

ls -lh demo_final.mp4
```

Watch it back once, all the way through, before sending. Check the panel text is
readable and your voice is audible.

---

## Quick card — keep this visible while recording

```
0:00  OPEN   "Hi Dan, Anita here..." — who, how long, his problem, three things,
             "not a mock-up".  Screen still. Do not click.
0:45  bridge "Let me start where your team starts. In the inbox."
0:45  Aktiv for Outlook → Connect (4 fields) → header shows server + user
1:45  Email A  → Create CRM Lead → Odoo: title, contact, note, attachment
3:00  bridge "Say this one is a support problem, not a sale."
3:00  Email C  → Create Helpdesk Ticket
3:45  bridge "Now the part that usually goes wrong — the second email."
3:45  Email B  → Add to existing Lead… → pick → Added to <name>
5:15  bridge "And it is not only for mail you receive."
5:15  New email → To → subject → attach → Create CRM Lead
5:45  Send & add to Lead… → pick → "Added to X. Sending…" → window closes
      → show Sent Items + the note reading "Sent to:"
6:00  new address → Send & create Lead → "Lead created (#N). Sending…"
      (or Send & add to Lead… → "no leads found" → Create a new lead and send)
6:15  bridge "The three questions your IT team will ask."
6:15  Disconnect · API Keys · internal users only
7:00  CLOSE  Three promises back · what it costs him · the ask:
             "one mailbox and one test user, this week."  End on the ask.
```

**Pause 2 seconds after every result message. Do not fill silence.**
