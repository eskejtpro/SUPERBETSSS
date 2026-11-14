(() => {
  const clean = value => (value || '').replace(/\s+/g, ' ').trim();
  const parseFormat = text => { const m = text.match(/2\s*[x×]\s*(\d+)\s*minut/i); return m ? Number(m[1]) * 2 : null; };
  const contextFor = anchor => {
    let node = anchor;
    for (let level = 0; level < 5 && node; level++, node = node.parentElement) for (let previous = node.previousElementSibling; previous; previous = previous.previousElementSibling) {
      const text = clean(previous.innerText), format = parseFormat(text);
      if (format || /league|liga|battle|h2h|turniej|rozgrywki/i.test(text)) return {text: text.slice(0, 100), format};
    }
    return {text: 'e-Piłka nożna live', format: null};
  };
  const discovered = new Map();
  const readVisible = () => [...document.querySelectorAll('a[href*="/kursy/e-pilka-nozna/"]')].map(anchor => {
    const raw = clean(anchor.innerText), lines = (anchor.innerText || '').split('\n').map(clean).filter(Boolean);
    const half = raw.match(/([12])\.\s*Połowa/i), clock = raw.match(/\b(\d+)(?:\+(\d+))?'/);
    const marker = lines.findIndex(line => line === '1P');
    const candidates = (marker > 1 ? lines.slice(0, marker) : lines).filter(line => !/połowa/i.test(line) && !/^\d+(?:\+\d+)?'$/.test(line) && !/^[\W_]+$/u.test(line));
    const scores = marker >= 0 ? lines.slice(marker + 1).filter(line => /^\d+$/.test(line)).slice(0, 2) : [];
    const context = contextFor(anchor);
    return {url: anchor.href, home: candidates.at(-2) || '', away: candidates.at(-1) || '', homeScore: scores[0] ?? null, awayScore: scores[1] ?? null, half: half ? Number(half[1]) : null, clock: clock ? Number(clock[1]) * 60 + Number(clock[2] || 0) : null, clockLabel: clock ? clock[0] : '', competition: context.text, formatMinutes: context.format, isLive: Boolean(half && clock), status: /powróci wkrótce/i.test(raw) ? 'oferta wstrzymana' : 'aktywny'};
  }).filter(match => match.home && match.away && match.isLive);
  const collect = () => { for (const match of readVisible()) discovered.set(match.url || match.home + '|' + match.away, match); return [...discovered.values()]; };
  const publish = () => { const matches = collect(); chrome.runtime.sendMessage({type: 'live-fifa-snapshot', matches, scanCount: matches.length}); };
  let scanning = false;
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const scanAll = async () => {
    if (scanning) return {ok: false, message: 'Skanowanie już trwa'};
    scanning = true;
    const scroller = document.scrollingElement || document.documentElement;
    const originalTop = window.scrollY;
    let stablePasses = 0, steps = 0, previousHeight = scroller.scrollHeight, lastTop = -1;
    try {
      chrome.runtime.sendMessage({type: 'live-fifa-scan-status', status: 'Skanowanie wszystkich sekcji…'});
      while (steps < 120 && stablePasses < 4) {
        const maxTop = Math.max(0, scroller.scrollHeight - window.innerHeight);
        const nextTop = Math.min(maxTop, Math.max(0, lastTop) + Math.max(350, Math.floor(window.innerHeight * 0.72)));
        window.scrollTo(0, nextTop);
        await sleep(450);
        collect(); steps += 1;
        const height = scroller.scrollHeight;
        if (height === previousHeight && nextTop >= maxTop) stablePasses += 1; else stablePasses = 0;
        previousHeight = height; lastTop = nextTop;
        if (nextTop >= maxTop && stablePasses < 4) await sleep(500);
      }
      publish();
      chrome.runtime.sendMessage({type: 'live-fifa-scan-status', status: `Skan zakończony: ${discovered.size} meczów · ${steps} etapów`});
      return {ok: true, count: discovered.size, steps};
    } finally { window.scrollTo(0, originalTop); scanning = false; }
  };
  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === 'live-fifa-scan-all') { scanAll().then(sendResponse).catch(error => sendResponse({ok: false, message: error.message})); return true; }
  });
  publish();
  setInterval(() => { if (!scanning) publish(); }, 20_000);
})();