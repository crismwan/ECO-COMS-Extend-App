# ECO-COMS live demo · 8 November 2026 · narration

## 01 Title
This is a live demo of ECO-COMS, the Custom Organization Management System, rebuilt as a Workday Extend app. Everything you'll see is running in our development tenant today. First, the picture behind it.

## 02 Today's architecture
This is the architect's diagram of how shell roles work today. Three bands. At the top, Workday: a worker in a position, a shell role assignment on that position, a shell organization with the X-code naming, and a shell assignable role. In the middle, AccessUBC, which extracts all of that from Workday. At the bottom, the application, which maps each role to its own grants. Workday is the source of truth, and everything downstream is fed from it. The hard part is the top band: today, only ISC can create those shell organizations and roles, so every change is a ticket, or, for Clockwork, the old Appian form.

## 03 ECO-COMS solution architecture
Here's where ECO-COMS fits. People sign in to Workday as they always do. Everything inside the big box is the Workday tenant, and ECO-COMS lives entirely inside it: forty pages and fifty-two cards, thirteen orchestrations that do the work, and the app's own records for requests, the audit log and bulk runs. When ECO-COMS changes something, it calls Workday's own services: the Human Resources web service to create or inactivate a shell organization, the Staffing web service to assign roles, and the Business Process API for reviews. So Workday's own rules still apply. And the only arrow that leaves the tenant is the one that's already there: AccessUBC's existing extract, then the applications. Nothing downstream changes. Same pipes downstream, a safer front door upstream.

## 04 The front door: the RBAC Hub
And this is that front door: the RBAC Hub. Every card answers one question. Needs My Attention: my own requests and bulk uploads. Shell Org Manager: two hundred and nineteen active shell organizations. Insights for trends, the Audit Log with every change, and Access Review for roles still held by positions that are now vacant. The ISC Queue shows what's waiting for ISC, and App Activity charts the last seven days. Further down, the quick actions: shell organizations, bulk role changes, and role requests. Let's start where COMS started: patterns.

## 05 Application patterns: one engine
In the Appian version, the pattern form was built for one application, Clockwork. Here, fifteen applications have a schema today, maintained in the app on Maintain Application Pattern. Each row is one application: its prefixes, its fields, and a worked example. Let me open Clockwork. Its prefix is PATTERN, and it has five fields in order: academic unit, subject, course number, section and academic period. Each field has its own rule, either a simple setting, like two to four capital letters, or a regular expression for the hard cases, with a hint and an example. And a field can carry a Workday check: academic unit, course subject and academic period are looked up in Workday itself. One engine reads this record to draw the form, build the name, check on the page, and re-check on the server before Workday is touched. So onboarding the next tool is a record, not a release.

## 06 Add a Clockwork pattern
Here's that engine at work: Add Shell Org Pattern for Clockwork. The fields come straight from the schema. Subject and academic period aren't typed: they're picked from Workday. I can browse subjects by first letter, or just type to search, and the same for academic periods, by academic year, with whole sessions and wildcards too. A period goes into the name in its short form, so twenty twenty-four Winter Term One becomes twenty twenty-four W one. Course number and section are typed, and as I fill them in, the Pattern Name Preview builds the full Workday name. Effective dates must be weekdays: pick a Saturday and it says so, pick a weekday and the error clears. And if I switch to Final Grades Submission, it's the same form with Final Grades' own two fields and its own rules.

## 07 New shell organization naming
Shell organizations themselves come in two kinds, and ECO-COMS knows the naming rules for both. An X:META organization with no application is a brand-new application, so its code becomes the whole name, exactly as typed. Under an application, an X:META name goes in brackets after the application's base, and the code must be in capitals: type it in lower case and the field says so straight away; fix it, and the error clears. Switch to X:SHELL, and the application becomes required, and the name becomes the application, a colon, then the code. The Generated Organization Name shows the result as you go, and the same rules are checked again on the server.

## 08 Shell Org Manager
This is the Shell Org Manager. It opens on every application, worked out from the shell organizations themselves, so a new application shows up on its own. I can narrow to one family, then one application, and the whole page follows. From here, each organization has a detail page with its roles and the people on them, and a status change: organizations are inactivated or reactivated, never deleted, so the meaning of an existing role assignment never changes underneath it.

## 09 Manage a role assignment
Creating organizations is half the job. The other half is putting the right positions on the roles. On Manage Role Assignment, if I click OK without picking anyone, it tells me to pick at least one position. And I don't need to remember a position ID: I can browse the way Workday's own prompts work, by my organizations, by manager, or every supervisory organization from A to Z. The moment I pick one, the error clears.

## 10 Bulk edit, like an EIB
For many changes at once, there's Bulk Edit. Anyone who has used an EIB will recognise it, but you never leave the app. Pick an application, and the grid fills with every position that holds a role there today. Tick Remove to take one off, or add a row and find the position right inside the grid. Each row checks itself: if that position already holds that role, it goes red straight away, and the counter at the top only counts changes that would really go through. OK runs a dress rehearsal first: every row goes through Workday's own checks and nothing changes until you press Apply on the results.

## 11 Results and the Excel template
Here's a validated run on the results page: every row, its outcome, and the reason. For bigger jobs, there's the Excel template. It's published inside the app with a version and an as-of time, it rebuilds itself from Workday on every deploy, and it comes pre-filled with every current assignment, so you only mark what changes. Up to fifty changes per submit in the grid, and a thousand per file.

## 12 Role requests and the ISC queue
What about a brand-new shell role? The requester fills in one form instead of a ticket, and the Functional Unit Hierarchy and Academic Unit pickers can be browsed by type, with an A to Z level for big groups. AAA role requests work the same way, and the role name uses the application's full ID, so a duplicate of an existing Workday role is refused before ISC ever sees it. On the other side, the ISC Queue: oldest first, with how long each request has been waiting, and anything past three business days counts as overdue. Each request is a real Workday business process, so it's in ISC's Workday inbox too, and the requester can never approve their own.

## 13 Quick tour: what else is in the app
A few more things, quickly. My Requests lists everything I've asked for, with its status, and a request that's still in review can be withdrawn. Insights turns activity into numbers: ISC turnaround, what's pending and overdue, approvals and changes, and bulk runs, then Applications at a Glance, one row per application. Access Review lists shell roles still held by positions whose holder has left, so each one can be kept or removed.

## 14 The Audit Log
And how do we know a change really happened? The Audit Log. Every change is here: who, what, when, and the result, newest first. Each record links to the Workday event behind it and to the orchestration run that made the change, so any line can be traced back to Workday itself.

## 15 The value it adds
So what does this add? Here's the value stream map. On top, today: the requester uses the Appian form, which only knows Clockwork, or raises an ISC ticket. Then it waits in the ISC queue, ISC reads it and asks for missing details, there's rework, ISC keys the change by hand, and the requester is told later. Underneath, with ECO-COMS: the application administrator fills in the form, grid or Excel file in Workday, every check happens as they type, an orchestration makes the change in Workday in seconds, and they get a receipt and an audit record. ISC is only involved where it should be: approving a brand-new assignable role, in their Workday inbox. The waits, the rework and the hand-keying disappear, and downstream, AccessUBC and the applications carry on exactly as before.

## 16 Fun fact: the navigation map
And a fun fact to finish. This is the ECO-COMS navigation map. It has thirty-four screens and five ways in from Workday itself: search, the worker profile, Home page cards, the inbox, and a related action on an application record. From the RBAC Hub, every one of those screens is at most four clicks away, and the farthest is Pattern Created, at the end of the one form that serves every application. Thank you.
