# Enterprise Dashboard Internationalization (i18n) Implementation Guide

**Version:** 1.0  
**Date:** January 2026  
**Platform:** Security Dashboard (CVE / Risk / SOC)

---

## 1. ARCHITECTURE OVERVIEW

### 1.1 System Design

The i18n system is **lightweight, framework-agnostic, and production-ready**:

```
┌─────────────────────────────────────────────────┐
│           User Browser                          │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  HTML Templates with data-i18n attrs    │  │
│  └────────────────┬─────────────────────────┘  │
│                   │                             │
│  ┌────────────────▼─────────────────────────┐  │
│  │  i18n.js (Core Library)                 │  │
│  │  - Load translations                    │  │
│  │  - Store language preference            │  │
│  │  - Translate DOM elements               │  │
│  │  - Handle placeholders                  │  │
│  └────────────────┬─────────────────────────┘  │
│                   │                             │
│  ┌────────────────┼─────────────────────────┐  │
│  │  i18n-ui.js (Language Selector)         │  │
│  │  - Dropdown component                   │  │
│  │  - Button group component               │  │
│  │  - Keyboard/a11y support                │  │
│  └────────────────┬─────────────────────────┘  │
│                   │                             │
│  ┌────────────────▼─────────────────────────┐  │
│  │  i18n.css (Styling)                     │  │
│  │  - Light/dark mode support              │  │
│  │  - Responsive design                    │  │
│  │  - Accessibility features               │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘

                     │
                     │ HTTP Request
                     ▼
         ┌────────────────────────┐
         │  Translation Files     │
         │  /static/i18n/         │
         │  ├── en.json          │
         │  └── vi.json          │
         └────────────────────────┘
```

### 1.2 Key Features

✅ **Runtime Language Switching** - No page reload required  
✅ **localStorage Persistence** - User preference saved across sessions  
✅ **Browser Language Detection** - Auto-detect user locale  
✅ **Placeholder Support** - Dynamic content in translations  
✅ **Data-Attribute Based** - Clean separation from content  
✅ **Accessibility (a11y)** - ARIA labels, keyboard navigation  
✅ **Responsive Design** - Works on desktop and mobile  
✅ **Dark Mode Support** - Theme-aware styling  

---

## 2. TRANSLATION FILES STRUCTURE

### 2.1 File Organization

```
web/static/i18n/
├── en.json          (English translations)
└── vi.json          (Vietnamese translations)
```

### 2.2 Translation Key Naming Convention

Use **semantic, hierarchical keys** with dot notation:

```json
{
  "sidebar": {
    "dashboard": "Dashboard",
    "scan_targets": "Scan Targets"
  },
  "dashboard": {
    "title": "Security Dashboard",
    "total_cves": "Total CVEs Detected"
  },
  "messages": {
    "error_loading_data": "Error loading data"
  }
}
```

**Benefits:**
- Logical grouping by feature/page
- Easy to find and maintain
- Scalable for future languages
- Clear hierarchy

---

## 3. IMPLEMENTATION STEPS

### Step 1: Update HTML Templates

Replace hard-coded text with `data-i18n` attributes:

```html
<!-- BEFORE -->
<span>Dashboard</span>
<label>Target Hosts</label>
<input placeholder="Enter IP addresses...">

<!-- AFTER -->
<span data-i18n="sidebar.dashboard">Dashboard</span>
<label for="targets" data-i18n="scan.target_hosts">Target Hosts</label>
<input 
  id="targets"
  data-i18n="scan.target_placeholder"
  data-i18n-attr="placeholder"
>
```

**Pattern Summary:**
```html
<!-- Text content -->
<element data-i18n="key.name">Fallback Text</element>

<!-- Attributes (placeholder, title, alt, etc.) -->
<element 
  data-i18n="key.name"
  data-i18n-attr="placeholder"
>

<!-- Dynamic placeholders -->
<element 
  data-i18n="message.welcome"
  data-i18n-placeholders='{"name":"John"}'
>
  Welcome {name}!
</element>
```

### Step 2: Include i18n Scripts

Add to `base.html` template:

```html
<!-- Load i18n library FIRST -->
<script src="{{ url_for('static', filename='js/i18n.js') }}"></script>

<!-- Optional: Language selector component -->
<script src="{{ url_for('static', filename='js/i18n-ui.js') }}"></script>

<!-- Include i18n CSS -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/i18n.css') }}">

<!-- Your other scripts -->
<script src="{{ url_for('static', filename='js/dashboard.js') }}"></script>
```

### Step 3: Initialize Language Selector

In `base.html` template, within the header:

```html
<div id="language-selector-container"></div>

<script>
document.addEventListener('DOMContentLoaded', () => {
    // Create language selector
    i18nUI.createLanguageSelector({
        containerId: 'language-selector-container',
        style: 'dropdown',  // or 'buttons'
        onLanguageChange: (lang) => {
            console.log('Language changed to:', lang);
        }
    });

    // Listen for language changes
    document.addEventListener('i18n:languageChanged', (e) => {
        console.log(`Switched from ${e.detail.oldLanguage} to ${e.detail.newLanguage}`);
    });
});
</script>
```

### Step 4: Use i18n in JavaScript

```javascript
// Get translation
const text = i18n.t('dashboard.title');

// Get translation with placeholders
const message = i18n.t('messages.welcome', { name: 'John' });

// Switch language programmatically
await i18n.setLanguage('vi');

// Get current language
const lang = i18n.getLanguage();

// Listen for language changes
document.addEventListener('i18n:languageChanged', (e) => {
    console.log('Language changed to:', e.detail.newLanguage);
});
```

---

## 4. USAGE EXAMPLES

### 4.1 Static Content (HTML)

```html
<!-- Sidebar Navigation -->
<nav class="sidebar-nav">
    <a href="/dashboard" class="nav-item" data-i18n="sidebar.dashboard">
        Dashboard
    </a>
    <a href="/scan" class="nav-item" data-i18n="sidebar.scan_targets">
        Scan Targets
    </a>
</nav>

<!-- KPI Cards -->
<div class="kpi-card">
    <span class="kpi-label" data-i18n="dashboard.total_cves">Total CVEs Detected</span>
    <div class="kpi-value">{{ stats.total_cves }}</div>
</div>

<!-- Form Elements -->
<label for="targets" data-i18n="scan.target_hosts">Target Hosts</label>
<textarea 
    id="targets"
    data-i18n="scan.target_placeholder"
    data-i18n-attr="placeholder"
></textarea>
<span class="help-text" data-i18n="scan.target_help">
    Supports: IP addresses, CIDR notation, hostnames
</span>
```

### 4.2 Dynamic Content (JavaScript)

```javascript
// Load data and display with i18n
async function loadActiveScans() {
    try {
        const response = await fetch('/api/scans');
        const data = await response.json();
        
        if (data.scans.length === 0) {
            // Use i18n for empty state
            container.innerHTML = `
                <div class="empty-state">
                    <p>${i18n.t('scan.no_active_scans')}</p>
                </div>
            `;
            return;
        }
        
        // Render scans...
    } catch (error) {
        // Show error with i18n
        showError(i18n.t('messages.error_loading_data'));
    }
}

// Display messages
function showMessage(type) {
    const messageKey = type === 'success' 
        ? 'messages.success_message'
        : 'messages.error_occurred';
    
    alert(i18n.t(messageKey));
}

// React to language changes
document.addEventListener('i18n:languageChanged', () => {
    // Reload dynamic content
    loadActiveScans();
});
```

### 4.3 Placeholders in Translations

Translation file (`en.json`):
```json
{
    "messages": {
        "scan_complete": "Scan completed in {duration} seconds",
        "hosts_found": "{count} hosts found on {date}"
    }
}
```

JavaScript usage:
```javascript
const text1 = i18n.t('messages.scan_complete', { duration: 45 });
// Output: "Scan completed in 45 seconds"

const text2 = i18n.t('messages.hosts_found', { 
    count: 5, 
    date: '2026-01-08' 
});
// Output: "5 hosts found on 2026-01-08"
```

---

## 5. LANGUAGE SELECTOR COMPONENTS

### 5.1 Dropdown Style

```javascript
i18nUI.createLanguageSelector({
    containerId: 'language-selector-container',
    style: 'dropdown'
});
```

**Appearance:** Single button with dropdown menu  
**Best For:** Limited space (top bar, compact layouts)  
**Features:** Arrow indicator, keyboard accessible, click-to-toggle

### 5.2 Button Group Style

```javascript
i18nUI.createLanguageSelector({
    containerId: 'language-selector-container',
    style: 'buttons'
});
```

**Appearance:** Multiple buttons in a row  
**Best For:** Settings page, more prominent visibility  
**Features:** Active state indicator, direct selection

### 5.3 Custom Styling

The components use CSS custom properties (variables) for theming:

```css
:root {
    --color-primary: #0066cc;
    --color-border: #e0e0e0;
    --color-hover: #f5f5f5;
    --color-text: #333;
    --color-bg-secondary: #fff;
}

body.dark-mode {
    --color-bg-secondary: #2d2d2d;
    --color-text: #e0e0e0;
    --color-border: #444;
}
```

---

## 6. BEST PRACTICES FOR ENTERPRISE DASHBOARDS

### 6.1 Translation Key Management

✅ **DO:**
- Use semantic, hierarchical keys (`dashboard.total_cves`)
- Group related translations (`sidebar.*, dashboard.*, scan.*`)
- Use short, descriptive names
- Translate error/success messages
- Include help text and tooltips

❌ **DON'T:**
- Use generic keys like `text1`, `label2`, `msg3`
- Mix English and Vietnamese in same file
- Translate variable values (CVE IDs, numbers, dates)
- Hard-code formatting (use placeholders instead)

### 6.2 Dynamic Content Handling

```javascript
// ✅ GOOD: Translate the template, keep data as-is
const html = `
    <div class="result">
        <p>${i18n.t('results.severity')}: ${data.severity}</p>
        <p>${i18n.t('results.cve_id')}: ${data.cve_id}</p>
    </div>
`;

// ❌ BAD: Trying to translate the data
const html = `
    <p>${i18n.t(data.severity)}: ${data.severity}</p>
`;
```

### 6.3 Language Switching Performance

- Translations are cached in memory (fast lookups)
- No network requests on language switch
- DOM updates are batch-optimized
- Safe for rapid switching (users can test languages)

### 6.4 Accessibility (a11y)

The i18n system includes:
- ARIA labels for language selector
- Keyboard navigation (Tab, Enter, Space)
- Focus indicators
- High contrast mode support
- Reduced motion support

Verify in settings:
```bash
# Check in DevTools:
# 1. Keyboard navigation: Tab → language selector → Enter
# 2. Screen reader: Read the ARIA labels
# 3. Colors: Check contrast in DevTools
```

### 6.5 Vietnamese Translation Guidelines

**Professional & Formal Language** (Enterprise Context)

✅ **CORRECT:**
- "Quét" (scan as a noun/verb)
- "Lỗ hổng Bảo mật" (security vulnerability)
- "Mức độ Nghiêm trọng" (severity level)
- "Báo cáo" (report)
- "Xác thực" (authentication)

❌ **INCORRECT:**
- "quét quét" (childish repetition)
- "lỗi hổng" (informal variant)
- "độ nguy hiểm" (too casual)
- "cái báo" (colloquial)

**Capitalization:**
- Title case for menu items: "Bảng Điều khiển"
- Lower case for labels: "nhập tên người dùng"
- Preserve acronyms: "CVE", "CVSS", "CPE"

---

## 7. TESTING & VALIDATION

### 7.1 Manual Testing Checklist

```
□ Text renders correctly in both languages
□ Language preference persists across page reload
□ Language switch works without page reload
□ All form inputs show correct placeholders
□ Buttons and links have correct labels
□ Modal dialogs display translated text
□ Error messages translate properly
□ Empty states show translated text
□ Breadcrumbs/navigation update in real-time
□ Date/number formatting respects locale
□ Mobile layout works with both languages
□ Dark mode text is readable in both languages
```

### 7.2 Browser DevTools Validation

```javascript
// Test in Console
i18n.t('dashboard.title');                    // Should return translated text
i18n.getLanguage();                           // Should return current language
i18n.getSupportedLanguages();                 // Should return ['en', 'vi']
localStorage.getItem('app_language');         // Should persist choice

// Check translation coverage
Object.keys(i18n.getAllTranslations()).length; // Should be consistent
```

### 7.3 Performance Validation

```javascript
// Measure language switch time
console.time('languageSwitch');
await i18n.setLanguage('vi');
console.timeEnd('languageSwitch');
// Should complete in < 100ms

// Measure DOM update time
console.time('DOMUpdate');
i18n.translateDOM();
console.timeEnd('DOMUpdate');
// Should complete in < 50ms
```

---

## 8. ADDING NEW LANGUAGES

To add a new language (e.g., Mandarin Chinese):

### Step 1: Create translation file
```
web/static/i18n/zh.json
```

### Step 2: Add language metadata
In `i18n-ui.js`:
```javascript
const languageMetadata = {
    en: { label: 'English', flag: '🇬🇧', code: 'en' },
    vi: { label: 'Tiếng Việt', flag: '🇻🇳', code: 'vi' },
    zh: { label: '中文', flag: '🇨🇳', code: 'zh' }  // ADD THIS
};
```

### Step 3: Initialize with new language
```javascript
i18n.init({
    supportedLanguages: ['en', 'vi', 'zh']  // ADD HERE
});
```

That's it! The system will auto-detect and support the new language.

---

## 9. MIGRATION STRATEGY

### Phase 1: Implement Foundation (Week 1)
- Deploy i18n.js and i18n-ui.js
- Create en.json and vi.json files
- Update base.html with language selector

### Phase 2: Migrate Templates (Week 2-3)
- Convert one template at a time
- Test each template fully
- Verify all dynamic content works

### Phase 3: JavaScript Integration (Week 3-4)
- Update dashboard.js, scan.js, etc.
- Handle dynamic error/success messages
- Test language switching behavior

### Phase 4: Polish & Validation (Week 4-5)
- Vietnamese translation review
- Accessibility audit (a11y)
- Performance testing
- User acceptance testing

### Phase 5: Gradual Rollout (Week 5+)
- Deploy to staging environment
- Get user feedback
- Monitor for issues
- Gradually release to production

---

## 10. TROUBLESHOOTING

### Issue: Translations not loading
```javascript
// Check if i18n is initialized
console.log(i18n.getLanguage());  // Should return language code
console.log(i18n.getAllTranslations());  // Should show translation object
```

**Solution:**
- Verify JSON files are in `/static/i18n/` folder
- Check browser console for 404 errors
- Ensure i18n.js is loaded before other scripts

### Issue: Language switch doesn't work
```javascript
// Force reinitialize
await i18n.init({ detectBrowser: false, defaultLanguage: 'en' });
```

**Solution:**
- Clear localStorage: `localStorage.clear()`
- Check browser permissions (storage)
- Verify i18n-ui.js is loaded

### Issue: Vietnamese text displays incorrectly
- Check HTML charset: `<meta charset="UTF-8">`
- Verify JSON files are saved as UTF-8
- Check CSS font-family supports Vietnamese characters

### Issue: Fallback text still showing
```javascript
// Add to HTML element as fallback
<span data-i18n="missing.key">Fallback Text</span>
```

**Solution:**
- Ensure translation key exists in JSON
- Check for typos in key names
- Use browser DevTools to inspect data-i18n attributes

---

## 11. PRODUCTION CHECKLIST

Before deploying to production:

```
□ All hard-coded UI text translated to both languages
□ Translation files are minified (optional but recommended)
□ No console errors in browser DevTools
□ Language preference persists correctly
□ Mobile layout works with both languages
□ Accessibility tested (keyboard, screen readers)
□ Vietnamese translations reviewed by native speaker
□ Error handling implemented for missing translations
□ Performance tested (switch time < 100ms)
□ Backup/fallback strategy if translation files unavailable
□ Documentation updated for future maintainers
```

---

## 12. FILES SUMMARY

| File | Purpose | Size |
|------|---------|------|
| `en.json` | English translations | ~4 KB |
| `vi.json` | Vietnamese translations | ~4 KB |
| `i18n.js` | Core library (auto-init) | ~8 KB |
| `i18n-ui.js` | Language selector component | ~7 KB |
| `i18n.css` | Styling & responsive | ~4 KB |
| **TOTAL** | | **~27 KB** |

All files are production-ready with no external dependencies.

---

## 13. API REFERENCE

### i18n Object

```javascript
// Initialize
i18n.init({
    defaultLanguage: 'en',      // Fallback language
    detectBrowser: true,         // Auto-detect user locale
    supportedLanguages: ['en', 'vi']
})

// Get translation
i18n.t(key, placeholders)       // Return translated string

// Language management
i18n.setLanguage(lang)          // Switch language (async)
i18n.getLanguage()              // Get current language
i18n.getSupportedLanguages()    // Get available languages
i18n.isLanguageSupported(lang)  // Check if language supported

// DOM
i18n.translateDOM()             // Translate all data-i18n elements

// Advanced
i18n.setTranslation(key, value) // Set/override translation
i18n.getAllTranslations()       // Get all translations object
```

### i18nUI Object

```javascript
// Create language selector
i18nUI.createLanguageSelector({
    containerId: 'selector',
    style: 'dropdown',              // or 'buttons'
    onLanguageChange: (lang) => {}  // Callback
})

// Language metadata
i18nUI.getLanguageMetadata(lang)    // Get language info
i18nUI.getAllLanguageMetadata()     // Get all languages info
```

### Events

```javascript
// Listen for language changes
document.addEventListener('i18n:languageChanged', (e) => {
    console.log(e.detail.oldLanguage);  // Previous language
    console.log(e.detail.newLanguage);  // New language
});
```

---

## 14. SUPPORT & MAINTENANCE

### Common Questions

**Q: Do I need to translate dynamic data (CVE IDs, numbers)?**  
A: No. Only translate UI text (labels, buttons, messages). Data values should remain unchanged.

**Q: Can users switch languages multiple times?**  
A: Yes. The system is optimized for rapid switching with caching and batch updates.

**Q: What if a translation is missing?**  
A: The system returns the key itself (e.g., "dashboard.title") and logs a warning.

**Q: Does i18n work offline?**  
A: Yes. Translations are loaded once and cached. Works offline after initial load.

**Q: Can I use HTML in translations?**  
A: No. Use `data-i18n-attr="innerHTML"` for rich content, but sanitize carefully to prevent XSS.

---

## 15. CONCLUSION

This i18n system provides:
- ✅ Enterprise-grade internationalization
- ✅ Lightweight & framework-agnostic
- ✅ Production-ready code
- ✅ Excellent accessibility support
- ✅ Easy maintenance and scaling
- ✅ Professional Vietnamese support

**Next Steps:**
1. Review the translation files (en.json, vi.json)
2. Copy i18n files to your web/static folder
3. Update your base.html template
4. Test language switching
5. Gradually migrate remaining templates
6. Deploy to staging for user feedback
7. Release to production

For questions or issues, refer to the troubleshooting section or review the example files provided.

---

**Created:** January 8, 2026  
**Last Updated:** January 8, 2026  
**Status:** Production Ready
