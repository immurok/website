// ── Terminal Typing Animation ──

const scenarios = [
  {
    mode: 'lockscreen',
  },
  {
    mode: 'terminal',
    lines: [
      { type: 'command', text: '$ ssh git@github.com' },
      { type: 'spinner', text: 'immurok: touch to sign...' },
      { type: 'success', text: '✓ Authenticated as User (immurok IK-1)' },
    ],
  },
  {
    mode: 'terminal',
    lines: [
      { type: 'command', text: '$ sudo brew upgrade' },
      { type: 'spinner', text: 'immurok: touch to verify...' },
      { type: 'success', text: '✓ Authenticated' },
    ],
  },
];

const CHAR_DELAY = 45;
const SPINNER_DURATION = 1500;
const SUCCESS_PAUSE = 2000;
const CLEAR_PAUSE = 500;

const spinnerFrames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

class TerminalAnimator {
  constructor(el, fpEl) {
    this.el = el;
    this.fpEl = fpEl;
    this.headerEl = el.previousElementSibling;
    this.containerEl = el.closest('.terminal');
    this.currentScenario = 0;
    this.running = false;
    const styles = getComputedStyle(document.documentElement);
    this.colorWarning = '#eab308';
    this.colorSuccess = styles.getPropertyValue('--green').trim() || '#1faa20';
    this.colorText = '#d1d5db';
  }

  start() {
    if (this.running) return;
    this.running = true;
    this.loop();
  }

  stop() {
    this.running = false;
  }

  async loop() {
    while (this.running) {
      const scenario = scenarios[this.currentScenario];
      await this.playScenario(scenario);
      this.currentScenario = (this.currentScenario + 1) % scenarios.length;
      await this.sleep(CLEAR_PAUSE);
    }
  }

  fpShow() {
    if (this.fpEl) this.fpEl.classList.add('active');
  }

  fpHide() {
    if (this.fpEl) this.fpEl.classList.remove('active');
  }

  async playScenario(scenario) {
    if (scenario.mode === 'lockscreen') {
      return this.playLockscreen();
    }
    return this.playTerminal(scenario);
  }

  showHeader() {
    if (this.headerEl) this.headerEl.style.display = '';
  }

  hideHeader() {
    if (this.headerEl) this.headerEl.style.display = 'none';
  }

  async playTerminal(scenario) {
    this.showHeader();
    this.el.innerHTML = '';
    this.el.style.opacity = '1';

    const cmdLine = this.createLine();
    await this.typeText(cmdLine, scenario.lines[0].text, 'cmd');

    this.fpShow();

    const spinnerLine = this.createLine();
    const spinnerSpan = document.createElement('span');
    spinnerSpan.style.color = this.colorWarning;
    spinnerLine.appendChild(spinnerSpan);

    const spinnerChar = document.createElement('span');
    spinnerChar.textContent = spinnerFrames[0];
    spinnerSpan.appendChild(spinnerChar);

    const spinnerText = document.createTextNode(' ' + scenario.lines[1].text);
    spinnerSpan.appendChild(spinnerText);

    let frame = 0;
    const spinnerInterval = setInterval(() => {
      frame = (frame + 1) % spinnerFrames.length;
      spinnerChar.textContent = spinnerFrames[frame];
    }, 80);

    await this.sleep(SPINNER_DURATION);
    clearInterval(spinnerInterval);

    spinnerLine.remove();
    const successLine = this.createLine();
    const successSpan = document.createElement('span');
    successSpan.style.color = this.colorSuccess;
    successSpan.textContent = scenario.lines[2].text;
    successLine.appendChild(successSpan);

    await this.sleep(SUCCESS_PAUSE);

    this.fpHide();
    this.el.style.opacity = '0';
    await this.sleep(300);
    this.el.innerHTML = '';
  }

  async playLockscreen() {
    this.hideHeader();
    this.el.innerHTML = '';
    this.el.style.opacity = '1';

    const wrapper = document.createElement('div');
    wrapper.className = 'lockscreen-ui';
    wrapper.innerHTML = `
      <div class="ls-avatar">
        <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
        </svg>
      </div>
      <div class="ls-name">User</div>
      <div class="ls-password-row">
        <div class="ls-password-field">
          <div class="ls-dots"></div>
        </div>
      </div>
      <div class="ls-status"></div>
    `;
    this.el.appendChild(wrapper);

    const dots = wrapper.querySelector('.ls-dots');
    const status = wrapper.querySelector('.ls-status');
    const field = wrapper.querySelector('.ls-password-field');

    await this.sleep(800);

    this.fpShow();
    status.textContent = '⠋ Touch immurok to unlock...';
    status.className = 'ls-status ls-status--waiting';

    await this.sleep(SPINNER_DURATION);

    dots.innerHTML = '••••••••';
    status.textContent = '';

    await this.sleep(400);

    field.style.borderColor = this.colorSuccess;
    status.textContent = '✓ Unlocked';
    status.className = 'ls-status ls-status--success';

    await this.sleep(SUCCESS_PAUSE);

    this.fpHide();
    this.el.style.opacity = '0';
    await this.sleep(300);
    this.el.innerHTML = '';
  }

  createLine() {
    const div = document.createElement('div');
    div.style.lineHeight = '1.8';
    this.el.appendChild(div);
    return div;
  }

  async typeText(container, text, cls) {
    const span = document.createElement('span');
    span.style.color = this.colorText;
    container.appendChild(span);

    const cursor = document.createElement('span');
    cursor.className = 'cursor';
    container.appendChild(cursor);

    for (let i = 0; i < text.length; i++) {
      span.textContent += text[i];
      await this.sleep(CHAR_DELAY);
    }

    cursor.remove();
  }

  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

// ── Problem section: auth demo animation ──

const BRAILLE = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'];

const AUTH_SCENES = [
  { type: 'lock' },
  {
    type: 'term',
    cmd: [['$ ', 't-prompt'], ['sudo ', 't-cmd'], ['make install', 't-arg']],
    success: '✓ approved',
  },
  {
    type: 'term',
    cmd: [['$ ', 't-prompt'], ['git ', 't-cmd'], ['push', 't-arg']],
    success: '✓ approved',
    note: '↳ now signing…',
  },
  { type: 'github' },
  { type: 'agent' },
];

// Three-step beat shared by every scene:
//   1. prompt to touch        (PROMPT)
//   2. fingerprint icon shows  (TOUCH)
//   3. success                 (SUCCESS)
const AUTH_PROMPT_MS = 1500;
const AUTH_TOUCH_MS = 1000;
const AUTH_SUCCESS_MS = 500;
const AUTH_FADE_MS = 400;

function cel(tag, cls) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  return e;
}

const USER_SVG =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">' +
  '<path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>';

const FP_SVG =
  '<svg viewBox="0 0 32 32" fill="currentColor" aria-hidden="true">' +
  '<path d="M7,5.21a.77.77,0,0,1-.46-1.38A15.46,15.46,0,0,1,16,1c2.66,0,6.48.45,9.5,2.62a.77.77,0,0,1,.18,1.07.78.78,0,0,1-1.08.17A15,15,0,0,0,16,2.53,14,14,0,0,0,7.5,5.05.74.74,0,0,1,7,5.21Z"/>' +
  '<path d="M28.23,12.26a.78.78,0,0,1-.63-.33C25.87,9.49,22.78,6.24,16,6.24a14,14,0,0,0-11.63,5.7.77.77,0,0,1-1.07.17A.76.76,0,0,1,3.15,11,15.54,15.54,0,0,1,16,4.71c5.61,0,9.81,2.08,12.84,6.34a.77.77,0,0,1-.19,1.07A.79.79,0,0,1,28.23,12.26Z"/>' +
  '<path d="M12.28,31a.78.78,0,0,1-.72-.49.75.75,0,0,1,.44-1c4.37-1.68,7-5.12,7-9.21a2.8,2.8,0,0,0-3-3c-1.86,0-2.76,1-3,3.35a4.27,4.27,0,0,1-4.52,3.83,4.27,4.27,0,0,1-4.32-4.59A11.71,11.71,0,0,1,16,8.39a12,12,0,0,1,12,11.93,18.66,18.66,0,0,1-1.39,6.5.78.78,0,0,1-1,.41.76.76,0,0,1-.41-1,17.25,17.25,0,0,0,1.27-5.91A10.45,10.45,0,0,0,16,9.92a10.18,10.18,0,0,0-10.38,10,2.77,2.77,0,0,0,2.79,3.06,2.74,2.74,0,0,0,3-2.48c.36-3.11,1.89-4.69,4.56-4.69a4.31,4.31,0,0,1,4.52,4.56c0,4.74-3,8.72-8,10.63A.92.92,0,0,1,12.28,31Z"/>' +
  '<path d="M19.77,30.28a.81.81,0,0,1-.52-.2.76.76,0,0,1,0-1.08,12.63,12.63,0,0,0,3.54-8.68c0-1.56-.48-6.65-6.7-6.65a6.83,6.83,0,0,0-4.94,1.87A6.17,6.17,0,0,0,9.32,20a.77.77,0,0,1-.77.76h0A.76.76,0,0,1,7.78,20,7.73,7.73,0,0,1,10,14.46a8.34,8.34,0,0,1,6-2.32c6.08,0,8.24,4.4,8.24,8.18A14.09,14.09,0,0,1,20.34,30,.75.75,0,0,1,19.77,30.28Z"/>' +
  '<path d="M8.66,27.74a14.14,14.14,0,0,1-1.56-.09.76.76,0,1,1,.17-1.52c2.49.28,4.45-.16,5.84-1.32a6.37,6.37,0,0,0,2.12-4.53.75.75,0,0,1,.82-.71.78.78,0,0,1,.72.81A7.89,7.89,0,0,1,14.09,26,8.2,8.2,0,0,1,8.66,27.74Z"/></svg>';

const GITHUB_SVG =
  '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">' +
  '<path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/></svg>';

class AuthDemoAnimator {
  constructor(el) {
    this.el = el;
    this.stage = el.querySelector('.auth-stage');
    this.running = false;      // desired state: visible & should animate
    this.loopRunning = false;  // a loop() is currently executing
    this.timer = null;
  }

  start() {
    this.running = true;
    // Never spawn a second loop. If one is still draining its current
    // scene, just flip `running` back on — it'll keep going on its own.
    if (this.loopRunning) return;
    this.loop();
  }

  stop() {
    this.running = false;
  }

  async loop() {
    this.loopRunning = true;
    while (this.running) {
      for (const scene of AUTH_SCENES) {
        if (!this.running) break;
        if (scene.type === 'lock') await this.playLock();
        else if (scene.type === 'agent') await this.playAgent();
        else if (scene.type === 'github') await this.playGithub();
        else await this.playTerminal(scene);
        if (!this.running) break;
        await this.sleep(300);
      }
    }
    this.loopRunning = false;
  }

  fpShow() { this.el.classList.add('fp-active'); }
  fpHide() { this.el.classList.remove('fp-active'); }

  spin(cb) {
    let f = 0;
    cb(BRAILLE[0]);
    return setInterval(() => {
      f = (f + 1) % BRAILLE.length;
      cb(BRAILLE[f]);
    }, 90);
  }

  async setStage(node) {
    if (this.stage.firstChild) {
      this.stage.classList.add('fading');
      await this.sleep(AUTH_FADE_MS);
    }
    this.stage.innerHTML = '';
    this.stage.appendChild(node);
    this.stage.classList.remove('fading');
    await this.sleep(AUTH_FADE_MS);
  }

  async playTerminal(scene) {
    const term = cel('div', 'auth-term');
    const chrome = cel('div', 'term-chrome');
    chrome.innerHTML = '<span></span><span></span><span></span>';
    const body = cel('div', 'term-body');

    const cmdLine = cel('div', 'term-line');
    scene.cmd.forEach(([text, cls]) => {
      const s = cel('span', cls);
      s.textContent = text;
      cmdLine.appendChild(s);
    });

    const vLine = cel('div', 'term-line');
    const spinEl = cel('span', 't-spin');
    const please = cel('span', 't-please');
    please.textContent = ' Please verify your fingerprint...';
    const cursor = cel('span', 't-cursor');
    vLine.append(spinEl, please, cursor);

    body.append(cmdLine, vLine);
    term.append(chrome, body);
    await this.setStage(term);

    const iv = this.spin((c) => { spinEl.textContent = c; });
    // 1. prompt
    await this.sleep(AUTH_PROMPT_MS);
    // 2. touch
    this.fpShow();
    await this.sleep(AUTH_TOUCH_MS);
    clearInterval(iv);
    this.fpHide();

    // 3. success
    cursor.remove();
    vLine.innerHTML = '';
    const ok = cel('span', 't-ok');
    ok.textContent = scene.success;
    vLine.appendChild(ok);
    if (scene.note) {
      const noteLine = cel('div', 'term-line');
      const n = cel('span', 't-note');
      n.textContent = scene.note;
      noteLine.appendChild(n);
      body.appendChild(noteLine);
    }
    await this.sleep(AUTH_SUCCESS_MS);
  }

  async playLock() {
    const lock = cel('div', 'auth-lock');
    lock.innerHTML =
      '<div class="ls-avatar">' + USER_SVG + '</div>' +
      '<div class="ls-name">User</div>' +
      '<div class="ls-field"><span class="ls-dots"></span></div>' +
      '<div class="ls-status">Touch immurok to unlock…</div>';
    await this.setStage(lock);

    const field = lock.querySelector('.ls-field');
    const dots = lock.querySelector('.ls-dots');
    const status = lock.querySelector('.ls-status');

    const iv = this.spin((c) => { status.textContent = c + ' Touch immurok to unlock…'; });
    // 1. prompt
    await this.sleep(AUTH_PROMPT_MS);
    // 2. touch
    this.fpShow();
    await this.sleep(AUTH_TOUCH_MS);
    clearInterval(iv);
    this.fpHide();

    // 3. success
    dots.textContent = '••••••••';
    field.classList.add('ok');
    status.classList.add('ok');
    status.textContent = '✓ Unlocked';
    await this.sleep(AUTH_SUCCESS_MS);
  }

  async playAgent() {
    const wrap = cel('div', 'auth-agent');
    wrap.innerHTML =
      '<div class="agent-term">' +
        '<div class="term-chrome"><span></span><span></span><span></span></div>' +
        '<div class="cc-body">' +
          '<div class="cc-banner">' +
            '<pre class="cc-mascot"> ▟▛▀█▀▜▙\n▝▜█████▛▘\n  ▘▘ ▝▝</pre>' +
            '<div class="cc-meta">' +
              '<div class="cc-meta-1">AI Agent Code v2.1.160</div>' +
              '<div>Open Model 4.8 (1M context) with high effort</div>' +
              '<div>Project neo</div>' +
            '</div>' +
          '</div>' +
          '<div class="cc-line cc-user-line"><span class="cc-arrow">&gt;</span> deploy the latest build</div>' +
          '<div class="cc-line"><span class="cc-dot">⏺</span> <span class="cc-text">Build succeeded in 12.4s</span></div>' +
          '<div class="cc-line"><span class="cc-dot">⏺</span> <span class="cc-text">All 42 tests passed</span></div>' +
          '<div class="cc-line"><span class="cc-dot cc-dot--live">⏺</span> ' +
            '<span class="cc-text cc-text--cur">Now I will deploy to the production environment, asking for your approve.</span></div>' +
        '</div>' +
      '</div>' +
      '<div class="agent-veil"><div class="agent-dialog">' +
        '<div class="agent-app">AI Agent</div>' +
        '<div class="agent-msg">Wants to run a terminal command</div>' +
        '<div class="agent-cmd"><span class="t-prompt">$</span> ./deploy.sh production</div>' +
        '<div class="agent-verify">Verify with immurok to allow…</div>' +
        '<div class="agent-actions">' +
          '<span class="agent-btn">Cancel</span>' +
        '</div>' +
      '</div></div>';
    await this.setStage(wrap);

    const dialog = wrap.querySelector('.agent-dialog');
    const verify = wrap.querySelector('.agent-verify');

    requestAnimationFrame(() => dialog.classList.add('in'));

    const suffix = ' Verify with immurok to allow…';
    const iv = this.spin((c) => { verify.textContent = c + suffix; });
    // 1. prompt
    await this.sleep(AUTH_PROMPT_MS);
    // 2. touch
    this.fpShow();
    await this.sleep(AUTH_TOUCH_MS);
    clearInterval(iv);
    this.fpHide();

    // 3. success
    verify.classList.add('ok');
    verify.textContent = '✓ approved';
    await this.sleep(AUTH_SUCCESS_MS);
  }

  async playGithub() {
    const gh = cel('div', 'auth-gh');
    gh.innerHTML =
      '<div class="gh-browser">' +
        '<div class="gh-bar"><span></span><span></span><span></span>' +
          '<div class="gh-url">github.com/login</div></div>' +
        '<div class="gh-page">' +
          '<div class="gh-mark">' + GITHUB_SVG + '</div>' +
          '<div class="gh-title">Sign in to GitHub</div>' +
          '<div class="gh-field"><span class="gh-label">Username</span>' +
            '<div class="gh-input"><span class="gh-val" data-k="user"></span></div></div>' +
          '<div class="gh-field"><span class="gh-label">Password</span>' +
            '<div class="gh-input"><span class="gh-val" data-k="pass"></span></div></div>' +
          '<div class="gh-signin">Sign in</div>' +
        '</div>' +
      '</div>' +
      '<div class="gh-veil"><div class="gh-dialog">' +
        '<div class="gh-dialog-fp">' + FP_SVG + '</div>' +
        '<div class="gh-dialog-title">Verify your fingerprint to input password</div>' +
        '<div class="gh-dialog-spin"></div>' +
      '</div></div>';
    await this.setStage(gh);

    const veil = gh.querySelector('.gh-veil');
    const dialog = gh.querySelector('.gh-dialog');
    const spin = gh.querySelector('.gh-dialog-spin');
    const userVal = gh.querySelector('[data-k="user"]');
    const passVal = gh.querySelector('[data-k="pass"]');
    const page = gh.querySelector('.gh-page');
    const url = gh.querySelector('.gh-url');

    // ── Beat A: password ──
    requestAnimationFrame(() => dialog.classList.add('in'));
    const ivA = this.spin((c) => { spin.textContent = c + ' Waiting for touch…'; });
    // 1. prompt
    await this.sleep(AUTH_PROMPT_MS);
    // 2. touch
    this.fpShow();
    await this.sleep(AUTH_TOUCH_MS);
    clearInterval(ivA);
    this.fpHide();
    // 3. success — fill credentials, dismiss verify window
    spin.classList.add('ok');
    spin.textContent = '✓ Verified';
    userVal.textContent = 'octocat';
    passVal.textContent = '••••••••••';
    veil.classList.add('gone');
    await this.sleep(AUTH_SUCCESS_MS);

    // ── transition to 2FA view ──
    url.textContent = 'github.com/sessions/two-factor';
    page.innerHTML =
      '<div class="gh-mark">' + GITHUB_SVG + '</div>' +
      '<div class="gh-title">Two-factor authentication</div>' +
      '<div class="gh-2fa-sub">Please input your 2FA OTP</div>' +
      '<div class="gh-otp">' +
        '<span class="gh-otp-box"></span><span class="gh-otp-box"></span>' +
        '<span class="gh-otp-box"></span><span class="gh-otp-box"></span>' +
        '<span class="gh-otp-box"></span><span class="gh-otp-box"></span>' +
      '</div>';
    const sub = page.querySelector('.gh-2fa-sub');
    const boxes = Array.prototype.slice.call(page.querySelectorAll('.gh-otp-box'));

    // ── Beat B: OTP ──
    // 1. prompt
    boxes[0].classList.add('active');
    await this.sleep(AUTH_PROMPT_MS);
    // 2. touch
    this.fpShow();
    await this.sleep(AUTH_TOUCH_MS);
    this.fpHide();
    // 3. success — auto-fill PIN and sign in
    boxes[0].classList.remove('active');
    const pin = '009527';
    boxes.forEach((b, i) => { b.textContent = pin[i]; b.classList.add('filled'); });
    sub.classList.add('ok');
    sub.textContent = '✓ Signed in';
    await this.sleep(AUTH_SUCCESS_MS);
  }

  renderStatic() {
    const term = cel('div', 'auth-term');
    const chrome = cel('div', 'term-chrome');
    chrome.innerHTML = '<span></span><span></span><span></span>';
    const body = cel('div', 'term-body');
    const cmdLine = cel('div', 'term-line');
    cmdLine.innerHTML =
      '<span class="t-prompt">$ </span><span class="t-cmd">sudo </span><span class="t-arg">make install</span>';
    const okLine = cel('div', 'term-line');
    okLine.innerHTML = '<span class="t-ok">✓ approved</span>';
    body.append(cmdLine, okLine);
    term.append(chrome, body);
    this.stage.appendChild(term);
  }

  sleep(ms) {
    return new Promise((resolve) => { this.timer = setTimeout(resolve, ms); });
  }
}

// ── Loops.so Newsletter Form ──

// Local dedup: remember which emails already joined the waitlist from this
// browser so a repeat submit is a friendly no-op (no GA event, no POST).
const JOINED_EMAILS_KEY = "immurok-waitlist-emails";

function normalizeEmail(value) {
  return (value || "").trim().toLowerCase();
}

function getJoinedEmails() {
  try {
    const raw = localStorage.getItem(JOINED_EMAILS_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    return [];
  }
}

function hasJoined(email) {
  return getJoinedEmails().includes(normalizeEmail(email));
}

function addJoinedEmail(email) {
  const normalized = normalizeEmail(email);
  if (!normalized) return;
  const emails = getJoinedEmails();
  if (emails.includes(normalized)) return;
  emails.push(normalized);
  try {
    localStorage.setItem(JOINED_EMAILS_KEY, JSON.stringify(emails));
  } catch (e) { /* storage full / disabled — dedup is best-effort */ }
}

// ── Discord guide modal ──

let discordModalLastFocus = null;

function openDiscordModal() {
  const modal = document.getElementById("discord-modal");
  if (!modal) return;
  discordModalLastFocus = document.activeElement;
  modal.hidden = false;
  // Force a reflow so the transition runs from the hidden state.
  void modal.offsetWidth;
  modal.classList.add("is-open");
  const primary = modal.querySelector("[data-discord-primary]");
  if (primary) primary.focus();
}

function closeDiscordModal() {
  const modal = document.getElementById("discord-modal");
  if (!modal || modal.hidden) return;
  modal.classList.remove("is-open");
  const finish = () => {
    modal.hidden = true;
    modal.removeEventListener("transitionend", finish);
  };
  modal.addEventListener("transitionend", finish);
  // Fallback in case transitionend doesn't fire (reduced motion, etc.).
  setTimeout(finish, 350);
  if (discordModalLastFocus && typeof discordModalLastFocus.focus === "function") {
    discordModalLastFocus.focus();
  }
  discordModalLastFocus = null;
}

function setupDiscordModal() {
  const modal = document.getElementById("discord-modal");
  if (!modal || modal.classList.contains("discord-handlers-added")) return;
  modal.querySelectorAll("[data-discord-close]").forEach((el) => {
    el.addEventListener("click", closeDiscordModal);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.hidden) closeDiscordModal();
  });
  modal.classList.add("discord-handlers-added");
}

function submitHandler(event) {
  event.preventDefault();
  const container = event.target.parentNode;
  const form = container.querySelector(".newsletter-form");
  const formInput = container.querySelector(".newsletter-form-input");
  const success = container.querySelector(".newsletter-success");
  const errorContainer = container.querySelector(".newsletter-error");
  const errorMessage = container.querySelector(".newsletter-error-message");
  const backButton = container.querySelector(".newsletter-back-button");
  const submitButton = container.querySelector(".newsletter-form-button");
  const loadingButton = container.querySelector(".newsletter-loading-button");

  const formLocation = container.classList.contains("hero-waitlist") ? "hero" : "pricing";

  const rateLimit = () => {
    errorContainer.style.display = "flex";
    errorMessage.innerText = "Too many signups, please try again in a little while";
    submitButton.style.display = "none";
    formInput.style.display = "none";
    backButton.style.display = "block";
  };

  // Local dedup — if this email already joined from this browser, it's a
  // friendly no-op: show an "already on the list" note, guide them to Discord,
  // and record NOTHING to GA (no join_click, no signup) nor POST to Loops.
  if (hasJoined(formInput.value)) {
    const successText = success.querySelector("p");
    if (successText) successText.innerText = "You're already on the list 🎉";
    success.style.display = "flex";
    form.reset();
    form.style.display = "none";
    formInput.style.display = "none";
    submitButton.style.display = "none";
    backButton.style.display = "block";
    openDiscordModal();
    return;
  }

  // Which of the two waitlist forms fired (hero vs pricing section) — lets
  // GA4 compare conversion by placement. gtag/fbq are head-script stubs that
  // queue until consent, so these calls are consent-safe no-ops on reject.
  if (typeof window.gtag === "function") {
    window.gtag("event", "join_click", { form_location: formLocation });
  }

  const time = new Date();
  const timestamp = time.valueOf();
  const previousTimestamp = localStorage.getItem("loops-form-timestamp");

  if (previousTimestamp && Number(previousTimestamp) + 60000 > timestamp) {
    if (typeof window.gtag === "function") {
      window.gtag("event", "waitlist_error", { error_type: "local_throttle", form_location: formLocation });
    }
    rateLimit();
    return;
  }
  localStorage.setItem("loops-form-timestamp", timestamp);

  // Capture the email before form.reset() clears it on success.
  const submittedEmail = formInput.value;

  submitButton.style.display = "none";
  loadingButton.style.display = "flex";

  const formBody = "userGroup=&mailingLists=&email=" + encodeURIComponent(formInput.value);

  fetch(event.target.action, {
    method: "POST",
    body: formBody,
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  })
    .then((res) => [res.ok, res.json(), res])
    .then(([ok, dataPromise, res]) => {
      if (ok) {
        success.style.display = "flex";
        form.reset();
        // Remember this email so a repeat submit is deduped locally.
        addJoinedEmail(submittedEmail);
        // Mark the signup in the URL (no navigation / reload) so analytics
        // can segment by landing state and manual checks are easy. GA4
        // enhanced measurement picks this up as a page_view on history change.
        if (window.history && typeof history.replaceState === "function") {
          try {
            const successUrl = new URL(window.location.href);
            successUrl.searchParams.set("success", "true");
            history.replaceState(null, "", successUrl);
          } catch (e) { /* URL API unavailable — cosmetic feature, skip */ }
        }
        // Guide the new signup into the Discord community.
        openDiscordModal();
        // Track waitlist signup conversion (only fires if the user accepted
        // consent — fbq / gtag are no-ops on reject).
        if (typeof window.fbq === "function") {
          window.fbq("track", "Lead", { content_name: "Waitlist Signup", content_category: formLocation });
        }
        if (typeof window.gtag === "function") {
          window.gtag("event", "waitlist_signup", { method: "loops_form", form_location: formLocation });
        }
      } else {
        // Loops replied with a readable (CORS-visible) error — record the
        // HTTP status so GA can tell these apart from opaque failures.
        if (typeof window.gtag === "function") {
          window.gtag("event", "waitlist_error", { error_type: "loops_reject_" + res.status, form_location: formLocation });
        }
        dataPromise.then(data => {
          errorContainer.style.display = "flex";
          errorMessage.innerText = data.message ? data.message : res.statusText;
        });
      }
    })
    .catch(() => {
      // A rejection here is always a network-level failure — the browser could
      // not complete the request. The most common cause is Loops returning a
      // rate-limit 429 WITHOUT CORS headers (it throttles per IP), which the
      // browser surfaces as an opaque cross-origin block: "Failed to fetch"
      // in Chrome, "Load failed" in Safari. We can't read the status, so show
      // one friendly, browser-agnostic retry message instead of matching a
      // single engine's wording (which leaked the raw error to Safari users).
      if (typeof window.gtag === "function") {
        window.gtag("event", "waitlist_error", { error_type: "fetch_failed", form_location: formLocation });
      }
      errorContainer.style.display = "flex";
      errorMessage.innerText = "Hmm, that didn't go through — please try again in a little while.";
      // The failure wasn't the user mistyping, so clear our own 60s throttle
      // to let them retry as soon as the transient issue clears.
      localStorage.setItem("loops-form-timestamp", '');
    })
    .finally(() => {
      formInput.style.display = "none";
      loadingButton.style.display = "none";
      backButton.style.display = "block";
      // Hide the form's pill wrapper too so we don't leave an empty styled
      // container behind (visible on the hero variant where the form has its
      // own pill background).
      form.style.display = "none";
    });
}

function resetFormHandler(event) {
  const container = event.target.parentNode;
  const form = container.querySelector(".newsletter-form");
  const formInput = container.querySelector(".newsletter-form-input");
  const success = container.querySelector(".newsletter-success");
  const errorContainer = container.querySelector(".newsletter-error");
  const errorMessage = container.querySelector(".newsletter-error-message");
  const backButton = container.querySelector(".newsletter-back-button");
  const submitButton = container.querySelector(".newsletter-form-button");

  success.style.display = "none";
  errorContainer.style.display = "none";
  errorMessage.innerText = "Oops! Something went wrong, please try again";
  backButton.style.display = "none";
  formInput.style.display = "";
  submitButton.style.display = "";
  if (form) form.style.display = "";
}

function setupLoopsForms() {
  const formContainers = document.getElementsByClassName("newsletter-form-container");
  for (let i = 0; i < formContainers.length; i++) {
    const formContainer = formContainers[i];
    if (formContainer.classList.contains('newsletter-handlers-added')) continue;
    formContainer.querySelector(".newsletter-form").addEventListener("submit", submitHandler);
    formContainer.querySelector(".newsletter-back-button").addEventListener("click", resetFormHandler);
    formContainer.classList.add("newsletter-handlers-added");
  }
}

// ── Intersection Observer ──

function setupFadeIn() {
  const els = Array.from(document.querySelectorAll('.fade-in'));
  if (!('IntersectionObserver' in window)) {
    els.forEach((el) => el.classList.add('visible'));
    return;
  }
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    },
    { threshold: 0.1 }
  );
  els.forEach((el) => observer.observe(el));

  // Safety net: the entrance animation must never be able to hide content
  // permanently. On some load paths (anchor jumps, prerender, embedders)
  // observer callbacks fail to deliver and everything stays at opacity 0.
  // Shortly after load: if the observer delivered nothing, reveal all;
  // otherwise just catch up any element already inside the viewport.
  const safetyNet = () => {
    if (!els.some((el) => el.classList.contains('visible'))) {
      els.forEach((el) => el.classList.add('visible'));
      return;
    }
    const vh = window.innerHeight;
    els.forEach((el) => {
      if (el.classList.contains('visible')) return;
      const r = el.getBoundingClientRect();
      if (r.top < vh && r.bottom > 0) el.classList.add('visible');
    });
  };
  if (document.readyState === 'complete') {
    setTimeout(safetyNet, 400);
  } else {
    window.addEventListener('load', () => setTimeout(safetyNet, 400));
  }
}

// ── Nav scroll ──

function setupNavScroll() {
  const nav = document.getElementById('nav');
  if (!nav) return;
  const onScroll = () => {
    nav.classList.toggle('scrolled', window.scrollY > 20);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

// ── Smooth scroll ──

function setupSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (e) => {
      const target = document.querySelector(link.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

// ── Mobile nav ──

function setupMobileNav() {
  const toggle = document.querySelector('.nav-toggle');
  const links = document.querySelector('.nav-links');
  if (!toggle || !links) return;
  toggle.addEventListener('click', () => {
    const open = links.classList.toggle('open');
    toggle.setAttribute('aria-expanded', open);
  });
  links.querySelectorAll('a').forEach((a) => {
    a.addEventListener('click', () => {
      links.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  });
}

// ── Discord link click tracking ──

// GA event on every Discord invite click, tagged by placement so we can see
// which entry point (nav button / footer / post-signup modal) actually
// converts people into the community. Links open in a new tab, so firing
// synchronously here is safe — the page stays alive.
function setupDiscordTracking() {
  document.querySelectorAll('a[href*="discord.gg"]').forEach((link) => {
    link.addEventListener('click', () => {
      let location = 'header';
      if (link.closest('#discord-modal')) location = 'signup_modal';
      else if (link.closest('footer')) location = 'footer';
      if (typeof window.gtag === 'function') {
        window.gtag('event', 'discord_click', { link_location: location });
      }
    });
  });
}

// ── Init ──

document.addEventListener('DOMContentLoaded', () => {
  const terminalBody = document.getElementById('hero-terminal');
  const fpTouch = document.getElementById('fp-touch');
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (terminalBody && !prefersReducedMotion) {
    const animator = new TerminalAnimator(terminalBody, fpTouch);
    animator.start();
  }

  setupMobileNav();
  setupLoopsForms();
  setupDiscordModal();
  setupDiscordTracking();
  setupFadeIn();
  setupNavScroll();
  setupSmoothScroll();
  setupSpecs3DVisibility();
  setupHeroCtaExpand();
  setupAuthDemo(prefersReducedMotion);
  setupAdMarquee(prefersReducedMotion);
  setupObfuscatedEmail();
});

// Anti-scrape email: the address is stored as reversed user/domain parts in
// data-eu / data-ed (no literal address, "@", or mailto: in the HTML source).
// Reassemble at runtime so real visitors get a working mailto link while
// harvesters that read the static HTML come up empty.
function setupObfuscatedEmail() {
  const rev = (s) => s.split('').reverse().join('');
  document.querySelectorAll('a[data-eu][data-ed]').forEach((a) => {
    const addr = `${rev(a.dataset.eu)}@${rev(a.dataset.ed)}`;
    a.href = `mailto:${addr}`;
    a.textContent = addr;
    a.removeAttribute('data-eu');
    a.removeAttribute('data-ed');
  });
}

// Gallery: a native horizontally-scrolling filmstrip of product shots.
// Click the left/right half to step to the previous/next image; drag also
// works. Vertical wheel is left alone so the page scrolls normally.
function setupAdMarquee() {
  const strip = document.getElementById('photo-gallery');
  if (!strip) return;
  const imgs = strip.querySelectorAll('img');

  // Don't let the browser's native image drag / selection hijack the gesture.
  imgs.forEach((img) => {
    img.addEventListener('dragstart', (e) => e.preventDefault());
    img.addEventListener('selectstart', (e) => e.preventDefault());
  });

  // Distance between two consecutive centered images (image width + gap).
  const step = () => (imgs.length > 1 ? imgs[1].offsetLeft - imgs[0].offsetLeft : strip.clientWidth);

  let down = false;
  let startX = 0;
  let startScroll = 0;
  let dragged = false;

  strip.addEventListener('pointerdown', (e) => {
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    down = true;
    dragged = false;
    startX = e.clientX;
    startScroll = strip.scrollLeft;
    strip.setPointerCapture(e.pointerId);
    strip.classList.add('dragging');
  });

  strip.addEventListener('pointermove', (e) => {
    if (!down) return;
    const dx = e.clientX - startX;
    if (Math.abs(dx) > 4) dragged = true;
    strip.scrollLeft = startScroll - dx;
  });

  const release = (e) => {
    if (!down) return;
    down = false;
    strip.classList.remove('dragging');
    try { strip.releasePointerCapture(e.pointerId); } catch (_) {}
  };
  strip.addEventListener('pointerup', release);
  strip.addEventListener('pointercancel', release);

  // Click left/right half → previous/next image (ignored if it was a drag).
  strip.addEventListener('click', (e) => {
    if (dragged) { e.preventDefault(); e.stopPropagation(); return; }
    const rect = strip.getBoundingClientRect();
    const dir = e.clientX < rect.left + rect.width / 2 ? -1 : 1;
    strip.scrollBy({ left: dir * step(), behavior: 'smooth' });
  });
}

// Problem-section auth demo: animate only while on-screen; honor reduced motion.
function setupAuthDemo(prefersReducedMotion) {
  const demoEl = document.getElementById('auth-demo');
  if (!demoEl) return;
  const animator = new AuthDemoAnimator(demoEl);
  if (prefersReducedMotion) {
    animator.renderStatic();
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) animator.start();
        else animator.stop();
      });
    },
    { threshold: 0.25 }
  );
  io.observe(demoEl);
}

// Hero "Join Waitlist" button expands in-place to an email input + Join
// button instead of scrolling to the pricing form. The form submission is
// wired by setupLoopsForms() since it shares the .newsletter-form-container.
function setupHeroCtaExpand() {
  const trigger = document.querySelector('.hero-cta-trigger');
  const container = document.querySelector('.hero-waitlist');
  if (!trigger || !container) return;
  trigger.addEventListener('click', () => {
    trigger.hidden = true;
    container.hidden = false;
    const input = container.querySelector('.newsletter-form-input');
    if (input) input.focus();
  });
  // Allow showing the trigger again from the success-state "Back" button
  const back = container.querySelector('.newsletter-back-button');
  if (back) {
    back.addEventListener('click', () => {
      // Brief delay so the form's own reset handler runs first
      setTimeout(() => {
        container.hidden = true;
        trigger.hidden = false;
      }, 0);
    });
  }
}

// Pause the 3D viewer's render loop when its iframe leaves the viewport so
// scrolling stays smooth (constant WebGL rendering on a hidden iframe was
// causing perceptible jank).
function setupSpecs3DVisibility() {
  const iframe = document.querySelector('.specs-3d iframe');
  if (!iframe) return;
  const post = (visible) => {
    if (iframe.contentWindow) {
      iframe.contentWindow.postMessage({ type: 'ik1-visibility', visible }, '*');
    }
  };
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => post(e.isIntersecting));
  }, { threshold: 0 });
  io.observe(iframe);
  // Initial probe — iframe likely off-screen on first load.
  const rect = iframe.getBoundingClientRect();
  const onscreen = rect.bottom > 0 && rect.top < window.innerHeight;
  iframe.addEventListener('load', () => post(onscreen), { once: true });
}
