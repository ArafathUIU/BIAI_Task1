"""Control Center CSS - single source of design tokens and presentation."""

from __future__ import annotations

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root {
  --sv-bg: #F5F7FA;
  --sv-surface: #FFFFFF;
  --sv-sidebar: #0F1B2D;
  --sv-sidebar-text: #D5DEE8;
  --sv-sidebar-muted: #8FA0B5;
  --sv-sidebar-hover: rgba(255,255,255,0.06);
  --sv-accent: #0F6B7F;
  --sv-accent-deep: #0C5566;
  --sv-accent-soft: #E6F4F7;
  --sv-border: #DCE3EC;
  --sv-text: #12263A;
  --sv-muted: #6B7A8C;
  --sv-approve: #1B7F4B;
  --sv-approve-bg: #E6F4EC;
  --sv-reject: #B42318;
  --sv-reject-bg: #FDECEA;
  --sv-needs: #B54708;
  --sv-needs-bg: #FFF4E5;
  --sv-neutral: #475569;
  --sv-neutral-bg: #F1F5F9;
  --sv-radius-card: 10px;
  --sv-radius-btn: 8px;
  --sv-space: 8px;
}

html, body, [class*="css"] {
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  color: var(--sv-text);
  font-size: 14px;
}

.stApp { background: var(--sv-bg); }

/* Hide Streamlit chrome for a more app-like feel */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
.stDeployButton, [data-testid="stDeployButton"] { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
  background: var(--sv-sidebar) !important;
  border-right: 1px solid #0A1422;
  min-width: 260px !important;
  max-width: 270px !important;
  width: 260px !important;
}
section[data-testid="stSidebar"] > div:first-child {
  width: 260px !important;
}
section[data-testid="stSidebar"] * { color: var(--sv-sidebar-text) !important; }
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] small {
  color: var(--sv-sidebar-muted) !important;
}

/* Hide default radio circle; style as nav rows */
section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {
  display: none !important;
}
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child {
  display: none !important;
}
section[data-testid="stSidebar"] div[data-testid="stRadio"] label[data-baseweb="radio"],
section[data-testid="stSidebar"] div[data-testid="stRadio"] label,
section[data-testid="stSidebar"] [role="radiogroup"] label {
  background: transparent !important;
  border-radius: 8px !important;
  padding: 10px 14px !important;
  margin: 0 0 4px 0 !important;
  border: 1px solid transparent !important;
  transition: background 0.12s ease;
  min-height: 36px !important;
}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {
  background: var(--sv-sidebar-hover) !important;
}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked),
section[data-testid="stSidebar"] div[data-testid="stRadio"] label:has(input:checked) {
  background: rgba(15, 107, 127, 0.25) !important;
  border-color: rgba(15, 107, 127, 0.35) !important;
  color: #FFFFFF !important;
  font-weight: 600 !important;
}
section[data-testid="stSidebar"] [role="radiogroup"] {
  gap: 2px !important;
}

/* Main canvas - extra top padding so titles are not clipped */
.block-container {
  padding-top: 2rem !important;
  padding-bottom: 2.5rem !important;
  padding-left: 1.75rem !important;
  padding-right: 1.75rem !important;
  max-width: 1180px;
}
div[data-testid="stVerticalBlock"] > div { gap: 8px; }
.stMarkdown, .stCaption { margin-bottom: 0 !important; }
hr { margin: 16px 0 !important; border-color: var(--sv-border) !important; }

/* Buttons: teal primary, muted disabled, visible focus */
div[data-testid="stButton"] > button {
  border-radius: var(--sv-radius-btn) !important;
  min-height: 36px !important;
  font-weight: 600 !important;
  transition: background 0.12s ease, box-shadow 0.12s ease;
}
div[data-testid="stButton"] > button:focus-visible {
  outline: 2px solid var(--sv-accent) !important;
  outline-offset: 2px !important;
}
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
  background: var(--sv-accent) !important;
  border-color: var(--sv-accent) !important;
  color: #FFFFFF !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover:not(:disabled),
div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:hover:not(:disabled) {
  background: var(--sv-accent-deep) !important;
  border-color: var(--sv-accent-deep) !important;
}
div[data-testid="stButton"] > button:disabled,
div[data-testid="stButton"] > button[disabled],
div[data-testid="stButton"] > button[kind="primary"]:disabled,
div[data-testid="stButton"] > button[data-testid="baseButton-primary"]:disabled {
  background: #E8EEF4 !important;
  color: #8A97A8 !important;
  border-color: #D5DCE5 !important;
  opacity: 1 !important;
  box-shadow: none !important;
  cursor: not-allowed !important;
}

.sv-brand {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 4px 4px 16px 4px;
  border-bottom: 1px solid #24344D;
  margin-bottom: 16px;
}
.sv-brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: linear-gradient(145deg, #0F6B7F, #0C5566);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.85rem;
  flex-shrink: 0;
}
.sv-brand-copy strong {
  display: block;
  color: #FFFFFF !important;
  font-size: 0.82rem;
  line-height: 1.25;
  font-weight: 700;
}
.sv-brand-copy span {
  display: block;
  color: var(--sv-sidebar-muted) !important;
  font-size: 0.68rem;
  line-height: 1.3;
  margin-top: 2px;
}

.sv-side-stats {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #24344D;
  font-size: 12px;
  color: var(--sv-sidebar-muted) !important;
  line-height: 1.5;
}
.sv-side-stats strong { color: #E8EEF7 !important; font-weight: 600; }
.sv-side-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}
.sv-side-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(255,255,255,0.08);
  color: #E8EEF7 !important;
  border: 1px solid rgba(255,255,255,0.12);
}
.sv-side-badge.ok { border-color: rgba(27,127,75,0.45); color: #A7F3D0 !important; }
.sv-side-badge.warn { border-color: rgba(181,71,8,0.45); color: #FCD34D !important; }
.sv-side-badge.err { border-color: rgba(180,35,24,0.45); color: #FECACA !important; }

.sv-page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}
.sv-page-header h1 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--sv-text);
  line-height: 1.2;
}
.sv-page-header p {
  margin: 8px 0 0 0;
  color: var(--sv-muted);
  font-size: 14px;
  max-width: 42rem;
  line-height: 1.45;
}

.sv-cta-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: linear-gradient(135deg, #0F1B2D 0%, #0F6B7F 100%);
  color: #fff;
  border-radius: var(--sv-radius-card);
  padding: 20px 24px;
  margin-bottom: 16px;
  border: 1px solid #1A3348;
}
.sv-cta-banner h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #fff !important;
  letter-spacing: -0.02em;
}
.sv-cta-banner p {
  margin: 8px 0 0 0;
  color: #C9D4E3;
  font-size: 14px;
}
.sv-cta-banner .sv-cta-note {
  margin-top: 8px;
  color: #9FB0C5;
  font-size: 12px;
}
.sv-cta-action-wrap div[data-testid="stButton"] > button {
  min-height: 44px !important;
  font-size: 15px !important;
  font-weight: 700 !important;
  border-radius: var(--sv-radius-btn) !important;
  background: var(--sv-accent) !important;
  border-color: var(--sv-accent) !important;
  color: #fff !important;
  box-shadow: 0 6px 16px rgba(15, 107, 127, 0.28);
}
.sv-cta-action-wrap div[data-testid="stButton"] > button:disabled {
  background: #E8EEF4 !important;
  color: #8A97A8 !important;
  border-color: #D5DCE5 !important;
  box-shadow: none !important;
}

.sv-reason-panel {
  background: #fff;
  border: 1px solid var(--sv-border);
  border-left: 4px solid var(--sv-accent);
  border-radius: var(--sv-radius-card);
  padding: 16px;
  margin-bottom: 16px;
}
.sv-reason-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}
.sv-reason-list {
  margin: 0;
  padding-left: 18px;
  color: var(--sv-text);
  font-size: 14px;
  line-height: 1.45;
}
.sv-reason-list li { margin-bottom: 4px; }
.sv-reason-evidence {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--sv-border);
  font-size: 12px;
}
.sv-reason-evidence ul {
  margin: 8px 0 0 0;
  padding-left: 16px;
}
.sv-reason-evidence code {
  font-size: 12px;
  white-space: pre-wrap;
}

.sv-pie-card {
  background: #fff;
  border: 1px solid var(--sv-border);
  border-radius: var(--sv-radius-card);
  padding: 16px;
  height: 100%;
}
.sv-pie-layout {
  display: flex;
  align-items: center;
  gap: 16px;
}
.sv-pie {
  width: 108px;
  height: 108px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: inset 0 0 0 8px rgba(255,255,255,0.65);
}
.sv-pie-sm {
  width: 72px;
  height: 72px;
  box-shadow: inset 0 0 0 6px rgba(255,255,255,0.65);
}
.sv-pie-card-sm {
  min-height: 0;
  max-height: 160px;
}
.sv-pie-single {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 8px 0;
}
.sv-pie-single-count {
  font-size: 40px;
  font-weight: 700;
  line-height: 1;
}
.sv-pie-legend { flex: 1; min-width: 0; }
.sv-pie-legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--sv-muted);
  margin-bottom: 4px;
}
.sv-pie-legend-row i {
  width: 8px;
  height: 8px;
  border-radius: 2px;
  display: inline-block;
  flex-shrink: 0;
}
.sv-pie-legend-row strong { color: var(--sv-text); }

.sv-detail-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin-top: 8px;
}

.sv-sum-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.sv-sum-card {
  background: var(--sv-surface);
  border: 1px solid var(--sv-border);
  border-radius: var(--sv-radius-card);
  padding: 12px 14px;
  box-shadow: 0 1px 3px rgba(18, 38, 58, 0.04);
}
.sv-sum-card .label {
  font-size: 12px;
  color: var(--sv-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.sv-sum-card .value {
  margin-top: 4px;
  font-size: 18px;
  font-weight: 600;
  color: var(--sv-text);
  line-height: 1.3;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.sv-equal-card {
  background: var(--sv-surface);
  border: 1px solid var(--sv-border);
  border-radius: var(--sv-radius-card);
  padding: 16px;
  margin-bottom: 12px;
  min-height: 140px;
  box-shadow: 0 1px 3px rgba(18, 38, 58, 0.04);
}
.sv-kv-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 16px;
  margin-top: 12px;
}
.sv-kv-grid .lbl {
  display: block;
  font-size: 12px;
  color: var(--sv-muted);
  margin-bottom: 2px;
}
.sv-kv-grid strong { font-size: 14px; color: var(--sv-text); }
.sv-price-ok { color: var(--sv-approve) !important; }
.sv-price-warn { color: var(--sv-needs) !important; }
.sv-price-bad { color: var(--sv-reject) !important; }

.sv-stat-chips {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}
.sv-stat-chip {
  background: #fff;
  border: 1px solid var(--sv-border);
  border-radius: 8px;
  padding: 10px 12px;
}
.sv-stat-chip .lbl {
  display: block;
  font-size: 12px;
  color: var(--sv-muted);
  margin-bottom: 2px;
}
.sv-stat-chip strong {
  font-size: 15px;
  color: var(--sv-text);
}

/* Full-width extraction field table — no horizontal scroll */
.sv-field-table-wrap {
  width: 100%;
  max-height: 420px;
  overflow-y: auto;
  overflow-x: hidden;
  border: 1px solid var(--sv-border);
  border-radius: var(--sv-radius-card);
  background: #fff;
  margin-bottom: 16px;
}
.sv-field-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 13px;
}
.sv-field-table thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: #F8FAFC;
  color: var(--sv-muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  text-align: left;
  padding: 8px 12px;
  border-bottom: 1px solid var(--sv-border);
}
.sv-field-table tbody td {
  padding: 8px 12px;
  border-bottom: 1px solid #EEF2F7;
  vertical-align: middle;
  height: 40px;
  max-height: 40px;
  overflow: hidden;
}
.sv-field-table tbody tr:hover td { background: #F8FBFC; }
.sv-field-table .col-field { width: 22%; }
.sv-field-table .col-value { width: 38%; }
.sv-field-table .col-status { width: 16%; }
.sv-field-table .col-conf { width: 12%; }
.sv-field-table .col-evidence { width: 12%; }
.sv-field-table .col-field code {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}
.sv-cell-clip {
  display: block;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: normal;
  max-width: 100%;
}
.sv-cell-empty { color: var(--sv-muted); }
.sv-conf {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--sv-muted);
}
.sv-conf-bar {
  flex: 1;
  height: 6px;
  border-radius: 999px;
  background: #E2E8F0;
  overflow: hidden;
  min-width: 36px;
}
.sv-conf-bar > span {
  display: block;
  height: 100%;
  background: var(--sv-accent);
  border-radius: 999px;
}

.sv-card {
  background: var(--sv-surface);
  border: 1px solid var(--sv-border);
  border-radius: var(--sv-radius-card);
  padding: 16px;
  box-shadow: 0 1px 3px rgba(18, 38, 58, 0.04);
  margin-bottom: 16px;
}
.sv-card.compact { padding: 12px 16px; }

.sv-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin: 0 0 16px 0;
}
.sv-kpi {
  background: var(--sv-surface);
  border: 1px solid var(--sv-border);
  border-radius: var(--sv-radius-card);
  padding: 16px;
  box-shadow: 0 1px 3px rgba(18, 38, 58, 0.04);
  border-top: 3px solid var(--sv-accent);
}
.sv-kpi.approve { border-top-color: var(--sv-approve); }
.sv-kpi.reject { border-top-color: var(--sv-reject); }
.sv-kpi.needs { border-top-color: var(--sv-needs); }
.sv-kpi .label {
  color: var(--sv-muted);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.sv-kpi .value {
  font-size: 28px;
  font-weight: 700;
  margin-top: 4px;
  line-height: 1.1;
  color: var(--sv-text);
}
.sv-kpi .hint {
  margin-top: 8px;
  color: var(--sv-muted);
  font-size: 12px;
  line-height: 1.3;
}
.sv-kpi.approve .value { color: var(--sv-approve); }
.sv-kpi.reject .value { color: var(--sv-reject); }
.sv-kpi.needs .value { color: var(--sv-needs); }

.sv-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
  white-space: nowrap;
  line-height: 1.35;
  min-height: 24px;
  vertical-align: middle;
}
.sv-badge.approve { background: var(--sv-approve-bg); color: var(--sv-approve); border-color: #B7E4C7; }
.sv-badge.reject { background: var(--sv-reject-bg); color: var(--sv-reject); border-color: #F0B4B0; }
.sv-badge.needs { background: var(--sv-needs-bg); color: var(--sv-needs); border-color: #F5D0A9; }
.sv-badge.neutral { background: var(--sv-neutral-bg); color: var(--sv-neutral); border-color: #CBD5E1; }
.sv-badge.failed { background: #FEE2E2; color: #991B1B; border-color: #FECACA; }
.sv-badge.processing { background: #E6F4F7; color: #0C5566; border-color: #B6E0EA; }
.sv-badge.uploaded { background: #F8FAFC; color: #6B7A8C; border-color: #E2E8F0; }
.sv-badge.processed { background: #E6F4EC; color: #1B7F4B; border-color: #B7E4C7; }

.sv-section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 8px 0 12px 0;
  color: var(--sv-text);
}
.sv-muted { color: var(--sv-muted); font-size: 12px; }
.sv-eyebrow {
  color: var(--sv-muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin: 0 0 8px 0;
}

/* Compact horizontal stepper */
.sv-steps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0 0 16px 0;
}
.sv-step {
  background: #fff;
  border: 1px solid var(--sv-border);
  border-radius: var(--sv-radius-card);
  padding: 12px;
  font-size: 12px;
  color: var(--sv-muted);
}
.sv-step strong {
  display: block;
  color: var(--sv-text);
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 2px;
}
.sv-step .n {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #94A3B8;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  margin-right: 6px;
}
.sv-step.active {
  border-color: #9ED4DF;
  background: var(--sv-accent-soft);
}
.sv-step.active .n { background: var(--sv-accent); }
.sv-step.active strong { color: var(--sv-accent-deep); }
.sv-step.done {
  border-color: #B7E4C7;
  background: var(--sv-approve-bg);
}
.sv-step.done .n { background: var(--sv-approve); }

.sv-upload-shell {
  background: #fff;
  border: 1px solid var(--sv-border);
  border-radius: var(--sv-radius-card);
  padding: 16px;
  margin-bottom: 8px;
}
.sv-upload-shell .sv-upload-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 8px;
}
.sv-upload-icon {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: var(--sv-accent-soft);
  color: var(--sv-accent-deep);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}
.sv-upload-shell h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}
.sv-upload-shell p {
  margin: 4px 0 0 0;
  color: var(--sv-muted);
  font-size: 14px;
}

.sv-next-panel {
  background: #fff;
  border: 1px solid #B7E4C7;
  border-left: 4px solid var(--sv-approve);
  border-radius: var(--sv-radius-card);
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 4px 14px rgba(27, 127, 75, 0.08);
}
.sv-next-panel.warn {
  border-color: #F5D0A9;
  border-left-color: var(--sv-needs);
  box-shadow: 0 4px 14px rgba(181, 71, 8, 0.08);
}
.sv-next-panel.err {
  border-color: #F0B4B0;
  border-left-color: var(--sv-reject);
  box-shadow: 0 4px 14px rgba(180, 35, 24, 0.08);
}
.sv-next-panel h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--sv-text);
}
.sv-next-panel p {
  margin: 8px 0 12px 0;
  color: var(--sv-muted);
  font-size: 14px;
}
.sv-next-list {
  margin: 0 0 12px 0;
  padding: 0;
  list-style: none;
}
.sv-next-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 0;
  border-top: 1px solid #EEF2F7;
  font-size: 14px;
}
.sv-next-list li:first-child { border-top: none; }
.sv-next-hint {
  background: var(--sv-accent-soft);
  border: 1px solid #B6E0EA;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--sv-accent-deep);
  margin-bottom: 8px;
}

.sv-attention {
  background: var(--sv-needs-bg);
  border: 1px solid #F5D0A9;
  border-left: 4px solid var(--sv-needs);
  border-radius: var(--sv-radius-card);
  padding: 12px 16px;
  margin-bottom: 16px;
  color: var(--sv-needs);
  font-size: 14px;
}
.sv-attention strong { color: var(--sv-needs); }

.sv-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--sv-border);
  border-radius: var(--sv-radius-card);
  background: #fff;
}
.sv-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.sv-table th {
  text-align: left;
  padding: 12px 16px;
  border-bottom: 1px solid var(--sv-border);
  background: #F8FAFC;
  color: var(--sv-muted);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.sv-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #EEF2F7;
  vertical-align: middle;
}
.sv-table tr:last-child td { border-bottom: none; }
.sv-table tbody tr:hover td { background: #F8FBFC; }
.sv-table .sv-row-actions { white-space: nowrap; text-align: right; }
.sv-table a.sv-view-link {
  color: var(--sv-accent);
  font-weight: 600;
  text-decoration: none;
  font-size: 13px;
}
.sv-table a.sv-view-link:hover { text-decoration: underline; }

.sv-bar {
  display: flex;
  height: 12px;
  border-radius: 999px;
  overflow: hidden;
  background: #E2E8F0;
  margin: 8px 0;
}
.sv-bar > span {
  display: block;
  height: 100%;
  min-width: 0;
}
.sv-bar .a { background: var(--sv-approve); }
.sv-bar .r { background: var(--sv-reject); }
.sv-bar .n { background: #F59E0B; }
.sv-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  color: var(--sv-muted);
  font-size: 12px;
}
.sv-legend i {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  margin-right: 6px;
}

.sv-empty {
  background: #fff;
  border: 1px dashed #94A3B8;
  border-radius: var(--sv-radius-card);
  padding: 32px 24px;
  text-align: center;
  margin: 8px 0 16px 0;
}
.sv-empty .sv-empty-icon {
  font-size: 28px;
  margin-bottom: 8px;
  line-height: 1;
}
.sv-empty strong {
  display: block;
  font-size: 16px;
  margin-bottom: 4px;
  color: var(--sv-text);
}
.sv-empty span {
  color: var(--sv-muted);
  font-size: 14px;
}

/* Compact document row layout helpers */
.sv-doc-row {
  border-bottom: 1px solid #EEF2F7;
  padding: 8px 0;
}
.sv-doc-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--sv-text);
  line-height: 1.3;
}
.sv-doc-meta {
  color: var(--sv-muted);
  font-size: 12px;
  margin-top: 2px;
}
.sv-action-bar {
  background: #fff;
  border: 1px solid var(--sv-border);
  border-radius: var(--sv-radius-card);
  padding: 12px 16px;
  margin-top: 16px;
  box-shadow: 0 -2px 12px rgba(18, 38, 58, 0.04);
}
.sv-btn-ghost div[data-testid="stButton"] > button {
  background: transparent !important;
  border-color: transparent !important;
  color: var(--sv-muted) !important;
  box-shadow: none !important;
  font-weight: 500 !important;
}
.sv-btn-ghost div[data-testid="stButton"] > button:hover:not(:disabled) {
  background: #F1F5F9 !important;
  color: var(--sv-accent-deep) !important;
}
.sv-btn-compact div[data-testid="stButton"] > button {
  min-height: 36px !important;
  padding: 0 12px !important;
  font-size: 13px !important;
}

/* Compact file uploader */
div[data-testid="stFileUploader"] {
  background: #F8FBFC;
  border: 2px dashed #9ED4DF;
  border-radius: var(--sv-radius-card);
  padding: 4px 8px;
}
div[data-testid="stFileUploader"] section {
  padding: 8px !important;
}
div[data-testid="stFileUploader"] section > div { min-height: unset !important; }
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
  min-height: 64px !important;
  padding: 12px 16px !important;
}
div[data-testid="stFileUploader"] small { font-size: 12px !important; color: var(--sv-muted) !important; }

div[data-testid="stMetricValue"] { font-size: 1.25rem !important; }
div[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }

@media (max-width: 900px) {
  .sv-kpi-grid, .sv-steps { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sv-stat-chips { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sv-kv-grid { grid-template-columns: 1fr; }
  .sv-field-table .col-evidence,
  .sv-field-table th.col-evidence,
  .sv-field-table td.col-evidence { display: none; }
  .sv-field-table .col-field { width: 26%; }
  .sv-field-table .col-value { width: 42%; }
  .sv-field-table .col-status { width: 18%; }
  .sv-field-table .col-conf { width: 14%; }
}
@media (max-width: 640px) {
  .sv-kpi-grid, .sv-steps { grid-template-columns: 1fr; }
  .sv-page-header h1 { font-size: 22px; }
  .sv-stat-chips { grid-template-columns: 1fr 1fr; }
  .sv-field-table .col-conf,
  .sv-field-table th.col-conf,
  .sv-field-table td.col-conf { display: none; }
  .sv-field-table .col-field { width: 30%; }
  .sv-field-table .col-value { width: 48%; }
  .sv-field-table .col-status { width: 22%; }
}
</style>
"""


def inject_styles() -> None:
    import streamlit as st

    st.markdown(APP_CSS, unsafe_allow_html=True)
