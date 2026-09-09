"""
HTML Report Generator for E2B API Compatibility Tests.
"""
import os
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))

def _normalize_reason(reason: str) -> str:
    r = reason.lower().strip()
    for sep in [" (test_", " in test_", "):", "\n"]:
        idx = r.find(sep)
        if idx > 0:
            r = r[:idx].strip()
    return r[:200] if len(r) <= 200 else r[:197] + "..."

class HTMLReportCollector:
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.platform_name = os.environ.get("E2B_PLATFORM", "unknown")
        self.api_url = os.environ.get("E2B_API_URL", "(default)")
        self.template = os.environ.get("CUBE_TEMPLATE_ID", "base")
    def set_platform(self, info: Dict[str, str]):
        self.platform_name = info.get("name", "unknown")
        self.api_url = info.get("api_url", "(default)")
        self.template = info.get("template", "base")
    def add_result(self, test_name, module, api, description,
                   success, duration, details="", error="",
                   skipped=False, skip_reason=""):
        self.results.append({
            "test_name": test_name, "module": module, "api": api,
            "description": description, "success": success,
            "duration": duration, "details": details, "error": error,
            "skipped": skipped, "skip_reason": skip_reason,
        })
    def _compute_stats(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"] and not r["skipped"])
        failed = sum(1 for r in self.results if not r["success"] and not r["skipped"])
        skipped = sum(1 for r in self.results if r["skipped"])
        denom = total - skipped
        pass_rate = (passed / denom * 100) if denom > 0 else 0
        skip_r = Counter()
        fail_r = Counter()
        for r in self.results:
            if r["skipped"] and r["skip_reason"]:
                skip_r[_normalize_reason(r["skip_reason"])] += 1
            elif not r["success"] and not r["skipped"] and r["error"]:
                fail_r[_normalize_reason(r["error"])] += 1
        return dict(total=total, passed=passed, failed=failed, skipped=skipped,
                    pass_rate=pass_rate, skip_reasons=skip_r, fail_reasons=fail_r)
    def generate(self, filepath: str):
        end_time = datetime.now()
        stats = self._compute_stats()
        modules = {}
        for r in self.results:
            modules.setdefault(r["module"], []).append(r)
        html = self._build_html(stats, modules, self.start_time, end_time)
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)
        return filepath
    def _build_module_rows(self, modules):
        rows = ""
        for mod, tests in modules.items():
            mp = sum(1 for t in tests if t["success"] and not t["skipped"])
            mf = sum(1 for t in tests if not t["success"] and not t["skipped"])
            ms = sum(1 for t in tests if t["skipped"])
            mt = len(tests)
            bc = "badge-fail" if mf else ("badge-warn" if ms else "badge-pass")
            trs = ""
            for i, t in enumerate(tests):
                tid = f"{mod}_{i}"
                if t["skipped"]:
                    si, sc, st = "\u23ed", "skipped", "SKIPPED"
                elif t["success"]:
                    si, sc, st = "\u2705", "passed", "PASSED"
                else:
                    si, sc, st = "\u274c", "failed", "FAILED"
                det = ""
                if t["api"]:
                    det += f'<p><b>API:</b> <code>{_esc(t["api"])}</code></p>'
                if t["description"]:
                    det += f'<p><b>\u9a8c\u8bc1\u70b9:</b> {_esc(t["description"])}</p>'
                det += f'<p><b>\u8017\u65f6:</b> {t["duration"]:.3f}s</p>'
                if t["details"]:
                    det += f'<p><b>\u8f93\u51fa:</b></p><pre>{_esc(t["details"][:2000])}</pre>'
                if t["error"]:
                    det += f'<p><b>\u9519\u8bef:</b></p><pre class="error-text">{_esc(t["error"][:2000])}</pre>'
                if t["skip_reason"]:
                    det += f'<p><b>\u8df3\u8fc7\u539f\u56e0:</b></p><pre>{_esc(t["skip_reason"][:2000])}</pre>'
                trs += (f'<tr class="test-row" onclick="toggleDetail(\'{tid}\')">'
                        f'<td class="icon-cell">{si}</td><td>{_esc(t["test_name"])}</td>'
                        f'<td class="{sc}">{st}</td><td>{t["duration"]:.3f}s</td></tr>'
                        f'<tr id="{tid}" class="detail-row" style="display:none">'
                        f'<td colspan="4"><div class="detail-content">{det}</div></td></tr>')
            sb = f'<span class="badge badge-skip">{ms} skipped</span>' if ms else ""
            fb = f'<span class="badge badge-fail">{mf} failed</span>' if mf else ""
            rows += (f'<div class="module-section">'
                     f'<div class="module-header" onclick="toggleModule(\'{_esc(mod)}\')">'
                     f'<span class="module-icon" id="icon_{_esc(mod)}">\u25b6</span>'
                     f'<span class="module-title">{_esc(mod)}</span>'
                     f'<span class="module-badges"><span class="badge {bc}">{mp}/{mt} passed</span>{sb}{fb}</span></div>'
                     f'<div class="module-body" id="body_{_esc(mod)}" style="display:none">'
                     f'<table class="test-table"><thead><tr>'
                     f'<th width="30"></th><th>\u7528\u4f8b</th>'
                     f'<th width="100">\u72b6\u6001</th><th width="80">\u8017\u65f6</th>'
                     f'</tr></thead><tbody>{trs}</tbody></table></div></div>')
        return rows

    def _build_html(self, stats, modules, start_time, end_time):
        total=stats["total"];passed=stats["passed"];failed=stats["failed"];skipped=stats["skipped"]
        pass_rate=stats["pass_rate"];dur=(end_time-start_time).total_seconds()
        bp=(passed/total*100) if total else 0;bf=(failed/total*100) if total else 0;bs=(skipped/total*100) if total else 0
        vi,vt,vc=("\u2705","\u65e0\u5931\u8d25\uff0c\u6240\u6709\u53ef\u6267\u884c\u7528\u4f8b\u5747\u5df2\u901a\u8fc7","verdict-pass") if failed==0 else ("\u274c","\u5b58\u5728\u5931\u8d25\u7528\u4f8b","verdict-fail")
        reason_html=self._build_reason_cards(stats)
        module_rows=self._build_module_rows(modules)
        CSS=self._css();JS=self._js()
        sp=f'<div class="seg seg-pass" style="width:{bp:.1f}%">{passed}</div>' if passed else ''
        sf=f'<div class="seg seg-fail" style="width:{bf:.1f}%">{failed}</div>' if failed else ''
        ss=f'<div class="seg seg-skip" style="width:{bs:.1f}%">{skipped}</div>' if skipped else ''
        return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>E2B API \u517c\u5bb9\u6027\u6d4b\u8bd5\u62a5\u544a</title><style>{CSS}</style></head>
<body><div class="container">
<div class="header"><h1>\U0001f9ea E2B API \u517c\u5bb9\u6027\u6d4b\u8bd5\u62a5\u544a</h1>
<div class="meta">\u5e73\u53f0: {_esc(self.platform_name)} | API: {_esc(self.api_url)} | Template: {_esc(self.template)}<br>
\u5f00\u59cb: {start_time.strftime('%Y-%m-%d %H:%M:%S')} | \u7ed3\u675f: {end_time.strftime('%Y-%m-%d %H:%M:%S')} | \u603b\u8017\u65f6: {dur:.1f}s</div></div>
<div class="verdict-banner {vc}"><div class="verdict-icon">{vi}</div><div class="verdict-info">
<div class="verdict-label">{vt}</div>
<div class="verdict-sub">{total} \u4e2a\u7528\u4f8b: {passed} \u901a\u8fc7 | {failed} \u5931\u8d25 | {skipped} \u8df3\u8fc7 &mdash; \u901a\u8fc7\u7387 {pass_rate:.1f}%</div></div></div>
<div class="stat-row">
<div class="stat-card stat-total"><div class="num">{total}</div><div class="label">\u603b\u7528\u4f8b</div></div>
<div class="stat-card stat-pass"><div class="num">{passed}</div><div class="label">\u2705 \u901a\u8fc7</div></div>
<div class="stat-card stat-fail"><div class="num">{failed}</div><div class="label">\u274c \u5931\u8d25</div></div>
<div class="stat-card stat-skip"><div class="num">{skipped}</div><div class="label">\u23ed \u8df3\u8fc7</div></div>
<div class="stat-card stat-rate"><div class="num">{pass_rate:.1f}%</div><div class="label">\u901a\u8fc7\u7387</div></div></div>
<div class="progress-bar-wrap"><div class="progress-bar">{sp}{sf}{ss}</div>
<div class="progress-legend">
<span><span class="legend-dot" style="background:var(--green)"></span>\u901a\u8fc7 {passed}</span>
<span><span class="legend-dot" style="background:var(--red)"></span>\u5931\u8d25 {failed}</span>
<span><span class="legend-dot" style="background:var(--amber)"></span>\u8df3\u8fc7 {skipped}</span></div></div>
{reason_html}
<div class="toolbar">
<button onclick="expandAll()">\u5c55\u5f00\u5168\u90e8</button>
<button onclick="collapseAll()">\u6298\u53e0\u5168\u90e8</button>
<span class="filter-label">\u7b5b\u9009:</span>
<select onchange="filterStatus(this.value)">
<option value="all">\u5168\u90e8</option><option value="PASS">\u901a\u8fc7</option>
<option value="FAIL">\u5931\u8d25</option><option value="SKIP">\u8df3\u8fc7</option></select></div>
{module_rows}
<div class="footer">Generated by E2B Compatibility Test Suite</div>
</div><script>{JS}</script></body></html>"""
    def _build_reason_cards(self, stats):
        html=""
        if stats["skip_reasons"]:
            items="".join(f'<tr><td class="reason-count">{c}</td><td class="reason-text">{_esc(r)}</td></tr>' for r,c in stats["skip_reasons"].most_common())
            html+=('<div class="reason-card"><div class="reason-header reason-header-skip">'
                   f'<span>\u23ed\ufe0f</span> \u8df3\u8fc7\u539f\u56e0\u5206\u7ec4<span class="reason-total">{stats["skipped"]} \u4e2a</span></div>'
                   f'<table class="reason-table">{items}</table></div>')
        if stats["fail_reasons"]:
            items="".join(f'<tr><td class="reason-count reason-count-fail">{c}</td><td class="reason-text reason-text-fail">{_esc(r)}</td></tr>' for r,c in stats["fail_reasons"].most_common())
            html+=('<div class="reason-card"><div class="reason-header reason-header-fail">'
                   f'<span>\u274c</span> \u5931\u8d25\u539f\u56e0\u5206\u7ec4<span class="reason-total">{stats["failed"]} \u4e2a</span></div>'
                   f'<table class="reason-table">{items}</table></div>')
        return f'<div class="reason-cards">{html}</div>' if html else ''
    def _css(self):
        css_path = os.path.join(os.path.dirname(__file__), "report_style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    def _js(self):
        return """
function toggleDetail(id) {
  var e = document.getElementById(id);
  if (!e) return;
  if (e.style.display === 'none' || e.style.display === '') {
    e.style.display = 'table-row';
  } else {
    e.style.display = 'none';
  }
}
function toggleModule(n) {
  var b = document.getElementById('body_' + n);
  var i = document.getElementById('icon_' + n);
  if (!b || !i) return;
  if (b.style.display === 'none' || b.style.display === '') {
    b.style.display = 'block';
    i.textContent = '\\u25bc';
  } else {
    b.style.display = 'none';
    i.textContent = '\\u25b6';
  }
}
function expandAll() {
  document.querySelectorAll('.module-body').forEach(function(e) { e.style.display = 'block'; });
  document.querySelectorAll('.module-icon').forEach(function(e) { e.textContent = '\\u25bc'; });
}
function collapseAll() {
  document.querySelectorAll('.module-body').forEach(function(e) { e.style.display = 'none'; });
  document.querySelectorAll('.module-icon').forEach(function(e) { e.textContent = '\\u25b6'; });
}
function filterStatus(status) {
  document.querySelectorAll('.test-row').forEach(function(row) {
    var detailRow = row.nextElementSibling;
    var statusCell = row.querySelectorAll('td')[2];
    if (!statusCell) return;
    var text = statusCell.textContent.trim().toUpperCase();
    var show = (status === 'all') || text.startsWith(status);
    row.style.display = show ? '' : 'none';
    if (detailRow && detailRow.classList.contains('detail-row')) {
      if (!show) detailRow.style.display = 'none';
    }
  });
}
"""
