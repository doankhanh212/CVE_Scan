# i18n Implementation Checklist

Use this checklist to track progress as you integrate i18n into your dashboard.

## Phase 1: Setup (Day 1)

- [ ] Copy translation files to `/static/i18n/`
  - [ ] en.json
  - [ ] vi.json

- [ ] Copy JavaScript files to `/static/js/`
  - [ ] i18n.js
  - [ ] i18n-ui.js

- [ ] Copy CSS file to `/static/css/`
  - [ ] i18n.css

- [ ] Update `base.html`
  - [ ] Add `<link>` for i18n.css in `<head>`
  - [ ] Add language selector container div
  - [ ] Include i18n.js script before other scripts
  - [ ] Include i18n-ui.js script
  - [ ] Add initialization code for language selector

- [ ] Test basic functionality
  - [ ] Language selector appears in header
  - [ ] Can switch between English and Vietnamese
  - [ ] No JavaScript errors in console
  - [ ] Language preference persists on refresh

## Phase 2: Template Migration (Days 2-5)

### Core Templates
- [ ] **dashboard.html**
  - [ ] Dashboard title and subtitle
  - [ ] KPI card labels
  - [ ] Chart titles
  - [ ] Table headers
  - [ ] Button labels
  - [ ] Empty state messages
  - [ ] Test in both languages

- [ ] **scan.html**
  - [ ] Form labels
  - [ ] Input placeholders
  - [ ] Help text
  - [ ] Button labels
  - [ ] Active scans section
  - [ ] Test in both languages

- [ ] **results.html**
  - [ ] Page title
  - [ ] Filter labels
  - [ ] Column headers
  - [ ] Button labels
  - [ ] Empty state messages
  - [ ] Test in both languages

- [ ] **vulnerabilities.html**
  - [ ] Page title
  - [ ] Filter labels
  - [ ] Vulnerability details labels
  - [ ] Button labels
  - [ ] Test in both languages

- [ ] **settings.html**
  - [ ] Section headers
  - [ ] Setting labels
  - [ ] Checkbox/toggle labels
  - [ ] Input placeholders
  - [ ] Help text
  - [ ] Button labels
  - [ ] Test in both languages

### Supporting Templates
- [ ] Components folder
  - [ ] severity.html
  - [ ] scan_form.html
  - [ ] recent_scans.html
  - [ ] Test in both languages

## Phase 3: JavaScript Integration (Days 5-6)

- [ ] **dashboard.js**
  - [ ] Error messages use `i18n.t()`
  - [ ] Success messages use `i18n.t()`
  - [ ] Listen for language changes
  - [ ] Reload data on language change if needed
  - [ ] Test translations work correctly

- [ ] **scan.js**
  - [ ] Form validation messages translated
  - [ ] Status messages translated
  - [ ] Error handling uses i18n
  - [ ] Test in both languages

- [ ] **modal-handlers.js**
  - [ ] Modal titles translated
  - [ ] Button labels translated
  - [ ] Confirmation messages translated
  - [ ] Test in both languages

- [ ] **result.js**
  - [ ] Filter labels translated
  - [ ] Export messages translated
  - [ ] Error messages translated
  - [ ] Test in both languages

- [ ] **vulnerabilities.js**
  - [ ] Table headers translated
  - [ ] Filter options translated
  - [ ] Messages translated
  - [ ] Test in both languages

- [ ] **settings.js**
  - [ ] Confirm dialogs translated
  - [ ] Success/error messages translated
  - [ ] Test in both languages

## Phase 4: Vietnamese Translation Review (Day 7)

- [ ] Have native Vietnamese speaker review:
  - [ ] Formal/professional tone
  - [ ] Technical term accuracy
  - [ ] Consistency across translations
  - [ ] No grammatical errors
  - [ ] Proper capitalization

- [ ] Common Vietnamese corrections:
  - [ ] "Quét" (scan) vs other variants
  - [ ] "Lỗ hổng Bảo mật" (security vulnerability)
  - [ ] "Mức độ Nghiêm trọng" (severity level)
  - [ ] Consistency in technical terms

- [ ] Update vi.json with feedback

## Phase 5: Testing & Validation (Days 8-9)

### Functional Testing
- [ ] [ ] Language selector works correctly
- [ ] [ ] Switch between EN and VI without page reload
- [ ] [ ] Language preference persists across pages
- [ ] [ ] Language preference persists after browser close
- [ ] [ ] All UI text is translated
- [ ] [ ] No hard-coded English text visible in VI mode
- [ ] [ ] All placeholders are translated
- [ ] [ ] All tooltips/titles are translated
- [ ] [ ] Error messages translate properly
- [ ] [ ] Success messages translate properly

### Layout & Styling Testing
- [ ] [ ] English text doesn't break layout
- [ ] [ ] Vietnamese text doesn't break layout (longer text)
- [ ] [ ] Buttons resize correctly for both languages
- [ ] [ ] Forms look good in both languages
- [ ] [ ] Mobile layout works in both languages
- [ ] [ ] Dark mode styling works
- [ ] [ ] Language selector looks good in header

### Accessibility Testing
- [ ] [ ] Keyboard navigation works (Tab through selector)
- [ ] [ ] Enter/Space keys work to select language
- [ ] [ ] Language selector has ARIA labels
- [ ] [ ] Screen reader announces language options
- [ ] [ ] High contrast mode works
- [ ] [ ] Reduced motion preference respected

### Performance Testing
- [ ] [ ] Language switch completes in < 100 ms
- [ ] [ ] No console errors
- [ ] [ ] No memory leaks
- [ ] [ ] Works on slow connections
- [ ] [ ] Works offline (after initial load)

### Cross-Browser Testing
- [ ] [ ] Chrome/Chromium
- [ ] [ ] Firefox
- [ ] [ ] Safari
- [ ] [ ] Edge
- [ ] [ ] Mobile browsers (iOS Safari, Chrome Mobile)

## Phase 6: Documentation & Handoff (Day 10)

- [ ] **Documentation Created**
  - [ ] I18N_IMPLEMENTATION_GUIDE.md (comprehensive guide)
  - [ ] I18N_QUICK_START.md (5-minute setup)
  - [ ] This checklist with your notes

- [ ] **Developer Notes**
  - [ ] How to add new languages
  - [ ] How to add new translations
  - [ ] Common gotchas and solutions
  - [ ] Translation key naming convention
  - [ ] Where to find translation files

- [ ] **Maintenance Instructions**
  - [ ] How to update translations
  - [ ] How to handle missing translations
  - [ ] Performance monitoring
  - [ ] User feedback handling

- [ ] **Code Review**
  - [ ] All changes follow naming conventions
  - [ ] No hard-coded text remains
  - [ ] Proper use of data-i18n attributes
  - [ ] JavaScript uses i18n.t() correctly
  - [ ] No accessibility issues introduced

## Phase 7: Staging & Production (Days 11-15)

- [ ] Deploy to staging environment
  - [ ] All files in correct locations
  - [ ] Static file serving works
  - [ ] No 404 errors for translation files
  - [ ] No console errors in DevTools

- [ ] User Acceptance Testing (UAT)
  - [ ] Business stakeholders review translations
  - [ ] Users from Vietnam review in Vietnamese
  - [ ] Users from English-speaking regions review in English
  - [ ] Gather feedback

- [ ] Production Deployment
  - [ ] Get approval from team lead
  - [ ] Create deployment plan
  - [ ] Deploy to production
  - [ ] Monitor for errors
  - [ ] Collect user feedback

- [ ] Post-Launch Monitoring
  - [ ] Check error logs daily for 1 week
  - [ ] Monitor language switch frequency
  - [ ] Collect user feedback
  - [ ] Fix any reported issues quickly

## Post-Launch: Future Language Support

- [ ] If adding Mandarin Chinese:
  - [ ] Create zh.json translation file
  - [ ] Add to supportedLanguages array
  - [ ] Get professional translation
  - [ ] Test thoroughly
  - [ ] Deploy with feature flag if needed

- [ ] If users request new languages:
  - [ ] Evaluate effort and cost
  - [ ] Get professional translation
  - [ ] Follow same process as Mandarin example
  - [ ] Document the addition

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| QA Lead | | | |
| Product Owner | | | |
| Ops Lead | | | |

---

## Notes & Issues

### During Implementation

Issue: ___________________
Status: [ ] Open [ ] Closed
Resolution: ___________________
Date: ___________________

---

**Last Updated:** January 8, 2026  
**Estimated Timeline:** 10-15 working days  
**Team Members:** _____________________
