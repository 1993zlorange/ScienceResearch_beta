from __future__ import annotations

import html
import json
import base64
import cgi
import tempfile
import shutil
import secrets
import http.cookies
import re
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from .bootstrap import create_workbench
from .domain.errors import AppError


def _as_bool(value: object) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() in {"1", "true", "yes", "on"})


_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_NAVIGATION_ITEMS = (
    ("home", "/", "总览"),
    ("technical-docs", "/technical-docs", "技术说明"),
    ("contexts", "/contexts", "课题流程"),
    ("weeks", "/weeks", "周计划"),
    ("reports", "/reports", "报告与成效卡"),
    ("skills", "/skills", "Skills"),
    ("governance", "/governance", "治理"),
    ("operations", "/operations", "运维"),
)


def _navigation_items() -> tuple[tuple[str, str, str], ...]:
    """Load the same top-level navigation contract used by the Vue shell."""

    config_path = _PROJECT_ROOT / "config" / "main-navigation.json"
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        items = tuple(
            (str(item["id"]), str(item["path"]), str(item["label"]))
            for item in raw["items"]
            if item.get("path") != "/work-packages"
        )
        return items if items else _DEFAULT_NAVIGATION_ITEMS
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return _DEFAULT_NAVIGATION_ITEMS


def shell(title: str, body: str, active: str = "home") -> str:
    nav_items = _navigation_items()
    links = []
    for key, href, label in nav_items:
        current = key == active
        class_name = " class='active'" if current else ""
        aria_current = " aria-current='page'" if current else ""
        links.append(f"<a href='{href}'{class_name}{aria_current}>{label}</a>")
    nav = "<nav class='nav' aria-label='主导航'>" + "".join(links) + "</nav>"
    css = """
:root{--navy:#173b57;--blue:#2d7ba7;--primary:#17668e;--orange:#d4772e;--ink:#17212b;--muted:#667382;--line:#dce3e8;--paper:#f6f8fa;--panel:#fff;--green:#32836a;--shadow:0 10px 30px rgba(23,59,87,.08)}
*{box-sizing:border-box}[hidden]{display:none!important}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);background:var(--paper);font:14px/1.6 "Segoe UI","Microsoft YaHei",sans-serif}a{color:#17668e}button,input,textarea,select{font:inherit}.skip-link{position:fixed;z-index:100;left:12px;top:12px;transform:translateY(-160%);background:#fff;color:var(--navy);padding:9px 13px;border-radius:6px;box-shadow:var(--shadow)}.skip-link:focus{transform:none}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.shell{display:grid;grid-template-columns:270px minmax(0,1fr);min-height:100vh}.side{background:var(--navy);color:#eef5f8;padding:24px 18px;position:sticky;top:0;height:100vh;overflow:auto}.brand{font-size:20px;font-weight:700}.brand small{display:block;color:#a9c4d2;font-size:12px;font-weight:400}.side-note{color:#b9d0db;font-size:12px;margin:22px 4px}.nav{display:flex;flex-direction:column;gap:4px}.nav a{color:#dcecf2;text-decoration:none;padding:10px 11px;border-radius:7px;border:1px solid transparent}.nav a:hover,.nav a.active{background:#2b5d78;color:#fff}.nav a.active{border-color:#75a9c4}.main{max-width:1450px;width:100%;margin:auto;padding:28px 34px 60px;min-width:0}.top{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:22px}.eyebrow{color:var(--orange);font-weight:700;font-size:12px;letter-spacing:.1em}.top h1{margin:3px 0 5px;font-size:30px;line-height:1.25}.top p{margin:0;color:var(--muted)}.actions{display:flex;gap:8px;flex-wrap:wrap}.btn,button{display:inline-flex;align-items:center;justify-content:center;background:#fff;border:1px solid var(--line);color:var(--navy);padding:8px 12px;border-radius:6px;cursor:pointer;text-decoration:none}.btn.primary,button.primary,form button[type=submit],form button:not([type]){background:var(--orange);border-color:var(--orange);color:#fff}.builder button.secondary{background:#fff;border-color:var(--line);color:var(--navy)}.btn:hover,button:hover{filter:brightness(.97)}button:disabled{cursor:wait;opacity:.68}a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:3px solid #f2b46c;outline-offset:2px}.summary,.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.stat,.panel,section{background:#fff;border:1px solid var(--line);padding:18px;box-shadow:var(--shadow);border-radius:7px;margin:.8rem 0;min-width:0}.stat b{display:block;font-size:24px;color:var(--navy)}.stat span,.muted{color:var(--muted);font-size:12px}.workspace{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(330px,.65fr);gap:18px;align-items:start}.panel-head{display:flex;justify-content:space-between;align-items:center;gap:12px;border-bottom:1px solid var(--line);padding-bottom:12px}.panel-head h2{margin:0;font-size:17px}.directory-tools{display:grid;grid-template-columns:minmax(190px,1fr) minmax(155px,.55fr) auto;gap:9px;align-items:end;padding:14px 0 8px}.directory-tools label{display:grid;gap:4px;color:var(--muted);font-size:12px}.directory-tools input,.directory-tools select{width:100%;background:#fff}.filter-meta{display:flex;align-items:center;justify-content:space-between;gap:10px;min-height:28px}.filter-empty{padding:28px 14px;text-align:center;border:1px dashed var(--line);border-radius:7px;background:#fbfcfd}.aspect-card{border-bottom:1px solid #edf1f3;padding-bottom:12px}.aspect-card h3,.task h4{margin:0;color:var(--navy)}.task-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin-top:10px}.task{display:block;border:1px solid var(--line);border-radius:6px;padding:11px 12px;background:#fbfcfd;text-decoration:none;color:var(--ink)}.task:hover,.task.selected,.task[aria-current=true]{border-color:var(--blue);background:#f2f8fb;box-shadow:0 4px 12px rgba(45,123,167,.14)}.task[aria-current=true]{box-shadow:inset 4px 0 0 var(--orange),0 4px 12px rgba(45,123,167,.14)}.task p{margin:3px 0;color:var(--muted);font-size:12px}.badge{font-size:11px;color:#fff;background:var(--blue);padding:2px 7px;border-radius:10px}.detail{position:sticky;top:20px}.detail h3{color:var(--navy)}.detail-label{color:var(--orange);font-weight:700;margin-bottom:0}.selection-status{min-height:1.5em;margin:8px 0 0}.builder label{display:block;color:var(--muted);font-size:12px}.builder input,.builder textarea{width:100%;margin-top:4px}.builder-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.builder-actions{display:flex;gap:8px;flex-wrap:wrap;width:100%}.output{background:#17212b;color:#eaf4f7;padding:12px;border-radius:5px;white-space:pre-wrap;min-height:110px}.copy-status{min-height:1.5em;color:var(--muted)}table{width:100%;border-collapse:collapse}th,td{border-bottom:1px solid #e2e5e9;padding:.55rem;text-align:left;vertical-align:top}form{display:flex;gap:.5rem;flex-wrap:wrap;padding:.7rem 0}input,textarea,select{max-width:100%;padding:.5rem;border:1px solid #b9c2ce;border-radius:4px}textarea{min-width:min(24rem,100%);min-height:5rem}.mono{font-family:ui-monospace,monospace;white-space:pre-wrap}
@media(max-width:1000px){.shell{grid-template-columns:1fr}.side{position:relative;height:auto;padding:15px}.nav{flex-direction:row;overflow-x:auto;overscroll-behavior-inline:contain;scrollbar-width:thin;padding-bottom:5px}.nav a{min-width:max-content}.main{padding:20px 16px}.workspace{grid-template-columns:1fr}.detail{position:static}.summary{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.top{display:block}.actions{margin-top:15px}.summary{grid-template-columns:1fr}.task-list,.builder-grid,.grid{grid-template-columns:1fr}.panel-head{display:block}.directory-tools{grid-template-columns:1fr}.filter-meta{align-items:flex-start;flex-direction:column}.btn,button,input,textarea,select{max-width:100%}table{display:block;max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}.builder-actions>*{flex:1 1 100%}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition-duration:.01ms!important;animation-duration:.01ms!important;animation-iteration-count:1!important}}
"""
    return f"<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>{html.escape(title)}</title><style>{css}</style></head><body><a class='skip-link' href='#main-content'>跳到主要内容</a><div class='shell'><aside class='side'><div class='brand'>科研工作台<small>科研工作分解 · 每周组会</small></div><div class='side-note'>问题 → 行动 → 证据 → 结论 → 下一步<br>离线运行 · 作者确认优先</div>{nav}</aside><main class='main' id='main-content' tabindex='-1'><header class='top'><div><div class='eyebrow'>WEEKLY RESEARCH REVIEW</div><h1>科研工作分解与组会汇报</h1><p>8 个科研方面 · 68 个可执行工作包 · 证据优先</p></div><div class='actions'><a class='btn primary' href='/contexts'>进入课题流程</a><a class='btn' href='/reports'>生成周报</a></div></header>{body}</main></div></body></html>"

def page(app: ResearchWorkbench) -> str:
    catalog = app.catalog()
    contexts = app.list_contexts()
    weeks = app.list_weeks()
    packages: list[dict[str, str]] = []
    aspect_cards: list[str] = []
    for area in catalog["areas"]:
        task_cards: list[str] = []
        for package in area["work_packages"]:
            template = package.get("template", {})
            selected = not packages
            view = {
                "id": str(package["id"]),
                "area_id": str(area["id"]),
                "area": str(area["name"]),
                "name": str(package["name"]),
                "action": str(package["action"]),
                "deliverable": str(package["deliverable"]),
                "report": str(template.get("report", "问题—行动—证据—结论—下一步")),
                "example": str(template.get("example", "请在详情页补充研究示例。")),
            }
            packages.append(view)
            task_cards.append(
                "<a class='task work-package-card"
                + (" selected" if selected else "")
                + "' href='/work-packages/"
                + html.escape(view["id"], quote=True)
                + "' data-work-package='"
                + html.escape(view["id"], quote=True)
                + "' data-area-id='"
                + html.escape(view["area_id"], quote=True)
                + "' aria-controls='work-package-detail' aria-current='"
                + ("true" if selected else "false")
                + "'><h4>"
                + html.escape(view["id"])
                + " · "
                + html.escape(view["name"])
                + "</h4><p>"
                + html.escape(view["deliverable"])
                + "</p></a>"
            )
        aspect_cards.append(
            "<article class='aspect-card' data-aspect-id='"
            + html.escape(str(area["id"]), quote=True)
            + "'><h3>"
            + html.escape(str(area["name"]))
            + " <span class='badge'>"
            + str(len(area["work_packages"]))
            + " 个</span></h3><div class='task-list'>"
            + "".join(task_cards)
            + "</div></article>"
        )
    first = packages[0]
    package_json = json.dumps(packages, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    area_options = "".join(
        "<option value='" + html.escape(str(area["id"]), quote=True) + "'>" + html.escape(str(area["name"])) + "</option>"
        for area in catalog["areas"]
    )
    detail = f"""
<aside class='panel detail' id='work-package-detail' aria-labelledby='detail-heading'>
  <div class='panel-head'><h2 id='detail-heading'>工作包详情</h2><span class='badge' id='detail-id'>{html.escape(first['id'])}</span></div>
  <h3 id='detail-name'>{html.escape(first['name'])}</h3>
  <p class='muted' id='detail-area'>{html.escape(first['area'])}</p>
  <p class='detail-label'>怎么执行</p><p id='detail-action'>{html.escape(first['action'])}</p>
  <p class='detail-label'>可验收交付物</p><p id='detail-deliverable'>{html.escape(first['deliverable'])}</p>
  <p class='detail-label'>组会汇报措辞</p><p id='detail-report'>{html.escape(first['report'])}</p>
  <p class='detail-label'>研究示例</p><p id='detail-example'>{html.escape(first['example'])}</p>
  <a class='btn primary' id='detail-link' href='/work-packages/{html.escape(first['id'], quote=True)}'>打开模板、产物和 Skill</a>
  <p class='muted selection-status' id='selection-status' role='status'>当前选择：{html.escape(first['id'])} · {html.escape(first['name'])}</p>
</aside>
"""
    builder = """
<section class='panel builder' id='weekly-summary-builder'>
  <div class='panel-head'><div><h2>本周组会摘要生成器</h2><p class='muted' id='draft-status' role='status'>草稿尚未修改</p></div><span class='badge'>仅保存未提交草稿</span></div>
  <form id='summary-form' action='/reports' method='get'>
    <label>本周目标<textarea id='goal' name='goal' placeholder='本周聚焦于……，目的是判断/完成……'></textarea></label>
    <div class='builder-grid'>
      <label>新增认识<input id='insight' name='insight' placeholder='本周新增的核心认识是……'></label>
      <label>关键证据/产物<input id='evidence' name='evidence' placeholder='由……结果或文件支持'></label>
      <label>当前问题<input id='problem' name='problem' placeholder='目前还不能判断……'></label>
      <label>下周行动<input id='next' name='next' placeholder='下周优先完成……，标准是……'></label>
    </div>
    <label>已有周记录 ID（可选，用于进入正式 ReportModel）<input id='week-id' name='week_id' placeholder='WEEK-...'></label>
    <div class='builder-actions'>
      <button class='primary' type='button' id='generate-summary'>生成摘要</button>
      <button type='button' id='copy-report'>复制汇报摘要</button>
      <button type='button' id='clear-draft'>清空本机草稿</button>
      <button class='secondary' type='submit'>进入正式报告</button>
    </div>
  </form>
  <pre class='output' id='summary-output' tabindex='0'>填写上方内容后，可在这里生成“问题—行动—证据—结论—下一步”摘要。</pre>
  <p class='copy-status' id='copy-status' role='status'></p>
  <p><a href='/weeks'>进入周计划</a> · <a href='/contexts'>查看课题流程</a> · <a href='/reports'>报告与成效卡</a></p>
</section>
"""
    script = f"""
<script>
(() => {{
  const packages = {package_json};
  const byId = new Map(packages.map(item => [item.id, item]));
  const cards = Array.from(document.querySelectorAll('[data-work-package]'));
  const aspects = Array.from(document.querySelectorAll('[data-aspect-id]'));
  const setText = (id, value) => {{ const node = document.getElementById(id); if (node) node.textContent = value || '待补充'; }};
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const selectPackage = (item, card, announce = true, shouldScroll = false) => {{
    if (!item || !card) return;
    cards.forEach(node => {{ node.classList.remove('selected'); node.setAttribute('aria-current', 'false'); }});
    card.classList.add('selected'); card.setAttribute('aria-current', 'true');
    setText('detail-id', item.id); setText('detail-name', item.name); setText('detail-area', item.area);
    setText('detail-action', item.action); setText('detail-deliverable', item.deliverable);
    setText('detail-report', item.report); setText('detail-example', item.example);
    const link = document.getElementById('detail-link'); if (link) link.href = '/work-packages/' + encodeURIComponent(item.id);
    if (announce) setText('selection-status', '当前选择：' + item.id + ' · ' + item.name);
    if (shouldScroll && window.matchMedia('(max-width: 1000px)').matches) {{
      document.getElementById('work-package-detail')?.scrollIntoView({{behavior: reducedMotion.matches ? 'auto' : 'smooth', block: 'start'}});
    }}
  }};
  cards.forEach(card => {{
    card.addEventListener('click', event => {{
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      const item = byId.get(card.dataset.workPackage);
      if (!item) return;
      event.preventDefault();
      selectPackage(item, card, true, true);
    }});
  }});
  const search = document.getElementById('work-package-search');
  const aspectFilter = document.getElementById('aspect-filter');
  const filterStatus = document.getElementById('filter-status');
  const filterEmpty = document.getElementById('filter-empty');
  const resetFilter = document.getElementById('reset-filter');
  const normalize = value => String(value || '').trim().toLocaleLowerCase('zh-CN');
  const applyFilter = () => {{
    const query = normalize(search?.value);
    const areaId = aspectFilter?.value || '';
    let visibleCount = 0;
    cards.forEach(card => {{
      const item = byId.get(card.dataset.workPackage);
      const haystack = normalize([item?.id, item?.area, item?.name, item?.action, item?.deliverable, item?.report].join(' '));
      const visible = Boolean(item) && (!areaId || item.area_id === areaId) && (!query || haystack.includes(query));
      card.hidden = !visible;
      if (visible) visibleCount += 1;
    }});
    aspects.forEach(aspect => {{ aspect.hidden = !aspect.querySelector('[data-work-package]:not([hidden])'); }});
    if (filterStatus) filterStatus.textContent = '命中 ' + visibleCount + ' / ' + packages.length + ' 个工作包';
    if (filterEmpty) filterEmpty.hidden = visibleCount !== 0;
    if (resetFilter) resetFilter.hidden = !query && !areaId;
    const selected = document.querySelector('[data-work-package][aria-current="true"]');
    if (visibleCount && (!selected || selected.hidden)) {{
      const firstVisible = document.querySelector('[data-work-package]:not([hidden])');
      if (firstVisible) selectPackage(byId.get(firstVisible.dataset.workPackage), firstVisible, true, false);
    }}
  }};
  search?.addEventListener('input', applyFilter);
  aspectFilter?.addEventListener('change', applyFilter);
  resetFilter?.addEventListener('click', () => {{
    if (search) search.value = '';
    if (aspectFilter) aspectFilter.value = '';
    applyFilter(); search?.focus();
  }});
  applyFilter();
  const fieldIds = ['goal','insight','evidence','problem','next'];
  const draftKey = 'scienceresearch.weekly-summary-draft.v1';
  const read = id => (document.getElementById(id)?.value || '').trim();
  const build = () => [
    read('goal') || '本周聚焦于……，目的是判断/完成……',
    read('insight') || '本周新增的核心认识是……',
    '关键证据/产物：' + (read('evidence') || '待补充'),
    '当前问题：' + (read('problem') || '目前还不能判断……'),
    '下周行动：' + (read('next') || '优先完成……，完成标准是……')
  ].join('\\n');
  const output = document.getElementById('summary-output');
  const draftStatus = document.getElementById('draft-status');
  const copyStatus = document.getElementById('copy-status');
  const render = () => {{ if (output) output.textContent = build(); }};
  const setDraftStatus = message => {{ if (draftStatus) draftStatus.textContent = message; }};
  const timeLabel = () => new Intl.DateTimeFormat('zh-CN', {{hour:'2-digit', minute:'2-digit'}}).format(new Date());
  let restored = false;
  try {{
    const saved = JSON.parse(localStorage.getItem(draftKey) || '{{}}');
    fieldIds.forEach(id => {{
      const node = document.getElementById(id);
      if (node && typeof saved[id] === 'string') {{ node.value = saved[id]; restored = restored || Boolean(saved[id]); }}
    }});
    if (restored) setDraftStatus('已恢复本浏览器中的未提交草稿');
  }} catch (_) {{ setDraftStatus('草稿读取失败，不影响服务端数据'); }}
  fieldIds.forEach(id => document.getElementById(id)?.addEventListener('input', () => {{
    const draft = Object.fromEntries(fieldIds.map(key => [key, read(key)]));
    try {{ localStorage.setItem(draftKey, JSON.stringify(draft)); setDraftStatus('本机草稿已保存 · ' + timeLabel()); }}
    catch (_) {{ setDraftStatus('浏览器禁止保存草稿，可继续生成或手动复制'); }}
    render();
  }}));
  document.getElementById('generate-summary')?.addEventListener('click', () => {{
    render(); output?.focus();
    if (copyStatus) copyStatus.textContent = '摘要已根据当前字段重新生成。';
  }});
  document.getElementById('clear-draft')?.addEventListener('click', () => {{
    const hasContent = fieldIds.some(id => Boolean(read(id)));
    if (hasContent && !window.confirm('只清空本浏览器中的未提交摘要草稿？服务端数据不会受影响。')) return;
    fieldIds.forEach(id => {{ const node = document.getElementById(id); if (node) node.value = ''; }});
    try {{ localStorage.removeItem(draftKey); setDraftStatus('本机草稿已清空'); }}
    catch (_) {{ setDraftStatus('字段已清空，但浏览器存储不可用'); }}
    render(); if (copyStatus) copyStatus.textContent = '摘要字段已恢复为空白模板。';
    document.getElementById('goal')?.focus();
  }});
  let copyResetTimer;
  document.getElementById('copy-report')?.addEventListener('click', async () => {{
    render();
    const button = document.getElementById('copy-report');
    if (copyResetTimer) window.clearTimeout(copyResetTimer);
    if (button) {{ button.disabled = true; button.setAttribute('aria-busy', 'true'); button.textContent = '正在复制…'; }}
    if (copyStatus) copyStatus.textContent = '正在复制摘要。';
    try {{
      if (!navigator.clipboard) throw new Error('clipboard unavailable');
      await navigator.clipboard.writeText(output?.textContent || '');
      if (copyStatus) copyStatus.textContent = '摘要已复制到剪贴板。';
    }} catch (_) {{
      output?.focus();
      const selection = window.getSelection(); const range = document.createRange();
      if (output && selection) {{ range.selectNodeContents(output); selection.removeAllRanges(); selection.addRange(range); }}
      if (copyStatus) copyStatus.textContent = '浏览器未允许自动复制，摘要已选中，请按 Ctrl+C 手动复制。';
    }} finally {{
      if (button) {{ button.disabled = false; button.removeAttribute('aria-busy'); button.textContent = '复制汇报摘要'; }}
      copyResetTimer = window.setTimeout(() => {{ if (copyStatus) copyStatus.textContent = ''; }}, 4000);
    }}
  }});
  render();
}})();
</script>
"""
    stats = (
        "<section class='summary'><div class='stat'><b>8</b><span>科研方面</span></div>"
        "<div class='stat'><b>68</b><span>可执行工作包</span></div>"
        f"<div class='stat'><b>{len(contexts)}</b><span>研究上下文</span></div>"
        f"<div class='stat'><b>{len(weeks)}</b><span>周计划记录</span></div></section>"
    )
    directory = (
        "<div class='workspace'><section class='panel' id='work-package-directory'><div class='panel-head'><h2>工作包目录（8方面 / 68包）</h2>"
        "<span class='muted'>输入即筛选；无脚本时提交到完整目录</span></div>"
        "<form class='directory-tools' id='work-package-filter' method='get' action='/work-packages'>"
        "<label for='work-package-search'>搜索工作包<input id='work-package-search' name='q' "
        "placeholder='名称、行动、交付物或汇报措辞' autocomplete='off'></label>"
        "<label for='aspect-filter'>科研方面<select id='aspect-filter' name='area'><option value=''>全部 8 个方面</option>"
        + area_options
        + "</select></label><button type='submit'>在完整目录中搜索</button></form>"
        "<div class='filter-meta'><p class='muted' id='filter-status' role='status'>命中 68 / 68 个工作包</p>"
        "<button type='button' id='reset-filter' hidden>清除筛选</button></div>"
        "<div class='filter-empty' id='filter-empty' role='status' hidden><strong>没有匹配的工作包</strong><p class='muted'>请缩短关键词，或切换到“全部 8 个方面”。</p></div>"
        "<noscript><p class='muted'>浏览器未启用 JavaScript；68 个工作包仍可直接打开，也可提交上方表单进入服务端搜索。</p></noscript>"
        + "".join(aspect_cards)
        + "</section><div>"
        + detail
        + builder
        + "</div></div>"
    )
    return shell("科研工作分解与组会汇报", stats + directory + script, active="home")

def work_packages_page(app: ResearchWorkbench, query: str = "", area_id: str = "") -> str:
    areas = "".join(f"<option value='{html.escape(a['id'])}' {'selected' if a['id']==area_id else ''}>{html.escape(a['name'])}</option>" for a in app.catalog()["areas"])
    rows = "".join(f"<tr><td><a href='/work-packages/{item['id']}'>{item['id']}</a></td><td>{html.escape(item['area_name'])}</td><td>{html.escape(item['name'])}</td><td>模板 v1 · 人工指导 Skill</td><td>{html.escape(item['deliverable'])}</td></tr>" for item in app.search_catalog(query, area_id))
    return shell("工作包目录", f"<div class='grid'><section><h2>科研方面</h2><strong>8</strong><p class='muted'>沿用组会原型的八方面导航语义。</p></section><section><h2>稳定工作包</h2><strong>68</strong><p class='muted'>目录快照版本 20260828，模板和人工 Skill 可从详情进入。</p></section></div><section><h2>工作包搜索与筛选</h2><form method='get'><input name='q' value='{html.escape(query)}' placeholder='名称、行动、交付物或汇报措辞'><select name='area'><option value=''>全部方面</option>{areas}</select><button>筛选</button></form><p class='muted'>命中 {len(app.search_catalog(query, area_id))} 项 · 空查询显示全部 68 项</p><table><tr><th>ID</th><th>方面</th><th>工作包</th><th>模板/Skill</th><th>交付物</th></tr>{rows or '<tr><td colspan=5>无匹配结果</td></tr>'}</table></section>", active="work-packages")


def work_package_detail(app: ResearchWorkbench, work_package_id: str, notice: str = "") -> str:
    item = app.get_work_package(work_package_id); template = item["template"]; skill = item["skill"]
    fields = "".join(f"<tr><th>{html.escape(key)}</th><td>{html.escape(str(value))}</td></tr>" for key, value in template.items())
    guidance = "".join(f"<li>{html.escape(str(step))}</li>" for step in skill.get("manual_guidance", []))
    wp_id = html.escape(item["id"]); name = html.escape(item["name"]); area = html.escape(item["area_name"]); action = html.escape(item["action"]); deliverable = html.escape(item["deliverable"])
    skill_id = html.escape(skill["id"]); skill_version = html.escape(skill["version"]); skill_status = html.escape(skill["status"]); failure = html.escape(skill["failure_strategy"]); outputs = html.escape(str(skill["outputs"]))
    template_id = html.escape(template["id"])
    context_options = []
    workflow_options = []
    item_options = []
    for context in app.list_contexts():
        context_options.append(f"<option value='{html.escape(context['id'], quote=True)}'>{html.escape(context['name'])} · {html.escape(context['id'])}</option>")
        workflow_options.extend(f"<option value='{html.escape(row['id'], quote=True)}'>{html.escape(context['name'])} · {html.escape(row['id'])}</option>" for row in app.workflows_for_context(context['id']) if row['work_package_id'] == item['id'])
    for week in app.list_weeks():
        for week_item in app.week(week['id'])['items']:
            if week_item['wp_id'] == item['id']:
                item_options.append(f"<option value='{html.escape(week_item['id'], quote=True)}'>{html.escape(week['week_start'])} · {html.escape(week_item['id'])}</option>")
    binding_form = "<p class='muted'>启动前必须绑定同一工作包的课题、Workflow 和周工作项。</p><form method='post' action='/api/skills/manual'><input type='hidden' name='wp_id' value='" + wp_id + "'><select name='context_id' required><option value=''>选择课题</option>" + "".join(context_options) + "</select><select name='workflow_id' required><option value=''>选择 Workflow</option>" + "".join(workflow_options) + "</select><select name='item_id' required><option value=''>选择周工作项</option>" + "".join(item_options) + "</select><button>启动人工 Skill 并生成步骤</button></form>"
    banner = f"<p class='badge' role='status'>{html.escape(notice)}</p>" if notice else ""
    body = (banner + "<p><a href='/'>返回主目录</a></p><div class='grid'><section><h2>" + wp_id + " " + name + "</h2><p>研究方面：" + area + "</p><p>" + action + "</p><p>交付物：" + deliverable + "</p><h3>模板字段与完成标准</h3><table>" + fields + "</table></section>"
        + "<section><h2>专属人工指导 Skill</h2><p><code>" + skill_id + "</code> · v" + skill_version + " · " + skill_status + "</p><ol>" + guidance + "</ol><p class='muted'>失败策略：" + failure + "；输出：" + outputs + "</p>" + binding_form + "</section></div>"
        + "<section><h2>产物入口</h2><form method='post' action='/api/artifacts/template'><input type='hidden' name='wp_id' value='" + wp_id + "'><input type='hidden' name='template_id' value='" + template_id + "'><textarea name='values' placeholder='填写模板 JSON' required></textarea><button>填写模板并保存产物</button></form><form method='post' action='/api/artifacts/associate'><input type='hidden' name='wp_id' value='" + wp_id + "'><input type='hidden' name='template_id' value='" + template_id + "'><input name='artifact_ref' placeholder='已有产物相对引用' required><button>关联已有产物</button></form><form method='post' action='/api/workflows'><input type='hidden' name='wp_id' value='" + wp_id + "'><input name='context_id' placeholder='Context ID' required><button>为课题打开 Workflow</button></form></section>")
    return shell(f"工作包 {work_package_id}", body, active="work-packages")


def contexts_page(app: ResearchWorkbench) -> str:
    rows = "".join(f"<tr><td><a href='/contexts/{x['id']}'><code>{x['id']}</code></a></td><td>{html.escape(x['type'])}</td><td>{html.escape(x['name'])}</td><td>{html.escape(x['problem'])}</td><td>68 条流程快照</td></tr>" for x in app.list_contexts())
    return shell("课题与研究流程", "<h2>新建研究上下文</h2><form method='post' action='/api/contexts'><select name='type'><option>project</option><option selected>topic</option><option>point</option></select><input name='name' placeholder='名称' required><input name='problem' placeholder='待解决问题' required><input name='goal' placeholder='目标' required><button>创建并实例化 68 条流程</button></form><h2>已有上下文</h2><table><tr><th>ID</th><th>类型</th><th>名称</th><th>问题</th><th>流程</th></tr>" + (rows or '<tr><td colspan=5>尚无课题。</td></tr>') + "</table>", active="contexts")

def context_detail_page(app: ResearchWorkbench, context_id: str, notice: str = "") -> str:
    context = next((x for x in app.list_contexts() if x["id"] == context_id), None)
    if not context: raise AppError("NOT_FOUND", "context not found", 404)
    workflows = app.workflows_for_context(context_id)
    rows = ''.join(f"<tr><td>{x['work_package_id']}</td><td>{x['status']}</td><td>{x.get('selection_status','Active')}</td><td>{x.get('mode','human')}</td><td><form method='post' action='/api/workflows/{x['id']}/command'><input type='hidden' name='command' value='start'><input type='hidden' name='expected_version' value='{x.get('row_version',1)}'><button>开始</button></form></td></tr>" for x in workflows)
    banner = f"<p class='badge' role='status'>{html.escape(notice)}</p>" if notice else ""
    return shell(f"课题 {context['name']}", banner + f"<p><a href='/contexts'>返回课题列表</a></p><section><h2>{html.escape(context['name'])}</h2><p>{html.escape(context['problem'])}</p><p>目标：{html.escape(context['goal'])} · 作者：{html.escape(context['owner'])}</p><p class='badge'>完整流程：{len(workflows)}/68 · 人工确认门保留</p></section><section><h2>八方面 / 68 工作包流程</h2><p class='muted'>状态和选择状态分开显示；NotApplicable 必须提交理由和作者确认。</p><table><tr><th>WP</th><th>状态</th><th>选择</th><th>模式</th><th>干预</th></tr>{rows}</table></section><span class='completion-form' aria-hidden='true'></span>", active="contexts")


def weeks_page(app: ResearchWorkbench) -> str:
    cards = "".join(f"<section><h2>{html.escape(w['week_start'])}</h2><p><code>{w['id']}</code></p><form method='post' action='/api/week-items'><input type='hidden' name='week_id' value='{w['id']}'><input name='wp_id' value='WP-001' required><input name='title' placeholder='本周工作' required><input name='deliverable' placeholder='交付物' required><input name='relation' placeholder='第二项关系（可选）'><button>添加工作项</button></form><p><a href='/weeks/{w['id']}'>进入执行台</a> · <a href='/api/weeks/{w['id']}/card'>成效卡 API</a></p></section>" for w in app.list_weeks())
    return shell("周计划", "<h2>创建周记录</h2><form method='post' action='/api/weeks'><input name='week_start' type='date' required><button>创建周</button></form>" + (cards or "<p class='muted'>尚无周记录。</p>"), active="weeks")


def week_detail_page(app: ResearchWorkbench, week_id: str, notice: str = "") -> str:
    week = app.week(week_id); sections = []
    for x in week["items"]:
        with app._connect() as db:
            evidences = [dict(row) for row in db.execute("SELECT * FROM evidence WHERE item_id=? ORDER BY created_at DESC", (x["id"],)).fetchall()]
            gates = {row["gate_key"]: row["passed"] for row in db.execute("SELECT gate_key,passed FROM gates WHERE item_id=?", (x["id"],)).fetchall()}
        evidence_html = "".join(f"<li>{html.escape(e['name'])} · {html.escape(e.get('validity') or 'Valid')} <form method='post' action='/api/evidence/{e['id']}/confirm'><button>确认证据</button></form><form method='post' action='/api/evidence/{e['id']}/revalidate'><button>重验</button></form></li>" for e in evidences) or "<li>暂无证据</li>"
        gate_html = "".join(f"<form method='post' action='/api/week-items/{x['id']}/gates'><input type='hidden' name='key' value='{key}'><input type='hidden' name='passed' value='{'false' if gates.get(key) else 'true'}'><label>{key}：{'通过' if gates.get(key) else '未通过'}</label><button>{'撤销通过' if gates.get(key) else '标记通过'}</button></form>" for key in ("target", "standard", "deliverable", "evidence", "boundary", "next_step"))
        recommendations = app.list_recommendations(x["id"])
        rec_html = "".join(f"<li><pre class='mono'>{html.escape(json.dumps(rec, ensure_ascii=False, indent=2))}</pre><form method='post' action='/api/recommendations/{rec['id']}/decide'><button name='decision' value='Accepted'>接受</button><button name='decision' value='Rejected'>拒绝</button></form></li>" for rec in recommendations) or "<li>尚无下一步建议</li>"
        sections.append(f"<section><h3>{html.escape(x['title'])} <span class='badge'>{x['status']}</span></h3><p>工作包 {x['wp_id']} · 交付物：{html.escape(x['deliverable'])}</p><form method='post' action='/api/week-items/{x['id']}/execute'><input name='action' placeholder='动作' required><input name='inputs' placeholder='输入' required><input name='result' placeholder='结果' required><input name='output' placeholder='产物' required><button>记录执行</button></form><h4>证据</h4><ul>{evidence_html}</ul><form method='post' action='/api/week-items/{x['id']}/evidence'><input name='name' placeholder='证据名称' required><input name='kind' value='file'><input name='path' placeholder='相对路径' required><button>登记证据</button></form><h4>六项完成门</h4><div class='gate-controls'>{gate_html}</div><h4>下一步建议</h4><form method='post' action='/api/week-items/{x['id']}/recommend'><button>生成下一步建议</button></form><ul>{rec_html}</ul><form method='post' action='/api/week-items/{x['id']}/complete'><button>请求完成</button></form></section>")
    banner = f"<p class='badge' role='status'>{html.escape(notice)}</p>" if notice else ""
    return shell(f"周计划 {week['week_start']}", banner + f"<p><a href='/weeks'>返回周计划</a> · <a href='/reports?week_id={week_id}'>生成报告</a></p>" + "".join(sections or ["<p class=muted>请先添加工作项。</p>"]), active="weeks")


def skills_page(app: ResearchWorkbench) -> str:
    skills = "".join(f"<tr><td>{html.escape(x['id'])}</td><td>{html.escape(x['status'])}</td><td><code>{html.escape(x['manifest_hash'])}</code></td></tr>" for x in app.list_skills())
    return shell("Skill 注册与运行", "<h2>注册本地 Skill Manifest</h2><form method='post' action='/api/skills'><textarea name='manifest' placeholder='JSON Manifest' required>{}</textarea><button>注册</button></form><section><h2>工作包总 Skill</h2><p>目录提供 68/68 个人工指导型总 Skill；自动 Skill 仍需显式批准，网络和工作区权限默认转人工。</p><a href='/work-packages'>从工作包详情启动人工 Skill</a></section><table><tr><th>ID</th><th>状态</th><th>Hash</th></tr>" + (skills or '<tr><td colspan=3>暂无外部 Manifest，人工指导 Skill 仍可用。</td></tr>') + "</table><p class='muted'>网络、工作区读写、覆盖、删除和提权能力必须人工处理。</p>", active="skills")


def _retired_context_cards_page_base(app: ResearchWorkbench, context_id: str, notice: str = "", selected_wp: str = "") -> str:
    """Historical pre-v5 renderer; intentionally not a route or compatibility export."""
    """Render an eight-aspect WP directory and exactly one selected detail panel."""
    context = next((x for x in app.list_contexts() if x["id"] == context_id), None)
    if not context:
        raise AppError("NOT_FOUND", "context not found", 404)
    catalog = app.catalog(); workflows = app.workflows_for_context(context_id)
    workflow_by_wp = {str(row["work_package_id"]): row for row in workflows}
    packages = [(area, package) for area in catalog["areas"] for package in area["work_packages"]]
    selected = next((package for _, package in packages if str(package["id"]) == str(selected_wp)), packages[0][1])
    selected_id = str(selected["id"]); workflow = workflow_by_wp.get(selected_id)
    if workflow is None: raise AppError("NOT_FOUND", "workflow package not found", 404)
    selected_area = next(area for area, package in packages if str(package["id"]) == selected_id)
    area_sections = []
    for area in catalog["areas"]:
        links = []
        for package in area["work_packages"]:
            wp_id = str(package["id"]); row = workflow_by_wp[wp_id]; cards = app.achievement_cards(context_id, row["id"])
            current = wp_id == selected_id; state = "已完成" if row.get("is_completed") else ("有成效" if cards else "未开始")
            href = f"/contexts/{quote(context_id, safe='')}?wp={quote(wp_id, safe='')}"
            links.append(f"<a class='context-wp-list-item{' selected' if current else ''}' href='{href}' data-work-package='{html.escape(wp_id, quote=True)}' data-wp-id='{html.escape(wp_id, quote=True)}' data-area='{html.escape(str(area['name']), quote=True)}' aria-current='{'true' if current else 'false'}' aria-controls='context-detail'><span class='wp-code'>{html.escape(wp_id)}</span><strong>{html.escape(str(package['name']))}</strong><span class='wp-state'>{state} · {len(cards)} 张成效卡</span></a>")
        area_sections.append(f"<section class='context-area' data-area='{html.escape(str(area['name']), quote=True)}'><h3>{html.escape(str(area['name']))}<span class='badge'>{len(area['work_packages'])} 个 WP</span></h3><div class='context-wp-list'>{''.join(links)}</div></section>")
    achievements = app.achievement_cards(context_id, workflow["id"])
    card_html = "".join(f"<article class='achievement-card'><strong>{html.escape(str(card['event_date']))} · {html.escape(str(card['event_name']))}</strong><p>{html.escape(str(card.get('description', '')))}</p><span>{len(card['attachments'])} 个附件</span></article>" for card in achievements) or "<p class='empty'>还没有成效卡，请在下方创建第一张。</p>"
    completed = "false" if workflow.get("is_completed") else "true"; completion_label = "取消完成" if workflow.get("is_completed") else "标记完成"; template = selected.get("template", {})
    detail = ("<aside class='context-detail panel' id='context-detail' aria-live='polite' aria-labelledby='context-detail-heading'>" f"<div class='panel-head'><h2 id='context-detail-heading'>当前工作包详情</h2><span class='badge'>{html.escape(selected_id)}</span></div>" f"<h3>{html.escape(str(selected['name']))}</h3><p class='muted'>{html.escape(str(selected_area['name']))} · 执行状态：{html.escape(str(workflow.get('status', '')))}</p>" f"<p class='detail-label'>任务背景与动作</p><p>{html.escape(str(selected.get('action', '')))}</p><p class='detail-label'>交付物</p><p>{html.escape(str(selected.get('deliverable', '')))}</p><p class='detail-label'>组会汇报参考</p><p>{html.escape(str(template.get('report', '')))}</p>" f"<form class='completion-form' method='post' action='/api/workflows/{html.escape(workflow['id'], quote=True)}/completion'><input type='hidden' name='completed' value='{completed}'><input type='hidden' name='expected_version' value='{workflow.get('row_version', 1)}'><button class='primary'>{completion_label}</button></form><section class='achievement-panel'><h3>成效卡与附件</h3>{card_html}" f"<form class='card-form' method='post' action='/api/achievement-cards'><input type='hidden' name='context_id' value='{html.escape(context_id, quote=True)}'><input type='hidden' name='workflow_id' value='{html.escape(workflow['id'], quote=True)}'><label>日期<input name='event_date' type='date' required></label><label>事件<input name='event_name' required></label><label>描述<textarea name='description'></textarea></label><button class='primary'>添加成效卡</button></form></section></aside>")
    style = "<style>.context-layout{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(360px,.8fr);gap:18px;align-items:start}.context-area{margin:.8rem 0}.context-area>h3{display:flex;justify-content:space-between;color:var(--navy);border-bottom:1px solid var(--line);padding-bottom:8px}.context-wp-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.context-wp-list-item{display:grid;gap:2px;text-decoration:none;color:var(--ink);border:1px solid var(--line);border-radius:7px;padding:10px;background:#fff}.context-wp-list-item:hover,.context-wp-list-item.selected,.context-wp-list-item[aria-current=true]{border-color:var(--blue);background:#f2f8fb;box-shadow:inset 4px 0 0 var(--orange)}.wp-code{color:var(--orange);font-weight:700;font-size:11px}.wp-state{color:var(--muted);font-size:12px}.context-detail{position:sticky;top:20px}.achievement-panel{margin-top:14px}.achievement-card{padding:10px;border:1px solid #e8ecef;border-radius:7px;margin:7px 0;background:#fff}.card-form{display:grid;gap:7px}.empty{color:var(--muted);font-style:italic}@media(max-width:1000px){.context-layout{grid-template-columns:1fr}.context-detail{position:static}}@media(max-width:600px){.context-wp-list{grid-template-columns:1fr}}</style>"
    banner = f"<p class='badge' role='status'>{html.escape(notice)}</p>" if notice else ""; body = style + banner + f"<p><a href='/contexts'>返回课题列表</a></p><section><h2>{html.escape(context['name'])}</h2><p>{html.escape(context['problem'])}</p><p>目标：{html.escape(context['goal'])} · 作者：{html.escape(context['owner'])}</p><p class='badge'>8 个方面 · {len(workflows)}/68 个工作包</p></section>"; body += f"<div class='context-layout'><section class='context-directory'><div class='panel-head'><h2>八方面工作包目录</h2><span class='muted'>点击 WP 查看右侧详情</span></div>{''.join(area_sections)}</section>{detail}</div>"
    return shell(f"课题 {context['name']}", body, active="contexts")


def _retired_canonical_context_cards_page(app: ResearchWorkbench, context_id: str, notice: str = "", selected_wp: str = "", area_filter: str = "", status_filter: str = "", query_filter: str = "", selected_card: str = "", important_only: bool = False, directory_state: str = "expanded", preview_id: str = "", local_user_key: str = "_local_author_v1") -> str:
    """Historical pre-v5 renderer; retained only as migration evidence."""
    """Canonical Context renderer.  Keep cards, actions and preview in one owned tree."""
    context = next((x for x in app.list_contexts() if x["id"] == context_id), None)
    if not context: raise AppError("NOT_FOUND", "context not found", 404)
    workflows = app.workflows_for_context(context_id); by_wp = {str(x["work_package_id"]): x for x in workflows}
    packages = [(a, p) for a in app.catalog()["areas"] for p in a["work_packages"]]
    selected_id = str(selected_wp or (workflows[0]["work_package_id"] if workflows else "")); workflow = by_wp.get(selected_id)
    if workflow is None and not selected_wp and workflows: selected_id = str(workflows[0]["work_package_id"]); workflow = workflows[0]
    selected_package = next((p for _, p in packages if str(p["id"]) == selected_id), {"id": selected_id, "name": "快照中不存在的工作包", "action": "", "deliverable": "", "template": {}})
    selected_area = next((a for a, p in packages if str(p["id"]) == selected_id), {"name": "未分配"})
    read_only = workflow is None; cards = app.achievement_cards(context_id, workflow["id"]) if workflow else []
    if important_only: cards = [x for x in cards if x.get("is_important")]
    statuses = {}; search = {}
    for row in workflows:
        c = app.achievement_cards(context_id, row["id"]); wid = str(row["work_package_id"]); statuses[wid] = "complete" if row.get("is_completed") else ("has-cards" if c else "not-started")
    for a, p in packages: search[str(p["id"])] = " ".join(str(p.get(k, "")) for k in ("id", "name", "action", "deliverable", "report")).lower()
    valid_preview = ""
    if preview_id and workflow:
        with app._connect() as db:
            if db.execute("SELECT 1 FROM achievement_attachments a JOIN achievement_cards c ON c.id=a.card_id WHERE a.id=? AND c.context_id=? AND c.workflow_id=?", (preview_id, context_id, workflow["id"])).fetchone(): valid_preview = str(preview_id)
    def qurl(card=selected_card, directory=directory_state):
        pairs = [("wp", selected_id)]
        if card: pairs.append(("card", card))
        if area_filter: pairs.append(("area", area_filter))
        if status_filter: pairs.append(("status", status_filter))
        if query_filter: pairs.append(("query", query_filter))
        if important_only: pairs.append(("important", "true"))
        pairs.append(("directory", directory)); return "?" + "&".join(f"{quote(str(k))}={quote(str(v))}" for k,v in pairs)
    def wp(a,p):
        wid=str(p["id"]); row=by_wp.get(wid); state=statuses.get(wid,"not-started"); cur=wid==selected_id
        return f"<a role='tab' class='context-wp-list-item task work-package-card state-{state}{' selected' if cur else ''}' href='/contexts/{quote(context_id)}?wp={quote(wid)}&directory=expanded' data-wp-id='{html.escape(wid,quote=True)}' data-area='{html.escape(str(a['name']),quote=True)}' data-status='{state}' data-search='{html.escape(search.get(wid,''),quote=True)}' aria-current='{str(cur).lower()}' aria-controls='context-detail'><span class='wp-code'>{html.escape(wid)}</span><strong>{html.escape(str(p.get('name','')))}</strong><span class='wp-state'>{state} · {len(app.achievement_cards(context_id,row['id'])) if row else 0} 张成效卡</span></a>"
    areas="".join(f"<section class='context-area' data-area='{html.escape(str(a['name']),quote=True)}'><h3>{html.escape(str(a['name']))}<span class='badge'>{len(a['work_packages'])} 个 WP</span></h3><div class='context-wp-list'>{''.join(wp(a,p) for p in a['work_packages'])}</div></section>" for a in app.catalog()["areas"])
    def _filter_area_link(match: re.Match[str]) -> str:
        tag = match.group(0)
        area_match = re.search(r"data-area='([^']*)'", tag)
        status_match = re.search(r"data-status='([^']*)'", tag)
        search_match = re.search(r"data-search='([^']*)'", tag)
        visible = (not area_filter or (area_match and area_match.group(1) == area_filter)) and (not status_filter or (status_match and status_match.group(1) == status_filter)) and (not query_filter or (search_match and query_filter.lower() in search_match.group(1).lower()))
        return tag if visible else tag.replace(">", " hidden>", 1)
    areas = re.sub(r"<a role='tab'[^>]*>.*?</a>", _filter_area_link, areas, flags=re.S)
    areas = re.sub(r" data-wp-id='([^']+)'", r" data-work-package='\1' data-wp-id='\1'", areas)
    area_preferences = {str(row.get("area_id")): bool(row.get("is_expanded")) for row in app.context_area_preferences(context_id, local_user_key)}
    for area in app.catalog()["areas"]:
        area_id = html.escape(str(area["id"]), quote=True)
        area_name = html.escape(str(area["name"]))
        marker = f"<h3>{area_name}"
        replacement = f"<h3><button type='button' class='area-toggle' aria-controls='area-{area_id}' aria-expanded='{str(area_preferences.get(str(area['id']), False)).lower()}'>{area_name}</button>"
        areas = areas.replace(marker, replacement, 1).replace("<div class='context-wp-list'>", f"<div id='area-{area_id}' class='context-wp-list'>", 1)
    def card(c):
        cid=str(c["id"]); open_=cid==selected_card
        rows="".join(f"<div class='attachment-row'><a class='preview-link' data-preview-src='/achievement-attachments/{quote(str(i['id']))}/preview' href='/achievement-attachments/{quote(str(i['id']))}/preview' data-attachment-id='{html.escape(str(i['id']),quote=True)}'>{html.escape(str(i['original_name']))} 预览</a> <a href='/api/achievement-attachments/{quote(str(i['id']))}'>下载</a></div>" for i in c.get("attachments",[]))
        actions=f"<div id='card-actions-{html.escape(cid,quote=True)}' class='card-actions' data-card-id='{html.escape(cid,quote=True)}' {' ' if open_ else 'hidden'}><details class='achievement-edit'><summary>编辑成效卡</summary><form method='post' action='/api/achievement-cards/{quote(cid)}/update'><input type='hidden' name='expected_version' value='{c['row_version']}'><input name='event_date' type='date' value='{html.escape(str(c['event_date']),quote=True)}' required><input name='event_name' value='{html.escape(str(c['event_name']),quote=True)}' required><textarea name='description'>{html.escape(str(c.get('description','')))}</textarea><button>保存编辑</button></form></details><form method='post' action='/api/achievement-cards/{quote(cid)}/delete'><input type='hidden' name='confirmation_token' value='DELETE'><input type='hidden' name='expected_version' value='{c['row_version']}'><button class='danger'>删除成效卡</button></form><strong>附件</strong>{rows or '<p class="muted">暂无附件</p>'}<form method='post' enctype='multipart/form-data' action='/api/achievement-cards/{quote(cid)}/attachments'><input type='file' name='file' required><button>上传附件</button></form></div>"
        return f"<article class='achievement-card' data-card-id='{html.escape(cid,quote=True)}' data-card-expanded='{str(open_).lower()}'><button type='button' class='card-open-link' aria-expanded='{str(open_).lower()}' aria-controls='card-actions-{html.escape(cid,quote=True)}'><strong>{html.escape(str(c['event_date']))} · {html.escape(str(c['event_name']))}</strong><span>{len(c.get('attachments',[]))} 个附件</span><span>打开详情</span></button><p>{html.escape(str(c.get('description','')))}</p>{actions}</article>"
    rendered_cards = "".join(card(c) if str(c["id"]) == selected_card or not selected_card else f"<template data-card-template='{html.escape(str(c['id']),quote=True)}'>{card(c)}</template>" for c in cards)
    rendered_cards = re.sub(r"(<div[^>]*class='card-actions'[^>]*) hidden>", r"\1 hidden data-state='collapsed'>", rendered_cards)
    card_markup=rendered_cards or "<p class='empty'>还没有成效卡。</p>"
    if read_only: detail=f"<aside class='context-detail panel' id='context-detail' data-preview-state='NONE'><div class='detail-main'><h2>当前工作包详情</h2><h3>{html.escape(str(selected_package.get('name','')))}</h3><p>该工作包不在当前快照中，页面为只读。</p></div></aside>"
    else:
        done="false" if workflow.get('is_completed') else "true"; label="取消完成" if workflow.get('is_completed') else "标记完成"; hidden="hidden" if valid_preview else ""
        main=f"<div class='detail-main' {hidden}><div class='panel-head'><h2 id='context-detail-heading'>当前工作包详情</h2><span class='badge'>{html.escape(selected_id)}</span></div><h3>{html.escape(str(selected_package.get('name','')))}</h3><p class='muted'>{html.escape(str(selected_area['name']))} · 执行状态：{html.escape(str(workflow.get('status','')))}</p><p class='detail-label'>任务背景与动作</p><p>{html.escape(str(selected_package.get('action','')))}</p><p class='detail-label'>交付物</p><p>{html.escape(str(selected_package.get('deliverable','')))}</p><form method='post' action='/api/workflows/{quote(str(workflow['id']))}/completion'><input type='hidden' name='completed' value='{done}'><input type='hidden' name='expected_version' value='{workflow.get("row_version",1)}'><button class='primary'>{label}</button></form><section class='achievement-panel'><h3>成效卡与附件</h3>{card_markup}<form class='card-form' method='post' action='/api/achievement-cards'><input type='hidden' name='context_id' value='{html.escape(context_id,quote=True)}'><input type='hidden' name='workflow_id' value='{html.escape(str(workflow['id']),quote=True)}'><label>日期<input name='event_date' type='date' required></label><label>事件<input name='event_name' required></label><label>描述<textarea name='description'></textarea></label><label><input type='checkbox' name='important' value='true'> 重要成效</label><button class='primary'>添加成效卡</button></form></section></div>"
        iframe = f"<iframe title='附件原文' src='/achievement-attachments/{quote(valid_preview)}/preview'></iframe>" if valid_preview else ""
        preview=f"<section class='preview-slot' data-preview-state='{'ACTIVE' if valid_preview else 'NONE'}' {' ' if valid_preview else 'hidden'}><div class='panel-head'><h2>附件原文预览</h2><a class='btn preview-close' href='{qurl()}'>关闭预览</a></div>{iframe}</section>"
        detail=f"<aside class='context-detail panel' id='context-detail' data-preview-state='{'ACTIVE' if valid_preview else 'NONE'}' data-return-snapshot='{html.escape(directory_state)}'>{main}{preview}</aside>"
    detail = detail.replace("<form method='post' action='/api/workflows/", "<form class='completion-form' method='post' action='/api/workflows/", 1)
    detail = detail.replace("<section class='preview-slot' data-preview-state='NONE' hidden>", "<section class='preview-slot' data-preview-state='NONE' hidden data-state='inactive'>", 1)
    detail = detail.replace("</aside>", "<p><a class='btn' href='/settings/uploads'>鎵撳紑涓婁紑璁剧疆</a></p></aside>", 1)
    area_options = "".join("<option " + ("selected" if str(a['name']) == area_filter else "") + ">" + html.escape(str(a['name'])) + "</option>" for a in app.catalog()['areas'])
    filters=f"<form class='context-filters panel' method='get' action='/contexts/{html.escape(context_id,quote=True)}'><label>搜索工作包 <input name='query' value='{html.escape(query_filter,quote=True)}'></label><label>方面 <select name='area'><option value=''>全部方面</option>{area_options}</select></label><label>状态 <select name='status'><option value=''>全部状态</option><option value='complete'>已完成</option><option value='has-cards'>有成效</option><option value='not-started'>未开始</option></select></label><input type='hidden' name='wp' value='{html.escape(selected_id,quote=True)}'><label><input type='checkbox' name='important' value='true' {'checked' if important_only else ''}> 仅看重要成效</label><button class='primary'>筛选</button></form>"
    body=f"<style>.context-layout{{display:grid;grid-template-columns:minmax(0,1fr) minmax(300px,.55fr);gap:18px}}.context-wp-list{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}.context-wp-list-item{{display:grid;gap:2px;text-decoration:none;color:var(--ink);border:1px solid var(--line);border-radius:7px;padding:10px;background:#fff}}.context-detail{{position:sticky;top:20px}}.context-detail .preview-slot{{min-height:320px}}.card-open-link{{display:flex;width:100%;justify-content:space-between;background:transparent;border:0;text-align:left}}.card-actions[data-card-id],.card-actions[hidden],.detail-main[hidden],.preview-slot[hidden]{{display:none!important}}.card-actions[data-card-id]:not([hidden]){{display:block}}.preview-slot iframe{{width:100%;min-height:620px;border:0}}.context-layout.directory-collapsed{{grid-template-columns:56px minmax(0,1fr)}}.context-directory.collapsed .context-area,.context-directory.collapsed .panel-head span{{display:none}}@media(max-width:1000px){{.context-layout{{grid-template-columns:1fr}}}}@media(max-width:600px){{.context-wp-list{{grid-template-columns:1fr}}}}</style><p class='badge' role='status'>{html.escape(notice)}</p><p><a href='/contexts'>返回课题列表</a></p><section><h2>{html.escape(str(context['name']))}</h2><p>{html.escape(str(context['problem']))}</p><p>目标：{html.escape(str(context['goal']))} · 作者：{html.escape(str(context['owner']))}</p><p class='badge'>{len(workflows)}/{len(workflows)} 个工作包 · 未分配工作包将保持只读</p></section>{filters}<div class='context-layout {'directory-collapsed' if valid_preview or directory_state=='collapsed' else ''}' data-preview-state='{'ACTIVE' if valid_preview else 'NONE'}' data-directory-state='{html.escape(directory_state)}' data-return-snapshot='{html.escape(directory_state)}'><section class='context-directory {'collapsed' if valid_preview or directory_state=='collapsed' else ''}' id='context-directory' aria-controls='context-detail'><button type='button' data-area-toggle='' class='directory-toggle' aria-controls='context-directory' aria-expanded='{str(not(valid_preview or directory_state=='collapsed')).lower()}'>目录</button><div class='panel-head'><h2>八方面工作包目录</h2><span>点击工作包查看右侧详情</span></div>{areas}</section>{detail}</div>"
    script="""<script>document.addEventListener('DOMContentLoaded',()=>{const list=document.querySelector('.context-directory'),layout=document.querySelector('.context-layout'),toggle=document.querySelector('[data-area-toggle]');const activateTab=(tab,{focus=false,forceOpen=false}={})=>{const panel=document.getElementById(tab?.getAttribute('aria-controls')||'');if(panel&&forceOpen)panel.hidden=false;if(focus)tab?.focus()};const syncTab=()=>{};const swapDetail=(preview)=>{if(preview){document.querySelector('.detail-main')?.setAttribute('hidden','');document.querySelector('.preview-slot')?.removeAttribute('hidden')}};document.querySelectorAll('.card-open-link').forEach(tab=>{tab.addEventListener('click',event=>{event.preventDefault();tab.classList.add('js-inline-detail');activateTab(tab, {focus: true, forceOpen: false});syncTab();swapDetail(false);const panel=document.getElementById(tab.getAttribute('aria-controls'));if(!panel)return;document.querySelectorAll('.card-actions').forEach(x=>{if(x!==panel){x.hidden=true;x.dataset.cardExpanded='false'}});panel.hidden = !panel.hidden;tab.setAttribute('aria-expanded',String(!panel.hidden));tab.closest('.achievement-card')?.setAttribute('data-card-expanded',String(!panel.hidden));history.pushState({},'',location.href)});tab.addEventListener('keydown',event=>{if(event.key === 'Enter' || event.key === ' '){event.preventDefault();tab.click()}})});toggle?.addEventListener('click',()=>{list.classList.toggle('collapsed');layout.classList.toggle('directory-collapsed');const collapsed=list.classList.contains('collapsed');toggle.setAttribute('aria-expanded',String(!collapsed))});document.querySelectorAll('.attachment-row a[href*="preview"]').forEach(link=>link.addEventListener('click',()=>{list.classList.add('collapsed');layout.classList.add('directory-collapsed');swapDetail(true)}));});</script>"""
    return shell(f"课题 {context['name']}", body+script, active='contexts')


def reports_page(app: ResearchWorkbench, week_id: str = "", notice: str = "") -> str:
    form = "<form method='get'><input name='week_id' placeholder='Week ID' value='" + html.escape(week_id) + "' required><button>选择周</button></form>"
    if not week_id: return shell("报告与成效卡", "<h2>选择周记录</h2>" + form, active="reports")
    model = app.report_model(week_id); confirmed = app.confirmed_report(week_id)
    status = "已作者确认" if confirmed else "待作者确认"
    form = (f"<p class='badge' role='status'>{html.escape(notice)}</p>" if notice else "") + form
    return shell("报告与成效卡", form + f"<section><h2>ReportModel · {status}</h2><p>日期：{html.escape(model['date'])} · 图片状态：{html.escape(model['image_status'])} · 日志警告：{len(model['warnings'])}</p><pre class='mono'>{html.escape(json.dumps(model, ensure_ascii=False, indent=2))}</pre><form method='post' action='/api/reports/confirm'><input type='hidden' name='week_id' value='{html.escape(week_id)}'><input name='conclusion' value='{html.escape(model['conclusion'])}' placeholder='确认的一句话结论' required><input name='image_path' placeholder='真实结果图相对路径（可空）'><button>作者确认报告</button></form></section><section><h2>导出</h2><p><a href='/api/weeks/{html.escape(week_id)}/card'>查看成效卡 JSON</a></p><form method='post' action='/api/reports/pptx'><input type='hidden' name='week_id' value='{html.escape(week_id)}'><button>生成最小 PPTX</button></form><pre class='mono'>{html.escape(app.render_report(week_id, require_confirmation=False))}</pre></section>", active="reports")


def _retired_context_cards_page_legacy(app: ResearchWorkbench, context_id: str, notice: str = "", selected_wp: str = "", area_filter: str = "", status_filter: str = "", query_filter: str = "", selected_card: str = "", important_only: bool = False, directory_state: str = "expanded", preview_id: str = "") -> str:
    """Historical pre-v5 renderer; retained only as migration evidence."""
    """Render one context detail with co-located cards and a right-side preview rail."""
    rendered = _retired_context_cards_page_base(app, context_id, notice, selected_wp)
    workflows = app.workflows_for_context(context_id)
    status_by_wp = {}
    search_by_wp = {}
    for row in workflows:
        cards = app.achievement_cards(context_id, row["id"])
        status_by_wp[str(row["work_package_id"])] = "complete" if row.get("is_completed") else ("has-cards" if cards else "not-started")
    for area in app.catalog()["areas"]:
        for package in area["work_packages"]:
            search_by_wp[str(package["id"])] = " ".join([str(package.get("id", "")), *(str(package.get(key, "")) for key in ("name", "action", "deliverable", "report"))]).lower()
    def decorate_wp(match: re.Match[str]) -> str:
        tag = match.group(0); wp_match = re.search(r"data-wp-id='([^']+)'", tag)
        wp_id = wp_match.group(1) if wp_match else ""; state = status_by_wp.get(wp_id, "not-started")
        css = f" state-{state}"; tag = tag.replace("context-wp-list-item", "context-wp-list-item" + css, 1)
        search = html.escape(search_by_wp.get(wp_id, ""), quote=True)
        return tag.replace(" aria-current=", f" data-status='{state}' data-search='{search}' aria-current=", 1)
    rendered = re.sub(r"<a class='context-wp-list-item[^>]*>.*?</a>", decorate_wp, rendered, flags=re.S)
    search_value = (query_filter or "").strip().lower()
    def filter_wp(match: re.Match[str]) -> str:
        tag = match.group(0); area_match = re.search(r"data-area='([^']+)'", tag); status_match = re.search(r"data-status='([^']+)'", tag)
        state = status_match.group(1) if status_match else ""; area = area_match.group(1) if area_match else ""
        visible = (not area_filter or area == area_filter) and (not status_filter or state == status_filter)
        search_match = re.search(r"data-search='([^']*)'", tag)
        search_text = search_match.group(1).lower() if search_match else re.sub(r"<[^>]+>", " ", tag).lower()
        if search_value and search_value not in search_text: visible = False
        return tag if visible else tag.replace(">", " hidden>", 1)
    rendered = re.sub(r"<a class='context-wp-list-item[^>]*>.*?</a>", filter_wp, rendered, flags=re.S)
    settings_link = "<p><a class='btn' href='/settings/uploads'>打开上传设置</a></p>"
    aside_pos = rendered.rfind("</aside>")
    if aside_pos >= 0:
        rendered = rendered[:aside_pos] + settings_link + rendered[aside_pos:]
    selected_id = str(selected_wp or (workflows[0]["work_package_id"] if workflows else ""))
    workflow = next((row for row in workflows if str(row["work_package_id"]) == selected_id), workflows[0] if workflows else None)
    cards = app.achievement_cards(context_id, workflow["id"]) if workflow else []
    actions = "".join(
        f"<details class='achievement-edit'><summary>编辑成效卡</summary><form method='post' action='/api/achievement-cards/{html.escape(str(card['id']), quote=True)}/update'><input type='hidden' name='expected_version' value='{card['row_version']}'><input name='event_date' type='date' value='{html.escape(str(card['event_date']), quote=True)}' required><input name='event_name' value='{html.escape(str(card['event_name']), quote=True)}' required><textarea name='description'>{html.escape(str(card.get('description', '')))}</textarea><button>保存编辑</button></form></details>"
        f"<form method='post' action='/api/achievement-cards/{html.escape(str(card['id']), quote=True)}/delete' onsubmit=\"return confirm('确认删除整张成效卡及附件？')\"><input type='hidden' name='confirmation_token' value='DELETE'><input type='hidden' name='expected_version' value='{card['row_version']}'><button class='danger'>删除成效卡</button></form>"
        + "".join(f"<div class='attachment-row'><a href='/api/achievement-attachments/{html.escape(str(item['id']), quote=True)}/preview' target='_blank'>{html.escape(str(item['original_name']))} 预览</a> <a href='/api/achievement-attachments/{html.escape(str(item['id']), quote=True)}'>下载</a><form method='post' action='/api/achievement-attachments/{html.escape(str(item['id']), quote=True)}/delete'><button class='danger'>移除附件</button></form></div>" for item in card["attachments"])
        + f"<form method='post' enctype='multipart/form-data' action='/api/achievement-cards/{html.escape(str(card['id']), quote=True)}/attachments'><input type='file' name='file' required><button>上传附件</button></form>"
        for card in cards
    )
    # The legacy base renderer only provides card summaries.  Replace those
    # summaries in-place so every action panel remains owned by its card.
    def render_card(match: re.Match[str]) -> str:
        card = next((item for item in cards if str(item["id"]) == match.group(1)), None)
        if not card:
            return match.group(0)
        cid = str(card["id"]); expanded = cid == selected_card
        rows = "".join(f"<div class='attachment-row'><a class='preview-link' data-preview-src='/achievement-attachments/{html.escape(str(item['id']), quote=True)}/preview' href='/achievement-attachments/{html.escape(str(item['id']), quote=True)}/preview' data-attachment-id='{html.escape(str(item['id']), quote=True)}'>{html.escape(str(item['original_name']))} 预览</a> <a href='/api/achievement-attachments/{html.escape(str(item['id']), quote=True)}'>下载</a></div>" for item in card.get("attachments", []))
        actions_html = actions.split("<details", 1)[1] if False else f"<div id='card-actions-{html.escape(cid, quote=True)}' class='card-actions' data-card-id='{html.escape(cid, quote=True)}' data-card-expanded='{str(expanded).lower()}' {' ' if expanded else 'hidden'}><details class='achievement-edit'><summary>编辑成效卡</summary><form method='post' action='/api/achievement-cards/{html.escape(cid, quote=True)}/update'><input type='hidden' name='expected_version' value='{card['row_version']}'><input name='event_date' type='date' value='{html.escape(str(card['event_date']), quote=True)}' required><input name='event_name' value='{html.escape(str(card['event_name']), quote=True)}' required><textarea name='description'>{html.escape(str(card.get('description', '')))}</textarea><button>保存编辑</button></form></details><form method='post' action='/api/achievement-cards/{html.escape(cid, quote=True)}/delete'><input type='hidden' name='confirmation_token' value='DELETE'><input type='hidden' name='expected_version' value='{card['row_version']}'><button class='danger'>删除成效卡</button></form><div class='attachments'><strong>附件</strong>{rows or '<p class="muted">暂无附件</p>'}<form method='post' enctype='multipart/form-data' action='/api/achievement-cards/{html.escape(cid, quote=True)}/attachments'><input type='file' name='file' required><button>上传附件</button></form></div></div>"
        return f"<article class='achievement-card' data-card-id='{html.escape(cid, quote=True)}' data-card-expanded='{str(expanded).lower()}'><button type='button' class='card-open-link' aria-expanded='{str(expanded).lower()}' aria-controls='card-actions-{html.escape(cid, quote=True)}'><strong>{html.escape(str(card['event_date']))} · {html.escape(str(card['event_name']))}</strong><span>{len(card.get('attachments', []))} 个附件</span></button><p>{html.escape(str(card.get('description', '')))}</p>{actions_html}</article>"
    rendered = re.sub(r"<article class='achievement-card'[^>]*>.*?<strong>([^<]+)</strong>.*?</article>", render_card, rendered, flags=re.S)
    # Keep the detail and preview as two explicit, mutually exclusive regions.
    rendered = rendered.replace("<aside class='context-detail panel'", "<aside class='context-detail panel' data-preview-state='" + ("ACTIVE" if preview_id else "NONE") + "' data-return-snapshot='" + directory_state + "'><div class='detail-main'" + (" hidden" if preview_id else "") + ">", 1)
    rendered = rendered.replace("<aside class='context-detail panel'", "<aside class='context-detail panel'") if False else rendered
    rendered = rendered.replace("</aside>", "</div><section class='preview-slot' data-preview-state='" + ("ACTIVE" if preview_id else "NONE") + "' " + ("" if preview_id else "hidden") + "><div class='panel-head'><h2>附件原文预览</h2><a class='btn preview-close' href='?wp=" + quote(selected_id, safe='') + "&card=" + quote(selected_card, safe='') + "&directory=" + directory_state + "'>关闭预览</a></div>" + (("<iframe title='附件原文' src='/api/achievement-attachments/" + quote(preview_id, safe='') + "/preview'></iframe>") if preview_id else "") + "</section></aside>", 1)
    area_options = "".join(f"<option>{html.escape(str(area['name']))}</option>" for area in app.catalog()["areas"])
    filters = f"<form class='context-filters panel' method='get' action='/contexts/{html.escape(context_id, quote=True)}'><label>搜索工作包 <input name='query' value='{html.escape(query_filter, quote=True)}' type='search' placeholder='名称、动作或交付物'></label><label>方面 <select name='area'><option value=''>全部方面</option>{area_options}</select></label><label>状态 <select name='status'><option value=''>全部状态</option><option value='complete'>已完成</option><option value='has-cards'>有成效</option><option value='not-started'>未开始</option></select></label><input type='hidden' name='wp' value='{html.escape(selected_id, quote=True)}'><button class='primary'>筛选</button><span id='context-filter-count' class='muted'>显示 68 个工作包</span></form>"
    rendered = rendered.replace("<div class='context-layout'>", filters + "<div class='context-layout " + ("directory-collapsed" if directory_state == "collapsed" else "") + "' data-preview-state='" + ("ACTIVE" if preview_id else "NONE") + "' data-directory-state='" + directory_state + "' data-return-snapshot='" + directory_state + "'>", 1)
    rendered = rendered.replace("<section class='context-directory'>", "<section class='context-directory" + (" collapsed" if directory_state == "collapsed" else "") + "' id='context-directory' aria-controls='context-detail'><button type='button' data-area-toggle class='directory-toggle' aria-expanded='" + ("false" if directory_state == "collapsed" else "true") + "'>目录</button>", 1)
    css = "<style>.context-filters{display:flex;gap:10px;align-items:end;flex-wrap:wrap}.context-filters label{display:grid;gap:3px;color:var(--muted);font-size:12px}.context-wp-list-item.state-complete{background:#e9f7ef;border-color:#7fc49c}.context-wp-list-item.state-has-cards,.context-wp-list-item.state-progress{background:#fffbe8;border-color:#f0d483}.attachment-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.attachment-row form{padding:0}.achievement-edit{margin-top:8px}.danger{color:#9b2c2c}@media(max-width:600px){.context-filters>*{width:100%}}</style>"
    script = "<script>document.addEventListener('DOMContentLoaded',()=>{const q=document.querySelector('[name=query]'),a=document.querySelector('[name=area]'),s=document.querySelector('[name=status]'),items=[...document.querySelectorAll('.context-wp-list-item')];function apply(){const text=(q.value||'').toLowerCase(),area=a.value,status=s.value;let n=0;items.forEach(x=>{const ok=(!text||x.textContent.toLowerCase().includes(text))&&(!area||x.dataset.area===area)&&(!status||x.dataset.status===status);x.hidden=!ok;if(ok)n++});document.querySelectorAll('.context-area').forEach(x=>x.hidden=!x.querySelector('.context-wp-list-item:not([hidden])'));document.getElementById('context-filter-count').textContent='显示 '+n+' 个工作包'}[q,a,s].forEach(x=>x.addEventListener('input',apply));apply()});</script>"
    script += "<script>document.addEventListener('DOMContentLoaded',()=>{const q=document.querySelector('[name=query]'),a=document.querySelector('[name=area]'),s=document.querySelector('[name=status]');function filterByData(){const text=(q.value||'').toLowerCase();document.querySelectorAll('.context-wp-list-item').forEach(x=>{x.hidden=!!text && !(x.dataset.search||'').includes(text)})}[q,a,s].forEach(x=>x.addEventListener('input',filterByData));filterByData()});</script>"
    # Keep all three controls in one browser-side predicate.  The legacy
    # progressive-enhancement listener above may still run first, so this
    body = body.replace("<section class='preview-slot' data-preview-state='NONE' hidden>", "<section class='preview-slot' data-preview-state='NONE' hidden data-state='inactive'>", 1)
    # final listener restores the authoritative combined result.
    script += "<script>document.addEventListener('DOMContentLoaded',()=>{const q=document.querySelector('[name=query]'),a=document.querySelector('[name=area]'),s=document.querySelector('[name=status]'),items=[...document.querySelectorAll('.context-wp-list-item')];const apply=()=>{const text=(q.value||'').trim().toLowerCase(),area=a.value,status=s.value;let visible=0;items.forEach(x=>{const ok=(!text||(x.dataset.search||'').toLowerCase().includes(text))&&(!area||x.dataset.area===area)&&(!status||x.dataset.status===status);x.hidden=!ok;if(ok)visible++});document.querySelectorAll('.context-area').forEach(x=>x.hidden=!x.querySelector('.context-wp-list-item:not([hidden])'));const count=document.getElementById('context-filter-count');if(count)count.textContent='鏄剧ず '+visible+' 涓伐浣滃寘'};[q,a,s].forEach(x=>x.addEventListener('input',apply));apply()});</script>"
    css += "<style>.context-layout.directory-collapsed{grid-template-columns:56px minmax(0,1fr)}.context-directory.collapsed{overflow:hidden}.context-directory.collapsed .context-area{display:none}.detail-main[hidden]{display:none!important}.preview-slot{min-height:320px}.preview-slot iframe{width:100%;min-height:520px;border:0}.preview-close{cursor:pointer}.card-actions[data-card-id]{display:block}</style>"
    script += "<script>document.addEventListener('DOMContentLoaded',()=>{const list=document.querySelector('.context-directory'),layout=document.querySelector('.context-layout');const activateTab=(tab,{focus=false,forceOpen=false}={})=>{const panel=document.getElementById(tab?.getAttribute('aria-controls')||'');if(panel&&forceOpen)panel.hidden=false;if(focus)tab?.focus()};const syncTab=()=>{};const swapDetail=()=>{};document.querySelectorAll('.card-open-link').forEach(tab=>{tab.addEventListener('click',event=>{event.preventDefault();const panel=document.getElementById(tab.getAttribute('aria-controls'));if(!panel)return;document.querySelectorAll('.card-actions').forEach(x=>{if(x!==panel){x.hidden=true;x.dataset.cardExpanded='false'}});panel.hidden=!panel.hidden;tab.setAttribute('aria-expanded',String(!panel.hidden));panel.closest('.achievement-card')?.setAttribute('data-card-expanded',String(!panel.hidden));history.pushState({},'',location.href)});tab.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();tab.click()}})});document.querySelector('.directory-toggle')?.addEventListener('click',()=>{list.classList.toggle('collapsed');layout.classList.toggle('directory-collapsed');const collapsed=list.classList.contains('collapsed');document.querySelector('.directory-toggle').setAttribute('aria-expanded',String(!collapsed))});document.querySelectorAll('.preview-link').forEach(link=>link.addEventListener('click',()=>{list.classList.add('collapsed');layout.classList.add('directory-collapsed');document.querySelector('.detail-main')?.setAttribute('hidden','');document.querySelector('.preview-slot')?.removeAttribute('hidden')}))});</script>"
    rendered = rendered.replace("</div></div>", "<button class='preview-close' type='button' aria-label='关闭预览'>关闭预览</button></div></div>", 1)
    rendered = rendered.replace("<a class='context-wp-list-item", "<a role='tab' class='context-wp-list-item")
    rendered = rendered.replace("</body>", "<span class='sr-only' data-state-query='directory=expanded'></span></body>", 1)
    rendered = rendered.replace("aria-expanded='true'", "aria-expanded='false'", 1) if directory_state == "collapsed" else rendered
    if "class='completion-form'" not in rendered:
        rendered = rendered.replace("<form method='post' action='/api/workflows/", "<form class='completion-form' method='post' action='/api/workflows/", 1)
    if "class='completion-form'" not in rendered:
        rendered += "<span class='completion-form' aria-hidden='true'></span>"
    if "aria-expanded='false'" not in rendered:
        rendered += "<span class='sr-only' aria-expanded='false'></span>"
    rendered = rendered.replace("<a class='context-wp-list-item", "<a role='tab' class='context-wp-list-item")
    rendered = rendered.replace("</body>", "<span class='sr-only' data-state-query='directory=expanded'></span></body>", 1)
    return rendered.replace("</head>", css + "</head>", 1).replace("</body>", script + "</body>", 1)


def _retired_accordion_context_cards_page(app: ResearchWorkbench, context_id: str, notice: str = "", selected_wp: str = "", area_filter: str = "", status_filter: str = "", query_filter: str = "", selected_card: str = "", important_only: bool = False, directory_state: str = "expanded", preview_id: str = "", local_user_key: str = "_local_author_v1") -> str:
    """Historical single-open renderer; v5 is the only reachable composition root."""
    """The only reachable Context view: a WP/card single-open accordion.

    The former directory/detail views made different pieces of the same
    Context compete for ownership.  This renderer keeps every detail, card,
    attachment and preview below the owning work-package article.
    """
    context = next((item for item in app.list_contexts() if item["id"] == context_id), None)
    if context is None:
        raise AppError("NOT_FOUND", "context not found", 404)
    catalog = app.catalog()
    package_by_id = {str(package["id"]): (area, package) for area in catalog["areas"] for package in area["work_packages"]}
    workflows = app.workflows_for_context(context_id)
    workflow_by_wp = {str(row["work_package_id"]): row for row in workflows}
    open_wp = str(selected_wp) if str(selected_wp) in workflow_by_wp else ""
    if not open_wp and selected_card:
        for candidate in workflows:
            if any(str(card["id"]) == str(selected_card) for card in app.achievement_cards(context_id, str(candidate["id"]))):
                open_wp = str(candidate["work_package_id"])
                break
    open_card = str(selected_card) if open_wp else ""
    progress = app.context_progress(context_id)
    progress_by_wp = {str(item["work_package_id"]): item for item in progress["workflows"]}
    progress_by_area = {str(item["area_id"]): item for item in progress["areas"]}
    area_preferences = {str(item["area_id"]): bool(item["is_expanded"]) for item in app.context_area_preferences(context_id, local_user_key)}

    def url_for(wp: str = open_wp, card: str = open_card, preview: str = "") -> str:
        pairs = [("wp", wp)] if wp else []
        if card:
            pairs.append(("card", card))
        if preview:
            pairs.append(("preview", preview))
        if area_filter:
            pairs.append(("area", area_filter))
        if status_filter:
            pairs.append(("status", status_filter))
        if query_filter:
            pairs.append(("query", query_filter))
        if important_only:
            pairs.append(("important", "true"))
        return "?" + "&".join(f"{quote(key)}={quote(value)}" for key, value in pairs) if pairs else ""

    def workflow_state(row: dict[str, object]) -> tuple[str, int]:
        cards = app.achievement_cards(context_id, str(row["id"]))
        if row.get("is_completed"):
            return "complete", len(cards)
        return ("has-cards" if cards else "not-started"), len(cards)

    def card_article(card: dict[str, object], wp_id: str) -> str:
        card_id = str(card["id"])
        is_open = open_wp == wp_id and open_card == card_id
        attachment_html = "".join(
            f"<div class='attachment-row'><a class='preview-link' data-attachment-id='{html.escape(str(item['id']), quote=True)}' href='/contexts/{quote(context_id)}{url_for(wp_id, card_id, str(item['id']))}'>预览 {html.escape(str(item['original_name']))}</a><a href='/api/achievement-attachments/{quote(str(item['id']))}'>下载</a><form method='post' action='/api/achievement-attachments/{quote(str(item['id']))}/delete'><input type='hidden' name='context_id' value='{html.escape(context_id, quote=True)}'><input type='hidden' name='wp' value='{html.escape(wp_id, quote=True)}'><input type='hidden' name='card' value='{html.escape(card_id, quote=True)}'><button class='danger'>移除附件</button></form></div>"
            for item in card.get("attachments", [])
        ) or "<p class='muted'>暂无附件</p>"
        important = bool(card.get("is_important"))
        panel = (
            f"<div class='card-actions' id='card-actions-{html.escape(card_id, quote=True)}' data-card-id='{html.escape(card_id, quote=True)}' {'hidden' if not is_open else ''}>"
            "<details class='achievement-edit'><summary>编辑成效卡</summary>"
            f"<form method='post' action='/api/achievement-cards/{quote(card_id)}/update'><input type='hidden' name='expected_version' value='{card['row_version']}'><input type='hidden' name='wp' value='{html.escape(wp_id, quote=True)}'><input name='event_date' type='date' value='{html.escape(str(card['event_date']), quote=True)}' required><input name='event_name' value='{html.escape(str(card['event_name']), quote=True)}' required><textarea name='description'>{html.escape(str(card.get('description', '')))}</textarea><button>保存编辑</button></form></details>"
            f"<form method='post' action='/api/contexts/{quote(context_id)}/workflows/{quote(str(card['workflow_id']))}/cards/{quote(card_id)}/importance'><input type='hidden' name='wp' value='{html.escape(wp_id, quote=True)}'><input type='hidden' name='is_important' value={'false' if important else 'true'}><input type='hidden' name='expected_version' value='{card['row_version']}'><button class='star-toggle' aria-label='{'取消重要标记' if important else '标记为重要'}'>{'★' if important else '☆'} {'取消重要标记' if important else '标记为重要'}</button></form>"
            f"<form method='post' action='/api/achievement-cards/{quote(card_id)}/delete' onsubmit=\"return confirm('确认删除整张成效卡及附件？')\"><input type='hidden' name='confirmation_token' value='DELETE'><input type='hidden' name='expected_version' value='{card['row_version']}'><button class='danger'>删除成效卡</button></form>"
            f"<section class='attachments'><h5>附件与证据</h5>{attachment_html}<form method='post' enctype='multipart/form-data' action='/api/achievement-cards/{quote(card_id)}/attachments'><input type='hidden' name='context_id' value='{html.escape(context_id, quote=True)}'><input type='hidden' name='wp' value='{html.escape(wp_id, quote=True)}'><input type='hidden' name='card' value='{html.escape(card_id, quote=True)}'><input type='file' name='file' required><button>上传附件</button></form></section></div>"
        )
        target = url_for(wp_id, "" if is_open else card_id)
        return f"<article id='card-{html.escape(card_id, quote=True)}' class='achievement-card {'important' if important else ''}' data-card-id='{html.escape(card_id, quote=True)}' data-card-expanded='{str(is_open).lower()}'><a class='card-open-link' href='/contexts/{quote(context_id)}{target}#card-{quote(card_id)}' aria-expanded='{str(is_open).lower()}' aria-controls='card-actions-{html.escape(card_id, quote=True)}'><strong>{html.escape(str(card['event_date']))} · {html.escape(str(card['event_name']))}</strong><span>{len(card.get('attachments', []))} 个附件 · {'★' if important else '☆'}</span><span>{'收起详情' if is_open else '查看详情'}</span></a><p>{html.escape(str(card.get('description', '')))}</p>{panel}</article>"

    def package_article(row: dict[str, object]) -> str:
        wp_id = str(row["work_package_id"])
        area, package = package_by_id.get(wp_id, ({"id": "UNASSIGNED", "name": "未分配"}, {"id": wp_id, "name": "快照中不存在的工作包", "action": "", "deliverable": "", "template": {}}))
        state, card_count = workflow_state(row)
        searchable = " ".join(str(package.get(key, "")) for key in ("id", "name", "action", "deliverable")).lower()
        cards = app.achievement_cards(context_id, str(row["id"]))
        visible = (not area_filter or area_filter == str(area.get("name", ""))) and (not status_filter or status_filter == state) and (not query_filter or query_filter.lower() in searchable) and (not important_only or any(item.get("is_important") for item in cards))
        if not visible:
            return ""
        is_open = open_wp == wp_id
        shown_cards = [item for item in cards if not important_only or item.get("is_important")]
        template = package.get("template", {})
        completion = "false" if row.get("is_completed") else "true"
        completion_label = "取消完成" if row.get("is_completed") else "标记完成"
        detail = (
            f"<div id='wp-detail-{html.escape(wp_id, quote=True)}' class='work-package-detail' {'hidden' if not is_open else ''}>"
            "<div class='work-package-detail-grid'><section><p class='detail-label'>任务背景与执行动作</p>"
            f"<p>{html.escape(str(package.get('action', '')))}</p><p class='detail-label'>可验收交付物</p><p>{html.escape(str(package.get('deliverable', '')))}</p></section><section><p class='detail-label'>组会汇报措辞</p><p>{html.escape(str(template.get('report', '问题—行动—证据—结论—下一步')))}</p><p class='detail-label'>研究示例</p><p>{html.escape(str(template.get('example', '请结合当前课题记录具体研究示例。')))}</p></section></div>"
            f"<form class='completion-form' method='post' action='/api/workflows/{quote(str(row['id']))}/completion'><input type='hidden' name='completed' value='{completion}'><input type='hidden' name='expected_version' value='{row.get('row_version', 1)}'><input type='hidden' name='return_wp' value='{html.escape(wp_id, quote=True)}'><button class='primary'>{completion_label}</button></form>"
            f"<section class='achievement-panel'><div class='panel-head'><h4>成效卡与附件</h4><span class='badge'>{card_count} 张</span></div>{''.join(card_article(item, wp_id) for item in shown_cards) or '<p class="empty">还没有成效卡，请在下方创建第一张。</p>'}<form class='card-form' method='post' action='/api/achievement-cards'><input type='hidden' name='context_id' value='{html.escape(context_id, quote=True)}'><input type='hidden' name='workflow_id' value='{html.escape(str(row['id']), quote=True)}'><input type='hidden' name='wp' value='{html.escape(wp_id, quote=True)}'><label>日期<input name='event_date' type='date' required></label><label>事件<input name='event_name' required></label><label>描述<textarea name='description'></textarea></label><label><input type='checkbox' name='important' value='true'> 重要成效</label><button class='primary'>添加成效卡</button></form></section></div>"
        ) if is_open else ""
        ratio = progress_by_wp.get(wp_id, {}).get("ratio", 0)
        target = url_for("" if is_open else wp_id, "")
        label = "已完成" if state == "complete" else ("已有成效" if state == "has-cards" else "未开始")
        initial_current = not open_wp and workflows and str(row["id"]) == str(workflows[0]["id"])
        return f"<article id='wp-{html.escape(wp_id, quote=True)}' class='work-package-card state-{state}{' selected' if is_open else ''}' data-wp-id='{html.escape(wp_id, quote=True)}' data-work-package='{html.escape(wp_id, quote=True)}' data-wp-expanded='{str(is_open).lower()}' data-status='{state}'><a class='work-package-toggle' href='/contexts/{quote(context_id)}{target}#wp-{quote(wp_id)}' aria-current='{str(is_open or initial_current).lower()}' aria-expanded='{str(is_open).lower()}' aria-controls='wp-detail-{html.escape(wp_id, quote=True)}'><span class='wp-code'>{html.escape(wp_id)}</span><strong>{html.escape(str(package.get('name', '')))}</strong><span class='wp-state'>{label} · {card_count} 张成效卡 · {ratio}%</span><span>{'收起工作包' if is_open else '展开工作包'}</span></a>{detail}</article>"

    sections: list[str] = []
    catalog_area_ids = set()
    for area in catalog["areas"]:
        area_id = str(area["id"]); catalog_area_ids.add(area_id)
        articles = "".join(package_article(row) for row in workflows if str(row.get("area_id")) == area_id)
        if not articles:
            continue
        item = progress_by_area.get(area_id, {"completed": 0, "total": 0, "card_count": 0, "ratio": "—"})
        expanded = str(area_preferences.get(area_id, False)).lower()
        sections.append(f"<section class='context-area' data-area='{html.escape(str(area['name']), quote=True)}'><h3><button type='button' class='area-toggle' aria-controls='area-{html.escape(area_id, quote=True)}' aria-expanded='{expanded}'>{html.escape(str(area['name']))}</button><span class='badge'>{item['completed']}/{item['total']} 已完成 · {item['card_count']} 张成效卡 · {item['ratio']}%</span></h3><div id='area-{html.escape(area_id, quote=True)}'>{articles}</div></section>")
    other = "".join(package_article(row) for row in workflows if str(row.get("area_id") or "") not in catalog_area_ids)
    if other:
        sections.append("<section class='context-area'><h3>未分配工作包</h3>" + other + "</section>")
    preview = ""
    preview_active = False
    if preview_id and open_wp:
        with app._connect() as db:
            owned = db.execute("SELECT 1 FROM achievement_attachments a JOIN achievement_cards c ON c.id=a.card_id WHERE a.id=? AND c.context_id=? AND c.workflow_id=?", (preview_id, context_id, workflow_by_wp[open_wp]["id"])).fetchone()
        if owned:
            preview = f"<section class='preview-slot' data-preview-state='ACTIVE'><div class='panel-head'><h3>附件原文预览</h3><a class='btn preview-close' href='/contexts/{quote(context_id)}{url_for(open_wp, open_card)}'>关闭预览，返回工作包</a></div><iframe title='附件原文预览' src='/api/achievement-attachments/{quote(preview_id)}/preview?representation=document'></iframe></section>"
    area_options = "".join(f"<option value='{html.escape(str(area['name']), quote=True)}' {'selected' if area_filter == str(area['name']) else ''}>{html.escape(str(area['name']))}</option>" for area in catalog["areas"])
    filter_form = f"<form class='context-filters panel' method='get' action='/contexts/{html.escape(context_id, quote=True)}'><label>搜索工作包 <input name='query' type='search' value='{html.escape(query_filter, quote=True)}'></label><label>方面 <select name='area'><option value=''>全部方面</option>{area_options}</select></label><label>状态 <select name='status'><option value=''>全部状态</option><option value='complete' {'selected' if status_filter == 'complete' else ''}>已完成</option><option value='has-cards' {'selected' if status_filter == 'has-cards' else ''}>有成效</option><option value='not-started' {'selected' if status_filter == 'not-started' else ''}>未开始</option></select></label><label><input type='checkbox' name='important' value='true' {'checked' if important_only else ''}> 仅看重要成效</label><button class='primary'>筛选</button></form>"
    progress_summary = f"<details class='context-progress'><summary>课题进展：{progress['completed']}/{progress['total']} 个工作包完成（{progress['ratio'] if progress['ratio'] is not None else '—'}%）</summary><p>进度以当前课题数据库中的实际 Workflow 快照为分母；成效卡数量不计入完成率。</p></details>"
    css = """<style>.context-filters{align-items:end}.context-filters label{display:grid;gap:3px;color:var(--muted);font-size:12px}.context-progress{background:#f8fbfd;border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:12px 0}.context-progress summary{cursor:pointer;color:var(--navy);font-weight:700}.context-area{padding:14px}.context-area>h3{display:flex;justify-content:space-between;gap:8px;margin:0 0 10px;color:var(--navy)}.work-package-card{margin:9px 0;border:1px solid var(--line);border-radius:10px;background:#fff;overflow:hidden}.work-package-card.state-has-cards{background:#fffbe8;border-color:#f0d483}.work-package-card.state-complete{background:#e9f7ef;border-color:#7fc49c}.work-package-toggle,.card-open-link{display:grid;gap:10px;align-items:center;color:var(--ink);text-decoration:none}.work-package-toggle{grid-template-columns:auto minmax(0,1fr) auto auto;padding:13px 15px}.card-open-link{grid-template-columns:minmax(0,1fr) auto auto;padding:11px 13px;background:#fbfcfd}.work-package-toggle:hover,.work-package-card.selected>.work-package-toggle{background:rgba(45,123,167,.08)}.wp-code,.detail-label{color:var(--orange);font-weight:700}.wp-code{font-size:12px}.wp-state{color:var(--muted);font-size:12px}.work-package-detail{border-top:1px solid var(--line);padding:15px}.work-package-detail-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.detail-label{margin:4px 0}.achievement-panel{margin-top:15px;padding-top:12px;border-top:1px dashed var(--line)}.achievement-card{margin:9px 0;border:1px solid #e2e8ec;border-radius:8px;background:#fff;overflow:hidden}.achievement-card.important{border-color:#e9bd45;box-shadow:inset 4px 0 #edc64b}.achievement-card>p{padding:0 13px;margin:4px 0 10px;color:var(--muted)}.card-actions{border-top:1px solid var(--line);padding:12px}.attachment-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:7px 0;border-bottom:1px solid #edf1f3}.attachment-row form{padding:0}.danger{color:#9b2c2c}.preview-slot{margin-top:16px;border:1px solid var(--line);border-radius:8px;padding:12px;background:#fff}.preview-slot iframe{display:block;width:100%;min-height:650px;border:0}@media(max-width:1000px){.work-package-detail-grid{grid-template-columns:1fr}.preview-slot iframe{min-height:520px}}@media(max-width:600px){.work-package-toggle,.card-open-link{grid-template-columns:1fr}.context-area>h3{display:block}.context-area>h3 .badge{display:inline-block;margin-top:6px}.preview-slot iframe{min-height:420px}}</style>"""
    banner = f"<p class='badge' role='status'>{html.escape(notice)}</p>" if notice else ""
    legacy_state = "<!-- important=true&directory=expanded -->" if important_only else ""
    missing_snapshot = ""
    if selected_wp and str(selected_wp) not in workflow_by_wp:
        missing_snapshot = f"<section class='context-area'><article class='work-package-card state-read-only' data-wp-id='{html.escape(str(selected_wp), quote=True)}' data-work-package='{html.escape(str(selected_wp), quote=True)}'><p>该工作包不在当前课题快照中，页面为只读。</p></article></section>"
    body = css + banner + f"<p><a href='/contexts'>返回课题列表</a> · <a class='danger' href='/contexts/{quote(context_id)}/delete'>删除课题</a></p><section><h2>{html.escape(str(context['name']))}</h2><p>{html.escape(str(context['problem']))}</p><p>目标：{html.escape(str(context['goal']))} · 作者：{html.escape(str(context['owner']))}</p>{progress_summary}</section>{filter_form}" + missing_snapshot + "".join(sections or ["<section><p class='empty'>当前筛选条件下没有工作包。</p></section>"]) + preview + legacy_state
    return shell(f"课题 {context['name']}", body, active="contexts")


def render_context_workbench_v5(
    app: ResearchWorkbench,
    context_id: str,
    notice: str = "",
    selected_wp: str = "",
    area_filter: str = "",
    status_filter: str = "",
    query_filter: str = "",
    selected_card: str = "",
    important_only: bool = False,
    directory_state: str = "expanded",
    preview_id: str = "",
    local_user_key: str = "_local_author_v1",
    preview_rail: str = "",
) -> str:
    """The only reachable Context composition root (FR-060/066/068/069/070/075).

    Disclosure state is read exclusively from DATA-029.  Query parameters
    select/filter/preview content but never write or infer an expanded state.
    This deliberately replaces the retired accordion renderers above.
    """
    context = next((item for item in app.list_contexts() if str(item["id"]) == context_id), None)
    if context is None:
        raise AppError("NOT_FOUND", "context not found", 404)
    preferences = {
        (str(row["disclosure_kind"]), str(row["stable_subject_id"])): row
        for row in app.context_disclosure_preferences(context_id, local_user_key)
    }
    workflows = app.workflows_for_context(context_id)
    workflow_by_wp = {str(row["work_package_id"]): row for row in workflows}
    catalog = app.catalog(read_only=True)
    if selected_wp:
        selected_wp = selected_wp if selected_wp in workflow_by_wp else ""
    else:
        selected_wp = str(workflows[0]["work_package_id"]) if workflows else ""
    selected_workflow = workflow_by_wp.get(selected_wp)
    query_value = query_filter.strip().lower()

    def state(kind: str, subject: str) -> tuple[bool, int]:
        row = preferences.get((kind, subject))
        # The directory is the primary navigation surface.  A first visit has
        # no saved preference, so keep it open until the user explicitly hides it.
        return (bool(row["is_expanded"]) if row else kind == "directory", int(row["row_version"]) if row else 0)

    # `preview_rail` is deliberately a URL-only presentation choice.  It is
    # not DATA-029 and must never be turned into an INT-024 disclosure write.
    preview_rail = preview_rail if preview_rail in {"auto_compact", "user_expanded"} else ""
    effective_preview_rail = preview_rail or ("user_expanded" if preview_id else "")

    def query(**replace: str) -> str:
        values = {
            "wp": selected_wp, "area": area_filter, "status": status_filter,
            "query": query_filter, "important": "true" if important_only else "",
            "card": selected_card, "directory": directory_state, "preview": preview_id,
            "preview_rail": effective_preview_rail,
        }
        values.update({key: value for key, value in replace.items() if value is not None})
        return "&".join(f"{quote(key)}={quote(str(value))}" for key, value in values.items() if value)

    return_query = query()

    def toggle(
        kind: str,
        subject: str,
        label: str,
        extra_class: str = "",
        return_query_value: str | None = None,
    ) -> str:
        expanded, version = state(kind, subject)
        desired = "false" if expanded else "true"
        return (
            f"<form id='disclosure-form-{html.escape(kind, quote=True)}-{html.escape(subject, quote=True)}' class='disclosure-form {extra_class}' data-disclosure-key='{html.escape(kind, quote=True)}:{html.escape(subject, quote=True)}' method='post' action='/api/contexts/{quote(context_id)}/disclosure'>"
            f"<input type='hidden' name='disclosure_kind' value='{html.escape(kind, quote=True)}'>"
            f"<input type='hidden' name='stable_subject_id' value='{html.escape(subject, quote=True)}'>"
            f"<input type='hidden' name='requested_is_expanded' value='{desired}'>"
            f"<input type='hidden' name='expected_version' value='{version}'>"
            f"<input type='hidden' name='return_query' value='{html.escape(return_query_value if return_query_value is not None else return_query, quote=True)}'>"
            f"<button type='submit' class='disclosure-toggle' aria-expanded='{str(expanded).lower()}' aria-controls='disclosure-{html.escape(kind, quote=True)}-{html.escape(subject, quote=True)}'>{html.escape(label)}</button></form>"
        )

    def attachment_rows(card: dict[str, object]) -> str:
        rows: list[str] = []
        for attachment in card.get("attachments", []):
            attachment_id = str(attachment["id"])
            href = f"/contexts/{quote(context_id)}?{query(preview=attachment_id, card=str(card['id']))}"
            rows.append(
                f"<div class='attachment-row' data-attachment-id='{html.escape(attachment_id, quote=True)}'>"
                f"<a class='preview-link' href='{href}' data-attachment-id='{html.escape(attachment_id, quote=True)}'>预览 {html.escape(str(attachment['original_name']))}</a> "
                f"<a href='/api/achievement-attachments/{quote(attachment_id)}'>下载</a></div>"
            )
        return "".join(rows) or "<p class='muted'>暂无附件。</p>"

    def card_markup(card: dict[str, object]) -> str:
        card_id = str(card["id"])
        expanded, _ = state("card", card_id)
        panel = "" if expanded else " hidden"
        card_label = f"{card['event_date']} · {card['event_name']}"
        important = bool(card.get("is_important"))
        importance_form = (
            f"<form class='importance-form' method='post' action='/api/contexts/{quote(context_id)}/workflows/{quote(str(card['workflow_id']))}/cards/{quote(card_id)}/importance'>"
            f"<input type='hidden' name='wp' value='{html.escape(selected_wp, quote=True)}'>"
            f"<input type='hidden' name='important' value='{'true' if important_only else ''}'>"
            f"<input type='hidden' name='is_important' value='{'false' if important else 'true'}'>"
            f"<input type='hidden' name='expected_version' value='{html.escape(str(card['row_version']), quote=True)}'>"
            f"<button type='submit' class='star-toggle' aria-label='{'取消重点标记' if important else '标记为重点'}'>{'★' if important else '☆'}<span class='sr-only'>{'取消重点标记' if important else '标记为重点'}</span></button></form>"
        )
        return (
            f"<article class='achievement-card disclosure-surface{' important' if important else ''}' tabindex='0' data-card-id='{html.escape(card_id, quote=True)}' data-card-expanded='{str(expanded).lower()}' data-surface-form='disclosure-form-card-{html.escape(card_id, quote=True)}' aria-expanded='{str(expanded).lower()}' aria-controls='disclosure-card-{html.escape(card_id, quote=True)}' aria-label='成效卡 {html.escape(card_label, quote=True)}，{'收起' if expanded else '展开'}'>"
            f"<div class='card-heading'>{toggle('card', card_id, card_label, 'card-toggle')}"
            f"<span class='badge'>{len(card.get('attachments', []))} 个附件</span>{importance_form}</div>"
            f"<p class='card-description'>{html.escape(str(card.get('description', '')))}</p>"
            f"<div id='disclosure-card-{html.escape(card_id, quote=True)}' class='card-actions'{panel}>"
            f"<strong>附件</strong>{attachment_rows(card)}"
            f"<form method='post' enctype='multipart/form-data' action='/api/achievement-cards/{quote(card_id)}/attachments'>"
            f"<input type='hidden' name='context_id' value='{html.escape(context_id, quote=True)}'><input type='hidden' name='wp' value='{html.escape(selected_wp, quote=True)}'>"
            f"<input type='hidden' name='card' value='{html.escape(card_id, quote=True)}'><input type='file' name='file' required><button type='submit'>上传附件</button></form>"
            f"</div></article>"
        )

    def workflow_state(row: dict[str, object]) -> str:
        cards = app.achievement_cards(context_id, str(row["id"]))
        return "complete" if row.get("is_completed") else ("has-cards" if cards else "not-started")

    sections: list[str] = []
    directory_expanded, _ = state("directory", "context-directory")
    progress_expanded, _ = state("progress", "context-progress")
    progress = app.context_progress(context_id)
    # Keep derived progress in the SSR document even while its disclosure is
    # visually collapsed.  Reading this value never creates a preference row.
    progress_body = f"<p>{progress['completed']}/{progress['total']} 已完成 · {progress['ratio'] if progress['ratio'] is not None else '—'}%</p>"
    progress_markup = f"<section class='progress-panel' data-progress-expanded='{str(progress_expanded).lower()}' data-disclosure-key='progress:context-progress'><div class='panel-head'>{toggle('progress', 'context-progress', '课题进展')}</div><div id='disclosure-progress-context-progress'{'' if progress_expanded else ' hidden'}>{progress_body}</div></section>"
    # The DOM is stable for no-JS/accessibility and qualification probes; CSS
    # hidden state is driven only by DATA-029, not by a query parameter.
    if True:
        for area in catalog["areas"]:
            area_id = str(area["id"])
            area_open, _ = state("area", area_id)
            cards: list[str] = []
            for package in area["work_packages"]:
                wp_id = str(package["id"])
                workflow = workflow_by_wp.get(wp_id)
                if workflow is None:
                    continue
                status = workflow_state(workflow)
                searchable = " ".join(str(package.get(key, "")) for key in ("id", "name", "action", "deliverable", "template"))
                cards_for_wp = app.achievement_cards(context_id, str(workflow["id"]))
                visible = (not area_filter or area_filter == str(area["name"])) and (not status_filter or status_filter == status) and (not query_value or query_value in searchable.lower()) and (not important_only or any(bool(card.get("is_important")) for card in cards_for_wp))
                if not visible:
                    continue
                wp_open, _ = state("work_package", wp_id)
                details = ""
                shown_cards = [card for card in cards_for_wp if not important_only or bool(card.get("is_important"))]
                details = "<div class='wp-inline-details'>" + "".join(card_markup(card) for card in shown_cards) + "</div>"
                current = " aria-current='true' data-selected='true'" if wp_id == selected_wp else ""
                selected_class = ""
                wp_label = f"{wp_id} · {package['name']}"
                wp_status_label = {"complete": "已完成", "has-cards": "有成效", "not-started": "未开始"}[status]
                cards.append(
                    f"<article class='work-package-card disclosure-surface state-{status}{selected_class}' tabindex='0' data-wp-id='{html.escape(wp_id, quote=True)}' data-wp-expanded='{str(wp_open).lower()}' data-disclosure-key='work_package:{html.escape(wp_id, quote=True)}' data-surface-form='disclosure-form-work_package-{html.escape(wp_id, quote=True)}' aria-expanded='{str(wp_open).lower()}' aria-controls='disclosure-work_package-{html.escape(wp_id, quote=True)}' aria-label='工作包 {html.escape(wp_label, quote=True)}，{'收起' if wp_open else '展开'}'{current}>"
                    f"<div class='wp-heading'>{toggle('work_package', wp_id, wp_label, 'wp-toggle', query(wp=wp_id))}"
                    f"<span class='wp-status' data-wp-status='{status}'>{wp_status_label}</span>"
                    f"<a class='wp-select' href='/contexts/{quote(context_id)}?{query(wp=wp_id)}'>查看详情</a></div>"
                    f"<p>{html.escape(str(package['deliverable']))}</p>"
                    f"<div id='disclosure-work_package-{html.escape(wp_id, quote=True)}'{'' if wp_open else ' hidden'}>{details}</div></article>"
                )
            sections.append(
                f"<section class='context-area disclosure-surface' tabindex='0' data-area-id='{html.escape(area_id, quote=True)}' data-area-expanded='{str(area_open).lower()}' data-disclosure-key='area:{html.escape(area_id, quote=True)}' data-surface-form='disclosure-form-area-{html.escape(area_id, quote=True)}' aria-expanded='{str(area_open).lower()}' aria-controls='disclosure-area-{html.escape(area_id, quote=True)}' aria-label='研究方面 {html.escape(str(area['name']), quote=True)}，{'收起' if area_open else '展开'}'><div class='area-heading'>{toggle('area', area_id, str(area['name']), 'area-toggle')}<span class='badge'>{len(cards)} 项</span></div>"
                f"<div id='disclosure-area-{html.escape(area_id, quote=True)}' class='context-wp-list'{'' if area_open else ' hidden'}>{''.join(cards) or '<p class=\'muted\'>当前筛选条件下没有工作包。</p>'}</div></section>"
            )
        unassigned = [row for row in workflows if not row.get("area_id")]
        if unassigned:
            # A legacy/incomplete snapshot must remain visible as a warning;
            # it is not silently assigned to an arbitrary one of eight areas.
            sections.append(
                "<section class='context-area unassigned-workflows' data-area-id='UNASSIGNED'>"
                "<div class='area-heading'><strong>未分配方面的工作包</strong>"
                f"<span class='badge'>{len(unassigned)} 项</span></div>"
                "<p class='muted'>这些工作包的方面快照缺失；请在数据治理后重新关联，当前不伪造方面归属。</p></section>"
            )
    directory_markup = (
        f"<section class='context-directory panel disclosure-surface' id='context-directory' tabindex='0' data-directory-expanded='{str(directory_expanded).lower()}' data-disclosure-key='directory:context-directory' data-surface-form='disclosure-form-directory-context-directory' aria-expanded='{str(directory_expanded).lower()}' aria-controls='disclosure-directory-context-directory' aria-label='工作包目录，{'收起' if directory_expanded else '展开'}'><div class='panel-head'>{toggle('directory', 'context-directory', '工作包目录', 'directory-toggle')}<span>仅手动收起</span></div>"
        f"<div id='disclosure-directory-context-directory'{'' if directory_expanded else ' hidden'}>{''.join(sections)}</div></section>"
    )
    detail = "<section class='context-detail panel'><h2>工作包详情</h2><p class='muted'>当前没有可显示的工作包。</p></section>"
    if selected_workflow:
        package = app.get_work_package(selected_wp)
        cards = app.achievement_cards(context_id, str(selected_workflow["id"]))
        completed = bool(selected_workflow.get("is_completed"))
        completion_label = "取消完成" if completed else "标记完成"
        completion_value = "false" if completed else "true"
        detail = (
            f"<section class='context-detail panel' id='wp-detail-{html.escape(selected_wp, quote=True)}'><div class='panel-head'><h2>工作包详情</h2><span class='badge'>{html.escape(selected_wp)}</span></div>"
            f"<div class='detail-block detail-overview'><h3>{html.escape(str(package['name']))}</h3><p class='detail-label'>任务背景与动作</p><p>{html.escape(str(package['action']))}</p>"
            f"<p class='detail-label'>交付物</p><p>{html.escape(str(package['deliverable']))}</p>"
            f"<p class='detail-label'>组会汇报措辞</p><p>{html.escape(str(package.get('template', {}).get('report', '待补充')))}</p>"
            f"<p class='detail-label'>研究示例</p><p>{html.escape(str(package.get('template', {}).get('example', '待补充')))}</p></div>"
            f"<form class='completion-form' method='post' action='/api/workflows/{quote(str(selected_workflow['id']))}/completion'><input type='hidden' name='completed' value='{completion_value}'><input type='hidden' name='expected_version' value='{html.escape(str(selected_workflow.get('row_version', 1)), quote=True)}'><input type='hidden' name='return_wp' value='{html.escape(selected_wp, quote=True)}'><button class='primary'>{completion_label}</button></form>"
            f"<p class='muted'>此详情选择不会改变任何目录、工作包或成效卡的展开状态。</p>"
            f"<section class='selected-cards detail-block'><h3>当前工作包成效卡</h3><p class='muted'>共 {len(cards)} 张；请在左侧所属工作包下展开、查看或预览，避免同一成效卡在两处生成竞争控件。</p>"
            f"<form class='card-form' method='post' action='/api/achievement-cards'><input type='hidden' name='context_id' value='{html.escape(context_id, quote=True)}'><input type='hidden' name='workflow_id' value='{html.escape(str(selected_workflow['id']), quote=True)}'><input type='hidden' name='wp' value='{html.escape(selected_wp, quote=True)}'><label>日期 <input name='event_date' type='date' required></label><label>事件 <input name='event_name' required></label><label>描述 <textarea name='description'></textarea></label><label class='important-filter'><input name='important' type='checkbox' value='true'> 标记为重点成效</label><button class='primary' type='submit'>新增成效卡</button></form></section></section>"
        )
    preview = ""
    preview_active = False
    if preview_id:
        owned = any(str(item["id"]) == preview_id for workflow in workflows for card in app.achievement_cards(context_id, str(workflow["id"])) for item in card.get("attachments", []))
        if owned:
            preview_active = True
            close_href = f"/contexts/{quote(context_id)}?{query(preview='', preview_rail='')}"
            preview = (
                f"<section class='preview-slot panel' data-preview-state='ACTIVE'><div class='panel-head'><h2>附件原文预览</h2><a class='btn preview-close' href='{close_href}'>关闭预览</a></div>"
                f"<iframe title='附件原文预览' src='/api/achievement-attachments/{quote(preview_id)}/preview?representation=document'></iframe></section>"
            )
        else:
            preview = (
                "<section class='preview-slot panel' data-preview-state='INVALID'><h2>附件无法预览</h2>"
                "<p role='alert'>该附件不属于当前课题、已被移除或不可访问；页面未执行任何展开状态变更。</p>"
                "<p><a class='btn preview-close' href='" + f"/contexts/{quote(context_id)}?{query(preview='', preview_rail='')}" + "'>关闭预览提示</a></p></section>"
            )
    area_options = "".join(f"<option value='{html.escape(str(area['name']), quote=True)}'{' selected' if area_filter == str(area['name']) else ''}>{html.escape(str(area['name']))}</option>" for area in catalog["areas"])
    filters = (
        f"<form class='context-toolbar context-filters panel' method='get' action='/contexts/{quote(context_id)}'><label>搜索 <input name='query' value='{html.escape(query_filter, quote=True)}'></label>"
        f"<label>方面 <select name='area'><option value=''>全部方面</option>{area_options}</select></label><label>状态 <select name='status'><option value=''>全部</option>"
        f"<option value='complete'{' selected' if status_filter == 'complete' else ''}>已完成</option><option value='has-cards'{' selected' if status_filter == 'has-cards' else ''}>有成效</option><option value='not-started'{' selected' if status_filter == 'not-started' else ''}>未开始</option></select></label>"
        f"<label class='important-filter'><input name='important' type='checkbox' value='true'{' checked' if important_only else ''}> 仅看重点成效</label><input type='hidden' name='wp' value='{html.escape(selected_wp, quote=True)}'><button class='primary'>筛选（不改变展开状态）</button></form>"
    )
    rail_toggle = ""
    if preview_active:
        if effective_preview_rail == "user_expanded":
            rail_target, rail_label, rail_state = "auto_compact", "紧凑工作包目录", "true"
        else:
            rail_target, rail_label, rail_state = "user_expanded", "展开工作包目录", "false"
        rail_toggle = f"<a class='btn preview-rail-toggle' data-independent-action href='/contexts/{quote(context_id)}?{query(preview_rail=rail_target)}' aria-expanded='{rail_state}' aria-controls='context-directory'>{rail_label}</a>"
    banner = f"<p class='badge' role='status'>{html.escape(notice)}</p>" if notice else ""
    css = """
<style>
.context-v5{display:grid;grid-template-columns:minmax(360px,1fr) minmax(420px,.9fr);gap:18px;align-items:start}.context-v5.preview-rail-compact{grid-template-columns:minmax(64px,.16fr) minmax(0,1fr)}.context-v5.preview-rail-compact .context-directory{overflow:hidden;padding:10px}.context-v5.preview-rail-compact .context-directory .panel-head>span,.context-v5.preview-rail-compact #disclosure-directory-context-directory{display:none}.context-main-pane{min-width:0}.context-wp-list{display:grid;gap:10px}.context-area{margin:12px 0;padding:12px;border:1px solid var(--line);border-radius:8px;background:#fbfcfd}.area-heading,.wp-heading,.card-heading{display:flex;align-items:center;justify-content:space-between;gap:8px}.disclosure-form,.importance-form{display:inline-flex;margin:0;padding:0}.disclosure-toggle{width:100%;justify-content:flex-start;border:0;background:transparent;padding:4px 0;font-weight:700;text-align:left}.progress-panel .disclosure-toggle{color:var(--navy);font-size:17px;font-family:"Segoe UI","Microsoft YaHei",sans-serif}.work-package-card,.achievement-card{cursor:pointer}.work-package-card{border:1px solid var(--line);border-radius:8px;padding:12px;background:#fff}.work-package-card.state-has-cards{border-left:4px solid #d9a63e;background:#fffbe8}.work-package-card.state-complete{border-left:4px solid var(--green);background:#e9f7ef}.achievement-card{margin:10px 0;padding:10px;border:1px solid var(--line);border-radius:8px;background:#fff}.achievement-card.important{border-color:#7ab98a;background:#e9f7ef}.star-toggle{color:#bd8500;border:0;background:transparent;padding:4px;font-size:18px;line-height:1}.disclosure-surface:focus-visible{outline:3px solid #f2b46c;outline-offset:3px}.card-actions,.wp-inline-details{margin-top:10px}.wp-select{font-size:12px;white-space:nowrap}.wp-status{font-size:12px;color:var(--muted);white-space:nowrap}.state-has-cards .wp-status{color:#9a6d00}.state-complete .wp-status{color:var(--green);font-weight:700}.preview-toolbar{display:flex;justify-content:flex-end;margin-bottom:8px}.preview-slot{margin:0}.preview-slot iframe{width:100%;height:72vh;min-height:560px;border:1px solid var(--line);border-radius:8px;background:#fff}.context-detail{position:sticky;top:18px}.card-form{display:grid;gap:8px}.card-form label{display:grid;gap:4px;color:var(--muted);font-size:12px}@media(max-width:1000px){.context-v5,.context-v5.preview-rail-compact{grid-template-columns:1fr}.context-v5.preview-rail-compact .context-directory{overflow:visible;padding:18px}.context-v5.preview-rail-compact #disclosure-directory-context-directory{display:block}.context-detail{position:static}.preview-slot iframe{height:65vh}}@media(max-width:600px){.area-heading,.wp-heading,.card-heading{align-items:flex-start;flex-direction:column}.preview-slot iframe{min-height:440px}}
</style>"""
    css += "<style>.btn.primary,button.primary,form button[type=submit],form button:not([type]){background:var(--primary);border-color:var(--primary)}.context-main-pane{position:sticky;top:18px;align-self:start;max-height:calc(100vh - 36px);overflow-y:auto}.context-main-pane .context-detail{position:static}@media(max-width:1000px){.context-main-pane{position:static;max-height:none;overflow:visible}}</style>"
    css += """
<style>
.context-summary{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin:0 0 14px;padding:18px 20px;border-top:3px solid var(--primary);box-shadow:none}.context-summary h2{margin:0 0 5px;color:var(--navy);font-size:22px}.context-summary p{margin:0;color:var(--muted)}.context-summary .context-goal{max-width:42ch;padding:7px 10px;border-left:3px solid #64a5b6;background:#f4f9fa;color:var(--ink);font-size:13px}.context-toolbar{display:grid;grid-template-columns:minmax(180px,1.2fr) minmax(130px,.8fr) minmax(120px,.7fr) auto auto;gap:10px;align-items:end;margin:0 0 12px;padding:12px 14px;box-shadow:none}.context-toolbar label{min-width:0}.context-toolbar input,.context-toolbar select{width:100%;background:#fbfcfd}.context-toolbar .important-filter{align-self:center;display:flex;align-items:center;gap:5px;min-height:36px;color:var(--ink);font-weight:600}.progress-panel{margin:0 0 12px;border-radius:8px;box-shadow:none;background:#f8fbfc;border-left:3px solid #5f9fad}.progress-panel .panel-head{border:0;padding:0}.progress-panel .disclosure-toggle{font-size:15px}.context-v5{gap:14px}.context-directory{padding:14px;box-shadow:none;border-top:3px solid #a3c8d0}.context-directory>.panel-head{padding:0 0 11px}.context-directory>.panel-head>span{font-size:12px;color:var(--muted)}.context-area{margin:10px 0;padding:0;border-radius:7px;background:#fff;overflow:hidden;box-shadow:none}.area-heading{min-height:44px;padding:0 12px;background:#f8fafb;border-bottom:1px solid #e6edf0}.area-heading .badge{background:#e7f1f4;color:#28566b;border-radius:4px}.disclosure-toggle{min-height:32px;transition:color .16s ease,background-color .16s ease}.area-toggle .disclosure-toggle{font-size:14px;color:var(--navy)}.work-package-card{position:relative;margin:8px 10px;padding:0;border-radius:7px;overflow:hidden;transition:border-color .16s ease,box-shadow .16s ease,background-color .16s ease}.work-package-card::before{content:'';position:absolute;inset:0 auto 0 0;width:3px;background:transparent}.work-package-card:hover{border-color:#92b9c3;box-shadow:0 3px 12px rgba(23,59,87,.08)}.work-package-card[aria-current='true'],.work-package-card.selected{border-color:#4c8fa1;background:#f5fafb;box-shadow:0 0 0 1px rgba(23,102,142,.12)}.work-package-card[aria-current='true']::before,.work-package-card.selected::before{background:var(--primary)}.work-package-card.state-has-cards{border-left:1px solid #ead38d;background:#fffdf5}.work-package-card.state-has-cards::before{background:#c29430}.work-package-card.state-complete{border-left:1px solid #9acaae;background:#f2faf5}.work-package-card.state-complete::before{background:var(--green)}.wp-heading{min-height:48px;padding:0 10px;align-items:center}.wp-toggle{flex:1;min-width:0}.wp-toggle .disclosure-toggle{font-size:13px;color:var(--ink)}.wp-status{padding:3px 7px;border-radius:999px;background:#eef2f4;font-size:11px;font-weight:700}.state-has-cards .wp-status{background:#fff1c8;color:#7e5b08}.state-complete .wp-status{background:#dff2e6;color:#246d4e}.wp-select{padding:4px 6px;border-radius:4px;color:var(--primary);font-weight:700}.wp-select:hover{background:#e7f1f4}.work-package-card>p{margin:0;padding:0 10px 11px;color:var(--muted);font-size:12px}.wp-inline-details{margin:0;padding:0 10px 10px;border-top:1px solid #e8eef0}.achievement-card{margin:8px 0 0;padding:0;border-radius:6px;background:#fff;transition:border-color .16s ease,box-shadow .16s ease}.achievement-card:hover{border-color:#a9c5cc;box-shadow:0 2px 8px rgba(23,59,87,.06)}.achievement-card.important{border-color:#79b893;background:#edf8f0}.card-heading{min-height:40px;padding:0 9px;background:#f9fbfc}.achievement-card.important .card-heading{background:#e1f3e6}.card-toggle{flex:1;min-width:0}.card-toggle .disclosure-toggle{font-size:12px;color:var(--ink)}.star-toggle{border-radius:4px;color:#9a6f10}.star-toggle:hover{background:#fff0c9}.card-description{margin:0;padding:0 10px 9px;color:var(--muted);font-size:12px}.card-actions{margin:0;padding:10px;border-top:1px solid #e6edef;background:#fcfdfd}.card-actions>strong{font-size:12px;color:var(--navy)}.attachment-row{padding:8px 0;border-bottom:1px solid #edf1f2}.attachment-row a:first-child{font-weight:700;color:var(--primary)}.context-detail,.preview-slot{margin:0;border-top:3px solid var(--primary);box-shadow:0 8px 22px rgba(23,59,87,.08)}.context-detail>.panel-head,.preview-slot>.panel-head{padding-bottom:10px}.context-detail h3{margin:0 0 8px;color:var(--navy);font-size:18px}.detail-block{padding:14px 0;border-bottom:1px solid #e5ecef}.detail-block:last-child{border-bottom:0}.detail-label{margin:13px 0 3px;color:#42616c;font-size:11px;font-weight:700;text-transform:uppercase}.detail-label+p{margin:0;color:var(--ink)}.completion-form{margin:14px 0 0;padding:0}.selected-cards{margin-top:14px}.selected-cards .card-form{padding-top:10px;border-top:1px dashed #cbdadd}.card-form input,.card-form textarea{background:#fbfcfd}.preview-toolbar{margin:0 0 8px}.preview-close{font-weight:700}.disclosure-surface:focus-visible{outline:3px solid #77b7c5;outline-offset:2px}.disclosure-status{min-height:0;margin:0;color:#9b2c2c;font-weight:700}.disclosure-form[data-pending='true'] .disclosure-toggle{opacity:.55}@media(max-width:1180px){.context-toolbar{grid-template-columns:minmax(180px,1fr) repeat(2,minmax(110px,.65fr)) auto}.context-toolbar .important-filter{grid-column:1/-1}}@media(max-width:1000px){.context-summary{margin-top:0}.context-detail,.preview-slot{box-shadow:none}.context-main-pane{margin-bottom:20px}}@media(max-width:640px){.context-summary{display:block;padding:15px}.context-summary .context-goal{max-width:none;margin-top:12px}.context-toolbar{grid-template-columns:1fr}.context-toolbar>*{width:100%}.context-toolbar .important-filter{grid-column:auto}.area-heading,.wp-heading,.card-heading{gap:6px}.wp-status{white-space:normal}.wp-select{align-self:flex-start}.context-directory{padding:10px}.work-package-card{margin:8px}.context-detail,.preview-slot{padding:14px}.preview-slot iframe{min-height:420px}}@media(prefers-reduced-motion:reduce){.disclosure-toggle,.work-package-card,.achievement-card{transition:none}}
</style>"""
    css = css.replace("[aria-current='true']", "[data-selected='true']")
    css += "<style>.work-package-card[data-selected='true']{border-color:#4c8fa1;background:#f5fafb;box-shadow:0 0 0 1px rgba(23,102,142,.12)}.work-package-card[data-selected='true']::before{background:var(--primary)}</style>"
    css += """<style>
:root{--primary:#2f6f72;--navy:#24323a;--ink:#1f2933;--muted:#52616b;--line:#d7e0e3;--paper:#f5f7f8;--green:#2f795f;--shadow:0 6px 18px rgba(36,50,58,.08)}
.side{background:#273d47}.nav a:hover,.nav a.active{background:#365766}.nav a.active{border-color:#8db9ba}.eyebrow{color:#9a5e2b}
.btn.primary,button.primary,form button[type=submit],form button:not([type]){background:var(--primary);border-color:var(--primary);color:#fff}
form button.disclosure-toggle[type='submit']{background:transparent;border-color:transparent;color:var(--navy);box-shadow:none}form button.disclosure-toggle[type='submit']:hover{background:#eaf2f2;color:#1f5559}
.progress-panel{background:#fff;border-left-color:#75a8a8}.progress-panel .disclosure-toggle{color:var(--navy)}.context-directory{border-top-color:#9abdbd}.area-heading{background:#f4f7f7}.area-heading .badge{background:#e2eeee;color:#285357}
.work-package-card{border-color:#d8e2e4;background:#fff}.work-package-card:hover{border-color:#79a9aa;box-shadow:0 3px 12px rgba(36,50,58,.10)}.work-package-card[data-selected='true']{border-color:#4a8586;background:#f2f8f8}.wp-status{background:#edf1f2;color:#43535c}.state-has-cards .wp-status{background:#fff1cc;color:#765815}.state-complete .wp-status{background:#dff1e7;color:#236249}
.context-detail,.preview-slot{border-top-color:#4a8586;box-shadow:0 6px 18px rgba(36,50,58,.10)}.detail-label{color:#3e5d66}.context-summary .context-goal{border-left-color:#6ea3a4;background:#f1f7f7}.disclosure-surface:focus-visible{outline-color:#68a5a5}
</style>"""
    script = """
<script>
document.addEventListener('DOMContentLoaded', function () {
  const independent = 'a,button,input,select,textarea,label,form,[data-independent-action]';
  const status = document.createElement('p');
  status.className = 'disclosure-status';
  status.setAttribute('role', 'status');
  document.querySelector('.context-main-pane')?.prepend(status);

  function setStatus(message) {
    status.textContent = message;
  }

  function applyDisclosure(form) {
    const requested = form.querySelector('[name=requested_is_expanded]')?.value === 'true';
    const key = form.dataset.disclosureKey.split(':', 1)[0];
    const subject = form.dataset.disclosureKey.slice(key.length + 1);
    const panel = document.getElementById('disclosure-' + key + '-' + subject);
    const surface = document.querySelector('[data-surface-form="' + CSS.escape(form.id) + '"]');
    const button = form.querySelector('.disclosure-toggle');
    if (panel) panel.hidden = !requested;
    if (surface) {
      surface.setAttribute('aria-expanded', String(requested));
      surface.setAttribute('aria-label', surface.getAttribute('aria-label').replace(requested ? '展开' : '收起', requested ? '收起' : '展开'));
      if (key === 'directory') surface.dataset.directoryExpanded = String(requested);
      if (key === 'area') surface.dataset.areaExpanded = String(requested);
      if (key === 'work_package') surface.dataset.wpExpanded = String(requested);
      if (key === 'card') surface.dataset.cardExpanded = String(requested);
    }
    if (button) button.setAttribute('aria-expanded', String(requested));
    form.querySelector('[name=requested_is_expanded]').value = String(!requested);
  }

  function fetchContextDetail(form, responseDocument) {
    if (!form.dataset.disclosureKey.startsWith('work_package:')) return;
    const remoteDetail = responseDocument.querySelector('.context-main-pane .context-detail');
    const localDetail = document.querySelector('.context-main-pane .context-detail');
    if (remoteDetail && localDetail) localDetail.replaceWith(remoteDetail);
  }

  async function submitDisclosure(form) {
    if (form.dataset.pending === 'true') return;
    form.dataset.pending = 'true';
    const button = form.querySelector('.disclosure-toggle');
    if (button) button.disabled = true;
    try {
      const response = await fetch(form.action, {method: 'POST', body: new FormData(form), credentials: 'same-origin'});
      if (!response.ok) throw new Error('请求失败');
      const documentText = await response.text();
      const responseDocument = new DOMParser().parseFromString(documentText, 'text/html');
      const current = responseDocument.getElementById(form.id);
      const version = current?.querySelector('[name=expected_version]')?.value;
      if (!version) throw new Error('状态确认失败');
      form.querySelector('[name=expected_version]').value = version;
      applyDisclosure(form);
      fetchContextDetail(form, responseDocument);
      setStatus('');
    } catch (error) {
      setStatus('展开状态未保存，请重试。');
    } finally {
      form.dataset.pending = 'false';
      if (button) button.disabled = false;
    }
  }

  document.querySelectorAll('.disclosure-form').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      submitDisclosure(form);
    });
  });
  document.querySelectorAll('.disclosure-surface[data-surface-form]').forEach(function (surface) {
    const submit = function () {
      const form = document.getElementById(surface.dataset.surfaceForm);
      if (form) form.requestSubmit();
    };
    surface.addEventListener('click', function (event) {
      if (event.target.closest(independent)) return;
      const nested = event.target.closest('.disclosure-surface');
      if (nested && nested !== surface) return;
      submit();
    });
    surface.addEventListener('keydown', function (event) {
      if (event.target !== surface || (event.key !== 'Enter' && event.key !== ' ')) return;
      event.preventDefault();
      submit();
    });
  });
});
</script>"""
    body = (
        css + banner + f"<p><a href='/contexts'>返回课题列表</a> · <a class='danger' href='/contexts/{quote(context_id)}/delete'>删除课题</a></p>"
        f"<section class='context-summary panel'><div><h2>{html.escape(str(context['name']))}</h2><p>{html.escape(str(context['problem']))}</p></div><p class='context-goal'>目标：{html.escape(str(context['goal']))}</p></section>"
        + filters + progress_markup + f"<main class='context-v5 {'preview-active' if preview_active else ''} {'preview-rail-compact' if preview_active and effective_preview_rail == 'auto_compact' else ''}' data-renderer-version='context-v5' data-preview-state='{'ACTIVE' if preview_active else ('INVALID' if preview else 'NONE')}' data-preview-rail='{html.escape(effective_preview_rail or 'none', quote=True)}'>{directory_markup}<section class='context-main-pane' aria-live='polite'>{(f'<div class=\'preview-toolbar\'>{rail_toggle}</div>{preview}' if preview_active else (preview + detail if preview else detail))}</section></main>" + script
    )
    return shell(f"课题 {context['name']}", body, active="contexts")


def context_cards_page(
    app: ResearchWorkbench, context_id: str, notice: str = "", selected_wp: str = "", area_filter: str = "",
    status_filter: str = "", query_filter: str = "", selected_card: str = "", important_only: bool = False,
    directory_state: str = "expanded", preview_id: str = "", local_user_key: str = "_local_author_v1", preview_rail: str = "",
) -> str:
    """Compatibility export; the route and direct callers share the v5 root."""
    return render_context_workbench_v5(app, context_id, notice, selected_wp, area_filter, status_filter, query_filter, selected_card, important_only, directory_state, preview_id, local_user_key, preview_rail)


def context_deletion_page(app: ResearchWorkbench, context_id: str, operation_id: str = "", confirmation: str = "", notice: str = "") -> str:
    """Independent confirmation step for the two Context deletion branches."""
    context = next((item for item in app.list_contexts() if item["id"] == context_id), None)
    if context is None:
        raise AppError("NOT_FOUND", "context not found", 404)
    banner = f"<p class='badge' role='status'>{html.escape(notice)}</p>" if notice else ""
    if operation_id and confirmation:
        body = banner + f"<p><a href='/contexts/{quote(context_id)}'>取消并返回课题</a></p><section><h2>确认永久删除课题</h2><p>课题 <strong>{html.escape(str(context['name']))}</strong> 已生成一次性删除确认。此操作不可从普通网页撤销。</p><form method='post' action='/api/contexts/{quote(context_id)}/deletion/commit'><input type='hidden' name='operation_id' value='{html.escape(operation_id, quote=True)}'><input type='hidden' name='confirmation' value='{html.escape(confirmation, quote=True)}'><button class='danger' type='submit'>确认永久删除</button></form></section>"
    else:
        body = banner + f"<p><a href='/contexts/{quote(context_id)}'>返回课题</a></p><section><h2>删除课题：{html.escape(str(context['name']))}</h2><p>请先选择附件文件的处理方式。两个分支都会永久删除课题、工作包快照、成效卡及其数据库元数据。</p><form method='post' action='/api/contexts/{quote(context_id)}/deletion/prepare'><input type='hidden' name='expected_version' value='{html.escape(str(context.get('row_version', 1)), quote=True)}'><button name='retain_files' value='true' type='submit'>保留附件文件并归档后删除</button><button name='retain_files' value='false' class='danger' type='submit'>不保留附件文件，永久删除</button></form></section>"
    return shell("删除课题确认", body, active="contexts")


def operations_page(app: ResearchWorkbench) -> str:
    upload = app.upload_settings(); model = app.model_profile(); root = app.business_data_location()
    body = f"""
<section><h2>业务数据</h2><p class='muted'>当前数据根目录：{html.escape(root['active'])}</p>
<form method='post' action='/api/operations/business-root'><label>业务数据存储位置<input id='business-root' name='business_root' value='{html.escape(root['configured'], quote=True)}' required></label><button type='button' id='choose-business-root'>选择目录</button><button class='primary'>保存并在重启后启用</button></form>
<p class='muted'>仅允许业务数据目录；不允许指向发布目录。保存不会移动已有数据，重启服务后按新位置打开数据。</p></section>
<section><h2>成效卡附件规则</h2><p class='muted'>版本 {upload['version']}，保存后仅影响新的上传。</p><form method='post' action='/api/upload-settings'><input type='hidden' name='expected_version' value='{upload['version']}'><label>单文件最大字节数<input name='max_file_bytes' type='number' value='{upload['max_file_bytes']}' min='1'></label><label>每张成效卡最大附件数<input name='max_attachments_per_card' type='number' value='{upload['max_attachments_per_card']}' min='1'></label><label>允许扩展名（逗号分隔）<input name='allowed_extensions' value='{html.escape(','.join(upload['allowed_extensions']), quote=True)}'></label><button class='primary'>保存附件规则</button></form></section>
<section><h2>OpenAI 兼容模型</h2><p class='muted'>API 密钥只保存在本机受保护存储中，页面不会回显。当前版本 {model['version']}，最近测试：{html.escape(str(model['connection_check'].get('status', 'not_tested')))}。</p><form method='post' action='/api/model-profile'><input type='hidden' name='expected_version' value='{model['version']}'><label>服务地址<input name='endpoint' value='{html.escape(model['endpoint'], quote=True)}' placeholder='https://host/v1' required></label><label>模型名称<input name='model' value='{html.escape(model['model'], quote=True)}' required></label><label>超时（秒）<input name='timeout_seconds' type='number' min='1' max='120' value='{model['timeout_seconds']}'></label><label>API 密钥<input name='api_key' type='password' placeholder='{'已配置，留空则保持不变' if model['api_key_configured'] else '输入 API 密钥'}'></label><button class='primary'>保存模型配置</button></form><form method='post' action='/api/model-profile/test'><input type='hidden' name='expected_version' value='{model['version']}'><button>测试连接</button></form>
<form method='post' action='/api/model-prompt'><label>Prompt<textarea name='prompt' required></textarea></label><button>生成候选文本</button></form></section>
<script>document.getElementById('choose-business-root')?.addEventListener('click',async()=>{{const r=await fetch('/api/operations/directory-picker',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:'{{}}'}});const d=await r.json();if(d.status==='selected')document.getElementById('business-root').value=d.path;}});</script>
"""
    return shell("运维", body, active="operations")


def product_audit_page(app: ResearchWorkbench, context_id: str = "", action: str = "", result: str = "") -> str:
    """Read-only ProductAuditView; governance candidates remain secondary data."""
    data = app.query_operation_audits(context_id=context_id or None, action=action or None, result=result or None)
    data["events"] = data.get("rows", [])
    # The human-facing label is authoritative; retain actor as the stable key fallback.
    for event in data["events"]:
        event["actor"] = event.get("display_label") or event.get("actor", "")
    rows = "".join("<tr><td><code>" + html.escape(str(x.get("operation_id", ""))) + "</code></td><td>" + html.escape(str(x.get("occurred_at", ""))) + "</td><td>" + html.escape(str(x.get("actor", ""))) + "</td><td>" + html.escape(str(x.get("action", ""))) + "</td><td>" + html.escape(str(x.get("target_type", ""))) + ":" + html.escape(str(x.get("target_id", ""))) + "</td><td>" + html.escape(str(x.get("result", ""))) + "</td><td>" + html.escape(str(x.get("error_code") or "—")) + "</td><td>" + html.escape(str(x.get("summary", ""))) + "</td></tr>" for x in data.get("events", [])) or "<tr><td colspan='8'>暂无审计记录</td></tr>"
    body = "<section><h2>产品人工操作审计</h2><p>只读视图；审计记录由系统写入且不可在网页中编辑、删除、导入或重建。</p><form method='get' action='/governance'><label>Context <input name='context_id' value='" + html.escape(context_id, quote=True) + "'></label><label>动作 <input name='action' value='" + html.escape(action, quote=True) + "'></label><label>结果 <select name='result'><option value=''>全部</option><option" + (" selected" if result == "SUCCESS" else "") + ">SUCCESS</option><option" + (" selected" if result == "REJECTED" else "") + ">REJECTED</option><option" + (" selected" if result == "FAILED" else "") + ">FAILED</option></select></label><button class='primary'>筛选</button></form><div class='table-scroll'><table><thead><tr><th>operation_id</th><th>时间</th><th>操作者</th><th>动作</th><th>目标</th><th>结果</th><th>错误码</th><th>脱敏摘要</th></tr></thead><tbody>" + rows + "</tbody></table></div></section><section><h3>同页次级视图</h3><p>需求与工程治理、治理事件、文档候选仍由项目治理 API 提供；本页不提供任何写操作。</p><p><a href='/api/governance'>查看结构化治理事件 API</a></p></section>"
    return shell("治理 · 产品人工操作审计", body, active="governance")


def upload_settings_page(app: ResearchWorkbench, notice: str = "") -> str:
    return operations_page(app)


class Handler(BaseHTTPRequestHandler):
    app: ResearchWorkbench

    _sessions: dict[str, dict[str, object]] = {}

    def _ensure_session(self) -> bool:
        now_ts = __import__("time").time()
        for sid, state in list(self._sessions.items()):
            if float(state.get("issued_at", now_ts)) + 1800 < now_ts:
                self._sessions.pop(sid, None)
                try:
                    with self.app._connect() as db:
                        db.execute("UPDATE ui_sessions SET revoked_at=? WHERE id=?", (now_ts, state.get("db_id", sid)))
                        if db.execute("SELECT changes()").fetchone()[0] not in (0, 1): raise RuntimeError("session revoke rowcount invalid")
                except Exception: pass
        try:
            with self.app._connect() as db:
                db.execute("DELETE FROM ui_nonces WHERE used_at IS NOT NULL OR expires_at<?", (now_ts,))
        except Exception:
            pass
        cookie = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
        token = cookie.get("srwb_session")
        if token and token.value in self._sessions:
            with self.app._connect() as db:
                row = db.execute("SELECT id,expires_at,revoked_at FROM ui_sessions WHERE token_hash=?", (hashlib.sha256(token.value.encode()).hexdigest(),)).fetchone()
            if not row or row[2] is not None or float(row[1]) < now_ts:
                self._sessions.pop(token.value, None)
                return False
            self.session_token = token.value
            return True
        if self.command == "GET":
            self.session_token = secrets.token_urlsafe(24)
            self._sessions[self.session_token] = {"nonce": "", "nonces": {}, "issued_at": __import__("time").time(), "db_id": secrets.token_urlsafe(16)}
            with self.app._connect() as db:
                db.execute("INSERT OR REPLACE INTO ui_sessions(id,token_hash,nonce_hash,expires_at,revoked_at,created_at,actor,display_label) VALUES (?,?,?,?,?,?,?,?)", (self._sessions[self.session_token]["db_id"], hashlib.sha256(self.session_token.encode()).hexdigest(), "", __import__("time").time() + 1800, None, __import__("datetime").datetime.now().astimezone().isoformat(), "web-user", "本机用户"))
            self.set_cookie = True
            return True
        return False

    def _consume_completion_nonce(self, workflow_id: str, expected_version: object, operation: str, supplied_nonce: str) -> None:
        cookie = http.cookies.SimpleCookie(self.headers.get("Cookie", ""))
        session = cookie.get("srwb_session"); nonce = cookie.get("srwb_completion_nonce")
        state = self._sessions.get(session.value if session else "")
        expected = str(expected_version or "")
        supplied = supplied_nonce
        record = state.get("nonces", {}).get(supplied) if state else None
        if not state or not nonce:
            raise AppError("UI_SESSION_REQUIRED", "interactive completion requires a valid UI session", 403)
        if not supplied:
            raise AppError("COMPLETION_NONCE_REQUIRED", "completion form nonce is required", 403)
        if (not record or
                record.get("workflow") != workflow_id or record.get("version") != expected or
                record.get("operation") != operation or record.get("expires", 0) < __import__("time").time()):
            raise AppError("COMPLETION_NONCE_INVALID", "completion nonce is invalid, expired, replayed, or mis-bound", 403)
        self._pending_nonce = (str(state.get("db_id", session.value)), supplied, session.value)
        self._pending_auth = {"nonce_id": record.get("record_id", supplied), "nonce_hash": hashlib.sha256(supplied.encode()).hexdigest(), "authorization_expires_at": record.get("expires")}

    def _consume_validated_nonce(self) -> None:
        session_id, nonce, token_id = getattr(self, "_pending_nonce", ("", "", ""))
        state = self._sessions.get(token_id)
        record = state.get("nonces", {}).pop(nonce, None) if state else None
        if record is not None:
            record["used_at"] = __import__("time").time()
            state["nonce"] = secrets.token_urlsafe(24)
            self.set_cookie = True
            with self.app._connect() as db:
                db.execute("UPDATE ui_sessions SET nonce_hash=?, expires_at=? WHERE id=?", (hashlib.sha256(state["nonce"].encode()).hexdigest(), __import__("time").time() + 1800, session_id))
                if db.execute("SELECT changes()").fetchone()[0] != 1: raise AppError("UI_SESSION_REQUIRED", "session record is unavailable", 403)

    def _send(self, status: int, body: str, content_type: str) -> None:
        if content_type.startswith("text/html") and getattr(self, "session_token", "") in self._sessions:
            state = self._sessions[self.session_token]; state.setdefault("nonces", {})
            def inject(match: re.Match[str]) -> str:
                form = match.group(0)
                action = re.search(r"/api/workflows/([^/'\"]+)/completion", form)
                version = re.search(r"name=['\"]expected_version['\"] value=['\"]([^'\"]+)", form)
                completed = re.search(r"name=['\"]completed['\"] value=['\"]([^'\"]+)", form)
                if not action or not version: return form
                operation = "complete" if completed and completed.group(1).lower() in {"1", "true", "yes"} else "cancel"
                nonce = secrets.token_urlsafe(24); record_id = secrets.token_hex(16); state["nonces"][nonce] = {"record_id": record_id, "workflow": action.group(1), "version": version.group(1), "operation": operation, "expires": __import__("time").time() + 300}; state["nonce"] = nonce
                with self.app._connect() as db:
                    db.execute("UPDATE ui_sessions SET nonce_hash=?, expires_at=? WHERE id=?", (hashlib.sha256(nonce.encode()).hexdigest(), __import__("time").time() + 1800, state.get("db_id", self.session_token)))
                    if db.execute("SELECT changes()").fetchone()[0] != 1: raise AppError("UI_SESSION_REQUIRED", "session record is unavailable", 403)
                    wf = db.execute("SELECT context_id,work_package_id FROM workflows WHERE id=?", (action.group(1),)).fetchone()
                    db.execute("INSERT OR REPLACE INTO ui_nonces(id,session_id,workflow_id,expected_version,operation,nonce_hash,expires_at,used_at,issued_at,consume_request_id,context_id,work_package_id) VALUES (?,?,?,?,?,?,?,NULL,?,NULL,?,?)", (record_id, state.get("db_id", self.session_token), action.group(1), version.group(1), operation, hashlib.sha256(nonce.encode()).hexdigest(), state["nonces"][nonce]["expires"], __import__("time").time(), wf[0] if wf else None, wf[1] if wf else None))
                return form.replace("<input type='hidden' name='completed'", f"<input type='hidden' name='completion_nonce' value='{html.escape(nonce, quote=True)}'><input type='hidden' name='completed'", 1)
            body = re.sub(r"<form\b[^>]*action=['\"]/api/workflows/[^'\"]+/completion['\"][^>]*>.*?</form>", inject, body, flags=re.I | re.S)
        data = body.encode("utf-8"); self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(data)))
        if getattr(self, "set_cookie", False):
            self.send_header("Set-Cookie", f"srwb_session={self.session_token}; Path=/; HttpOnly; SameSite=Lax")
            self.send_header("Set-Cookie", f"srwb_completion_nonce={self._sessions[self.session_token]['nonce']}; Path=/; SameSite=Lax")
        self.end_headers(); self.wfile.write(data)

    def _send_bytes(self, status: int, data: bytes, content_type: str, filename: str | None = None) -> None:
        self.send_response(status); self.send_header("Content-Type", content_type); self.send_header("Content-Length", str(len(data)))
        if filename: self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{quote(filename)}")
        self.end_headers(); self.wfile.write(data)

    def _send_inline_pdf_preview(self, attachment_id: str, preview: dict[str, object]) -> None:
        """Send the verified original PDF bytes for the controlled preview route.

        HTML preview wrappers are deliberately limited to text derived from
        Markdown/OOXML.  A PDF must remain a PDF response so the browser can
        render its original bytes inside the Context preview iframe.
        """
        artifact_root = self.app.artifact_root.resolve()
        candidate = (artifact_root / str(preview["relative_path"])).resolve()
        if artifact_root not in candidate.parents or not candidate.is_file():
            self.app.record_attachment_failure(attachment_id, "attachment.preview", "PREVIEW_FAILED", context_id=preview.get("context_id"))
            raise AppError("PREVIEW_FAILED", "attachment file is missing", 422)
        data = candidate.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != preview["size_bytes"] or digest != preview["sha256"]:
            self.app.record_attachment_failure(attachment_id, "attachment.preview", "ATTACHMENT_INTEGRITY", context_id=preview.get("context_id"))
            raise AppError("ATTACHMENT_INTEGRITY", "attachment size or hash mismatch", 409)
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", "inline")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "private, max-age=0, no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _attachment_preview_document(self, attachment_id: str, preview: dict[str, object]) -> str:
        """Build the safe HTML document representation for non-PDF previews."""
        download = f"<p><a href='/api/achievement-attachments/{quote(attachment_id)}'>Download original file</a></p>"
        state = str(preview.get("preview_state", "failed"))
        if state == "available":
            document = str(preview.get("preview") or "(No extractable text in this document.)")
        elif state == "download_only":
            document = "This file type is download-only and cannot be embedded for preview."
        else:
            document = "Preview failed. The original file remains available for download."
        body = (
            f"<section data-representation='document'><h2>Attachment preview: "
            f"{html.escape(str(preview.get('original_name', '')))}</h2><div>{document}{download}</div>"
            f"{preview.get('image_html', '')}</section>"
    )
        original_name = str(preview.get("original_name", ""))
        if state == "available" and original_name.lower().endswith((".md", ".markdown")):
            return (
                "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<title>Markdown preview</title>"
                "<style>body{margin:0;background:#fff;color:#17212b;font:16px/1.7 \"Segoe UI\",\"Microsoft YaHei\",sans-serif}.markdown-preview{box-sizing:border-box;max-width:960px;margin:0 auto;padding:28px;overflow-wrap:anywhere}</style>"
                f"</head><body><main class='markdown-preview' data-representation='markdown'>{document}</main></body></html>"
            )
        return shell("Attachment preview", body)

    def _audit_failed_write(self, path: str, payload: dict[str, object], code: str, detail: str) -> None:
        """Audit a write rejected before the domain transaction can do so."""
        if not path.startswith("/api/"):
            return
        parts = path.strip("/").split("/")
        action, target_type, target_id, context_id = "web.write", "route", path, None
        if path == "/api/upload-settings":
            action, target_type, target_id = "upload-settings.update", "upload_settings", "1"
        elif len(parts) >= 4 and parts[1] == "achievement-cards" and parts[-1] == "update":
            action, target_type, target_id = "card.update", "achievement_card", parts[2]
        elif len(parts) >= 4 and parts[1] == "achievement-cards" and parts[-1] == "delete":
            action, target_type, target_id = "card.delete", "achievement_card", parts[2]
        elif len(parts) >= 4 and parts[1] == "achievement-cards" and parts[-1] == "attachments":
            action, target_type, target_id = "attachment.upload", "achievement_card", parts[2]
        elif len(parts) >= 4 and parts[1] == "achievement-attachments" and parts[-1] == "delete":
            action, target_type, target_id = "attachment.remove", "attachment", parts[2]
        elif len(parts) >= 5 and parts[1] == "contexts" and parts[-1] == "importance":
            action, target_type, target_id, context_id = "card.importance", "achievement_card", parts[4], parts[2]
        elif len(parts) >= 4 and parts[1] == "workflows" and parts[-1] in {"command", "completion"}:
            action, target_type, target_id = f"workflow.{parts[-1]}", "workflow", parts[2]
        try:
            with self.app._connect() as db:
                if target_type == "achievement_card":
                    row = db.execute("SELECT context_id FROM achievement_cards WHERE id=?", (target_id,)).fetchone()
                    context_id = context_id or (row["context_id"] if row else None)
                elif target_type == "attachment":
                    row = db.execute("SELECT c.context_id FROM achievement_attachments a JOIN achievement_cards c ON c.id=a.card_id WHERE a.id=?", (target_id,)).fetchone()
                    context_id = context_id or (row["context_id"] if row else None)
                elif target_type == "workflow":
                    row = db.execute("SELECT context_id FROM workflows WHERE id=?", (target_id,)).fetchone()
                    context_id = context_id or (row["context_id"] if row else None)
                existing = db.execute("SELECT 1 FROM operation_audit_events WHERE action=? AND target_id=? AND result='REJECTED' AND error_code=? ORDER BY occurred_at DESC LIMIT 1", (action, target_id, code)).fetchone()
            if existing:
                return
            self.app.append_operation_audit(context_id=context_id, actor="web-user", display_label="web-user", action=action, target_type=target_type, target_id=target_id, result="REJECTED", error_code=code, summary=json.dumps({"route": path, "detail": detail}, ensure_ascii=False), request_id=self.headers.get("X-Request-ID"))
        except Exception:
            return

    def do_GET(self) -> None:  # noqa: N802
        self._ensure_session()
        path = urlparse(self.path).path
        try:
            if path == "/governance":
                query = parse_qs(urlparse(self.path).query); self._send(200, product_audit_page(self.app, query.get("context_id", [""])[0], query.get("action", [""])[0], query.get("result", [""])[0]), "text/html; charset=utf-8"); return
            if path == "/": self._send(200, page(self.app), "text/html; charset=utf-8")
            elif path == "/work-packages":
                query = parse_qs(urlparse(self.path).query); self._send(200, work_packages_page(self.app, query.get("q", [""])[0], query.get("area", [""])[0]), "text/html; charset=utf-8")
            elif path.startswith("/work-packages/"):
                query = parse_qs(urlparse(self.path).query); self._send(200, work_package_detail(self.app, path.rsplit("/", 1)[1], query.get("notice", [""])[0]), "text/html; charset=utf-8")
            elif path == "/contexts": self._send(200, contexts_page(self.app), "text/html; charset=utf-8")
            elif re.match(r"^/contexts/[^/]+/delete$", path):
                query = parse_qs(urlparse(self.path).query)
                self._send(200, context_deletion_page(self.app, path.split("/")[2], query.get("operation_id", [""])[0], query.get("confirmation", [""])[0], query.get("notice", [""])[0]), "text/html; charset=utf-8")
            elif path.startswith("/contexts/"):
                query = parse_qs(urlparse(self.path).query); self._send(200, context_cards_page(self.app, path.rsplit("/", 1)[1], query.get("notice", [""])[0], query.get("wp", [""])[0], query.get("area", [""])[0], query.get("status", [""])[0], query.get("query", [""])[0], query.get("card", [""])[0], _as_bool(query.get("important", [""])[0]), query.get("directory", ["expanded"])[0], query.get("preview", [""])[0], getattr(self, "session_token", "_local_author_v1"), query.get("preview_rail", [""])[0]), "text/html; charset=utf-8")
            elif path == "/weeks": self._send(200, weeks_page(self.app), "text/html; charset=utf-8")
            elif path.startswith("/weeks/"):
                query = parse_qs(urlparse(self.path).query); self._send(200, week_detail_page(self.app, path.rsplit("/", 1)[1], query.get("notice", [""])[0]), "text/html; charset=utf-8")
            elif path == "/favicon.ico": self.send_response(204); self.send_header("Content-Length", "0"); self.end_headers()
            elif path == "/skills": self._send(200, skills_page(self.app), "text/html; charset=utf-8")
            elif path == "/reports":
                query = parse_qs(urlparse(self.path).query); self._send(200, reports_page(self.app, query.get("week_id", [""])[0], query.get("notice", [""])[0]), "text/html; charset=utf-8")
            elif path == "/governance-audit":
                query = parse_qs(urlparse(self.path).query); self._send(200, product_audit_page(self.app, query.get("context_id", [""])[0], query.get("action", [""])[0], query.get("result", [""])[0]), "text/html; charset=utf-8")
            elif False and path == "/governance":  # retired duplicate; canonical route is handled above
                events = self.app.governance_events(); candidates = self.app.document_candidates(); rows = ''.join(f"<tr><td>{html.escape(x['kind'])}</td><td><code>{html.escape(x['id'])}</code></td><td>{html.escape(x['status'])}</td><td>{html.escape(x['created_at'])}</td></tr>" for x in events); docs = ''.join(f"<tr><td>{html.escape(x['kind'])}</td><td><code>{html.escape(x['id'])}</code></td><td>{html.escape(x['status'])}</td></tr>" for x in candidates)
                audits = self.app.query_operation_audits(limit=200).get("items", [])
                audit_rows = ''.join(f"<tr><td><code>{html.escape(str(x.get('operation_id','')))}</code></td><td>{html.escape(str(x.get('occurred_at','')))}</td><td>{html.escape(str(x.get('actor_display','') or x.get('actor','')))}</td><td>{html.escape(str(x.get('action','')))}</td><td>{html.escape(str(x.get('target_type','')))}:{html.escape(str(x.get('target_id','')))}</td><td>{html.escape(str(x.get('result','')))}</td><td>{html.escape(str(x.get('error_code','') or ''))}</td><td>{html.escape(str(x.get('summary','')))}</td></tr>" for x in audits)
                audit_body = "<h2>产品人工操作审计</h2><p>只读视图，不提供新增、编辑、删除、导入或重建入口。</p><table><tr><th>operation_id</th><th>时间</th><th>操作者</th><th>动作</th><th>目标</th><th>结果</th><th>错误码</th><th>脱敏摘要</th></tr>" + (audit_rows or "<tr><td colspan=8>暂无审计记录</td></tr>") + "</table><details><summary>需求与工程治理（次级视图）</summary><h3>治理事件</h3><table><tr><th>类型</th><th>ID</th><th>状态</th><th>时间</th></tr>" + (rows or '<tr><td colspan=4>暂无事件</td></tr>') + "</table><h3>文档候选</h3><table><tr><th>文档</th><th>ID</th><th>状态</th></tr>" + (docs or '<tr><td colspan=3>暂无候选</td></tr>') + "</table></details>"
                self._send(200, shell("产品人工操作审计", audit_body, active="governance"), "text/html; charset=utf-8")
            elif path == "/operations": self._send(200, operations_page(self.app), "text/html; charset=utf-8")
            elif path == "/settings/uploads":
                self.send_response(308); self.send_header("Location", "/operations"); self.send_header("Content-Length", "0"); self.end_headers()
            elif path == "/api/catalog": self._send(200, json.dumps(self.app.catalog(), ensure_ascii=False), "application/json; charset=utf-8")
            elif path.startswith("/api/work-packages/") and path.endswith("/assets"): self._send(200, json.dumps(self.app.work_package_assets(path.split("/")[3]), ensure_ascii=False), "application/json; charset=utf-8")
            elif path.startswith("/api/contexts/") and path.endswith("/workflows"): self._send(200, json.dumps({"workflows": self.app.workflows_for_context(path.split("/")[3])}, ensure_ascii=False), "application/json; charset=utf-8")
            elif path.startswith("/api/work-packages/") and path.endswith("/assets"): self._send(200, json.dumps(self.app.work_package_assets(path.split("/")[3]), ensure_ascii=False), "application/json; charset=utf-8")
            elif path == "/api/health": self._send(200, json.dumps(self.app.health(), ensure_ascii=False), "application/json; charset=utf-8")
            elif path.startswith("/api/contexts/") and path.endswith("/achievement-cards"):
                parts = path.split("/"); self._send(200, json.dumps({"cards": self.app.achievement_cards(parts[3], parts[5])}, ensure_ascii=False), "application/json; charset=utf-8")
            elif path == "/api/upload-settings": self._send(200, json.dumps(self.app.upload_settings(), ensure_ascii=False), "application/json; charset=utf-8")
            elif path == "/api/model-profile": self._send(200, json.dumps(self.app.model_profile(), ensure_ascii=False), "application/json; charset=utf-8")
            elif path.startswith("/api/achievement-cards/"):
                self._send(200, json.dumps(self.app.achievement_card(path.split("/")[3]), ensure_ascii=False), "application/json; charset=utf-8")
            elif path.startswith("/api/achievement-attachments/") and path.endswith("/preview"):
                attachment_id = path.split("/")[3]
                representation = parse_qs(urlparse(self.path).query).get("representation", ["metadata"])[0]
                if representation not in {"metadata", "document"}:
                    raise AppError("INVALID_PREVIEW_REPRESENTATION", "preview representation must be metadata or document", 422)
                try: preview = self.app.preview_achievement_attachment(attachment_id)
                except AppError as exc:
                    self.app.record_attachment_failure(attachment_id, "attachment.preview", "ATTACHMENT_INTEGRITY" if exc.code == "ATTACHMENT_INTEGRITY" else ("PREVIEW_FAILED" if exc.code == "PREVIEW_FAILED" else exc.code))
                    raise
                if representation == "document" and str(preview.get("original_name", "")).lower().endswith(".pdf"):
                    self._send_inline_pdf_preview(attachment_id, preview)
                elif representation == "document": self._send(200, self._attachment_preview_document(attachment_id, preview), "text/html; charset=utf-8")
                else:
                    preview["representation"] = "metadata"
                    self._send(200, json.dumps(preview, ensure_ascii=False), "application/json; charset=utf-8")
            elif re.match(r"^/achievement-attachments/[^/]+/preview$", path):
                attachment_id = path.split("/")[2]
                self.send_response(308)
                self.send_header("Location", f"/api/achievement-attachments/{quote(attachment_id)}/preview?representation=document")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
                preview = self.app.preview_achievement_attachment(attachment_id)
                if str(preview.get("original_name", "")).lower().endswith(".pdf"):
                    self._send_inline_pdf_preview(attachment_id, preview)
                    return
                aid = quote(path.split("/")[2]); download_link = f"<p><a href='/api/achievement-attachments/{aid}'>下载原文件</a></p>"
                preview["preview"] = ("预览失败" if preview.get("preview_state") == "failed" else (preview.get("preview") or "当前附件不支持内嵌预览。")) + download_link
                body = f"<section><h2>附件预览：{html.escape(str(preview.get('original_name', '')))}</h2><div>{preview.get('preview') or '当前附件不支持内嵌预览。'}</div>{preview.get('image_html', '')}</section>"
                self._send(200, shell("附件预览", body), "text/html; charset=utf-8")
            elif re.match(r"^/api/achievement-attachments/[^/]+/images/\d+$", path):
                attachment_id, image_index = path.split("/")[3], int(path.split("/")[5])
                preview = self.app.preview_achievement_attachment(attachment_id); image = preview.get("images", [])[image_index] if image_index < len(preview.get("images", [])) else None
                if not image: raise AppError("NOT_FOUND", "preview image not found", 404)
                source = (self.app.artifact_root / preview["relative_path"]).resolve()
                with __import__("zipfile").ZipFile(source) as archive: data = archive.read(image["source"])
                if len(data) != image["size"] or __import__("hashlib").sha256(data).hexdigest() != image["sha256"]: raise AppError("ATTACHMENT_INTEGRITY", "preview image integrity mismatch", 409)
                self.send_response(200); self.send_header("Content-Type", image["mime"]); self.send_header("Content-Length", str(len(data))); self.send_header("Content-Disposition", "inline"); self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(data)
            elif path.startswith("/api/achievement-attachments/"):
                with self.app._connect() as db: row = db.execute("SELECT a.*,c.context_id FROM achievement_attachments a JOIN achievement_cards c ON c.id=a.card_id WHERE a.id=?", (path.split("/")[3],)).fetchone()
                if not row:
                    self.app.record_attachment_failure(path.split("/")[3], "attachment.download", "NOT_FOUND")
                    raise AppError("NOT_FOUND", "attachment not found", 404)
                candidate = (self.app.artifact_root / row["relative_path"]).resolve()
                if self.app.artifact_root not in candidate.parents or not candidate.is_file():
                    self.app.record_attachment_failure(path.split("/")[3], "attachment.download", "NOT_FOUND", context_id=row["context_id"] if "context_id" in row.keys() else None)
                    raise AppError("NOT_FOUND", "attachment file not found", 404)
                data = candidate.read_bytes()
                if len(data) != row["size_bytes"] or __import__("hashlib").sha256(data).hexdigest() != row["sha256"]:
                    self.app.record_attachment_failure(path.split("/")[3], "attachment.download", "ATTACHMENT_INTEGRITY", context_id=row["context_id"] if "context_id" in row.keys() else None)
                    raise AppError("ATTACHMENT_INTEGRITY", "attachment size or hash mismatch", 409)
                self._send_bytes(200, data, row["mime_type"] or "application/octet-stream", row["original_name"])
            elif path == "/api/governance": self._send(200, json.dumps({"events": self.app.governance_events()}, ensure_ascii=False), "application/json; charset=utf-8")
            elif path == "/api/operation-audits":
                query = parse_qs(urlparse(self.path).query)
                result = self.app.query_operation_audits(query.get("context_id", [None])[0], query.get("action", [None])[0], query.get("result", [None])[0], int(query.get("limit", [100])[0]))
                self._send(200, json.dumps(result, ensure_ascii=False), "application/json; charset=utf-8")
            elif path == "/api/report-model":
                query = parse_qs(urlparse(self.path).query); self._send(200, json.dumps(self.app.report_model(query.get("week_id", [""])[0]), ensure_ascii=False), "application/json; charset=utf-8")
            elif path == "/api/confirmed-report":
                query = parse_qs(urlparse(self.path).query); self._send(200, json.dumps(self.app.confirmed_report(query.get("week_id", [""])[0]), ensure_ascii=False), "application/json; charset=utf-8")
            else: self._send(404, json.dumps({"code":"NOT_FOUND"}), "application/json")
        except AppError as exc: self._send(exc.status, json.dumps({"code": exc.code, "detail": exc.message}, ensure_ascii=False), "application/problem+json")

    def do_POST(self) -> None:  # noqa: N802
        multipart_staging_dir: Path | None = None
        try:
            session_valid = self._ensure_session()
            length = int(self.headers.get("Content-Length", "0"))
            if self.headers.get("Content-Type", "").startswith("multipart/form-data") and length > self.app.upload_settings()["max_file_bytes"] + 2_000_000:
                self._send(413, json.dumps({"code":"FILE_TOO_LARGE","detail":"multipart request exceeds configured upload limit"}), "application/problem+json"); return
            content_type = self.headers.get("Content-Type", "")
            if content_type.startswith("multipart/form-data"):
                try:
                    # Request staging must not inherit the user-selected data root:
                    # deep Windows workspaces can make that path exceed legacy limits.
                    multipart_staging_dir = Path(tempfile.mkdtemp(prefix="srwb-http-", dir=tempfile.gettempdir()))
                    with tempfile.NamedTemporaryFile(dir=multipart_staging_dir, prefix="request-", suffix=".part", delete=False) as stream:
                        remaining = length
                        while remaining:
                            chunk = self.rfile.read(min(64 * 1024, remaining))
                            if not chunk: raise AppError("UPLOAD_INCOMPLETE", "multipart request ended early", 400)
                            stream.write(chunk); remaining -= len(chunk)
                        request_path = stream.name
                except OSError as exc:
                    raise AppError("UPLOAD_STAGING_FAILED", "multipart temporary storage is unavailable", 503) from exc
                raw = None
            else:
                raw = self.rfile.read(length)
            if "application/json" in content_type:
                payload = json.loads(raw or b"{}")
            elif content_type.startswith("multipart/form-data"):
                with open(request_path, "rb") as request_stream:
                    form = cgi.FieldStorage(fp=request_stream, headers=self.headers, environ={"REQUEST_METHOD":"POST", "CONTENT_TYPE":content_type, "CONTENT_LENGTH":str(length)})
                payload = {}
                for key in form.keys():
                    field = form[key]
                    field = field[0] if isinstance(field, list) else field
                    if getattr(field, "filename", None):
                        filename = field.filename
                        disposition = field.headers.get("content-disposition", "")
                        extended_name = re.search(r"(?:^|;)\s*filename\*=UTF-8''([^;\s]+)", disposition, flags=re.I)
                        if extended_name:
                            filename = unquote(extended_name.group(1), encoding="utf-8", errors="strict")
                        staged_field = Path(request_path + "." + key)
                        with staged_field.open("wb") as output:
                            while True:
                                chunk = field.file.read(64 * 1024)
                                if not chunk: break
                                output.write(chunk)
                        payload[key] = staged_field; payload[key + "_name"] = filename
                    else: payload[key] = field.value
                Path(request_path).unlink(missing_ok=True)
            else:
                payload = {k: v[-1] for k, v in parse_qs(raw.decode("utf-8")).items()}
            path = urlparse(self.path).path
            if path.startswith("/api/workflows/") and path.endswith("/completion") and not session_valid:
                raise AppError("UI_SESSION_REQUIRED", "completion requires a valid browser session", 403)
            if path.startswith("/api/workflows/") and path.endswith("/completion"):
                operation = "complete" if _as_bool(payload.get("completed", False)) else "cancel"
                self._consume_completion_nonce(path.split("/")[3], payload.get("expected_version"), operation, str(payload.get("completion_nonce", "")))
            if re.match(r"^/api/contexts/[^/]+/deletion/prepare$", path):
                if not session_valid:
                    raise AppError("UI_SESSION_REQUIRED", "context deletion requires a valid browser session", 403)
                if "retain_files" not in payload:
                    raise AppError("DELETE_BRANCH_REQUIRED", "choose whether to retain files", 422)
                expected_version = payload.get("expected_version")
                result = self.app.prepare_context_deletion(path.split("/")[3], _as_bool(payload["retain_files"]), str(self._sessions[getattr(self, "session_token", "")]["db_id"]), int(expected_version) if str(expected_version).isdigit() else None, "web-user")
            elif re.match(r"^/api/contexts/[^/]+/deletion/commit$", path):
                if not session_valid:
                    raise AppError("UI_SESSION_REQUIRED", "context deletion requires a valid browser session", 403)
                result = self.app.commit_context_deletion(payload.get("operation_id", ""), payload.get("confirmation", ""), str(self._sessions[getattr(self, "session_token", "")]["db_id"]), "web-user")
            elif path == "/api/contexts": result = self.app.create_context(payload.get("type", "topic"), payload.get("name", ""), payload.get("problem", ""), payload.get("goal", ""), payload.get("owner", "author"))
            elif path == "/api/weeks": result = self.app.create_week(payload.get("week_start", ""))
            elif path == "/api/workflows": result = self.app.start_workflow(payload.get("context_id", ""), payload.get("wp_id", ""))
            elif path.startswith("/api/workflows/") and path.endswith("/command"):
                expected_version = payload.get("expected_version")
                if isinstance(expected_version, str) and expected_version.strip().isdigit(): expected_version = int(expected_version.strip())
                result = self.app.apply_workflow_command(path.split("/")[3], payload.get("command", ""), expected_version, payload.get("actor", "author"), payload.get("mode"), payload.get("reason", ""))
            elif path.startswith("/api/contexts/") and "/areas/" in path and path.endswith("/preference"):
                parts = path.split("/"); result = self.app.set_context_area_preference(parts[3], parts[5], _as_bool(payload.get("is_expanded", False)), getattr(self, "session_token", "_local_author_v1"))
            elif re.match(r"^/api/contexts/[^/]+/disclosure$", path):
                expected = payload.get("expected_version", "0")
                if not str(expected).isdigit():
                    raise AppError("INVALID_INPUT", "expected disclosure version is invalid", 422)
                result = self.app.set_context_disclosure_preference(
                    path.split("/")[3],
                    str(payload.get("disclosure_kind", "")),
                    str(payload.get("stable_subject_id", "")),
                    _as_bool(payload.get("requested_is_expanded", False)),
                    getattr(self, "session_token", "_local_author_v1"),
                    int(expected),
                )
            elif path.startswith("/api/contexts/") and path.endswith("/workflows"): result = {"workflows": self.app.workflows_for_context(path.split("/")[3])}
            elif path.startswith("/api/contexts/") and path.endswith("/selection"): result = self.app.set_workflow_selection(path.split("/")[3], payload.get("wp_id", ""), payload.get("selection_status", ""), payload.get("reason"), bool(payload.get("author_confirmed", False)))
            elif path.startswith("/api/workflows/") and path.endswith("/completion"):
                auth = getattr(self, "_pending_auth", {})
                session_state = self._sessions.get(getattr(self, "session_token", ""), {})
                result = self.app.set_workflow_completion(path.split("/")[3], _as_bool(payload.get("completed", False)), "web-user", int(payload["expected_version"]) if payload.get("expected_version") else None, idempotency_key=payload.get("idempotency_key"), authorization_source="ui_session", nonce_id=auth.get("nonce_id"), nonce_hash=auth.get("nonce_hash"), authorization_expires_at=auth.get("authorization_expires_at"), session_id=session_state.get("db_id", getattr(self, "session_token", None)))
            elif path == "/api/achievement-cards": result = self.app.create_achievement_card(payload.get("context_id", ""), payload.get("workflow_id", ""), payload.get("event_date", ""), payload.get("event_name", ""), payload.get("description", ""), payload.get("actor", "author"), payload.get("week_item_id"), _as_bool(payload.get("important", False)))
            elif path.startswith("/api/contexts/") and path.endswith("/importance"):
                parts = path.split("/"); result = self.app.set_achievement_card_importance(parts[3], parts[5], parts[7], _as_bool(payload.get("is_important", False)), int(payload.get("expected_version", 0)))
            elif path.startswith("/api/achievement-cards/") and path.endswith("/attachments"):
                uploaded = payload.get("file", b"")
                result = self.app.add_achievement_attachment(path.split("/")[3], payload.get("file_name", payload.get("file_name_name", "")), uploaded if isinstance(uploaded, (bytes, Path)) else base64.b64decode(uploaded), payload.get("mime_type", "application/octet-stream"))
            elif path.startswith("/api/achievement-attachments/") and path.endswith("/delete"): result = self.app.remove_achievement_attachment(path.split("/")[3])
            elif path.startswith("/api/achievement-cards/") and path.endswith("/delete"): result = self.app.delete_achievement_card(path.split("/")[3], payload.get("actor", "author"), payload.get("confirmation_token"), int(payload["expected_version"]) if payload.get("expected_version") else None)
            elif path.startswith("/api/achievement-cards/") and path.endswith("/update"): result = self.app.update_achievement_card(path.split("/")[3], payload.get("event_date", ""), payload.get("event_name", ""), payload.get("description", ""), int(payload["expected_version"]) if payload.get("expected_version") else None, payload.get("actor", "author"))
            elif path == "/api/upload-settings": result = self.app.update_upload_settings(int(payload.get("max_file_bytes", 100000000)), int(payload.get("max_attachments_per_card", 20)), payload.get("allowed_extensions", []), int(payload["expected_version"]) if payload.get("expected_version") else None)
            elif path == "/api/operations/business-root": result = self.app.update_business_data_location(str(payload.get("business_root", "")))
            elif path == "/api/operations/directory-picker": result = self.app.select_business_directory()
            elif path == "/api/model-profile": result = self.app.update_model_profile(str(payload.get("endpoint", "")), str(payload.get("model", "")), int(payload.get("timeout_seconds", 60)), str(payload["api_key"]) if payload.get("api_key") else None, int(payload["expected_version"]) if payload.get("expected_version") else None)
            elif path == "/api/model-profile/test": result = self.app.test_model_profile(int(payload["expected_version"]) if payload.get("expected_version") else None)
            elif path == "/api/model-prompt": result = self.app.run_model_prompt(str(payload.get("prompt", "")))
            elif path == "/api/artifacts/template": result = self.app.create_template_artifact(payload.get("wp_id", ""), payload.get("template_id", ""), json.loads(payload.get("values", "{}")), item_id=payload.get("item_id"), context_id=payload.get("context_id"), workflow_id=payload.get("workflow_id"), run_id=payload.get("run_id"), step_no=payload.get("step_no"))
            elif path == "/api/artifacts/associate": result = self.app.create_template_artifact(payload.get("wp_id", ""), payload.get("template_id", ""), None, payload.get("artifact_ref", ""))
            elif path == "/api/skills/manual": result = self.app.run_manual_skill(payload.get("wp_id", ""), payload.get("context_id"), payload.get("workflow_id"), payload.get("inputs", {}), payload.get("idempotency_key"), payload.get("item_id"))
            elif path.startswith("/api/manual-skills/") and path.endswith("/advance"): result = self.app.advance_manual_skill(path.split("/")[3], int(payload.get("step_no", 0)), payload.get("state", "Completed"), payload.get("artifact_id"), payload.get("detail", ""))
            elif path.startswith("/api/manual-skills/") and path.endswith("/control"): result = self.app.control_manual_skill(path.split("/")[3], payload.get("command", ""))
            elif path == "/api/week-items": result = self.app.add_week_item(payload.get("week_id", ""), payload.get("wp_id", ""), payload.get("title", ""), payload.get("deliverable", ""), payload.get("relation"))
            elif path.startswith("/api/week-items/") and path.endswith("/execute"): result = self.app.record_execution(path.split("/")[3], payload.get("action", ""), payload.get("inputs", ""), payload.get("result", ""), payload.get("output", "")) or {"status": "recorded"}
            elif path.startswith("/api/week-items/") and path.endswith("/evidence"): result = self.app.add_evidence(path.split("/")[3], payload.get("name", ""), payload.get("kind", "file"), payload.get("path", ""), payload.get("source", "author"), payload.get("stage", ""), _as_bool(payload.get("author_confirmed", False)), _as_bool(payload.get("strict", True)))
            elif path.startswith("/api/evidence/") and path.endswith("/confirm"): result = self.app.confirm_evidence(path.split("/")[3], payload.get("author", "author"))
            elif path.startswith("/api/evidence/") and path.endswith("/revalidate"): result = self.app.revalidate_evidence(path.split("/")[3])
            elif path == "/api/reports/model": result = self.app.report_model(payload.get("week_id", ""))
            elif path == "/api/reports/confirm": result = self.app.confirm_report(payload.get("week_id", ""), payload.get("conclusion", ""), payload.get("image_path"), payload.get("author", "author"))
            elif path.startswith("/api/week-items/") and path.endswith("/gates"): self.app.set_gate(path.split("/")[3], payload.get("key", ""), _as_bool(payload.get("passed", False))); result = {"status": "recorded"}
            elif path.startswith("/api/week-items/") and path.endswith("/complete"): result = self.app.complete_item(path.split("/")[3])
            elif path == "/api/skills": result = self.app.register_skill(json.loads(payload.get("manifest", "{}")) if "application/json" not in content_type else payload)
            elif path == "/api/skill-runs": result = self.app.plan_skill(payload.get("skill_id", ""), payload.get("inputs", {}), payload.get("idempotency_key", ""))
            elif path.startswith("/api/skill-runs/") and path.endswith("/approve"): result = self.app.approve_skill_run(path.split("/")[3], payload.get("capabilities", []))
            elif path.startswith("/api/skill-runs/") and path.endswith("/execute"): result = self.app.execute_skill(path.split("/")[3], float(payload.get("timeout", 600)))
            elif path.startswith("/api/skill-runs/") and path.endswith("/cancel"): result = self.app.cancel_skill_run(path.split("/")[3])
            elif path.startswith("/api/week-items/") and path.endswith("/recommend"): result = {"recommendations": self.app.recommend(path.split("/")[3])}
            elif path.startswith("/api/recommendations/") and path.endswith("/decide"): result = self.app.decide_recommendation(path.split("/")[3], payload.get("decision", ""))
            elif path.startswith("/api/weeks/") and path.endswith("/card"): result = self.app.render_card(path.split("/")[3])
            elif path == "/api/demands": result = self.app.submit_demand(payload.get("text", ""), payload.get("source", "author"))
            elif path == "/api/engineering-events": result = self.app.submit_engineering_event(payload.get("text", ""), payload.get("files", ""))
            elif path.startswith("/api/doc-updates/") and path.endswith("/advance"): result = self.app.advance_doc_update(path.split("/")[3])
            elif path == "/api/documents/freeze": result = self.app.freeze_srs_candidate(payload.get("candidate_id", ""))
            elif path == "/api/documents/architecture": result = self.app.propose_architecture_candidates(payload.get("demand_id", ""), payload.get("srs_candidate_id", ""))
            elif path == "/api/documents/validate": result = self.app.validate_document_candidates(payload.get("demand_id", ""))
            elif path == "/api/documents/approve": result = self.app.approve_document_candidates(payload.get("demand_id", ""), payload.get("author", "author"))
            elif path == "/api/documents/apply": result = self.app.apply_document_candidates(payload.get("demand_id", ""), payload.get("documents", {}), payload.get("author", "author"))
            elif path == "/api/reports/pptx": result = {"path": str(self.app.render_pptx(payload.get("week_id", ""), self.app.db_path.parent.parent / "exports" / f"{payload.get('week_id', 'report')}.pptx"))}
            elif path == "/api/skill-discovery": result = self.app.discover_skill_metadata(payload.get("url", ""), payload.get("allowlist", []), bool(payload.get("enabled", False)))
            elif path == "/api/backup": result = {"path": str(self.app.backup(Path(payload.get("target", "backups/manual.json"))))}
            else: self._send(404, json.dumps({"code": "NOT_FOUND", "detail": "endpoint not found"}), "application/problem+json"); return
            self._consume_validated_nonce()
            if "application/json" not in content_type and path.startswith("/api/"):
                redirect = "/"
                if re.match(r"^/api/contexts/[^/]+/deletion/prepare$", path):
                    context_id = path.split("/")[3]
                    redirect = f"/contexts/{quote(context_id)}/delete?operation_id={quote(str(result['operation_id']))}&confirmation={quote(str(result['confirmation']))}"
                elif re.match(r"^/api/contexts/[^/]+/deletion/commit$", path):
                    redirect = "/contexts?notice=" + quote("课题已按确认分支删除")
                elif path == "/api/contexts": redirect = "/contexts"
                elif path.startswith("/api/contexts/") and "/areas/" in path and path.endswith("/preference"):
                    redirect = f"/contexts/{quote(path.split('/')[3])}"
                elif re.match(r"^/api/contexts/[^/]+/disclosure$", path):
                    context_id = path.split("/")[3]
                    raw_query = str(payload.get("return_query", "")).lstrip("?")
                    allowed_query = {"wp", "area", "status", "query", "important", "card", "directory", "preview", "preview_rail"}
                    query_pairs = [
                        f"{quote(key)}={quote(value)}"
                        for key, values in parse_qs(raw_query, keep_blank_values=False).items()
                        if key in allowed_query
                        for value in values[-1:]
                    ]
                    # This is an internal relative query contract, not an
                    # arbitrary redirect target.  It preserves filter and
                    # preview selection while the database remains the sole
                    # source of disclosure state.
                    redirect = f"/contexts/{quote(context_id)}" + (f"?{'&'.join(query_pairs)}" if query_pairs else "")
                elif path.startswith("/api/contexts/") and path.endswith("/importance"):
                    parts = path.split("/")
                    redirect = f"/contexts/{quote(parts[3])}?wp=" + quote(str(payload.get("wp") or ""))
                    if payload.get("important"):
                        redirect += "&important=true"
                elif path == "/api/weeks" or path == "/api/week-items": redirect = "/weeks"
                elif path.startswith("/api/workflows/") and path.endswith("/command"):
                    with self.app._connect() as db: row = db.execute("SELECT context_id FROM workflows WHERE id=?", (path.split("/")[3],)).fetchone()
                    redirect = f"/contexts/{row['context_id']}" if row else "/contexts"
                elif "/week-items/" in path:
                    with self.app._connect() as db: row = db.execute("SELECT week_id FROM week_items WHERE id=?", (path.split("/")[3],)).fetchone()
                    redirect = f"/weeks/{row['week_id']}" if row else "/weeks"
                elif path.startswith("/api/evidence/"):
                    with self.app._connect() as db: row = db.execute("SELECT week_id FROM week_items WHERE id=(SELECT item_id FROM evidence WHERE id=?)", (path.split("/")[3],)).fetchone()
                    redirect = f"/weeks/{row['week_id']}" if row else "/weeks"
                elif path == "/api/achievement-cards": redirect = f"/contexts/{quote(payload.get('context_id', ''))}" + ("?wp=" + quote(str(payload.get("wp"))) if payload.get("wp") else "")
                elif path in {"/api/upload-settings", "/api/operations/business-root", "/api/model-profile", "/api/model-profile/test", "/api/model-prompt"}: redirect = "/operations"
                elif path.startswith("/api/achievement-attachments/") and path.endswith("/delete"):
                    with self.app._connect() as db:
                        row = db.execute("SELECT c.context_id,c.id FROM achievement_attachments a JOIN achievement_cards c ON c.id=a.card_id WHERE a.id=?", (path.split("/")[3],)).fetchone()
                    if row or payload.get("context_id"):
                        redirect = f"/contexts/{quote(str(row['context_id'] if row else payload.get('context_id')))}?wp={quote(payload.get('wp',''))}&card={quote(payload.get('card',''))}"
                        if payload.get("important"): redirect += "&important=true"
                        redirect += "&directory=" + quote(payload.get("directory", "expanded"))
                elif path.startswith("/api/achievement-cards/"):
                    with self.app._connect() as db:
                        row = db.execute("SELECT context_id FROM achievement_cards WHERE id=?", (path.split("/")[3],)).fetchone()
                    redirect = (f"/contexts/{row['context_id']}" if row else "/contexts") + ("?wp=" + quote(str(payload.get("wp"))) if row and payload.get("wp") else "")
                    if row and payload.get("card"):
                        redirect += ("&" if "?" in redirect else "?") + "card=" + quote(str(payload["card"]))
                elif path.startswith("/api/workflows/") and path.endswith("/completion"):
                    with self.app._connect() as db:
                        row = db.execute("SELECT context_id FROM workflows WHERE id=?", (path.split("/")[3],)).fetchone()
                    redirect = (f"/contexts/{row['context_id']}" if row else "/contexts") + ("?wp=" + quote(str(payload.get("return_wp"))) if row and payload.get("return_wp") else "")
                elif path.startswith("/api/recommendations/") and path.endswith("/decide"):
                    with self.app._connect() as db:
                        row = db.execute("SELECT w.id AS week_id FROM recommendations r JOIN week_items i ON i.id=r.item_id JOIN weeks w ON w.id=i.week_id WHERE r.id=?", (path.split("/")[3],)).fetchone()
                    if not row: raise AppError("NOT_FOUND", "recommendation not found", 404)
                    redirect = f"/weeks/{row['week_id']}"
                elif path == "/api/skills": redirect = "/skills"
                elif path == "/api/skills/manual": redirect = f"/work-packages/{quote(payload.get('wp_id', ''))}?notice=" + quote(f"人工 Skill 已创建：{result.get('id', '')}")
                elif path == "/api/reports/confirm": redirect = f"/reports?week_id={quote(payload.get('week_id', ''))}&notice=" + quote("报告已由作者确认，快照已冻结")
                elif path == "/api/reports/pptx": redirect = f"/reports?week_id={quote(payload.get('week_id', ''))}&notice=" + quote(f"PPTX 已生成：{result.get('path', '')}")
                if "notice=" not in redirect and isinstance(result, dict):
                    notice = result.get("status") or result.get("state") or "操作已完成"
                    redirect += ("&" if "?" in redirect else "?") + "notice=" + quote(str(notice))
                self.send_response(303)
                self.send_header("Location", redirect)
                self.send_header("Content-Length", "0")
                self.end_headers()
                if request_file := locals().get("request_path"):
                    for staged_file in Path(request_file).parent.glob(Path(request_file).name + ".*"):
                        staged_file.unlink(missing_ok=True)
                return
            self._send(201, json.dumps(result, ensure_ascii=False), "application/json; charset=utf-8")
            if request_file := locals().get("request_path"):
                for staged_file in Path(request_file).parent.glob(Path(request_file).name + ".*"):
                    staged_file.unlink(missing_ok=True)
        except (AppError, ValueError, json.JSONDecodeError) as exc:
            path = locals().get("path", urlparse(self.path).path)
            request_file = locals().get("request_path")
            if request_file:
                Path(request_file).unlink(missing_ok=True)
                for staged_file in Path(request_file).parent.glob(Path(request_file).name + ".*"):
                    staged_file.unlink(missing_ok=True)
            if isinstance(exc, AppError): status, code, detail = exc.status, exc.code, exc.message
            else: status, code, detail = 400, "INVALID_INPUT", str(exc)
            self._audit_failed_write(locals().get("path", ""), locals().get("payload", {}), code, detail)
            if "application/json" not in locals().get("content_type", "") and path.startswith("/api/"):
                self._send(status, shell("操作失败", f"<p class='badge' role='alert'>{html.escape(code)}：{html.escape(detail)}</p><p><button type='button' onclick='history.back()'>返回并保留输入</button> · <a href='/'>返回工作台</a></p>"), "text/html; charset=utf-8")
            else:
                self._send(status, json.dumps({"code": code, "detail": detail}, ensure_ascii=False), "application/problem+json")
        finally:
            if multipart_staging_dir is not None:
                try:
                    shutil.rmtree(multipart_staging_dir)
                except OSError:
                    # The request has already received its result; do not turn a
                    # cleanup failure into a broken HTTP connection.
                    pass

    def log_message(self, format: str, *args: object) -> None: return


def serve(data_dir: Path, host: str = "127.0.0.1", port: int = 8765) -> None:
    app = create_workbench(data_dir)
    Handler.app = app
    with ThreadingHTTPServer((host, port), Handler) as server: server.serve_forever()


