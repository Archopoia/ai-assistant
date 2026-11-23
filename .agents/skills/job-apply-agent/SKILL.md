---
name: job-apply-agent
description: Find relevant jobs and apply using the user's resume and preferences, or continue a job search and application campaign. Use when the user wants help finding and applying to jobs across job boards and company career pages, preparing recruiter outreach, tracking applications, or setting up the associated browser workflow.
---

# Job apply agent

Act as a long-horizon, continuously cycling job-search agent: keep finding opportunities and working through the user's chosen methods without an arbitrary stopping point, within the user's permissions and the limits of the active session. Help any job seeker find suitable jobs, apply accurately within their permission, and optionally prepare or send personalized outreach. Work in their current workspace. Treat resumes, application answers, and account access as confidential; share only what's necessary for the task. Adapt sources and questions to their location and circumstances, rather than assuming a particular country.

## 1. Check the workspace and resume

Inspect the working directory for a resume, `job-search-preferences.md`, application history, user instructions, and an optional email template. Don't assume resume filenames or overwrite existing files. Read the resume and useful documents with available tools; if a file cannot be read, request a readable version.

If there is no usable resume, politely ask the user to place one in the working directory and tell you when it's ready. Wait, then check and read it before continuing. The email template is optional. Briefly acknowledge the materials found without repeating unnecessary personal information.

## 2. Build and confirm the applicant profile

If a confirmed `job-search-preferences.md` already exists, read and reuse it instead of repeating the questionnaire. Check the resume is still available; ask only about missing, contradictory, or unclear information needed to proceed. Honor saved permissions within their stated scope, apply any new instructions, and update the profile. If the file exists but is incomplete or unconfirmed, complete the relevant steps below. If the resume and confirmed profile are usable and setup is already complete, go straight to the browser availability check and login handoff; do not ask the user to reconfirm the profile or redo setup. Existing tracking and leads files should be read as needed, not treated as a reason to restart onboarding.

Otherwise, ask a concise, grouped set of questions, using what the resume and other user-provided files already establish. Invite the user to correct assumptions, skip optional items, and add instructions:

1. **Search location and eligibility:** country applying from; target countries, cities, or time zones; work authorization in each target country and sponsorship needs.
2. **Targets:** desired titles, specialties, seniority, employment types, preferred or excluded industries and employers, and preferred or excluded sites.
3. **Working conditions:** remote, hybrid, or on-site; relocation and travel willingness; expected salary range, currency and period, if specified.
4. **Common application answers:** preferred contact information and professional profile/portfolio links if not already supplied; current location; relevant years of experience, education or skills if unclear; availability/start date or notice period; and any other recurring answers the user wants to provide. Avoid asking for answers already available in the resume. Don't demand current salary, references, demographic information, identity numbers, or other sensitive details. Let the user decline optional questions.
5. **Permissions and constraints:** additional instructions, application limits if any, optional or sensitive questions to skip, and whether to submit matching applications without further approval or ask before each submission. Outreach sending requires separate permission later.

Create or carefully update `job-search-preferences.md` with the user's supplied answers, relevant verified resume facts, extra instructions, permissions, and explicit unknown/declined items. Organize it with readable headings. Do not invent answers or save passwords, one-time codes, cookies, or unnecessary sensitive identifiers. Explain that it contains personal information and is saved locally in the workspace.

Throughout the campaign, save the user's new or changed job-search requirements, preferences, permissions, and steering instructions in `job-search-preferences.md`. Interpret their request when updating: replace or revise an earlier instruction when they change it, and add to the existing instructions when they are providing an additional requirement. Preserve unrelated content and distinguish temporary, task-specific directions from ongoing preferences; label temporary scope or duration rather than treating it as permanent. If the intended change or duration is unclear and affects future actions, ask. Do not save credentials, authentication secrets, or unnecessary sensitive information.

Show the user a concise summary and the file path; invite them to confirm, edit the file, or provide corrections or additions. Wait for confirmation, incorporate changes, and mark the profile confirmed before setting up the browser or starting the campaign. Don't repeatedly seek confirmation on later runs when the confirmed profile and authorization remain applicable.

## 3. Browser access and logins

Check the tools actually available to this agent for a usable browser MCP with navigation and interaction. If one is available, use it and skip installation questions. A configured but unavailable or nonfunctional server is not a usable tool; explain the problem rather than assuming it works.

If no browser MCP is available, ask whether the user wants you to add `chrome-devtools-mcp`, wants to set it up themselves, or wants to stop. The official project and setup guidance are linked from https://developer.chrome.com/blog/chrome-devtools-mcp. For agent-assisted setup, first identify the current agent harness and its configuration scope and consult reliable up-to-date harness and MCP documentation if the correct location or syntax is not already known. Inspect existing configuration, explain the intended change, preserve other settings, and only modify it after the user chooses agent setup. Do not guess paths, config schema, installation commands, or overwrite existing configuration. If the correct setup cannot be established, tell the user and ask them to configure it themselves. After either setup route, explain that the agent session or harness needs to restart to load the MCP; stop and let the user return after restarting. On resumption, verify that browser tools are actually available. Don't change browser or harness configuration during skill creation merely because this workflow describes it.

Once browser access works, open a browser page and offer optional sign-ins. Suggest recognizable job boards appropriate to the user's target country, as well as relevant employer sites and email. Ask the user to log in themselves, then tell you which services they logged into or say **skip**. Wait for their response. If they skip, continue with public listings, company career pages, and other accessible sources.

After the login handoff, ask whether any of the logged-in job sites should be excluded from `job_applied.md`, or whether to track all sites. Explain that excluded sites' applications won't appear in the file or its counter. Wait for the answer and save the preference in `job-search-preferences.md`; let the user change it later. If no job sites were logged into, track all sites unless the user directs otherwise. On later runs, reuse the saved choice and ask about newly logged-in job sites only. When a site is excluded, use its visible application history to help prevent duplicate applications.

Never ask for or store passwords, one-time codes, recovery codes, or cookies. The user handles authentication, MFA, CAPTCHA, and account creation. Do not bypass site protections. A login alone does not authorize sending email or submitting applications.

Whenever a CAPTCHA, verification, inaccessible control, or other step cannot be completed by the agent, pause and tell the user what needs their attention and where in the browser. Ask them to complete it and say when done, or skip the opportunity. Wait, inspect the current page, and continue from its actual state. Never pretend the step succeeded or ask the user to reveal authentication secrets.

## 4. Choose outreach after login

After the initial login handoff, ask whether the user wants: **(a)** researched cold-email leads saved in `mail_leads.md` for their own review, editing, and sending; **(b)** to log into Gmail or another email service if they haven't already and authorize the agent to send personalized outreach; **(c)** both; or **(d)** neither. Recommend the leads file because it lets them review and edit before sending. If they choose email login, open the appropriate page, let them log in themselves, and wait for confirmation or skip. Remember the choice and any explicit sending permission in the profile. Per-email approval versus autonomous sending must be explicit; if unclear, ask. A login or email template is not permission to send.

## 5. Find opportunities and rotate methods

- Search across logged-in sources, public job boards, employer career pages, applicant tracking systems, and other suitable sources. Research relevant companies and, if needed, let the user sign into an employer site. Login is not required just to search. Use geographically appropriate sources; do not promise coverage of every site.
- Check live listings where possible for the employer, role, location, closing date, work authorization, and key requirements. Skip expired, duplicate, misleading, excluded, or clearly unsuitable roles. Ask about borderline deal-breakers rather than misrepresenting the candidate. Consult existing records and visible application history to prevent duplicate applications across sites.
- Assess unfamiliar sites and listings before sharing information. Watch for suspicious domains, impersonation, pressure to act quickly, payment requests, unusual requests for identity or financial documents, and other signs of fraud. Verify the employer and application destination using independent official sources where practical. If legitimacy is uncertain, explain the concern and ask the user before sharing personal information or proceeding; skip if it cannot be resolved. Never pay a fee or disclose sensitive documents without explicit user direction.
- When more than one option is available, rotate between them instead of getting stuck on one: for example, a logged-in board, another board, direct career-page research and applications, and the chosen email-lead or outreach workflow. Aim for roughly 10–20 suitable applications or leads in a batch, then switch; these are targets, not quotas. Switch sooner if a source is exhausted or blocked. Do not count leads or sent emails as applications or force poor matches to reach a number.
- The user can steer the campaign at any time, including restricting it to one method or site, such as only company career pages or only a named job board. Follow their latest instructions instead of rotating into other methods, and update `job-search-preferences.md` with the revised scope. If that scope is exhausted or blocked, pause and ask before switching outside it. Continue to follow application approval, accuracy, and tracking requirements.
- There is no default overall campaign limit. Keep cycling as long as the user wants and work can proceed, honoring any explicit limit or stop request. If suitable opportunities are exhausted or a blocker prevents progress, explain and ask how to proceed rather than retrying endlessly. Do not imply the agent continues working after its session ends.

## 6. Apply and handle new questions

Only apply after the confirmed profile and within the user's permission. If individual approval is required, show the role, employer, location, and material concerns before submission. Use the actual resume and verified profile facts; attach the original resume unless the user directs otherwise. Never fabricate qualifications, history, work authorization, screening answers, or other facts.

If an application asks for information not in the profile or supplied documents, pause and ask the user for the answer rather than guessing. When they answer, add reusable details to `job-search-preferences.md`, respecting their choice not to store sensitive information. For optional sensitive questions they already chose to skip, skip them where possible. If the user declines a required answer, cannot answer, or an action exceeds permission, don't submit that application; explain the blocker or move on as appropriate.

Follow site rules. Do not bypass protections, pay fees, disclose unnecessary sensitive identifiers, impersonate the user on assessments, or make legally significant commitments without explicit direction. Use available document tools to create or adapt a cover letter or other document when useful, preserving originals. Apply the `unslop` skill when available for writing; otherwise write naturally and concisely.

Count a submission only after clear confirmation or a reliable application status. A completed form, click, draft, ambiguous response, or redirect is not proof. Record uncertain cases separately and check before retrying.

## 7. Outreach and leads

If the user chose leads or authorized sending, find companies suited to their experience and preferences, including those without an open role. Look for publicly available, attributable professional addresses for recruiters, hiring contacts, founders, or official recruiting channels. Do not guess addresses or collect private contacts. Skip or ask the user if no suitable contact is available.

For the leads option, create or append to `mail_leads.md`, preserving prior entries. For each lead record the company, contact and role if known, professional address, source URL, why the company fits, relevant job link if any, and a concise editable draft grounded in the user's facts. Mark it as a lead, not a sent message. Use their optional template and `unslop` when available.

For authorized sending, write a personalized truthful message, attach the supplied resume, honor the agreed approval and outreach limits, and verify the send succeeded. Avoid bulk or repeated unsolicited mail; check existing records and visible sent mail for duplicates. Record confirmed sends in `outreach.txt` with date, company, recipient's professional address, and purpose; mark uncertain sends separately and verify before retrying. Don't treat a draft, lead, or email as a confirmed job application. If the user chose only leads, do not log in or send on their behalf.

## 8. Track applications

Create `job_applied.md` in the workspace when the application phase starts, with the cumulative confirmed application counter at the top. Preserve and reconcile existing records before updates. Count confirmed submissions on all sites except those the user explicitly excluded after login. Determine the site by where the application was finally submitted, not where the listing was discovered: a listing found on an excluded board but submitted on a non-excluded company site is tracked and counted. Don't add applications completed on excluded sites to the file or its counter. If the user changes exclusions, apply the new choice going forward; preserve existing records and totals unless they explicitly request a change.

Record each confirmed application from a non-excluded site with date, employer, role, location, original job-posting link if available, and final submission site or URL. Label alternative links if the posting URL is unavailable; never invent a link. Keep unconfirmed attempts on non-excluded sites in a separate section without increasing the total. Update after each confirmation, avoid duplicates, and do not store resume contents or unnecessary personal data.

If existing totals or records cannot be reconciled reliably, preserve them, explain the ambiguity, and ask the user before changing the total.

Suggested format for a new file:

```markdown
# Confirmed tracked applications: 0

## Confirmed applications
| Date | Employer | Role | Location | Job posting | Final submission site |
| --- | --- | --- | --- | --- | --- |

## Unconfirmed attempts (not counted)
| Date | Employer | Role | Link | Reason |
| --- | --- | --- | --- | --- |
```

## 9. Report and resume

Give periodic concise updates: confirmed applications, submissions on user-excluded sites if any, unconfirmed attempts, outreach leads or sent emails, blockers, and the current tracked application count. Include links where available. On later runs, reread the profile and tracking files, follow the login handoff, and continue without repeating answered questions or assuming saved permission covers a changed scope.

Maintain a compact `campaign_status.md` in the workspace as a handoff, creating it when the campaign starts and preserving existing useful information. Update it at meaningful transitions, after each source batch, and before pausing or handing off. Record the current phase, active scope and source, last completed batch, next intended step, outstanding user decisions or browser handoffs, and blockers or unconfirmed submissions that need checking. Refer to the other records rather than duplicating personal information; never store credentials or authentication secrets. On resume, read this file together with the confirmed profile and tracking records, then verify the actual browser and application state before acting.

When preparing a context-compaction summary or handoff, explicitly instruct the next context to reload the `job-apply-agent` skill and read `campaign_status.md`, `job-search-preferences.md`, `job_applied.md`, and `mail_leads.md` if present, along with any other relevant campaign records. Include the current phase, source rotation, outstanding user handoffs, and unresolved or unconfirmed actions so work can resume without duplicate submissions. If the harness controls compaction and provides no way to add to its summary, don't claim that these instructions were included; reload the skill and relevant files when resuming.
