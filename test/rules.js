// Pattern field rules (2026-11-07): a rule (type, length, characters or values, options) compiles to the regex every
// check already uses, and a regex the builder could have written reads back as a rule. Mirrors the Workday Script in
// presentation/scripts/comsAppSetup.script (written by tools/build_app_patterns.py); the static check Rules.engine
// runs this over the real formats, so keep the two in step.
const BS = '\\';
const TYPES = [
  ['upper', 'Capital letters'], ['upperDigits', 'Capital letters and digits'], ['digits', 'Digits'],
  ['list', 'One of a list'], ['fixed', 'Fixed text'], ['any', 'Any text'], ['regex', 'Regular expression (advanced)'],
];
// Options: [starts with a letter or digit, optional ending, shorter start + *]
const OPTIONS = {
  none: ['None', false, '', false],
  first: ['Starts with a letter or digit', true, '', false],
  star: ['May end with *', false, 'star', false],
  firstStar: ['Starts with a letter or digit, may end with *', true, 'star', false],
  campus: ['May end with _ and a campus letter (e.g. _V)', false, 'campus', false],
  letter: ['May end with a capital letter (e.g. 100A)', false, 'letter', false],
  shorter: ['Or a shorter start then * (e.g. 1*)', false, '', true],
  letterShorter: ['May end with a capital letter, or a shorter start then *', false, 'letter', true],
};
const ENDING = { star: BS + '*?', campus: '(_[A-Z])?', letter: '[A-Z]?' };
const CHARS = ['upper', 'upperDigits', 'digits'];
const trim = (s) => String(s ?? '').trim();
const esc = (v) => v.split('*').join(BS + '*').split('.').join(BS + '.').split('+').join(BS + '+');
const unesc = (v) => v.split(BS + '*').join('*').split(BS + '.').join('.').split(BS + '+').join('+');
const lo = (len) => +trim(trim(len).split('-')[0]);
const hi = (len) => (trim(len).includes('-') ? +trim(trim(len).split('-')[1]) : lo(len));
const quant = (len) => (!trim(len) ? '+' : trim(len).includes('-') ? `{${lo(len)},${hi(len)}}` : `{${lo(len)}}`);
const restQuant = (len) => (!trim(len) ? '*' : trim(len).includes('-') ? `{${lo(len) - 1},${hi(len) - 1}}` : `{${lo(len) - 1}}`);
const baseOf = (t) => (t === 'upper' ? 'A-Z' : t === 'upperDigits' ? 'A-Z0-9' : '0-9');
const extraOf = (x) => String(x ?? '').split(' ').join('');
const classOf = (t, extra) => { const x = extraOf(extra); return '[' + baseOf(t) + x.split('-').join('') + (x.includes('-') ? '-' : '') + ']'; };
const listValues = (text) => (trim(text) ? String(text).split(',').map(trim).filter(Boolean) : []);
const opt = (o) => OPTIONS[o] || OPTIONS.none;
const ruleBody = (t, len, values, o) => {
  if (CHARS.includes(t)) {
    const [, first, ending, shorter] = opt(o);
    const main = first && extraOf(values) ? '[' + baseOf(t) + ']' + classOf(t, values) + restQuant(len) : classOf(t, values) + quant(len);
    return (shorter ? classOf(t, values) + `{1,${hi(len) - 1}}` + BS + '*|' : '') + main + (ENDING[ending] || '');
  }
  if (t === 'any') return '[^: ]' + quant(len);
  if (t === 'list') return '(' + listValues(values).map(esc).join('|') + ')';
  if (t === 'fixed') return esc(trim(values));
  return '';
};
const compileRule = (t, len, values, o, blank) => (blank === true ? BS + '*|' : '') + ruleBody(t, len, values, o);

const lengthOk = (len) => {
  const l = trim(len);
  if (!l) return true;
  if (/^[0-9]+$/.test(l)) return +l > 0;
  if (/^[0-9]+ *- *[0-9]+$/.test(l)) return lo(l) > 0 && lo(l) <= hi(l);
  return false;
};
const VALUE = /^[A-Z0-9_.*\/+-]+$/;
const lengthError = (t, len, o) => {
  if ((CHARS.includes(t) || t === 'any') && !lengthOk(len)) return 'the length must be a number (3) or a range (2-6).';
  if (CHARS.includes(t) && opt(o)[3] && (!trim(len) || hi(len) < 2)) return 'a shorter start then * needs a length of 2 or more.';
  return '';
};
const valuesError = (t, values, o) => {
  if (CHARS.includes(t) && !/^[-_.*\/+]*$/.test(extraOf(values))) return 'extra characters can only be - _ . * / +';
  if (CHARS.includes(t) && opt(o)[1] && !extraOf(values)) return '"starts with a letter or digit" only matters with extra characters such as - or _.';
  if (t === 'list' && listValues(values).length < 2) return 'list at least two values, separated by commas (e.g. V, O, S).';
  if (t === 'list' && listValues(values).some((v) => !VALUE.test(v))) return 'list values use capital letters, digits and - _ . * / + only.';
  if (t === 'fixed' && !VALUE.test(trim(values))) return 'the fixed text uses capital letters, digits and - _ . * / + only.';
  return '';
};
const ruleError = (t, len, values, o) => lengthError(t, len, o) || valuesError(t, values, o);

const lengthWords = (len) => (!trim(len) ? 'one or more' : trim(len).includes('-') ? `${lo(len)} to ${hi(len)}` : `${lo(len)}`);
const WORDS = { upper: 'capital letters', upperDigits: 'capital letters or digits', digits: 'digits', any: 'characters (no colons or spaces)' };
const ENDWORDS = { star: '; may end with * to match many', campus: '; may end with _ and a campus letter (e.g. _V)', letter: '; may end with a capital letter' };
const hintFor = (t, len, values, o, blank) => {
  const x = extraOf(values);
  const [, first, ending, shorter] = opt(o);
  const core = CHARS.includes(t)
    ? `${lengthWords(len)} ${WORDS[t]}${x ? ', or any of ' + x : ''}${first && x ? ', starting with a letter or digit' : ''}${ENDWORDS[ending] || ''}${shorter ? `; or the first 1 to ${hi(len) - 1} followed by * (e.g. 1*)` : ''}`
    : t === 'any' ? `${lengthWords(len)} ${WORDS.any}`
    : t === 'list' ? `one of ${listValues(values).join(', ')}` : t === 'fixed' ? `always ${trim(values)}` : '';
  if (!core) return '';
  return core.charAt(0).toUpperCase() + core.slice(1) + (blank === true ? '. Leave blank for any.' : '.');
};

// regex -> rule: take the regex apart the way compileRule builds it, then keep the rule only if it compiles back to
// exactly the same regex. Anything else stays a regular expression.
const REGEX = { ruleType: 'regex', ruleLength: '', ruleValues: '', ruleOption: 'none' };
const asRule = (t, len, values, o, regex, blank) =>
  t && t !== 'regex' && !ruleError(t, len, values, o) && compileRule(t, len, values, o, blank) === regex
    ? { ruleType: t, ruleLength: len, ruleValues: values, ruleOption: o } : null;
const optionId = (first, ending, shorter) =>
  Object.keys(OPTIONS).find((k) => OPTIONS[k][1] === first && OPTIONS[k][2] === ending && OPTIONS[k][3] === shorter) || '';
const lenFrom = (q, plus) => {
  if (q === '+') return '';
  if (q === '*' && plus === 1) return '';
  if (!(q.startsWith('{') && q.endsWith('}'))) return 'x';
  const m = q.slice(1, -1);
  return m.includes(',') ? `${+m.split(',')[0] + plus}-${+m.split(',')[1] + plus}` : `${+m + plus}`;
};
const typeOf = (inner) => (inner.startsWith('A-Z0-9') ? 'upperDigits' : inner.startsWith('A-Z') ? 'upper' : inner.startsWith('0-9') ? 'digits' : '');
const parseChars = (body, r, blank) => {
  const shorter = body.includes(BS + '*|') && body.split(BS + '*|')[0].includes('{1,');
  let b = shorter ? body.slice(body.indexOf(BS + '*|') + 3) : body;
  const ending = Object.keys(ENDING).find((k) => b.endsWith(ENDING[k])) || '';
  if (ending) b = b.slice(0, -ENDING[ending].length);
  const c1 = b.split(']')[0].slice(1);
  const rest = b.slice(b.indexOf(']') + 1);
  const first = rest.startsWith('[');
  const inner = first ? rest.split(']')[0].slice(1) : c1;
  const q = first ? rest.slice(rest.indexOf(']') + 1) : rest;
  const t = typeOf(inner);
  const extra = t === 'upperDigits' ? inner.slice(6) : t ? inner.slice(3) : '';
  const o = optionId(first, ending, shorter);
  return o ? asRule(t, lenFrom(q, first ? 1 : 0), extra, o, r, blank) : null;
};
const parseRegex = (regex, blank) => {
  const r = trim(regex);
  const body = blank === true && r.startsWith(BS + '*|') ? r.slice(3) : r;
  let rule = null;
  if (body === '[^: ]+' || (body.startsWith('[^: ]{') && body.endsWith('}'))) rule = asRule('any', lenFrom(body.slice(5), 0), '', 'none', r, blank);
  else if (body.startsWith('[') && body.includes(']')) rule = parseChars(body, r, blank);
  else if (body.startsWith('(') && body.endsWith(')')) rule = asRule('list', '', body.slice(1, -1).split('|').filter(Boolean).map(unesc).join(', '), 'none', r, blank);
  else rule = asRule('fixed', '', unesc(body), 'none', r, blank);
  return rule || { ...REGEX };
};

module.exports = { TYPES, OPTIONS, compileRule, ruleError, lengthError, valuesError, hintFor, parseRegex };
