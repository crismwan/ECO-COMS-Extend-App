"""Helpers to fill the Confluence-exported template HTML (UBC Workday Solutions SDLC template v2.0)."""
import html as _html, re
from bs4 import BeautifulSoup, NavigableString


class H(str):
    """Raw HTML value (not escaped)."""


def esc(t):
    return _html.escape(t, quote=False)


def cell_html(v):
    """Plain text: '\n' splits paragraphs; lines starting with '• ' become a bullet list. H(...) is raw HTML."""
    if isinstance(v, H):
        return str(v)
    out, bullets = [], []
    for line in str(v).split('\n'):
        if line.startswith('• '):
            bullets.append('<li>' + esc(line[2:]) + '</li>')
            continue
        if bullets:
            out.append('<ul>' + ''.join(bullets) + '</ul>'); bullets = []
        out.append('<p>' + (esc(line) if line else '<br/>') + '</p>')
    if bullets:
        out.append('<ul>' + ''.join(bullets) + '</ul>')
    return ''.join(out)


def frag(soup, s):
    return BeautifulSoup(s, 'html.parser')


def tables(soup):
    return soup.find_all('table')


def T(soup, start, nth=0):
    """Table whose first cell text starts with `start`."""
    hits = [t for t in soup.find_all('table')
            if t.find('tr') and t.find('tr').find(['td', 'th']) and
            t.find('tr').find(['td', 'th']).get_text(' ', strip=True).startswith(start)]
    if len(hits) <= nth:
        raise KeyError(start)
    return hits[nth]


def _fill_td(td, v, soup):
    td.clear()
    for n in list(frag(soup, cell_html(v)).contents):
        td.append(n)


def set_rows(soup, table, rows, keep=1, bold_first=False):
    trs = table.find_all('tr')
    tbody = trs[0].parent
    for tr in trs[keep:]:
        tr.decompose()
    ncols = len(trs[0].find_all(['td', 'th']))
    for r in rows:
        tr = soup.new_tag('tr')
        for i in range(ncols):
            td = soup.new_tag('td', attrs={'class': 'confluenceTd'})
            v = r[i] if i < len(r) else ''
            if bold_first and i == 0 and not isinstance(v, H):
                v = H('<p><strong>' + esc(v) + '</strong></p>')
            _fill_td(td, v, soup)
            tr.append(td)
        tbody.append(tr)


def kv(soup, table, key, value, col=1):
    for tr in table.find_all('tr'):
        cells = tr.find_all(['td', 'th'])
        if cells and cells[0].get_text(' ', strip=True).startswith(key):
            _fill_td(cells[col], value, soup)
            return
    raise KeyError(key)


def set_cell(soup, table, r, c, value):
    _fill_td(table.find_all('tr')[r].find_all(['td', 'th'])[c], value, soup)


def wrap_of(table):
    p = table.parent
    return p if p.name == 'div' and 'table-wrap' in p.get('class', []) else table


def insert_after(soup, elem, html_s):
    nodes = list(frag(soup, html_s).contents)
    for n in reversed(nodes):
        elem.insert_after(n)


def insert_before(soup, elem, html_s):
    for n in list(frag(soup, html_s).contents):
        elem.insert_before(n)


def heading(soup, start, tags=('h1', 'h2', 'h3', 'p')):
    for h in soup.find_all(tags):
        if h.get_text(' ', strip=True).startswith(start):
            return h
    raise KeyError(start)


def p_after_heading(soup, start):
    """The first paragraph after a heading (guidance text), to place content after it."""
    return heading(soup, start).find_next_sibling()


def img(src, alt, width=900):
    return (f'<p><img src="{src}" alt="{esc(alt)}" title="{esc(alt)}" width="{width}" '
            f'style="max-width:100%"/></p><p><em>{esc(alt)}</em></p>')


def para(t):
    return cell_html(t)


def replace_placeholders(soup, mapping):
    for s in soup.find_all(string=True):
        txt = str(s)
        for a, b in mapping.items():
            if a in txt:
                txt = txt.replace(a, b)
        if txt != str(s):
            s.replace_with(NavigableString(txt))


def diagram_html(soup, title_start, html_s):
    """Put HTML after the last guidance paragraph of a 'Diagram — …' block (paragraphs with class dh)."""
    p = heading(soup, title_start, tags=('p',))
    last = p
    while last.find_next_sibling() is not None and 'dh' in (last.find_next_sibling().get('class') or []):
        last = last.find_next_sibling()
    insert_after(soup, last, html_s)
