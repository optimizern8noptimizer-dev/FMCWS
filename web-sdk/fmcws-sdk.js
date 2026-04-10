/**
 * FMCWS Web SDK v1.0.0
 * Fraud Monitoring & Customer Warning Service — JavaScript SDK
 *
 * Подключение:
 *   <script src="fmcws-sdk.js"></script>
 *   <script>
 *     const fmcws = new FMCWS({
 *       apiUrl: 'https://fmcws.bank.by',
 *       apiKey: 'YOUR_API_KEY',
 *       clientId: 'PSEUDONYMIZED_CLIENT_ID',
 *     });
 *     fmcws.init();
 *   </script>
 *
 * Отправка события вручную:
 *   fmcws.track('TRANSFER_CREATE', { amount: 1500, currency: 'BYN' });
 */
(function (global) {
  'use strict';

  // ── Константы ──────────────────────────────────────────────────────────────
  var SDK_VERSION = '1.0.0';
  var WARN_STYLES = {
    medium: { bg: '#FFF3CD', border: '#FFC107', icon: '⚠️', title: 'Внимание' },
    high:   { bg: '#FFE0B2', border: '#FF9800', icon: '🔶', title: 'Подозрительная активность' },
    critical: { bg: '#FFEBEE', border: '#F44336', icon: '🚨', title: 'Критическое предупреждение' },
  };

  // ── Утилиты ────────────────────────────────────────────────────────────────
  function generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function getOrCreateSessionId() {
    var key = '__fmcws_sid';
    var sid = sessionStorage.getItem(key);
    if (!sid) {
      sid = generateId();
      sessionStorage.setItem(key, sid);
    }
    return sid;
  }

  function getDeviceFingerprint() {
    var parts = [
      navigator.userAgent,
      navigator.language,
      screen.width + 'x' + screen.height,
      new Date().getTimezoneOffset(),
      navigator.platform || '',
    ];
    // Простой non-crypto хэш для fingerprint
    var str = parts.join('|');
    var hash = 0;
    for (var i = 0; i < str.length; i++) {
      hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
    }
    return 'fp_' + Math.abs(hash).toString(16);
  }

  function getConnectionInfo() {
    var conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (conn) return { type: conn.effectiveType || '', downlink: conn.downlink };
    return {};
  }

  // ── Класс FMCWS ───────────────────────────────────────────────────────────
  function FMCWS(options) {
    if (!options || !options.apiUrl || !options.apiKey || !options.clientId) {
      throw new Error('[FMCWS] Required: apiUrl, apiKey, clientId');
    }

    this._apiUrl    = options.apiUrl.replace(/\/$/, '');
    this._apiKey    = options.apiKey;
    this._clientId  = options.clientId;
    this._sessionId = getOrCreateSessionId();
    this._fp        = getDeviceFingerprint();
    this._queue     = [];
    this._sending   = false;
    this._autoTrack = options.autoTrack !== false; // по умолчанию включено
    this._debug     = !!options.debug;

    this._log('[FMCWS] SDK initialized. Session:', this._sessionId);
  }

  // ── Инициализация ──────────────────────────────────────────────────────────
  FMCWS.prototype.init = function () {
    if (this._autoTrack) {
      this._attachAutoTracking();
    }
    // Отправляем события из очереди при восстановлении сети
    window.addEventListener('online', this._flush.bind(this));
    this._log('[FMCWS] ready');
    return this;
  };

  // ── Отправка события ───────────────────────────────────────────────────────
  FMCWS.prototype.track = function (eventType, extra) {
    var payload = {
      session_id:         this._sessionId,
      client_id:          this._clientId,
      event_type:         eventType,
      channel:            'web',
      device_fingerprint: this._fp,
      user_agent:         navigator.userAgent,
      extra:              extra || {},
    };

    // Добавляем в очередь и пробуем отправить
    this._queue.push(payload);
    this._flush();
    return this;
  };

  // ── Flush очереди ──────────────────────────────────────────────────────────
  FMCWS.prototype._flush = function () {
    if (this._sending || this._queue.length === 0) return;
    var self = this;
    var payload = this._queue.shift();
    this._sending = true;

    this._sendEvent(payload)
      .then(function (response) {
        self._sending = false;
        // Показываем предупреждение если нужно
        if (response && response.show_warning && response.warning_message) {
          self._showWarning(response.risk_level, response.warning_message);
        }
        if (self._queue.length > 0) self._flush();
      })
      .catch(function (err) {
        self._log('[FMCWS] Send error, re-queuing:', err);
        // Возвращаем в очередь для повторной отправки
        self._queue.unshift(payload);
        self._sending = false;
        // Retry через 5 сек
        setTimeout(function () { self._flush(); }, 5000);
      });
  };

  // ── HTTP запрос ───────────────────────────────────────────────────────────
  FMCWS.prototype._sendEvent = function (payload) {
    var self = this;
    var url = this._apiUrl + '/v1/events';

    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', url, true);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.setRequestHeader('X-API-Key', self._apiKey);
      xhr.timeout = 8000;

      xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) return;
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText));
          } catch (e) {
            resolve(null);
          }
        } else {
          reject(new Error('HTTP ' + xhr.status));
        }
      };
      xhr.ontimeout = function () { reject(new Error('timeout')); };
      xhr.onerror   = function () { reject(new Error('network error')); };
      xhr.send(JSON.stringify(payload));
    });
  };

  // ── UI: Предупреждение клиенту ─────────────────────────────────────────────
  FMCWS.prototype._showWarning = function (level, message) {
    // Убираем предыдущее предупреждение если есть
    var existing = document.getElementById('__fmcws_warning');
    if (existing) existing.parentNode.removeChild(existing);

    var style = WARN_STYLES[level] || WARN_STYLES.medium;
    var div = document.createElement('div');
    div.id = '__fmcws_warning';

    div.style.cssText = [
      'position:fixed',
      'top:20px',
      'right:20px',
      'z-index:999999',
      'max-width:420px',
      'padding:16px 20px',
      'background:' + style.bg,
      'border:2px solid ' + style.border,
      'border-radius:8px',
      'box-shadow:0 4px 20px rgba(0,0,0,0.15)',
      'font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif',
      'font-size:14px',
      'line-height:1.5',
      'color:#1a1a1a',
      'animation:__fmcws_slide 0.3s ease',
    ].join(';');

    // Inject keyframes once
    if (!document.getElementById('__fmcws_css')) {
      var style_el = document.createElement('style');
      style_el.id = '__fmcws_css';
      style_el.textContent = '@keyframes __fmcws_slide{from{transform:translateX(120%);opacity:0}to{transform:translateX(0);opacity:1}}';
      document.head.appendChild(style_el);
    }

    var closeBtn = '<button onclick="this.parentNode.parentNode.removeChild(this.parentNode)" '
      + 'style="float:right;background:none;border:none;cursor:pointer;font-size:18px;line-height:1;padding:0;margin-left:8px;color:#666">×</button>';

    div.innerHTML = closeBtn
      + '<strong style="font-size:15px">' + style.icon + ' ' + style.title + '</strong>'
      + '<p style="margin:8px 0 0">' + this._escapeHtml(message) + '</p>';

    document.body.appendChild(div);

    // Для critical — не автоскрываем
    if (level !== 'critical') {
      setTimeout(function () {
        if (div.parentNode) div.parentNode.removeChild(div);
      }, 12000);
    }
  };

  FMCWS.prototype._escapeHtml = function (str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  };

  // ── Автотрекинг ────────────────────────────────────────────────────────────
  FMCWS.prototype._attachAutoTracking = function () {
    var self = this;

    // Отслеживаем изменения visibility (параллельные сессии / переключение вкладок)
    document.addEventListener('visibilitychange', function () {
      self.track(document.hidden ? 'PAGE_HIDDEN' : 'PAGE_VISIBLE');
    });

    // Перехват форм с data-fmcws-event аттрибутом
    // Пример: <form data-fmcws-event="TRANSFER_CONFIRM" data-fmcws-amount="1500">
    document.addEventListener('submit', function (e) {
      var form = e.target;
      var eventType = form.getAttribute('data-fmcws-event');
      if (eventType) {
        var extra = {};
        Array.prototype.forEach.call(form.attributes, function (attr) {
          if (attr.name.startsWith('data-fmcws-') && attr.name !== 'data-fmcws-event') {
            var key = attr.name.replace('data-fmcws-', '');
            extra[key] = attr.value;
          }
        });
        self.track(eventType, extra);
      }
    }, true);
  };

  // ── Вспомогательные методы ─────────────────────────────────────────────────
  FMCWS.prototype._log = function () {
    if (this._debug) console.log.apply(console, arguments);
  };

  /** Явно задать clientId (например, после логина) */
  FMCWS.prototype.identify = function (clientId) {
    this._clientId = clientId;
    return this;
  };

  /** Сбросить сессию (например, после логаута) */
  FMCWS.prototype.reset = function () {
    sessionStorage.removeItem('__fmcws_sid');
    this._sessionId = getOrCreateSessionId();
    return this;
  };

  // ── Экспорт ───────────────────────────────────────────────────────────────
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = FMCWS;
  } else {
    global.FMCWS = FMCWS;
  }

})(typeof window !== 'undefined' ? window : this);
