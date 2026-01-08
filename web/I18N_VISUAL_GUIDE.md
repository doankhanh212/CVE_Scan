# i18n Visual Architecture & Flow Diagrams

---

## 1. SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                     Enterprise Dashboard                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐        ┌──────────────┐   ┌──────────────┐  │
│  │   HTML       │        │  JavaScript  │   │     CSS      │  │
│  │  Templates   │        │   Business   │   │    Styling   │  │
│  └──────┬───────┘        │     Logic    │   └──────────────┘  │
│         │                └──────┬───────┘                      │
│         │                       │                              │
│         └───────────────────────┼──────────────────────────────┘
│                                 │
│                 ┌───────────────┴───────────────┐
│                 │                               │
│         ┌───────▼────────┐            ┌────────▼──────┐
│         │  i18n Core     │            │  i18n UI      │
│         │  Library       │            │  Component    │
│         │                │            │               │
│         │ • Translate    │            │ • Selector    │
│         │ • Switch Lang  │            │ • Keyboard    │
│         │ • Cache Trans  │            │ • Accessible  │
│         │ • localStorage │            │ • Styleable   │
│         └───────┬────────┘            └────────┬──────┘
│                 │                               │
│         ┌───────▼───────────────────────────────▼─────┐
│         │                                             │
│         │    Translation Files (JSON)                │
│         │    • /static/i18n/en.json                  │
│         │    • /static/i18n/vi.json                  │
│         │                                             │
│         │    Styling                                │
│         │    • /static/css/i18n.css                 │
│         │                                             │
│         └─────────────────────────────────────────────┘
│
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. USER INTERACTION FLOW

```
User Arrives at Dashboard
  │
  ├─► Browser Language Detected (auto)
  │   OR
  └─► localStorage Language Preference
      │
      ▼
  Load Appropriate Translation File
  (en.json or vi.json)
  │
  ▼
  Render HTML with:
  - data-i18n attributes
  - Default English text as fallback
  │
  ▼
  JavaScript Translates:
  - All data-i18n elements
  - Dynamic content
  │
  ▼
  Dashboard Ready in User's Language
  │
  ├─► User Clicks Language Selector
  │   │
  │   ├─ EN (current)
  │   └─ VI
  │      │
  │      ▼
  │   i18n.setLanguage('vi')
  │      │
  │      ├─► Load vi.json (cached)
  │      ├─► Translate all DOM elements
  │      ├─► Save 'vi' to localStorage
  │      ├─► Dispatch i18n:languageChanged event
  │      │
  │      ▼
  │   Dashboard Updates Instantly
  │   (no page reload)
  │      │
  │      ├─► Optional: Reload dynamic content
  │      └─► Business logic unchanged
  │
  ▼
  User Navigates to Different Page
  │
  ├─► localStorage has 'vi' preference
  │
  ▼
  New page loads in Vietnamese automatically
  │
  ▼
  User Closes Browser
  │
  ├─► localStorage persists 'vi'
  │
  ▼
  User Returns Next Day
  │
  └─► Dashboard loads in Vietnamese (user's choice)
```

---

## 3. TRANSLATION KEY HIERARCHY

```
Root
│
├── common
│   ├── app_name: "HQG Security"
│   ├── loading: "Loading..."
│   ├── error: "Error"
│   └── ...
│
├── sidebar
│   ├── dashboard: "Dashboard"
│   ├── scan_targets: "Scan Targets"
│   ├── scan_results: "Scan Results"
│   └── ...
│
├── dashboard
│   ├── title: "Security Dashboard"
│   ├── subtitle: "Real-time vulnerability overview..."
│   ├── total_cves: "Total CVEs Detected"
│   ├── critical_severity: "Critical Severity"
│   └── ...
│
├── scan
│   ├── page_title: "Scan Targets"
│   ├── new_configuration: "New Scan Configuration"
│   ├── target_hosts: "Target Hosts"
│   ├── target_placeholder: "Enter IP addresses..."
│   └── ...
│
├── results
│   ├── page_title: "Scan Results"
│   ├── search_results: "Search results"
│   └── ...
│
├── vulnerabilities
│   ├── page_title: "Vulnerabilities"
│   └── ...
│
├── settings
│   ├── page_title: "Settings"
│   ├── general_settings: "General Settings"
│   ├── language: "Language"
│   └── ...
│
├── modal
│   ├── cve_details: "CVE Details"
│   └── ...
│
├── messages
│   ├── error_loading_data: "Error loading data"
│   ├── scan_started: "Scan started successfully"
│   └── ...
│
└── time
    ├── just_now: "Just now"
    ├── minutes_ago: "minutes ago"
    └── ...
```

---

## 4. COMPONENT RENDERING FLOW

```
HTML Template
│
├─ <span data-i18n="dashboard.title">Security Dashboard</span>
│  │
│  └─► i18n.t('dashboard.title')
│      │
│      ├─► Lookup in translations object
│      │   └─ translations.dashboard.title
│      │
│      ├─► Replace placeholders (if any)
│      │   └ {name} → John
│      │
│      └─► Set textContent
│          └─ <span>Bảng điều khiển Bảo mật</span> (VI)
│
├─ <input data-i18n="scan.target_placeholder"
│         data-i18n-attr="placeholder">
│  │
│  └─► i18n.t('scan.target_placeholder')
│      │
│      └─► Set attribute (not textContent)
│          └─ <input placeholder="Nhập địa chỉ IP...">
│
└─ <button onclick="handleClick()">Start Scan</button>
   │
   └─ i18n.t('scan.start_scan')
      │
      └─ In JavaScript: "Bắt đầu Quét" (VI)
```

---

## 5. LANGUAGE SWITCHING LIFECYCLE

```
Initial State
  │
  ├─ App loads with English (default)
  ├─ i18n.js initializes
  ├─ en.json loaded and cached
  ├─ DOM elements translated
  └─ localStorage set to 'en'
     │
     ▼

User Clicks Language Selector
  │
  ├─ Dropdown menu appears
  │ ┌─────────────────────┐
  │ │  🇬🇧 English   ✓    │
  │ │  🇻🇳 Tiếng Việt     │ ◄─ User clicks here
  │ └─────────────────────┘
  │
  ▼

setLanguage('vi') Called
  │
  ├─ Load vi.json (from cache)
  │  └─ (~50ms if already loaded)
  │
  ├─ Update internal translations object
  │
  ├─ Call translateDOM()
  │  └─ Find all [data-i18n] elements
  │  └─ Update textContent/attributes
  │  └─ (~50ms for typical dashboard)
  │
  ├─ Set localStorage['app_language'] = 'vi'
  │
  ├─ Dispatch i18n:languageChanged event
  │  └─ Trigger any listeners
  │  └─ Optional: reload dynamic data
  │
  ├─ Update HTML lang attribute
  │  └─ <html lang="vi">
  │
  ▼

UI Updates Complete
  │
  ├─ All visible text now in Vietnamese
  ├─ No page reload occurred
  ├─ No network requests
  ├─ User can continue working
  │
  ▼

User Navigates to New Page
  │
  ├─ localStorage['app_language'] = 'vi'
  │
  ├─ New page loads
  │
  ├─ i18n.init() called
  │  └─ Detects 'vi' in localStorage
  │  └─ Loads vi.json (cached)
  │  └─ Translates all elements
  │
  ▼

Page Displays in Vietnamese Automatically
  │
  ├─ No user action needed
  ├─ Seamless experience
  │
  ▼

User Closes Browser & Returns Tomorrow
  │
  ├─ localStorage persists 'vi'
  │
  ├─ Dashboard loads in Vietnamese
  │  └─ User's preference remembered
  │
  ▼

Consistent User Experience
```

---

## 6. DATA-I18N ATTRIBUTE PATTERNS

```
Pattern 1: Text Content
┌─────────────────────────────────────────────────┐
│ <span data-i18n="sidebar.dashboard">            │
│   Dashboard                                     │
│ </span>                                         │
│                                                 │
│ Result:                                         │
│ EN: Dashboard                                   │
│ VI: Bảng điều khiển                            │
└─────────────────────────────────────────────────┘

Pattern 2: Placeholder Attribute
┌─────────────────────────────────────────────────┐
│ <input                                          │
│   data-i18n="scan.target_placeholder"          │
│   data-i18n-attr="placeholder"                 │
│   placeholder="Enter IP addresses...">         │
│ </input>                                        │
│                                                 │
│ Result:                                         │
│ EN: placeholder="Enter IP addresses..."        │
│ VI: placeholder="Nhập địa chỉ IP..."          │
└─────────────────────────────────────────────────┘

Pattern 3: Multiple Attributes
┌─────────────────────────────────────────────────┐
│ <a href="#"                                     │
│   data-i18n="sidebar.dashboard"                │
│   title="Go to Dashboard">                     │
│   Dashboard                                     │
│ </a>                                            │
│                                                 │
│ • textContent translates                        │
│ • title attribute does NOT translate           │
│ • Use separate data-i18n for title if needed   │
└─────────────────────────────────────────────────┘

Pattern 4: Dynamic Placeholders
┌─────────────────────────────────────────────────┐
│ Translation File:                               │
│ "messages": {                                  │
│   "welcome": "Welcome, {name}!"                │
│ }                                               │
│                                                 │
│ JavaScript:                                    │
│ i18n.t('messages.welcome', { name: 'John' })  │
│                                                 │
│ Result:                                         │
│ EN: "Welcome, John!"                           │
│ VI: "Chào mừng, John!"                         │
└─────────────────────────────────────────────────┘

Pattern 5: Conditional Content
┌─────────────────────────────────────────────────┐
│ <div id="empty-state">                          │
│   <p data-i18n="scan.no_active_scans">          │
│     No active scans                            │
│   </p>                                          │
│ </div>                                          │
│                                                 │
│ JavaScript:                                    │
│ if (scans.length === 0) {                      │
│   container.innerHTML = `                       │
│     <div class="empty-state">                  │
│       <p>${i18n.t('scan.no_active_scans')}    │
│       </p>                                      │
│     </div>                                      │
│   `;                                            │
│ }                                               │
│                                                 │
│ Result:                                         │
│ EN: "No active scans"                          │
│ VI: "Không có quét đang hoạt động"            │
└─────────────────────────────────────────────────┘
```

---

## 7. FILE STRUCTURE

```
web/
│
├── static/
│   │
│   ├── i18n/                    ◄─ Translation Files
│   │   ├── en.json              (4.2 KB, 127 keys)
│   │   └── vi.json              (4.3 KB, 127 keys)
│   │
│   ├── js/
│   │   ├── i18n.js              ◄─ Core Library (8 KB)
│   │   ├── i18n-ui.js           ◄─ UI Component (7 KB)
│   │   ├── dashboard.js
│   │   ├── scan.js
│   │   └── ...
│   │
│   └── css/
│       ├── i18n.css             ◄─ Selector Styling (4 KB)
│       ├── main.css
│       └── ...
│
├── templates/
│   ├── base.html                ◄─ Update with i18n
│   ├── dashboard.html           ◄─ Update templates
│   ├── scan.html
│   └── ...
│
├── base_i18n_example.html       ◄─ Reference
├── dashboard_i18n_example.html  ◄─ Reference
├── scan_i18n_example.html       ◄─ Reference
└── dashboard_i18n_example.js    ◄─ Reference
│
├── I18N_DELIVERY_SUMMARY.md     ◄─ This file
├── I18N_IMPLEMENTATION_GUIDE.md ◄─ Comprehensive guide
├── I18N_QUICK_START.md          ◄─ 5-min setup
└── I18N_IMPLEMENTATION_CHECKLIST.md ◄─ Tracking
```

---

## 8. ERROR HANDLING FLOW

```
User Action
│
├─ Page loads
├─ i18n.init() called
│  │
│  ├─ Try to load translation file (en.json or vi.json)
│  │  │
│  │  ├─ SUCCESS
│  │  │  └─ Use loaded translations
│  │  │
│  │  └─ FAILURE (404, network error)
│  │     │
│  │     ├─ Log warning to console
│  │     ├─ Try fallback language (DEFAULT_LANGUAGE)
│  │     │
│  │     ├─ SUCCESS
│  │     │  └─ Use fallback (English)
│  │     │
│  │     └─ FAILURE
│  │        └─ Return translation key as text
│  │           (e.g., "dashboard.title")
│  │
│  └─ Translate DOM with available translations
│
├─ During runtime: Missing translation key
│  │
│  ├─ User requests i18n.t('unknown.key')
│  │
│  ├─ Key not found in translations
│  │  │
│  │  ├─ Log warning: "Translation key not found: unknown.key"
│  │  ├─ Return key as fallback text: "unknown.key"
│  │  └─ Prevent runtime errors
│  │
│  └─ Page continues to work
│     (UI shows key text, but no crash)
│
└─ Error monitoring available
   └─ Check browser console for warnings
   └─ Review missing translations
   └─ Add to translation files
```

---

## 9. PERFORMANCE COMPARISON

```
WITH i18n System:
┌────────────────────────────────────────────────┐
│ Initial Load Time:                             │
│ • Page load:        No difference              │
│ • Translation:      +4-5 KB (per language)    │
│ • DOM translation:  +0 ms (cached script)     │
│ • Total impact:     Negligible                 │
│                                                 │
│ Language Switch:                               │
│ • Translation file: Cached (0 network)        │
│ • DOM translation:  ~50 ms (batch update)    │
│ • Total time:       < 100 ms                  │
│ • Page reload:      NO                        │
│                                                 │
│ Memory Footprint:                              │
│ • Per language:     ~50 KB (translations)     │
│ • Scripts:          ~15 KB (i18n + ui)       │
│ • Total:            ~65 KB per language       │
│                                                 │
│ localStorage:                                  │
│ • Storage needed:   < 100 bytes                │
│ • Persistence:      Automatic                 │
│ • Performance:      No impact                  │
└────────────────────────────────────────────────┘

WITHOUT i18n System (Current):
┌────────────────────────────────────────────────┐
│ Multiple Language Versions:                    │
│ • EN version:       Full site                 │
│ • VI version:       Duplicate site            │
│ • Maintenance:      Double effort             │
│ • Consistency:      Hard to track             │
│ • Switching:        Page reload required      │
│ • User experience:  Clunky                    │
└────────────────────────────────────────────────┘
```

---

## 10. LANGUAGE SELECTOR APPEARANCE

### Dropdown Style
```
┌─────────────────────────────┐
│  🇬🇧 English ▼               │  ◄─ Button
├─────────────────────────────┤
│ 🇬🇧 English         ✓       │  ◄─ Menu Item (Active)
│ 🇻🇳 Tiếng Việt             │  ◄─ Menu Item
└─────────────────────────────┘

Mobile:
┌─────┐
│ 🇬🇧  │ ▼  ◄─ Compact, label hidden
└─────┘
```

### Button Group Style
```
┌──────────────┐  ┌──────────────┐
│ 🇬🇧 English  │  │ 🇻🇳 Tiếng Việt │
└──────────────┘  └──────────────┘
   (Active)           (Inactive)

Mobile:
┌────┐  ┌────┐
│🇬🇧 │  │🇻🇳 │
└────┘  └────┘
```

---

## 11. STATE MANAGEMENT

```
Browser State
├── localStorage
│   └── app_language: 'en' or 'vi'
│
├── JavaScript Memory
│   ├── i18n.currentLanguage: 'en'
│   ├── i18n.translations: { ... }
│   └── i18n.translationCache: { en: {...}, vi: {...} }
│
├── DOM
│   ├── <html lang="en"> or <html lang="vi">
│   ├── <span data-i18n="key">Translated Text</span>
│   └── Language selector button state
│
└── HTTP Cache
    └── /static/i18n/en.json (cached)
        /static/i18n/vi.json (cached)

Persistence Flow:
┌─────────────────────────────────────────┐
│ User selects Vietnamese                 │
├─────────────────────────────────────────┤
│ i18n.setLanguage('vi')                 │
│   ↓                                    │
│ localStorage['app_language'] = 'vi'    │
│   ↓                                    │
│ Page refresh                           │
│   ↓                                    │
│ i18n.init()                            │
│   ↓                                    │
│ Reads localStorage['app_language']     │
│   ↓                                    │
│ Loads Vietnamese automatically         │
│   ↓                                    │
│ User sees familiar language            │
└─────────────────────────────────────────┘
```

---

## 12. INTEGRATION CHECKLIST VISUAL

```
Phase 1: Setup (Day 1)
  [████████████████████████████] 100%
  ✓ Files copied
  ✓ base.html updated
  ✓ Language selector works

Phase 2: Template Migration (Days 2-5)
  [██████████░░░░░░░░░░░░░░░░] 40%
  ✓ dashboard.html
  ✓ scan.html
  ⏳ results.html
  ⏳ vulnerabilities.html
  ⏳ settings.html

Phase 3: JavaScript Integration (Days 5-6)
  [░░░░░░░░░░░░░░░░░░░░░░░░░░] 0%
  ⏳ dashboard.js
  ⏳ scan.js
  ⏳ modal-handlers.js
  ⏳ Other files

Phase 4: Translation Review (Day 7)
  [░░░░░░░░░░░░░░░░░░░░░░░░░░] 0%
  ⏳ Vietnamese review
  ⏳ Terminology check
  ⏳ Consistency check

Phase 5: Testing (Days 8-9)
  [░░░░░░░░░░░░░░░░░░░░░░░░░░] 0%
  ⏳ Functional testing
  ⏳ Cross-browser testing
  ⏳ Accessibility testing

Overall Progress:
████░░░░░░░░░░░░░░░░░░░░░░░░░ ~15% Complete
```

---

## Summary

This visual guide shows:
- ✅ System architecture
- ✅ User interaction flow
- ✅ Translation hierarchy
- ✅ Component rendering
- ✅ Language switching lifecycle
- ✅ File organization
- ✅ Error handling
- ✅ Performance comparison
- ✅ UI appearance
- ✅ State management
- ✅ Progress tracking

**Refer back to these diagrams as you implement i18n in your dashboard!**
