/**
 * i18n-ui.js - Language Selector UI Component
 * 
 * Provides a reusable language switcher component that:
 * - Displays available languages
 * - Handles language switching
 * - Updates UI in real-time
 * - Maintains visual consistency
 * 
 * Usage:
 *   <div id="language-switcher" class="language-switcher"></div>
 *   <script>
 *     i18nUI.createLanguageSelector({
 *       containerId: 'language-switcher',
 *       position: 'header', // or 'settings'
 *       style: 'dropdown' // or 'buttons'
 *     });
 *   </script>
 */

const i18nUI = (function () {
  'use strict';

  // Language metadata
  const languageMetadata = {
    en: {
      label: 'English',
      flag: '🇬🇧',
      code: 'en'
    },
    vi: {
      label: 'Tiếng Việt',
      flag: '🇻🇳',
      code: 'vi'
    }
  };

  /**
   * Create a dropdown language selector
   */
  function createDropdownSelector(containerId, onLanguageChange) {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`Container with id "${containerId}" not found`);
      return;
    }

    const languages = i18n.getSupportedLanguages();
    const currentLang = i18n.getLanguage();

    // Create wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'language-selector-dropdown';

    // Create button
    const button = document.createElement('button');
    button.className = 'language-selector-button';
    button.id = 'language-selector-button';
    button.setAttribute('aria-label', 'Select language');
    button.setAttribute('aria-expanded', 'false');

    const meta = languageMetadata[currentLang] || { flag: '🌐', label: currentLang };
    button.innerHTML = `<span class="flag">${meta.flag}</span> <span class="label">${meta.label}</span> <i class="fas fa-chevron-down"></i>`;

    // Create dropdown menu
    const menu = document.createElement('div');
    menu.className = 'language-selector-menu';
    menu.id = 'language-selector-menu';
    menu.style.display = 'none';
    menu.setAttribute('role', 'listbox');

    languages.forEach((lang) => {
      const option = document.createElement('button');
      option.className = 'language-selector-option';
      if (lang === currentLang) {
        option.classList.add('active');
      }
      option.setAttribute('data-lang', lang);
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', lang === currentLang);

      const langMeta = languageMetadata[lang] || { flag: '🌐', label: lang };
      option.innerHTML = `<span class="flag">${langMeta.flag}</span> <span class="label">${langMeta.label}</span>`;
      option.title = langMeta.label;

      option.addEventListener('click', async () => {
        console.log(`[i18n-ui] Language option clicked: ${lang}`);
        console.log('[i18n-ui] Calling i18n.setLanguage...');
        const result = await i18n.setLanguage(lang);
        console.log(`[i18n-ui] setLanguage returned:`, result);
        updateDropdownUI(button, menu, languages);
        if (onLanguageChange) {
          console.log('[i18n-ui] Calling onLanguageChange callback');
          onLanguageChange(lang);
        }
      });

      menu.appendChild(option);
    });

    // Toggle menu
    button.addEventListener('click', (e) => {
      e.stopPropagation();
      console.log('[i18n-ui] Button clicked, menu display:', menu.style.display);
      const isOpen = menu.style.display === 'block';
      if (isOpen) {
        console.log('[i18n-ui] Closing menu');
        menu.style.display = 'none';
        button.setAttribute('aria-expanded', 'false');
      } else {
        console.log('[i18n-ui] Opening menu');
        menu.style.display = 'block';
        button.setAttribute('aria-expanded', 'true');
      }
    });

    // Close menu on outside click
    document.addEventListener('click', (e) => {
      if (!wrapper.contains(e.target)) {
        console.log('[i18n-ui] Clicked outside, closing menu');
        menu.style.display = 'none';
        button.setAttribute('aria-expanded', 'false');
      }
    });

    // Keyboard support
    button.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        button.click();
      }
    });

    wrapper.appendChild(button);
    wrapper.appendChild(menu);
    container.appendChild(wrapper);
  }

  /**
   * Create button group language selector
   */
  function createButtonGroupSelector(containerId, onLanguageChange) {
    const container = document.getElementById(containerId);
    if (!container) {
      console.error(`Container with id "${containerId}" not found`);
      return;
    }

    const languages = i18n.getSupportedLanguages();
    const currentLang = i18n.getLanguage();

    // Create wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'language-selector-buttons';

    languages.forEach((lang) => {
      const button = document.createElement('button');
      button.className = 'language-selector-btn';
      button.setAttribute('data-lang', lang);
      button.setAttribute('title', languageMetadata[lang]?.label || lang);

      if (lang === currentLang) {
        button.classList.add('active');
      }

      const meta = languageMetadata[lang] || { flag: '🌐', label: lang };
      button.innerHTML = `<span class="flag">${meta.flag}</span> <span class="label">${meta.label}</span>`;

      button.addEventListener('click', async () => {
        await i18n.setLanguage(lang);
        document.querySelectorAll('.language-selector-btn').forEach((btn) => {
          btn.classList.remove('active');
        });
        button.classList.add('active');
        if (onLanguageChange) onLanguageChange(lang);
      });

      wrapper.appendChild(button);
    });

    container.appendChild(wrapper);
  }

  /**
   * Update dropdown UI after language change
   */
  function updateDropdownUI(button, menu, languages) {
    const currentLang = i18n.getLanguage();
    const meta = languageMetadata[currentLang] || { flag: '🌐', label: currentLang };

    // Update button
    button.innerHTML = `<span class="flag">${meta.flag}</span> <span class="label">${meta.label}</span> <i class="fas fa-chevron-down"></i>`;

    // Update menu items
    menu.querySelectorAll('.language-selector-option').forEach((option) => {
      const lang = option.getAttribute('data-lang');
      if (lang === currentLang) {
        option.classList.add('active');
        option.setAttribute('aria-selected', 'true');
      } else {
        option.classList.remove('active');
        option.setAttribute('aria-selected', 'false');
      }
    });

    menu.style.display = 'none';
    button.setAttribute('aria-expanded', 'false');
  }

  // ================== PUBLIC API ==================

  return {
    /**
     * Create language selector
     */
    createLanguageSelector(options = {}) {
      const {
        containerId = 'language-selector',
        style = 'dropdown', // 'dropdown' or 'buttons'
        onLanguageChange = null
      } = options;

      console.log(`[i18nUI] Creating language selector: ${style} in #${containerId}`);

      if (!document.getElementById(containerId)) {
        console.error(`[i18nUI] Container #${containerId} not found!`);
        return;
      }

      if (style === 'dropdown') {
        createDropdownSelector(containerId, onLanguageChange);
        console.log('[i18nUI] ✅ Dropdown selector created');
      } else if (style === 'buttons') {
        createButtonGroupSelector(containerId, onLanguageChange);
        console.log('[i18nUI] ✅ Button group selector created');
      } else {
        console.error(`[i18nUI] Unknown style: ${style}`);
      }
    },

    /**
     * Get language metadata
     */
    getLanguageMetadata(lang) {
      return languageMetadata[lang] || null;
    },

    /**
     * Get all language metadata
     */
    getAllLanguageMetadata() {
      return { ...languageMetadata };
    }
  };
})();

// Expose i18nUI to global window object
window.i18nUI = i18nUI;
console.log('[i18n-ui.js] ✅ i18nUI exposed to window');
