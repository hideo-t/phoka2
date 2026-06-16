/*
 * prices.js — 価格の単一ソース読み込みローダー（依存なし）
 *
 * data/prices.json を取得し、data-price="modelId.field" 属性を持つ
 * 全要素にテキストを差し込みます。
 *   例: data-price="casa.body"  → models.casa.body
 *       data-price="ranges.lineupOverall" → ranges.lineupOverall
 *
 * fetch パスはこのスクリプトの <script src> から導出するため、
 * ルート直下(index.html)でも pages/ 配下でも、また GitHub Pages の
 * プロジェクトサブパス(/phoka2/)でも正しく解決されます。
 * 取得に失敗した場合は何もせず、HTML内のフォールバックテキストを残します。
 */
(function () {
  'use strict';

  // このスクリプト自身の URL を取得（src から base を導出）
  function getSelfSrc() {
    if (document.currentScript && document.currentScript.src) {
      return document.currentScript.src;
    }
    var scripts = document.getElementsByTagName('script');
    for (var i = scripts.length - 1; i >= 0; i--) {
      if (scripts[i].src && /\/prices\.js(\?|$)/.test(scripts[i].src)) {
        return scripts[i].src;
      }
    }
    return null;
  }

  // assets/js/prices.js → ../../data/prices.json を絶対URLで解決
  function resolveJsonUrl(selfSrc) {
    if (!selfSrc) return null;
    try {
      // selfSrc は .../assets/js/prices.js（絶対URL）
      // data/prices.json はサイトルート基準: assets の親 = サイトルート
      return new URL('../../data/prices.json', selfSrc).href;
    } catch (e) {
      return null;
    }
  }

  // "a.b.c" のパスでネストされた値を取り出す
  function digPath(obj, parts) {
    var cur = obj;
    for (var i = 0; i < parts.length; i++) {
      if (cur == null || typeof cur !== 'object') return undefined;
      cur = cur[parts[i]];
    }
    return cur;
  }

  // data-price のキーを解決する。
  //   "ranges.lineupOverall" のようにトップレベル直下を指す場合はそのまま。
  //   "casa.body" のようにモデルID始まりの場合は models 配下を探す。
  function dig(data, path) {
    var parts = path.split('.');
    // まずトップレベルから解決
    var direct = digPath(data, parts);
    if (direct !== undefined) return direct;
    // 見つからなければ models.<modelId>.<field> として解決
    if (data && data.models) {
      return digPath(data.models, parts);
    }
    return undefined;
  }

  function applyPrices(data) {
    var nodes = document.querySelectorAll('[data-price]');
    for (var i = 0; i < nodes.length; i++) {
      var key = nodes[i].getAttribute('data-price');
      if (!key) continue;
      var val = dig(data, key);
      // 値が文字列で空でない場合のみ差し込む（空ならフォールバックを残す）
      if (typeof val === 'string' && val !== '') {
        nodes[i].textContent = val;
      }
    }
  }

  function init() {
    var url = resolveJsonUrl(getSelfSrc());
    if (!url || typeof fetch !== 'function') return;
    fetch(url, { cache: 'no-cache' })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        applyPrices(data);
      })
      .catch(function () {
        // 取得失敗時は何もしない（HTML内のフォールバックを表示したまま）
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
