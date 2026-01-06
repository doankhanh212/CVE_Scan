# CSS Grid & Flexbox Reference Card: Dashboard Redesign

## 🎯 The 3-Panel Layout

```
┌─────────────────────────────────────────────────┐
│  Dashboard Grid (12 columns, 3 rows height)    │
├─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┤
│               PANEL 1 (4 cols)                  │  All panels:
├─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┤  • height: 100%
│               PANEL 2 (4 cols)                  │  • min-height: 540px
├─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┤  • flex: column
│               PANEL 3 (4 cols)                  │  • align-items: stretch
└─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

## Key CSS Properties

### Container Level
```css
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);  /* 3 equal columns */
    align-items: stretch;                   /* Fill height */
    gap: 1.25rem;                          /* Consistent spacing */
}
```

### Panel Level
```css
.panel {
    display: flex;              /* Flex children */
    flex-direction: column;     /* Stack vertically */
    height: 100%;              /* Fill grid cell */
    min-height: 540px;         /* Minimum height */
    padding: 0.85rem;          /* Consistent padding */
}
```

### Content Level
```css
.panel > .panel-header {
    flex: 0;                    /* Fixed height */
    margin-bottom: 0.5rem;
}

.panel > [content-area] {
    flex: 1;                    /* Expand to fill */
    min-height: [appropriate];
}
```

## Flexbox Rules

### flex: 0 (Don't Expand)
**Use for:** Headers, filters, fixed-size elements
```css
.panel-header { flex: 0; }      /* Header stays fixed */
.filter-controls { flex: 0; }   /* Filters stay fixed */
```

### flex: 1 (Expand to Fill)
**Use for:** Charts, lists, content areas
```css
.chart-container { flex: 1; }           /* Chart expands */
.host-risk-container { flex: 1; }      /* List expands */
```

### min-height (Prevent Crushing)
**Use for:** All flex containers
```css
.panel { min-height: 540px; }           /* Panel minimum */
.chart-container { min-height: 140px; } /* Chart minimum */
.dual-chart-container { min-height: 300px; }
```

## Grid Row Distribution

### Dual Chart Layout (Left Panel)
```css
.dual-chart-container {
    display: grid;
    grid-template-rows: 1fr 1fr;    /* Equal height */
    gap: 0.4rem;
    flex: 1;                        /* Expand to fill panel */
    min-height: 300px;
}
```

**Result:** Both charts get 50% of space each
```
┌─────────────────────┐
│   Chart 1 (50%)     │  flex: 1
├─────────────────────┤  gap: 0.4rem
│   Chart 2 (50%)     │  flex: 1
└─────────────────────┘
```

## Responsive Breakpoints

### Desktop (1920px+)
```css
/* 3 columns, all visible */
.dashboard-grid {
    grid-template-columns: repeat(3, 1fr);
}
.panel { height: 100%; }
```

### Tablet (1024px—1199px)
```css
@media (max-width: 1024px) {
    .dashboard-grid {
        grid-template-columns: repeat(2, 1fr);
    }
    .panel { height: 100%; }  /* Still maintain height */
}
```

### Mobile (< 768px)
```css
@media (max-width: 768px) {
    .dashboard-grid {
        grid-template-columns: 1fr;
    }
    .panel { height: auto; }  /* Content-driven */
}
```

## Common Patterns

### Pattern 1: Header + Content
```css
.container {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.container > .header {
    flex: 0;        /* Fixed */
}

.container > .content {
    flex: 1;        /* Expands */
    overflow-y: auto;
}
```

### Pattern 2: Dual Content
```css
.container {
    display: grid;
    grid-template-rows: 1fr 1fr;  /* Equal split */
    gap: 0.5rem;
    flex: 1;
}

.container > .item {
    min-height: 150px;  /* Minimum */
}
```

### Pattern 3: Header + Filters + List
```css
.container {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.header { flex: 0; }      /* Fixed */
.filters { flex: 0; }     /* Fixed */
.list { flex: 1; }        /* Expands */
```

## Height Calculation Example

### Total: 540px Panel

```
┌─────────────────────────┐  0px
│    Panel Header         │  28px
├─────────────────────────┤  28px
│                         │
│  Chart Container        │  ~484px
│  (flex: 1, min: 140px)  │  ← Expands to fill
│                         │
├─────────────────────────┤  ~512px
│    Padding/Borders      │  28px
└─────────────────────────┘  540px

flex: 0 elements = 28px (fixed)
flex: 1 elements = 540px - 28px - padding = ~484px
```

## Troubleshooting Checklist

| Issue | Check |
|-------|-------|
| Panel not expanding | `height: 100%` on `.panel` |
| Content not filling space | `flex: 1` on content container |
| Headers moving | `flex: 0` on header |
| Content crushed | Check `min-height` value |
| Unequal heights | `grid-template-rows: 1fr 1fr` |
| Large gap appears | Check for `margin-bottom` on filters |
| Chart too small | `flex: 1` + `min-height: [value]` |
| Mobile broken | Check media query override |

## Quick Copy-Paste Templates

### New Panel Template
```css
.new-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 540px;
    padding: 0.85rem;
}

.new-panel .header {
    flex: 0;
    margin-bottom: 0.5rem;
}

.new-panel .content {
    flex: 1;
    min-height: 300px;
    overflow-y: auto;
}
```

### New Chart Container Template
```css
.new-chart {
    flex: 1;
    min-height: 200px;
    position: relative;
    width: 100%;
    padding: 0;
}
```

### New List Container Template
```css
.new-list {
    flex: 1;
    overflow-y: auto;
    padding: 0.5rem 0.75rem;
    border-radius: 8px;
    gap: 0.3rem;
    display: flex;
    flex-direction: column;
}

.new-list .item {
    flex: 0;
    padding: 0.5rem;
    border-radius: 6px;
}
```

## Browser DevTools Tips

### Inspect Flexbox
1. Right-click element → Inspect
2. Look for "flex" badge on element
3. Click to enable flex/grid overlay
4. See flex distribution visually

### Check Grid
1. Inspect `.dashboard-grid`
2. Look for "grid" badge
3. Enable grid overlay
4. See 12-column layout

### Debug Heights
```javascript
// In console:
document.querySelector('.panel').offsetHeight    // Current height
getComputedStyle(document.querySelector('.panel')).flex  // Flex value
```

## Performance Notes

### What's Good
✅ Flexbox/Grid: GPU-accelerated
✅ No JavaScript required
✅ Responsive: Automatic layout
✅ No reflow hacks

### What to Avoid
❌ Fixed heights on flex: 1 elements
❌ Overflow hidden (prevents content)
❌ Negative margins (unreliable)
❌ JavaScript-driven sizes

## Reference Values

| Element | Property | Value | Why |
|---------|----------|-------|-----|
| `.panel` | height | 100% | Fill grid |
| `.panel` | min-height | 540px | Minimum |
| `.panel` | padding | 0.85rem | Consistent |
| `.panel-header` | flex | 0 | Fixed |
| `.content` | flex | 1 | Expand |
| `.dual-chart-container` | grid-template-rows | 1fr 1fr | Equal |
| `.chart` | min-height | 140px | Min visible |
| `.gap` | gap | 0.3–0.5rem | Tight |

## One-Line Summaries

```css
/* Make items fill container */
.container { height: 100%; }

/* Distribute space equally */
.container { grid-template-rows: 1fr 1fr; }

/* Expand content to available space */
.content { flex: 1; }

/* Keep header fixed size */
.header { flex: 0; }

/* Prevent content crushing */
.element { min-height: 100px; }

/* Stretch grid items to height */
.grid { align-items: stretch; }

/* Stack items vertically, expandable */
.container { display: flex; flex-direction: column; }
```

## Memory Aid

**"Flex 0 = Fixed, Flex 1 = Flexible"**

Think of:
- `flex: 0` = Anchor (doesn't move, doesn't expand)
- `flex: 1` = Sponge (expands to fill space)
- `min-height` = Safety net (prevents crushing)

## Color-Coded Example

```css
/* Blue = Grid container */
.dashboard-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    align-items: stretch;
}

/* Green = Flex containers */
.panel {
    display: flex;
    flex-direction: column;
    height: 100%;
}

/* Red = Fixed size items */
.panel-header {
    flex: 0;
    margin-bottom: 0.5rem;
}

/* Orange = Flexible size items */
.chart-container {
    flex: 1;
    min-height: 140px;
}
```

---

**This reference card covers 95% of common CSS Grid & Flexbox patterns used in the dashboard redesign.**

Print or bookmark for quick reference! 📌

