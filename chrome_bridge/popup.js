const status = document.querySelector('#status');
chrome.storage.local.get(['bridgeStatus', 'bridgeUpdatedAt'], ({bridgeStatus, bridgeUpdatedAt}) => {
  status.textContent = bridgeStatus ? `${bridgeStatus}${bridgeUpdatedAt ? ` (${new Date(bridgeUpdatedAt).toLocaleTimeString()})` : ''}` : 'Oczekiwanie na kartę live…';
});
