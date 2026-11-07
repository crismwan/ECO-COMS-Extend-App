# Narration, 7 November 2026 deck

What each slide's audio says (from the speaker notes).

## Slide 1

Good [morning]. This is an update on where COMS stands today, 7 November. Last time [the solution architect] walked us through shell roles and what COMS is for, and on 3 November we showed Phase A running. Since then we’ve hardened it and filled in a lot of what people asked for: browsing for positions instead of remembering IDs, naming rules for new shell organizations, pattern formats you maintain in the app, an audit trail that links to Workday itself, and an access review for vacant positions. And this week, pattern fields are checked against Workday itself: academic units, course subjects and academic periods are picked from Workday, not typed.

I’ll start with an architectural overview: the shell-role model, today’s architecture, and where COMS sits in it, so we share one picture. Then three things, with one slide on what changed this week. One: play back the goal in the architect’s own terms, so we agree on what “done” means. Two: show what we built and how it maps to Phases A, B and C. Three: propose the target architecture and data flow, including how we answer the concern about delegating AAA.

I’ll finish with the decisions I need from this group.

## Slide 2

In Workday, every role assignment is a three-legged stool. The assignee, usually a position. The assigner, the context, usually an organization. And the assignable role. The architect’s example: Luca’s position is an Advisor, for the academic unit Electrical Engineering.

Shell roles use exactly the same stool, with one twist: the role isn’t attached to any Workday security group. So inside Workday it grants nothing. It’s an empty shell. Its power is outside: the role assignments are extracted from Workday into AccessUBC and pushed to the target application, like Clockwork or OAMS, and soon AWS.

My analogy: Workday is a building with a key office. Shell roles are keys cut in that key office, labelled and logged there, but they don’t open a single door in this building; they open doors in other buildings across campus.

Why do it this way? Because the key is attached to the desk, not the person. The must-have: when someone leaves their position, for any reason, their access to the downstream app turns off, using Workday’s own HR events. The nice-to-have: when their replacement is hired into that position, access turns on by itself.

## Slide 3

This is the architect’s diagram, and it’s busy on purpose: it’s the whole shell-role machine. Three bands.

Top band, Workday. On the bottom row of that band you see the shell pieces: a worker in a position, a shell position role assignment, a shell organization with the X-code naming, and a shell assignable role. Above them, the meta layer: the Organizations and Roles Assignment Administrator role, what we call AAA, assigned on a meta organization, which is how someone is allowed to manage an application’s roles.

Middle band, AccessUBC. Everything is extracted from Workday into AccessUBC, which can also hold ad hoc assignments with a sunset date, and approver groups.

Bottom band, the application. It receives the shell role assignments, organizations and roles, and maps each role to its own grants and permissions.

The key phrase is “extract”: Workday is the source of truth, everything downstream is fed from it. COMS lives entirely in the top band. It never talks to AccessUBC or the applications directly; it just makes the Workday side easy and safe to maintain.

## Slide 4

“So that’s today. Here’s where COMS fits into that picture.”

“Users come in through their normal Workday sign-in. Everything inside the big box is the Workday tenant, and COMS lives entirely inside it: the pages people use, the orchestrations that do the work, and COMS’s own records, its requests, audit log and bulk runs.”

“When COMS makes a change, it doesn’t write to Workday’s data directly. It calls Workday’s own services: the Human Resources web service to create or inactivate a shell organization, the Staffing web service to assign roles, and the Business Process API for reviews. So Workday’s own rules and validation still apply, and Workday stays the source of truth.”

“And the only arrow that leaves the tenant is the one that’s already there: AccessUBC extracting the current role assignments from Workday, then the applications turning roles into access. COMS doesn’t touch it.”

[POINT at the four numbers] “Inside the tenant, three Workday services, one boundary crossing, and zero changes downstream.”

Bridge to the next slide: “With that picture in mind, here’s what we were asked to do.”

## Slide 5

Here’s what I heard in the briefing, in three boxes.

Objective one: exit Appian. COMS runs on Appian today; moving it to Workday Extend lets us retire that license.

Objective two: get our hands dirty with Extend on something low risk. COMS has very few users, the change management is small, and the subject-matter experts are in this room.

And the point of COMS itself: fewer tickets to ISC. Shell organizations for a tool like Clockwork change every term, at a granularity as fine as one section of one course in one academic period. Today each of those is an ISC ticket. COMS delegates that to the Clockwork administrators, bounded to Clockwork’s own organization type, so they can never create a supervisory org, an academic unit or anything else inside Workday.

One more thing the architect was clear about: the Appian version was built too narrowly, only for one shape of pattern. The rebuild should be schema-driven: Clockwork wants five columns, the next tool might want seven, and adding a tool should not mean rewriting the app.

## Slide 6

Three pains, all from the briefing.

One: ISC is the bottleneck. In Workday only ISC, with elevated privileges, can create shell organizations and assignable roles. That was fine for stable apps: TeachEval and Exam Management have two shell orgs each. It’s not fine for Clockwork, where the shell organizations encode course, section and academic period and change every term. Every one is a ticket.

Two: the Appian COMS was built too narrowly. The design the architect handed over was flexible, a schema per application, but what was built only handles Clockwork’s shape. The next tool would mean another rebuild.

Three: the AAA concern. If we delegate the AAA role inside Workday, that person can see other role assignments on a position, including real Workday roles, and click delete. It doesn’t delete; it sends a request to the owner. But if the owner also clicks agree without reading, someone loses access. Two errors in a row. The architect thinks that’s a little overblown; ISC is uncomfortable with it. Either way, the cleanest fix is to make the first error impossible, and that’s Phase C.

## Slide 7

Phase A, move COMS off Appian. Built, and since 3 November hardened further. In our development tenant, an application team can create shell organizations and pattern organizations through one form that reads each application’s own format: Clockwork’s five fields, academic unit, subject, course, section and academic period, and fourteen other applications with theirs. The app enforces the naming rules and the org type and subtype, so nothing outside the application’s own tree can be created. New this week: adding a shell organization now follows the naming rules for both kinds, X:META for an application level and X:SHELL under an application, checked on the page and again on the server. The pattern formats themselves are maintained in the app, on Maintain Application Pattern, rather than in code. Organizations can be inactivated or reactivated, never deleted, so the meaning of an existing role assignment never changes underneath it. Everything is audited, and each audit record now links to the Workday event behind it. The “right way” part the architect asked for is done: Clockwork’s hand-built wizard is retired, and every application uses the same schema-driven form. What’s left for Phase A is locking the records behind an integration user and a pilot with Clockwork.

Phase B, shell assignable roles. Partly built: there’s a request form, it runs through a real Workday review business process, and ISC links the Workday role at the end. ISC sees its queue, oldest first, on a card on their Workday Home page, and we now measure turnaround and how long each request has been waiting; a reviewer gets a reminder after two days. AAA requests now use the application’s full ID in the role name, X:BPMS(COMS), so duplicates of existing Workday roles are caught. That already replaces the fiddly ticket. Full delegation, no ISC step for roles that stay inside an application’s boundary, is a policy decision for this group.

Phase C, contextual role assignments. The mechanics are built: assign positions to shell roles one at a time, in an in-app grid, or by Excel, and only X: shell roles are ever shown. Since 3 November every position picker can be browsed by supervisory organization, the way Workday’s own prompts work, and an Access Review page lists shell roles still held by positions that have become vacant. What’s missing is per-user scoping, so a Clockwork admin sees only Clockwork. That’s the piece that answers ISC’s concern, and it’s the centre of the proposal.

“Phase A is done; B and C are not done, but they’re close, and the hard plumbing exists.”

## Slide 8

Six things changed on the sixth and seventh, all live in the development tenant.

Picked from Workday. On the Add Pattern form, a field that has to match something in Workday is now a list, not a text box. Academic units by subtype, course subjects by first letter, academic periods by academic year, or type a code or a name to search. The box underneath shows exactly what goes into the name.

Checked twice, at scale. Every value is checked against Workday on the page as you choose it, and again by the orchestration before Workday is changed. Each check is one small query for that one value, so it stays quick even with tens of thousands of subjects or periods.

Rules or regex. Each field’s format can be a simple rule, like two to four capital letters, or a regular expression for the hard cases. You can switch between them and copy either way, so nobody has to read a regular expression unless they want to.

The value, mapped. A value stream map now shows today’s path, a ticket and a queue, against COMS, a checked change in seconds; it’s on the requirements page too.

Team naming standard. The app and its orchestrations now follow the X T N D and I O R C naming standard, and the Workday setups that point at them were updated.

More gates on deploy. Every deploy now also runs Workday’s own App Builder validation and Workday’s code review tool, Arcane Auditor, before anything reaches the tenant.

And one thing worth saying out loud: the subject and period checks are switched on for Clockwork and Final Grades, and the tests read whatever is in Workday at the time, so they keep working when the data changes. It changed twice today.

## Slide 9

The architect described it beautifully: “I do exam accommodations for all physics courses. No, only 100-level. No, only Physics 100, section 101. No, section 101 in a particular academic period.” That granularity is exactly what Clockwork’s shell organizations encode.

Step one: the Clockwork administrator opens Add Pattern from Shell Org Manager, picks Clockwork, and fills five fields: academic unit, subject, course, section and academic period. Any field left blank means “any”, so the same form makes a coarse pattern, all physics, or a fine one, one section in one term.

Step two: COMS builds the full name live and checks every part against Clockwork’s own format: capital letters, a real course number, a valid term. If something is wrong, the field says what it expects, with an example, and on OK it refuses a pattern that already exists.

Step three: on OK, COMS creates a real Workday custom organization of type X:CLW and subtype X:SHELL. Only inside Clockwork’s own tree; it physically can’t create a supervisory org or an academic unit.

Step four: positions are assigned to Clockwork’s shell roles on that organization, and the next extract carries it through AccessUBC to Clockwork.

The code on the slide is a real one we created in development. No ticket to ISC anywhere in this story.

## Slide 10

This is the first thing everyone sees: the RBAC Hub.

Think of it as a car dashboard. Needs My Attention: your own requests and bulk uploads. ISC Queue: what Security still has to review, and what’s overdue. Shell Org Manager: how many shell organizations are live. Audit Log: changes in the last 24 hours. And Insights, one click to the trends.

Since this screenshot, two cards were added: Pending Requests by Age, which groups waiting requests by business days, and Access Review, for shell roles held by vacant positions. On the right is App Activity: one bar per day for the last week, split into the three things COMS does, shell organizations, role assignments and role requests. One glance tells you whether the app is being used, and for what. Click it and you land in the Audit Log filtered to the same seven days.

Two design rules. Every card answers one question and is a doorway to where you act on it. And every subject has one icon, used on every page: the badge always means role requests, the building always means shell organizations, the inbox always means work waiting for review.

These are real screens from our development tenant, so the numbers are test numbers.

## Slide 11

If the hub is the dashboard, Shell Org Manager is the map.

Four tabs. Summary: how many key rings are active, inactive, and how many naming patterns exist, with quick buttons to add more. Application Patterns: the naming templates per application. Application Shell Organizations: every key ring with its status and an Inactivate or Activate button. And Manage Role Assignments: one row per role on each organization, with the positions and the people in them.

The trick that makes it usable at scale is the bar above the tabs. It opens on all thirty-three applications, worked out from the shell organizations themselves, so a new application appears without anyone adding it. Pick a family, BPMS here with sixteen applications, and its applications appear as buttons: a filled dot means the pattern format is set up, an open circle means not yet. Pick one and the whole page narrows to that application, with previous and next to step through the family and one click back to everything. You go from “everything in the university” to “my team’s stuff” in two clicks.

Note for the technical crowd: this page is reading live Workday data through WQL, Workday’s query language, so it is never a stale copy.

## Slide 12

The best app is the one you don’t have to remember to open.

On everyone’s Workday Home page there are now two COMS cards. A requester sees My Role Requests: how many are pending, the oldest one and since when, and a link that fits: Track My Requests, or Request a Role if they have none. ISC reviewers see the ISC Queue card: how many are waiting, the oldest, and Review Now. The numbers are live; they come from the same records the app uses.

There’s also a COMS section on the Worker Profile, so an administrator finds their requests where they look up people, and every review step lands in the reviewer’s normal Workday inbox.

And inside the app, every page now has the same look: a clear title, a short About box you can open when you need it, the same grid style, and back links in the same place. Small things, but they’re why nobody needs training.

## Slide 13

This is the Add Pattern form, and it’s the same form for every application. What you see here is Clockwork’s version: the format guide at the top, the field names, the examples in each box, all come from Clockwork’s schema record, which an administrator now maintains in the app on Maintain Application Pattern. Pick a different application and the same page draws that application’s fields.

Fields that must match Workday, like academic unit, subject and term, are picked from a list now; I’ll show that next. As you fill in the rest, the Pattern Name Preview builds the full Workday name. If a value breaks the rule, here a lowercase term, the field says exactly what it expects, with an example. A Saturday effective date is refused. And on OK, COMS checks the pattern doesn’t already exist before it calls Workday at all.

After OK you get a receipt: what was created, the effective date, and a View in Audit Log link to its record.

The phrase I use for this: guard rails, not gates. It doesn’t slow good requests down; it stops mistakes before they become Workday data.

## Slide 14

This is new this week. On the left, the Subject list for Clockwork. Click it and you browse: a folder for each letter, here C, with every course subject Workday has, its abbreviation and its name. Or just type, say phys, and Workday finds the nineteen matches.

In the middle, the Academic Period list, opened on the 2024-25 academic year. You can pick a single term, or the whole Winter session, the Summer, or any period in the year, and there’s a folder for wildcards, like Winter Term 1 every year.

On the right, the result. The subject shows as picked, and the line under it, Subject in the name, is exactly what goes into the pattern name. A period goes in as its short form, so 2024-25 Winter Term 1 becomes 2024W1, the same form Clockwork’s patterns already use.

Why this matters: a pattern can’t name a subject or term that doesn’t exist, and it can’t be misspelled. Every value is a small Workday query, checked as you pick it and checked again on the server, so it stays fast even with tens of thousands of subjects.

## Slide 15

Sometimes you need to change one desk. Sometimes you need to change two hundred. ECO-COMS has three ways, and you pick by size.

One: Manage Role Assignment. Open a role on an organization, pick positions to add or remove, OK. Done.

Two: the in-app grid. If you’ve used an EIB, this will feel familiar, except you never leave the app. Pick an application, and the grid fills with every position that holds a role there. Tick Remove on the rows you want gone; click plus to add a row and search for the position. Each column checks itself as you go: for example it tells you immediately if that position already has that role. Up to 50 changes per submit.

Three: the Excel template, for big or offline work. You download it from the app, and it comes pre-filled with every current assignment, so you only mark what changes. It has drop-downs, format checks, duplicate detection and a status box that says “Ready” when the file is clean. Save as CSV, upload. Up to a thousand changes per file.

And whichever you use, there’s a dress rehearsal. Validate-only runs every row through Workday’s checks and changes nothing. You see a row-by-row result, fix anything red, then press Apply. Just like rehearsing before opening night.

Why 50 and 1,000? Platform limits: a page must finish in 60 seconds, and a background job in production must finish within 60 minutes. We set the limits so a run always finishes cleanly.

## Slide 16

Four promises.

One: no self-approval. If you start a request, Workday itself removes you from the approver list. Not a convention, a rule in the business process.

Two: every change is recorded. Creating an organization, inactivating it, adding or removing a position on a role, requesting or approving a role: each writes an audit record with who, what and when, shown in Pacific time to the minute. Each record also links to the Workday event behind it, so an auditor can go from our log to Workday’s own history in one click.

Three: success means success. This sounds obvious but it isn’t. When a page hands work to a background process, Workday normally says “accepted” even if the work later fails. ECO-COMS doesn’t trust that: after every change it goes back and checks the result is really there before it tells you “done”. If Workday rejected it, you see the rejection. Think of registered mail: we don’t say “sent”, we wait for the signed receipt.

Four: you only see your part. Seven security domains, configured in Workday, decide who sees which pages and who can change what.

Coming next, being honest: today the audit records can still be edited through the REST API by people with full rights. The fix, an integration system user that alone writes those records, is built and waiting for setup.

## Slide 17

The hub tells you what needs you today. Insights tells you whether COMS is doing its job.

Top row: ISC turnaround, the median time from request to approval over the last 90 days; what’s pending and overdue after three business days; approvals and changes in the last 30 days; bulk runs and how many failed.

Then the breakdowns: role requests by status and by application, active versus inactive shell organizations, changes by action. And at the bottom, Applications at a Glance: one row per application with its shell orgs, patterns, pending, approved and denied requests, and its last request. Click an application and you land in Shell Org Manager filtered to it.

For anyone who wants their own reports, there are four lean Workday report data sources, so a custom report is a Workday task, not a development request.

This is the slide for managers: it turns “we think it’s helping” into numbers.

## Slide 18

ECO-COMS is a Workday Extend app. That matters: nothing runs outside Workday. No separate server, no separate database, no extra logins. It’s deployed into the tenant and uses the tenant’s security.

Top to bottom, four layers.

People: requesters, reviewers and admins, using the normal Workday UI, on web or phone.

Pages: 40 pages and 45 dashboard cards, plus two cards on the Workday Home page. They’re defined as metadata (Workday calls them PMD files) and they do the first round of checking: required fields, naming rules, dates, duplicates.

Then three things the pages talk to. Logic: thirteen orchestrations, Workday’s server-side workflows, sharing four sub-orchestrations so the common steps, like writing an audit record, exist once. They do anything that needs more than one step: call Workday’s web services to create an organization or assign roles, check the result, write the audit record. App data: five business objects, which are the app’s own tables (applications and their schemas, requests, audit log, bulk runs, row results) plus two file stores for uploads and templates, and four report data sources for custom reports. Live reads: six WQL queries and one Graph query that read organizations, roles and positions straight from Workday, so we never keep a copy that can go stale.

At the bottom, Workday core: the real Custom Organizations, the Assign Roles function, our review business process, and security domains.

the pages are the dining room where you order, the orchestrations are the kitchen that does the cooking, the business objects are the pantry and the order book, and Workday is the farm everything comes from. The customer never walks into the kitchen; the kitchen never lets a wrong order out.

## Slide 19

One design principle: COMS becomes the delegated control plane for shell roles, and nothing downstream changes. AccessUBC and the applications keep consuming Workday exactly as they do today.

Inside the Workday tenant, COMS has six parts. Grey ones exist today; orange ones are new.

One, Context: when you open COMS it works out which applications you manage, by reading your own meta role assignments, the AAA role on the meta organization X:«code» from the architect’s diagram. You never pick from applications you don’t own.

Two, the Schema registry, built since last week: one record per application holding its prefix, org type and subtype, and its pattern schema: which columns, in what order, with what rules or lookups. Clockwork has five columns, another app seven. Onboarding a new tool is data, not a code change.

Three, Pages: one generic form, the in-app grid and the Excel template, all driven by the schema and filtered by context. Already built for every application with a schema.

Four, Guarded orchestrations: the server side re-checks both context and schema before calling Workday, so nobody can go around the page.

Five, Audit: every change recorded, written by an integration user so records can’t be edited through the API.

Six, a COMS API: a read and request interface so automation, like the AWS account provisioning the architect mentioned, can create shell orgs and assignments the same safe way, instead of a person copy-pasting.

Underneath, Workday core stays the source of truth: the custom org hierarchy, the shell roles, the position role assignments and the review process. And out of the right side, the same extracts as today.

A one-line summary: “Same pipes downstream, a smarter and safer front door upstream.”

## Slide 20

Top lane, provisioning, driven by the application’s admin.

1, sign in: COMS resolves my context, the applications I administer, from my own AAA meta assignments.

2, enter the change: the generic form for a new shell organization, or the grid or Excel template for role assignments.

3, check, twice: the page validates against the application’s schema and my context, and the orchestration validates again on the server. Two locks.

4, write: COMS calls Workday’s own APIs, the custom organization API or Assign Roles. Workday stays the source of truth.

5, record: an audit record, then the receipt on screen only once Workday has confirmed.

6, extract: on the existing schedule, AccessUBC picks it up and the application maps the role to its grants.

Bottom lane, deprovisioning, and this is the must-have from the architect: there is no COMS step at all. When HR terminates someone or moves them, they leave the position. The role assignment stays on the position, the desk, but nobody is sitting there, so the next extract turns their access off. And the nice-to-have: when a replacement is hired into that position, access turns back on, with no ticket.

“COMS only touches the top lane. The bottom lane is Workday doing what it already does well.”

## Slide 21

Let’s go straight at the concern. In the standard Workday task, a AAA looking at a position sees every role assignment on it, including real Workday roles that aren’t theirs, and can request that one be deleted. The architect called it two errors: I click delete by mistake, the owner clicks agree without reading. Rare, but someone loses access, and ISC has to clean up.

The fix is to make the first error impossible. In COMS, a Clockwork administrator only ever sees X:CLW shell roles and Clockwork’s shell organizations. They can add and remove those, and nothing else exists on their screen. And it isn’t just hidden in the page: the orchestration on the server re-checks every change against the same context, so even a hand-crafted request can’t touch anything else.

How does COMS know my context? From Workday itself. The architect’s diagram already has it: the AAA role assigned to my position on the meta organization X:«code». COMS reads my own meta role assignments and turns them into the list of applications I manage. If I administer two, say Clockwork and Exam Management, I pick which one I’m working on, exactly as the architect described.

This means we could stop handing people the standard AAA task at all, the architect’s “Plan B”: keep the AAA meta role as a marker of who manages what, but do the work in COMS. Must-have deprovisioning still works because it’s all position-based.

“Would scoped COMS access address your concern?”

## Slide 22

The architect’s complaint about the Appian version was that it hard-coded one shape. We didn’t repeat that.

Every application has a schema record: its prefix and org type, always subtype X:SHELL; its columns, in order; and the rule for each column, with a hint and an example. A rule is either a simple setting, like two to four capital letters, or a regular expression, and you can switch between the two. Clockwork has five columns: academic unit, subject, course, section and academic period. Final Grades Submission has two. Admissions has several prefixes and one role-name column. Fifteen applications in all, and every example in them is checked by our tests.

One engine reads that record to draw the form, build the name preview, validate on the page, and validate again in the orchestration before Workday is called. A blank field means “any”, so the same scheme can say “any physics course” or “Physics 100, section 101, winter term one.”

Onboarding the next tool is now filling in a record with its owner, not a development release, and since 3 November that record is edited on a page in COMS, Maintain Application Pattern, with copy-from-another-application and an audit trail. Clockwork itself moved onto this engine; its old wizard is gone.

Last week I said lookups were still to do: a column that must match something real in Workday. That’s done now. A column can carry a Workday check, academic unit, course subject or academic period, switched on per column in the same page. Clockwork has all three; Final Grades checks its subject. The form then offers a Workday list for that column, and the orchestration checks the value again before Workday is changed.

## Slide 23

Let me show what happens when someone clicks OK, say to add a position to a role.

First the page checks: required fields, naming rules, weekday dates, no duplicates.

Second, the guard. The orchestration doesn’t trust the page. It re-checks every input: is this organization really one of our shell orgs, is the action allowed, do the parameters agree. That matters because anything that can be called from a page can, in principle, be called directly; the guard closes that door.

Third, the actual Workday call, through Workday’s own web services, the same ones Workday’s integrations use. Assign Roles, Organization create, inactivate, reactivate.

Fourth, the audit record, written only after the call is confirmed successful. So the log can’t say something happened that didn’t.

Fifth, the receipt: the page goes back and confirms the audit record exists before it shows “done”.

This is the registered-mail idea from before. Technically we call it run-and-verify, and it fixed a real problem we found: Workday reports a background launch as accepted even when the work later fails. Without this step users would have seen false successes.

## Slide 24

The grid and the Excel upload look different, but behind them is one engine. That’s deliberate: one set of checks, one place to fix a bug.

The upload stores the CSV as a file record. The grid writes each change as a draft row. Either way, the page then starts an asynchronous orchestration, a background job, and returns immediately so nobody stares at a spinner.

The job takes each row: looks the position up in Workday so the name and ID are Workday’s own, calls Assign Roles (or, in validate mode, only checks), and writes a row result: VALID or INVALID for a rehearsal, DONE or FAILED for the real thing, with Workday’s own message when something is rejected. A failed row doesn’t stop the others.

About the limits, because someone always asks: they aren’t business rules, they’re physics. A page request in Workday Extend has 60 seconds, so the grid takes 50 changes per submit. A background run in production has 60 minutes, so a file takes a thousand. Unchanged rows in the pre-filled template don’t count.

it’s a sorting office. Two letterboxes, one sorting machine, and every letter gets a delivery stamp.

## Slide 25

Security is layered, because a lock on the front door doesn’t help if the back door is open.

Pages: seven Workday security domains decide who can open each page. A requester doesn’t see admin pages; they don’t even appear.

Orchestrations: these can be called by URL, not only through a page. So every orchestration a user can launch is secured by the same domain as its page. Without that, someone clever could skip the page.

Inputs: inside each orchestration a guard re-checks the parameters before anything reaches Workday: the organization really is one of ours, the action matches, the values are allowed.

Approvals: role requests go through a real Workday business process, and the requester is excluded from approving their own.

Records: the last layer is built but waiting on setup. We want audit and request records to be written only by an integration system user, so that nobody, even with full app rights, can quietly edit history through the API. The code is ready on a branch; it needs the ISU created and assigned in each tenant.

your key card opens your floor, the safe in the room has its own code, and the front desk keeps a log nobody else can edit. We have the first two fully and the third nearly done.

## Slide 26

Everything about ECO-COMS lives in GitHub, and nothing reaches Workday by hand.

Push a change and a pipeline runs. First, static checks: dozens of known Workday Extend pitfalls, each one learned the hard way, encoded as tests. Things like lowercase page types that silently break a page, card parameters that fail a deploy, or a hidden OK button. If any fails, the upload is blocked before it touches the tenant. Since this week the pipeline also runs Workday’s own App Builder validation, and Arcane Auditor, the code review tool from Workday’s developer relations team, on every deploy. And if Workday’s own build rejects something, the pipeline now prints Workday’s build errors in the run.

Then it uploads to Workday’s App Hub and deploys to the development tenant, usually in one to three minutes. Then smoke tests run against the real tenant, reading every collection and checking that requests and their business process events agree.

Many pages are generated by scripts rather than hand-edited, and a check proves the scripts reproduce exactly what’s committed. That keeps 40 pages consistent: same headings, same back links, same help boxes.

Beyond smoke there are suites for full write tests, cleanup of test data, one-off repairs, a second-user test and the security lockdown. Thirty-two in all, including a demo reset, a check that every application schema’s examples really pass its own rules, and guard tests that send bad input to each orchestration and check it’s refused.

The numbers on the slide: 513 commits since the project started on October 29. [Update the commit count on the day; it keeps growing.]

every car goes through the car wash and the inspection bay before it gets on the road.

## Slide 27

The headline numbers: 40 pages and 52 cards, plus two cards on the Workday Home page; thirteen orchestrations doing the work behind them, sharing four sub-orchestrations; five business objects and two file stores holding the app’s own data; fifteen application schemas; seven security domains and one review business process.

And my favourite number: zero. Zero servers outside Workday. No extra infrastructure to patch, no extra database to back up, no extra login. Everything runs inside the tenant with the tenant’s security.

If someone asks “how big is this?”: it’s a substantial Workday Extend app, built and tested like a software product, not a one-off configuration.

## Slide 28

“Let’s follow one change. A Clockwork administrator needs a shell organization for next term.”

[POINT at the top lane] “Today: they fill the Appian form, or for any other application they raise a ticket. It waits in ISC’s queue. ISC reads it, often has to ask for missing details, and then keys it into Workday by hand. Four steps, two hand-offs, and a queue in the middle.”

[POINT at the bottom lane] “With COMS: the administrator fills one form in Workday. It’s checked as they type: format, dates, duplicates. On OK, COMS makes the change in Workday in seconds, and writes a receipt and an audit record. ISC only steps in for something genuinely new, a new assignable role, and approves it in their Workday inbox.”

“You saw that a minute ago: the change I applied in the demo is already in the Audit Log, linked to the Workday event.”

[POINT at the right-hand end of both lanes] “And notice where both lanes end: the same place. AccessUBC extracts the current role assignments from Workday, exactly as today. Nothing downstream changes. It just gets there sooner, and right first time.”

[POINT at the four numbers] Pick two: four steps become two; the ISC queue disappears for routine changes. If asked how long the queue is today: “We’ll measure it from ISC’s tickets; that’s the number I want for the pilot report.”

## Slide 29

“Why do this in Workday Extend rather than keep Appian?”

“One: one platform. It runs inside the tenant, with Workday’s own sign-in, security and business processes, so there’s no Appian licence, hosting or second support team.”

“Two: it works for every application. In Appian the form only knew Clockwork’s shape; here a new application’s format is a record we fill in. Fifteen applications are set up today, without a release.”

“Three: it’s safe by design. Every change is checked twice, approvals are real Workday business processes where you can’t approve your own request, and every change is on the record, linked to the Workday event.”

“Four: the same pipes. AccessUBC and the target applications don’t change at all.”

[BOTTOM LINE] “So Appian’s cost goes, and the delegation, the checks and the evidence move into Workday, right next to the data they protect.”

If asked about the saving: the Appian licence and ISC’s hours per change are still to be confirmed; offer to bring both numbers to the pilot review.

## Slide 30

Four steps, and the order matters: objective one, exiting Appian, comes first.

Step one, finish Phase A. Switch the audit and request records to an integration system user so they can’t be edited through the API; the code is ready and waiting on the ISU setup. Pilot with the Clockwork administrators. Promote through implementation and sandbox to production. Then cut over and retire the Appian COMS. That’s the license saving.

Step two, context scoping. The schema engine, “COMS knows what each application’s organizations look like”, is already built. Scoping adds the other half: “COMS knows which applications you own.”

Step three, Phase B: delegate shell assignable roles inside each application’s boundary, if this group agrees.

Step four, Phase C and beyond: scoped role assignments become the way AAAs work, so the standard AAA task can be withdrawn, and a COMS API lets automation, like AWS provisioning, use the same safe path.

The same pipeline carries every step, with the same checks. One operational reminder: the integration user has to be assigned to the app again in every tenant; it doesn’t carry over on promotion.

## Slide 31

One: scope every COMS user by their own AAA meta assignments. We recommend yes; it’s what removes the first of the two errors and answers ISC’s concern.

Two: delegate shell assignable roles, Phase B, but only roles inside an application’s own X:«code» boundary. Anything else stays with ISC. Today our role requests still go through an ISC review step; this decision would let in-boundary roles skip it.

Three: shell organizations are add and inactivate only. The architect was clear: once a role assignment depends on an organization, its meaning must not change. COMS already never renames or deletes; we want that written down as policy.

Four: a question raised in the briefing: has Workday improved custom organization security since we designed shell roles? Neither of us knows of a change, but we should check the current release before building Phase C, in case Workday now offers some of this natively. Even if it does, the schema validation in COMS stays valuable.

Five: a COMS API for automation, such as AWS account provisioning. We recommend yes, after context scoping is live, so the API inherits the same boundaries.

## Slide 32

Bring it home in one line, and pause after it: same pipes downstream, a safer front door upstream. Today a shell change is a ticket and a queue; with COMS it’s a checked change in seconds, on the record, inside Workday, and Appian can go. AccessUBC and the applications don’t change. What changes is that application teams can maintain their own shell organizations and, with your agreement, their own shell roles and assignments, inside Workday, inside their own boundary, with every change checked and recorded.

Three asks. One: agree that Phase A is ready for a pilot with the Clockwork administrators. Two: decide on context scoping and on delegating in-boundary shell roles, the decisions from the previous slide. Three: get the integration system user set up so we can lock the records, and then let’s put dates on the plan.
