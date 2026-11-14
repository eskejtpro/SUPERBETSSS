(() => {
  const clean = value => (value || '').replace(/\s+/g, ' ').trim();
  const parseFormat = text => { const m = text.match(/2\s*[x×]\s*(\d+)\s*minut/i); return m ? Number(m[1]) * 2 : null; };
  const contextFor = anchor => {
    let node = anchor;
    for (let level = 0; level < 5 && node; level++, node = node.parentElement) for (let previous = node.previousElementSibling; previous; previous = previous.previousElementSibling) {
      const text = clean(previous.innerText), format = parseFormat(text); if (format || /league|liga|battle|h2h/i.test(text)) return {text: text.slice(0, 100), format};
    }
    return {text: 'e-Piłka nożna live', format: null};
  };
  const read = () => [...document.querySelectorAll('a[href*="/kursy/e-pilka-nozna/"]')].map(anchor => {
    const raw = clean(anchor.innerText), lines = (anchor.innerText || '').split('\n').map(clean).filter(Boolean), half = raw.match(/([12])\.\s*Połowa/i), clock = raw.match(/\b(\d+)(?:\+(\d+))?'/), marker = lines.findIndex(line => line === '1P');
    const candidates = (marker > 1 ? lines.slice(0, marker) : lines).filter(line => !/połowa/i.test(line) && !/^\d+(?:\+\d+)?'$/.test(line) && !/^[\W_]+$/u.test(line));
    const scores = marker >= 0 ? lines.slice(marker + 1).filter(line => /^\d+$/.test(line)).slice(0, 2) : [], context = contextFor(anchor);
    return {url: anchor.href, home: candidates.at(-2) || '', away: candidates.at(-1) || '', homeScore: scores[0] ?? null, awayScore: scores[1] ?? null, half: half ? Number(half[1]) : null, clock: clock ? Number(clock[1]) * 60 + Number(clock[2] || 0) : null, clockLabel: clock ? clock[0] : '', competition: context.text, formatMinutes: context.format, status: /powróci wkrótce/i.test(raw) ? 'oferta wstrzymana' : 'aktywny'};
  }).filter(match => match.home && match.away);
  const publish = () => chrome.runtime.sendMessage({type: 'live-fifa-snapshot', matches: read()});
  publish(); setInterval(publish, 20_000);
})();
