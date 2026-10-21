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
  var NEXT = 'https://parkhomes-okinawa.com/contact/thanks.html';
  // 例: 'https://script.google.com/macros/s/XXXXXXXX/exec'（空のときは記録しない）
  var SHEET_URL = '';
  var AUTORESPONSE =
    'このたびはパークホームズオキナワへお問い合わせいただき、ありがとうございます。\n' +
    '内容を確認のうえ、担当者より2営業日以内にご連絡いたします。\n\n' +
    'お急ぎの場合は、お電話（098-856-6666／平日 9:00–18:00）または\n' +
    'LINE（ID：@612soivj）でもご相談いただけます。\n\n' +
    'パークホームズオキナワ　https://parkhomes-okinawa.com/';

  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

  // スプレッドシートへの記録。失敗してもメール送信は止めない。
  function logToSheet(subject, fields) {
    if (!SHEET_URL) return;
    try {
      var payload = JSON.stringify({ subject: subject, page: location.pathname, fields: fields });
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
    addHidden(form, '_subject', subject);
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

  window.PHInquiry = { send: send };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bindForms);
  else bindForms();
})();
