/* ============================================================
 * Park Homes Okinawa — アクセス解析
 *
 * ▼ 使い方：下の2行にIDを入れるだけで計測が始まります。
 *   空のままなら何も読み込まないので、ID未発行でも置いたままで安全です。
 *
 *   GA4      … https://analytics.google.com/ → 管理 → データストリーム
 *               「G-」で始まる測定ID
 *   Clarity  … https://clarity.microsoft.com/ → Settings → Setup
 *               「Clarity project id」の英数字
 *
 * ▼ 全67ページがこのファイル1本を読んでいます。
 *   広告タグの追加など、今後の変更はこのファイルだけ直せば全ページに効きます。
 * ============================================================ */

var GA4_ID     = 'G-RHS863EHBQ';   // 例: 'G-XXXXXXXXXX'
var CLARITY_ID = '';   // 例: 'abcd1234ef'

(function () {
  'use strict';

  // 自分のPCでの表示確認まで数えてしまわないよう、本番ドメイン以外では動かさない
  var host = location.hostname;
  var isProduction = /(^|\.)parkhomes-okinawa\.com$/.test(host);
  if (!isProduction) {
    console.log('[analytics] 本番ドメイン外のため計測しません (' + (host || 'file://') + ')');
    return;
  }

  /* ---------- GA4 ---------- */
  if (GA4_ID) {
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(GA4_ID);
    document.head.appendChild(s);

    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    gtag('js', new Date());
    gtag('config', GA4_ID);
  }

  /* ---------- Microsoft Clarity ---------- */
  if (CLARITY_ID) {
    (function (c, l, a, r, i, t, y) {
      c[a] = c[a] || function () { (c[a].q = c[a].q || []).push(arguments); };
      t = l.createElement(r); t.async = 1;
      t.src = 'https://www.clarity.ms/tag/' + i;
      y = l.getElementsByTagName(r)[0]; y.parentNode.insertBefore(t, y);
    })(window, document, 'clarity', 'script', CLARITY_ID);
  }

  /* ---------- コンバージョンのクリック計測 ----------
   * GA4 の自動計測は tel: と mailto: のクリックを拾わない。
   * この会社への問い合わせは電話が主なので、ここは自前で送る。
   */
  function send(name, params) {
    if (typeof window.gtag !== 'function') return;
    params = params || {};
    params.page_path = location.pathname;
    gtag('event', name, params);
  }

  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;

    var href = a.getAttribute('href') || '';
    var label = (a.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60);

    if (/^tel:/i.test(href)) {
      send('contact_tel', { tel_number: href.replace(/^tel:/i, ''), link_text: label });
    } else if (/^mailto:/i.test(href)) {
      send('contact_mail', { link_text: label });
    } else if (/lin\.ee|line\.me/i.test(href)) {
      send('contact_line', { link_text: label });
    } else if (/\.pdf($|\?)/i.test(href)) {
      send('download_pdf', { file_name: href.split('/').pop(), link_text: label });
    }
  }, true);

  /* ---------- 問い合わせフォーム送信 ---------- */
  document.addEventListener('submit', function (e) {
    var f = e.target;
    if (f && f.tagName === 'FORM') {
      send('contact_form_submit', { form_action: f.getAttribute('action') || '' });
    }
  }, true);
})();
