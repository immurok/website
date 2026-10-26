// Download page: dropdown pickers for the Windows / Linux build variants.
(() => {
  const menus = Array.from(document.querySelectorAll('.dl-menu'));
  if (!menus.length) return;

  const setOpen = (menu, open) => {
    menu.classList.toggle('is-open', open);
    menu.querySelector('.dl-menu-toggle').setAttribute('aria-expanded', String(open));
    menu.closest('.download-card')?.classList.toggle('is-menu-open', open);
  };
  const closeAll = (except) => menus.forEach((m) => { if (m !== except) setOpen(m, false); });

  menus.forEach((menu) => {
    const toggle = menu.querySelector('.dl-menu-toggle');
    const items = Array.from(menu.querySelectorAll('[role="menuitem"]'));

    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const open = !menu.classList.contains('is-open');
      closeAll(menu);
      setOpen(menu, open);
      if (open) items[0]?.focus({ preventScroll: true });
    });

    menu.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        setOpen(menu, false);
        toggle.focus();
        return;
      }
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
      if (!menu.classList.contains('is-open')) return;
      e.preventDefault();
      const i = items.indexOf(document.activeElement);
      const next = e.key === 'ArrowDown' ? (i + 1) % items.length : (i - 1 + items.length) % items.length;
      items[next].focus();
    });

    // Safari does not focus links on click, so closing on focusout would hide
    // the menu between mousedown and click; outside-click + Escape suffice.
    menu.addEventListener('click', (e) => e.stopPropagation());

    // "Copy" rows (Homebrew): copy the command, keep the menu open, show feedback.
    menu.querySelectorAll('.dl-menu-copy').forEach((row) => {
      const hint = row.querySelector('.dl-menu-copy-hint');
      const idle = hint.textContent;
      row.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(row.dataset.copy);
          hint.textContent = 'Copied';
        } catch {
          hint.textContent = 'Select & copy';
        }
        row.classList.add('is-copied');
        setTimeout(() => { hint.textContent = idle; row.classList.remove('is-copied'); }, 1800);
      });
    });
  });

  document.addEventListener('click', () => closeAll());
})();
