(function(){
  function el(q){ return document.querySelector(q); }
  function create(tag, cls, text){ var e=document.createElement(tag); if(cls) e.className=cls; if(text) e.textContent=text; return e; }

  function getCookie(name) {
    var v = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
  }

  document.addEventListener('DOMContentLoaded', function(){
    var toggle = el('#chatbot-toggle');
    var win = el('#chatbot-window');
    var messages = el('#chatbot-messages');
    var input = el('#chatbot-input');
    var send = el('#chatbot-send');
    var topics = el('#chatbot-topics');
    var employeeSelect = el('#chatbot-employee');
    var employeeLabel = el('.chatbot-employee-label');
    var dateInput = el('#chatbot-date');
    var dateContainer = el('.chatbot-date-container');
    var hints = el('#chatbot-hints');
  var statusLine = el('#chatbot-status');
  var modeLabel = el('#chatbot-mode-label');

  var chatbotMode = 'faq';
  var hrRefreshTimer = null;
  var statusDefaultFaq = 'Assistant data RH prêt : solde congés, paie, absences…';
  var statusDefaultHr = 'Discutez en direct avec le service RH.';

    function toggleHints(show){
      if(!hints) return;
      hints.style.display = show ? 'block' : 'none';
    }

    function setMode(mode, message, force){
      chatbotMode = mode;
      if(modeLabel){
        modeLabel.textContent = mode === 'hr' ? 'Service RH connecté' : 'Assistant data RH';
      }
      if(statusLine && (force || !statusLine.dataset.dynamic)){
        statusLine.textContent = message || (mode === 'hr' ? statusDefaultHr : statusDefaultFaq);
        statusLine.dataset.dynamic = '';
      }
      if(mode === 'hr'){
        if(topics) topics.style.display = 'none';
        if(dateContainer) dateContainer.style.display = 'none';
        if(employeeLabel) employeeLabel.textContent = 'Destinataire RH';
        toggleHints(false);
      } else {
        if(topics) topics.style.display = 'block';
        if(dateContainer) dateContainer.style.display = 'block';
        if(employeeLabel) employeeLabel.textContent = 'Pour quel employé ?';
        toggleHints(true);
      }
    }

    function htmlEscape(str){
      return (str === undefined || str === null ? '' : String(str)).replace(/[&<>"']/g, function(ch){
        return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[ch]);
      });
    }

    function summarizeArray(arr){
      if(!Array.isArray(arr) || !arr.length) return '';
      return arr.slice(0, 3).map(function(item){
        if(item && typeof item === 'object'){
          if(item.name && item.total !== undefined) return item.name + ' (' + item.total + ')';
          if(item.employee && item.date_end) return item.employee + ' → ' + item.date_end;
          if(item.employee && item.start_date) return item.employee + ' (' + item.start_date + ')';
          if(item.title) return item.title;
          return JSON.stringify(item);
        }
        return item;
      }).join(', ');
    }

    function renderInsights(payload){
      if(!statusLine){ if(!payload) toggleHints(true); return; }
      if(payload && (payload.insights || payload.data)){
        statusLine.dataset.dynamic = '1';
      } else {
        statusLine.dataset.dynamic = '';
      }
      if(payload && payload.insights && payload.insights.length){
        var html = '<ul class="chatbot-insights">';
        payload.insights.forEach(function(line){ html += '<li>' + htmlEscape(line) + '</li>'; });
        html += '</ul>';
        statusLine.innerHTML = html;
        toggleHints(false);
        return;
      }
      if(payload && payload.data){
        if(Array.isArray(payload.data)){
          statusLine.innerHTML = '<pre class="chatbot-insights">' + htmlEscape(JSON.stringify(payload.data.slice(0, 3), null, 2)) + '</pre>';
        } else {
          var entries = Object.entries(payload.data).slice(0, 5);
          var htmlList = '<ul class="chatbot-insights">';
          entries.forEach(function(entry){
            var key = entry[0].replace(/_/g, ' ');
            var value = entry[1];
            if(Array.isArray(value)){
              value = summarizeArray(value);
            } else if(value && typeof value === 'object'){
              value = JSON.stringify(value);
            }
            htmlList += '<li><strong>' + htmlEscape(key) + ':</strong> ' + htmlEscape(value) + '</li>';
          });
          htmlList += '</ul>';
          statusLine.innerHTML = htmlList;
        }
        toggleHints(false);
        return;
      }
      setMode(chatbotMode, null, true);
      if(chatbotMode === 'faq') toggleHints(true);
    }

    function appendMessage(text, who){
      if(!messages) return;
      var row = create('div','chatbot-msg '+(who==='user'?'user':'bot'));
      var bubble = create('div','bubble');
      bubble.textContent = text;
      row.appendChild(bubble);
      messages.appendChild(row);
      messages.scrollTop = messages.scrollHeight;
    }

    function renderHrInbox(list){
      if(!messages) return;
      messages.innerHTML = '';
      if(!list || !list.length){
        appendMessage('Aucune réponse RH pour le moment.', 'bot');
        return;
      }
      list.slice().reverse().forEach(function(msg){
        var sender = msg.sender || 'RH';
        var ts = msg.created_at ? new Date(msg.created_at).toLocaleString() : '';
        var subject = msg.subject ? msg.subject + ' — ' : '';
        var body = msg.body || '';
        appendMessage('[' + sender + ' • ' + ts + '] ' + subject + body, 'bot');
      });
    }

    function loadHrInbox(){
      return fetch('/api/messages/inbox/', { credentials: 'same-origin' })
        .then(function(res){
          if(!res.ok) throw new Error('Impossible de récupérer les réponses RH.');
          return res.json();
        })
        .then(function(data){
          renderHrInbox((data && data.messages) || []);
          if(statusLine){
            statusLine.dataset.dynamic = '';
            statusLine.textContent = 'Dernière mise à jour : ' + new Date().toLocaleTimeString();
          }
        })
        .catch(function(err){
          if(statusLine){
            statusLine.dataset.dynamic = '';
            statusLine.textContent = err.message || 'Messagerie RH indisponible.';
          }
        });
    }

    function populateRecipients(recipients){
      if(!employeeSelect) return;
      employeeSelect.innerHTML = '';
      recipients.forEach(function(r, idx){
        var option = document.createElement('option');
        option.value = r.id;
        option.textContent = r.name + (r.function ? ' — ' + r.function : '');
        if(idx === 0) option.selected = true;
        employeeSelect.appendChild(option);
      });
    }

    function enableHrMode(){
      return fetch('/api/messages/recipients/', { credentials: 'same-origin' })
        .then(function(res){
          if(res.status === 401 || res.status === 403){
            throw new Error('Connectez-vous pour discuter directement avec le service RH.');
          }
          if(!res.ok){
            throw new Error('Messagerie RH momentanément indisponible.');
          }
          return res.json();
        })
        .then(function(data){
          if(!data.recipients || !data.recipients.length){
            throw new Error('Aucun contact RH n\'est configuré.');
          }
          populateRecipients(data.recipients);
          setMode('hr', data.help_text || 'Discutez directement avec le service RH.', true);
          renderInsights(null);
          loadHrInbox();
          if(hrRefreshTimer) clearInterval(hrRefreshTimer);
          hrRefreshTimer = setInterval(loadHrInbox, 60000);
        });
    }

    function loadFaqTopics(){
      if(!topics) return;
      topics.innerHTML = '';
      fetch('/api/chatbot/', { credentials: 'same-origin' })
        .then(function(r){ return r.json(); })
        .then(function(data){
          var list = data.topics || [];
          if(!list.length){
            var empty = create('span','topic disabled','Aucun sujet prédéfini.');
            topics.appendChild(empty);
            if(statusLine && !statusLine.dataset.dynamic){
              statusLine.textContent = statusDefaultFaq;
            }
            return;
          }
          list.forEach(function(t){
            var b = create('span','topic', t);
            b.addEventListener('click', function(){ sendQuestion(t); });
            topics.appendChild(b);
          });
          if(statusLine && !statusLine.dataset.dynamic){
            statusLine.textContent = 'Sélectionnez un sujet ou posez votre question.';
          }
        })
        .catch(function(){
          var fail = create('span','topic disabled','Impossible de charger les sujets FAQ.');
          topics.appendChild(fail);
          if(statusLine){
            statusLine.dataset.dynamic = '';
            statusLine.textContent = 'Impossible de charger les sujets FAQ.';
          }
        });
    }

    function sendHrMessage(text){
      if(!employeeSelect || !employeeSelect.value){
        appendMessage('Aucun destinataire RH disponible.', 'bot');
        return;
      }
      appendMessage(text, 'user');
      input.value = '';
      renderInsights(null);
      if(statusLine) statusLine.textContent = 'Envoi au service RH…';
      var payload = {
        recipient: employeeSelect.value,
        subject: 'Chat RH — ' + new Date().toLocaleDateString(),
        body: text
      };
      var headers = { 'Content-Type': 'application/json' };
      var csrftoken = getCookie('csrftoken') || getCookie('CSRF_COOKIE') || '';
      if(csrftoken) headers['X-CSRFToken'] = csrftoken;
      fetch('/api/messages/send/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: headers,
        body: JSON.stringify(payload)
      }).then(function(res){
        if(!res.ok){
          return res.json().then(function(err){ throw new Error(err.error || 'Envoi impossible.'); }).catch(function(){ throw new Error('Envoi impossible.'); });
        }
      }).then(function(){
        appendMessage('Votre demande a été transmise au service RH.', 'bot');
        if(statusLine) statusLine.textContent = 'Message envoyé — en attente de réponse.';
        loadHrInbox();
      }).catch(function(err){
        appendMessage(err.message || 'Erreur côté serveur.', 'bot');
        if(statusLine) statusLine.textContent = err.message || 'Impossible d\'envoyer le message.';
      });
    }

    function sendFaqQuestion(text){
      appendMessage(text, 'user');
      input.value = '';
      if(statusLine){
        statusLine.dataset.dynamic = '';
        statusLine.textContent = 'Analyse des données RH…';
      }
      var payload = { question: text };
      try {
        var emp = employeeSelect && employeeSelect.value ? employeeSelect.value : null;
        if(emp) payload.employee_id = emp;
        var d = dateInput && dateInput.value ? dateInput.value : null;
        if(d) payload.date = d;
      } catch(e) {}
      var headers = { 'Content-Type': 'application/json' };
      var csrftoken = getCookie('csrftoken') || getCookie('CSRF_COOKIE') || '';
      if(csrftoken) headers['X-CSRFToken'] = csrftoken;
      fetch('/api/chatbot/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: headers,
        body: JSON.stringify(payload)
      }).then(function(r){ return r.json(); }).then(function(data){
        appendMessage(data.answer || 'Désolé, pas de réponse.', 'bot');
        renderInsights(data);
      }).catch(function(){
        appendMessage('Erreur de communication avec le serveur.', 'bot');
        renderInsights(null);
      });
    }

    function sendQuestion(value){
      var q = (value || '').trim();
      if(!q) return;
      if(chatbotMode === 'hr'){
        sendHrMessage(q);
      } else {
        sendFaqQuestion(q);
      }
    }

    if(toggle && win){
      toggle.addEventListener('click', function(){
        if(win.style.display === 'block'){
          win.style.display = 'none';
          toggle.textContent = 'Chat RH';
        } else {
          win.style.display = 'block';
          toggle.textContent = 'Fermer';
        }
      });
    }

    if(send){
      send.addEventListener('click', function(){ sendQuestion(input.value); });
    }
    if(input){
      input.addEventListener('keydown', function(e){ if(e.key === 'Enter'){ e.preventDefault(); sendQuestion(input.value); } });
    }

    enableHrMode().catch(function(err){
      setMode('faq', err && err.message ? err.message : null, true);
      renderInsights(null);
      loadFaqTopics();
    });
  });
})();
