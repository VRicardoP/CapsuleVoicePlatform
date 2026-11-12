/**
 * CapsuleCorp WhatsApp Widget
 * Embeddable chat button that opens WhatsApp conversation.
 *
 * Usage:
 * <script src="https://yourdomain.com/widget.js"
 *   data-tenant="uuid" data-color="#25D366" data-position="bottom-right"></script>
 */
(function() {
  'use strict';

  var script = document.currentScript;
  if (!script) return;

  var tenant = script.getAttribute('data-tenant');
  var color = script.getAttribute('data-color') || '#25D366';
  var position = script.getAttribute('data-position') || 'bottom-right';
  var phone = script.getAttribute('data-phone') || '';
  var welcome = script.getAttribute('data-welcome') || 'Hola! ¿En qué podemos ayudarte?';
  var name = script.getAttribute('data-name') || '';
  var autoOpen = parseInt(script.getAttribute('data-auto-open') || '0', 10);

  // WhatsApp icon SVG
  var waIcon = '<svg width="28" height="28" fill="white" viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/></svg>';
  var closeIcon = '<svg width="20" height="20" fill="white" viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>';

  // Position styles
  var isRight = position === 'bottom-right';
  var posStyle = isRight ? 'right:20px' : 'left:20px';

  // Create styles
  var style = document.createElement('style');
  style.textContent = [
    '.sai-wa-btn{position:fixed;bottom:20px;' + posStyle + ';z-index:999999;width:56px;height:56px;border-radius:50%;border:none;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.3);display:flex;align-items:center;justify-content:center;transition:transform .2s}',
    '.sai-wa-btn:hover{transform:scale(1.1)}',
    '.sai-wa-popup{position:fixed;bottom:88px;' + posStyle + ';z-index:999998;width:320px;background:#fff;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,.2);overflow:hidden;display:none;animation:sai-slide .3s ease}',
    '.sai-wa-popup.open{display:block}',
    '@keyframes sai-slide{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}',
    '.sai-wa-header{padding:16px;color:#fff;display:flex;align-items:center;gap:10px}',
    '.sai-wa-header-info{flex:1}',
    '.sai-wa-header h3{margin:0;font-size:14px;font-weight:600}',
    '.sai-wa-header p{margin:2px 0 0;font-size:11px;opacity:.8}',
    '.sai-wa-body{padding:16px;background:#e5ddd5;min-height:80px}',
    '.sai-wa-bubble{background:#fff;padding:8px 12px;border-radius:0 8px 8px 8px;font-size:13px;line-height:1.4;max-width:80%;box-shadow:0 1px 1px rgba(0,0,0,.1);color:#333}',
    '.sai-wa-footer{padding:12px 16px;background:#f0f0f0;display:flex;gap:8px}',
    '.sai-wa-input{flex:1;border:1px solid #ddd;border-radius:20px;padding:8px 14px;font-size:13px;outline:none}',
    '.sai-wa-input:focus{border-color:' + color + '}',
    '.sai-wa-send{background:' + color + ';border:none;border-radius:50%;width:36px;height:36px;cursor:pointer;display:flex;align-items:center;justify-content:center}',
    '.sai-wa-close{background:none;border:none;cursor:pointer;padding:4px;opacity:.8}',
    '.sai-wa-close:hover{opacity:1}',
  ].join('');
  document.head.appendChild(style);

  // Create popup
  var popup = document.createElement('div');
  popup.className = 'sai-wa-popup';
  popup.innerHTML = [
    '<div class="sai-wa-header" style="background:' + color + '">',
    '  <div style="width:40px;height:40px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center">' + waIcon.replace('width="28"', 'width="22"').replace('height="28"', 'height="22"') + '</div>',
    '  <div class="sai-wa-header-info">',
    '    <h3>' + (name || 'WhatsApp') + '</h3>',
    '    <p>Normalmente responde en minutos</p>',
    '  </div>',
    '  <button class="sai-wa-close" onclick="document.querySelector(\'.sai-wa-popup\').classList.remove(\'open\')">' + closeIcon + '</button>',
    '</div>',
    '<div class="sai-wa-body">',
    '  <div class="sai-wa-bubble">' + welcome + '</div>',
    '</div>',
    '<div class="sai-wa-footer">',
    '  <input class="sai-wa-input" placeholder="Escribe un mensaje..." id="sai-wa-msg">',
    '  <button class="sai-wa-send" id="sai-wa-send-btn"><svg width="18" height="18" fill="white" viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg></button>',
    '</div>',
  ].join('');
  document.body.appendChild(popup);

  // Create button
  var btn = document.createElement('button');
  btn.className = 'sai-wa-btn';
  btn.style.background = color;
  btn.innerHTML = waIcon;
  btn.onclick = function() {
    popup.classList.toggle('open');
  };
  document.body.appendChild(btn);

  // Send button → opens WhatsApp Web/app with prefilled message
  var sendBtn = document.getElementById('sai-wa-send-btn');
  var msgInput = document.getElementById('sai-wa-msg');
  if (sendBtn && msgInput) {
    sendBtn.onclick = function() {
      var text = msgInput.value.trim();
      if (!text) return;
      var url = 'https://wa.me/' + phone.replace(/[^0-9]/g, '') + '?text=' + encodeURIComponent(text);
      window.open(url, '_blank');
      msgInput.value = '';
      popup.classList.remove('open');
    };
    msgInput.addEventListener('keypress', function(e) {
      if (e.key === 'Enter') sendBtn.click();
    });
  }

  // Auto-open
  if (autoOpen > 0) {
    setTimeout(function() {
      popup.classList.add('open');
    }, autoOpen * 1000);
  }
})();
