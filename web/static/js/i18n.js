/**
 * i18n.js - Enterprise Dashboard Internationalization (i18n) System
 * 
 * Provides lightweight, framework-agnostic translation and language switching
 * for the security dashboard. Supports English (en) and Vietnamese (vi).
 * 
 * Features:
 * - Load translations from JSON files
 * - Switch language at runtime without page reload
 * - Persist language preference in localStorage
 * - Data-attribute based translation mechanism
 * - Dynamic content support (placeholders)
 * 
 * Usage:
 *   i18n.init({ defaultLanguage: 'en', supportedLanguages: ['en', 'vi'] });
 *   i18n.t('dashboard.title');
 *   i18n.setLanguage('vi');
 */

const i18n = (function () {
  'use strict';

  // ================== PRIVATE VARIABLES ==================
  let currentLanguage = 'en';
  const supportedLanguages = ['en', 'vi'];
  let translations = {};
  const translationCache = {};
  let isInitialized = false;

  // Default language preference order
  const DEFAULT_LANGUAGE = 'en';
  const STORAGE_KEY = 'app_language';

  // ================== PRIVATE FUNCTIONS ==================

  /**
   * Detect browser language (if supported)
   */
  function detectBrowserLanguage() {
    if (!navigator.language) return DEFAULT_LANGUAGE;

    const browserLang = navigator.language.split('-')[0].toLowerCase();
    return supportedLanguages.includes(browserLang) ? browserLang : DEFAULT_LANGUAGE;
  }

  /**
   * Load translation file for a specific language
   */
  async function loadLanguageFile(lang) {
    if (translationCache[lang]) {
      console.log(`[i18n] Using cached language: ${lang}`);
      return translationCache[lang];
    }

    try {
      // Add a lightweight cache-busting query to avoid stale JSON in production caching
      const cacheBust = (window.I18N_VERSION || Date.now());
      const url = `/static/i18n/${lang}.json?v=${cacheBust}`;
      console.log(`[i18n] Fetching: ${url}`);
      
      const response = await fetch(url);
      if (!response.ok) {
        console.error(`[i18n] Failed to load translation file for ${lang}: HTTP ${response.status}`);
        return null;
      }

      const data = await response.json();
      console.log(`[i18n] ✅ Loaded ${lang}: ${Object.keys(data).length} top-level keys`);
      translationCache[lang] = data;
      return data;
    } catch (error) {
      console.error(`[i18n] Error loading translation file for ${lang}:`, error);
      return null;
    }
  }

  /**
   * Get nested translation value using dot notation
   * Example: getNestedValue(translations, 'dashboard.title')
   */
  function getNestedValue(obj, path) {
    const keys = path.split('.');
    let value = obj;

    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        return null;
      }
    }

    return value;
  }

  /**
   * Process placeholders in translation string
   * Example: 'Hello {name}' with { name: 'John' } → 'Hello John'
   */
  function replacePlaceholders(text, placeholders = {}) {
    return text.replace(/\{(\w+)\}/g, (match, key) => {
      return placeholders[key] !== undefined ? placeholders[key] : match;
    });
  }

  /**
   * Translate all elements with data-i18n attribute
   */
  function translateElements() {
    const elements = document.querySelectorAll('[data-i18n]');

    elements.forEach((element) => {
      const key = element.getAttribute('data-i18n');
      const attr = element.getAttribute('data-i18n-attr') || 'textContent';
      const placeholders = element.getAttribute('data-i18n-placeholders');

      const translation = module.t(key);
      if (translation) {
        const finalText = placeholders
          ? replacePlaceholders(translation, JSON.parse(placeholders))
          : translation;

        if (attr === 'textContent' || attr === 'innerText') {
          element.textContent = finalText;
        } else if (attr === 'innerHTML') {
          element.innerHTML = finalText;
        } else {
          element.setAttribute(attr, finalText);
        }
      }
    });
  }

  /**
   * Dispatch custom event when language changes
   */
  function dispatchLanguageChangeEvent(oldLang, newLang) {
    const event = new CustomEvent('i18n:languageChanged', {
      detail: { oldLanguage: oldLang, newLanguage: newLang }
    });
    document.dispatchEvent(event);
  }

  // ================== PUBLIC API ==================

  const module = {
    /**
     * Initialize i18n system
     */
    async init(options = {}) {
      const {
        defaultLanguage = DEFAULT_LANGUAGE,
        detectBrowser = true,
        supportedLangs = supportedLanguages
      } = options;

      console.log('[i18n] Initializing...');

      // Set supported languages
      supportedLanguages.length = 0;
      supportedLanguages.push(...supportedLangs);

      // Determine initial language
      const storedLanguage = localStorage.getItem(STORAGE_KEY);
      if (storedLanguage && supportedLanguages.includes(storedLanguage)) {
        currentLanguage = storedLanguage;
      } else if (detectBrowser) {
        currentLanguage = detectBrowserLanguage();
      } else {
        currentLanguage = defaultLanguage;
      }

      console.log(`[i18n] Detected language: ${currentLanguage}`);

      // Load current language
      console.log(`[i18n] Loading language file: ${currentLanguage}`);
      translations = await loadLanguageFile(currentLanguage);
      if (!translations) {
        console.warn(`[i18n] Failed to load language ${currentLanguage}, falling back to ${DEFAULT_LANGUAGE}`);
        translations = await loadLanguageFile(DEFAULT_LANGUAGE);
        currentLanguage = DEFAULT_LANGUAGE;
      }

      isInitialized = true;

      // Translate existing elements
      console.log('[i18n] Translating DOM elements...');
      this.translateDOM();

      // Set HTML lang attribute
      document.documentElement.lang = currentLanguage;

      console.log(`[i18n] ✅ Initialized with language: ${currentLanguage}`);
      return true;
    },

    /**
     * Get translation by key
     */
    t(key, placeholders = {}) {
      if (!isInitialized) {
        console.warn('i18n not initialized. Call i18n.init() first.');
        return key;
      }

      const value = getNestedValue(translations, key);
      if (!value) {
        console.warn(`Translation key not found: ${key}`);
        return key;
      }

      return replacePlaceholders(value, placeholders);
    },

    /**
     * Get current language
     */
    getLanguage() {
      return currentLanguage;
    },

    /**
     * Get supported languages
     */
    getSupportedLanguages() {
      return [...supportedLanguages];
    },

    /**
     * Check if language is supported
     */
    isLanguageSupported(lang) {
      return supportedLanguages.includes(lang);
    },

    /**
     * Set language and translate all elements
     */
    async setLanguage(lang) {
      if (!supportedLanguages.includes(lang)) {
        console.error(`Language ${lang} is not supported`);
        return false;
      }

      if (lang === currentLanguage) {
        return true;
      }

      const oldLanguage = currentLanguage;

      // Load language file if not cached
      const langData = await loadLanguageFile(lang);
      if (!langData) {
        console.error(`Failed to load language ${lang}`);
        return false;
      }

      currentLanguage = lang;
      translations = langData;

      // Save preference
      localStorage.setItem(STORAGE_KEY, lang);

      // Set HTML lang attribute
      document.documentElement.lang = currentLanguage;

      // Translate DOM
      this.translateDOM();

      // Dispatch event
      dispatchLanguageChangeEvent(oldLanguage, lang);

      console.log(`Language changed to: ${lang}`);
      return true;
    },

    /**
     * Translate all elements with data-i18n attribute
     */
    translateDOM() {
      if (!isInitialized) {
        console.warn('i18n not initialized');
        return;
      }
      translateElements();
    },

    /**
     * Add or update a translation key
     * (Useful for dynamic content)
     */
    setTranslation(key, value, lang = currentLanguage) {
      if (!translations) translations = {};

      const keys = key.split('.');
      let obj = translations;

      for (let i = 0; i < keys.length - 1; i++) {
        const k = keys[i];
        if (!(k in obj)) {
          obj[k] = {};
        }
        obj = obj[k];
      }

      obj[keys[keys.length - 1]] = value;
    },

    /**
     * Get all translations for current language
     */
    getAllTranslations() {
      return { ...translations };
    }
  };

  return module;
})();

// Expose i18n to global window object so other scripts can use it
window.i18n = i18n;
console.log('[i18n.js] ✅ i18n exposed to window');

// Auto-initialize if DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    i18n.init({ detectBrowser: true });
  });
} else {
  i18n.init({ detectBrowser: true });
}
