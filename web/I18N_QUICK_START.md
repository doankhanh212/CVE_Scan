# i18n Quick Start Guide

**5-Minute Setup for Enterprise Dashboard Internationalization**

---

## 1. Copy Files to Your Project

```bash
# Translation files
cp en.json web/static/i18n/
cp vi.json web/static/i18n/

# JavaScript libraries
cp i18n.js web/static/js/
cp i18n-ui.js web/static/js/

# Styling
cp i18n.css web/static/css/
```

---

## 2. Update Your Base Template

Add these scripts and styles to `web/templates/base.html`:

```html
<!-- In <head> section -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/i18n.css') }}">

<!-- In <body> section, before closing </body> tag -->
<script src="{{ url_for('static', filename='js/i18n.js') }}"></script>
<script src="{{ url_for('static', filename='js/i18n-ui.js') }}"></script>

<!-- Language selector container (put in your header) -->
<div id="language-selector-container"></div>

<!-- Initialize language selector -->
<script>
document.addEventListener('DOMContentLoaded', () => {
    i18nUI.createLanguageSelector({
        containerId: 'language-selector-container',
        style: 'dropdown'
    });
});
</script>
```

---

## 3. Replace Hard-Coded Text

### In HTML Templates

```html
<!-- BEFORE -->
<span>Dashboard</span>
<label>Target Hosts</label>

<!-- AFTER -->
<span data-i18n="sidebar.dashboard">Dashboard</span>
<label data-i18n="scan.target_hosts">Target Hosts</label>
```

### For Attributes (placeholder, title, etc.)

```html
<!-- BEFORE -->
<input placeholder="Enter IP addresses...">

<!-- AFTER -->
<input 
  data-i18n="scan.target_placeholder"
  data-i18n-attr="placeholder"
  placeholder="Enter IP addresses..."
>
```

### In JavaScript

```javascript
// BEFORE
alert('Error loading data');

// AFTER
alert(i18n.t('messages.error_loading_data'));
```

---

## 4. Test It Out

1. Open your app in a browser
2. Look for the language selector (top right, typically)
3. Click English or Tiếng Việt
4. Page should update instantly without reload
5. Refresh the page — your choice should be remembered

---

## 5. File Locations

```
web/
├── static/
│   ├── i18n/
│   │   ├── en.json          ← English translations
│   │   └── vi.json          ← Vietnamese translations
│   ├── js/
│   │   ├── i18n.js          ← Core library
│   │   ├── i18n-ui.js       ← Language selector
│   │   └── dashboard.js
│   └── css/
│       ├── i18n.css         ← Selector styling
│       └── main.css
└── templates/
    ├── base.html            ← Update this
    ├── dashboard.html
    └── scan.html
```

---

## Translation Key Cheat Sheet

| Location | Key | Example |
|----------|-----|---------|
| Sidebar | `sidebar.dashboard` | Dashboard |
| Dashboard | `dashboard.title` | Security Dashboard |
| Scan page | `scan.page_title` | Scan Targets |
| Messages | `messages.error_loading_data` | Error loading data |
| Common | `common.app_name` | HQG Security |

**Full list:** See `en.json` for all available keys

---

## Common Changes

### Add New Text

1. Find the section in `en.json`
2. Add a new key-value pair
3. Add corresponding Vietnamese in `vi.json`
4. Use in HTML: `<element data-i18n="section.new_key">`

Example:
```json
{
  "sidebar": {
    "dashboard": "Dashboard",
    "new_feature": "New Feature"    ← Add this
  }
}
```

### Change Existing Translation

Edit `en.json` or `vi.json` and update the value:

```json
{
  "dashboard": {
    "title": "Security Dashboard"    ← Update this
  }
}
```

Changes take effect immediately on next language switch.

### Use Dynamic Values

```javascript
const message = i18n.t('messages.scan_found', {
    count: 5,
    duration: 30
});
// Returns: "Found 5 vulnerabilities in 30 seconds"
```

In translation file:
```json
{
  "messages": {
    "scan_found": "Found {count} vulnerabilities in {duration} seconds"
  }
}
```

---

## Real-World Examples

### Example 1: Translating a Form

**HTML:**
```html
<form id="scan-form">
    <label data-i18n="scan.target_hosts">Target Hosts</label>
    <textarea 
        id="targets"
        data-i18n="scan.target_placeholder"
        data-i18n-attr="placeholder"
    ></textarea>
    
    <button type="submit" data-i18n="scan.start_scan">
        Start Scan
    </button>
</form>
```

**Translation (en.json):**
```json
{
  "scan": {
    "target_hosts": "Target Hosts",
    "target_placeholder": "Enter IP addresses, CIDR ranges, or hostnames",
    "start_scan": "Start Scan"
  }
}
```

**Translation (vi.json):**
```json
{
  "scan": {
    "target_hosts": "Máy chủ Mục tiêu",
    "target_placeholder": "Nhập địa chỉ IP, dải CIDR hoặc tên máy chủ",
    "start_scan": "Bắt đầu Quét"
  }
}
```

### Example 2: Dynamic Error Message

**JavaScript:**
```javascript
async function loadScans() {
    try {
        const response = await fetch('/api/scans');
        if (!response.ok) {
            throw new Error('Failed to load');
        }
        // Process data...
    } catch (error) {
        // Show translated error
        const errorMsg = i18n.t('messages.error_loading_data');
        showErrorAlert(errorMsg);
    }
}
```

**Translation:**
```json
{
  "messages": {
    "error_loading_data": "Error loading data"  // en.json
    "error_loading_data": "Lỗi khi tải dữ liệu"  // vi.json
  }
}
```

### Example 3: Listen to Language Changes

```javascript
document.addEventListener('i18n:languageChanged', (e) => {
    console.log(`Switched to: ${e.detail.newLanguage}`);
    
    // Reload data if needed
    loadScans();
});
```

---

## Debugging

### Check if i18n is loaded

```javascript
// In browser console
console.log(typeof i18n);  // Should be 'object'
console.log(i18n.getLanguage());  // Should be 'en' or 'vi'
```

### List all translations

```javascript
Object.keys(i18n.getAllTranslations());
```

### Test a translation

```javascript
i18n.t('dashboard.title');  // Should return the translated text
```

### Check localStorage

```javascript
localStorage.getItem('app_language');  // Should show 'en' or 'vi'
```

---

## Styling the Language Selector

The selector uses CSS custom properties (variables) for easy theming:

```css
/* In your main CSS file */
:root {
    --color-primary: #0066cc;        /* Active state color */
    --color-border: #e0e0e0;         /* Border color */
    --color-text: #333;              /* Text color */
    --color-hover: #f5f5f5;          /* Hover background */
    --color-bg-secondary: #fff;      /* Background color */
}

/* Dark mode */
body.dark-mode {
    --color-bg-secondary: #2d2d2d;
    --color-text: #e0e0e0;
    --color-border: #444;
    --color-hover: #3d3d3d;
}
```

---

## Best Practices

✅ **DO:**
- Keep translations short and clear
- Group related translations by section
- Use professional language (enterprise context)
- Test in both languages before deployment
- Have Vietnamese reviewed by a native speaker

❌ **DON'T:**
- Mix English and Vietnamese in same value
- Translate numbers, dates, or CVE IDs
- Use machine translation without review
- Change the JSON structure without updating code
- Hard-code locale-specific formatting

---

## Performance

- **First load:** Translation file (~4 KB) loaded once
- **Language switch:** < 100 ms (cached, no network request)
- **DOM translation:** < 50 ms (optimized batch updates)

No performance impact on your dashboard.

---

## Troubleshooting Table

| Problem | Solution |
|---------|----------|
| Language selector not appearing | Check `language-selector-container` div exists |
| Translations not loading | Verify JSON files are in `/static/i18n/` folder |
| English text still showing | Check data-i18n attribute spelling |
| Switch doesn't work | Clear localStorage and refresh |
| Vietnamese garbled | Ensure UTF-8 charset in HTML |

---

## Next Steps

1. ✅ Copy i18n files to your project
2. ✅ Update base.html template
3. ✅ Start migrating templates (pick one at a time)
4. ✅ Test thoroughly in both languages
5. ✅ Deploy to staging for user feedback
6. ✅ Release to production

---

## Getting Help

**Common Questions:**

Q: Where are the translation files?  
A: `web/static/i18n/` folder

Q: How do I add a new language?  
A: Create a JSON file and update the `supportedLanguages` array

Q: Will this break my existing code?  
A: No. The i18n system only adds functionality; it doesn't modify business logic

Q: Can users revert to English?  
A: Yes. The language selector allows switching any time

Q: Do I need to restart the server?  
A: No. Just refresh the page in your browser

---

**Remember:** This system is designed to be simple, fast, and maintainable. Focus on translating text, and let the framework handle the rest.

**Good luck with your i18n implementation! 🚀**
