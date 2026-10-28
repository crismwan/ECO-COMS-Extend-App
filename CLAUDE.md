# Workday Extend development

These preferences apply to **all** Workday Extend apps I work on (not any single project).

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

### simpleCard (the .card file side)

File `simpleStatusCard.card` → `"id": "simpleStatusCard"`. Set `body.type` to `"simpleCard"`.

**Attributes:**

- `id` (string, **req**) — must match the card file name.

- `parameters` (string array) — parameter names the PMD may pass in. Reference them bare in scripts (`<% title %>`), not via a prefix. Use `?: null` for optional ones (e.g. `"icon": "<% icon ?: null %>"`).

- `header` (object) — `title` (stringScript, bold, top of card), `subtitle` (stringScript, below title), `icon` (string — must be a **`wd-accent-*`** icon), `indicator` (object: `label` stringScript + `color`).

  - `indicator.color` valid values: **`blue`, `gray`, `green`, `orange`, `red`, `transparent`**.

- `body` (object, **req**) — `type` (**req**, `"simpleCard"`) and `value` (stringScript, **req**) = the body content.

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