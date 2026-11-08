// Workday checks that look one value up (2026-11-07): a JS mirror of the query builders in
// presentation/scripts/comsPatterns.script (lookupWql, treeWql, searchWql, fillValue). The smoke suite runs these exact
// queries against Workday; Static.lookups checks every query text below still appears in the script.
const FRAGMENTS = {
  subjectCheck: "SELECT abbreviation, name FROM courseSubjects WHERE inactive = false AND abbreviation = '",
  periodCheck: "SELECT name FROM academicPeriods WHERE inactive = false AND name startswith '",
  periodWords: " AND name contains '",
  subjectTree: "SELECT abbreviation, name FROM courseSubjects WHERE inactive = false AND abbreviation startswith '",
  subjectTreeEnd: "' ORDER BY abbreviation",
  periodNoYear: 'SELECT name FROM academicPeriods WHERE inactive = false AND academicYear is empty ORDER BY name',
  periodYear: 'SELECT name FROM academicPeriods WHERE inactive = false AND academicYear in (',
  subjectSearch: "SELECT abbreviation, name FROM courseSubjects WHERE inactive = false AND (abbreviation startswith '",
  subjectSearchMid: "' OR name contains '",
  periodSearch: "SELECT name FROM academicPeriods WHERE inactive = false AND name contains '",
  unitSearch: "SELECT academicUnitCode, academicUnitName FROM academicUnits WHERE inactive = false AND academicUnitCode is not empty AND (academicUnitCode startswith '",
  unitSearchMid: "' OR academicUnitName contains '",
  subjectWid: "SELECT courseSubject FROM courseSubjects WHERE abbreviation = '",
  courseList: 'SELECT course, title FROM courseDefinitions WHERE courseSubjects in (',
};
const F = FRAGMENTS;
const text = (v) => String(v ?? '').split("'").join('').split('\\').join('').trim();
const year = (v) => (v.length < 4 ? v : v.slice(0, 4));
const words = (v) => ({ W1: 'Winter Term 1', W2: 'Winter Term 2', W: 'Winter', S: 'Summer' }[v.length > 4 ? v.slice(4) : ''] || '');
const lookupWql = (kind, v) => {
  const t = text(v);
  if (!t || t.startsWith('*')) return '';
  if (kind === 'courseSubject') return F.subjectCheck + t + "'";
  if (kind === 'academicPeriod') return F.periodCheck + year(t) + "'" + (words(t) ? F.periodWords + words(t) + "'" : '');
  return '';
};
const treeWql = (kind, folder) => (kind === 'courseSubject' ? F.subjectTree + text(folder).replace(/^.*?LETTER_/, '') + F.subjectTreeEnd
  : folder === 'NOYEAR' ? F.periodNoYear : F.periodYear + text(folder) + ') ORDER BY name');
const searchWql = (kind, q) => (kind === 'courseSubject' ? F.subjectSearch + text(q) + F.subjectSearchMid + text(q) + "') ORDER BY abbreviation"
  : kind === 'academicUnitCode' ? F.unitSearch + text(q) + F.unitSearchMid + text(q) + "') ORDER BY academicUnitCode"
  : F.periodSearch + text(q) + "' ORDER BY name");
// wildcard choices offered when the field's format allows them (comsPatterns.wildcards / yearCodes)
const wildcards = (regex) => ['*', '*W1', '*W2', '*S', '1*', '2*', '3*', '4*', '5*', '6*'].filter((c) => new RegExp('^(?:' + regex + ')$').test(c));
const yearCodes = (regex, periodName) => { const y = year(periodName); return [y, y + 'W', (/^[0-9]+$/.test(y) ? String(+y + 1) : y) + 'S'].filter((c) => new RegExp('^(?:' + regex + ')$').test(c)); };
const fillValue = (kind, id) => {
  if (id.startsWith('CODE:')) return id.slice(5);
  if (kind !== 'academicPeriod') return id;
  const name = id.split('|')[0]; const y = year(name);
  return name.includes('Winter Term 1') ? y + 'W1' : name.includes('Winter Term 2') ? y + 'W2' : name.includes('Summer') ? y + 'S' : name.includes('Winter') ? y + 'W' : '';
};
// a course list: the picked subject's WID first, then its courses (comsPatterns.subjectWql / courseWql)
const subjectWql = (abbr) => (text(abbr) && !text(abbr).startsWith('*') ? F.subjectWid + text(abbr) + "'" : '');
const courseWql = (rows) => (rows && rows[0] && rows[0].courseSubject ? F.courseList + text(rows[0].courseSubject.id) + ')' : '');
module.exports = { subjectWql, courseWql, FRAGMENTS, lookupWql, treeWql, searchWql, fillValue, wildcards, yearCodes };
