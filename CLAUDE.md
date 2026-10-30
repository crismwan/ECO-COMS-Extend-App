# Workday Extend development

These preferences apply to **all** Workday Extend apps I work on (not any single project).

## This file is a guide, NOT the single source of truth

CLAUDE.md captures notes and findings from past sessions. It is incomplete and can be wrong or out of date. Do not treat it as authoritative, and do not keep retrying approaches just because this file suggests them.

When there is any confusion about the right solution (syntax, attributes, widget behavior, platform limitations, or a fix that isn't working):

1. **Check the Workday developer site first:** go to https://developer.workday.com/ and use the site's **search bar** to look up the widget, attribute, function, or error. Prefer the official docs over this file when they disagree.
2. **If the developer site doesn't answer it:** stop and ask the user. If I have an idea that goes beyond what CLAUDE.md says, describe it briefly and ask permission to try it before doing so.
3. **After confirming something new**, add it to the relevant section of this file and note where it came from (developer.workday.com page, live test, or user).

## Test data in the tenant

Never put the text "claude" (any casing) into anything entered in the Workday tenant — test org codes, pattern values, role names, comments, audit details. Use neutral test values such as `TEST:ORG:1029`.

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

The `guide` attribute places a **"?" tooltip icon** beside the widget label. It is placed as a sibling attribute on the widget definition:

```json
"guide": {
  "type": "guide",
  "id": "guideMyWidget",
  "title": "Tooltip Title",
  "text": "Tooltip body text explaining the field."
}
```

**Critical rendering limitation (confirmed via accessibility tree analysis):** The `guide` attribute on `text` and `date` widget types inside a `fieldSet` with `labelPosition: "side_align_left"` does **NOT** render a visible "?" icon in the Workday UI. The code deploys without errors and is accepted by the platform, but no guide button or icon element is inserted into the DOM — it is a **silent failure**. This applies to `text`, `date`, `number`, and similar read-only/inline field widgets in that layout context.

**What DOES render a guide icon:**

- `fileUploader` — confirmed to show the guide icon correctly.
- `dropdown` — renders the guide icon (confirmed working in production).
- `instanceList` — renders the guide icon (confirmed working in production).
- `textArea` — renders the guide icon (confirmed working in production).

**Mitigation for text/date fields:** Use `richText` banners with an `ⓘ` prefix (inline HTML) for visible inline guidance on sections containing text/date-only fields. These render correctly as informational banners.

**`richText` value format — two equivalent forms:**
- **Script-wrapped:** `"value": "<% '<span style=\"...\">text</span>' %>"` — required when the string contains dynamic expressions or variable interpolation.
- **Direct HTML:** `"value": "<span style=\"...\">text</span>"` — valid for purely static content with no PMD expressions. Both forms are used throughout this codebase and both deploy/render correctly.

```json
{
  "type": "richText",
  "id": "sectionDesc",
  "value": "<% '<span style=\"color:#374151;font-size:13px\">ⓘ Explanation of this section and its fields.</span>' %>"
}
```

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

**Color conventions used in this app:**
- `color:#B45309` — amber/warning tone
- `color:#0055B7` — blue/informational tone
- `color:#374151` — body text (dark grey)

**Do NOT** place two `richText` nodes in the same `fieldSet` expecting both to render — only the first will appear.

**Conditional visibility with `visible`:** For conditionally shown error/info messages, use `text` widgets (not `richText`) with the `visible` attribute. `richText` + `visible` inside a `fieldSet` may cause page-level errors. The safe confirmed pattern is `text` widgets with `visible` inside a single `fieldSet`:

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

**Scripting methods available on widgets:** `clearError()`, `clearWarning()`, `setError(String)`, `setWarning(String)` (non-blocking), `getLabel()` / `setLabel(String)`, `getValue()` / `setValue(Object)`, `getValueOutBinding()` / `setValueOutBinding(String)`, `isEnabled()` / `setEnabled(boolean)`, `isRequired()` / `setRequired(boolean)`, `isVisible()` / `setVisible(boolean)`, `isUpdated()` (changed by the end user), `isUpdatedByScript()` (changed by a PMD script).

`setVisible()` only works reliably when the widget is inside a `fieldSet`.

### Widget scripting — confirmed platform limitations (editWizard context)

**`setValue()` on `text` widgets is silently ignored** — calling `someText.setValue(...)` from an `onChange` handler produces no visible update. This is a confirmed platform limitation, not a coding error.

**`setLabel()` on `text` widgets does NOT update reactively** in `editWizard` step context — confirmed via live UI testing (2026-10-29). Even with real keyboard input triggering `onChange`, `setLabel()` calls execute without error but the label in the DOM never changes. The platform appears to render the label once at page load and ignore subsequent `setLabel()` calls on `text` widgets.

**What DOES work in onChange handlers:**
- `setError(String)` / `clearError()` — confirmed working for validation feedback
- `setWarning(String)` / `clearWarning()` — confirmed working
- `setEnabled(boolean)` — confirmed working (enable/disable a widget)
- `setVisible(boolean)` — confirmed working (show/hide, must be inside a `fieldSet`)

**For live preview / computed display fields:** Do NOT attempt reactive updates via `setLabel()` or `setValue()` on `text` widgets. Instead:
- Use the `value` expression (evaluated at page load and on the wizard's Summary review step) for correct display in the summary
- Use `setError()` to surface validation info (the only confirmed-working dynamic text display)
- Use `setWarning()` for non-blocking inline preview text below a field (e.g. "Generated name: X:CLW:ORG"). This IS reactive in onChange — confirmed working in editWizard step context (2026-10-29). **Important caveat from Workday docs:** The editWizard section also notes "No warnings support — calling `setWarning()` on a step page causes an error at submission time." If `setWarning()` on a disabled text widget blocks submit, fall back to `setError()` on a separate helper text widget, or use a `richText` banner.
- Use `richText` banners for static explanatory text about the naming format

**editWizard "Discard Changes?" dialog — ROOT CAUSE AND FIX (confirmed by live test 2026-10-29, supersedes earlier notes):**
- Cause: the wizard step page had `"standardEditButtonsHidden": true`. The wizard's Next saves the step via the step's own OK; with OK hidden, Next is treated as navigating away from a dirty page, so Workday shows "Discard Changes?" — and clicking Discard really does drop the entered values (Review step showed empty fields).
- Fix: do NOT set `standardEditButtonsHidden` (or a custom `editButtonBar`) on editWizard step pages. With it removed, Next goes straight to Review & Submit with all values preserved, no dialog. Confirmed on createShellOrgWizard and createShellOrgPatternWizard.
- Step pages may keep `cancelOverride`.

**Live preview fields in editWizard steps (confirmed live 2026-10-29):**
- `readOnlyText` + `setValue()` in `onChange` DOES update reactively in the step (e.g. Generated Organization Name, Pattern Name Preview).
- For a `values`-scripted dropdown or `instanceListLoopTag` dropdown, read the selected label with `<dropdown>.selectedEntries[0].descriptor` (guard with `!empty(<dropdown>.value)`). `.value.descriptor` raised "Property Error found: descriptor" on newShellOrg and returned empty on newShellOrgPattern.
- The Review & Submit summary does NOT show the setValue'd preview, nor a `value` expression re-evaluated with entered data — it shows the page-load value. Other fields (dropdown, text, date) display correctly. Open question.
- Don't use `setWarning()` on step pages (errors at submit per Workday docs).

## grid widget

Grid columns are NOT typed widgets placed directly in `columns`. Putting `"type": "text"`/`"number"` as the column type errors with "invalid tag" — those types are only valid INSIDE a `cellTemplate`.

- The grid declares `rowVariableName` (e.g. `"swagRow"`); cell bindings reference THAT alias, not `row` — e.g. `<% swagRow.name %>`.

- Each column is `{ "type": "column", "columnId": "...", "label": "...", "cellTemplate": { <widget> } }`.

- The actual widget (`text`, `number`, `dropdown`, `date`, `checkBox`, etc.) lives inside `cellTemplate` with its own `id` and `value`.

- **`required` goes on the `column`, NOT on the `cellTemplate` widget.** In a grid, mark a column required at the column level: `{ "type": "column", "columnId": "statusColumn", "label": "Status", "required": true, "cellTemplate": { ... } }`. (Outside a grid, `required` sits on the widget itself as usual.)

- Editable grid: start with `"rows": "<% [] %>"`; users add/remove rows via the +/trash icons. Set `isArrayOutBinding: true` to submit all rows as one outbound array.

- Read-only display grid: set `readOnly: true` on the grid.

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
  "title": "Create Shell Organization",
  "subtitle": "ECO-COMS Shell Organization Manager",
  "summarySettings": { "enabled": true, "label": "Review & Submit" },
  "editTasks": [
    { "label": "Organization Details", "task": { "taskId": "newShellOrg" } },
    { "label": "Confirm & Submit", "task": { "taskId": "newShellOrgConfirm" } }
  ],
  "conclusion": { "task": { "taskId": "newShellOrgSuccess" }, "render": true }
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

### Deferred endpoints — null guard required (`?? []`)

An inbound endpoint marked `"deferred": true` does **not** fetch until its data is first needed (e.g. when a tab using it is opened). However, Workday evaluates **all PMD script expressions at page load time** — including `rows`, `visible`, and `filter` expressions on every tab, not just the active one. This means a deferred endpoint's `.data` property is accessed before the fetch has occurred, causing:

```
Property Error found: data. Script Excerpt: myEndpoint.data
```

**Fix:** Always guard deferred endpoint data with `?? []` in any PMD expression:

```json
"rows": "<% comsApplications.data ?? [] %>"
```

**Pattern to apply everywhere deferred endpoints are used:**

- `"rows": "<% deferredEndpoint.data ?? [] %>"` — grids
- `"visible": "<% (deferredEndpoint.data ?? []).size() > 0 %>"` — conditional visibility
- `"values": "<% deferredEndpoint.data ?? [] %>"` — instanceList / dropdown

**Non-deferred (eager) endpoints do NOT need this guard** — their data is fetched before the page renders, so `.data` is always a list.

**Confirmed failure:** In `shellOrgManager.pmd`, the `comsApplications` endpoint (`deferred: true`) was referenced as bare `comsApplications.data` in the `appsGrid` rows expression. Even though `appsGrid` is on the "Application Patterns" tab (not the default Summary tab), Workday still evaluated the expression at page load — throwing the Property Error and crashing the entire page with a red "!" error indicator.

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
{ "name": "shellOrgPatterns", "baseUrlType": "workday-wql", "url": "data", "deferred": true, ... }

// FIXED — fetches eagerly on page load, grid populates correctly:
{ "name": "shellOrgPatterns", "baseUrlType": "workday-wql", "url": "data", ... }
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

- `footer` (TaskButton array) — up to **5** links. Each: `label` (stringScript, **req**) plus **exactly one** of:

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
## SMD (Security Model Definition)

The SMD file (`<appId>.smd`) lives alongside the AMD and defines site-level configuration. Key attributes:

- `id` / `siteId` / `applicationId` — all set to the app's `applicationId`.
- `languages` — array of `{ "code": "en-US", "description": "English" }`.
- `siteAuth.authTypes` — defines auth schemes used by outbound endpoints. The only auth type needed for SSO apps: `{ "scheme": "SSO", "id": "sso" }`.
- `errorPageConfigurations` — maps HTTP status codes to error PMD pages: `{ "statusCode": "404", "page": { "id": "errorPage" } }`. Common codes: 400, 401, 403, 404, 408, 500, 503.
- `cdnEnabled` — boolean, typically `true`.
- `siteProperties` — array, usually empty `[]`.
- `headerBackgroundColor` — hex colour for the app header bar (e.g. `"#0055B3"` for UBC blue).
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

## AMD data providers — this app's full list

These `dataProviders` are registered in the AMD. All use `apiGatewayEndpoint` (the Workday gateway for the tenant):

| Key | URL template | Use |
|---|---|---|
| `BUSINESS-OBJECT` | `https://api.workday.com/apps/{{site.applicationId}}/v1` | Extend model BOs |
| `COMMON` | `https://api.workday.com/common/v1` | Static common API (worker `/me`) |
| `workday-app` | `{{apiGatewayEndpoint}}/apps/{{site.applicationId}}/v1/` | Gateway BO endpoint |
| `workday-common` | `{{apiGatewayEndpoint}}/common/v1/` | Gateway common API |
| `workday-staffing` | `{{apiGatewayEndpoint}}/staffing/v1/` | Staffing v1 |
| `workday-staffing-v6` | `{{apiGatewayEndpoint}}/staffing/v6/` | Staffing v6 (job positions) |
| `workday-staffing-v7` | `{{apiGatewayEndpoint}}/staffing/v7/` | Staffing v7 |
| `workday-academic` | `{{apiGatewayEndpoint}}/studentAcademicFoundation/v1/` | Academic Foundation API |
| `workday-wql` | `{{apiGatewayEndpoint}}/wql/v1/` | WQL query endpoint |
| `workday-orchestrate` | `{{apiGatewayEndpoint}}/orchestrate/v1/` | Orchestrate API |
| `orchestrate` | `{{apiGatewayEndpoint}}/orchestrate/v1/apps/{{site.applicationId}}/orchestrations/` | App orchestration base |
| `orchestration` | `apiGatewayEndpoint + '/orchestrate/v1/apps/' + site.applicationId + '/orchestrations'` | Alt orchestration key (script form) |
| `workday-bp` | `{{apiGatewayEndpoint}}/businessProcess/v1/` | Business Process API |
| `wdayCom` | `{{apiGatewayEndpoint}}/staffing/v1` | Alt staffing (no trailing slash) |
| `wdayRef` | `{{apiGatewayEndpoint}}/referenceData/v1` | Reference Data API |
| `workday-org` | `{{apiGatewayEndpoint}}/common/v1/` | Common API aliased as org |

**Endpoint for the signed-in worker:** use `baseUrlType: "COMMON"`, `url: "/workers/me"`.

**Endpoint for BO collections:** use `baseUrlType: "BUSINESS-OBJECT"`, `url: "/collectionName"` with `isCollection: true`.

## Script include files (`.script`)

PMD pages can reference shared Workday Script modules via the top-level `include` array:

```json
{
  "id": "myPage",
  "include": ["comsValidations.script"],
  ...
}
```

- Script files live in `presentation/scripts/` and have the extension `.script`.
- The module name (without `.script`) becomes a variable in PMD script expressions: `comsValidations.isValidSubject(text)`.
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

Scripts can reference Workday built-in namespaces (`date:`, `validate:`, `regex:`, etc.) and interact with business objects (`comsAuditLogs.create()`). They do NOT have page widget access (no `self`, no widget IDs) — they are pure functions operating on passed-in values.

## footer / pod widget

The page `footer` (inside `presentation`) renders a persistent footer bar below the page body. It references a `.pod` file by `podId`:

```json
"footer": {
  "type": "footer",
  "children": [
    { "type": "pod", "podId": "ecoComsFooter" }
  ]
}
```

- Pod files live in `presentation/pods/` and have the `.pod` extension.
- The `podId` must match the filename without extension.
- Pods define reusable UI fragments (logos, branding, links) that can appear on multiple pages without repeating code.
- Pod files can include their own PMD-style widget declarations.

## Button `action` values

A `button` widget's `action` attribute controls its visual style and role. Confirmed values in this codebase:

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
    "taskId": "shellOrgManager",
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

### `autoPaging`

`"autoPaging": true` on a read-only grid automatically paginates large result sets without requiring the user to click a "load more" button. Use on view pages that may show many rows.

### `sortableAndFilterable`

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
- `showPercentLabels` (boolean) — show percentage on each slice.
- `animateOnLoad` (boolean) — animate the chart when the card loads.

```json
{
  "id": "ShellOrgStatusChart",
  "parameters": ["activeCount", "inactiveCount", "totalPatterns"],
  "header": {
    "title": "Shell Org Overview",
    "subtitle": "Active vs. Inactive shell organizations"
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
  "name": "comsAssignableRoles",
  "baseUrlType": "BUSINESS-OBJECT",
  "url": "/comsAssignableRoles",
  "authType": "sso",
  "isCollection": true,
  "bestEffort": "true"
}
```

Returns `{ "data": [...] }` — access items via `comsAssignableRoles.data`.

## Button navigation — `parameterBindings` vs `parameters` pitfall

On a `button`'s `taskReference`, both `parameters` and `parameterBindings` appear to work individually, but **`parameterBindings` silently overwrites `parameters` when both are present**. Only one key should ever appear. Prefer `parameterBindings` consistently:

```json
{
  "type": "button",
  "action": "PRIMARY",
  "label": "Open",
  "taskReference": {
    "taskId": "shellOrgManager",
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

## Endpoints — `failOnStatusCodes` required

**Always set `failOnStatusCodes`** (at minimum `[400, 403]`) on every inbound endpoint. Without it, HTTP error responses are swallowed silently — the endpoint appears to succeed with no data:

```json
{
  "name": "comsAssignableRoles",
  "baseUrlType": "BUSINESS-OBJECT",
  "url": "/comsAssignableRoles",
  "authType": "sso",
  "isCollection": true,
  "bestEffort": "true",
  "failOnStatusCodes": [400, 403, 404, 500]
}
```

This is an enforced best-practice rule (EndpointFailOnStatusCodesRule) in the Workday DevRel Arcane Auditor.

## Endpoints — REST collections default to 20 rows

**Workday REST collection endpoints return only 20 rows by default** (max 100 per request). Always pass an explicit `limit` parameter, or paginate. Without it, your grid silently shows only the first 20 records even when more exist:

```json
{
  "name": "allRoles",
  "baseUrlType": "BUSINESS-OBJECT",
  "url": "/comsAssignableRoles?limit=100",
  "authType": "sso",
  "isCollection": true
}
```

For large datasets, use WQL with paging or RaaS (which has no pagination limit).

## Endpoints — `isCollection: true` performance warning

Using `isCollection: true` on inbound endpoints **can degrade the entire tenant under concurrent use** (NoIsCollectionOnEndpointsRule). For querying data, prefer **WQL** or **RaaS** instead of `isCollection`. Reserve `isCollection` only for small, bounded BO collections where WQL is unavailable.

## Grid — do not combine paging with `sortableAndFilterable`

**Never combine server-side paging with `sortableAndFilterable` columns.** Every page change triggers a refetch, re-sort and re-filter cycle, causing severe performance problems. Choose one approach:

- Server-side paging + search prompts for filtering (no `sortableAndFilterable`)
- Client-side sorting with `sortableAndFilterable` + keep the result set small and unpaged

## Grid — `excelExportEnabled` row limit

`"excelExportEnabled": true` on a grid has a **~60 second export limit**. Workday warns against it above ~4,000 rows. For large exports, use a **RaaS report** instead — RaaS has no pagination and is designed for bulk data export.

## WQL — injection risk in string concatenation

**Do not concatenate user input into WQL `contains(...)` expressions** in PMD script:

```
// UNSAFE — user controls the search string
"query": "<% 'SELECT ... WHERE name contains \\'' + searchInput.value + '\\'' %>"
```

Instead, use a **WQL Query component** (`.wqlquery` file) with typed `parameters`, which passes values safely:

```json
{
  "id": "searchOrgs",
  "parameters": ["searchTerm"],
  "query": "SELECT ... WHERE name contains \"<% searchTerm %>\""
}
```

WQL Query component parameters are interpolated server-side — not string-concatenated by the PMD script — which prevents injection.

## Orchestrations — debugging runs (confirmed 2026-10-29)

- A page's "success" only means the orchestration launch returned 200. AddShellOrg / AddShellOrgPattern catch errors in a global error handler and still return 200, so **always verify the record exists** (Shell Org Manager counts) and read the run log.
- Run logs: developer.workday.com → Apps → this app → **Logs** tab (last 15 min). Find the "Aggregated step totals" line for the run's commonId: it lists each step with success/failure counts. **Orchestration Activity** tab lists runs.
- Root cause found this way: the PMD sent an empty `comsAppId` (`dropdown.value.id` is empty), so `GetApplication` hit `/comsApplications/` (the collection) and `ExtractOrgType` failed before the SOAP call.
- Shell-org apps like X:ADM have no COMSApplication record. AddShellOrg now takes `orgType` (= application code) as a query param; its GetApplication node is disabled (`isDisabled: true`).
- Organization_Code = Organization_Name = the generated name for both orchestrations (user decision).
- The `Organization_Add_Update` SOAP body via `SendWorkdayApiRequest` POST `/soap/v42.2/Human_Resources` works (HTTP 200, org created) with Organization_Type_Name = `X:CLW` / `X:ADM` and subtype `X:Shell`.
- Orchestration files are single-line JSON: when editing with a script, re-serialize compactly (`separators=(',',':')`) to keep diffs small.

## Orchestrations — failure handling (confirmed live 2026-10-29)

- AddShellOrg / AddShellOrgPattern now have a **Continue on Conditions** step `CheckWWSAccepted` right after `CallAddUpdateOrganization`: assertion `data.CallAddUpdateOrganization.responseStatusCode.is2xxStatusCode().not().or(data.CallAddUpdateOrganization.response.isSoapFault()).not()`, message `"Workday rejected the request for " + <name>`. Node `_type` is `ContinueOnConditions` with `assertions: List<Assertion{assertion: Expr Boolean, message: Expr String}>` (JSON taken from Orchestration Builder output, source: developer.workday.com "Concept: Orchestration Logic Components").
- The global error handler was removed (it only logged and swallowed errors).
- **Confirmed:** a forced WWS rejection (SOAP 500) → CheckWWSAccepted fails with an ERROR log → nothing created. **But the Orchestrate `/launch` call still returns HTTP 200** (text/plain body ~107 bytes) to the PMD, so the page's `failOnStatusCodes` never fires and the success page still shows. The page cannot see failures through the outbound launch endpoint. Solved by run-and-verify, below.
- Getting real JSON for a component the repo doesn't use yet: add it in Orchestration Builder (drag from Components; synthetic drags need HTML5 DragEvents), save that orchestration to App Hub (no deploy), then console → app → Related Actions → **View Source** → Activity build → open the `.orchestration` file. CI's next upload overwrites App Hub with the repo version.
- Orchestration Builder may show "Updates Available in App Hub" with an old session; Discard Session loads the latest.


### Run-and-verify in `onSubmit` (confirmed live 2026-10-30)

Used by newShellOrg / newShellOrgPattern so a Workday rejection blocks OK instead of showing "Created":

- Launch the orchestration from `onSubmit` through a **deferred inbound** endpoint (`baseUrlType: "orchestration"`, url `'/<Name>/launch?param=' + p + ...`, params bare in the URL) with `endpoint.invoke({'p': value, ...})`.
- Then re-read the data with a second deferred endpoint and check the record exists. If it doesn't, call `someField.setError('Workday rejected this request, so nothing was created...')` and return `false`.
- **`.invoke()` on a WQL endpoint that uses `wqlQuery` / `queryId` throws `Unknown Function call: .invoke({ })`.** Instead, call WQL as a plain GET: `"baseUrlType": "workday-wql"`, `"url": "<% 'data?limit=' + lim + '&query=<URL-encoded WQL>' %>"`, and invoke it with `.invoke({'lim': '10000'})`. Keep the WQL static (no user input) and filter in script.
- In an editWizard, Next on a step runs the step's `onSubmit` validation, and the final OK runs it again. The launch only fires once all validation passes, on OK.
- Tested: forced failure → field error, nothing created; valid submit → success page, record verified (Active Orgs 195→196, patterns 377→378).

## manageShellOrgStatus — working (confirmed live 2026-10-30)

- **`Organization_Add_Update` cannot change status.** Its `Organization_DataType` (v42.2 WSDL) has no Inactive element. Sending `<bsvc:Inactive>` returns the SOAP fault "Invalid Subelement Inactive ... for element Organization_Data". Source: the tenant WSDL at `https://wcpdev-services1.wd101.myworkday.com/ccx/service/ubc_wcpdev2/Human_Resources/v42.2?wsdl`. The community.workday.com docs page has moved.
- **The status change uses `Organization_Inactivate` / `Reactivate_Organization_Request`** in the same Human_Resources service:
  ```xml
  <bsvc:Organization_Inactivate bsvc:version="v42.2">
    <bsvc:Validate_Only>false</bsvc:Validate_Only>
    <bsvc:Organization_Reference_Data>
      <bsvc:Integration_ID_Reference><bsvc:ID bsvc:System_ID="WD-WID">{{orgWID}}</bsvc:ID></bsvc:Integration_ID_Reference>
    </bsvc:Organization_Reference_Data>
    <bsvc:Organization_Inactivate_Data bsvc:Effective_Date="{{yyyy-MM-dd}}"/>
  </bsvc:Organization_Inactivate>

  <bsvc:Reactivate_Organization_Request bsvc:version="v42.2">
    <bsvc:Organization_Reference><bsvc:ID bsvc:type="WID">{{orgWID}}</bsvc:ID></bsvc:Organization_Reference>
  </bsvc:Reactivate_Organization_Request>
  ```
  `System_ID="WD-WID"` with the org's WID is accepted. A success response is an empty SOAP Body. Reactivate is untested.
- **Use `Validate_Only=true` to test a WWS call safely.** Workday checks the request fully and changes nothing.
- **Orchestration text templates support `{{#if}}` but NOT `{{else}}`.** The build fails with "illegal start of simple expression". Use two `{{#if}}` blocks with Boolean flags. Handlebars treats any non-empty string as true, so the flags come from CreateValues Boolean assignments: `data.GetInputParams.includeInactive.equals("true")` (type `Boolean`, Expr `["Expr","Boolean"]`). This uploaded and ran fine.
- **Logging the WWS response:** a `Log` node with message `"..." + data.CallOrganizationUpdate.response.toString()` writes the full SOAP response, including fault text, to developer.workday.com → app → Logs. Kept in ManageShellOrgStatus as `LogWWSResponse`.
- **Reading CI build errors:** `gh run view --log` is blocked from the cloud container. The GitHub run page (Summary → "Upload Failure") in the browser shows the App Hub build output.
- **Page check (run-and-verify):**
  - The page reads `GET BUSINESS-OBJECT /comsAuditLogs?limit=1` `.total` before and after the launch. The orchestration writes an audit record only when Workday accepts the change.
  - A WQL count of `comsAuditLogs` lagged and gave false "rejected" errors.
  - Checking `cf_active1` can't work for future-dated changes, because the org is still active today.
- The page has an **Effective Date** field (sent to the SOAP request) and standard OK/Cancel, with `cancelOverride` to shellOrgManager.
- **Scope note:** a status change dated in the future leaves Shell Org Manager showing "Active" until that date.
- Test records inactivated effective 2026-12-15:
  - `X:ADM:TEST:ORG:1029`, `1030`, `1031`
  - `X:CLW:PATTERN:MATH:MATH:300/301/302:951:2026W1`
  - 1029 was confirmed in its Workday audit trail ("made inactive on 2026-12-15").

## Role assignments (Assign_Roles) — working (confirmed live 2026-10-30)

- Pages:
  - shellOrgManager "Manage Role Assignments" grid has one row per role + org, with positions taken from `cf_ZCF_EE_RoleAssignedToAsPositionRestrictions`.
  - Manage → `editRoleAssignment` (EDIT) directly; the separate view page was removed 2026-10-30 at the user's request (fewer clicks). Related actions stay on the shellOrgManager grid.
  - The edit page's `onSubmit` launches `AssignRolePositions` once per change and run-and-verifies with the `/comsAuditLogs?limit=1` `.total` count.
- WWS: Staffing v42.2 `Assign_Roles_Request` (`/soap/v42.2/Staffing`). Structure matches the user's Assign Roles EIB v35.0:
  - Event_Target_Assignee
  - Role_Assigner (WID)
  - Assignable_Role (WID)
  - Update_Later_Dated_Assignments=true
  - Assignees_to_Add / Assignees_to_Remove
  - Auto_Complete=true, Run_Now=true
- **Assignee IDs:**
  - The `allPositions` WID is rejected ("The provided Role Assignee is not valid as an Event Target Role Assignee").
  - **Add:** use `bsvc:type="Position_ID"` with `cf_PositionID` (e.g. P-00010).
  - **Remove:** use `type="WID"` with the current assignee id from the role-assignment data.
  - Both were tested live: P-00010 was added to X:BPMS(ODMT):ROLE:ADVISORS and then removed. Multi-position also tested: P-00009 + P-00010 added in one submit, then both removed in one submit (2 launches each, audit-count check passed).
- **`relatedTask` / instance links on instanceList render only on VIEW pages** (developer.workday.com instanceList reference). This is why there are separate view and edit pages.
  - On VIEW grids: an instanceList cell with `values` + `widKey:"id"` + `view:true` + `relatedTask:true` gives related actions on hover.
- **Read-only instanceList on an EDIT page:** `values` alone or `instanceList` showed "(empty)". Use `"values": "<% [] %>"` + `selectedValuesAndDescriptors`.
- **URL-encode free text in launch URLs** (`name.urlEncode()`). A space in a role or org name gives InvalidEndPointUrlException "Illegal character".
- **2026-10-30 (user request: fewer clicks):** the separate manageRoleAssignment view page was removed. Manage on the grid now opens editRoleAssignment directly. That page shows a one-row "Current Assignment" grid (role, org, current positions) above the Change Positions fields.
- **Confirmed live:** an instanceList grid cell on an EDIT page with `view:true` + `relatedTask:true` renders plain text, with no link and no related actions.
  - `values` alone renders blank cells on an edit page. Use `values:[]` + `multiSelect:true` + `selectedValuesAndDescriptors`.
  - An edit-page grid needs `doNotAdd:true` / `doNotRemove:true` to hide the +/- row icons. `readOnly:true` did not hide them.
- **More edit-page attempts at grid related actions, all failed (live 2026-10-30):**
  - `instanceList` as a script string fails the build ("Cannot deserialize ... ArrayList<Instance> from String"). It must be a literal array. For a variable list use `instanceListLoopTag` (`type: instanceLoop`, `on`, `as`, `templateInstance`).
  - Literal `instanceList` / `instanceLoop` with `wid` and `view:true`, plus grid `enabled:false`: the cells render blank.
  - Adding `id` + `selectedValues` + `relatedTask:true`: the values show as removable prompt pills, with no related actions.
  - Build warning: "If you set the relatedTask attribute ... the pmd must be a view page."
  - Conclusion: related actions need a VIEW page. The "pending ISC requests" grid that has them (iscRoleRequestsView) is a VIEW page.
- **Left for user testing (2026-10-30):** X:BPMS(ODMT):ROLE:ADVISORS now holds P-00009 (Pedro Santiago), P-00010 (Beth Liu) and P-00011 (Maria Cardoza). P-00009 and P-00010 were added in one submit, effective 2026-10-30.
- Position search matches by ID too (e.g. "P-00010").
- The Current Assignment grid's narrow positions column only shows up in a narrow (~800px) window. At desktop width it displays in full. The grid now uses `gridType: LIST`.
- **Audit Log Viewer "Property Error found: .worker" (fixed 2026-10-30):** audit records written by the orchestrations (role assignment, status) have no `worker` / `application`. Guard SINGLE_INSTANCE sub-properties with `!empty(logEntry.worker) ? (logEntry.worker.descriptor ?? '') : ''`, and default the text fields with `?? ''`.
- After OK, the edit page returns to the app home, not the manage page (seen on both tests). A flow or conclusion page would be needed to land back on Shell Org Manager.

## Audit log design (confirmed live 2026-10-30)

- **One writer per change.**
  - Orchestrated changes (AddShellOrg, AddShellOrgPattern, ManageShellOrgStatus, AssignRolePositions): the orchestration writes the record after CheckWWSAccepted.
  - The page-level `postAuditLog` outbound was removed from newShellOrg, newShellOrgPattern and manageShellOrgStatus.
  - Assignable-role pages (assignableRoleManager, adminProvisioning, assignableRoleManagerMaintain, deleteAssignableRole) have no orchestration, so they still write via their own outbound.
- **Pages pass to every launch:** `changedBy` (selectedWorker.descriptor, urlEncoded), `changedByWid` (selectedWorker.id), and `timestamp` (`date:now().format("yyyy-MM-dd'T'HH:mm:ss'Z'")`, urlEncoded). Before this, the orchestrations had no timestamp or user.
- **Previous AddShellOrg / AddShellOrgPattern audit writes never landed.** The template sent `"worker": "<wid>"` and `"application": ""` as plain strings to SINGLE_INSTANCE fields. Don't template SINGLE_INSTANCE fields as strings. Store WIDs in TEXT fields instead (`changedByWid`, `orgWid`, `roleWid`, `positionWid`).
- **COMSAuditLog new fields:** `effectiveDate` (DATE; the template sends "yyyy-MM-dd", which works), `roleName`, `positionName`, plus the TEXT WID fields above. `worker` and `application` stay but are unused.
- **Fixed vocabulary:**
  - `objectType` (Change Type): Shell Org | Shell Org Pattern | Org Status | Role Assignment | Assignable Role.
  - `action`: ADD | INACTIVATE | REACTIVATE | ASSIGN POSITION | REMOVE POSITION | REQUEST | APPROVE | DENY | DELETE.
  - manageShellOrgStatus now sends REACTIVATE (not ACTIVATE).
- **Viewer** (auditLogViewer, VIEW page):
  - Columns: Timestamp, Change Type, Action, Organization, Role, Position, Effective Date, Changed By, Details. Rows use `list:sort(auditLogs.data ?? [], 'timestamp', false)`, newest first.
  - **Related actions from a stored WID:** the cellTemplate is a `fieldSet` with two children: an `instanceList` (`values: [{'id': wid, 'descriptor': name}]`, `widKey:"id"`, `view`/`relatedTask` true, `visible: !empty(wid)`) and a `text` fallback (`visible: empty(wid)`). Confirmed: 4 related-action icons render.
- **Position WID for adds:** editRoleAssignment looks it up per added position with a deferred WQL GET (`posWidLookup`): `SELECT workdayID FROM allPositions WHERE cf_PositionID = '<P-id>'`. For removes, the assignee WID is `p.id`.
- **Deleting BO records from a page:**
  - An outbound `DELETE /collection?bulk=true` with a `values` body is **silently skipped**. Nothing is deleted and there's no error.
  - What works: a grid with `deleteEndPoint` + DELETE `'/collection/' + idCell.value`, removing rows and then OK (one DELETE per row).
  - Rows can be removed in bulk with JS that clicks `button[data-automation-id="removeRow"]`.
  - Used once to purge the 30 old audit records (2026-10-30). The temporary purgeAuditLogs page was then removed.
- **Reports consolidated 10 → 4:**
  - AllAssignableRoles (label "All Assignable Role Requests", 21 columns, 3 domains)
  - AllShellOrgs ("All Shell Org Requests", 11 columns, 2 domains)
  - AcademicUnits ("All COMS Applications")
  - AllAuditLogs (new columns)
  - A report can take multiple `defaultSecurityDomains`.
  - Unused WQL components were removed: academicUnits, auditLog, customOrganizationsFUH, shellOrgManager.
- **COMSShellOrgRequest business object:** nothing writes to it. Its only reader (assignableRoleManager) is `exclude: true`. It predates creating shell orgs directly via WWS, and its report was kept.
- **Full end-to-end test, all six flows (2026-10-30 ~17:30–17:55 UTC).** Each wrote exactly one complete audit record:
  - Assignable role request `X:ADM:ROLE:TESTROLE1030` (now Pending ISC Review)
  - AAA request for X:ADM
  - Shell org `X:ADM:TEST:ORG:1032`
  - Pattern `X:CLW:PATTERN:MATH:MATH_V:303:951:2026W1`
  - Inactivate and **Reactivate** of 1032. This was the first live Reactivate; 1032 is Active again.
- **Fixed during the test:**
  - assignableRoleManager and adminProvisioning had `standardEditButtonsHidden: true` with no editButtonBar, so there was no way to submit. The flag was removed and `cancelOverride` set to home.
  - Org names for inactive orgs carry " (inactive)". manageShellOrgStatus must `urlEncode()` the name and code (InvalidEndPointUrlException "Illegal character ' '") and strip " (inactive)". newShellOrg and newShellOrgPattern now urlEncode their names too.
  - Request audit records now include the selected positions and, for AAA, the application as Organization. Deployed but not yet seen live.
- **Linking to Workday events (developer.workday.com "Reference: Context Global Functions" + tenant WSDLs):**
  - `context.orchestrateId()` returns the orchestration instance ID (X-Orchestrate-Id). It is not a tenant instance, so it can be stored as text but cannot have related actions.
  - Staffing `Assign_Roles_Response` returns `Assign_Roles_Event_Reference`, the BP event. This is linkable.
  - Human_Resources `Organization_Add_Update` and `Organization_Inactivate` have **no output message** (one-way, empty body). They give no event and no new-org WID.
  - `Reactivate_Organization_Response` returns `Organization_Reference`.
- **CI:** a run stuck at "in_progress" with every step completed (job conclusion success) had actually deployed. `gh run cancel/rerun` and force-cancel all refuse such a run. Check the job conclusion with `gh api .../runs/<id>/jobs`.
- **CI:** a failure at "Authenticate as system user (for upload)" in about 20s was transient; a rerun passed.

## Orchestrations — ISU auth requires manual per-tenant setup

An orchestration endpoint using `isuAuth` will **fail with HTTP 500 and an empty body** until the ISU (Integration System User) is explicitly assigned to the app in **Application Manager** for that tenant. Naming the ISU in the SMD is not sufficient — it must be configured in each environment after every promotion:

1. Open Application Manager in Workday
2. Find the deployed Extend app
3. Assign the ISU to the app

Re-check this after every promotion (dev → impl → sandbox → prod) as it does not carry forward.

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

## CI/CD — GitHub Actions deploy pipeline

The deploy workflow (`.github/workflows/deploy.yml`) pushes to Workday on every `main` branch push. After every `git push`, check `gh run list` and confirm `conclusion: success` before declaring anything deployed.

### WD_DEV_TOKEN expiry (most common failure)

**Symptom:** GitHub Actions run fails in ~11–16 seconds at the step "Pre-populate wdcli config with developer token". All other steps are skipped.

**Root cause:** The `WD_DEV_TOKEN` GitHub secret holds a Workday PKCE user token (JWT) scoped to `ubc_wcpdev2`. This token has an ~8-hour TTL. When it expires, the workflow decodes the JWT, compares `exp` to `now`, and exits 1 with:
```
WARNING: WD_DEV_TOKEN EXPIRED (exp=..., now=..., expired ...s ago)
ACTION: run 'wdcli app deploy ...' locally, log in, update WD_DEV_TOKEN secret
```

**Fix (must be done by the user — requires browser login):**
1. On the local machine with `wdcli` installed, run:
   ```
   wdcli app deploy ecocomsphase_xclw_cm_sync2_vmzvxm
   ```
2. Complete the browser login for the `ubc_wcpdev2` tenant.
3. Open `~/.config/@workday/wdcli/config.json` and copy the value at `wcpTenantAccessToken["ubc_wcpdev2"]`.
4. Update the `WD_DEV_TOKEN` GitHub secret at:
   `https://github.com/crismwan/ECO-COMS-Extend-App/settings/secrets/actions`
5. Re-run the failed workflow with `gh run rerun <run-id>`.

**Important:** The code itself is fine when this failure occurs — do not revert commits or alter the code. The failure is purely an infrastructure/secrets rotation issue.

### Tests in the pipeline (added 2026-10-30)

- `test/static_checks.py` runs before upload and blocks on known pitfalls (pageType case, `_` attributes, hidden OK with no editButtonBar, unresolved taskIds, missing orchestrations, BP routes, card params/quotes, forbidden test text, size limits). Known issues go in `KNOWN_ISSUES` with a reason and show as warnings.
- `node test/e2e.js` runs after deploy (read-only smoke) with `WD_DEV_TOKEN`. `--suite full` (manual workflow_dispatch input `e2e_suite=full`) also creates and inactivates an `X:ADM:TEST:CI:<stamp>` org.
- Coverage map and manual checklist: `test/README.md`.
- Unverified until the first CI run: that the PKCE `WD_DEV_TOKEN` works for `api.workday.com` REST/WQL/BP calls, and that orchestration launch via `POST api.workday.com/orchestrate/v1/apps/<app>/orchestrations/<Name>/launch` works outside a page.
- `ManageShellOrgStatus` writes its audit record even when `validateOnly=true`, so validate-only can't be used for safe per-deploy write tests until the audit write is made conditional.

### Run time baseline

- A healthy deploy run completes in **~1m15s**.
- A run that finishes in **<20 seconds** has almost certainly failed at the token step (not a code error).

## ISC review business process (confirmed live 2026-10-30)

- `model/ReviewCOMSAssignableRoleRequest.businessprocess` targets COMSAssignableRole. Steps: details (VIEW `/reviewRoleRequestDetails/{eventId}`), approval (VIEW `/reviewRoleRequestApproval/{eventId}`), action steps CreateSecurityGroup and AddWorkdayAssignableRole (EDIT `/...{eventStepId}`). AMD tasks use those routingPatterns.
- Request pages save a fixed `referenceId` (hidden `requestRefHidden`, set at page load) and then launch `StartRoleRequestReview` (outbound POST, `orchestration` base, `?ref=`). The orchestration finds the request by `referenceId` (now indexed), POSTs `/apps/<app>/v1/reviewCOMSAssignableRoleRequestEvents` with `businessProcessTarget.id`, and PATCHes `reviewEventWid` onto the request.
- Orchestration build error "Function stringAtJsonPath cannot be applied to an instance of DataType": read API responses as `data.X.response.asJSON().stringAtJsonPath(...)`.
- Step pages get context with `GET workday-bp eventSteps/<eventStepId>` → `event.id`, then `GET workday-bp events/<id>` → `for.id` (the request WID). Inbound endpoints can reference earlier ones in their URL.
- An action step is completed by outbound `POST workday-bp eventSteps/<id>/submit` with `stepAction.id = d9e4223e446c11de98360015c5e6daf6` (Submitted). Tested: the step closed and the next step arrived in the inbox.
- Tenant setup, done by hand:
  1. BP type page → **Edit Policy**. HR Administrator on Initiate, both action steps, View All, Approve, Cancel, Deny.
  2. **Activate Pending Security Policy Changes**.
  3. **Create Business Process Definition (Default Definition)** → Edit Definition: a Initiation, b Approval, c Action Create Security Group, d Action Add Workday Assignable Role, each with Group HR Administrator.
  - Step groups only appear in the prompt AFTER the policy is activated ("No matches found" before that).
  - The definition is found by searching `bp: <name>`. Its related actions → Business Process → Edit Definition / Configure Orchestrations.
- When the initiator is in the approval group, Workday auto-completes the approval step. HR Admin testing goes straight to step 3.
- **Deny handling (tested live 2026-10-30 via a Cancel pairing):** orchestration `DenyRoleRequest` (template "Workday Business Process", flow type `.maya.FlowBusinessProcessTriggered`, start `StartBusinessProcess`, end `EndEmptyMaya`, default credential `AccessTokenFromInitiatingUser` — JSON copied from Orchestration Builder → Settings → Open Current Source Code). It GETs the request, PATCHes `status: Denied, active: false`, and POSTs a DENY audit record.
  - Denied request WID: `bp.eventTarget().getIDValues("WID").get(0)`. `bp.eventTarget().toString("WID")` is in the docs but fails the build ("Wrong number of arguments for function toString").
  - Timestamp: `datetime.now("UTC").format("yyyy-MM-dd'T'HH:mm:ss'Z'")` (developer.workday.com "Reference: DateTime Global Functions" + LocalDateTime member `format`). `bp.*` functions: "Reference: Business Process Global Functions".
  - Tenant: definition related actions → Business Process → **Configure Orchestrations** → Add → Action Deny → Orchestration → Create Orchestration Launch Configuration ("ECO-COMS Deny Role Request", BP type Review COMS Assignable Role Request, no parameters).
  - The launch configuration can't be saved until the tenant-wide **Edit Tenant Setup – Business Processes → User to perform Orchestration Launches** is set. Set to lmcneil (user approved, 2026-10-30).
  - Workday says BP-triggered orchestrations usually launch within ~15 minutes; in practice they ran in about 2–3 minutes. Status: Find Events → Orchestrations tab.
  - **Deny is only offered while an approval is awaiting action.** When the initiator is in the approval group, approval auto-completes and only Cancel remains. So DenyRoleRequest is also paired with the **Cancel** action (Configure Orchestrations). A cancelled request is marked Denied with a DENY audit record; without this it would stay "Pending" forever.
  - The DENY audit shows position names: request pages save `positionNames` (TEXT, from the positions widget's `selectedEntries` descriptors) and the orchestration uses it, falling back to `positionWids`.
- **Current BP definition (user-edited 2026-10-30):** a Initiation → b Approval (Compliance Administrator) → c1 To Do "Add Assignable Role" → c2 To Do "Create Role Based Security Group" → d Action (EDIT page reviewRoleRequestAssignableRole, "Link Workday Role"). The old CreateSecurityGroup action step / reviewRoleRequestSecurityGroup page is unused.
  - Security group: Type of Tenanted Security Group = **Role-Based Security Group**, Name = the **full role name as-is** (e.g. X:ADM:ROLE:TESTROLE1035; user decision). Step d prefills the name with `request.securityGroupName ?? request.roleName`.
  - Compliance Administrator needs Deny / View All on the BP policy for the Deny button to appear. Saving that policy change was blocked for the agent (permission grant); the user does it, then Activate Pending Security Policy Changes.
- **Approval group must be able to resolve people (live 2026-10-30):** with step b set to "Accounts Payable Data Entry Specialist" (a *constrained* role-based group), TESTROLE1036's approval showed Awaiting Action with **All Persons = 0**. Confirmed: the app domain "Manage: COMS Assignable Roles" lists **Allowed Security Group Types: Public Groups, Unconstrained Groups** (View Domain page), because COMSAssignableRole has no organization context. Use a user-based group or the **(Unconstrained)** variant.
  - An approver needs the group in **three** policies: the BP security policy (Approve, Deny, View All), the domain **Maintain: COMS Assignable Roles** (secures the four step pages; on 2026-10-30 it held only HR Administrator + the deploy ISSG), and **Manage: COMS Assignable Roles** (the request data). Then Activate Pending Security Policy Changes. The agent may not edit security policies; the user does this.
- **Fixed (live 2026-10-30):** with "Accounts Payable Data Entry Specialist (Unconstrained)" on the BP policy (View All, Approve, Deny), both domains, and step b, TESTROLE1038's approval resolved **8 persons** (incl. James Walker). Real Deny then tested end to end: James Walker (proxied by the user) denied TESTROLE1038 at 13:30:17, DenyRoleRequest completed the same second, a DENY audit record was written and the request left the pending list. An in-flight request keeps its original routing; definition changes only affect new requests. Edit Definition shows a page error if a step's group isn't in the BP policy.
- **Step help text:** definition related actions → Business Process → **Maintain Help Text** → pick the step → Edit Step Help Text → fill Help Text → OK → Done. Rewritten for all 5 steps on 2026-10-30 in one format: bold "Step N of 5: <name>" title (+ who does it), one-line purpose, bold "Check" / "How to" label with a bulleted list, then a bold "Next:" or "Outcome:" line. Step numbers match the "Step X of 5" banners on the ECO-COMS step pages. Example names use X:ADM:ROLE:EXAMPLE.
  - The Help Text cell is a plain textarea plus a **Format Text** button that opens a ProseMirror rich-text editor (bold, italic, underline, colour, bulleted list, link, email). No numbered list. Line breaks typed in the textarea are kept.
  - Agent technique: clear the *textarea* first (click it, ctrl+a, Delete; keys reach the textarea but not the ProseMirror editor), open Format Text, then dispatch a synthetic `paste` ClipboardEvent with `text/html` on `.ProseMirror`. Formatting is preserved. Then Done → OK.
- **Completion notification (2026-10-30):** definition related actions → Business Process → **Add Notification** → Create Workflow Notification: Trigger on Status = **Completed**, Recipients = **Initiator**, subject "ECO-COMS role request completed", short body. Completed only fires on the approve path (a deny ends with status Denied). Remove the empty Email Addresses row before OK.
- **Inbox titles:** `useForDisplay: true` on COMSAssignableRole `roleName` makes inbox items read "Review COMS Assignable Role Request: <role name>".
- **Orchestration Builder "Open Current Source Code"** (orchestration Settings page) shows the JSON without saving to App Hub — easier than Save + View Source. A stale App Builder session can be reset with ⋮ → Revert to App Hub.
- Browser pane tips: narrow window → Workday prompts open as full-screen pickers. Use resize_window 1600x1000 for BP grids. Related-action menus need hover to open sub-menus. Date fields need per-key input (`key "1 0 3 0 2 0 2 6"`).
