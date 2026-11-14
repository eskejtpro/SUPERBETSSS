const status = document.querySelector('#status');
const button = document.querySelector('#scanAllBtn');
chrome.storage.local.get(['bridgeStatus', 'bridgeUpdatedAt'], ({bridgeStatus, bridgeUpdatedAt}) => {
  status.textContent = bridgeStatus ? `${bridgeStatus}${bridgeUpdatedAt ? ` · ${new Date(bridgeUpdatedAt).toLocaleTimeString()}` : ''}` : 'Oczekiwanie na kartę Superbet LIVE…';
});
button.addEventListener('click', async () => {
  button.disabled = true; status.textContent = 'Uruchamiam skanowanie…';
  try {
    const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
    if (!tab?.id) throw new Error('Nie znaleziono aktywnej karty.');
    const result = await chrome.tabs.sendMessage(tab.id, {type: 'live-fifa-scan-all'});
    if (!result?.ok) throw new Error(result?.message || 'Nie udało się rozpocząć skanowania.');
    status.textContent = `Gotowe: ${result.count} meczów LIVE zebranych w ${result.steps} etapach.`;
  } catch (error) { status.textContent = `Błąd: ${error.message}. Otwórz stronę Superbet e-piłka nożna LIVE i spróbuj ponownie.`; }
  finally { button.disabled = false; }
});