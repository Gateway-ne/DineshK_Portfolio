#!/usr/bin/env python3
"""
sync.py - Single-Command Synchronizer for Dinesh K's Portfolio & Resume

Reads: data.json
Updates: index.html & resume.html

Usage:
    python sync.py
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"
INDEX_FILE = BASE_DIR / "index.html"
RESUME_FILE = BASE_DIR / "resume.html"

def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Cannot find {DATA_FILE}")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_experience_years(data) -> str:
    start_str = data.get("personal", {}).get("experienceStartDate", "2024-02-15")
    try:
        start = datetime.strptime(start_str, "%Y-%m-%d")
        now = datetime.now()
        months = (now.year - start.year) * 12 + (now.month - start.month)
        if now.day < start.day:
            months -= 1
        months = max(0, months)
        years = months // 12
        rem_months = months % 12
        return f"{years}.{rem_months}"
    except Exception:
        return "2.9"

def replace_block(content: str, tag: str, replacement: str) -> str:
    """Replaces content between <!-- SYNC:TAG_START --> and <!-- SYNC:TAG_END -->."""
    start_tag = f"<!-- SYNC:{tag}_START -->"
    end_tag = f"<!-- SYNC:{tag}_END -->"
    pattern = re.compile(f"{re.escape(start_tag)}.*?{re.escape(end_tag)}", re.DOTALL)
    
    if pattern.search(content):
        return pattern.sub(f"{start_tag}\n{replacement}\n{end_tag}", content)
    else:
        # If tag doesn't exist yet, warn and return untouched
        print(f"  [WARN] Marker <!-- SYNC:{tag}_START --> not found in file.")
        return content

# ==============================================================================
# HTML Generators for index.html (Portfolio UI)
# ==============================================================================

def generate_portfolio_metrics(data) -> str:
    exp_str = get_experience_years(data)
    projects_count = f"{len(data['projects'])}+"
    certs_count = f"{len(data['certifications'])}+"
    return f"""          <div class="metric-card glass-card">
            <div class="metric-num exp-years-dynamic">{exp_str}</div>
            <div class="metric-label">Years Experience</div>
          </div>
          <div class="metric-card glass-card">
            <div class="metric-num">{projects_count}</div>
            <div class="metric-label">Projects Completed</div>
          </div>
          <div class="metric-card glass-card">
            <div class="metric-num">{certs_count}</div>
            <div class="metric-label">Core Certifications</div>
          </div>
          <div class="metric-card glass-card">
            <div class="metric-num">1</div>
            <div class="metric-label">Enterprise Client</div>
          </div>"""

def generate_portfolio_skills(data) -> str:
    skills = data["skills"]
    panes = []
    
    mapping = [
        ("core-tc", "coreTC", "Core TC"),
        ("integration", "integration", "Integration"),
        ("programming", "programming", "Programming"),
        ("tools", "tools", "Tools"),
        ("documentation", "documentation", "Documentation"),
    ]
    
    for idx, (pane_id, key, title) in enumerate(mapping):
        items = skills.get(key, [])
        active_cls = " active" if idx == 0 else ""
        chips = []
        for item in items:
            chips.append(f"""            <div class="skill-chip glass-card">
              <div class="skill-icon">{item.get('icon', 'TC')}</div>
              <span class="skill-name">{item.get('name', '')}</span>
            </div>""")
        chips_html = "\n".join(chips)
        panes.append(f"""          <!-- Pane: {title} -->
          <div class="skills-pane{active_cls}" id="{pane_id}">
{chips_html}
          </div>""")
        
    return "\n\n".join(panes)

def generate_portfolio_timeline(data) -> str:
    projects = data.get("projects", [])
    items = []
    for idx, p in enumerate(projects, 1):
        cats = " ".join(p.get("categories", []))
        bullets = "\n".join([f"                <li>{b}</li>" for b in p.get("bullets", [])])
        tags = "\n".join([f'              <span class="tech-tag">{t}</span>' for t in p.get("techTags", [])])
        
        items.append(f"""        <!-- Project {idx}: {p.get('name')} -->
        <div class="timeline-item" data-categories="{cats}">
          <div class="timeline-dot"></div>
          <div class="timeline-card glass-card">
            <div class="timeline-header">
              <h3>{p.get('name')}</h3>
              <div class="timeline-meta">
                <span>
                  <svg class="timeline-meta-icon" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                  {p.get('period')}
                </span>
                <span>• {p.get('teamRole', 'Team Member')}</span>
              </div>
              <span class="timeline-role">{p.get('role', 'Teamcenter Developer')}</span>
            </div>
            <div class="timeline-body">
              <ul>
{bullets}
              </ul>
            </div>
            <div class="timeline-tech">
{tags}
            </div>
          </div>
        </div>""")
        
    return "\n\n".join(items)

def generate_portfolio_personal_projects(data) -> str:
    p_projects = data.get("personalProjects", [])
    cards = []
    for p in p_projects:
        tags = "\n".join([f'              <span class="tech-tag">{t}</span>' for t in p.get("tech", [])])
        is_live = p.get("status") == "Live"
        badge_style = "background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);" if is_live else "background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3);"
        
        cards.append(f"""        <!-- Project: {p.get('title')} -->
        <div class="glass-card" style="display: flex; flex-direction: column; justify-content: space-between; padding: 1.75rem;">
          <div>
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; gap: 0.5rem;">
              <h3 style="font-size: 1.2rem; font-weight: 700; color: var(--text-primary);">{p.get('title')}</h3>
              <span style="{badge_style} font-size: 0.75rem; font-weight: 600; padding: 0.2rem 0.6rem; border-radius: 9999px; white-space: nowrap;">{p.get('status')}</span>
            </div>
            <p style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6; margin-bottom: 1.25rem;">
              {p.get('description')}
            </p>
          </div>
          <div>
            <div style="display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1.25rem;">
{tags}
            </div>
            <a href="{p.get('url')}" target="_blank" rel="noopener" class="btn btn-secondary" style="width: 100%; text-align: center; justify-content: center; gap: 0.5rem;">
              <span>{p.get('buttonText', 'Visit Live Web App')}</span>
              <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
            </a>
          </div>
        </div>""")
        
    return "\n\n".join(cards)

# ==============================================================================
# HTML Generators for resume.html (Visual Resume & PDF)
# ==============================================================================

def generate_resume_header(data) -> str:
    p = data["personal"]
    exp_str = get_experience_years(data)
    return f"""        <div class="banner-name">{p.get('name').upper()}</div>
        <div class="banner-title">
          {p.get('title')} — <span class="exp-years-dynamic">{exp_str}</span> Years Experience
        </div>
        <div class="banner-contact">
          <a href="mailto:{p.get('email')}">{p.get('email')}</a> | {p.get('phone')} | <a href="{p.get('linkedin')}" target="_blank" rel="noopener">{p.get('linkedinDisplay')}</a><br>
          <a href="{p.get('portfolioUrl')}" target="_blank" rel="noopener">{p.get('portfolioDisplay')}</a> | {p.get('location')}
        </div>"""

def generate_resume_summary(data) -> str:
    exp_str = get_experience_years(data)
    summary_text = data["summary"]["short"].replace("{expYears}", f'<span class="exp-years-dynamic">{exp_str}</span> years')
    return f"""      <p class="section-p">
        {summary_text}
      </p>"""

def generate_resume_skills(data) -> str:
    skills = data["skills"]
    def join_skills(cat_key):
        items = skills.get(cat_key, [])
        return ", ".join([item.get("name") for item in items])

    return f"""      <div class="skills-grid">
        <div class="skills-label">Core TC</div>
        <div class="skills-value">{join_skills('coreTC')}</div>

        <div class="skills-label">Integration</div>
        <div class="skills-value">{join_skills('integration')}</div>

        <div class="skills-label">Programming</div>
        <div class="skills-value">{join_skills('programming')}</div>

        <div class="skills-label">Tools</div>
        <div class="skills-value">{join_skills('tools')}</div>

        <div class="skills-label">Documentation</div>
        <div class="skills-value">{join_skills('documentation').replace(', ', ' | ')}</div>
      </div>"""

def generate_resume_experience(data) -> str:
    exp = data["experience"]
    bullets = "\n".join([f"        <li>{b}</li>" for b in exp.get("bullets", [])])
    return f"""      <div class="company-title">{exp.get('role')} — {exp.get('company')}</div>
      <div class="role-timeline">{exp.get('timeline')}</div>
      <ul class="bullet-list">
{bullets}
      </ul>"""

def generate_resume_projects(data, page_num: int) -> str:
    projects = [p for p in data.get("projects", []) if p.get("page", 1) == page_num]
    blocks = []
    
    # Calculate starting project index based on page
    if page_num == 1:
        start_idx = 1
    else:
        p1_count = len([p for p in data.get("projects", []) if p.get("page", 1) == 1])
        start_idx = p1_count + 1
        
    for idx_offset, p in enumerate(projects):
        cur_idx = start_idx + idx_offset
        bullets = "\n".join([f"          <li>{b}</li>" for b in p.get("bullets", [])])
        tech_line = p.get("techResume", ", ".join(p.get("techTags", [])))
        
        blocks.append(f"""      <!-- Project {cur_idx} -->
      <div class="project-block">
        <div class="project-header-line">
          <span class="project-name">{p.get('name')}</span> | <span class="project-meta-info">{p.get('period')} | {p.get('role')} | {p.get('teamRole', 'Team Member')}</span>
        </div>
        <div class="project-tech-line">Tech: {tech_line}</div>
        <ul class="bullet-list">
{bullets}
        </ul>
      </div>""")
        
    return "\n\n".join(blocks)

def generate_resume_personal_projects(data) -> str:
    p_projects = data.get("personalProjects", [])
    items = []
    for p in p_projects:
        items.append(f"""        <li style="margin-bottom: 8px;">
          <strong>{p.get('title')}</strong> (<a href="{p.get('url')}" target="_blank" rel="noopener">{p.get('url')}</a>) — {p.get('description')}<br>
          <span style="color: #4b5563; font-size: 11px;">Project Status: {p.get('status')} (<a href="{p.get('url')}" target="_blank" rel="noopener">{p.get('url')}</a>)</span>
        </li>""")
    items_html = "\n".join(items)
    return f"""      <ul class="bullet-list">
{items_html}
      </ul>"""

# ==============================================================================
# Main Synchronizer
# ==============================================================================

def sync():
    print("[SYNC] Reading data.json...")
    data = load_data()
    
    # 1. Update index.html
    if INDEX_FILE.exists():
        print(f"[SYNC] Updating {INDEX_FILE.name}...")
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            idx_content = f.read()
            
        exp_str = get_experience_years(data)
        idx_content = re.sub(r'<span class="exp-years-dynamic">[^<]*</span>', f'<span class="exp-years-dynamic">{exp_str}</span>', idx_content)
        idx_content = replace_block(idx_content, "PORTFOLIO_METRICS", generate_portfolio_metrics(data))
        idx_content = replace_block(idx_content, "PORTFOLIO_SKILLS", generate_portfolio_skills(data))
        idx_content = replace_block(idx_content, "PORTFOLIO_TIMELINE", generate_portfolio_timeline(data))
        idx_content = replace_block(idx_content, "PORTFOLIO_PERSONAL_PROJECTS", generate_portfolio_personal_projects(data))
        
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            f.write(idx_content)
        print(f"  [OK] {INDEX_FILE.name} synchronized.")
        
    # 2. Update resume.html
    if RESUME_FILE.exists():
        print(f"[SYNC] Updating {RESUME_FILE.name}...")
        with open(RESUME_FILE, "r", encoding="utf-8") as f:
            res_content = f.read()
            
        res_content = replace_block(res_content, "RESUME_HEADER", generate_resume_header(data))
        res_content = replace_block(res_content, "RESUME_SUMMARY", generate_resume_summary(data))
        res_content = replace_block(res_content, "RESUME_SKILLS", generate_resume_skills(data))
        res_content = replace_block(res_content, "RESUME_EXPERIENCE", generate_resume_experience(data))
        res_content = replace_block(res_content, "RESUME_P1_PROJECTS", generate_resume_projects(data, page_num=1))
        res_content = replace_block(res_content, "RESUME_P2_PROJECTS", generate_resume_projects(data, page_num=2))
        res_content = replace_block(res_content, "RESUME_PERSONAL_PROJECTS", generate_resume_personal_projects(data))
        
        # Keep pre-rendered date current with today's date
        today_date_str = datetime.now().strftime("%d/%m/%Y")
        res_content = re.sub(r'<span id="resume-signature-date">[^<]*</span>', f'<span id="resume-signature-date">{today_date_str}</span>', res_content)
        
        with open(RESUME_FILE, "w", encoding="utf-8") as f:
            f.write(res_content)
        print(f"  [OK] {RESUME_FILE.name} synchronized.")
        
    print(f"\n[SUCCESS] Both portfolio UI and resume are 100% in sync with data.json!")
    print(f"Total Projects: {len(data['projects'])} | Personal Projects: {len(data['personalProjects'])} | Certifications: {len(data['certifications'])}")

if __name__ == "__main__":
    sync()
