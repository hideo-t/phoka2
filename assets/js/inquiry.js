/*
 * 問い合わせ送信の共通処理（お問い合わせ・見積もり・各LP）
 *
 * 送信は FormSubmit（formsubmit.co）への通常の POST。
 *   宛先    : kinjyo@  （FormSubmit 有効化済み）
 *   CC      : sakata@ / parkhomes.okinawa@gmail.com
 *             → 1つのメールボックスが容量オーバー等で止まっても取りこぼさない
 *   自動返信: お客様の email 宛に「受付しました」を返す（_autoresponse）
 * さらに SHEET_URL（Google Apps Script のウェブアプリ）を設定すると、
 * 送信内容をスプレッドシートにも1行ずつ記録する。メールが全滅しても記録が残る。
 * 設定手順は docs/inquiry-sheet.md を参照。
 */
(function () {
  var ENDPOINT = 'https://formsubmit.co/kinjyo@parkhomes-okinawa.com';
  var CC = 'sakata@parkhomes-okinawa.com,parkhomes.okinawa@gmail.com';
  // 例: 'https://script.google.com/macros/s/XXXXXXXX/exec'（空のときは記録しない）
  var SHEET_URL = '';

  // 翻訳ページ（/en/ 等、i18n/build.py が生成）はお客様向けの文面だけ切り替える。
  // 社内に届く件名・項目名は日本語のまま、件名に言語を添える。
  var LANG = { en: '英語', 'zh-Hant': '繁体字', 'zh-Hans': '簡体字', ko: '韓国語' };
  var lang = document.documentElement.getAttribute('lang') || 'ja';
  if (!LANG[lang]) lang = 'ja';
  var NEXT = 'https://parkhomes-okinawa.com/' + (lang === 'ja' ? '' : lang + '/') + 'contact/thanks.html';
  var AUTORESPONSE = {
    ja:
      'このたびはパークホームズオキナワへお問い合わせいただき、ありがとうございます。\n' +
      '内容を確認のうえ、担当者より2営業日以内にご連絡いたします。\n\n' +
      'お急ぎの場合は、お電話（098-856-6666／平日 9:00–18:00）または\n' +
      'LINE（ID：@612soivj）でもご相談いただけます。\n\n' +
      'パークホームズオキナワ　https://parkhomes-okinawa.com/',
    en:
      'Thank you for contacting Park Homes Okinawa.\n' +
      'We have received your inquiry and will get back to you within 2 business days.\n\n' +
      'If it is urgent, please call +81-98-856-6666 (weekdays 9:00–18:00 JST)\n' +
      'or message us on LINE (ID: @612soivj).\n\n' +
      'Park Homes Okinawa  https://parkhomes-okinawa.com/en/',
    'zh-Hant':
      '感謝您聯繫 Park Homes Okinawa。\n' +
      '我們已收到您的諮詢，將於 2 個工作天內與您聯絡。\n\n' +
      '如有急事，請致電 +81-98-856-6666（平日 9:00–18:00 日本時間）\n' +
      '或透過 LINE（ID：@612soivj）聯絡我們。\n\n' +
      'Park Homes Okinawa  https://parkhomes-okinawa.com/zh-Hant/',
    'zh-Hans':
      '感谢您联系 Park Homes Okinawa。\n' +
      '我们已收到您的咨询，将于 2 个工作日内与您联系。\n\n' +
      '如有急事，请致电 +81-98-856-6666（工作日 9:00–18:00 日本时间）\n' +
      '或通过 LINE（ID：@612soivj）联系我们。\n\n' +
      'Park Homes Okinawa  https://parkhomes-okinawa.com/zh-Hans/',
    ko:
      'Park Homes Okinawa에 문의해 주셔서 감사합니다.\n' +
      '문의 내용을 확인한 후 영업일 기준 2일 이내에 담당자가 연락드리겠습니다.\n\n' +
      '급한 용무는 전화 +81-98-856-6666(평일 9:00–18:00 일본 시간) 또는\n' +
      'LINE(ID: @612soivj)으로 문의해 주세요.\n\n' +
      'Park Homes Okinawa  https://parkhomes-okinawa.com/ko/'
  }[lang];

  function withLang(subject) {
    return lang === 'ja' ? subject : subject + '［' + LANG[lang] + 'ページ］';
  }

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  // スプレッドシートへの記録。失敗してもメール送信は止めない。
  function logToSheet(subject, fields) {
    if (!SHEET_URL) return;
    try {
      var payload = JSON.stringify({ subject: withLang(subject), page: location.pathname, fields: fields });
      var blob = new Blob([payload], { type: 'text/plain;charset=UTF-8' });
      if (!(navigator.sendBeacon && navigator.sendBeacon(SHEET_URL, blob))) {
        fetch(SHEET_URL, { method: 'POST', mode: 'no-cors', keepalive: true, body: payload });
      }
    } catch (e) { /* 記録失敗は無視 */ }
  }

  function addHidden(form, name, value) {
    var input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }

  function addControls(form, subject) {
    addHidden(form, '_cc', CC);
    addHidden(form, '_subject', withLang(subject));
    addHidden(form, '_template', 'table');
    addHidden(form, '_captcha', 'false');
    addHidden(form, '_next', NEXT);
    addHidden(form, '_autoresponse', AUTORESPONSE);
  }

  /*
   * JS で組み立てた内容を送る（見積もり・LP用）。
   * fields: { 'お名前': '...', email: '...', ... } — 表示順のまま本文の表になる。
   * email キーにメールアドレスがあれば、返信先と自動返信の宛先になる。
   */
  function send(subject, fields) {
    if ('email' in fields && !EMAIL_RE.test(fields.email || '')) delete fields.email;
    logToSheet(subject, fields);
    var form = document.createElement('form');
    form.method = 'POST';
    form.action = ENDPOINT;
    form.style.display = 'none';
    addControls(form, subject);
    Object.keys(fields).forEach(function (k) { addHidden(form, k, fields[k]); });
    document.body.appendChild(form);
    form.submit();
  }

  /*
   * 既存の HTML フォーム（<form data-inquiry="件名">）に送信設定を付ける。
   * フォームの name 属性がそのまま本文の項目名になる。
   */
  function bindForms() {
    document.querySelectorAll('form[data-inquiry]').forEach(function (form) {
      form.action = ENDPOINT;
      form.method = 'POST';
      addControls(form, form.getAttribute('data-inquiry'));
      form.addEventListener('submit', function () {
        if (form._honey && form._honey.value) return; // スパム（おとり欄に入力あり）は記録しない
        var fields = {};
        new FormData(form).forEach(function (v, k) { if (k.charAt(0) !== '_') fields[k] = v; });
        logToSheet(form.getAttribute('data-inquiry'), fields);
      });
    });
  }

  window.PHInquiry = { send: send, lang: lang };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bindForms);
  else bindForms();
})();
