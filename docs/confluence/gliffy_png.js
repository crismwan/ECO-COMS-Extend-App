// Render a Gliffy file made by gliffy.py to PNG (the preview Gliffy's Confluence macro shows on the page).
// Usage: node gliffy_png.js in.gliffy out.png
const fs = require('fs');
const { chromium } = require('playwright');
const [, , inFile, outFile] = process.argv;
const g = JSON.parse(fs.readFileSync(inFile, 'utf8'));
const sc = g.pages[0].scene;
const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
let svg = [];
const byId = {};
for (const o of sc.objects) byId[o.id] = o;
const textOf = (t) => t.graphic.Text.html.replace(/<\/p>/g, '\n').replace(/<[^>]+>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").trim();
function text(t, ox, oy) {
  const T = t.graphic.Text; const lines = textOf(t).split('\n');
  const bold = /font-weight:bold/.test(T.html); const size = +(T.html.match(/font-size:(\d+)px/) || [0, 12])[1];
  const left = /text-align:left/.test(T.html); const lh = size * 1.25;
  const x = ox + t.x + (left ? 6 : t.width / 2);
  const top = T.valign === 'top' ? oy + t.y + 6 + size : oy + t.y + t.height / 2 - (lines.length - 1) * lh / 2 + size * 0.35;
  return `<text x="${x}" y="${top}" font-family="Arial" font-size="${size}" ${bold ? 'font-weight="bold"' : ''} text-anchor="${left ? 'start' : 'middle'}">` +
    lines.map((l, i) => `<tspan x="${x}" dy="${i ? lh : 0}">${esc(l)}</tspan>`).join('') + '</text>';
}
for (const o of sc.objects) {
  if (o.graphic.type === 'Shape') {
    const S = o.graphic.Shape; const r = o.uid.includes('round') ? 10 : 0;
    svg.push(`<rect x="${o.x}" y="${o.y}" width="${o.width}" height="${o.height}" rx="${r}" fill="${S.fillColor}" stroke="${S.strokeColor}" stroke-width="${S.strokeWidth}"/>`);
    for (const c of o.children || []) svg.push(text(c, o.x, o.y));
  } else if (o.graphic.type === 'Line') {
    const L = o.graphic.Line; const p = L.controlPath.map(([x, y]) => [o.x + x, o.y + y]);
    svg.push(`<polyline points="${p.map((q) => q.join(',')).join(' ')}" fill="none" stroke="${L.strokeColor}" stroke-width="${L.strokeWidth}" ${L.dashStyle ? 'stroke-dasharray="4,4"' : ''} ${L.endArrow ? 'marker-end="url(#a)"' : ''}/>`);
  } else if (o.graphic.type === 'Text') {
    svg.push(`<rect x="${o.x + 3}" y="${o.y + 2}" width="${o.width - 6}" height="${o.height - 4}" fill="#ffffff" opacity="0.85"/>`);
    svg.push(text(o, 0, 0));
  }
}
const W = Math.ceil(sc.width), H = Math.ceil(sc.height);
const page = `<html><body style="margin:0;background:#fff"><svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}">
<defs><marker id="a" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#333"/></marker></defs>
${svg.join('\n')}</svg></body></html>`;
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await p.setContent(page); await p.screenshot({ path: outFile, clip: { x: 0, y: 0, width: W, height: H } }); await b.close();
})();
