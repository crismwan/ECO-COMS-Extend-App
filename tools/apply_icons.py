#!/usr/bin/env python3
"""One place for every icon in the app (cards, Extend Cards, hub title, hub navigation items).

Builders may write any icon; this pass runs last in rebuild_all and sets the icons below, so a
change here is the only edit needed. Icon choice follows the framework in CLAUDE.md ("Icons").
Valid names: developer.workday.com "Reference: Icons" (checked 2026-11-02).
"""
import json, os, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

ACCENT = set("""award-medal trophy calendar chart-bar-arrow data-loading data-refresh gauge megaphone
speech-bubbles credit-card financial-paper globe-coin shopping-cart electric-plug globe-earth globe leaves
lightbulb sustainability education-finance laptop-education skills student student-admissions student-search
coffee flag-wave fun rocket target heart shield-benefits tooth legal scroll-shield shield checkmarked-page
clipboard-checklist media-file news resources student-records building id-badge suitcase employees handshake
open-positions people-group person person-search touchpoints candidate-pipeline circuit-board credentials dna
inbox privacy radio-tower sigma tablet-lock-check time toolbox tools touch-id worksheets community location
universal""".split())
NAV = set("""calendar checkboxes clock contact-card-matrix-manager document folder-close globe location mail
search-user star task-academic timeline-milestone time-off-balance user""".split())

# Hub title and navigation items (navigation items take wd-icon-* only).
HUB = {"icon": "credentials",
       "items": {"hubLanding": "contact-card-matrix-manager",   # RBAC Hub: roles and the people who hold them
                 "fuhLandingPage": "folder-close"}}              # FUH Administration: the organization hierarchy

# Card id -> accent icon. One icon per subject, so the same icon means the same thing everywhere.
CARDS = {
    # Role requests (asking for and tracking roles)
    "HomeRoleRequestActionsCard": "id-badge", "myRoleRequestsCard": "id-badge",
    "ListAssignableActionsCard": "id-badge", "ListAaaActionsCard": "id-badge", "IscViewPillCard": "id-badge",
    # ISC review queue (work waiting for someone)
    "PendingIscCard": "inbox", "iscQueueCard": "inbox", "MyAttentionCard": "inbox",
    # Shell organizations
    "HomeShellOrgActionsCard": "building", "ShellOrgCard": "building", "ShellOrgQuickActionsCard": "building",
    # Bulk role changes (many positions at once)
    "HomeBulkActionsCard": "people-group", "BulkActionsPillCard": "people-group",
    "BulkNextStepCard": "people-group", "BulkRelatedCard": "people-group",
    # Audit
    "AuditLogCard": "scroll-shield", "AuditTypePillCard": "scroll-shield",
    # Measures and filters
    "InsightsCard": "chart-bar-arrow", "BreakdownChart": "chart-bar-arrow", "CountCard": "sigma",
    "AuditActionChart": "scroll-shield", "ShellOrgStatusChart": "building",
    # Activity over time across the whole app
    "AppActivityChart": "time",
    "IscStatusPillCard": "gauge", "AuditPeriodPillCard": "calendar",
    "AuditByPillCard": "person", "AuditOrgPillCard": "building",
    # Outcomes and recovery
    "ShellOrgReceiptCard": "award-medal", "ShellOrgPatternReceiptCard": "award-medal",
    "ShellOrgStatusReceiptCard": "award-medal",
    "ErrorStartAgainCard": "data-refresh", "ErrorOtherPagesCard": "resources",
}


def main():
    bad = [f"{k}: {v}" for k, v in CARDS.items() if v not in ACCENT]
    bad += [f"hub: {HUB['icon']}"] * (HUB['icon'] not in ACCENT)
    bad += [f"nav {k}: {v}" for k, v in HUB['items'].items() if v not in NAV]
    if bad:
        sys.exit("apply_icons: not in Workday's icon list: " + ", ".join(bad))
    cards_dir = os.path.join(ROOT, 'presentation', 'cards')
    changed = 0
    for f in sorted(os.listdir(cards_dir)):
        cid, ext = os.path.splitext(f)
        if cid not in CARDS or ext not in ('.card', '.carddefinition'):
            continue
        p = os.path.join(cards_dir, f)
        raw = open(p, encoding='utf-8').read()
        d = json.loads(raw)
        header = d['presentation']['header'] if ext == '.carddefinition' else d.setdefault('header', {})
        icon = 'wd-accent-' + CARDS[cid]
        if header.get('icon') != icon:
            header['icon'] = icon
            open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
            changed += 1
    p = os.path.join(ROOT, 'presentation', 'home.pmd')
    d = json.loads(open(p, encoding='utf-8').read())
    hub = d['presentation']['body']
    before = json.dumps(hub)
    hub['icon'] = 'wd-accent-' + HUB['icon']
    for it in hub['navigationTasks']:
        tid = (it.get('task') or {}).get('taskId')
        if tid in HUB['items']:
            it['icon'] = 'wd-icon-' + HUB['items'][tid]
    if json.dumps(hub) != before:
        open(p, 'w', encoding='utf-8').write(json.dumps(d, indent=2, ensure_ascii=False) + '\n')
        changed += 1
    missing = [c for c in CARDS if not any(os.path.exists(os.path.join(cards_dir, c + e)) for e in ('.card', '.carddefinition'))]
    print(f"icons set in {changed} file(s)" + (f"; no card file for {missing}" if missing else ""))


if __name__ == '__main__':
    main()
