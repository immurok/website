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

// ── Loops.so Newsletter Form ──

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

  const rateLimit = () => {
    errorContainer.style.display = "flex";
    errorMessage.innerText = "Too many signups, please try again in a little while";
    submitButton.style.display = "none";
    formInput.style.display = "none";
    backButton.style.display = "block";
  };

  const time = new Date();
  const timestamp = time.valueOf();
  const previousTimestamp = localStorage.getItem("loops-form-timestamp");

  if (previousTimestamp && Number(previousTimestamp) + 60000 > timestamp) {
    rateLimit();
    return;
  }
  localStorage.setItem("loops-form-timestamp", timestamp);

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
      } else {
        dataPromise.then(data => {
          errorContainer.style.display = "flex";
          errorMessage.innerText = data.message ? data.message : res.statusText;
        });
      }
    })
    .catch(error => {
      if (error.message === "Failed to fetch") {
        rateLimit();
        return;
      }
      errorContainer.style.display = "flex";
      if (error.message) errorMessage.innerText = error.message;
      localStorage.setItem("loops-form-timestamp", '');
    })
    .finally(() => {
      formInput.style.display = "none";
      loadingButton.style.display = "none";
      backButton.style.display = "block";
    });
}

function resetFormHandler(event) {
  const container = event.target.parentNode;
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
  formInput.style.display = "flex";
  submitButton.style.display = "flex";
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
  document.querySelectorAll('.fade-in').forEach((el) => observer.observe(el));
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
  setupFadeIn();
  setupNavScroll();
  setupSmoothScroll();
});
