# CVE_Scan Enterprise Dashboard - Visual Design Specification

## 📐 Design Overview

This document provides detailed visual specifications for the enterprise-grade security dashboard.

---

## 🎨 Visual Hierarchy

### Header: Enterprise Status Bar
```
┌──────────────────────────────────────────────────────────────┐
│  BACKGROUND: Linear gradient (secondary → tertiary)           │
│  BORDER-BOTTOM: 1px solid border-color                       │
│  SHADOW: 0 4px 6px rgba(0,0,0,0.1)                           │
│  PADDING: 1rem 2rem                                          │
│  HEIGHT: 80px                                                │
│  POSITION: Sticky top                                        │
└──────────────────────────────────────────────────────────────┘
```

### Main Content Area
```
LAYOUT: Flexbox row
├─ Sidebar (optional, 260px | collapsed: 80px)
│  ├ Background: secondary-bg
│  ├ Border-right: 1px solid border-color
│  └ Transition: width 0.3s ease
│
└─ Dashboard Container (flex: 1)
   ├ Background: primary-bg
   ├ Padding: 2rem
   ├ Max-width: 1600px
   └ Overflow-y: auto
```

---

## 🎯 Card Components

### KPI Card
```
┌─────────────────────────────────┐
│  STAT LABEL    [ICON]           │
│  (uppercase, secondary)          │
│                                 │
│  1247                           │
│  (2.25rem, bold, primary)       │
│                                 │
│  ↑ +127 this week              │
│  (0.875rem, success color)      │
└─────────────────────────────────┘

DIMENSIONS:
- Min-width: 260px
- Padding: 1.5rem
- Border: 1px solid border-color
- Border-radius: 12px
- Background: card-bg
- Transition: all 0.3s

HOVER STATE:
- Border-color: info
- Box-shadow: 0 10px 25px rgba(0,0,0,0.2)
- Transform: translateY(-2px)
```

### Severity Card
```
┌─────────────────────────────────┐
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━     │ ← 3px top border
│                                 │
│        42                       │
│    (3rem, bold)                 │
│                                 │
│     CRITICAL                    │
│  (1.125rem, bold)              │
│                                 │
│  CVSS 9.0-10.0 | Immediate      │
│  Action Required               │
│  (0.75rem, muted)              │
└─────────────────────────────────┘

DIMENSIONS:
- Min-width: 220px
- Padding: 2rem 1.5rem
- Border: 2px solid {severity-color}
- Border-radius: 12px
- Position: relative (for ::before)

COLORS BY SEVERITY:
- Critical: #ef4444
- High: #f97316
- Medium: #eab308
- Low: #3b82f6

HOVER:
- Box-shadow: 0 0 20px rgba({color}, 0.2)
```

### Panel (Generic Container)
```
┌─────────────────────────────────┐
│ TITLE                    [⟳] [⋮]│
├─────────────────────────────────┤
│                                 │
│        CONTENT                  │
│     (Variable height)           │
│                                 │
└─────────────────────────────────┘

DIMENSIONS:
- Padding: 1.5rem
- Border: 1px solid border-color
- Border-radius: 12px
- Background: card-bg
- Min-height: Variable (content)

HEADER:
- Display: flex
- Justify-content: space-between
- Margin-bottom: 1.5rem
```

---

## 🚨 Alert Component

```
┌────────────────────────────────────────────────────┐
│ ⚡ Critical Vulnerabilities Detected               │
│ 42 critical-severity CVEs require immediate action │
├────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────┐  │
│ │ CVE-2024-1234 • OpenSSH RCE       CRITICAL   │  │
│ │ Remote code execution in OpenSSH < 8.0...    │  │
│ │ 🖥️ 12 hosts | 🛡️ Port 22 | ⏱️ 2 hours ago    │  │
│ └──────────────────────────────────────────────┘  │
│                                                    │
│ ┌──────────────────────────────────────────────┐  │
│ │ CVE-2024-5678 • PostgreSQL Injection CRITICAL│  │
│ │ SQL injection vulnerability...                │  │
│ │ 🖥️ 8 hosts | 🛡️ Port 5432 | ⏱️ 1 day ago    │  │
│ └──────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘

ALERT PANEL STYLING:
- Grid-column: 1 / -1 (full width)
- Background: linear-gradient(135deg, rgba(239,68,68,0.05), rgba(249,115,22,0.05))
- Border: 1px solid border-color
- Border-radius: 12px
- Padding: 1.5rem

ALERT ICON:
- Width/Height: 44px
- Background: #ef4444
- Border-radius: 8px
- Display: flex
- Align-items: center
- Justify-content: center
- Color: white

ALERT ITEM:
- Background: card-bg
- Border: 1px solid border-color
- Border-left: 3px solid {severity-color}
- Border-radius: 8px
- Padding: 1rem
- Display: flex
- Gap: 1rem
- Transition: all 0.2s

ALERT ITEM HOVER:
- Background: hover-bg
- Border-left-color: High severity color
```

---

## 📊 Chart Components

### Doughnut Chart (Severity Distribution)
```
CONTAINER:
- Height: 300px
- Max-width: 400px
- Position: relative

CHART.JS CONFIG:
- Type: 'doughnut'
- backgroundColor: ['#ef4444', '#f97316', '#eab308', '#3b82f6']
- borderColor: '#1e2432'
- borderWidth: 2

LEGEND:
- Position: bottom
- Label color: #a0aec0
- Padding: 20px
- Font-size: 12px
```

### Line Chart (Trend)
```
CONTAINER:
- Height: 300px
- Position: relative

CHART.JS CONFIG:
- Type: 'line'
- borderColor: '#3b82f6'
- backgroundColor: 'rgba(59, 130, 246, 0.1)'
- Tension: 0.4
- Fill: true
- borderWidth: 2
- Point size: 6px

GRID:
- X-axis: hidden
- Y-axis: color #2d3748
- Tick color: #a0aec0
```

### Bar Chart (Horizontal)
```
CONTAINER:
- Height: 300px

CHART.JS CONFIG:
- Type: 'bar'
- indexAxis: 'y' (horizontal)
- backgroundColor: [gradient colors]
- borderRadius: 6px

LABELS:
- Port 22 (SSH)
- Port 443 (HTTPS)
- Port 80 (HTTP)
- Port 3306 (MySQL)
- Port 5432 (PostgreSQL)
```

### Bubble Chart (Risk Matrix)
```
CONTAINER:
- Height: 300px

DATA POINTS:
- x-axis: Hosts affected
- y-axis: Risk level %
- radius: Severity level

COLORS:
- Critical: #ef4444
- High: #f97316
- Medium: #eab308
- Low: #3b82f6
```

---

## 📋 Data Table

```
┌──────────────────────────────────────────────────────────────┐
│ TITLE                          [Search box]                   │
├──────┬──────────┬────────┬────────┬─────┬────┬────────────────┤
│ CVE  │ Host     │ Port   │ Sever. │ CVSS│#CVE│ Status         │
├──────┼──────────┼────────┼────────┼─────┼────┼────────────────┤
│CVE-2 │192.168.. │22 SSH  │CRITICAL│ 9.8 │ 3  │ Unpatched      │
├──────┼──────────┼────────┼────────┼─────┼────┼────────────────┤
│CVE-5 │192.168.. │5432 PG │CRITICAL│ 9.1 │ 2  │ In Progress    │
├──────┼──────────┼────────┼────────┼─────┼────┼────────────────┤
│CVE-9 │192.168.. │8080 HTTP│HIGH   │ 8.6 │ 5  │ Patched        │
└──────┴──────────┴────────┴────────┴─────┴────┴────────────────┘

TABLE STYLING:
- Width: 100%
- Border-collapse: collapse
- Overflow-x: auto (responsive)

HEADER (th):
- Background: hover-bg (#2d3748)
- Padding: 1rem
- Font-weight: 600
- Color: text-secondary
- Border-bottom: 1px solid border-color
- Font-size: 0.875rem
- Text-transform: uppercase
- Letter-spacing: 0.5px

CELLS (td):
- Padding: 1rem
- Border-bottom: 1px solid border-color
- Font-size: 0.875rem

ROW HOVER:
- Background: hover-bg
```

---

## 🎭 Badges & Labels

### Severity Badge
```
┌──────────────────┐
│  CRITICAL        │
└──────────────────┘

STYLING:
- Padding: 0.375rem 0.75rem
- Border-radius: 6px
- Font-size: 0.75rem
- Font-weight: 600
- Text-transform: uppercase
- Letter-spacing: 0.5px
- White-space: nowrap

BY SEVERITY:
Critical:
  - Background: rgba(239,68,68,0.2)
  - Color: #ef4444

High:
  - Background: rgba(249,115,22,0.2)
  - Color: #f97316

Medium:
  - Background: rgba(234,179,8,0.2)
  - Color: #eab308

Low:
  - Background: rgba(59,130,246,0.2)
  - Color: #3b82f6
```

### Status Badge
```
UNPATCHED:
- Color: #ef4444 (critical red)

IN PROGRESS:
- Color: #f97316 (orange/warning)

PATCHED:
- Color: #10b981 (success green)
```

---

## 🔄 Interaction States

### Button States
```
DEFAULT:
- Background: transparent
- Border: 1px solid border-color
- Color: text-secondary
- Padding: 0.5rem 0.75rem
- Border-radius: 6px

HOVER:
- Background: hover-bg
- Border-color: info
- Color: text-primary
- Transition: all 0.2s

ACTIVE:
- Background: info
- Color: white
```

### Card Hover States
```
KPI CARD:
- Border-color: info color (subtle blue)
- Box-shadow: 0 10px 25px rgba(0,0,0,0.2)
- Transform: translateY(-2px)
- Transition: all 0.3s

PANEL CARD:
- Border-color: rgba(59,130,246,0.3)
- Box-shadow: 0 10px 25px rgba(0,0,0,0.2)

SEVERITY CARD:
- Box-shadow: 0 0 20px rgba({color}, 0.2)

ALERT ITEM:
- Background: hover-bg
- Border-left-color: next severity level
```

---

## 🎬 Animations

### Pulse Animation (Status Indicator)
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

DURATION: 2s
ITERATION: infinite
```

### Fade In (Page Load)
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

DURATION: 0.5s
TIMING: ease-in
```

---

## 📱 Responsive Breakpoints

### Desktop (1200px+)
```
LAYOUT:
- Sidebar: 260px (visible)
- KPI Grid: 4 columns
- Severity Grid: 4 columns
- Main Grid: 2 columns (2×2 charts)
- Alert Panel: Full width
- Table: Full width

HEADER:
- Full layout with all elements inline
```

### Tablet (768px - 1200px)
```
LAYOUT:
- Sidebar: 80px (collapsed)
- KPI Grid: 2 columns
- Severity Grid: 2 columns
- Main Grid: 1 column (stacked)
- Alert Panel: Full width
- Table: Horizontal scroll

HEADER:
- Compressed, secondary actions icon-only
```

### Mobile (<768px)
```
LAYOUT:
- Sidebar: Hidden (hamburger menu)
- KPI Grid: 1 column
- Severity Grid: 1-2 columns
- Main Grid: 1 column
- Alert Panel: Full width
- Table: Horizontal scroll with sticky first column

HEADER:
- Flex-direction: column
- Brand: Compact
- Status: May hide
```

---

## 🌈 Color Usage Reference

### Severity Classification
```
CRITICAL (Red: #ef4444)
├─ KPI Card icon background
├─ Severity card border & top bar
├─ Alert badge
├─ Status "Unpatched"
└─ High priority visual

HIGH (Orange: #f97316)
├─ Secondary severity card
├─ Warning/elevated alerts
└─ In-progress status

MEDIUM (Yellow: #eab308)
├─ Medium severity card
├─ Schedule attention
└─ Monitor status

LOW (Blue: #3b82f6)
├─ Low severity card
├─ Info color throughout
└─ Non-urgent items
```

### Success/Status Colors
```
SUCCESS (Green: #10b981)
├─ Positive trends
├─ Healthy status
└─ Patched items

WARNING (Amber: #f59e0b)
├─ In-progress states
├─ Caution items
└─ Warning indicators

INFO (Cyan: #0ea5e9)
├─ Informational badges
├─ Hover states
└─ Navigation highlights
```

---

## 👁️ Visual Accessibility

### Contrast Ratios
```
Text Primary (#e2e8f0) on Primary BG (#0f1419): 14:1 ✓
Text Primary (#e2e8f0) on Card BG (#1e2432): 12:1 ✓
Badge Text on Badge BG: 4.5:1+ ✓
```

### Color Blindness Considerations
```
NOT USING color-only distinction:
✓ Use icons + colors
✓ Use text labels + colors
✓ Use patterns + colors
✗ Never color alone for meaning
```

### Touch Target Sizes
```
Buttons: Min 44x44px
Icons: Min 32x32px
Links: Min 44px height
```

---

## 🎯 Typography Details

### Font Family Stack
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
```

### Font Sizes
```
Page Title (h1): 1.875rem (30px) - 700 weight
Section Header (h2): 1.125rem (18px) - 600 weight
Metric Label: 0.875rem (14px) - 500 weight
Body Text: 0.875rem (14px) - 400 weight
Small/Badge: 0.75rem (12px) - 600 weight
```

### Line Heights
```
Default: 1.6
Headings: 1.2
Lists: 1.8
```

---

## 🏗️ Layout Spacing

### Consistency Scale
```
0.25rem = 4px (minimal)
0.5rem = 8px
0.75rem = 12px
1rem = 16px (base)
1.5rem = 24px (section gap)
2rem = 32px (major sections)
3rem = 48px (footer spacing)
```

---

## 📊 Grid System

### KPI Grid
```css
display: grid;
grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
gap: 1.5rem;
```

### Main Dashboard Grid
```css
display: grid;
grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
gap: 2rem;
```

### Alert Panel (Full Width)
```css
grid-column: 1 / -1;
```

---

## ✨ Polish Details

1. **Consistent corner radius**: 12px for cards, 6px for buttons
2. **Subtle shadows**: Always use calculated shadows, not harsh black
3. **Smooth transitions**: 0.2s for quick interactions, 0.3s for state changes
4. **Icon consistency**: All icons from Font Awesome 6.4+
5. **Whitespace**: Generous padding around key elements
6. **Alignment**: Perfect pixel alignment on all elements
7. **Borders**: Thin (1px) but visible contrast

