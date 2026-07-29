/* CloudTech Feedback Widget — Floating feedback button */
(function() {
  if (document.getElementById('ct-feedback-widget')) return;

  var css = `
#ct-feedback-widget { position:fixed; bottom:24px; right:24px; z-index:9999; font-family:-apple-system,"Microsoft YaHei",sans-serif; }
#ct-feedback-btn { width:48px; height:48px; background:#6c5ce7; color:#fff; border:none; border-radius:50%; font-size:1.4rem; cursor:pointer; box-shadow:0 4px 20px rgba(108,92,231,.4); transition:all .2s; display:flex; align-items:center; justify-content:center; }
#ct-feedback-btn:hover { transform:scale(1.1); }
#ct-feedback-panel { display:none; position:absolute; bottom:60px; right:0; width:320px; background:#111118; border:1px solid #1e1e2a; border-radius:12px; padding:20px; box-shadow:0 8px 40px rgba(0,0,0,.5); }
#ct-feedback-panel.open { display:block; }
#ct-feedback-panel h3 { font-size:0.95rem; color:#e0e0e0; margin-bottom:4px; }
#ct-feedback-panel .sub { font-size:0.75rem; color:#777; margin-bottom:16px; }
#ct-feedback-panel textarea { width:100%; height:80px; background:#0a0a0f; border:1px solid #1e1e2a; border-radius:8px; color:#e0e0e0; padding:10px; font-size:0.85rem; resize:none; margin-bottom:12px; outline:none; }
#ct-feedback-panel textarea:focus { border-color:#6c5ce7; }
#ct-feedback-panel .row { display:flex; gap:8px; margin-bottom:12px; }
#ct-feedback-panel .tag { padding:4px 12px; border-radius:12px; font-size:0.75rem; cursor:pointer; border:1px solid #1e1e2a; color:#999; background:transparent; }
#ct-feedback-panel .tag.active { background:rgba(108,92,231,.15); border-color:#6c5ce7; color:#a78bfa; }
#ct-feedback-panel .submit { width:100%; padding:10px; background:#6c5ce7; color:#fff; border:none; border-radius:8px; font-size:0.85rem; cursor:pointer; }
#ct-feedback-panel .submit:disabled { opacity:0.5; }
#ct-feedback-panel .thanks { text-align:center; color:#00c853; padding:20px 0; display:none; font-size:0.9rem; }
#ct-feedback-close { position:absolute; top:12px; right:12px; background:none; border:none; color:#777; cursor:pointer; font-size:1.1rem; }
`;

  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  var html = `
<div id="ct-feedback-widget">
  <button id="ct-feedback-btn" title="反馈">💬</button>
  <div id="ct-feedback-panel">
    <button id="ct-feedback-close">✕</button>
    <h3>帮助我们做得更好</h3>
    <p class="sub">遇到问题？有新想法？告诉我们</p>
    <div class="row" id="ct-tags">
      <button class="tag active" data-cat="bug">🐛 报Bug</button>
      <button class="tag" data-cat="feature">💡 提建议</button>
      <button class="tag" data-cat="other">💬 其他</button>
    </div>
    <textarea id="ct-msg" placeholder="请描述你的问题或建议..."></textarea>
    <button class="submit" id="ct-submit">发送反馈</button>
    <div class="thanks" id="ct-thanks">✅ 感谢你的反馈！</div>
  </div>
</div>`;

  var div = document.createElement('div');
  div.innerHTML = html;
  document.body.appendChild(div);

  var cat = 'bug';
  document.getElementById('ct-feedback-btn').onclick = function() {
    document.getElementById('ct-feedback-panel').classList.toggle('open');
  };
  document.getElementById('ct-feedback-close').onclick = function() {
    document.getElementById('ct-feedback-panel').classList.remove('open');
  };
  document.getElementById('ct-tags').onclick = function(e) {
    if (e.target.classList.contains('tag')) {
      document.querySelectorAll('#ct-tags .tag').forEach(function(t) { t.classList.remove('active'); });
      e.target.classList.add('active');
      cat = e.target.dataset.cat;
    }
  };
  document.getElementById('ct-submit').onclick = async function() {
    var msg = document.getElementById('ct-msg').value.trim();
    if (!msg) return;
    var btn = document.getElementById('ct-submit');
    btn.disabled = true; btn.textContent = '发送中...';
    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          user_id: (JSON.parse(localStorage.getItem('cloudtech_user')||'{}')).id || 'anonymous',
          category: cat, message: msg, url: location.href
        })
      });
      document.getElementById('ct-thanks').style.display = 'block';
      document.getElementById('ct-msg').style.display = 'none';
      document.getElementById('ct-tags').style.display = 'none';
      btn.style.display = 'none';
      setTimeout(function() {
        document.getElementById('ct-feedback-panel').classList.remove('open');
        document.getElementById('ct-thanks').style.display = 'none';
        document.getElementById('ct-msg').style.display = '';
        document.getElementById('ct-tags').style.display = '';
        btn.style.display = ''; btn.disabled = false; btn.textContent = '发送反馈';
        document.getElementById('ct-msg').value = '';
      }, 2000);
    } catch(e) {
      btn.disabled = false; btn.textContent = '发送失败，重试';
    }
  };
})();
