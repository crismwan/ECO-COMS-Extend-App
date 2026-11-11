# Workday Extend development

These notes apply to **all** Workday Extend apps I work on. Project-specific details (an app's names, tenant setup, test data, history) live in that repo's own notes file, e.g. `docs/<PROJECT>-NOTES.md`; read it when working in that repo. This repo's is `docs/ECO-COMS-NOTES.md`.

## Contents

- This file is a guide, NOT the single source of truth
- Test data in the tenant
- Ask before guessing Workday syntax
- ID naming convention
- Edit pages
- Security domain enforcement
- Widget types
- date widget
- guide attribute — rendering behavior
- richText — multiple banners in one fieldSet (silent failure)
- Widget validation — `onChange` + `setError` / `clearError`
- grid widget
- AMD task registration
- queryParams — accessing URL query parameters
- instanceList widget
- WQL Query components
- PMD page naming convention
- Flow definitions
- editWizard widget
- hub widget
- Icons (cards, hubs, navigation items)
- Common inbound endpoint patterns
- Submitting data (outbound endpoints)
- Orchestrations
- cardContainer & Page Configuration Cards
- Business objects (Extend model components)
- Workday Script built-in functions
- SMD (Security Model Definition)
- Script include files (`.script`)
- footer / pod widget
- Button `action` values
- Grid display attributes
- chartCard (the .card file side)
- Common inbound endpoint patterns (continued)
- Button navigation — `parameterBindings` vs `parameters` pitfall
- Workday Script — lambda returning object literal (double-brace pattern)
- Workday Script — direct widget state mutation
- Endpoints — `failOnStatusCodes` required
- Endpoints — REST collections default to 20 rows
- Endpoints — `isCollection: true` performance warning
- Grid — do not combine paging with `sortableAndFilterable`
- Grid — `excelExportEnabled` row limit
- WQL — operators and one-value lookups
- WQL — injection risk in string concatenation
- Moving an app between tenants: WIDs and calculated fields
- Orchestrations — debugging and failure handling
- Business processes on Extend business objects
- Security and ISU writes
- Audit logging pattern
- Files: offering a stored file for download
- Data and binding pitfalls
- Renaming an app or an orchestration
- Orchestrations — synchronous page limit is 25 seconds
- Orchestrations — no Excel parsing node
- Platform limits reference
- CI/CD — deploying with GitHub Actions and wdcli
- Deploy decision guide (what to ask the user to run)
- Promotion: what can't change after an app leaves dev
- More wdcli commands, and Arcane Auditor
- Testing an Extend app
- Working in the Workday UI with browser automation
- Patterns from Workday's sample apps (GraphQL, Extend Cards, Profile Groups, more widgets)

## This file is a guide, NOT the single source of truth

CLAUDE.md captures notes and findings from past sessions. It is incomplete and can be wrong or out of date. Do not treat it as authoritative, and do not keep retrying approaches just because this file suggests them.

When there is any confusion about the right solution (syntax, attributes, widget behavior, platform limitations, or a fix that isn't working):

1. **Check the Workday developer site first:** go to https://developer.workday.com/ and use the site's **search bar** to look up the widget, attribute, function, or error. Prefer the official docs over this file when they disagree.
2. **If the developer site doesn't answer it:** stop and ask the user. If I have an idea that goes beyond what CLAUDE.md says, describe it briefly and ask permission to try it before doing so.
3. **After confirming something new**, add it to the relevant section: a general platform lesson goes here, an app-specific detail goes in the project's notes file. Note where it came from (developer.workday.com page, live test, or user).

## Test data in the tenant

Never put the text "claude" (any casing) into anything entered in a Workday tenant: test org codes, pattern values, role names, comments, audit details. Use neutral, clearly marked test values such as `TEST:ORG:1029` or `...:TEST:CI:RUN12`.

## Ask before guessing Workday syntax

When I am unsure about Workday Extend syntax, attribute names, valid enum values, built-in Workday Script function signatures, widget capabilities, or any Workday platform behavior, I STOP and ask a specific, targeted question before proceeding — I do not guess or invent syntax.

- **Why:** Workday Extend is a proprietary, niche platform thinly represented in training data. A confident wrong guess (nonexistent attributes/widgets/functions) wastes time. The user prefers a quick clarifying question over a plausible-but-wrong answer, and has explicitly offered to provide context on request.

- **How to apply:** Treat the existing code in the current repo as the source of truth for conventions and confirm against it first. If the repo doesn't settle it and I'm not certain, ask (e.g. "Does widget X support attribute Y in your Workday release?"). When I do proceed with any residual uncertainty, flag it explicitly rather than asserting.

## ID naming convention

Component IDs are always **camelCase** and **end with the component type**.

- Examples: `newProviderFieldSet` (a Field Set), `providerNameText` (a Text), `submitButton` (a Button), `providersGrid` (a Grid), `enrollmentSection` (a Section).

- Apply this whenever I create or rename an ID, and follow it when suggesting new components.

## Edit pages

- `pageType` is `"EDIT"` (counterpart to `"VIEW"`). **Both values must be uppercase.** Lowercase `"edit"` or `"view"` silently cause page errors. Always use `"EDIT"` or `"VIEW"`.

- **Non-standard underscore attributes** (`_layout`, `_defaultSortColumnId`, `_defaultSortOrder`, `_tooltip`, `_successPage`, `_onSuccess`, `_color`) are silently ignored or cause runtime "1 Error" failures. These are App Builder auto-generated metadata that does NOT translate to valid PMD attributes. Remove any such attribute before deploying.

- Edit pages render framework **OK/Cancel** buttons automatically. Defining a custom `footer` (e.g. a "Powered By" richText) does **not** suppress those buttons — the footer content and the OK/Cancel buttons coexist.

- An editable `grid` can start empty with `"rows": "<% [] %>"`; users add rows via the `+` icon (`doNotAdd`/`doNotRemove` default to false).

- **`standardEditButtonsHidden` pitfall:** Setting `"standardEditButtonsHidden": true` on `presentation` WITHOUT also defining a custom `editButtonBar` leaves the page with **no submit button** — the user has no way to submit the form. Either remove `standardEditButtonsHidden` entirely (the standard OK/Cancel buttons will render) or pair it with an `editButtonBar` that includes an OK-equivalent submit button. Never set it alone.

- **`cancelOverride`:** Overrides where the Cancel button navigates. Shape: `"cancelOverride": { "taskId": "<taskId>" }`. Use this on edit pages to keep users within the app (e.g. return to a list page) instead of falling back to the Workday home page.

## Security domain enforcement

Pages redirect to the hub/landing when the signed-in user lacks the required `securityDomains` entry. This is expected Workday platform behavior — not a page error. If a page immediately redirects away during testing, confirm the test user has the correct security domain assigned before debugging the page itself.

## Widget types

- **Single boolean checkbox:** the widget `type` is `"checkBox"` (camelCase, capital B) — NOT `"checkbox"`. Binds to a boolean value, e.g. `"value": "<% row.isBrandNew ?? false %>"`. Distinct from `checkBoxList` (a multi-select list of options).

- **Single-select dropdown:** the widget `type` is `"dropdown"` (all lowercase) — NOT `"select"` or `"dropDown"` (`select` errors with "invalid tag"). Its choices come from an `instanceList` of `{ "id", "descriptor" }` objects. The selected value is an instance, so `myDropdown.value` returns the instance — use `.value.id` / `.value.descriptor` to get the string.

  ```json

  { "type": "dropdown", "id": "paymentMethodDropdown", "label": "Payment Option",

    "instanceList": [ { "id": "PAYROLL", "descriptor": "Payroll Deduction" } ] }

  ```

- **Text / number fields:** `"type": "text"` and `"type": "number"` are valid field widgets (with `id` + `value`). On VIEW pages they render read-only; on EDIT pages they're editable.

- **Button navigation:** a `button` navigates via a `taskReference` (app task) or `workdayTaskReference` (standard Workday task) attribute — mutually exclusive, one is REQUIRED. NOT a bare `taskId`. Shape: `{ "type": "button", "id": "backButton", "label": "Back", "taskReference": { "taskId": "Home" } }`.

- **Image / worker photo:** the widget `type` is `"image"`. Set `"userPhoto": true` to render a worker photo (no `value`/`url` needed) — useful as the avatar in a worker profile header. Sits as an ordinary sibling of `text` widgets inside a `fieldSet`.

  ```json

  { "type": "image", "id": "workerImage", "userPhoto": true }

  ```

## date widget

`"type": "date"` renders a calendar picker. On VIEW pages it's a non-editable text field; on EDIT pages the month/day/year fields are editable. The value's data type is **Date** (date + time + time zone). **To empty a date, set it to `null`, never `''`** — `myDate.setValue(null)`.

**Display attributes** (all optional):

- `dateFormat` — how to PARSE the *inbound* string. Default `yyyy-MM-dd HH:mm:ss.SSS`. **Model component REST APIs return `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'`, so a date coming from an EBO endpoint usually needs this set explicitly.** If `dateFormat` doesn't match the inbound string, the widget renders **empty** (silent failure — check this first when a date won't display).

- `dateDisplayPattern` — display format on VIEW pages. Default `MM/dd/yyyy` (or `MM/dd/yyyy hh:mm:ss AM/PM` when `datePrecision` includes time). **EDIT pages IGNORE this** and use the signed-in user's preferred display language.

- `datePrecision` — `YEAR` | `MONTH` | `DAY` (default) | `HOUR` | `MINUTE` | `SECOND` | `MILLISECOND`. Time only displays if set to HOUR or finer.

- `inputTimeZone` — time zone of the inbound string. Default UTC.

- `displayTimeZone` — time zone used to display. Default UTC. Use `"<% userTimeZone %>"` (predefined app variable) for the signed-in user's zone.

**Submitting a date:** format it in `valuesOut` with `format(dateFormat)` (UTC) or `formatWithTimeZone(dateFormat, timeZone)`. Inside a grid cell this works the same way:

```json

{ "type": "column", "columnId": "dateColumn", "label": "Date",

  "cellTemplate": {

    "type": "date", "id": "expenseDateDate",

    "value": "<% rowdata.date ?? pageVariables.defaultDate %>",

    "valuesOut": [ { "value": "<% self.value.format('yyyy-MM-dd') %>", "valueOutBinding": "postExpense.date" } ]

  } }

```

Note the escaping when a literal is embedded in the pattern: `'yyyy-MM-dd\\'T\\'HH:mm:ss.SSS\\'Z\\''`.

Other attributes: `enabled`, `guide`, `helpText`, `id`, `label` (max 255 chars), `render`, `required`, `sortOrder`, `value`, `valueOutBinding`, `valuesOut`, `visible`.

**`visible: false` DROPS the widget's `valueOutBinding`/`valuesOut` from the outbound payload** (true for widgets generally). To submit a hidden value, add it back in `onSend`.

## guide attribute — rendering behavior

Source: developer.workday.com "guide" (PMD Tags > Basic UI), checked 2026-10-31, and a live check the same day.

The `guide` attribute adds a "?" beside a widget on an **edit page**. It's a sibling attribute on the widget:

```json
"guide": {
  "type": "guide",
  "id": "myFieldGuide",
  "title": "Tooltip Title",
  "text": "Tooltip body text explaining the field.",
  "linkText": "Optional link text",
  "linkUrl": "https://example.com/more"
}
```

- **Guides are hidden by default.** The page banner shows a "?" button ("Start guided tours"); the user clicks it and the "?" appears beside every widget with a guide. That's why guides look like a silent failure: they render only after that click. (The tenant setting Edit Tenant Setup - System > Always Show Guided Tours shows them all the time.) An earlier note here said guides on `text`/`date` never render; that was wrong: confirmed live, text and date guides appear once guided tours are on.
- **Supported widgets:** `checkBox`, `date`, `dropdown`, `number`, `readOnlyText`, `richText`, `text`, `textArea`, `time`. **Not `instanceList`** (deploys, but no "?" ever appears), and not widgets inside a grid.
- Attributes: `id`, `title`, `text`, `linkText`, `linkUrl`, `render`.
- For help that must always be visible, or on an `instanceList`, put the text in the section's description `richText` instead.

**`richText` value format — two equivalent forms:**
- **Script-wrapped:** `"value": "<% '<span style=\"...\">text</span>' %>"` — required when the string contains dynamic expressions or variable interpolation.
- **Direct HTML:** `"value": "<span style=\"...\">text</span>"` — valid for purely static content with no PMD expressions. Both forms deploy and render correctly.

```json
{
  "type": "richText",
  "id": "sectionDesc",
  "value": "<% '<span style=\"color:#374151;font-size:13px\">ⓘ Explanation of this section and its fields.</span>' %>"
}
```

## Page banner and richText styling (live test 2026-11-02)

- **The Workday page banner can't be styled.** The `title` tag has only `id`, `label`, `render`; `presentation.headerSize` is `STANDARD` or `HIDDEN` (developer.workday.com "title", "presentation"). On a VIEW page with a `basicFormLayout` body, `headerSize: HIDDEN` did **not** remove the banner (the `pageHeader` element still rendered).
- **`richText` keeps only `color` and `font-size` from inline styles.** `background`, `border-radius`, `padding` and `display` are stripped (seen in the rendered ProseMirror HTML), so a coloured, rounded banner can't be drawn with richText. Rounded shapes come only from cards (`cardContainer`) and section boxes, which are white.
- **What works (live 2026-11-02):** remove the page's `title` tag (plus `headerSize: HIDDEN`): the blue banner disappears, and a first `layoutSection` holding a `richText` title (`color` + `font-size` + `<b>`) draws as a white rounded tile with blue text. Trade-off: the browser tab then reads "Workday - Workday" instead of the page title.

## richText — multiple banners in one fieldSet (silent failure)

**Confirmed failure pattern:** Placing two or more `richText` widgets as siblings inside the **same `fieldSet`** causes all but the first to be silently dropped — they do not appear in the DOM, no error is thrown, and the deploy succeeds.

**Fix:** Give each `richText` banner its own dedicated `layoutSection` + `fieldSet`. Each `fieldSet` can have a descriptive `title` (e.g. `"About this page"`, `"Navigation Guide"`).

```json
{
  "type": "layoutSection",
  "id": "warningSection",
  "children": [
    {
      "type": "fieldSet",
      "id": "wizardWarningFieldSet",
      "title": "Navigation Guide",
      "children": [
        {
          "type": "richText",
          "id": "wizardCloseWarning",
          "enabled": false,
          "value": "<% '<span style=\"color:#B45309;font-size:11px;font-weight:700\">⚠ Important: </span><span style=\"color:#374151;font-size:11px\">Warning text here.</span>' %>"
        }
      ]
    }
  ]
}
```

**Example colour conventions** (one app's palette; follow the repo's own):
- `color:#B45309` — amber/warning tone
- `color:#0055B7` — blue/informational tone
- `color:#374151` — body text (dark grey)

**Do NOT** place two `richText` nodes in the same `fieldSet` expecting both to render — only the first will appear.

**Conditional visibility with `visible`:** For conditionally shown error/info messages, use `text` widgets (not `richText`) with the `visible` attribute. **Put such a text in a box that always shows** (e.g. the About fieldSet): a `layoutSection` whose only content is hidden still draws its box, an empty gap on the page (confirmed live 2026-11-01). The static check `Static.hiddenSection` warns about it. `richText` + `visible` inside a `fieldSet` may cause page-level errors. The safe confirmed pattern is `text` widgets with `visible` inside a single `fieldSet`:

## Widget validation — `onChange` + `setError` / `clearError`

This is the mechanism for conditional/cross-field validation, including **inside a grid `cellTemplate`**. `onChange` fires when the user changes the widget's value; `self` is the widget. Call `setError(msg)` to push a message into the page error window (blocking), `clearError()` to remove it. Always clear on the passing branch — an error set once persists until cleared.

```json

{ "type": "date", "id": "sendByDate", "label": "Send By",

  "value": "<% row.sendBy %>",

  "onChange": "<% empty self.value || empty deadlineDate.value

                    ? self.clearError()

                    : (date:after(self.value, deadlineDate.value)

                         ? self.setError('Send By can\\'t be later than the deadline.')

                         : self.clearError()) %>" }

```

Compare a Date against another **widget's** value, not a raw inbound string — the widget has already parsed the string into a Date object.

**Cross-field checks go stale.** When a field's error depends on other fields (a name built from several boxes, "pick one of these two", a duplicate check), an `onChange` that sets the error only on `self` leaves it behind on the field that set it after another field changes (seen live 2026-11-04: an "already exists" error stayed under Course after Subject changed). In every such `onChange`, recheck **all** the fields involved and set or clear each one's error; when one field makes another's error moot (picking an existing item instead of typing a new name), clear the other's error; when a field resets others with `setValue`, clear their errors too.

**An error on a widget the user can't edit never goes away** (live 2026-11-04). Workday refuses OK while any error shows, and doesn't run `onSubmit` until then, so clearing at the start of `onSubmit` doesn't help when OK put the error on a disabled text or a message line (e.g. 'Field 2: the example doesn't match'). Clear it from the `onChange` of every box it's about (grid cells and `onRowAdd`/`onRowRemove` too). Static check `stuckError` enforces it.

**Testing an `onSubmit` check live:** Workday's own `required` checks run first and stop OK before `onSubmit` runs, so a scripted check is only reached with every required field filled, and if it then fails to stop OK the page really submits. Reach it safely by also tripping a check that can't pass (e.g. a duplicate-name check with a name you know exists), or leave it to static checks (live 2026-11-05).

**The same applies to `onSubmit`.** An error it sets stays after the user fixes the cause, and OK keeps failing until a reload (confirmed live 2026-10-31). Clear every widget's error at the start of `onSubmit`, and give confirmation checkboxes `"onChange": "<% self.clearError() %>"`. Enforce it with a build pass that adds the missing `clearError()` calls for every widget an `onSubmit` flags, plus a static check (one app had 6 pages without them, 2026-11-04).

**Scripting methods available on widgets:** `clearError()`, `clearWarning()`, `setError(String)`, `setWarning(String)` (non-blocking), `getLabel()` / `setLabel(String)`, `getValue()` / `setValue(Object)`, `getValueOutBinding()` / `setValueOutBinding(String)`, `isEnabled()` / `setEnabled(boolean)`, `isRequired()` / `setRequired(boolean)`, `isVisible()` / `setVisible(boolean)`, `isUpdated()` (changed by the end user), `isUpdatedByScript()` (changed by a PMD script).

`setVisible()` only works reliably when the widget is inside a `fieldSet`.

### Widget scripting — confirmed platform limitations (editWizard context)

**`setValue()` on `text` widgets is silently ignored** — calling `someText.setValue(...)` from an `onChange` handler produces no visible update. This is a confirmed platform limitation, not a coding error. **That's the editWizard step only:** on a plain EDIT page, a dropdown's `onChange` calling `someText.setValue(...)` updated the text boxes (live 2026-11-04, a "Copy from" picker).

**`setLabel()` on `text` widgets does NOT update reactively** in `editWizard` step context — confirmed via live UI testing (2026-10-29). Even with real keyboard input triggering `onChange`, `setLabel()` calls execute without error but the label in the DOM never changes. The platform appears to render the label once at page load and ignore subsequent `setLabel()` calls on `text` widgets.

**What DOES work in onChange handlers:**
- `setError(String)` / `clearError()` — confirmed working for validation feedback
- `setWarning(String)` / `clearWarning()` — confirmed working
- `setEnabled(boolean)` — confirmed working (enable/disable a widget)
- `setVisible(boolean)` — confirmed working (show/hide, must be inside a `fieldSet`)

**For live preview / computed display fields:** Do NOT attempt reactive updates via `setLabel()` or `setValue()` on `text` widgets. Instead:
- Use the `value` expression (evaluated at page load and on the wizard's Summary review step) for correct display in the summary
- Use `setError()` to surface validation info (the only confirmed-working dynamic text display)
- Use `setWarning()` for non-blocking inline preview text below a field (e.g. "Generated name: APP:ORG"). This IS reactive in onChange — confirmed working in editWizard step context (2026-10-29). **Important caveat from Workday docs:** The editWizard section also notes "No warnings support — calling `setWarning()` on a step page causes an error at submission time." If `setWarning()` on a disabled text widget blocks submit, fall back to `setError()` on a separate helper text widget, or use a `richText` banner.
- Use `richText` banners for static explanatory text about the naming format

**editWizard "Discard Changes?" dialog — ROOT CAUSE AND FIX (confirmed by live test 2026-10-29, supersedes earlier notes):**
- Cause: the wizard step page had `"standardEditButtonsHidden": true`. The wizard's Next saves the step via the step's own OK; with OK hidden, Next is treated as navigating away from a dirty page, so Workday shows "Discard Changes?" — and clicking Discard really does drop the entered values (Review step showed empty fields).
- Fix: do NOT set `standardEditButtonsHidden` (or a custom `editButtonBar`) on editWizard step pages. With it removed, Next goes straight to Review & Submit with all values preserved, no dialog. Confirmed on two wizards.
- Step pages may keep `cancelOverride`.

**Live preview fields in editWizard steps (confirmed live 2026-10-29):**
- `readOnlyText` + `setValue()` in `onChange` DOES update reactively in the step (e.g. Generated Organization Name, Pattern Name Preview).
- For a `values`-scripted dropdown or `instanceListLoopTag` dropdown, read the selected label with `<dropdown>.selectedEntries[0].descriptor` (guard with `!empty(<dropdown>.value)`). `.value.descriptor` raised "Property Error found: descriptor" on one page and returned empty on another.
- The Review & Submit summary does NOT show the setValue'd preview, nor a `value` expression re-evaluated with entered data — it shows the page-load value. Other fields (dropdown, text, date) display correctly. Open question.
- Don't use `setWarning()` on step pages (errors at submit per Workday docs).

## grid widget

Grid columns are NOT typed widgets placed directly in `columns`. Putting `"type": "text"`/`"number"` as the column type errors with "invalid tag" — those types are only valid INSIDE a `cellTemplate`.

- The grid declares `rowVariableName` (e.g. `"swagRow"`); cell bindings reference THAT alias, not `row` — e.g. `<% swagRow.name %>`.

- **The row variable is gone at OK** (live 2026-11-04: "Unknown Variable found: rv.posWid" on submit). `valuesOut` / `valueOutBinding` on a cell are evaluated when the body is built, so don't reference the row variable there: give each cell `value: "<% rv.x %>"` and bind `"<% self.value %>"`, carrying non-displayed values in `hidden` tags (inside a `fieldSet` cell).

- Each column is `{ "type": "column", "columnId": "...", "label": "...", "cellTemplate": { <widget> } }`.

- The actual widget (`text`, `number`, `dropdown`, `date`, `checkBox`, etc.) lives inside `cellTemplate` with its own `id` and `value`.

- **`required` goes on the `column`, NOT on the `cellTemplate` widget.** In a grid, mark a column required at the column level: `{ "type": "column", "columnId": "statusColumn", "label": "Status", "required": true, "cellTemplate": { ... } }`. (Outside a grid, `required` sits on the widget itself as usual.)

- Editable grid: start with `"rows": "<% [] %>"`; users add/remove rows via the +/trash icons. Set `isArrayOutBinding: true` to submit all rows as one outbound array.

- **`readOnly` is not a grid property** (App Hub build warning "You defined an invalid property in tag <grid>: readOnly", 2026-11-06). A grid on a VIEW page is read-only already; on an EDIT page use `enabled: false` cells and `doNotAdd`/`doNotRemove: true`.

- Give **every** `cellTemplate` an `id` — `onChange` handlers reference sibling cells in the same row by that id (`otherCell.value = ...`).

- Default every cell with `??` (`<% row.memo ?? pageVariables.defaultMemo %>`) — new rows start null and PMD scripting errors on null operations.

### Per-row vs array submission

- **Default (`isArrayOutBinding` false): the grid sends a SEPARATE outbound request PER ROW.** Bindings have no `[]`: `"valueOutBinding": "postExpense.date"`.

- **`isArrayOutBinding: true`**: all rows go in ONE request; bind with `endpoint.someArray[].field` → body `{ "someArray": [ {...}, {...} ] }`. Use for bulk APIs (e.g. a BO `?bulk=true` PATCH with `data[].id`) or when handing the whole grid to an orchestration.

- The add/update/delete pattern below relies on **per-row** submission (each row evaluates `exclude` against its own id cell).

### Insert + update in one grid (POST/PATCH switched by `exclude`)

Adding needs `doNotAdd: false` (default); `showRowMover: true` optionally lets users insert a row below a specific row. Define both endpoints and use `exclude` against the row's id cell so each row hits exactly one:

```json

{ "name": "postExpense", "url": "/entries", "baseUrlType": "workday-expenses",

  "exclude": "<% !empty entryId.value %>" },

{ "name": "putExpense", "url": "<% '/entries/' + entryId.value %>", "httpMethod": "PUT",

  "baseUrlType": "workday-expenses", "exclude": "<% empty entryId.value %>" }

```

- The **id column**: `cellTemplate.id` must match the id used in `exclude`, value is the row's record id, `valueOutBinding` is `<put/patchEndpoint>.id`, typically `enabled: false` (or a `hidden` tag — see below).

- **Every other column uses `valuesOut` to bind the same value to BOTH endpoints**; `exclude` decides which fires:

```json

"valuesOut": [

  { "value": "<% self.value %>", "valueOutBinding": "postExpense.date" },

  { "value": "<% self.value %>", "valueOutBinding": "putExpense.date" }

]

```

### Deleting rows (`deleteEndPoint`)

Needs `doNotRemove: false` (default). Define a DELETE outbound endpoint whose URL uses the row's id cell, then point the grid at it by name — the framework calls it for rows the user removed:

```json

{ "name": "deleteExpense", "url": "<% '/entries/' + entryId.value %>", "httpMethod": "DELETE",

  "baseUrlType": "workday-expenses", "authType": "sso" }

```

```json

{ "type": "grid", "id": "expenseGrid", "deleteEndPoint": "deleteExpense", ... }

```

**The per-row POST/PATCH/`deleteEndPoint` pattern breaks when a parent record's multi-instance list must stay in sync.** The page never sees the ids a POST creates, so it can't add them to the parent. In that case, submit the grid as an array to an orchestration (see **Orchestrations → Maintaining relationships**).

### Grid events

- `onRowAdd` / `onRowRemove` on the grid; `onChange` on a cell.

- A new row is at the TOP (when `showRowMover` is false): `var newRow = expenseGrid.rows[0]; newRow.childrenMap.dateColumn.value = ...` (`childrenMap` is keyed by **columnId**).

- `grid.getSubtotal('columnId')` (or `grid:getSubtotal`) sums a numeric column. A widget's own `value` can't call a script function that references that same widget (not constructed yet) — inline the expression instead.

### Hidden values in a column

Wrap the cell in a `fieldSet` and add a `hidden` tag (any column; order doesn't matter). Useful for record ids / a hidden index when data has no unique id:

```json

"cellTemplate": { "type": "fieldSet", "children": [

  { "type": "readOnlyText", "value": "<% row.company.descriptor %>" },

  { "type": "hidden", "id": "rowId", "value": "<% row.id %>" } ] }

```

Read it via the fieldSet's own childrenMap: `sampleGrid.selectedRows[0].childrenMap.companyColumn.childrenMap.rowId.value`. A `section` wrapper with a `hidden` child also works for carrying ids into `valueOutBinding` (seen in practice).

```json

{

  "type": "grid",

  "id": "swagCatalogGrid",

  "label": "Available Swag",

  "rows": "<% [] %>",

  "rowVariableName": "swagRow",

  "columns": [

    {

      "type": "column",

      "columnId": "itemNameColumn",

      "label": "Item",

      "cellTemplate": { "type": "text", "id": "itemNameText", "value": "<% swagRow.name ?? '' %>" }

    },

    {

      "type": "column",

      "columnId": "priceColumn",

      "label": "Price",

      "cellTemplate": { "type": "number", "id": "priceNumber", "value": "<% swagRow.price %>" }

    }

  ]

}

```

## AMD task registration

Pages are registered in a `tasks` array in the **AMD**. Each entry: `{ "id": "<TaskId>", "routingPattern": "/...", "page": { "id": "<PageId>" } }`. The task `id` is what `taskId` references (hub `initialTask`/`navigationTasks`, flow `flowSteps`, button `taskReference`). The Home/landing task typically uses `"routingPattern": "/"`.

## queryParams — accessing URL query parameters

URL query parameters (e.g. `?errorCode=404&view=list`) are accessed in PMD scripts via **`queryParams.<paramName>`** — NOT as bare variable names.

**Critical rule:** Bare variable references like `errorCode` or `view` do NOT resolve to query parameters and cause a **"1 Error" runtime failure** with an infinite spinner. Always use the `queryParams.` prefix.

```json
{ "type": "text", "id": "errorSummary404", "visible": "<% queryParams.errorCode == '404' %>" }
```

**Confirmed patterns:**

- `queryParams.errorCode` ✅ — accesses `?errorCode=404`
- `queryParams.roleId` ✅ — accesses `?roleId=abc123`
- `queryParams.view` ✅ — accesses `?view=list`
- `errorCode` ❌ — bare variable, causes "1 Error" at runtime

**`empty()` guard:** `empty(queryParams.errorCode)` safely returns true when the param is absent. Use it for default/fallback visibility conditions.

**Task registration note:** A task registered in the AMD with NO `parameters` block still receives query params — they arrive via `queryParams`, not via the `parameters` map. The AMD `parameters` block is for params passed programmatically from hub/flow navigation; URL query params always go through `queryParams`.

## instanceList widget

An `instanceList` presents Workday instances (`{ id, descriptor }`) for display or selection.

### Populating the list — the three attributes are MUTUALLY EXCLUSIVE

- **`values`** (most common) — endpoint data, a list whose items have root-level `id` and `descriptor`. Override those field names with `idKey` / `displayKey`. To reshape nested data, use scripting: `"values": "<% workers.data.map(w => { { 'id': w.person.id, 'descriptor': w.person.email } }) %>"`.

- **`instanceList`** — a hard-coded array of `{ id, descriptor }`.

- **`instanceListLoopTag`** — an `instanceLoop` with a `templateInstance`, `on`, and `as`. **Workday recommends scripting with `values` instead**; prefer that.

### Selecting: getting and setting

- `multiSelect` (default false) — allow multiple selections.

- **`value`** returns an **array of IDs**. Use `value[0]` for the single/first selection.

- **`selectedEntries`** returns maps — `selectedEntries[0].descriptor` gets the display text.

- `selectedValues` — default selections by ID; **must be a subset of `values`/`instanceList`**.

- `selectedValuesAndDescriptors` — default selections as full `{ id, descriptor }` objects; **does NOT need to be a subset**. Use this when the saved value may not be in the loaded list (e.g. a persisted worker in a grid row).

- **`selectedValues` and `selectedValuesAndDescriptors` can ONLY be set at page load — never from an event handler.** From script, call `setValue()` instead.

- **`setValue([idList])` vs `setValues([idAndDescriptorList])`** — `setValue` sets the *selection* (IDs only); `setValues` replaces the *available options* (id + descriptor). Easy to mix up.

### Searching: `onSearch` vs `searchEndPoint`

**In a grid or panelList, use `onSearch`.** `searchEndPoint` has **global page context** and doesn't know which row or panel fired it; `onSearch` does.

- **`onSearch`** — triggers when the user types in the prompt. `event.query` (read-only) holds the search string. **The handler's return value becomes the list.** It sees sibling widgets in the same row/panel.

  ```json

  { "type": "instanceList", "id": "ownerInstanceList", "multiSelect": false,

    "values": "<% row.owner ?? [] %>",

    "onSearch": "<% empty event.query ? [] : (searchWorkers.invoke({ 'q': event.query }).data ?? []) %>" }

  ```

  with a **deferred** endpoint whose URL/parameters reference the invoke key bare (`<% q %>`).

- **`searchEndPoint` + `searchResultValues`** (both required, non-grid contexts) — a **deferred** endpoint using the `instanceListQuery` variable for the typed text, guarded with `"exclude": "<% empty instanceListQuery %>"`. On the widget: `"searchEndPoint": "<% endpoints.workerSearch %>"`, `"searchResultValues": "<% workerSearch.data %>"`. Only ONE endpoint allowed. Users can pick from both search results and preloaded values.

- `searchValues` — local search data for multilevel lists (with `monikerLevels`), avoiding an endpoint. If both `searchValues` and `searchEndPoint` are set, **`searchEndPoint` wins**.

**Always initialize `values` at page load** (even to `<% [] %>`) when a list is populated by an event.

### Cascading lists via `onChange`

`onChange` fires on selection. Populate a dependent list by invoking a **deferred** endpoint and calling `setValues()` on the target, which must itself be initialized (`"values": "<% [] %>"`):

```json

"onChange": "<% if (!empty(self.value)) {

     orgMembersList.setValues(orgMembers.invoke({ 'id': self.value[0] }).data);

     orgMembersList.setValue(orgMembers.invoke({ 'id': self.value[0] }).data.map(i => { i.id }));

   } else { orgMembersList.setValues([]); } %>"

```

### Prompt values from Workday ("input prompt values"; developer.workday.com, read 2026-11-05, not yet tried live)

Workday can hand a page the same options its own prompts show, instead of a hand-built WQL list:
- **Graph API `prompts` query** ("Input Prompt Values for Mutations"): `prompts { mutation { <mutation> { <inputField> { <idField>(search: "...") { total data { id descriptor isFinalResult } } } } } }`. Only for ID fields of a Graph **mutation's** input (find them in Graph API Explorer → Documentation Explorer → `Mutation_Prompts.<mutation>`, or by introspection). `search` matches descriptors at every level, word by word like Workday's prompt ("gms ireland" found "Global Modern Services Ltd. (Ireland)"); `promptPath: [<category id>, ...]` walks levels. `isFinalResult: false` means the id is a category with values under it. The `...Reference` fields return WIDs, not reference IDs. If both arguments are given, `search` wins.
- **REST `values` endpoints:** many services have `GET /values/<group>/<field>/` ("Retrieves instances that can be used as values for other endpoint parameters", e.g. staffing `/v6/values/jobChangesGroup/supervisoryOrganization/`, skill `/values/skills/prompt/`). A category's `href` returns its next level.
- **On a page:** a list of `{id, descriptor}` goes straight into `values` / `searchResultValues`. Categories map to a multilevel instanceList ("Concept: Multilevel Lists"): `monikerLevels` (leaves all at one depth; each `monikerLevel` has `levelValues` + a deferred `endPoint` that reads `<list>.promptSelections[n]`), or `dynamicMonikerLevels` (a script on `self.promptSelections` that returns `[levelData, <boolean>]`; in Workday's sample `true` came back for a level with more under it). `searchValues` gives local search across levels.
- **Coverage is narrow (one tenant, 2026-11-05):** `Mutation_Prompts` had only 5 mutations (createReferenceLetterForWorker, referACandidate, startPerformanceReview, submitAccountingJournal, submitSupplier), none for positions, organizations or roles. Introspect `__type(name: "Mutation_Prompts")` before planning around them.
- **Trade-offs:** prompt values return only id + descriptor (no extra columns such as Position ID or filled status), follow the user's own security, and exist only where Workday defines a prompt for that field. WQL stays the tool when you need other fields or your own filter.

### Multilevel lists: confirmed live (2026-11-05, one dev tenant)

- `dynamicMonikerLevels` works together with `multiSelect: true` and `searchEndPoint`/`searchResultValues` on the same instanceList: clicking shows the root `values` as folders, typing runs the search, and selections from both stay selected (the same id ticked in either place).
- The script returns `[list, true]` when the items open to another level and `[list, false]` when they are the selectable leaves. `self.promptSelections` holds the chosen id at each level; `return` and `const` work in it, as in Workday's sample.
- Deferred endpoints called with `.invoke()` from the script work for each level, including an absolute `href` from a REST `values` list as the URL and a plain-GET WQL URL. `.total` on the invoke result lets a level fetch a second page (REST `values` lists return 100 at most).
- Workday's supervisory organization prompt (`staffing/v6/values/jobChangesGroup/supervisoryOrganization/`) returns org WIDs as ids. Its "... by Hierarchy" folders nest "Selectable Values" to any depth, so they need a recursive design.
- **Also works in a grid cell** (an instanceList with `onSearch`): root `values` and `dynamicMonikerLevels` with `self.promptSelections`, the row's `onChange` still fires on a picked leaf (live 2026-11-05).
- **No hierarchy? Group by a type field.** One eager list (`values` = distinct types with counts, `list.distinct().sort()`) and `dynamicMonikerLevels` filtering that same list, plus an A-Z level for big groups (first letter via `(name + ' ').substring(0, 1).upperCase()`). No call when a folder opens. Check first whether the data has parent links (WQL `dataSources/<id>/fields`, then count filled values): in one tenant the custom organizations' `superiorOrganization` and the academic units' `hierarchicParents` were empty for every row.
- Browser automation: the open list renders only a few rows in the DOM. Open a folder by its `find` ref or with the arrow keys plus Right, and read a level from the `w/prompt/context` response (`items[].text`; leaves have no `nextLevelPrompt`). Typing in the box returns to the root level.

### Persisting

`valueOutBinding` binds the selected ID to one outbound field; `valuesOut` binds to several. A map-returning endpoint must be wrapped as a list: `"values": "<% [worker] %>"`.

### Related actions menu (VIEW pages)

Enabling it also enables the instance view link. Which attribute depends on how the list is populated: `widKey` (with `values`), or `wid` on the instance (with `instanceList`) / on `templateInstance` (with `instanceListLoopTag`). Disable pieces with `view: false` (link) and `relatedTask: false` (menu).

## WQL Query components

A **WQL Query component** is a reusable query (Workday Query Language) living in its own `.wqlquery` file, referenced by inbound endpoints. Use one to simplify a complex WQL endpoint, pass query parameters, or share a query across PMDs. In App Builder they're under **Queries > WQL Queries**, and they can currently only be opened in **Code mode**.

**The query string is automatically URL-encoded** when sent to the tenant — do NOT wrap it in `string:urlEncode` (true for both `queryId` components and the inline `wqlQuery` attribute).

**Component attributes:**

- `id` (string, **required**) — must match the `queryId` of the endpoint referencing it.

- `query` (stringScript, **required**) — the WQL. **Max 2048 characters.** Parameters are interpolated with `<% %>`.

- `parameters` (list of strings) — unordered list of parameter names the endpoint may pass in. **A WQL Query component is self-contained and has NO page context** — `pageVariables`, `queryParams`, widget ids, etc. are not visible inside it. Anything page-specific must arrive through `parameters`.

- `limit` (numberScript) — max objects per response, ceiling **10,000**.

- `offset` (numberScript) — zero-based index of the first object. Default 0. Pair with `limit` for paging (limit 5 + offset 9 returns 5 objects starting at the 10th).

```json

{

  "id": "getWorkersHiredAfter",

  "parameters": ["locationId", "hireDate", "offsetParam", "limitParam"],

  "query": "

      SELECT worker, businessTitle, employeeID, hireDate

      FROM workersForHCMReporting(dataSourceFilter=allActiveWorkers)

      WHERE location in (\"<% locationId %>\") and hireDate >= \"<% hireDate %>\"

  ",

  "offset": "\"<% offsetParam %>\"",

  "limit": "\"<% limitParam %>\""

}

```

**Endpoint `wqlQuery` attribute** (on a PMD inbound endpoint hitting WQL `GET /data` or `POST /data`):

- `query` — an inline WQL string. **Mutually exclusive with `queryId`.** Page script variables ARE visible here (unlike in a component). Embed literal strings with escaped double quotes.

- `queryId` — static string, the `id` of a WQL Query component.

- `parameters` — map used WITH `queryId`. Key = parameter name matching the component's `parameters`; value = a script or any literal (boolean, string, number, JSON map/array).

- `limit` / `offset` — used with the inline `query` form.

```json

"endPoints": [

  {

    "baseUrlType": "workday-wql",

    "name": "getWorkersHiredAfter",

    "url": "data",

    "wqlQuery": {

      "queryId": "getWorkersHiredAfter",

      "parameters": {

        "locationId": "<% pageVariables.locationId %>",

        "hireDate": "<% pageVariables.hireDate %>",

        "offsetParam": "<% pagingVariables.offset ?? 0 %>",

        "limitParam": "<% pagingVariables.limit ?? 50 %>"

      }

    }

  }

]

```

`offsetParam`/`limitParam` pair naturally with a grid's `pagingInfo` attribute via `pagingVariables`.

The AMD needs a matching data provider, e.g. `{ "key": "workday-wql", "value": "https://api.workday.com/wql/v1/" }` (with `"url": "data"` on the endpoint). Some apps instead fold `/data` into the provider value and omit `url` — follow whichever the repo already does.

Note: Developer Copilot can generate WQL queries, but **not** WQL query components with parameters.

## PMD page naming convention

All PMD pages are named using **PascalCase** (e.g. `Dashboard`, `StartOETracker`, `PastOEs`). This applies to the page `id` and its task ID.

- This is distinct from component IDs *inside* a page, which are camelCase (see above).

- Apply this whenever I create or rename a PMD page, and follow it when suggesting new pages/tasks.

## Flow definitions

A **flow** is a sequence of edit pages that gives users a guided experience for a multistep transaction. A **flow step** represents each page (or task) in the flow. Use a flow to:

- Override the default navigation of an OK button on an edit page.

- Define conditional logic with page transitions.

- Define multiple navigation patterns using the same set of edit pages.

**Where defined:** Flows live in the `flowDefinitions` array in the **AMD** (not the PMD). Each flow references PMD/task pages by their `taskId`.

**Minimum steps:** A flow definition must have **at least 2 `flowSteps`** — a starting step and an ending step. A single-step flow fails validation ("Each flowDefinition must have at least 2 flowSteps"). For a one-edit-page interaction that should return to a landing page, make the edit page the `startsFlow` step and transition to an ending step whose `taskId` is the landing/view page (e.g. a Dashboard/hub or a conclude page).

**Navigation behavior:** By default, the OK button on an edit page navigates back to the previous page after submitting outbound endpoints. To redirect OK to a flow, reference the edit page's `taskId` in the flow's initial (starts-flow) step. When the flow reaches its last step, the user returns to the page they were on before the flow started.

**Flow step keys:**

- `id` — the flow step ID.

- `taskId` — the task ID of the edit/view page this step renders.

- `startsFlow: true` — marks the initial step.

- `endsFlow: true` — marks the final step.

- `transitions` — ordered list of possible next steps. Each transition has `order` (e.g. `"a"`, `"b"` — evaluated in order), `value` (the target step `id`), and `condition` (a Workday Script boolean expression). **The first `true` condition in `transitions` executes first.**

**View pages in a flow:** A view page (e.g. `orderConclude`) does NOT automatically show OK/Cancel buttons. Once the flow no longer controls navigation, add a button to navigate onward (e.g. to an Order History page).

**Example `flowDefinitions` (AMD):**

```json

"flowDefinitions": [

  {

    "id": "orderSubmitConcludeFlow",

    "flowSteps": [

      {

        "id": "orderStartStep",

        "taskId": "orderStart",

        "startsFlow": true,

        "transitions": [

          { "order": "a", "value": "orderSubmitStep", "condition": "<% flowVariables.isValid == true %>" },

          { "order": "b", "value": "orderStartStep",  "condition": "<% flowVariables.isValid == false %>" }

        ]

      },

      {

        "id": "orderSubmitStep",

        "taskId": "orderSubmit",

        "transitions": [

          { "order": "a", "value": "orderConcludeStep", "condition": "<% flowVariables.isConfirmed == true %>" },

          { "order": "b", "value": "orderStartStep",     "condition": "<% flowVariables.isConfirmed == false %>" }

        ]

      },

      {

        "id": "orderConcludeStep",

        "taskId": "orderConclude",

        "endsFlow": true

      }

    ]

  }

]

```

### flowVariables — passing values across pages in a flow

To send variable data into a flow, use an `outboundVariable` endpoint with `"variableScope": "flow"` in the **PMD**. To read it in a flow step's `condition`, reference the `flowVariables` app variable.

**Set a flow variable (PMD `outboundData`):**

```json

"outboundData": {

  "outboundEndPoints": [

    {

      "type": "outboundVariable",

      "variableScope": "flow",

      "name": "transitionOutboundVars",

      "values": [

        { "outboundPath": "isValid", "value": "<% !empty workerid.value %>" },

        { "outboundPath": "id",      "value": "<% workerid.value %>" }

      ]

    }

  ]

}

```

**Reference it in a flow step transition (AMD):** `"condition": "<% flowVariables.isValid == true %>"`.

## editWizard widget

An `editWizard` guides users through a series of independent edit-page tasks in a single wizard container. It lives on a **view page** and is the **only tag** in that page's `presentation.body`.

### Key constraints (confirmed from Workday developer docs)

- **View page only.** The container PMD must be `pageType: "VIEW"` (or no pageType = view). Each step (`editTask`) must be an edit page.
- **No flows within editWizard.** You cannot use AMD flow definitions inside an editWizard.
- **No cancel destination attribute.** The editWizard has **no `cancelTask`, `cancelOverride`, or equivalent attribute**. When the user clicks the X / Cancel button, the wizard navigates to the **last viewed page** — this is a Workday platform limitation and cannot be overridden at the wizard level.
  - The individual step edit pages CAN have `cancelOverride`, but that only controls the step-level Cancel button within the wizard, not the wizard container's close/X.
  - **Workaround:** Ensure users arrive at the wizard from a meaningful "back" location (e.g. a landing page), so the platform default "last viewed page" navigation sends them somewhere sensible.
- **Data is not submitted until OK.** All outbound endpoints on all edit pages submit when the user reaches the last page and clicks OK. Navigating away without clicking OK discards all entered data (it's cached on the server but not committed).
- **No data passing between steps.** A step cannot use data created by a previous step — all steps submit simultaneously on final OK.
- **No warnings support.** Calling `setWarning()` on a step page causes an error at submission time.
- **Performance:** Limit to 2–3 grids across all pages. Too many widgets/endpoints slow performance significantly.
- **Don't use an editWizard page as a hub navigation task.** Can be used as an `additionalLinks` entry in a hub.

### Attributes reference

| Attribute | Type | Required | Description |
|---|---|---|---|
| `type` | string | ✓ | `"editWizard"` |
| `title` | stringScript | | Title at top of left nav pane |
| `subtitle` | stringScript | | Subtitle under title in left nav pane |
| `editTasks` | array | ✓ | List of tasks (max 10 active at runtime). Each: `{ "label": stringScript, "render": booleanScript, "task": { "taskId": string, "parameters": map } }` |
| `summarySettings` | object | | `{ "enabled": booleanScript, "label": stringScript }`. Adds a summary review page. Default `enabled: true`. |
| `conclusion` | object | | `{ "task": { "taskId": string, "parameters": map }, "render": booleanScript }`. After OK, redirect to this view page. Without it, navigates to last viewed page. |
| `enableSaving` | boolean | | `true` enables Save for Later button + autosave. Requires `section` as top-level container on each step. Stores drafts 30 days. Default `false`. |
| `id` | binding-String | | Unique identifier for this widget |

### Summary / conclusion distinction

- `summarySettings.enabled: true` — adds a "Review & Submit" panel inside the wizard showing all fields read-only before the user clicks OK.
- `conclusion.task` — after the user clicks OK and data submits, the wizard redirects to this separate view page (e.g. a success/confirmation page).

### Minimal example

```json
{
  "type": "editWizard",
  "title": "Create Organization",
  "subtitle": "My App: Organization Manager",
  "summarySettings": { "enabled": true, "label": "Review & Submit" },
  "editTasks": [
    { "label": "Organization Details", "task": { "taskId": "newOrg" } },
    { "label": "Confirm & Submit", "task": { "taskId": "newOrgConfirm" } }
  ],
  "conclusion": { "task": { "taskId": "newOrgSuccess" }, "render": true }
}
```

## hub widget

A **hub** is a container widget: a left navigation pane plus task pages rendered on the right. Use it to create a centralized area with nav links to contextual tasks and related info.

**Rules & constraints:**

- **View pages ONLY.** The nav task pages must also be view pages — the hub does NOT support edit pages.

- The `hub` tag is the **only** tag in the presentation `body` of the view page.

- All task pages must be defined in the AMD.

- `queryParams` variables used in task pages must match the `parameters` sent from the hub.

- A task page can be used in only **1** hub — you cannot reuse the same `taskId` across multiple `hub`/`listDetailHub` widgets in multiple PMDs.

- `navigationTasks[]` max **20** items. `items[]` in a `group` max **5** (group items get **no** icons). `additionalLinks` max **20**.

- NOT supported embedded within a profile group or dashboard. Mobile: Android + iOS.

**Main attributes:**

- `label` (stringScript) — hub title at the top of the left nav pane.

- `icon` (string) — icon next to the title; use `wd-accent-*` (Hub Title Icons). Default is a task clipboard.

- `initialTask` (object, **required**) — default landing page shown on the right pane on load: `{ taskId, parameters }`. Does NOT appear as a nav link unless also added to `navigationTasks[]`.

- `navigationTasks[]` (**required**) — list of `item` and/or `group` objects:

  - `item`: `{ "type": "item", "label" (req), "task": { "taskId" (req), "parameters" }, "icon" (wd-icon-*), "render" (booleanScript, default true) }`.

  - `group`: `{ "type": "group", "label" (req, has expand/collapse arrow), "icon" (wd-icon-*), "render", "items": [ up to 5 items ] }`.

- `additionalLinks` (optional) — section at the bottom (separated by a line): `{ "title", "links": [...] }`. Each link is either:

  - `{ "type": "external", "label" (req), "url" (req) }` — opens an external URL outside the hub.

  - `{ "type": "task", "label" (req), "task": { "taskId", "parameters" } }` — opens a task page **outside** the hub.

`parameters` is `Map<String, StringScript>` (values support PMD scripting); the task page reads them via `queryParams`.

**Minimal shape (PMD `body`):**

```json

{

  "type": "hub",

  "label": "<% currentWorker.descriptor + ' Hub' %>",

  "icon": "wd-accent-award-medal",

  "initialTask": {

    "taskId": "hubTaskOne",

    "parameters": { "pageTitle": "Job Title", "field1": "<% currentWorker.primaryJob.businessTitle %>" }

  },

  "navigationTasks": [

    {

      "type": "item",

      "label": "Job Title",

      "task": { "taskId": "hubTaskOne", "parameters": { "pageTitle": "Job Title" } }

    },

    {

      "type": "group",

      "label": "Worker Details",

      "icon": "wd-icon-folder-close",

      "items": [

        {

          "type": "item",

          "label": "Skills",

          "task": { "taskId": "hubTaskTwo", "parameters": { "workerId": "<% currentWorker.id %>" } }

        }

      ]

    }

  ],

  "additionalLinks": {

    "title": "Suggested Links",

    "links": [

      { "type": "external", "label": "<% 'Workday' %>", "url": "<% 'https://www.workday.com' %>" }

    ]

  }

}

```

## Icons (cards, hubs, navigation items)

Source: developer.workday.com "Reference: Icons" (checked 2026-11-02). Only these names exist. **An unknown name doesn't fail the build**: Workday shows a default icon or none, so a typo or invented name (e.g. `wd-accent-home`, which doesn't exist) goes unnoticed.

**Where each set goes:**
- **`wd-accent-*`:** card headers (`.card`, `.carddefinition`), `hub` and `listDetailHub` titles.
- **`wd-icon-*`:** hub `navigationTasks[]` items and groups, and the `listDetailHub` `navigationTemplate`, **only**. A `wd-accent-*` icon there is wrong.

**`wd-accent-*` (by Workday's own category):**
- Awards: `award-medal`, `trophy`
- Calendar: `calendar`
- Charts and Data: `chart-bar-arrow`, `data-loading`, `data-refresh`, `gauge`
- Chat: `megaphone`, `speech-bubbles`
- Commerce: `credit-card`, `financial-paper`, `globe-coin`, `shopping-cart`
- Eco and Energy: `electric-plug`, `globe-earth`, `globe`, `leaves`, `lightbulb`, `sustainability`
- Education: `education-finance`, `laptop-education`, `skills`, `student`, `student-admissions`, `student-search`
- Fun and Food: `coffee`, `flag-wave`, `fun`, `rocket`, `target`
- Health: `heart`, `shield-benefits`, `tooth`
- Legal and Protection: `legal`, `scroll-shield`, `shield`
- Media, Papers, and Presentation: `checkmarked-page`, `clipboard-checklist`, `media-file`, `news`, `resources`, `student-records`
- Office and Buildings: `building`, `id-badge`, `suitcase`
- People and Hands: `employees`, `handshake`, `open-positions`, `people-group`, `person`, `person-search`, `touchpoints`
- Science, Technology, and Tools: `candidate-pipeline`, `circuit-board`, `credentials`, `dna`, `inbox`, `privacy`, `radio-tower`, `sigma`, `tablet-lock-check`, `time`, `toolbox`, `tools`, `touch-id`, `worksheets`
- Shapes: `community`, `location`, `universal`

**`wd-icon-*` (navigation):** `calendar`, `checkboxes`, `clock`, `contact-card-matrix-manager`, `document`, `folder-close`, `globe`, `location`, `mail`, `search-user`, `star`, `task-academic`, `timeline-milestone`, `time-off-balance`, `user`.

**Choosing an icon (framework):**
1. **Name the subject, not the layout.** Ask "what is this card about?" (role requests, organizations, audit), not "it's a list of actions". Generic icons such as `clipboard-checklist` or `checkmarked-page` on every card tell the user nothing.
2. **One icon per subject, used everywhere.** Every card about the same thing (the home action card, the list page's actions card, its filter pills, the Workday Home card) gets the same icon, so the icon becomes a signpost between pages. Two subjects never share an icon.
3. **Pick by meaning, in this order:** a literal match (calendar for a date filter, building for organizations, inbox for a review queue), then the action (sigma for counts, gauge for status, chart-bar-arrow for insights or trends, data-refresh for "start again"), then the outcome (award-medal for success receipts).
4. **Suggested mappings** for common admin-app subjects:

| Subject | `wd-accent-*` | Navigation `wd-icon-*` |
|---|---|---|
| App / hub title for access or role management | `credentials` | n/a |
| Roles, role requests, access | `id-badge` | `contact-card-matrix-manager` |
| Work waiting for review, approvals, "needs my attention" | `inbox` | `checkboxes` |
| Organizations, hierarchies | `building` | `folder-close` |
| Many people or positions at once (bulk changes) | `people-group` | `search-user` |
| One person or worker | `person` | `user` |
| Audit, compliance, history | `scroll-shield` | `timeline-milestone` |
| Insights, trends, reports | `chart-bar-arrow` | `document` |
| A count or total | `sigma` | n/a |
| Activity over time across the whole app | `time` | `clock` |
| Status filter or progress | `gauge` | n/a |
| Date or period filter | `calendar` | `calendar` |
| Templates, files, uploads | `worksheets` | `document` |
| Help, links to other pages | `resources` | `globe` |
| Success / receipt | `award-medal` | n/a |
| Error recovery ("start again") | `data-refresh` | n/a |
| Security, privacy, permissions | `privacy` or `shield` | n/a |
| Settings, configuration | `tools` | `star` (no settings icon exists) |
| Announcements, notifications | `megaphone` | `mail` |

5. **Keep the choices in one table in the repo** (a small pass that runs last in the build and sets every icon from a card-id → icon map), not scattered across builders, and add a static check that fails on any icon outside the lists above and on a non-`wd-icon-*` navigation icon.
6. **Images:** a custom image can replace a card-header `icon` only (developer.workday.com "Images"), and an app may hold at most 20 images. Prefer the built-in icons.

## Common inbound endpoint patterns

### Workday job positions (staffing)

Fetch all job positions for filtering/display in grids. Uses `workday-staffing-v6` base URL:

```json
{
  "name": "positions",
  "baseUrlType": "workday-staffing-v6",
  "url": "jobs",
  "authType": "sso",
  "isCollection": true,
  "bestEffort": "true"
}
```

Then filter in the grid `rows` binding: `"<% positions.data.filter(p => { myIdList.contains(p.id) }) %>"`.

The AMD data provider key is `workday-staffing-v6` pointing to the Workday Staffing v6 API base URL.

### Measuring page speed (2026-11-04)

- Time the server, not the browser: `GET /wday/app/<appId>/<tenant>/<appId>/<taskId>` with `Accept: application/json`, 7 loads, take the median (first loads after a quiet spell are 2-5x slower). Time each data call on its own from CI (an e2e `timing` suite with the developer token) to see which one costs what.
- Data calls run in parallel, except an endpoint that references another, which waits for it. A slow page is usually one big list (a 600-row WQL is ~500 ms) or page script over hundreds of rows, not the number of calls.
- **Graph isn't automatically faster.** The same 43-row read took 246-2043 ms through Graph against a steady ~300 ms for count + 3 REST pages. Measure before switching.
- An inbound endpoint takes `exclude`, so a page of a paged list can be skipped when the first page's total says it would be empty.
- A TEXT date field (e.g. an ISO timestamp stored as text) gets `String_Filter` in Graph: no `gt`/`gte`, so no server-side date range.
- Before deleting a fallback lookup list, backfill the records that needed it; then the page reads stored values only.

### Deferred endpoints — null guard required (`?? []`)

An inbound endpoint marked `"deferred": true` does **not** fetch until its data is first needed (e.g. when a tab using it is opened). However, Workday evaluates **all PMD script expressions at page load time** — including `rows`, `visible`, and `filter` expressions on every tab, not just the active one. This means a deferred endpoint's `.data` property is accessed before the fetch has occurred, causing:

```
Property Error found: data. Script Excerpt: myEndpoint.data
```

**Fix:** Always guard deferred endpoint data with `?? []` in any PMD expression:

```json
"rows": "<% applications.data ?? [] %>"
```

**Pattern to apply everywhere deferred endpoints are used:**

- `"rows": "<% deferredEndpoint.data ?? [] %>"` — grids
- `"visible": "<% (deferredEndpoint.data ?? []).size() > 0 %>"` — conditional visibility
- `"values": "<% deferredEndpoint.data ?? [] %>"` — instanceList / dropdown

**Non-deferred (eager) endpoints do NOT need this guard** — their data is fetched before the page renders, so `.data` is always a list.

**Confirmed failure:** a deferred endpoint was referenced as bare `applications.data` in a grid's rows expression. Even though the grid was on a second tab (not the default one), Workday still evaluated the expression at page load — throwing the Property Error and crashing the entire page with a red "!" error indicator.

### Deferred endpoints — WQL tab grids NEVER fetch (confirmed 2026-10-29)

**Critical additional pitfall:** Even with the `?? []` null guard in place, a `deferred: true` WQL endpoint used in a grid `rows` binding will **never auto-fetch its data**, even when the user clicks the tab. The guard prevents the page crash, but the grid silently shows 0 rows forever.

**Why:** Workday evaluates `rows` at page load (returning `[]` via the `?? []` guard), then considers the expression "resolved." It never re-evaluates it when the tab becomes visible, and because no widget explicitly calls `.invoke()` on the endpoint, the deferred fetch is never triggered. Network inspection shows zero WQL requests for the endpoint.

**Symptoms:**
- Grid shows "No items available." with 0 items
- No network call to the WQL endpoint appears in browser dev tools — not on page load, not after clicking the tab
- No page error (the `?? []` guard prevents the crash, masking the problem)

**Fix:** Remove `"deferred": true` from any WQL endpoint whose data is needed in a tab grid's `rows` binding. Make it eager so it fetches on page load:

```json
// BROKEN — grid always shows 0 items even when data exists:
{ "name": "orgPatterns", "baseUrlType": "workday-wql", "url": "data", "deferred": true, ... }

// FIXED — fetches eagerly on page load, grid populates correctly:
{ "name": "orgPatterns", "baseUrlType": "workday-wql", "url": "data", ... }
```

**Rule:** Only use `deferred: true` when the endpoint is explicitly invoked via `.invoke()` in a script or `onSearch` handler. Never use it for data that a grid `rows` binding reads passively.

## Submitting data (outbound endpoints)

Outbound endpoints are REST APIs that add/update/delete data. When the user clicks **OK** on an edit page, Presentation Components build the JSON request body from widget values and submit it. Defined in the PMD's `outboundData.outboundEndPoints[]`.

**Required fields per endpoint:**

- `url` — relative REST API URL. Default HTTP method is **POST**; override with `httpMethod` (PATCH/PUT/DELETE/etc.).

- `baseUrlType` — a `dataProvider` key defined in the AMD.

- `name` — reference name used to bind field values to this endpoint.

- `authType` — the `authType` id from `authTypes[]` in the SMD. Workday REST APIs use `sso` (default).

**Two tag types in `outboundEndPoints[]`** (edit pages only; URL protocol must be HTTP/HTTPS):

- `outboundDataURI` — the **default** tag (no `type` needed). A REST outbound endpoint invoked on submit.

- `outboundVariable` — requires `"type": "outboundVariable"`. Persists variables sent to other pages (e.g. `"variableScope": "flow"` with `values[]` of `{ outboundPath, value }`). See the Flow definitions section for `flowVariables`.

```json

"outboundData": {

  "outboundEndPoints": [

    { "name": "submitRequisition", "url": "/requisitions", "authType": "sso", "baseUrlType": "workday-procurement" },

    {

      "type": "outboundVariable",

      "name": "outboundFlowVariableExample",

      "variableScope": "flow",

      "values": [ { "outboundPath": "someFlowVariable", "value": "<% someWidget.value %>" } ]

    }

  ]

}

```

**Key behaviors & constraints:**

- **Only the OK button** (or an `editButtonBar` submit button) can call outbound endpoints. A PMD script's `invoke` method CANNOT — but `invoke` can call a deferred inbound endpoint (e.g. an Orchestration for extra processing).

- Endpoints are invoked **in the order listed** in `outboundEndPoints[]`.

- `exclude` — a boolean binding; if true, the endpoint is skipped (conditional invocation).

- **No rollback:** if an endpoint fails, updates from preceding outbound requests are NOT rolled back.

- **Timeouts:** 24s per endpoint; 60s per request (initial loads + submissions + remote validations combined). Limit endpoint count and use performant endpoints.

- Use the `onSend` event to construct/manipulate the request body; `onMultiPartSend` for multipart.

- `responseErrorDetail` (on `outboundData`) maps endpoint errors into a page error message: `{ "errorSummary": "<% error %>", "errors": "<% errors.map(item => { item.error }); %>" }`.

**Binding widget values → request body:**

- `valueOutBinding` on a tag — format `outboundEndpointName.fieldPath`. The combined `valueOutBinding` data forms the JSON body. List notation: `outboundEndpointName.listName[].fieldPath` (or `[0]` to target a specific item).

- `valuesOut[]` on a tag — bind one widget to **multiple** fields/endpoints, or split a multi-part value (currency, date). Each item: `{ "value": "<% ... %>", "valueOutBinding": "..." }`.

- `values[]` on the **endpoint** — specify all outbound data on the endpoint itself instead of per-tag. Each item: `{ "outboundPath": "fieldPath", "value": "<% ... %>" }`. Useful for submitting data sourced from *another* endpoint.

- Grid → array: set the grid's `isArrayOutBinding` to true to submit all rows as one outbound array.

- Hidden tags carry values the user doesn't edit (e.g. ids from an inbound endpoint) into the request body.

**Example — conditional update vs delete on the same resource:**

```json

"outboundData": {

  "outboundEndPoints": [

    {

      "name": "updatePayInput",

      "baseUrlType": "workday-payroll",

      "url": "<% 'payrollInputs/' + queryParams.donationId %>",

      "httpMethod": "PATCH",

      "authType": "sso",

      "exclude": "<% !payInput.usedInCompletedResult %>"

    },

    {

      "name": "deletePayInput",

      "baseUrlType": "workday-payroll",

      "url": "<% 'payrollInputs/' + queryParams.donationId %>",

      "httpMethod": "DELETE",

      "authType": "sso",

      "exclude": "<% payInput.usedInCompletedResult %>"

    }

  ],

  "responseErrorDetail": {

    "errorSummary": "<% error %>",

    "errors": "<% errors.map(item => { item.error }); %>"

  }

}

```

**Example — `values[]` on the endpoint (also pulling from other endpoints):**

```json

{

  "name": "charity",

  "baseUrlType": "app",

  "url": "charities",

  "httpMethod": "POST",

  "authType": "sso",

  "values": [

    { "outboundPath": "name", "value": "<% name.value %>" },

    { "outboundPath": "minDonationAmount.value", "value": "<% minAmount.value %>" },

    { "outboundPath": "createdBy.id", "value": "<% worker.id %>" },

    { "outboundPath": "image.id", "value": "<% (!empty(charityImage.id)) ? charityImage.id : null %>" }

  ]

}

```

**Multipart data:** `valueOutBinding` format is `<outboundEndpointName>:<formDataName>:<jsonFieldName>` (nested field paths allowed). Manipulate parts in `onMultiPartSend` via `self.data` (add a `<key, map|array>` part, set `self.data.<part>.<field>`, or reconstruct to remove parts; form-data name can't be `metadata`).

**Multipart with attachments (`fileUploader` `valueOutBinding` format):**

- Workday REST API attachment-only → `outboundEndpointName`.

- Workday multipart (attachment + JSON) → `outboundEndpointName:filePartName`.

- Model attachment object REST API → `outboundEndpointName:defaultCollectionName`.

- Third-party multipart → `outboundEndpointName:filePartName`.

**Submitting unchanged data:** Extend skips PUT endpoints when nothing changed. Set the endpoint's `allowPutForUnchangedData: true` to force submission (important when building the body in `onSend`/`onMultiPartSend`).

**Customizing the edit page buttons:**

- Edit pages auto-render **OK** (submits + navigates) and **Cancel** (no submit, navigates back; flow variables persist).

- `standardEditButtonsHidden` (on `presentation`) — booleanScript to hide OK/Cancel conditionally.

- `editButtonBar` — override OK and add more **submit** buttons (e.g. `dropdownEditButton` with an `instanceList`); cannot customize Cancel. Define navigation via AMD flow definitions. Persist a dropdown selection as a flow variable using the dropDown's id.

- `cancelOverride` (on `presentation`) — override Cancel navigation; supports `parameters`/`parameterBindings`. E.g. `"cancelOverride": { "taskId": "home" }`.

## Orchestrations

An **orchestration** is a server-side flow (`orchestration/<name>.orchestration`) used when a submit needs logic a PMD can't do. The main case: **chaining REST calls where a later call needs an id returned by an earlier one.** PMD outbound endpoints can't read each other's responses, so "create child records, then link them to a parent" must be an orchestration.

Everything below was learned from App Builder–authored orchestrations in a real app (flowVersion `3.1.0`–`3.4.0`). Anything marked **(unverified)** is an inference that hasn't been confirmed on a tenant yet.

### File format

- The whole file is one typed tree. Every value is wrapped as `{ "_type": <type>, "_value": <value> }`. Examples: `{"_type":"Identifier","_value":"myNode"}`, `{"_type":"Boolean","_value":false}`, and optionals as `{"_type":["Opt","ErrorHandler"],"_value":null}`.

- Top level: `{ "flowVersion", "_type": "Flow", "_value": { id (32-hex string), name (Identifier), type: ".maya.FlowSync", start, end, nodes, notes, resources, defaultWorkdayCredentialRef, ... } }`.

- Expressions are `{"_type":["Expr","String"],"_value":{"type":{"_type":"Type","_value":"String"},"source":{"_type":"String","_value":"<expression>"},"isAuto":{"_type":"Boolean","_value":false}}}`. The type can be `String`, `Boolean`, `Number` or `Data`. Json is written as the pair `["Json",{"_type":["Opt","JsonSchemaRef"],"_value":null}]`, and iterators as `["Iterator",[...]]`.

- **Don't hand-type these files.** They run to thousands of lines. Write a small Node script that **clones real nodes from an existing orchestration in the repo as prototypes** and swaps in names, expressions, templates and paths. That keeps every wrapper exactly as App Builder writes it. Registration isn't needed: dropping the file in `orchestration/` is enough.

- Notes: `notes._value` is a list of `{"_type":"Note","_value":{"key":{"_type":"String","_value":"description"},"value":{...}}}`. Use one on the flow and on each branch to document intent.

### Calling one from a PMD

- AMD data provider: `{ "key": "ORCHESTRATION", "value": "<% `https://api.workday.com/orchestrate/v1/apps/{{site.applicationId}}/orchestrations` %>" }`.

- Outbound endpoint: `{ "name": "...", "baseUrlType": "ORCHESTRATION", "url": "/<orchestrationName>/launch", "authType": "isuAuth", "onSend": "<% ... return request; %>" }`. It's a POST, so only OK / edit-button submits can call it.

- Build the whole request body in `onSend` from `self.data` (the grid array when `isArrayOutBinding: true`) plus widget values. **Shape the records in the PMD** so the orchestration can pass them straight through.

- The PMD's **24-second per-endpoint timeout covers the entire orchestration run**, so keep per-row calls modest. Nothing rolls back on failure.

- Orchestrations can also be *inbound* (e.g. wrapping a SOAP call and returning `data.x.response.asXML().convertToJson()`). The page reads the result by endpoint name, like any other endpoint.

### Start, request parsing, and end

- `start` is `StartBasic` with `structuredRequest` = `ObjectRequestStructure` (empty `props`). The raw body is `data.start.request`.

- First node, by convention: a `CreateValues` named `request` that pulls typed fields out of the body:

  - `data.start.request.asJSON().stringAtJsonPath("$.field")`

  - `...stringAtJsonPathWithDefault("$.field", "default")`

  - `...booleanAtJsonPath("$.flag")`

  - `...numberAtJsonPath("$.n")`

  - `...arrayAtJsonPath("$.list")` (Json)

- **Reading an uploaded CSV** (confirmed live 2026-10-31): `GET` the attachment object record with no Accept header (response type Any), then `data.<get>.response.asCSV().rows()` as the Loop input, typed explicitly as `["Iterator",["CsvRow",{"_type":["Opt","CsvFormatRef"],"_value":null}]]` (auto-typing fails the build with "columnValueAtIndex cannot be applied to an instance of AnyType"). Read cells with `item.columnValueAtIndex(n)`; `countRows()` counts rows. Quoted cells with commas inside and CRLF line ends (as Excel saves) parse correctly. The header row comes through as a row, so skip it by content.
- **There's no object extractor in use**, only arrays. To pass one record through untouched, send it from the PMD as a one-element list and use the bulk API.

- `end` is `EndSync`. `body` is `null` (no response) or a `DataRefBody` whose source is e.g. `data.someGroup.response`.

### Node types

| Node | Purpose | Key fields |

|---|---|---|

| `CreateValues` | Named typed variables | `values: [Assignment{ param{name,type}, expr }]`. Later assignments may reference earlier ones in the same node (`data.request.x`). |

| `CreateTextTemplate` | Build a string/JSON body | `message` (TextTemplate, `{{ }}` placeholders), `contentType: "application/json"`. Use it as a body via `data.<name>.message.asJSON()`. |

| `SendWorkdayApiRequest` | Call a Workday REST/SOAP API | `method` (HttpMethod), `path` (Expr String), `body` (`DataRefBody` → a data source, **or** inline `CreateTextTemplateBody{message, contentType}`), `auth`, timeouts, `retryConfigRef`. The response is at `data.<name>.response`. |

| `Group` | Named container. Its outputs are visible outside as `data.<groupName>.<value>`. | `nodes` |

| `ImplicitGroup` | Unnamed body of a loop/branch (`_group_<loop>`, `_group_IF_<branch>`, `_else_<branch>`) | `nodes` |

| `Loop` | Iterate a Json list | `inputData` iterator, `filter` (opt), `aggregateNode` → `Aggregate{ failOnEmptyStream:false, foldValues:[JsonFoldValue{nameProp, data, condition}] }`, `group` (ImplicitGroup) |

| `BranchOnConditions` | if/else | `ifBranches: [WhenBranch{ name:"IF", condition, group }]`, `elseBranch` (ImplicitGroup, may be empty), `exceptionIfNoBranchMatched:false`, `enableOutputs:true` |

| `Log` | Debug log | `message` (Expr String), `condition`. Also usable inside an `errorHandler` (`strategy: "PropagateError"`). |

### Referencing data

- Same group/scope: `data.<nodeName>.<valueName>` (e.g. `data.assignRates.zeroToSixtyRate`).

- From outside a `Group`: `data.<groupName>.<valueName>`. The group re-exports the values of its inner nodes and the folds of its inner loops (e.g. `data.createLaborLevels.createdLaborLevelWIDs`).

- Current loop item: `data.<loopName>.item` (use `.asJSON()` or `.stringAtJsonPath("$.body.id")` on it).

- A loop's fold result: `data.<loopName>.<foldName>`. It renders as a JSON array when templated, e.g. `{"data": {{data.iterateRows.rowFragments}}}`.

- Values produced inside a branch: reference the inner node directly (`data.<innerNode>.<value>`) **(unverified)**.

### Expression language

- Conditional: `if (cond) a else b`, e.g. `(if ((x > 2)) true else false)`. Lazy evaluation of the untaken side is assumed, not confirmed **(unverified)**.

- Empty-array test: `data.request.list.asJSON().contentLength() > 2`. That's the length of the JSON text, and `[]` is 2 characters.

- String equality: `.equals("...")`. Number comparison: `==`. `0.0d` is a double literal.

- Path interpolation: `s"""${"/apps/".append(context.appReferenceId())}${"/v1/myCollection/"}${data.request.wid}"""`.

- Iterators: `data.request.list.iterator("$[*]")`, `data.x.response.asJSON().iterator("$.data[*]")`.

- JSON filter: `numberAtJsonPath("$[?(@.bucketID == \"zeroToSixty\")].rate")`.

- Append to an id array: `existingArray.asJSON().addStringValue("id", newWID)`, which adds `{"id": newWID}`.

- Other functions seen: `.toString()`, `context.tenant()`, `date.now` / `datetime.now` (in templates), `wrapSoapV11()`, `asXML().convertToJson()`.

### Templates

- Placeholders are `{{expr}}`. A Json-typed value renders as raw JSON: `{{data.request.list}}` → `[...]`, `{{data.loop.item}}` → `{...}`.

- Handlebars `{{#if data.request.flag}} ... {{/if}}` works inside a template.

- **Don't template user-entered free text into a JSON string** (`"notes": "{{...}}"`). Quotes or HTML would break the JSON. Pass user records through as Json values, and only template ids and other safe values.

- Guard empty folds. When a loop had no items, branch to a literal body (e.g. `"list": []`) rather than templating an empty fold.

### Calling app business-object APIs

- Path: `/apps/<appReferenceId>/v1/<collectionName>`, with `/<wid>` for one record.

- Auth: `WorkdayCredentialRef` `_DEFAULT_WORKDAY_CREDENTIAL` with `retryConfigRef` `_DEFAULT_WORKDAY_RETRY_CONFIG`. Declaring an ISU credential under `resources.credentials` is only needed for things like SOAP calls.

- Header `allowEmptyValue: "true"` is used on BO POSTs.

- **Single create:** `POST /collection` with the record body. The new id is `response.asJSON().stringAtJsonPath("$.id")`.

- **Bulk create:** `POST /collection?bulk=true` with `{"data": [ {...}, ... ]}`. Loop `response.asJSON().iterator("$.data[*]")`; each id is at `item.stringAtJsonPath("$.body.id")`. A one-element list gives `$.data[0].body.id`.

- **Bulk update:** `PATCH /collection?bulk=true` with `{"data": [ {"id": "...", <fields>} ]}`. The same format works for a single row.

- **Bulk delete:** `DELETE /collection?bulk=true` with `{"data": [ {"id": "..."} ]}`.

- **GET:** `GET /collection/<wid>` returns the record, with multi-instance fields as `[{id, descriptor}]`.

### Maintaining relationships

- A `MULTI_INSTANCE` field is **replaced**, never appended, on PATCH. Send the complete list: `{"children": [{"id":"a"},{"id":"b"}]}`.

- To add one child to a list, GET the parent, use `arrayAtJsonPath("$.children")` + `addStringValue("id", newWID)`, then PATCH.

- **Unlink before delete.** First PATCH the parent's list to leave out the removed children (or `"child": {"id": ""}` for a single instance), then DELETE them.

- For **two-way links** (child `SINGLE_INSTANCE` → parent, parent `MULTI_INSTANCE` → children), write both sides on every save:

  - **Create:** POST the parent → POST the children (bulk) → PATCH the children's back-reference (bulk) → PATCH the parent's list with the new ids.

  - **Edit grid:** loop the rows (new → POST with the back-reference already set, existing → PATCH), fold every resulting id, PATCH the parent's list to exactly that fold, then bulk-DELETE the rows the PMD reports as removed.

  - Work out "removed rows" in the PMD `onSend`: the ids loaded in `onLoad` minus the ids still on the grid.

## cardContainer & Page Configuration Cards

A **Page Configuration Card** is defined in its own **`.card` file** — NOT inline in the PMD. Its `id` **must match the card file name**. In App Builder they live under **Page Configurations > Cards** in the Components panel.

A Page Configuration Card's `body.type` is one of: **`chartCard`**, **`imageCard`**, **`listCard`**, **`pillCard`**, **`simpleCard`**.

Do NOT confuse these with **Extend Cards** (a different thing — admins add those to Workday entry points like the Home page, delivered Hubs, Search, and Journey; they live in the `Cards` section of the Components panel).

### cardContainer (the PMD side)

`cardContainer` is the container for a group of cards on a page. Multiple cards create a dashboard-like experience.

- **`card` tags are ONLY legal inside a `cardContainer`.** You cannot place a `card` directly in a page body.

- Every `card` must reference a Page Configuration Card via `cardId`, and may pass `parameters` for dynamic content (this is what lets one card template be reused across pages with different contexts).

- Valid on **view AND edit** pages. Mobile: Android + iOS.

- Static cards **always render above** dynamic cards when both are present.

**Attributes:**

- `layout` (string) — `grid` (**default**, rows of equal height) or `masonry` (columns; content determines card height).

- `cards` (card array) — static collection; array order = display order. Each entry: `{ "type": "card", "cardId" (req), "parameters" (mapScript), "render" (binding-Boolean) }`.

- `dynamicCards` (object) — renders a card per item in a list:

  - `on` (listScript, **req**) — script/endpoint returning the data list.

  - `as` (string, **req**) — item variable name (alphanumeric + underscore only).

  - `template` (object, **req**) — `{ "cardId" (stringScript, req — may be static OR dynamic), "parameters" (mapScript) }`.

- `id` (binding-String) — must start with a letter, unique per page. To be referenceable by other widgets, define it BEFORE them (otherwise "Undefined variable" on validation). Recommended for debugging.

- `render` (binding-Boolean, default true) — unlike `visible`, when false other tags **cannot reference** this tag on edit pages.

`parameters` is a **mapScript** and supports only: `boolean`, `date`, `list`, `map`, `number`, `set`, `string`.

```json

{

  "type": "cardContainer",

  "id": "statusCardContainer",

  "layout": "grid",

  "cards": [

    {

      "type": "card",

      "cardId": "simpleStatusCard",

      "parameters": "<% { 'title': 'Good news!', 'icon': 'wd-accent-fun', 'indicatorLabel': 'Success', 'indicatorColor': 'green', 'body': 'Your request was submitted.' } %>"

    }

  ],

  "dynamicCards": {

    "on": "<% helpCases.data %>",

    "as": "item",

    "template": {

      "cardId": "caseCard",

      "parameters": "<% { 'title': item.title, 'subtitle': item.caseID, 'body': item.detailedMessage, 'id': item.id } %>"

    }

  }

}

```

### `.card` file — unused parameters cause build failure

**Workday enforces that every parameter declared in a card's `parameters` array MUST be referenced somewhere in the card body.** Declaring a parameter and never using it causes a fatal `ERROR` during the "Upload app to App Hub" CI step:

```
Remove unused parameters in the card. Unused parameters: <parameterName>.
```

This is an `ERROR` (not a `WARN`) and **blocks deployment**. The fix is to remove the unused parameter name from the `parameters` array. Note: passing extra params from the PMD's `parameters` map that are NOT declared in the card's `parameters` array is silently ignored and is fine — only declared-but-unused card parameters are an error.

**Example fix:**
```json
// BROKEN — 'organizationCode' declared but never referenced in body:
"parameters": ["organizationName", "organizationCode"]

// FIXED — only declare params you actually use in the card:
"parameters": ["organizationName"]
```

### simpleCard (the .card file side)

File `simpleStatusCard.card` → `"id": "simpleStatusCard"`. Set `body.type` to `"simpleCard"`.

**Attributes:**

- `id` (string, **req**) — must match the card file name.

- `parameters` (string array) — parameter names the PMD may pass in. Reference them bare in scripts (`<% title %>`), not via a prefix. Use `?: null` for optional ones (e.g. `"icon": "<% icon ?: null %>"`).

- `header` (object) — `title` (stringScript, bold, top of card), `subtitle` (stringScript, below title), `icon` (string — must be a **`wd-accent-*`** icon), `indicator` (object: `label` stringScript + `color`).

  - `indicator.color` valid values: **`blue`, `gray`, `green`, `orange`, `red`, `transparent`**.

- `body` (object, **req**) — `type` (**req**, `"simpleCard"`) and `value` (stringScript, **req**) = the body content.

  **CRITICAL — `.card` file script tokenization restriction:** Single-quoted string literals inside `<% %>` expressions in `.card` files cause a fatal `tokenization error in '''` during `wdcli` validation. This includes `simpleCard` `body.value` and any other `.card` attribute using `<% 'literal text' + variable %>` style concatenation. The workaround is to build the concatenated string in the PMD's `parameters` mapScript (where single-quoted literals are valid), pass it as a named parameter, and reference it in the card as `<% myParam ?? '' %>`. Example:

  ```json
  // PMD side — string concatenation with single-quoted literals is fine here:
  "parameters": "<% { 'bodyText': 'Code: ' + (orgCode ?? '') + ' | App: ' + (appCode ?? '') } %>"

  // .card side — just reference the pre-built parameter:
  "body": { "type": "simpleCard", "value": "<% bodyText ?? '' %>" }
  ```

  **CORRECTION:** Single-quoted string literals do NOT work inside `chartCard` `data` arrays either — this was incorrectly noted as confirmed. The tokenization restriction applies to ALL `.card` file `<% %>` expressions regardless of card type. Always use escaped double-quotes (`\"`) for string literals inside `<% %>` in any `.card` file, or pass pre-built values as parameters from the PMD.

- `footer` (TaskButton array) — up to **5** links. Only the **first** shows as a button; the rest go under the card's **More Actions** (⋯) menu (confirmed live 2026-10-31), so put the most used link first. Each: `label` (stringScript, **req**) plus **exactly one** of:

  - `taskReference` — `{ "taskId", "parameterBindings": { ... } }` to navigate to an app task.

  - `workdayTaskReference` — `{ "wid": "..." }` for a Workday-delivered task/report (use its Integration ID).

  - `url` (dynamicBinding-String) — external link.

  - These three are **mutually exclusive**.

```json

{

  "id": "caseCard",

  "parameters": ["title", "subtitle", "icon", "indicator", "body", "id"],

  "header": {

    "title": "<% title %>",

    "subtitle": "<% subtitle %>",

    "icon": "<% icon ?: null %>",

    "indicator": {

      "label": "<% indicator.label ?: null %>",

      "color": "<% indicator.color ?: null %>"

    }

  },

  "body": {

    "type": "simpleCard",

    "value": "<% string:toString(body) %>"

  },

  "footer": [

    {

      "label": "Case Details",

      "taskReference": {

        "taskId": "caseDetails",

        "parameterBindings": { "caseWid": "<% id %>" }

      }

    }

  ]

}

```

### pillCard (the .card file side)

Displays a **group of buttons (pills)** on a card — e.g. a "Suggested Tasks" launcher. Set `body.type` to `"pillCard"`. Mobile: Android + iOS.

**Attributes:**

- `id` (string, **req**) — must match the card file name.

- `parameters` (string array) — parameter names the PMD may pass in (same semantics as `simpleCard`).

- `header` (object) — `title` (stringScript, bold, top of card), `subtitle` (stringScript), `icon` (string — **`wd-accent-*`** only), `indicator` (object: `label` stringScript + `color`).

  - `indicator.color` valid values: **`blue`, `gray`, `green`, `orange`, `red`, `transparent`**.

- `body` (object, **req**):

  - `type` (**req**) — `"pillCard"`.

  - `pills` (TaskButton array, **req**) — the buttons to display, **max 10**. Each pill: `label` (stringScript, **req**) + `taskReference` (**req**) — the page to navigate to. Note: unlike `footer`, a pill's ONLY navigation option is `taskReference` (no `url` / `workdayTaskReference`).

- `footer` (TaskButton array) — up to **5** links. Each: `label` (stringScript, **req**) plus **exactly one** of `taskReference` (`{ "taskId", "parameterBindings" }`), `workdayTaskReference` (`{ "wid": "..." }`), or `url` (dynamicBinding-String) — mutually exclusive.

```json

{

  "id": "pillCardExample",

  "header": { "title": "Suggested Tasks" },

  "body": {

    "type": "pillCard",

    "pills": [

      { "label": "Create charity", "taskReference": { "taskId": "createCharity" } },

      { "label": "Donate",         "taskReference": { "taskId": "donate" } },

      { "label": "View donations", "taskReference": { "taskId": "donations" } }

    ]

  },

  "footer": [

    { "label": "Home", "taskReference": { "taskId": "home" } }

  ]

}

```

Referenced from a PMD like any other card (`cardId` must match the card file name / `id`):

```json

{

  "type": "cardContainer",

  "layout": "grid",

  "cards": [

    { "type": "card", "cardId": "pillCardExample" }

  ]

}

```

Each `taskId` referenced by a pill must exist in the AMD `tasks` array.

**A card can be picked at run time:** a `dynamicCards` template's `cardId` can be a script (`"cardId": "<% item.cardId %>"`, with `parameters: "<% item.params %>"`), so one container can show different card files per item (confirmed live 2026-11-05). Since a pill card's pill list is fixed, generate one card file per pill count (`Pills1`…`Pills10`) and pick `'Pills' + n`; a static orphan check must then count card ids named in scripts as used.

**Pills have no `render`** (developer.workday.com "pillCard": a pill is only `label` + `taskReference`), so a pill can't be hidden on its own. Hide or show a whole card with the `card`'s `render` in the `cardContainer` (used live 2026-11-04 for an Organization filter card that appears only while one is picked). When several pill cards drive one page's query params, give every pill every param, or switching one filter drops the others.

**Pills as filters and action rows (confirmed live 2026-10-31):** a pill's `taskReference` takes `parameterBindings`, so a pill card can drive a page's query-param filters (the Audit Log's `?period=7d` came through). Mark the current choice by scripting the label from card parameters, double-quoted only: `"label": "<% period == \"7d\" ? \"✓ Last 7 days\" : \"Last 7 days\" %>"`. Pills wrap side by side, so they replace a column of stacked buttons. Workday renders buttons in a section one per row; there is no row layout for plain buttons.

**Collapsible boxes (confirmed live):** `fieldSet` with `"collapsible": true, "initializeCollapsed": true` starts closed with an arrow; pair it with a one-line summary that stays visible.

**Card rows:** the number of cards per row follows the page width (three in a ~1440px window, four at 1600px, confirmed live 2026-11-01), so a fixed 'three per row' plan leaves gaps on wider screens. Put related cards in **one** `masonry` container rather than two half-full rows. Card subtitles show two lines (about 40 characters) and are then cut off with "…"; keep them short. A card's `render` hides it conditionally (used on the error page). A `cardContainer` can follow a `fieldSet` in the same `layoutSection`, which keeps help text and its action card in one box.

## Business objects (Extend model components)

Business objects define an app's data model: they extend Workday's single object model, persist app data, and can relate to each other and to Workday-delivered objects. Extend **automatically generates report data sources and REST API endpoints** for each one. Author them in App Builder as a **Business Object** component (Code mode shown below).

- **A business object's `id` can never be changed** once created.

- **Don't end business object names with a numeral.**

- Use model business objects for stand-alone data. To add custom fields to an existing Workday-delivered object, use **custom objects** instead.

### Object-level attributes

- `defaultSecurityDomains` (string array, **required, min 1**) — security domains controlling access. Only names of security domains defined **in the same app**.

- `defaultCollection` — `id`, `name`, `label`, optional `description`:

  - `name` → the **REST API resource name** for all instances. Recommend plural (e.g. `charities`).

  - `label` → the unfiltered **report data source** name. Recommend `All` + plural (e.g. `All Charities`).

  - `description` → the data source's Description in the Business Object Details report.

- `fields` / `derivedFields` — arrays of field definitions (below).

### Field-level attributes (all field types)

- `name` and `label` must be **unique within the business object** (or attachment object).

- `securityDomains` (optional string array) — overrides the object's `defaultSecurityDomains` for this field. Same-app domains only.

- `isPurgeable` (optional boolean) — `true` lets Extend purge data stored in the field.

- `enableIndex` (optional boolean) — index the field; Extend generates **query parameters** for all indexed fields.

  - Max **5** regular indexed fields per business object / attachment.

  - Only fields secured by the object's **default** security domains can be indexed.

  - **Cannot** index derived fields or `MULTI_INSTANCE` fields.

  - `SINGLE_INSTANCE` fields are indexed **automatically** — no need to set it.

### Field types and their extra attributes

- **`TEXT`**

  - `isReferenceId` — marks the field as the object's **Reference ID**. The field becomes required and can't be deleted. **Once per object.** Field name can't contain `\` `"` `/` `+` `;`. Values must be **unique** — adding it to a model with duplicate data **fails deployment**, so set it before loading data. The Reference ID Type (under Integration IDs) is the object name + `_ID` (e.g. `Charity_ID`).

  - `enableSearch` — lets users pick values from a prompt when filtering by instance in a custom report (and in the Comparison Value prompt). **Required for use in a Discovery Board filter.** Max **3** TEXT fields **per app**. **Requires `enableIndex: true`.** Values must be unique (same deployment-failure caveat) — set before loading data.

  - `useForDisplay` — this field's content becomes the object's display value / descriptor. **Once per object.**

- **`RICH_TEXT`** — stores formatted markup (bold, italics, lists). Pair with the `richText` widget on PMD pages. Does **NOT** support `enableIndex`, `enableSearch`, `isReferenceId`, or `useForDisplay`. Only for **new** fields — you can't change an existing field's type in promoted apps (IMPL/SBOX/PROD).

- **`DATE`** — `precision`: `MILLISECOND` | `SECOND` | `MINUTE` | `HOUR` | `DAY` | `MONTH` | `YEAR`.

- **A `BOOLEAN` left unset reads as `false`**, not empty (live 2026-11-04: a record created by hand before an `active` flag was used showed Inactive). Test with `x.active != false` only when the default should be true, and set the flag explicitly on every create.

- **`DECIMAL`** — `decimals`: up to **10** decimal places.

- **`INTEGER`**, **`CURRENCY`**, **`BOOLEAN`** — no extra attributes.

- **`SINGLE_INSTANCE`**

  - `target` — name of another business object **in the same app** or a Workday-delivered object (e.g. `WORKER`, `COST_CENTER`, `COMPANY`).

  - `secureByTarget` — `true` delegates contextual security to the target instance *in addition to* the object's own security. Can be set on **multiple** SINGLE_INSTANCE fields; security is then the aggregation of those contexts (enables BP routing/approval to multiple recipients).

  - `useForDisplay` — allowed (once per object).

- **`MULTI_INSTANCE`**

  - `target` — same as SINGLE_INSTANCE.

  - **Cannot** set `secureByTarget` or `useForDisplay`.

  - **A SINGLE_INSTANCE field can't be converted to MULTI_INSTANCE.**

  - Keep instances per field **below ~1,000** for performance.

**`useForDisplay` on attachment objects:** by default an attachment's descriptor is its `fileName`. Setting `useForDisplay` on an attachment field makes that field the descriptor instead — so don't use the descriptor as the file name in `fileUploader`/`attachmentList`; reference `fileName` explicitly: `"attachmentName": "<% getData.image.fileName %>"`.

**CURRENCY in API requests:** adding/updating a CURRENCY field requires **both** `currency` and `value` in the body:

```json

{ "name": "DogsMatter", "minDonationAmount": { "currency": "USD", "value": "50" } }

```

### Model reports

- A `.report` covers **one** business object: `{ id, name, label, businessObject, defaultSecurityDomains, sortConfigs: [{id, order, field, direction: ASCENDING|DESCENDING}], columns: [{id, name, order, field}] }`; a column with `"isSelfReferencing": true` (no field) shows the instance itself. None of the 36 sample apps joins objects in a report: for a cross-object view build a VIEW page. Limit 10 reports per app.

### Derived fields

Defined in `derivedFields` with an `expression`. Same attributes as standard fields, but **`CURRENCY` and `SINGLE_INSTANCE` types are NOT supported**, and derived fields can't be indexed. Expressions can reference other fields (including through a SINGLE_INSTANCE, e.g. `logo.uploadedDate`) and other derived fields.

### Reserved field names

- **Case-sensitive, all fields:** `attachmentContent`, `contentType`, `descriptor`, `displayID`, `filename`, `fileLength`, `id`, `wid`, `workdayID`.

- **Case-insensitive, all fields:** `select`, `from`, `where`, `limit`, `order`, `having`, `group`, `by`, `asc`, `desc`, `as`, `and`, `or`, `not`, `is`, `null`, `empty`, `in`, `datasourcefilter`, `entrymoment`, `effectivemoment`.

- **Case-sensitive, SINGLE_INSTANCE or `enableIndex: true` fields:** `offset`, `bulk`, `search`, `sort`, `type`, `view`, `name`. (Note: `name` is fine on an ordinary unindexed TEXT field, as in the example below — but not if you index it.)

### Example

```json

{

  "id": 1,

  "name": "Charity",

  "label": "Charity",

  "defaultSecurityDomains": ["ManageCharities"],

  "defaultCollection": { "name": "charities", "label": "All Charities" },

  "fields": [

    { "id": 1, "name": "name", "type": "TEXT", "label": "Name", "useForDisplay": true, "isReferenceId": true },

    { "id": 2, "name": "description", "type": "TEXT", "label": "Description" },

    { "id": 3, "name": "matchDonations", "type": "BOOLEAN", "label": "Match Donations" },

    { "id": 4, "name": "relationshipManager", "type": "SINGLE_INSTANCE", "label": "Relationship Manager", "target": "WORKER" },

    { "id": 5, "name": "logo", "type": "SINGLE_INSTANCE", "label": "Logo", "target": "CharityLogo" },

    { "id": 6, "name": "createdBy", "label": "Created By", "type": "SINGLE_INSTANCE", "target": "WORKER", "secureByTarget": true },

    { "id": 7, "name": "costCenter", "label": "Cost Center", "type": "SINGLE_INSTANCE", "target": "COST_CENTER", "secureByTarget": true },

    { "id": 8, "name": "company", "label": "Company", "type": "SINGLE_INSTANCE", "target": "COMPANY", "secureByTarget": true }

  ],

  "derivedFields": [

    { "id": 1, "name": "logoUploadedBefore2022", "type": "BOOLEAN", "label": "Logo Before 2022",

      "expression": "logo.uploadedDate.toYear().toNumber() < 2022" },

    { "id": 2, "name": "logoLabel", "type": "TEXT", "label": "Logo Label",

      "expression": "logoUploadedBefore2022 ? 'Old Image' : 'New Image'" },

    { "id": 3, "name": "workdayMatched", "type": "BOOLEAN", "label": "Workday Matched Charity",

      "expression": "matchDonations && (description == 'Workday Charity')" }

  ]

}

```

## Workday Script built-in functions

This is the **complete** list of available built-in functions (user-provided, authoritative). If a function is not on this list, it does not exist — do not invent one. Two call styles appear:

- **Namespace/static form** — the target is the first argument: `list:filter(myList, 'type', 'functional')`, `regex:replace(text, regex, replacement)`.

- **Method form** — called on the value itself: `myList.size()`, `myString.trim()`, `myDate.plusDays(5)`.

Signatures below use the doc's own convention: an entry with no leading target argument (e.g. `filter (closure)`) is the method form; one whose first parameter is the collection (e.g. `filter (list, key, value)`) is the namespace form. Many functions offer both.

### IMPORTANT gaps to plan around

- **There is NO built-in `sum`, `average`, `count`, or `round`.** Aggregations must be hand-rolled — use `map` + `reduce` for a sum, then divide by `size()`. Guard against an empty list (`size() == 0`) since dividing by zero and reducing an empty list both fail.

- `number:` has `max`, `min`, `pow`, `sqrt`, `toBigDecimal`, and the two int converters — nothing else arithmetic.

- Closures use the `item => { expression }` form (e.g. `errors.map(item => { item.error })`).

- **This list is not a perfect match for every tenant/release.** `number:convertNumberToInt(...)` is on the list but throws `Unknown Function call` at runtime (observed 2026-08-10). Treat the `number:` namespace as suspect and prefer confirmed-in-use alternatives.

- **NUMBERS HAVE NO `.toString()`.** `toString ( )` exists for `date`, `list`, `map`, `set`, and `string` — the `number` namespace has only `convertNumberToInt`, `convertStringToInt`, `max`, `min`, `pow`, `sqrt`, `toBigDecimal`. Calling `.toString()` on a number throws, and inside a listCard row template that silently renders **zero rows** rather than an obvious error.

- **To stringify a number, concatenate onto an empty string: `'' + myNumber`.** Order matters — `String + Number` concatenates, but `Number + String` throws. So `'' + value + '%'` works while `value + '%'` does not.

- Once stringified this way you can chain string functions, which is how to truncate a decimal without any `number:` call: `('' + (a / b)).substringBefore('.')`.

- **Confirmed working in a real app:** `list:filter(list, key, value)`, `.map(closure)`, `.reduce(closure)`, `.size()`, `.substringBefore(separator)`, `date.toString()`, and `'' + number` for stringifying.

- **Widget `.value` property access on null — use `!empty()` guard, NOT `?? ''`.** Accessing a sub-property like `.id` or `.descriptor` on a widget's `.value` when the value is null throws a null-pointer equivalent BEFORE the `?? ''` fallback can catch it. This is a silent, hard-to-diagnose runtime error.

  **WRONG (crashes if nothing selected):**
  ```json
  "<% selectedApplicationId.value.id ?? '' %>"
  ```

  **CORRECT — guard with `!empty()` first:**
  ```json
  "<% (!empty(selectedApplicationId.value)) ? (selectedApplicationId.value.id ?? '') : '' %>"
  ```

  Apply this pattern everywhere a widget value (especially from a `dropdown` or `instanceList`) has sub-properties accessed on it. The `!empty()` function safely returns `true` when the value is null, avoiding the NPE. After the guard passes, the inner `?? ''` catches any edge cases where the property itself is null.

### bool

`all (expression1, expressionN)` · `any (expression1, expressionN)`

### bpfTaskHelper

`fetchTaskType (businessProcessTask)`

### converter

`booleanAsInt (expression)` · `booleanAsString (expression)`

### date

`add (precision, duration)` · `between (date2, precision)` · `after (date1, date2)` · `checkTodaysDate (timeZone)` · `createMonth (mm, yyyy)` · `createYear (yyyy)` · `extractValue (precision, date)` · `format (dateFormat)` · `formatDateWithTimeZones (date, inputTimeZone, inputDateTimeFormat, outputTimeZone, outputDateTimeFormat)` · `formatWithTimeZone (dateFormat, timeZone)` · `get (precision)` · `getDateTimeZone (timeZone)` · `getTodaysDate (timeZone)` · `getTodaysDateFormatted (timeZone, dateTimeFormat)` · `minusDays (days)` · `minusHours (hours)` · `minusMinutes (minutes)` · `minusMonths (months)` · `minusNanos (nanoseconds)` · `minusSeconds (seconds)` · `minusWeeks (weeks)` · `minusYears (years)` · `month ( )` · `now ( )` · `now (timeZoneString)` · `parse (dateString)` · `parse (dateString, dateFormat)` · `parse (dateString, dateFormat, timeZoneString)` · `parseDateString (dateString)` · `parseFormattedDateString (dateString, dateFormat)` · `plusDays (days)` · `plusHours (hours)` · `plusMinutes (minutes)` · `plusMonths (months)` · `plusNanos (nanoseconds)` · `plusSeconds (seconds)` · `plusWeeks (weeks)` · `plusYears (years)` · `timeAfter (date2)` · `toString ( )` · `withDayOfMonth (dayOfMonth)` · `withDayOfYear (dayOfYear)` · `withHour (hour)` · `withMinute (minute)` · `withMonth (month)` · `withNano (nanosecond)` · `withSecond (second)` · `withYear (year)` · `year ( )`

### file

`byteCountToDisplaySize (size)`

### fileType

`getFileType (fileName)`

### graph

`createId(id)` · `createId(id, idType)` · `createId(ids)` · `createId(ids, idType)` · `createIds(ids)` · `createIds(ids, idType)`

### grid

`getSubtotal (grid, columnId)`

### json

`asJSON (object)` · `attribute (key, value)` · `create (attribute1, attributeN)` · `parse (jsonString)` · `stringify (object)` · `query (source, jsonPath)` · `query (source, jsonPath, resultsAsList)`

### list

`add (element)` · `add (index, element)` · `add (list, object, index)` · `addAll (elements)` · `addAll (index, elements)` · `clear ( )` · `contains (element)` · `containsAll (elements)` · `createMapList (list, key)` · `createMapListWithKeys (list, keyList)` · `distinct ( )` · `emptyList ( )` · `exclude (list, key, value)` · `excludeEmptyAttribute (list, key)` · `excludeMultiple (list, key, comparisonList)` · `excludeRegex (list, regexValue)` · `filter (closure)` · `filter (closure(item, index))` · `filter (list, key, value)` · `filterEmptyAttribute (list, key)` · `filterMultiple (list, key, comparisonList)` · `filterRegex (list, regexValue)` · `find (closure)` · `first ( )` · `firstNonEmpty (param1, paramN)` · `flatten (list)` · `forEach (closure)` · `forEach (closure(item, index))` · `get (index)` · `indexOf (element)` · `indexOf (object, list)` · `isEmpty ( )` · `isList (object)` · `join ( )` · `join (list1, list2)` · `join (separator)` · `last ( )` · `lastIndexOf (element)` · `map (closure)` · `map (closure(item, index))` · `mapAttribute (list, key)` · `mapBeanAttribute (listOfBeans, beanProperty)` · `nonNull (list)` · `reduce (closure)` · `remove (element)` · `removeAll (elements)` · `retainAll (elements)` · `reverse ( )` · `set (index, element)` · `size ( )` · `sort ( )` · `sort (closure)` · `sort (list, key, ascendingOrder)` · `subList (fromIndex, toIndex)` · `toJson ( )` · `toList (value1, valueN)` · `toListIncludeNull (value1, valueN)` · `toMap (list, key)` · `toString ( )`

### map

`add (key, value)` · `addAll (anotherMap)` · `clear ( )` · `containsKey (key)` · `containsValue (value)` · `filter (closure)` · `forEach (closure)` · `get (key)` · `getKeys (map)` · `getObject (map, key)` · `getValues (map)` · `getValuesFromKeys (map, keys)` · `isEmpty ( )` · `keys ( )` · `map (closure)` · `mapKey (closure)` · `mapValue (closure)` · `put (key, value)` · `remove (key)` · `size ( )` · `toJson ( )` · `toString ( )` · `values ( )`

### number

`convertNumberToInt (number)` · `convertStringToInt (string)` · `max (number1, numberN)` · `min (number1, numberN)` · `pow (base, exponent)` · `sqrt (number)` · `toBigDecimal (arithmeticExpression, scale, roundingMode)`

### object

`defaultIfNull (object, default)` · `firstNonNull (object1, objectN)`

### regex

`find (text, regex)` · `match (text, regex)` · `replace (text, regex, replacement)` · `replaceOnce (text, regex, replacement)` · `split (text, regex)`

### set

`add (element)` · `addAll (elements)` · `clear ( )` · `contains (element)` · `containsAll (elements)` · `filter (closure)` · `find (closure)` · `forEach (closure)` · `isEmpty ( )` · `join ( )` · `join (separator)` · `map (closure)` · `reduce (closure)` · `remove (element)` · `size ( )` · `toJson ( )` · `toString ( )`

### string

`abbreviate (maxWidth)` · `capitalize ( )` · `concat (string1, string2)` · `contains (searchString)` · `contains (string, substring)` · `containsIgnoreCase (searchString)` · `defaultIfBlank (defaultString)` · `defaultIfEmpty (defaultString)` · `endsWith (suffix)` · `endsWithIgnoreCase (suffix)` · `formatListToString (separator, list)` · `formatMessage (messageWithParameters, orderedParameters)` · `fuzzyMatchIndex (list, comparisonValue)` · `fuzzyMatchString (list, comparisonValue)` · `fuzzyScore (query)` · `indexOf (searchString)` · `indexOf (substring, startIndex)` · `isAllLowerCase ( )` · `isAllUpperCase ( )` · `isBlank ( )` · `isNumber ( )` · `isNumeric ( )` · `isString (value)` · `join (array, separator)` · `join (string1, stringN)` · `lastIndexOf (searchString)` · `lastIndexOf (subString, fromIndex)` · `leftPad (size)` · `leftPad (size, padCharacter)` · `length ( )` · `lowerCase ( )` · `lowerCase (locale)` · `pathEncode ( )` · `remove (subString)` · `removeEnd (subString)` · `removeEndIgnoreCase (subString)` · `removeStart (subString)` · `removeStartIgnoreCase (subString)` · `replace (searchString, replacement)` · `replaceIgnoreCase (searchString, replacement)` · `replaceOnce (searchString, replacement)` · `replaceOnceIgnoreCase (searchString, replacement)` · `replaceSubstring (string, origSubstring, newSubstring)` · `reverse ( )` · `rightPad (size)` · `rightPad (size, padCharacter)` · `size ( )` · `split (separatorChars)` · `splitByRegex (regex)` · `startsWith (prefix)` · `startsWith (string, substring, startIndex)` · `startsWithIgnoreCase (prefix)` · `stripPrefix (prefix)` · `stripSuffix (suffix)` · `substring (startIndex)` · `substring (startIndex, endIndex)` · `substringAfter (separator)` · `substringAfterLast (separator)` · `substringBefore (separator)` · `substringBeforeLast (separator)` · `toDecimal ( )` · `toDecimal (scale, mode)` · `toInt ( )` · `toString ( )` · `trim ( )` · `trimToEmpty ( )` · `truncate (maxWidth)` · `truncate (offset, maxWidth)` · `uncapitalize ( )` · `upperCase ( )` · `upperCase (locale)` · `urlDecode ( )` · `urlEncode ( )` · `uuid ( )`

### validate

`match (regex, comparisonString)`

### Averaging a list (the hand-rolled pattern)

Since there is no `sum`/`average`, average a numeric attribute like this — note the empty-list guard, which is required:

```

<% myList.size() == 0

     ? '0%'

     : ('' + (myList.map(item => { item.progress ?? 0 })

                    .reduce((runningTotal, value) => { runningTotal + value })

              / myList.size()

             )).substringBefore('.') + '%'

%>

```

The leading `'' +` is what makes the quotient a string — without it, neither `.substringBefore(...)` nor `+ '%'` is legal on a number. `substringBefore('.')` then truncates the decimal, and returns the string unchanged when there's no `.`, so it is safe whether the division yields `53.33` or a clean `100`. Do NOT reach for `number:convertNumberToInt` here; it throws `Unknown Function call`.

When comparing an average against exact boundaries (0 or 100), skip rounding entirely and compare the raw quotient — those cases are exact.

Keep percentages stored as **bare numbers** (`"progress": 85`) and append the `%` only at render time (`value.toString() + '%'`). Storing `"85%"` makes the value a display string and forces a `substringBefore('%')` + `toInt()` round-trip before any arithmetic.
### Workday Script — operator words can't be names (App Hub build 2026-11-07)

`le`, `lt`, `ge`, `gt`, `eq`, `ne`, `and`, `or`, `not`, `div`, `mod` (and `size`, `empty`, `new`) are operator words: `let le = ...` failed the App Hub build with "PMD Scripting syntax error ... Parsing Error" and nothing more specific. Keep a static check on `let`/`var`/parameter names.

### Business-object JSON text: key order isn't kept (live 2026-11-07)

A JSON string saved from a page (`json:stringify` into a TEXT field) comes back with its keys in Workday's own order (a field object read `{"ruleLength":..,"lookup":..,"regex":..}` though written label-first). Don't locate things in it by key order (e.g. "labels before this key"); count object boundaries (`},{`) or parse it. Compact form (no spaces) did hold.

### Grid cell dropdowns and switching cells (live 2026-11-07)

- A `dropdown` in a grid `cellTemplate` opens on each row's saved choice with `"selectedValues": "<% [rowVar.key ?? 'default'] %>"` (developer.workday.com "dropdown": the value is a list of ids, `selectedValues` picks the first); read it in `childrenMap.<columnId>.value[0]`.
- A cell's `enabled` can use the row variable at load, and a sibling cell's `onChange` can flip it with `otherCell.setEnabled(...)` and fill it with `setValue(...)` on an EDIT page.
- A literal backslash in Workday Script without escaping questions: `'%5C'.urlDecode()`.

### Workday Script — define helpers before use; counting without memory blow-ups (live 2026-11-02)

- **A `.script` helper that calls one defined further down the file is dropped**: the page fails with "Unknown Function call: .waitingText(row)" even though the function is exported. Define every helper before its first caller. (Static check `scriptOrder`.)
- **Matching a grid row against a lookup list (live 2026-11-05):** inside a grid cell, `list.filter(a => { a.key == rowVar.x })` and `list:filter(list, 'key', rowVar.x)` both returned nothing (list loaded, 0 matches), while `list.map(a => { a.key }).indexOf(rowVar.x)` then `list.get(i)` worked. Use the index lookup when a cell needs the matching record.
- **Record-level tasks (developer.workday.com "Add Tasks with Business Object Context"; live 2026-11-05):** a model task with `businessObject` and `routePath: "/page/{taskObjectId}"` shows as a related action on every instance of that business object (grouped under the object's name); Workday replaces `{taskObjectId}` with the instance WID. Add an AMD task with `routingPattern: "/page/{taskObjectId}"` pointing at the page, which reads `queryParams.taskObjectId` (Workday's capitalProjectPlanning sample does the same). An instanceList with `values: [{id: <record WID>, ...}]`, `widKey`, `view`/`relatedTask: true` on a VIEW page links an app business-object record and offers that task. **Name the AMD route parameter `{taskObjectId}`, the same as the model task's `routePath`:** App Builder marked the task's Page Route "(invalid)" while the AMD used `{recordId}` (live 2026-11-05). A page opened both ways can read `queryParams.recordId ?? queryParams.taskObjectId`.
- **Grouping counts hit the PMD script memory limit** ("Script Constraint exceeded: ... max memory limit") when a row expression builds a map per record (~1,000 orgs) and filters it per group. Instead build sorted lists of plain strings once and count with `i = list.indexOf(c); i < 0 ? 0 : list.lastIndexOf(c) - i + 1`.
- Day differences without date functions: positions in a list of `date:now().minusDays(n).format('yyyy-MM-dd')` keys (`keys.indexOf(a) - keys.indexOf(b)`).
- `readOnlyText.setValue()` also updates live on a plain EDIT page (not just wizard steps), called from a grid cell's `onChange`; `currentGrid.rows.filter(r => { r.childrenMap.<columnId>.value == true }).size()` reads a checkbox column (Bulk Edit change counter).
- `richText` keeps `<br>`: a title tile can carry a second, smaller line (`<br><span style="color:#374151;font-size:13px">…</span>`).

## SMD (Security Model Definition)

The SMD file (`<appId>.smd`) lives alongside the AMD and defines site-level configuration. Key attributes:

- `id` / `siteId` / `applicationId` — all set to the app's `applicationId`.
- `languages` — array of `{ "code": "en-US", "description": "English" }`.
- `siteAuth.authTypes` — defines auth schemes used by outbound endpoints. The only auth type needed for SSO apps: `{ "scheme": "SSO", "id": "sso" }`.
- `errorPageConfigurations` — maps HTTP status codes to error PMD pages: `{ "statusCode": "404", "page": { "id": "errorPage" } }`. Common codes: 400, 401, 403, 404, 408, 500, 503.
- `cdnEnabled` — boolean, typically `true`.
- `siteProperties` — array, usually empty `[]`.
- `headerBackgroundColor` — hex colour for the app header bar (e.g. `"#0055B3"`).
- `titleAlignment` — `"center"` or `"left"`.

```json
{
  "id": "myapp_id",
  "siteId": "myapp_id",
  "applicationId": "myapp_id",
  "languages": [{ "code": "en-US", "description": "English" }],
  "siteAuth": {
    "authTypes": [{ "scheme": "SSO", "id": "sso" }]
  },
  "errorPageConfigurations": [
    { "statusCode": "400", "page": { "id": "errorPage" } },
    { "statusCode": "404", "page": { "id": "errorPage" } },
    { "statusCode": "500", "page": { "id": "errorPage" } }
  ],
  "cdnEnabled": true,
  "siteProperties": [],
  "headerBackgroundColor": "#0055B3",
  "titleAlignment": "center"
}
```

## Script include files (`.script`)

PMD pages can reference shared Workday Script modules via the top-level `include` array:

```json
{
  "id": "myPage",
  "include": ["appValidations.script"],
  ...
}
```

- Script files live in `presentation/scripts/` and have the extension `.script`.
- The module name (without `.script`) becomes a variable in PMD script expressions: `appValidations.isValidSubject(text)`.
- A script file is a plain Workday Script file that exports an object map of named functions at its end: `{ "fnName": fnName, ... }`.
- Calling convention in PMD: `<% scriptModuleName.functionName(arg1, arg2) %>`.

**Example script module pattern:**
```javascript
var myFunction = function(arg) {
  // ... logic ...
  returnValue;
};

{
  "myFunction": myFunction
}
```

Scripts can reference Workday built-in namespaces (`date:`, `validate:`, `regex:`, etc.) and interact with business objects (`auditLogs.create()`). They do NOT have page widget access (no `self`, no widget IDs) — they are pure functions operating on passed-in values.

## footer / pod widget

The page `footer` (inside `presentation`) renders a persistent footer bar below the page body. It references a `.pod` file by `podId`:

```json
"footer": {
  "type": "footer",
  "children": [
    { "type": "pod", "podId": "appFooter" }
  ]
}
```

- Pod files live in `presentation/pods/` and have the `.pod` extension.
- The `podId` must match the filename without extension.
- Pods define reusable UI fragments (logos, branding, links) that can appear on multiple pages without repeating code.
- Pod files can include their own PMD-style widget declarations.

## Button `action` values

A `button` widget's `action` attribute controls its visual style and role. Confirmed values:

| `action` | Visual | Use |
|---|---|---|
| `"PRIMARY"` | Filled/highlighted button | Main call-to-action (e.g. "Open", "Submit") |
| `"AUXILIARY"` | Outlined/secondary button | Secondary actions (e.g. "Delete", "Add Pattern") |
| `"LINK"` | Plain text link style | Low-emphasis navigation (e.g. "← Home", "← Back") |

**Navigation buttons** use `taskReference` (app task) OR `workdayTaskReference` (delivered Workday task) — mutually exclusive, one required. Use `suppressDiscardDialog: true` on nav buttons inside edit pages to skip the "you have unsaved changes" warning.

**`parameterBindings`** passes named params to the target task (read via `queryParams` on that page):

```json
{
  "type": "button",
  "action": "PRIMARY",
  "label": "Open",
  "taskReference": {
    "taskId": "orgManager",
    "parameterBindings": {
      "appCode": "<% row.code %>",
      "appName": "<% row.descriptor %>"
    }
  }
}
```

## Grid display attributes

### `gridType`

`"gridType": "LIST"` renders the grid as a styled list view rather than a spreadsheet-style table. Useful for records-style display pages. Seen used with `"multiViewStylingEnabled": true`.

### `multiViewStylingEnabled`

`"multiViewStylingEnabled": true` enables richer multi-view styling on the grid (confirms to Workday that the grid supports multiple display modes). Use alongside `gridType: "LIST"` on view pages.

### Excel export with button cells

With `excelExportEnabled`, a `button` column needs `"excel": {"enabled": false}` **on the column** (not on the cell widget, which the build ignored), or the App Hub build fails: "To export a column with non-basic widget, configure the export properties in the excel attribute" (live 2026-11-02; not raised for every grid, so add it always).

**A `fieldSet` cell breaks the whole export** (live 2026-11-04): with `excelExportEnabled`, one `fieldSet` column without an `excel.value` makes Export to Excel fail for the grid ("attempted to resolve exporter, but no exporter found for widget ...StandardFieldSet"); the user just gets no file. `instanceList` and `text` columns export without settings. Give every `fieldSet` column `"excel": {"value": "<% row.someField ?? '' %>"}` (or `enabled: false`); the grid view doesn't change. Exports can't carry hyperlinks (`valueType` is `boolean`, `date`, `number` or `string`), so write an address as text, e.g. a Workday instance page `https://<host>/<tenant>/d/wid/<WID>.htmld` (`tenant` is a predefined app variable; there's none for the host).

**Checking an export without downloading it:** the Export to Excel click calls `GET .../w/excel/create/<id>`, which returns `{"docReadyUri": ".../w/excel/download/<id>?fileName=<grid label>.xlsx"}` or an `Application_Error` with the reason. Record the request in the page (wrap `XMLHttpRequest.prototype.open`), fetch it again, then fetch `docReadyUri` and unzip `xl/worksheets/sheet1.xml` with `DecompressionStream('deflate-raw')`.

### `autoPaging`

`"autoPaging": true` on a read-only grid automatically paginates large result sets without requiring the user to click a "load more" button. Use on view pages that may show many rows.

### Column widths and labels

- Column widths **can't be configured** (developer.workday.com "column": users can resize them in the UI only). Long values wrap into tall rows; shorten the values instead.
- Workday prints "n items" beside every grid label, so don't put a count in the label itself.

### `sortableAndFilterable`

**Only text-type columns sort** (live 2026-11-02): on a `button` or `fieldSet` column the attribute is ignored (no `aria-sort` on its header), and Workday draws an unsortable header about 10px lower than a sortable one. A list grid that mixes both has ragged headers; the only way to line them up is no sorting on that grid.

`"sortableAndFilterable": "true"` (string, not boolean) on a `column` makes that column sortable and filterable by the user in the rendered grid. Apply to columns where user sorting is desired (e.g. status, date, name columns).

```json
{
  "type": "column",
  "columnId": "colStatus",
  "label": "Status",
  "sortableAndFilterable": "true",
  "cellTemplate": {
    "type": "text",
    "value": "<% row.status ?? '' %>",
    "enabled": false
  }
}
```

## chartCard (the .card file side)

A `chartCard` embeds an interactive chart inside a Page Configuration Card. The `body.type` is `"chartCard"`.

### `donutChart2`

A donut/pie chart. All attributes:

- `type` (**req**) — `"donutChart2"`.
- `data` (listScript, **req**) — the data array. Each item is a map with at least two keys: one for slice size, one for slice color/label.
- `dataVariableName` (string, **req**) — alias for each item in `data` (used in `sliceSizeDataSet.value` and `sliceColorDataSet.value`).
- `title` (stringScript) — centre label inside the donut (e.g. total count).
- `sliceSizeDataSet` (**req**) — `{ "name": "Label", "value": "<% slice['fieldName'] %>" }` — which field drives the slice size.
- `sliceColorDataSet` (**req**) — `{ "name": "Label", "value": "<% slice['fieldName'] %>" }` — which field determines colour/legend label.
- `showPercentLabels` (boolean) — adds a percentage next to each slice's count (developer.workday.com donutChart2). It prints up to four decimals ("2 (0.939%)"); `false` shows the count only.
- `title` sits in the donut's centre, which is narrow: "213 organizations" was cut to "213 orga…". Use the bare number.
- `animateOnLoad` (boolean) — animate the chart when the card loads.

**Other chart types in a chartCard** (developer.workday.com "chartCard"): `bubbleChart2`, `clusteredBarChart2`, `comboChart2`, `donutChart2`, `dualAxisChart2`, `lineChart2`, `overlaidAreaChart2`, `percentAreaChart2`, `percentBarChart2`, `scatterChart2`, `stackedAreaChart2`, `stackedBarChart2`, `waterfallChart2`. The docs' example is a `stackedBarChart2`: `data`, `dataVariableName`, `categoryDataSet: {name, value}` (one bar per item), `measurementDataSets: [{name, value}, ...]` (one stacked segment each), `measurementAxisOptions: {axisTitle}`. A stacked bar of activity per day, split by area, is a good one-card summary of a whole app: build the day rows in a `.script` (oldest first) and pass them as one list parameter **(first live use pending)**.

```json
{
  "id": "OrgStatusChart",
  "parameters": ["activeCount", "inactiveCount", "totalPatterns"],
  "header": {
    "title": "Organization Overview",
    "subtitle": "Active vs. inactive organizations"
  },
  "body": {
    "type": "chartCard",
    "chart": {
      "type": "donutChart2",
      "data": "<% [{'status': 'Active', 'count': activeCount ?? 0}, {'status': 'Inactive', 'count': inactiveCount ?? 0}] %>",
      "dataVariableName": "slice",
      "title": "<% (totalPatterns ?? 0) + ' Total' %>",
      "sliceSizeDataSet": { "name": "Count", "value": "<% slice['count'] %>" },
      "sliceColorDataSet": { "name": "Status", "value": "<% slice['status'] %>" },
      "showPercentLabels": true,
      "animateOnLoad": true
    }
  }
}
```

**Passing data to a chartCard:** parameters are passed from `cardContainer` just like `simpleCard` — via `parameters` mapScript. Guard against nulls with `?? 0`.

## Common inbound endpoint patterns (continued)

### Current worker

```json
{
  "name": "selectedWorker",
  "baseUrlType": "COMMON",
  "url": "/workers/me",
  "authType": "sso",
  "bestEffort": "true"
}
```

Then reference worker fields as `selectedWorker.id`, `selectedWorker.descriptor`, `selectedWorker.primaryJob.businessTitle`, etc.

### Business-object collection

```json
{
  "name": "requests",
  "baseUrlType": "BUSINESS-OBJECT",
  "url": "/requests",
  "authType": "sso",
  "isCollection": true,
  "bestEffort": "true"
}
```

Returns `{ "data": [...] }` — access items via `requests.data`.

## Button navigation — `parameterBindings` vs `parameters` pitfall

On a `button`'s `taskReference`, both `parameters` and `parameterBindings` appear to work individually, but **`parameterBindings` silently overwrites `parameters` when both are present**. Only one key should ever appear. Prefer `parameterBindings` consistently:

```json
{
  "type": "button",
  "action": "PRIMARY",
  "label": "Open",
  "taskReference": {
    "taskId": "orgManager",
    "parameterBindings": {
      "appCode": "<% row.code %>",
      "appName": "<% row.descriptor %>"
    }
  }
}
```

**Never mix both keys** — the result is only the `parameterBindings` values, silently dropping anything in `parameters`.

## Workday Script — lambda returning object literal (double-brace pattern)

When using `.map()` or `.filter()` with a lambda that returns an **object literal**, the object must be wrapped in a **second nested brace block**:

```
workers.data.map(worker => {
  {
    'column1': worker.descriptor,
    'column2': worker.businessTitle
  }
})
```

A single brace block `worker => { 'col': worker.x }` is parsed as a code block (series of statements), not an object. The outer braces delimit the lambda body; the inner braces create the returned map literal.

## Workday Script — direct widget state mutation

In `.script` event handlers, widget state is mutated directly by assignment — no setter method needed for `value` and `visible`:

```javascript
descriptor.value = myEndpoint.data[0].descriptor;
workerDetail.visible = true;
```

This is the idiomatic pattern in the Workday DevRel corpus. The setter methods (`setValue()`, `setVisible()`) are also available, but direct assignment works and is commonly used in script files.

## Endpoints — `failOnStatusCodes`

Source: developer.workday.com "endPoints" reference (checked 2026-10-31).

- **Format:** a list of objects, `"failOnStatusCodes": [{"code": 400}, {"code": 429}]` (`codeName` is optional and informational). Not a plain number list.
- **Already errors by default:** 301, 302, 303, 307, 401, 404, 407, 408, 500, 503. **Ignored by default:** everything else, notably **400, 403 and 429**: without listing them, a bad request, a permission failure or throttling just looks like an empty result.
- A listed code gives a page error (or the custom error page mapped in the SMD).
- **Be deliberate with 403.** On an eager endpoint it fails the whole page. List it where a 403 means misconfigured security (the app's own business objects, `/workers/me`); leave it off side lists a user may legitimately lack access to (e.g. a Workday data source behind a search), so they see an empty list instead of a broken page.
- `bestEffort: true` is about **widget** errors (the page renders without the failing widget); it doesn't stop a listed status code from failing the page.
- Workday's DevRel Arcane Auditor flags inbound endpoints without it (EndpointFailOnStatusCodesRule). The static test suite warns on them.

## Endpoints — REST collections default to 20 rows

**Workday REST collection endpoints return only 20 rows by default** (max 100 per request). Always pass an explicit `limit` parameter, or paginate. Without it, your grid silently shows only the first 20 records even when more exist:

```json
{
  "name": "allRoles",
  "baseUrlType": "BUSINESS-OBJECT",
  "url": "/requests?limit=100",
  "authType": "sso",
  "isCollection": true
}
```

For large datasets, use WQL with paging or RaaS (which has no pagination limit).


**Order and paging (confirmed live 2026-10-31 on an app business object):** the collection comes back **oldest first**, so `?limit=100` shows the *oldest* 100 rows once there are more. `?limit=1` gives the total in `.total`; `offset` works, and an `offset` equal to the total returns an empty `data` list. To show the newest rows, add a count endpoint and offset pages that reference it (inbound endpoints can use an earlier endpoint in their URL):

```json
{ "name": "auditLogCount", "baseUrlType": "BUSINESS-OBJECT", "url": "/auditLogs?limit=1", "authType": "sso" },
{ "name": "auditPage0", "baseUrlType": "BUSINESS-OBJECT", "authType": "sso", "isCollection": true,
  "url": "<% let t = auditLogCount.total ?? 0; let start = (t - 100) < 0 ? 0 : (t - 100); let cnt = t - start; '/auditLogs?limit=' + (cnt > 0 ? cnt : 1) + '&offset=' + (cnt > 0 ? start : t) %>" }
```

Join several pages with `list:flatten([auditPage0.data ?? [], auditPage1.data ?? []])`. Leave 400 out of `failOnStatusCodes` on the extra pages so an empty page never fails the load. Tests that look for a just-written record must read every page too.

**Bulk DELETE can't be used from a PMD** (developer.workday.com "Reference: Business Object API Requests"); use a grid `deleteEndPoint` or an orchestration.

## App Hub build warnings (2026-11-06)

The upload's build log lists warnings that don't block a deploy. Worth fixing: duplicate widget ids on a page (e.g. two hidden fields built from the same first letter), grid `readOnly`, and endpoints "declared but never used". **That last check misses uses in `tabs`, card `parameters`, outbound `values` and event scripts** (it flagged an endpoint used 26 times), so check each one before deleting. The isCollection warning is the one below.

## Endpoints — `isCollection: true` performance warning

Using `isCollection: true` on inbound endpoints **can degrade the entire tenant under concurrent use** (NoIsCollectionOnEndpointsRule). For querying data, prefer **WQL** or **RaaS** instead of `isCollection`. Reserve `isCollection` only for small, bounded BO collections where WQL is unavailable.

## Grid — do not combine paging with `sortableAndFilterable`

**Never combine server-side paging with `sortableAndFilterable` columns.** Every page change triggers a refetch, re-sort and re-filter cycle, causing severe performance problems. Choose one approach:

- Server-side paging + search prompts for filtering (no `sortableAndFilterable`)
- Client-side sorting with `sortableAndFilterable` + keep the result set small and unpaged

## Grid — `excelExportEnabled` row limit

`"excelExportEnabled": true` on a grid has a **~60 second export limit**. Workday warns against it above ~4,000 rows. For large exports, use a **RaaS report** instead — RaaS has no pagination and is designed for bulk data export.

## WQL — operators and one-value lookups (2026-11-07)

- Text operators (doc.workday.com "WQL reference"): `=`, `!=`, `contains`, `not contains`, `startswith`, `endswith` (spelled lower case), `in (...)`, `not in`, `is empty`, `is not empty`. `contains`/`startswith`/`endswith` ignore case, and live `abbreviation = 'chem'` found CHEM, so `=` ignores case too: compare the returned value when case matters. `ORDER BY field` works; `SELECT *` doesn't ("This field is invalid: *"). An instance filter takes the WID bare: `academicYear in (e32e...)`.
- **For a check against a list that may hold tens of thousands of rows, query the one value** (a deferred endpoint `'data?limit=' + lim + '&query=' + string:pathEncode(q)`, `.invoke()` from onChange/onSubmit; about 0.2 s) instead of loading the list. Build `q` in a `.script` that strips quotes and backslashes; pass `res.total ?? (0 - 1)` so a failed lookup doesn't block.
- Data sources seen in a student tenant: `courseSubjects` (abbreviation, name, inactive), `academicPeriods` (name, academicYear, periodType, academicCalendar, startDate, inactive), `academicYears`, `academicUnits` (academicUnitCode). Find others with `GET /wql/v1/dataSources?alias=<alias>` or `?search=<words>`, then `/dataSources/<id>/fields`.
- **Courses in WQL:** the `courses` alias is the Course Subjects data source, not courses; course definitions are `courseDefinitions` (course, title, courseSubjects, courseListings, academicUnits, hiddenCourse). To list one subject's courses, find the subject's WID first (`SELECT courseSubject FROM courseSubjects WHERE abbreviation = '...'`), then filter `courseSubjects in (<WID>)` (live 2026-11-07; one dev tenant had 0 course definitions).
- Repeating a long check in every field's onChange grows a page fast (7 fields × 15 handlers took one page from 40 KB to 122 KB, over the 100 KB limit): move the logic into `.script` functions and read shared lists once per handler.

## Moving an app between tenants: WIDs and calculated fields (live 2026-11-10)

**Don't hard-code tenant data in an app.** A WID of a tenant-configured instance (an organization subtype or type, a role, an org) and a calculated field (`cf_...`) are tenant configuration: the next tenant has other WIDs, and its calculated fields may be missing or named differently. Workday-delivered instances (e.g. the BP step action "Submitted" `d9e4223e446c11de98360015c5e6daf6`) and the app's own orchestration ids are the same everywhere. Keep a static check that fails on any other 32-hex value in the app files.

**Find instances by name in WQL:**
- An instance field filters by WID only. Refused (one tenant): `subtype in (X:SHELL)` / `("X:SHELL")` ("cannot resolve instance"), `subtype in (Organization_Subtype_Name = "X:SHELL")`, the documented `(inst_refId = ...)` (both "Invalid WQL syntax ... at or near '='"), a bare reference ID, `subtype.descriptor = ...` ("This field is invalid").
- **Works: a GROUP BY lookup, then the WIDs as a parameter.** `SELECT subtype, COUNT(workdayID) FROM topLevelOrganizations GROUP BY subtype` returns one row per value, `{"subtype": {"descriptor", "id"}, "COUNT(workdayID)": "7"}` (34 rows here). Keep the ids whose descriptor matches and pass them into the real query (`WHERE subtype in (<% subtypes %>)` in a WQL component with `parameters`; an eager lookup endpoint that the query endpoint's `parameters` read). `SELECT DISTINCT` is refused.
- **GROUP BY refuses a multi-instance field** ("For grouping, specify a field other than a multi instance field"). Look for a single-instance twin: `customOrganizations.type1` (multi) has `organizationTypesPrimary` (single, same values here).
- **`in ()` with nothing in it returns no rows, no error**, so a name that doesn't exist in a tenant gives an empty list rather than a broken page. A made-up WID errors ("cannot resolve instance").
- In an orchestration: one GET for the lookup, then `stringAtJsonPathWithDefault("$.data[?(@.subtype.descriptor == 'X:SHELL')].subtype.id", "")` per name, joined into the next step's path.
- The lookup adds one small call (~0.3 s) before the query it feeds.

**Calculated fields can't be part of an app.** They're tenant report fields (Create Calculated Field), not Extend components, so an app that reads `cf_...` needs them recreated with the same alias in every tenant, or migrated with the tenant configuration. Prefer delivered fields, and **compare values over every row before switching**: a field with a matching name can differ. One tenant (2026-11-10):
- Same on every row, switched: `allPositions.cf_PositionID` = `positionID` (829/829); `cf_PositionIsFilled` = `worker` not empty (829/829; an empty instance field is left out of the WQL response, so in an orchestration test the response text for a `"worker":` key); `topLevelOrganizations.cf_active1` = not `inactive` (1704/1704; `inactive` comes back as `false`, not missing).
- **Read the calculated field's definition first** (user tip, 2026-11-10): search its name in Workday (it shows under Reporting; the descriptor, e.g. "zCF - EE - Role Assigned to as Position Restrictions", not the `cf_` alias) and open it. The page shows the type (Evaluate Expression, Extract Multi-Instance, ...), the business object, the source field and the condition, and links to any calculated fields it's built on. That tells you which delivered fields and business objects to rebuild it from, instead of guessing.
- Rebuilt from its definition: role assignment `cf_ZCF_EE_RoleAssignedToAsPositionRestrictions` is an Evaluate Expression over "zCF - EMI - Restricted Postions" = Extract Multi-Instance, Subset of **Role Assigned To** where class of instance is Position Restrictions. Delivered equivalent: `roleAssignedTo` kept to the ids that are an `allPositions.positionRestriction`, named by that field's descriptor ("P-00003 Controller - Teresa Serrano"); equal on 3459/3459 assignments and 3637/3637 names. `roleAssignedTo` alone isn't enough: it also lists other assignees and names a position by its worker. Note `allPositions.workdayID` (the position) and `positionRestriction.id` (what role assignments hold) are different WIDs.
- WQL's field list for a related object (`/dataSources/<id>/fields/<fieldId>` → `relatedFields`) is incomplete: Role Assignment listed 24 fields without `roleAssignedTo` or `workersAssigned`, which both query fine.
- No delivered match, kept: `cf_PositionText` ("Position Text" = Concatenate Text: Position and Job - All Staffing Models + "-" + Position ID; the name already starts with the ID). **No delivered text field holds the position's name** (2026-11-10: every text field of allPositions, allPositionsIncludingClosedPositions, allPositions1 "All Positions" and indexedPositionsAndJobs_AllStaffingModels "Positions for HCM Reporting" compared with the name on every row: none equal), and WQL can't search an instance's name ("This operator is invalid"). The name is built as `positionID + ' ' + (positionTitle, or openPositionTitle when vacant) + (' - ' + worker name, or ' (Unfilled)')`: 804/829 rebuild exactly; the rest add "(+)" or "(Position Fill:<date>,<name>)" for pending hires. **Search with delivered text fields:** `(positionID contains q OR positionTitle contains q OR openPositionTitle contains q OR worker_Name contains q)` returned exactly the same positions as `cf_PositionText contains q` for "analyst" 51, "beth" 2, "P-0001" 5, "director" 50, "senior it" 11, "controller" 7; "unfilled" needs `worker is empty` (185, vs 182 by name: 3 pending hires read "Position Fill"). A query whose words fall in different parts ("P-00030 senior") matches the name but not any one field, so split on spaces and require every word to match one field.
- A calculated field that stays is a tenant prerequisite: list it in the project notes (with its definition, so it can be recreated) and have a smoke test query it, so a tenant without it fails clearly. A static check can allow only the listed ones.

**A late build pass that rewrites generated files needs a `--restore` that runs in reverse order of the passes** (2026-11-10): restores go last-applied first, at the top of the rebuild script. Restoring a later pass's saved copies after an earlier pass's restore puts back files that still carry the earlier pass's changes, and the next builder fails (here: a page without its title, KeyError 'title').

- Field list of a data source: `GET /wql/v1/dataSources?alias=<alias>` → id, then `/dataSources/<id>/fields?limit=100&offset=<n>`; a related object's field shows `relatedBusinessObject`.

## WQL — injection risk in string concatenation

**Don't put user-typed text into a WQL string raw.** A quote in the search text ends the WQL string literal and lets the user change the query:

```
// UNSAFE: the user controls the search string
"url": "<% 'data?query=' + string:pathEncode('SELECT ... WHERE name contains \\'' + instanceListQuery + '\\'') %>"
```

- **Fix used in practice:** strip the characters that can end the literal before concatenating. In the script: `instanceListQuery.replace('\'', '').replace('\\', '')`; as written inside the .pmd JSON string: `instanceListQuery.replace('\\'', '').replace('\\\\', '')` (string `replace` replaces every occurrence; `replaceOnce` exists separately). Accented and other non-ASCII search text still works.
- **Alternative:** a WQL Query component (`.wqlquery`) with `parameters`, interpolated server-side. But a `queryId` endpoint can't be called with `.invoke()` (see run-and-verify), so check it works with `searchEndPoint` before relying on it **(unverified)**.
- Keep a static check that fails when `instanceListQuery` / `event.query` reaches a `data?query=` URL without the replace.

## Orchestrations — debugging and failure handling

- **A page's "success" only means the launch returned 200.** The Orchestrate `/launch` call returns HTTP 200 (a short text/plain body) even when the orchestration later fails, so an outbound launch endpoint's `failOnStatusCodes` never fires. Always confirm the result some other way (run-and-verify, below) and read the run log.
- **Orchestration runs in the tenant (checked 2026-11-03):** the tenant has an **Orchestration Runtime Tracker** business object (Runtime ID, Status, Launch and Completion Date Time, Runtime Status Error Message, Application ID), but it links only to **Action Event**, so it records business-process-triggered runs only (on the event's Orchestrations tab). Runs launched from a page or by API leave no Integration Event or other tenant record; their history is on developer.workday.com (Logs, Orchestration Activity). To tie an audit record to its run, store `context.orchestrateId()` as text; to tie it to a Workday event, store an event reference the web service returns (e.g. `Assign_Roles_Event_Reference`).
- **Run logs:** developer.workday.com → Apps → the app → **Logs** tab (last 15 minutes). The "Aggregated step totals" line for a run's commonId lists each step with its success/failure counts. The **Orchestration Activity** tab lists runs per orchestration.
- **A global error handler that only logs swallows failures.** Prefer letting a failed check stop the run.
- **Fail on a rejected Workday call with a Continue on Conditions step** right after the call (`_type` `ContinueOnConditions`, `assertions: List<Assertion{assertion: Expr Boolean, message: Expr String}>`). For a SOAP call: `data.<call>.responseStatusCode.is2xxStatusCode().not().or(data.<call>.response.isSoapFault()).not()`. Source: developer.workday.com "Concept: Orchestration Logic Components".
- **Guard the inputs too.** An orchestration that's launched by URL can be called by anyone who can reach that URL, not only through the page. Before the Workday call, add a Continue on Conditions step that checks every parameter that decides *what* changes: allowed values, prefixes, and that a passed WID really is the kind of object you expect (look it up). Never let a free parameter pick the operation (e.g. inactivate vs reactivate) while a different parameter is written to the audit record; derive both from the same value.
- **String member functions** (developer.workday.com "Reference: String Member Functions") include `contains`, `startsWith`, `equals`, `isEmpty`, `toString`, `append`.
- **Logging a Workday response:** a `Log` node with `"..." + data.<call>.response.toString()` writes the full response, including SOAP fault text, to the app Logs.
- **Text templates support `{{#if}}` but NOT `{{else}}`** (build error "illegal start of simple expression"). Use two `{{#if}}` blocks with Boolean flags created in a CreateValues node (`data.x.flag.equals("true")`, type Boolean). **The condition must be a Boolean:** `{{#if data.start.someText}}` fails the App Hub build ("Actual type of argument (StringType) is not compatible with required type of argument (BooleanType)", 2026-11-05); for "only when filled in" make a flag `data.start.someText.isEmpty().not()` first.
- **Reading API responses:** `data.X.response.asJSON().stringAtJsonPath(...)`. Calling `stringAtJsonPath` on the raw response can fail the build ("cannot be applied to an instance of DataType").
- **Getting real JSON for a component the repo doesn't use yet:** add it in Orchestration Builder, then the orchestration's Settings → **Open Current Source Code** shows the JSON without saving. (Alternative: save to App Hub, then console → app → Related Actions → View Source.) The next CI upload overwrites App Hub with the repo version. A stale App Builder session: ⋮ → Revert to App Hub, or Discard Session.
- **Returning data from a synchronous orchestration:** EndSync `body` = `{"_type":["Opt","DataRefBody"],"_value":{"_type":"DataRefBody","_value":{"dataRef": <Expr Data, e.g. data.Card.message>, "contentType": {"_type":["Opt",["Expr","String"]],"_value": <Expr String with source "\"application/json\"">}}}}` (a plain `["Opt","String"]` contentType, as in the samples, fails the 3.406 compiler: "\"String\" is not assignable to [\"Expr\",\"String\"]"), usually fed by a CreateTextTemplate node (`message` TextTemplate with `{{ }}`, `contentType`, `formatRef` null). Seen in Workday's sample apps up to flowVersion 3.3.0; in 3.7.0 files an empty Opt names the supertype (`["Opt","ResponseBody"]`, `["Opt","HttpBody"]`) while a filled one names the concrete type (`["Opt","CreateTextTemplateBody"]`). Confirmed live 2026-11-02 (flowVersion 3.7.0): `POST .../<Name>/launch` then returns the body as JSON; with no end body, or when a step fails, it returns text ("Completed", or "Completed with error: <reason>", still HTTP 200), which is the quickest way to read a run error.
- **Counting matches in an orchestration (live 2026-11-02):** `arrayAtJsonPath("$.data[?(@.status == 'X')].id")` builds but fails at run time ("Expected array but found string"): the path's first match must itself be an array. Count in the response text instead, without division: `t.replace("\"X\"", "\"X\"#").length() - t.length()` with `t = response.asJSON().toString()`, then `.toString()` on the number. `stringAtJsonPathWithDefault("$.data[?(@.status == 'X')].field", "")` returns the **first** match. `.truncate(n)` and `.append` work in CreateValues.
- Orchestration files are single-line JSON: when editing with a script, re-serialize compactly (`separators=(',',':')`) to keep diffs small. Clone an existing node of the same type as the prototype for a new one.

### Run-and-verify from a page

Pattern that lets a Workday rejection block OK instead of showing a false success:

- Launch from `onSubmit` through a **deferred inbound** endpoint (orchestration base URL, `'/<Name>/launch?p=' + p + ...`, parameters bare in the URL), with `endpoint.invoke({'p': value, ...})`.
- Then re-read something that only exists if the change worked (the new record, or an audit record the orchestration writes only after its success check) with a second deferred endpoint. If it's missing, `someField.setError('Workday rejected this request, so nothing was changed...')` and return `false`.
- Count audit records with the BO REST collection's `.total` (`GET /collection?limit=1`), not a WQL count: WQL lagged and gave false "rejected" errors.
- **`.invoke()` on a WQL endpoint that uses `wqlQuery` / `queryId` throws `Unknown Function call: .invoke({ })`.** Call WQL as a plain GET instead: `"baseUrlType": "<wql provider>"`, `"url": "<% 'data?limit=' + lim + '&query=<URL-encoded WQL>' %>"`, invoked with `.invoke({'lim': '10000'})`. Keep that WQL static (no user input) and filter in script.
- **URL-encode free text in launch URLs** (`value.urlEncode()`): a space gives InvalidEndPointUrlException "Illegal character".
- In an editWizard, Next on a step runs that step's `onSubmit` validation and the final OK runs it again; the launch fires only on OK, once validation passes.

### Calling Workday Web Services (SOAP) from an orchestration

- **`Organization_Add_Update` takes the subtype by name only:** `Organization_Subtype_Reference` holds just `Organization_Subtype_Name` (v47.0 Human_Resources XSD, checked 2026-11-02); a reference ID (`Organization_Subtype_ID`) can't be sent there.

- `SendWorkdayApiRequest` POST `/soap/v<version>/<Service>` (e.g. `/soap/v42.2/Human_Resources`) with a SOAP body works with the default credential.
- **Use `Validate_Only=true` to test a WWS call safely**: Workday checks the request fully and changes nothing.
- Check the operation's real shape in the tenant WSDL (`https://<services host>/ccx/service/<tenant>/<Service>/v<version>?wsdl`); community docs pages move. Several operations are **one-way** (empty response body): they return no event or new WID.
- Lessons from the Human_Resources and Staffing services:
  - `Organization_Add_Update` can't change status (no Inactive element). Status changes use `Organization_Inactivate` (`Organization_Reference_Data` with `System_ID="WD-WID"` + `Organization_Inactivate_Data Effective_Date`) and `Reactivate_Organization_Request`. Neither returns an event; Reactivate returns `Organization_Reference`.
  - **An org with a future-dated event can't take another status change** ("Organization has conflicting events (in progress or future events)"). Pick a date after the last future event, or expect the rejection. A future-dated inactivation leaves the org active until that date.
  - `Assign_Roles_Request`: add assignees by `bsvc:type="Position_ID"`; a position's WID from `allPositions` is rejected as an Event Target Role Assignee. Remove by the current assignee's WID from the role assignment data. The response returns `Assign_Roles_Event_Reference` (linkable).

### Business-process-triggered orchestrations

- Template "Workday Business Process": flow type `.maya.FlowBusinessProcessTriggered`, start `StartBusinessProcess`, end `EndEmptyMaya`, default credential `AccessTokenFromInitiatingUser`.
- The BP's target: `bp.eventTarget().getIDValues("WID").get(0)`. (`bp.eventTarget().toString("WID")` is in the docs but fails the build.) Timestamp: `datetime.now("UTC").format("yyyy-MM-dd'T'HH:mm:ss'Z'")`. References: "Reference: Business Process Global Functions", "Reference: DateTime Global Functions".
- Attach it: BP definition related actions → Business Process → **Configure Orchestrations** → Add → pick the action (e.g. Deny, Cancel) → create an Orchestration Launch Configuration. Saving it needs the tenant-wide **Edit Tenant Setup – Business Processes → User to perform Orchestration Launches** to be set first.
- Launches are queued: Workday says usually within ~15 minutes; in practice 2–3 minutes. Status: Find Events → the event → Orchestrations tab. After a deploy that changes such an orchestration, confirm it still fires (one launch went missing after such a deploy, cause not yet known).
- **Who denied / cancelled:** `bp.initiatingPerson()` returns a **Person** reference (not a Worker; `getIDValues("WID").get(0)` gives the Person WID, so `/common/v1/workers/{id}` won't find it). `GET /person/v4/people/{id}` returns only links; the name is at `GET /person/v4/people/{id}/preferredName` → `$.data[0].descriptor` (confirmed live 2026-10-31 with the default credential). An InstanceReference has no descriptor function, only IDs. Checked only where the requester was also the canceller.
- **Deny is offered only while an approval is awaiting action.** If the initiator is in the approval group, the approval auto-completes and only Cancel remains, so pair the same "close the request" orchestration with **Cancel** as well as Deny.


- **The API gateway can refuse a launch with an HTML 403** (body starts with `<style>`), before the orchestration or its security runs. Seen 2026-10-31: one role-assignment orchestration launch was refused every time, while the same call with any one of roleName, orgName or changedByWid changed went through; percent-encoding `( )` didn't help. It looks like a content filter scoring the whole query string. If a launch from a page fails this way, try shorter text values or pass ids the orchestration can look up instead of free text **(cause unverified)**. The same change made through the app page (values sent with `.urlEncode()`) went through, so try the page before changing the orchestration.
- **The gateway refusal is a score over the whole query string** (gateway probe 2026-11-04, launches with an invalid mode so nothing ran): with real values (role WID, role name, org name "X:...(...) ... (varies)", position WID, timestamp) the launch got HTML 403; removing any one of five values let it through, and every value alone passed. Encoding like Java URLEncoder (`+` for spaces, `( ) ! '` percent-encoded) didn't help. Shortening the one free-text value (org name to its code) did. Find the trigger with launches the orchestration's own guard rejects before any Workday call.
- **Run ID and event links confirmed (2026-11-04):** `context.orchestrateId()` equals the launch response's **`X-Orchestrate-Id`** header, so a test can check a stored run ID against the run it started. The Staffing `Assign_Roles` response's event WID can be read as text, `response.toString().substringAfter("Assign_Roles_Event_Reference").substringAfter("type=\"WID\">").substringBefore("<").trim()`, and `GET businessProcess/v1/events/<wid>` opens it ("Assign Roles for P-... effective ...").
- **Organization types of application-level orgs (probe 2026-11-05, one tenant):** each X: application org had an organization type of exactly its own name, including bracketed ones (X:LLIS(CPE) → type X:LLIS(CPE)); WQL topLevelOrganizations field `type1` (multi-instance) holds it, `subtype` the subtype. `Organization_Add_Update` with a type that doesn't exist is rejected, so creating a new application's org needs its type set up first.
- **Guard `mode`-style parameters.** A launch with an unexpected mode (neither ADD nor REMOVE) still called Workday and wrote audit records with no action. Check allowed values in a Continue on Conditions step before any Workday call.
- **String functions** in orchestration expressions include `replace`, `replaceOnce`, `normalizeSpace` (collapses whitespace and newlines), `truncate`, `escapeXml`, `trim`, `substringBefore/After`, `urlEncode` (developer.workday.com "Reference: String Member Functions"). To put free text into a JSON template: `.normalizeSpace().replace("\\", "/").replace("\"", "'")` (deploys; not yet tested with real quotes).

## Business processes on Extend business objects

- Tenant setup order: BP type → **Edit Policy** (Initiate, steps, View All, Approve, Deny, Cancel) → **Activate Pending Security Policy Changes** → **Create Business Process Definition** → Edit Definition. Step groups only show in the prompt after the policy is activated. Find the definition by searching `bp: <name>`.
- **The approval group must resolve to people.** A business object without organization context can't use constrained role-based groups: the domain's View Domain page lists **Allowed Security Group Types** (e.g. Public, Unconstrained). A constrained group shows the step as Awaiting Action with **All Persons = 0**. Use a user-based group or the **(Unconstrained)** variant.
- An approver's group needs **three** policies: the BP security policy (Approve, Deny, View All), the domain that secures the step pages, and the domain that secures the BO data. Then Activate Pending Security Policy Changes. Edit Definition shows a page error if a step's group isn't in the BP policy. An in-flight event keeps its original routing.
- **Block self-approval:** approval step → View Workflow Step → related actions → Business Process → **Maintain Advanced Routing** → Routing Restrictions → **Exclude Initiator**. If the restriction excludes everyone eligible, the step is marked **Not Required** and skipped, so add an Alternate Security Group when the approver pool is small. Whoever calls the API that starts the event is the initiator: start it as the requester (not an ISU) or Exclude Initiator stops working.
- **Starting an event on a BO record:** POST `/apps/<app>/v1/<businessProcessEventCollection>` with `businessProcessTarget.id`. Step pages get context with `GET businessProcess/v1/eventSteps/<eventStepId>` → `event.id`, then `GET events/<id>` → `for.id`. Complete an action step with `POST eventSteps/<id>/submit` and `stepAction.id = d9e4223e446c11de98360015c5e6daf6` (Submitted).
- **Cancel an event:** `POST businessProcess/v1/events/<id>/cancel` with `{ "comment": "..." }` (developer.workday.com "Events REST APIs").
- **Event status in the API:** a denied or cancelled event reads **"Process Terminated"**, not "Denied". Match on `denied|cancel|rescind|terminat` when checking that an app record agrees with its event.
- **A record linked to a BP event can't be deleted** (HTTP 500 "Attempt to delete instance ... with references"). Test data that starts events is permanent: close it (cancel), don't plan to delete it.
- **Inbox titles** use the target's display value: `useForDisplay: true` on the BO's name field.
- **Step help text:** definition related actions → Business Process → **Maintain Help Text** → step → Edit Step Help Text. The cell is a plain textarea plus a **Format Text** button that opens a rich-text editor (bold, italic, underline, colour, bulleted list, link; no numbered list). A consistent format works well: bold "Step N of M: <name>" title, one-line purpose, a bold "Check"/"How to" bulleted list, then a bold "Next:" or "Outcome:" line.
- **Completion notification:** definition related actions → Business Process → **Add Notification** → Trigger on Status = Completed, Recipients = Initiator. Completed fires on the approve path only. Remove any empty Email Addresses row before OK.

- **Event comments:** `GET businessProcess/v1/events/<id>/comments` returns `{ "data": [ { "person": {id, descriptor}, "comment": "...", "commentDate": "..." } ] }` (confirmed live 2026-10-31). A Deny or Cancel comment shows up here, so a BP-triggered orchestration can copy it into the record (e.g. Denial Reason).

## Security and ISU writes

- **Secure every orchestration a user can launch.** Without it, anyone who can reach the launch URL can run it (the page's own security doesn't cover the URL). Set `"enabledForOrchestrationSecurity": true` on the security domain (developer.workday.com "Add Security Domains"; changing it from false to true is allowed after promotion), then list the domain in the orchestration's `securityDomains`: `{"_type":["Opt",["List","String"]],"_value":{"_type":["List","String"],"_value":[{"_type":"String","_value":"ManageThings"}]}}`. Use the same domain as the page that launches it. **Only one security domain per orchestration** (App Hub build error "Only one security domain can be defined for an orchestration", 2026-10-31): if two pages with different domains launch the same logic, give each its own copy of the orchestration. Exactly which domain permission a launch needs is **(unverified)**: test with a user who has the page but not the domain. Business-process-triggered orchestrations run as the tenant's launch user; leave them out.
- Configure an ISU for Presentation Components (developer.workday.com "Configure ISU Authentication in Presentation Components"): SMD `"siteAuth": {"authTypes": [{"id": "isuAuth", "scheme": "ISU", "username": "<ISU username>"}]}`; on each endpoint, `"authType": "isuAuth"`.
- Setup per tenant ("Create Integration System Users for apps"): create the ISU and its security group, assign it to the app with the **App Manager** task, and create orchestration credentials in Orchestration Builder (ISU credentials can't be used in Custom Agent Action orchestrations).
- **An `isuAuth` endpoint fails with HTTP 500 and an empty body until the ISU is assigned to the app in App Manager** for that tenant. Naming it in the SMD isn't enough, and the assignment doesn't carry over on promotion: re-check after every move (dev → impl → sandbox → prod).
- **Pattern for tamper-resistant records** (audit logs, request status): pages write them with `isuAuth` and orchestrations with the ISU credential, users get View/Get only. Then a direct REST call by a user can't create, edit or delete them. Until the user groups are reduced, the records are editable and deletable through the REST API by anyone with Put on the domain.
- Keep BP-starting calls and step submits as the user, so the requester stays the initiator.

## Audit logging pattern

- **One writer per change.** If an orchestration makes the change, it writes the audit record after its success check; don't also write one from the page.
- Pass `changedBy`, `changedByWid` and `timestamp` into every launch; orchestrations have no other way to know who acted.
- **Don't template SINGLE_INSTANCE fields as plain strings** in an orchestration body (`"worker": "<wid>"`): the write silently fails. Store WIDs in TEXT fields (`changedByWid`, `orgWid`, `roleWid`, `positionWid`).
- Keep a fixed vocabulary for change type and action, and test it.
- **Related actions from a stored WID** (VIEW page grid): the cell is a `fieldSet` with an `instanceList` (`values: [{'id': wid, 'descriptor': name}]`, `widKey: "id"`, `view`/`relatedTask: true`, `visible: !empty(wid)`) plus a `text` fallback (`visible: empty(wid)`). For several WIDs, store them comma-separated and build one entry per WID.
- Store display names next to the WIDs at write time (e.g. position names), rather than re-looking them up when displaying: lookup lists are often capped (REST collections return 20 rows by default) and the names then silently disappear.
- When storing several names in one text field, pick a separator that can't occur inside a name, or split with a lookahead on the next item's ID (`splitByRegex(', (?=P-[0-9])')`): position names like "Director, Field Sales" contain ", ".
- **Grid rows that join two lists can hit the PMD script memory limit** ("Script Constraint exceeded: ... more than the allowed max memory limit"). Build each lookup list once, cut down to the keys the rows need, before mapping the rows. Don't filter a 500-row list inside every row.
- Deleting BO records from a page: an outbound `DELETE /collection?bulk=true` with a `values` body is **silently skipped**. What works: a grid with `deleteEndPoint` + DELETE `'/collection/' + idCell.value`, removing rows and then OK.

## Files: offering a stored file for download

Source: developer.workday.com "Concept: fileUploader", "fileUploaderRow", "attachmentList"; live test 2026-11-01.

- Store the file as a record of an **attachment object** (model `.attachment`), then show it on a VIEW page with a read-only `fileUploader` whose child `loop` (`on` the collection's `.data`, `as` the item) renders a `fileUploaderRow` with `allowRemove: false`, `fileName`, `fileType` (`fileType:getFileType(...)`), a `contentArea` for details, and an `attachment` `attachmentList` (`attachmentURL` = full `https://api.workday.com/apps/<appId>/v1/<collection>/<id>`, `attachmentAuth: "sso"`, `attachmentName` = the record's `fileName`, `attachmentUriTemplate: "[Target]"`, one `instanceList` item with `action: "attachment"`, `mimeType`, `iconId` e.g. `mime_msexcel`). Workday rewrites the link to its own `/w/download/assets/...` address and serves the file as an attachment (checked: same bytes, xlsx content type).
- Uploading from a page: `fileUploader` with `metadata` and `valueOutBinding: "<endpoint>:<defaultCollectionName>"`, endpoint `url: "/<defaultCollectionName>Collection"` (POST), fields set in `onMultiPartSend`.
- Uploading from a script (REST): multipart POST to `/<collection>Collection`. The JSON part must be a **plain form field without a filename** (`form.append('data', JSON.stringify({ <collection>: [{ file: 'cid:<collection>0', ...fields }] }))`), and the file part named `<collection>0`. Sending the JSON as a Blob/file part fails with HTTP 400 "Multipart Attachment requests must contain exactly one root body". Reading back: `GET /<collection>/<id>` with Accept JSON gives metadata, without Accept the file.
- **An attachment object's collection may ignore `limit`/`offset`** (live 2026-11-02: `?limit=1&offset=n` returned every record). To show one record, sort and cut it in the page: `list:sort(data, 'field', false).subList(0, 1)` (guard the empty list first).
- Workday Extend can't build an .xlsx itself (no Excel node in orchestrations). Generate files outside (a CI step) and publish them as above.
- Orchestration strings have `length()` (developer.workday.com "Reference: String Member Functions"; deployed 2026-11-01). Counting a substring: `(text.length() - text.replace("\\nADD,", "").length())` = 5 × occurrences.

## Data and binding pitfalls

- **Several widgets bound to the same outbound field:** which value wins isn't defined. Bind each field from one place; when a value depends on several widgets, compute it once in the endpoint's `values` list.
- **Don't save a picker's WID into a field that's displayed as text.** Save the selection's descriptor for display and the WID in its own field.
- **A grid cell `instanceList` filled with a literal `instanceList` whose entries are scripts renders blank on an EDIT page** (confirmed live 2026-10-31: every such column on a withdraw page was empty). A `values`-scripted one shows as plain text. On edit pages use `text` cells for display.
- `relatedTask` / instance links on `instanceList` render **only on VIEW pages** (developer.workday.com instanceList reference). On EDIT pages they render as plain text (`values` alone even renders blank; use `values: []` + `multiSelect: true` + `selectedValuesAndDescriptors` for a read-only list). `instanceList` must be a literal array (a script string fails the build); use `instanceListLoopTag` for a variable list. An edit-page grid needs `doNotAdd`/`doNotRemove: true` to hide the +/− icons (`readOnly: true` doesn't).
- After OK, an edit page returns to the app home unless a flow or conclusion page says otherwise.
- `context.orchestrateId()` (developer.workday.com "Reference: Context Global Functions") gives the orchestration instance ID: storable as text, not a tenant instance.
- Reports: one report can take several `defaultSecurityDomains`. Delete unused WQL components and reports as you go: apps have tight limits.


### Sub-orchestrations (confirmed live 2026-11-04)

- **File:** `orchestration/<Name>.suborchestration` (App Hub's own extension, seen by saving one in Orchestration Builder and downloading the app with `wdcli app download`). Nothing else registers it. The same JSON saved as `.orchestration` is ignored ("no orchestration with name: X found").
- **Shape** (flowVersion 3.7.0): flow type `.maya.FlowSubflow`; start `StartSubflow` {`parameters`: List<`ExprParameter` {name Identifier, type Type, expr Opt<Expr<Opt<Any>>> = null}>}; end `EndSubflow` {`exports`: List<`Assignment`>} (may be empty); `securityDomains` null (the callers carry the domain); default credential `AccessTokenFromInitiatingUser`.
- **Inside**, an input is `data.start.<input>`.
- **A sub-orchestration can call another one** (doc.workday.com "Modular Orchestration Design"; confirmed live 2026-11-05: an async parent → per-row sub → shared audit-record sub wrote its records). A business-process-triggered orchestration calling a sub is **(unverified)**.
- **One shared step for many callers:** when the callers' bodies differ (an audit record's fields), give the sub one String input per field, have each caller pass `""` for the ones it lacks, and inside the sub make Boolean `has<Field>` flags (`data.start.x.isEmpty().not()`) for `{{#if}}`, so empty fields stay out of the record as before.
- **The call step:** `CallSubflow` {name, isDisabled, errorHandler, `subflowId`, `parameters` List<Assignment> (one per input, same name and type), `executionDelay` Opt<`SubflowExecutionDelay`> = null}. **`subflowId` is the sub-orchestration's 32-hex `id`**; its name is rejected ("Invalid Subflow Reference ID"). An output is `data.<callStep>.<export>`. A call inside a Loop works.
- Proven with a probe: caller passed `text = "hello"`, the sub exported `"echo:".append(data.start.text)`, the caller returned `{"echo": "echo:hello"}`.
- In the builder: an open orchestration's left panel → **Suborchestrations +**; the caller gets it from Components → Suborchestrations → **Call <name>** (drag only; automated drags don't register). Docs: doc.workday.com "Modular Orchestration Design" (no Trigger Business Process or RaaS steps inside).
- **Run errors name the sub-orchestration's step:** "Completed with error: ... @[<Sub>.suborchestrationSteps.<Step>]" (the parent's own steps show as @[<Parent>.<Step>]), which makes a cheap test: launch the parent with input only Workday rejects and check the error comes from the sub. For a few minutes after a deploy, launches can run either the old or the new version of an orchestration (seen 2026-11-04: one run had AddShellOrg new and AddShellOrgPattern old, the next the other way round; consistent after ~5 minutes). Wait before concluding a change didn't deploy.
- Repo pattern: a final build step (`tools/extract_subflows.py` in one app) that moves a block two orchestrations share into the sub-orchestration, turns everything the block reads from outside into inputs, and replaces the block in each parent with the call. Build steps that patch the parents in place by step name must see the full files, so keep the full copies and restore them at the start of the build (`--restore`), extracting again at the end. Add a static check that every `subflowId` matches a `.suborchestration` id and the inputs match.

## Renaming an app or an orchestration (live 2026-11-06)

- **Orchestration names take letters, digits and underscores only.** Orchestration Builder keeps Done disabled for a name with a hyphen. A team naming standard written with hyphens (e.g. `IORC-0037-...`) becomes `IORC_0037_...` for the orchestration; the app name can keep hyphens.
- **Rename = same id, new `name`, new file name.** Keep the orchestration's 32-hex `id` (and every sub-orchestration's, which callers use as `subflowId`); a build step that derives ids from names must keep hashing the old name. App Hub then lists the same orchestrations under the new names.
- Update every launch URL (`/<Name>/launch`), tests and docs in the same change, and check nothing still uses an old name.
- **Tenant setup stores orchestrations by name:** a business process Orchestration Launch Configuration keeps "Orchestration Name" as text, so after a rename BP-triggered runs stop. It has no edit action: in Configure Orchestrations use the Orchestration prompt → **Create Orchestration Launch Configuration** (pick the renamed orchestration and the BP type), select it on every action row, OK (live 2026-11-06). External Cards lose their Home Card orchestration the same way (the field shows empty): Home Cards Workspace → the card → Edit → pick the renamed orchestration → OK (live 2026-11-06).
- **App display name:** developer.workday.com → Apps → the app → Related Actions → **Rename App**. The manifest `name` doesn't change the console name. The reference ID never changes.

## Orchestrations — synchronous page limit is 25 seconds

A **synchronous orchestration launched from a PMD page** has a **25-second total timeout** (overrides the orchestration's own 5-minute sync limit). Any orchestration that loops over many records (e.g. bulk creating/updating 50+ objects) will hit this limit and apply only partial work with no error shown to the user.

For bulk operations:

- Use **FlowAsync** (`"type": ".maya.FlowAsync"`) instead of FlowSync
- Create a **status business object** the page can poll
- Use **BatchLoop** with `SizeBasedBatchStrategy` to control chunk size
- The async timeout is 48 hours; production process limit is 60 minutes

## Orchestrations — no Excel parsing node

There is **no Excel parsing node** in the Workday Extend orchestration toolkit. File ingestion examples in the official DevRel corpus all use **CSV** (via `asCSV()` and `CsvFormat`/`CsvColumn` nodes). Treat XLSX upload parsing as unproven in orchestrations until demonstrated in a specific tenant release.

## Platform limits reference

Checked against developer.workday.com "Limits on Extend App Components", "Orchestration Runtime Limits", "Limits on Presentation Components". Re-verify each release.

**Model limits:**
- 20 business objects per app
- 50 fields per business object
- 10 SINGLE_INSTANCE or MULTI_INSTANCE fields per object
- 25 instance fields targeting Workday-delivered objects per app
- 5 `enableReportingFromTarget` fields per app
- 5 indexable fields per business object
- 40 derived fields per business object
- 3 searchable TEXT fields per app (enforced across the whole app, not per object)
- 10 security domains, 5 business processes, 20 tasks, 10 reports, 5 attachment objects per app
- 30 MB attachment size

**Presentation limits:**
- 24 seconds per endpoint
- 60 seconds per PMD request total (load + submit + remote validation combined)
- 30 outbound endpoints per PMD
- 30 non-deferred inbound endpoints
- 25 MB endpoint response
- 75 pages per app
- 100 KB per .pmd / .amd / .smd / .pod / .script file
- PMD script: 5 seconds CPU, 25 call frames, 2 nested module levels
- Labels: 255 characters max
- fileUploader: 10 MB per file, 5 files max; XLSX is not in the default allowed types

**Orchestration limits:**
- 25 seconds when a page triggers a synchronous orchestration (page-side limit)
- 5 minutes for a standalone synchronous orchestration
- 48 hours asynchronous
- 60 minutes per process in production; 45 minutes in other environments
- 31 recursive synchronous self-calls
- 300 steps per orchestration
- 150 orchestrations and sub-orchestrations per app
- 200 MB in-memory
- 20 MB launch message

**Data access limits:**
- REST collections: 20 rows default, 100 rows maximum per request — always pass an explicit limit
- WQL: 1,000,000 rows per query, 10,000 per page, 5-minute timeout via api.workday.com
- RaaS: no pagination
- API throttling: HTTP 429 under load — add RetryPolicy with BackOff in orchestrations


## CI/CD — deploying with GitHub Actions and wdcli

A typical pipeline: on push to `main`, run static checks, log in, upload to App Hub, deploy to the dev tenant with `wdcli`, then run smoke tests. After every push, check the run (`gh run list`, `gh api .../runs/<id>/jobs`) and confirm `conclusion: success` before saying anything is deployed. The project's own pipeline details (secret names, app ID, tenant) are in its notes file.

- **Put the static checks first**, before any login step, so a code error is reported even when the tokens have expired.
- **Strip quotes from pasted token secrets.** A secret pasted with its JSON quotes gave `Authorization: Bearer "…` and AOS answered "The resource requires authentication, which was not supplied with the request" (2026-11-02); the workflow now removes quotes and whitespace from token variables first.
- **The tenant token lasts 1 hour; the platform token 8 hours.** Decoded from wdcli's config (2026-11-02): `wcpTenantAccessToken.<tenant>` (the `WD_DEV_TOKEN`-style secret) has `exp - iat` = 3600 s, `wcpAccessToken` 28800 s. So a CI deploy needs tokens refreshed within the hour, and most token-step failures are this expiry. A run that fails in under 20 seconds at the token step is an expiry, not a code error: don't revert or change code; follow **Deploy decision guide** below.
- **A 401 at the deploy step (`.../aos/v1/deploy`, "The supplied authentication is invalid") while the expiry checks pass** means a revoked or invalidated session: refresh both tokens.
- **A token copied from an old config.json can expire mid-deploy.** wdcli then fails with "Cannot read properties of undefined (reading 'success')" instead of a 401. Rerun straight after updating the secrets.
- **`wdcli app upload` uploads the whole folder you give it.** From a repo root that also holds docs, tools, tests and image files, the upload was refused with only "Unable to upload app. Error" (2026-11-02; the repo had 30 PNGs in `brand-assets/`, and App Hub allows 20 images per app). Add a **`.wdignore`** at the app root (gitignore syntax, read by wdcli) listing everything that isn't the app (`docs/`, `tools/`, `test/`, `.github/`, image folders, `*.md`); the next CI upload went through. `wdcli app upload --dry-run -o app.zip` writes the archive without uploading, to check what's included. On Windows PowerShell there's no `unzip`: use `Expand-Archive`.
- **Reading App Hub build errors without the browser** (2026-11-05): `wdcli app builds logs <buildId> --ci -f json`. The build ID is in the upload output (`.../builds/<32 hex>`). Have CI run it when the upload fails and print the ERROR lines. A script error reads "There's a PMD Scripting syntax error in <Tag>:<event>: Parsing Error encountered in: <script>"; a static check that brackets balance in every `<% %>` script (string literals blanked first) catches the commonest cause.
- **A fileUploader has no `onChange`**: its events are `onFileAdd` / `onFileRemove` (developer.workday.com "fileUploader", 2026-11-05); `<uploader>.clearError()` in `onFileAdd` clears an OK error once a file is added (live). To add a file in browser tests, set the page's `input[type=file]` `.files` from a `DataTransfer` and dispatch `change`.
- A healthy upload + deploy takes about 1–3 minutes.
- A run stuck at "in_progress" with every step completed (job conclusion success) did deploy; it can't be cancelled or rerun. A failure at the system-user login step in ~20 s can be transient; rerun once.
- **GitHub CLI in a sandbox:** `gh workflow run` may fail when GraphQL is blocked; dispatch with REST instead: `gh api -X POST repos/<owner>/<repo>/actions/workflows/<file>.yml/dispatches -f ref=<branch> -f 'inputs[task]=<value>'`. Job logs may be blocked or truncated: write the full test output to `GITHUB_STEP_SUMMARY` and read the run's Summary page. App Hub build errors show on the run page (Summary → "Upload Failure").

### Deploy decision guide (what to ask the user to run)

Placeholders: `<appRef>` = the app's reference ID (in the project notes file), `<tenant>` = the tenant alias, `<owner>/<repo>`, `<app>` = a short folder name. The user runs these in **Windows PowerShell**; on Windows wdcli keeps its config at `$env:LOCALAPPDATA\@workday\wdcli\config.json` (not `~/.config`). Give the commands as one block they can paste, with the real values filled in.

**1. GitHub run failed at the token step (expired tokens).** Ask the user to log in once and push both tokens straight into the repo secrets. With `gh` installed the tokens never pass through the chat:

```powershell
wdcli app deploy <appRef>    # answer y to "Access token has expired ... log in?", finish the browser login
$c = Get-Content -Raw "$env:LOCALAPPDATA\@workday\wdcli\config.json" | ConvertFrom-Json
$c.wcpTenantAccessToken.'<tenant>' | gh secret set WD_DEV_TOKEN -R <owner>/<repo>
$c.wcpAccessToken | gh secret set WD_WCP_TOKEN -R <owner>/<repo>
```

Without `gh`: `$c.wcpTenantAccessToken.'<tenant>' | Set-Clipboard`, paste into the secret on GitHub (Settings → Secrets and variables → Actions), then the same for `wcpAccessToken`. Then the user says "refreshed" and I rerun the workflow at once (the tenant token has an hour). The `wdcli app deploy` in the first line already redeploys the version in App Hub, so if the latest commit had reached App Hub the app is live even before CI reruns.

**2. GitHub can't upload, or a refresh isn't worth it** (the user is about to leave, the tokens keep expiring, CI is broken for another reason). I build a zip of only the app folders (`git archive --format=zip -o <app>-app-upload.zip HEAD appManifest.json cards model orchestration presentation`, leaving out any that don't exist), send it, and give:

```powershell
New-Item -ItemType Directory -Force "$HOME\<app>-upload" | Out-Null
Set-Location "$HOME\<app>-upload"
Remove-Item * -Recurse -Force
Expand-Archive -Path "$HOME\Downloads\<app>-app-upload.zip" -DestinationPath . -Force
wdcli whoami                 # optional: confirms the CLI is signed in
"." | wdcli app upload       # "." answers the "path to the app directory" prompt
wdcli app deploy <appRef>    # answer Yes to the default tenant, y to a login prompt, N to "open in browser"
```

- `wdcli app deploy` needs the **full** reference ID (a partial one gives "Unable to find app with reference ID").
- The Version ID stays the same from upload to upload; the **Build ID** changes. A deploy table with `Success true` and the new Build ID means the upload just made is live.
- A browser download of the same name may become `<app>-app-upload (1).zip`: tell the user to delete old copies first, or adjust the path.

**3. Upload works but the App Hub build fails (build errors).** I fix these myself; don't hand them to the user to edit:
- Read the error (CI run Summary → "Upload Failure", or the build log on developer.workday.com for the app).
- Fix it in the repo, run the static checks, and add a static check for that error so it can't recur.
- If the fix has to be made or confirmed in Workday's tools (App Builder Code mode, Orchestration Builder), do it in the browser myself first. Saving there writes to App Hub, so the repo must get the same change, or the next upload undoes it. Ask before Deploy or Save All in Orchestration Builder.
- Then redeploy by route 1 or 2.

**Never ask the user to paste tokens into the chat**, and never repeat ones they paste. If they do, note that the tenant token is good for an hour and the platform token for 8, and that the `gh secret set` route avoids it next time.

## Promotion: what can't change after an app leaves dev

Source: a colleague's Extend skills (2026-11-07), citing developer.workday.com "Concept: Update Model Components", "Reference: Allowed Updates After Extend App Promotion", "Reference: Promotion Deadlines for Extend Apps with Model Components", "Reference: Limits on Model Components", "Reference: Model Component Error Codes". Check those pages before promoting.

- **Never, even in dev:** change a model component's `id`, swap two fields' ids, change a field's `type`, or reuse a field `id` that was used before. Ids are integers 1–32767; `<appReferenceId>` + a business object's `name` must stay within 124 characters (B202).
- **In a dev tenant, deleting a model component or field (or giving a field a new id) deletes all its data** on the next deploy. Settle the model in dev before the first promotion.
- **After promotion (implementation, sandbox, production) you can't:** delete business objects, attachment objects, business processes or regular fields; remove or change the security domains on attachment objects or business processes; remove all actions (or only `SEND_BACK`) from an approval step; turn `enabledForPageSecurity`, `enabledForOrchestrationSecurity` or `enableReportingFromTarget` from true to false.
- **Still allowed after promotion:** add components, fields and domains; rename a business object, field or collection, change labels and `defaultSecurityDomains`; change `enableIndex`, `enableSearch`, `isPurgeable`, `useForDisplay` (TEXT), `decimals`, `precision`, `secureByTarget`; remove or change derived fields, reports, tasks and profile groups; rename a security domain (update every reference).
- **Promotion deadline:** model components reach non-dev tenants in the Friday-night weekly service update. Promote by Thursday 11:59:59 pm local region time outside the US (US: Thursday 11:59:59 pm Pacific for WD10/WD12/WD104 and Workday's own data centres, 08:59:59 am Pacific for other US public-cloud ones); later than that waits a week. `wdcli app promote <ref> -l implementation|sandbox|production [--latest-version] [-n "<notes>"]` moves one level at a time.
- **Tenant reports that help:** Extend Object Instance Count (instances against the tenant limit), View Business Objects Available to Extend (which Workday objects allow `target`/`secureByTarget`), View Security for Extend Related Instance (an instance's security context), Business Object Details.
- **More than about 100 records to load or extract:** an inbound EIB with File Type "Extend Spreadsheet Template" (needs Modify on the app's domain policy in App Manager, then Activate Pending Security Policy Changes), or an outbound EIB over a web-service-enabled custom report.

## More wdcli commands, and Arcane Auditor

Source: the same colleague's skills (wdcli 1.9.x reference); the CI parts confirmed in this repo's deploy workflow 2026-11-07.

- `wdcli app validate -d <dir> [--ci -f json]` checks PMD/AMD/SMD/model components against App Builder's rules before an upload (orchestrations aren't checked). Reported to catch an unresolved `taskId` and a duplicate PMD `id` (e.g. a `_backup.pmd` copy that kept its id). **What it needs (CI, 2026-11-07):**
  - **The developer's own token, not the system user.** As the ISU it fails "App manifest organizationId does not match user's organization". Pass the platform token as `WDCLI_AUTH=<wcpAccessToken>` (wdcli's own override); a config file with just `wcpAccessToken` gave "Not logged in".
  - **`appManifest.json` must carry `organizationId`** = the account's organization UUID (wdcli compares it with `getOrganizations`' `organizationUuid`; `wdcli account list` doesn't show the UUID). App Hub's copy of the manifest has it: `wdcli app download <ref> --latest-version -d <tmp>`, then validate a copy of the app with that field added. A manifest without it always fails this check.
  - In this app it passes with WARNINGs only: `isCollection` endpoints and "endpoint declared but never used" (the latter misses some uses; see App Hub build warnings).
- `wdcli app upload --fail-on-build-timeout` exits non-zero when the build outlasts the CLI's wait (by default a still-running build exits 0); `--no-build-wait` returns straight away. In use in CI since 2026-11-07.
- `wdcli app versions <ref>`, `wdcli app builds <ref> [--latest-version]` (build history with SUCCESS/FAILED), `wdcli app info <ref>`.
- `wdcli app deploy <ref> -t <tenant alias> --latest-version` names the tenant without the interactive prompt (needs `wdcli tenant login <alias>` first).
- `wdcli tenant open <alias> -l app-manager -r <ref>` opens App Manager on the app; `wdcli config set defaultTenantAlias <alias>`.
- `wdcli app preview -d <dir> --skip-open` serves the UI locally (port 9329), Extend pages only.
- **Arcane Auditor** (Workday DevRel's code review tool, github.com/Developers-and-Dragons/ArcaneAuditor; binary `ArcaneAuditorCLI`): `ArcaneAuditorCLI review-app <dir> --agent` prints JSON findings (`rule_id`, `severity` ACTION/ADVICE, `fix_strategy` actionable/human_review, `location.path` as a JSONPath, `target_text` + `suggested_replacement`). `--config development` picks its development rule profile; `list-rules` / `describe-rule <RuleId>` explain each rule. Exit codes: 0 clean or ADVICE only, 1 ACTION found, 2 usage error, 3 crash. Runs locally, no network. For an `actionable` fix inside a `<% %>` script, replace only `target_text`, never the whole field.
  - **In CI (2026-11-07):** the repo isn't pip-installable (setuptools "Multiple top-level packages discovered in a flat-layout"); use the release asset `ArcaneAuditor_linux_CLI.tar.gz` (v2.0.0, with a `.sha256`), binary `ArcaneAuditorCLI`. With `--agent` its parser warnings come before the JSON on stdout, so write `--format json --quiet --output <file>` instead.
  - First run on this app: 551 ACTION and 3,342 ADVICE over 51 files, so it runs warning-only. Biggest ACTION groups: EndpointFailOnStatusCodesRule 121, OnlyMaximumEffortRule 119, WidgetIdRequiredRule 96, GridPagingWithSortableFilterableRule 89, NoIsCollectionOnEndpointsRule 71, OrchestrationApiStepErrorHandlerRule 37, OrchestrationGlobalErrorHandlerRule 13. Weigh the orchestration error-handler rules against "A global error handler that only logs swallows failures" above before following them.
  - Its script parser fails on a backslash string literal such as `.replace('\\', '')` (the WQL injection strip) and skips that script with a warning.
- **Same skills, unverified layout notes:** a `layout` object on `section`/`fieldSet` (`density`, `alignment`, `horizontalSizing`, `labelPosition`) needs an explicit `labelPosition` or labels move to the side, and isn't allowed inside a grid; in a horizontal `section` each column needs more than about 280 px or the row stacks; `columnWidthRatios` must have one entry per child; `text`/`textArea` take a `placeholder`. Write PMD/JSON as UTF-8 **without** a BOM (Windows PowerShell's `-Encoding UTF8` adds one and App Builder rejects the file). Note that skill writes `pageType` lowercase; keep it uppercase here (see Edit pages).

## Testing an Extend app

- **Layers:** static repo checks (no tenant; block the upload), a read-only smoke suite after every deploy, a write suite run by hand, a cleanup suite (dry run by default), and opt-in suites for changes that aren't live yet (e.g. ISU lockdown). Keep them in one runner so they share helpers and one results format.
- **Static checks are cheap insurance:** encode every pitfall in this file that has bitten you (pageType case, `_` attributes, hidden OK with no editButtonBar, unresolved taskIds, missing orchestrations, BP routes without AMD tasks, card parameter/quote rules, protected keys inside `presentation`, size limits, forbidden test text). List known exceptions with a reason so they warn instead of fail.
- **Live tests can call the same APIs the pages use** (BO REST, WQL, BP events, and orchestration `POST .../orchestrations/<Name>/launch`) with the developer's PKCE token. They exercise orchestrations, not page scripts; page behaviour still needs a manual checklist or browser tests.
- **Verify every write through its side effect**, e.g. the audit record the orchestration writes only after success, matched by record ID (timestamps can tie). Check the record's type, action and key fields, not just that something appeared.
- **Use the tenant's local date for effective dates in tests**, not the UTC date: after 5 pm Pacific the UTC date is tomorrow, Workday schedules the change for tomorrow, and a readback that expects it now fails (and leaves the change behind). Seen 2026-10-31.
- **WQL can lag a change by more than 20 seconds.** Poll for up to a minute or two before reading back, and if the readback never shows the change, say plainly what was left behind.
- **Plan test data you can't delete:** orgs can only be inactivated, BP-linked records can't be deleted, and a role assignment test changes a real role (add then remove). Use short, readable, clearly marked names (e.g. `...:TEST:CI:RUN<n>`), document what each run leaves, and give cleanup a dry-run mode that lists what it would touch next to what it keeps.
- Check that records agree with their BP events (status vs event outcome) as a tamper check.
- Run the write suite before sign-offs or after risky changes, not on every push: it is slow and leaves data.

## Working in the Workday UI with browser automation

- A narrow window turns prompts into full-screen pickers; resize to about 1600×1000 for BP and definition grids.
- Related-action menus open their sub-menus on hover.
- Date fields need per-key input (e.g. key presses "1 0 3 0 2 0 2 6"), not a pasted string.
- Rich-text editors (ProseMirror) ignore scripted selection and key events. Clear the underlying textarea first, then dispatch a synthetic `paste` ClipboardEvent with `text/html` on `.ProseMirror`; formatting is kept.
- Find an org with the search prefix `org: <name>`, a BP definition with `bp: <name>`.
- Changes to security policies and permission grants are for the person to make, not the assistant.
- An Extend app page opens at `https://<tenant host>/<tenant>/d/wday/app/<appId>/<appId>/<taskId>.htmld?param=value`, e.g. `.../errorPage.htmld?errorCode=404`. A `#/task` hash on the app root doesn't navigate.
- A page's text is readable with `document.body.innerText` after ~10 s; cards render lazily, so scroll a card into view before reading it.
- **Timing a page:** in a hidden or background browser pane, cards can take 45 s or more to draw, which isn't the app. Time the server instead: `GET /wday/app/<appId>/<tenant>/<appId>/<taskId>` with `Accept: application/json` returns the page, and each card's `contentUri` returns its content (confirmed 2026-11-01: page 0.9 s, cards 0.1–0.2 s).

## Patterns from Workday's sample apps (GraphQL, Extend Cards, Profile Groups, more widgets)

Source: 36 Workday sample apps exported from Workday (2026-11-02): vehicleRegistration, createAWorkEvent, workFromAlmostAnywhere, pmdWidgetDictionary, chartDictionary, capitalProjectPlanning and others. These patterns deploy in Workday's own samples but **haven't been tried in this tenant yet**: treat each as (unverified) until a live test, and check the developer site before relying on exact attribute names.

### GraphQL queries (`.graphquery`)

- Files live in `presentation/graphQueries/<id>.graphquery`: `{ "id", "parameters": [...], "query": "<GraphQL text>", "variables": { ... } }`. Parameters are interpolated in `variables` with `<% name %>`, like a WQL Query component.
- AMD data provider: `{ "key": "workday-graph", "value": "<% `{{apiGatewayEndpoint}}/graphql/v1/` %>" }` (one sample used `"graph"` with `apiGatewayEndpoint + '/graphql/v1/'`).
- Inbound endpoint: `{ "name": "me", "baseUrlType": "workday-graph", "httpMethod": "POST", "authType": "sso", "graphQuery": { "queryId": "me", "parameters": { "vehicleId": "<% queryParams.vehicleId %>" } } }`. Results come back under `data.<field>`: `me.data.worker.data[0].primaryJob.location.workdayID.id`.
- Outbound (create/update/delete) uses the same `graphQuery` on an outbound endpoint, with `variables` built from widget values (`"createVehicle_input": { "color": "<% vehicleColor.value[0] %>", "location": { "id": { "id": "<wid>", "type": "WID" } } }`).
- App business objects appear in the schema with the **app reference ID as a prefix**: query `<appRef>_<Object>(dataSource: {<appRef>_<collection>: {}} where: {workdayID: {in: [{id: $id}]}})`, mutations `<appRef>_create<Object>` / `_update<Object>` / `_delete<Object>`, input types `<AppRef>_<Collection>Summary_CreateInput` (first letter capitalised). References are `{ "id": { "id": "<wid>", "type": "WID" } }`.
- Useful because a `where` filter replaces `isCollection` + paging (see the isCollection performance warning), and one query can return nested instance fields (nested fields not yet tried live). Example worker query: `query { worker(dataSource:{ processingWorker:{}}) { data { descriptor workdayID {id} } } }`.

**Confirmed live (2026-11-04, one dev tenant; developer.workday.com "Run Graph API Queries on a Page", "Graph Query Components", "Pagination of Graph API Query Results", "Query Filters"):**
- A `.graphquery` in `presentation/graphQueries/` deploys through App Hub, and an inbound endpoint `{ "baseUrlType": "workday-graph", "httpMethod": "POST", "authType": "sso", "graphQuery": { "queryId", "parameters" } }` (no `url`) works on a page. Provider value used: `` <% `{{apiGatewayEndpoint}}/graphql/v1` %> ``.
- **Every field of an app business object is filterable** in `where` (`String_Filter`: eq, neq, in, notIn, contains, startsWith, endsWith, empty; `Instant_Filter` adds gt/gte/lt/lte), not just the 5 indexed ones REST allows. **`orderBy: {field: DESC}`** (enum `ASC`/`DESC`) sorts on the server, which fixes REST collections coming back oldest first.
- Field names match REST; the record id is `workdayID { id }` instead of `id`, and empty fields come back as `null`. Aliases work (`r: <appRef>_<Object>(...)` → `endpoint.data.r.data`, `.data.r.total`).
- `limit` is 100 at most (default 20), like REST.
- **Offsets need a first request without one.** A request with `offset > 0` that runs before the same query ran with offset 0 returns HTTP 200 with `"Requests with offsets need to be run after an initial request without an offset"`, and **the page shows an endpoint error even without that code in `failOnStatusCodes`**. So later page endpoints must reference the first one (e.g. read its `total` in their `offset` parameter), which makes them wait for it. A test paging 624 workers (offset 0 then 100) confirmed no repeated rows.
- **Errors come back as HTTP 200** with `data.<field>: null` plus `errors`. Guard reads: `(!empty(x.data) && !empty(x.data.r)) ? (x.data.r.data ?? []) : []`.
- Speed: warm page loads matched REST (about 0.8 s); the first call after a while was slower (2-7 s).
- Users need the **Workday Graph API Applications** domain (System). In one dev tenant its Report/Task View already included All Users; check the policy before promoting to another tenant.
- Introspection (`__schema`, `__type`) works with a normal user token and is the quickest way to list an object's criteria and order fields.
- A build pass that rewrites expressions must be **idempotent**: one that only matched the original text silently skipped its own later changes on the second run (a page showed every record 5 times).

### Extend Cards on Workday pages (Cards, Card Tenant Settings)

Different from the Page Configuration Cards in `presentation/cards/*.card`. They're cards an administrator places on Workday's own Home page or hubs.

- `presentation/cards/<id>.carddefinition`: `{ "id", "presentation": { "type": "inlineCard", "header": { "type": "cardHeader", "title", "subtitle", "indicator": {"label", "color": "GREEN"}, "icon" }, "body": { "type": "simpleCard" | "listCard", ... }, "footer": [ { "label", "taskReference": {"taskId"} } ] }, "endPoints": [ ... ] }`. A card has its own inbound endpoints. Indicator colours are UPPERCASE here (`GREEN`, `BLUE`).
- `listCard` body: `{ "type": "listCard", "title", "subtitle", "on": "<% list %>", "as": "row", "template": { "label", "value", "secondaryValue", "secondaryValueWidth": "MEDIUM" } }`.
- Register the card as an AMD task: `{ "id": "createRequestCard", "routingPattern": "/createRequestCard", "page": { "id": "createRequestCard" } }`. The task's `page.id` is the `.carddefinition` id (there's no .pmd), so static checks that resolve pages must accept card definitions.
- **A card definition may have at most 2 inbound endpoints** (App Hub build error "has exceeded the maximum of 2 inbound endpoints", 2026-11-02). Filter on the server instead of paging (e.g. a SINGLE_INSTANCE query param such as `?requestedBy=<wid>`), or use one count + one page.
- Card body scripts follow the `.card` rule: double-quoted string literals only. A card can't `include` page scripts, so repeat any helper logic inline.
- **Extend Cards (`.carddefinition`) can't go on Workday Home.** App Manager → app → Cards → Configuration offers Home Cards Workspace, Journeys Workspace, Maintain Hubs and Maintain Search Topics, but Home Cards Workspace → Add Card doesn't list them (live 2026-11-02). Workday docs: Extend Cards go on **Workday-delivered hubs that already have card sections** (Maintain Hubs → hub → View Overview Configuration → Edit → Customize Sections and Cards → add row; security Set Up: Tenant Setup - Hub). A **Workday Home** card is a different thing: an orchestration of type "Workday Home Card" (Create Workday Home Card step), then the Create External Card task (developer.workday.com doc mwd1629844754304; Home needs Journeys outside WCP dev tenants). **Prerequisites (doc.workday.com "Steps: Create External Home Page Cards"):** Workday Journeys access, People Experience and the Journeys functional area enabled, the Set Up: Custom Card and View: Custom Card policies, then Home Cards Workspace → Add Card → Create External Card picks the orchestration. Workday plans to retire External Cards for Journeys. In one dev tenant (2026-11-02) the app's Create Orchestration page offered only Synchronous, Asynchronous, Workday Business Process and Workday Integration System (the list comes from the server per app), but **a Home Card orchestration written in code uploads and opens in Orchestration Builder**:
  - Shapes from the builder's own type schema (developer.workday.com flowbuilder bundle): flow type `.maya.FlowWorkdayTodayCard`; start `StartWorkdayTodayCard` (no properties); step `CreateWorkdayTodayCard` {name, isDisabled, errorHandler, `source` String ("POWERED BY"), `title`/`subtitle`/`linkText` Expr String, `linkDestination` Expr **Url**}; end `EndWorkdayTodayCard` {`refreshFrequency` Int seconds (0 = don't cache … 2419200), `card` Expr Json}.
  - The card step's output is **`card`**: end `card` = `data.<CardStep>.card` (the builder's data picker; `.json` fails the build).
  - **No `securityDomains`** on this type (App Hub: "Security domains can only be defined for Sync and Async orchestrations").
  - Default credential `AccessTokenFromInitiatingUser`, so `/workers/me` is the viewer. Builder steps per doc mwd1629844754304 (dev tenants: no Journeys needed).
- `cards/<Name>.cardtenantsetting` at the app root: `{ "id": 1, "name", "label", "securityDomains": [...], "routePath": "/createRequestCard" }`. This is what an administrator picks when adding the card in Workday.
- None of the samples uses **Profile Groups**; see the next section.

### Profile Groups (model profile groups)

Source: developer.workday.com "Profile Group", "Add Profile Groups", "Profile Group Best Practices and Considerations", "Configure Extend Profile Groups in the Tenant", "Add Context-Free Tasks" (read 2026-11-02); Workday admin guide "Steps: Set Up Profiles and Profile Groups". Not yet tried in this tenant.

- **What it is:** a new section in the left pane of a Workday profile (Worker Profile, Organization, Position Restriction Profile and so on), like Job or Compensation on a worker. Its content is the app's **context-free model tasks** (each opens an app page) and **model reports**, shown as tabs.
- **Component (Code mode):** `{ "id": 1, "name": "myCharityProfile", "label": "My Charity Profile", "profile": "WORKER_PROFILE", "tasks": ["CharityHome"], "reports": ["AllCharities"] }`. It needs at least one task or report, one `profile` only, and the tasks and reports must already exist in the app. Up to **10** profile groups per app. To use the same content on two profiles, make two groups with different names.
- **Which profiles:** run the tenant report **View Profiles Available to Extend**; its Target Attribute Name is the `profile` value. One dev tenant listed 31 (checked 2026-11-02), including `WORKER_PROFILE`, `ORGANIZATION`, `SUPERVISORY_ORGANIZATION`, `POSITION_RESTRICTION_PROFILE`, `JOB_PROFILE`, `COMPANY`, `COST_CENTER`, `STUDENT`, `COURSE_SECTION`.
- **Context-free only:** a context-free task is one with no business object on it, so the page it opens is **not told which worker or organization the profile belongs to**. A group on the Organization profile shows the same page whichever organization you're on. Whether a model report can be filtered by the profile's subject isn't documented for Extend (the admin guide requires a prompt for the object on custom reports) **(unverified)**.
- **Tenant setup after deploy (administrator, Set Up: System domain):** App Manager → Configure on the app → Profile Groups grid → Configure → pick the profile, tick **Display in Profile**, set the order. Then **Configure Profile Group** → pick the group → Display in Profile → + → add the allowed tasks and reports in order. Check by opening a profile (e.g. a worker's) and looking for the group in the left pane.
- **Limits:** users need the domain permission for each task and report. Long Name/Label values can be cut off and can stop tasks rendering. Pages with nested tabs may not render inside a profile group.
- **Tenant switch-on (live 2026-11-02):** App Manager → app → Configure → Profile Groups → Configure → tick **Display in Profile** → OK. The Configure Profile Group form only lists **reports** (its grid's column is Report); the group's tasks come from the `.profilegroup` file. Users still need the group's tasks' domain to see the section.
- **Repo file:** `model/<Name>.profilegroup` with `{ "id", "name", "label", "profile", "tasks": [<model task names>] }` (`reports` optional). Deployed 2026-11-02; App Manager → Configure then lists it as "<label> for Worker Profile". The tasks are `model/<Name>.task` files with no `businessObject` (context-free), a `routePath` to an app page and `securityDomains`.

### Widgets and attributes not yet tried live

- **Page errors from script:** `presentation.applicationExceptions: [{ "type": "applicationException", "severity": "ERROR", "message": "...", "render": "<% pageVariables.x %>" }]`.
- **Extra submit buttons:** `editButtonBar` with `editButtons: [{ "type": "editButton", "id", "label", "buttonType": "PRIMARY", "ignoreRequiredFields": "true" }]` (e.g. Save as Draft and Submit; the clicked button's id is available to flows).
- **Run script from a button:** `pageActionButton` with `onClick` (no navigation, no submit).
- **Charts in a page (not a card):** `clusteredBarChart2`, `stackedBarChart2` (`categoryDataSet`, `secondaryCategory`, `measurementDataSets: [{name, value}]`, `barOrientation`, `hideChartControls`), `lineChart2`, `comboChart2`, `percentBarChart2`, `waterfallChart2`.
- **List and detail:** `listDetailHub` (`items`, `itemVariableName`, `navigationTemplate: {label, task}`): a hub whose left pane is generated from a list.
- **Repeated panels:** `panelList` (`panels`, `panelName`, `indexVariableName`), as an alternative to a grid for a few rich rows.
- **Others:** `radioGroup`, `externalLink` (`label`, `url`), `progressIndicator` (`value`, `maximumValue`), `congratulationsPopup` (`textCongrats`, `textSubmitted`, shown after a flow), `dynamicSection` (`data`, `dataVariableName`).
- **Business process history:** `bpExtender` with `bpTemplatedList` + `processHistory` / `commentHistory` templates; the sample fills them from an orchestration that reads the event's history and comments.

