chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== 'live-fifa-snapshot' || !Array.isArray(message.matches)) return;
  fetch('http://127.0.0.1:8765/snapshot', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({matches: message.matches}),
  })
    .then(response => chrome.storage.local.set({bridgeStatus: response.ok ? 'Połączono' : `Błąd HTTP ${response.status}`, bridgeUpdatedAt: new Date().toISOString()}))
    .catch(error => chrome.storage.local.set({bridgeStatus: `Błąd połączenia: ${error.message}`, bridgeUpdatedAt: new Date().toISOString()}));
  sendResponse({queued: true});
  return true;
});
