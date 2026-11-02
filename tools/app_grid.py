"""Application grid columns shared by every page that lists applications (needs comsApplications + comsPatterns.script)."""


def app_columns(var, link_task, link_params, button_label, show_format=True):
    """Application grid columns shared by this page's picker and Shell Org Manager's Application Patterns tab
    (product owner 2026-11-02: the two should match): Application ID as a link, Name, Pattern Format, then the action."""
    ref = {"taskId": link_task, "parameterBindings": link_params}
    cols = [{"type": "column", "columnId": "colAppId", "label": "Application ID",
             "cellTemplate": {"type": "button", "id": "appIdLinkButton", "action": "LINK", "label": f"<% {var}.appCode ?? '' %>", "suppressDiscardDialog": True, "taskReference": ref}},
            {"type": "column", "columnId": "colAppTitle", "label": "Name", "cellTemplate": {"type": "text", "id": "appTitleText", "enabled": False,
             "value": f"<% (comsPatterns.recordFor(comsApplications.data, {var}.appCode) ?? {{'name': ''}}).name ?? '' %>"}},
            {"type": "column", "columnId": "colAppFormat", "label": "Pattern Format", "cellTemplate": {"type": "text", "id": "appFormatText", "enabled": False,
             "value": f"<% comsPatterns.summary(comsApplications.data, {var}.appCode) %>"}},
            {"type": "column", "columnId": "colAppAction", "label": button_label, "cellTemplate": {"type": "button", "id": "appActionButton", "label": button_label,
             "action": "AUXILIARY", "suppressDiscardDialog": True, "taskReference": dict(ref)}}]
    return cols if show_format else [c for c in cols if c["columnId"] != "colAppFormat"]
