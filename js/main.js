/**
 * Guardian Runner: The Unpaid Debt - Master Interactive Controller
 * Powered by modern UI/UX psychology, gamified quest tracker, and dopamine audio feedback.
 */

document.addEventListener('DOMContentLoaded', () => {
  initAudio();
  initParallax();
  initTransformEngine();
  initCharacterCodex();
  initScrollytelling();
  initChoiceChamber();
  initNarrationAudio();
  initEndings();
  initCosmology();
  initNavigation();
  initCard3DTilt();
});

/* ----------------------------------------------------
 * 1. Audio System (Atmosphere & SFX Engine)
 * -------------------------------------------------- */
let bgMusic = null;
let isAudioPlaying = false;
let currentNarration = null;

function initAudio() {
  bgMusic = new Audio('assets/audio/dark-forest.ogg');
  bgMusic.loop = true;
  bgMusic.volume = 0.35;

  const audioToggle = document.getElementById('audio-toggle');
  const soundBars = document.querySelectorAll('.sound-wave span');

  function updateAudioUI(playing) {
    isAudioPlaying = playing;
    if (audioToggle) {
      audioToggle.setAttribute('aria-pressed', playing);
      audioToggle.classList.toggle('playing', playing);
      const label = audioToggle.querySelector('.audio-label');
      if (label) label.textContent = playing ? 'Sound: ON 🔊' : 'Sound: OFF 🔇';
    }
    soundBars.forEach(bar => {
      bar.style.animationPlayState = playing ? 'running' : 'paused';
    });
  }

  if (audioToggle) {
    audioToggle.addEventListener('click', () => {
      if (isAudioPlaying) {
        bgMusic.pause();
        updateAudioUI(false);
      } else {
        bgMusic.play().then(() => {
          updateAudioUI(true);
        }).catch(err => {
          console.warn('Autoplay blocked:', err);
        });
      }
    });
  }
}

function playSfx(type) {
  let file = 'assets/audio/mixkit-quick-knife-slice-cutting-2152.mp3';
  if (type === 'whoosh') file = 'assets/audio/whoosh-cinematic-sound-effect-376889.mp3';
  if (type === 'magic') file = 'assets/audio/magic sound effect.mp3';
  if (type === 'reveal') file = 'assets/audio/Reveal Sound Effect.mp3';
  if (type === 'laugh') file = 'assets/audio/Evil laugh.mp3';
  if (type === 'celestial') file = 'assets/audio/Magical Light Aura Sound Effect.mp3';
  if (type === 'sword') file = 'assets/audio/sword-slice-2-393845.mp3';

  try {
    const sfx = new Audio(file);
    sfx.volume = 0.35;
    sfx.play().catch(() => {});
  } catch (e) {}
}

window.playSfx = playSfx;

/* ----------------------------------------------------
 * 2. Gamified Soul Fragment Quest Tracker
 * -------------------------------------------------- */
const unlockedSouls = new Set();
const TOTAL_SOULS = 12;

function registerSoulInspection(charId) {
  if (!unlockedSouls.has(charId)) {
    unlockedSouls.add(charId);
    playSfx('reveal');

    // Update HUD count
    const hudCount = document.getElementById('hud-souls-count');
    const hudBar = document.getElementById('hud-souls-bar');
    if (hudCount) {
      hudCount.textContent = `${unlockedSouls.size} / ${TOTAL_SOULS}`;
    }
    if (hudBar) {
      const pct = (unlockedSouls.size / TOTAL_SOULS) * 100;
      hudBar.style.width = `${pct}%`;
    }

    // Show achievement toast
    showToast(`✨ New Lore Unlocked: +1 Soul Fragment (${unlockedSouls.size}/${TOTAL_SOULS})`);

    if (unlockedSouls.size === TOTAL_SOULS) {
      setTimeout(() => {
        playSfx('celestial');
        showToast('🏆 Master Chronicler: All 12 Souls Discovered!');
      }, 800);
    }
  }
}

function showToast(msg) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'dopamine-toast';
  toast.innerHTML = msg;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 400);
  }, 3500);
}

/* ----------------------------------------------------
 * 3. Parallax Controller
 * -------------------------------------------------- */
function initParallax() {
  if (window.ParallaxController) {
    new window.ParallaxController();
  }
}

/* ----------------------------------------------------
 * 4. Transformation Engine
 * -------------------------------------------------- */
function initTransformEngine() {
  if (window.TransformEngine) {
    new window.TransformEngine();
  }
}

/* ----------------------------------------------------
 * 5. Interactive "Would You Take The Deal?" Chamber
 * -------------------------------------------------- */
function initChoiceChamber() {
  const btnTake = document.getElementById('btn-choice-take');
  const btnWalk = document.getElementById('btn-choice-walk');
  const outcomeBox = document.getElementById('choice-outcome');

  if (!btnTake || !btnWalk || !outcomeBox) return;

  btnTake.addEventListener('click', () => {
    playSfx('sword');
    btnTake.classList.add('active-choice');
    btnWalk.classList.remove('active-choice');

    outcomeBox.innerHTML = `
      <div class="outcome-card outcome-take">
        <span class="outcome-badge">Deal Accepted 🗡️</span>
        <h4>You plunged the black iron fragment into your chest!</h4>
        <p>A shock of dark lightning shoots through your arms! Unnatural shadow speed and razor scythes surge into your veins. You now have a real shot at saving Elise! But the clock is ticking: every slash of your blade costs a piece of your mortal soul.</p>
        <div class="outcome-reward">+500 XP // Unlocked: The Cursed Runner Stance</div>
      </div>
    `;
    outcomeBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });

  btnWalk.addEventListener('click', () => {
    playSfx('magic');
    btnWalk.classList.add('active-choice');
    btnTake.classList.remove('active-choice');

    outcomeBox.innerHTML = `
      <div class="outcome-card outcome-walk">
        <span class="outcome-badge walk">Deal Refused 🕊️</span>
        <h4>You stepped away from the shadow.</h4>
        <p>The Ledger closes his book with a soft snap. Elise's soul fades into the mist, gone forever. You walk back to your empty home, completely human, completely safe—but your heart will carry the heavy weight of what could have been for the rest of your days.</p>
        <div class="outcome-reward">+100 XP // Unlocked: The Grieving Wanderer</div>
      </div>
    `;
    outcomeBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });
}

/* ----------------------------------------------------
 * 6. Story Narration Voiceover Audio Player
 * -------------------------------------------------- */
function initNarrationAudio() {
  const narrationBtns = document.querySelectorAll('.narration-btn');
  const audioFiles = [
    'assets/audio/story_narration.mp3',
    'assets/audio/story_narration1.mp3',
    'assets/audio/story_narration2.mp3'
  ];

  narrationBtns.forEach((btn, index) => {
    btn.addEventListener('click', () => {
      const file = audioFiles[index % audioFiles.length];

      if (currentNarration && !currentNarration.paused) {
        currentNarration.pause();
        currentNarration.currentTime = 0;
        narrationBtns.forEach(b => {
          b.classList.remove('playing');
          b.innerHTML = '🎧 Listen to Narrator';
        });
        if (btn.dataset.activeFile === file) {
          btn.dataset.activeFile = '';
          return;
        }
      }

      currentNarration = new Audio(file);
      currentNarration.volume = 0.8;
      btn.classList.add('playing');
      btn.dataset.activeFile = file;
      btn.innerHTML = '⏸️ Playing Voiceover...';
      playSfx('magic');

      currentNarration.play().catch(() => {
        btn.classList.remove('playing');
        btn.innerHTML = '🎧 Listen to Narrator';
      });

      currentNarration.onended = () => {
        btn.classList.remove('playing');
        btn.innerHTML = '🎧 Listen to Narrator';
      };
    });
  });
}

/* ----------------------------------------------------
 * 7. Character Codex & Modal Dossier
 * -------------------------------------------------- */
let activeModalAnimator = null;

function initCharacterCodex() {
  const grid = document.getElementById('character-grid');
  const filterBtns = document.querySelectorAll('.codex-filter-btn');
  const characters = window.CHARACTER_DATA || [];

  if (!grid || characters.length === 0) return;

  function renderCards(filter = 'all') {
    grid.innerHTML = '';

    const filtered = filter === 'all' 
      ? characters 
      : characters.filter(c => c.faction === filter || (filter === 'staff' && c.classification.includes('Staff')) || (filter === 'husks' && c.classification.includes('Husks')));

    filtered.forEach(char => {
      const card = document.createElement('article');
      card.className = `character-card faction-${char.faction}`;
      card.setAttribute('tabindex', '0');
      card.setAttribute('role', 'button');
      card.setAttribute('aria-label', `View profile of ${char.name}`);

      card.innerHTML = `
        <div class="card-canvas-wrap">
          <canvas class="card-canvas" width="180" height="180"></canvas>
          <span class="card-faction-badge ${char.faction}">${char.classification}</span>
          <span class="unlock-indicator ${unlockedSouls.has(char.id) ? 'unlocked' : ''}" title="Soul status">★</span>
        </div>
        <div class="card-info">
          <h3 class="card-name">${char.name}</h3>
          <p class="card-title">${char.title}</p>
          <p class="card-snippet">${char.accordRole}</p>
          <button class="inspect-btn">
            Inspect Character <span>&rarr;</span>
          </button>
        </div>
      `;

      // Live animated sprite on card
      const canvas = card.querySelector('.card-canvas');
      const cardAnimator = new SpriteAnimator(canvas, { fps: 9 });
      const defaultAnimKey = char.defaultAnim || Object.keys(char.animations)[0];
      const animData = char.animations[defaultAnimKey];

      if (animData && animData.frames.length > 0) {
        cardAnimator.loadFrames(animData.frames, animData.fps || 8);
      } else if (char.staticPortrait) {
        const img = new Image();
        img.onload = () => {
          const ctx = canvas.getContext('2d');
          ctx.imageSmoothingEnabled = false;
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        };
        img.src = char.staticPortrait;
      }

      card.addEventListener('click', () => {
        registerSoulInspection(char.id);
        const star = card.querySelector('.unlock-indicator');
        if (star) star.classList.add('unlocked');
        openCharacterModal(char);
      });

      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          registerSoulInspection(char.id);
          openCharacterModal(char);
        }
      });

      grid.appendChild(card);
    });

    initCard3DTilt();
  }

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      playSfx('whoosh');
      renderCards(btn.dataset.filter);
    });
  });

  renderCards('all');
  initModalListeners();
}

function openCharacterModal(char) {
  const modal = document.getElementById('character-modal');
  if (!modal) return;

  const nameEl = document.getElementById('modal-char-name');
  const titleEl = document.getElementById('modal-char-title');
  const classEl = document.getElementById('modal-char-class');
  const loreEl = document.getElementById('modal-char-lore');
  const quoteEl = document.getElementById('modal-char-quote');
  const accordEl = document.getElementById('modal-char-accord');
  const actionsWrap = document.getElementById('modal-actions-wrap');
  const canvas = document.getElementById('modal-canvas');

  nameEl.textContent = char.name;
  titleEl.textContent = char.title;
  classEl.textContent = char.classification;
  loreEl.textContent = char.lore;
  quoteEl.textContent = char.quote;
  accordEl.textContent = char.accordRole;

  if (activeModalAnimator) {
    activeModalAnimator.destroy();
  }

  activeModalAnimator = new SpriteAnimator(canvas, { fps: 10 });

  actionsWrap.innerHTML = '';
  const animKeys = Object.keys(char.animations);

  animKeys.forEach((key, idx) => {
    const anim = char.animations[key];
    const btn = document.createElement('button');
    btn.className = `action-btn ${idx === 0 ? 'active' : ''}`;
    btn.innerHTML = `${anim.name} <span>▶</span>`;
    btn.addEventListener('click', () => {
      actionsWrap.querySelectorAll('.action-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      playSfx('slash');
      activeModalAnimator.loadFrames(anim.frames, anim.fps || 10);
    });
    actionsWrap.appendChild(btn);
  });

  const firstAnim = char.animations[char.defaultAnim] || char.animations[animKeys[0]];
  if (firstAnim) {
    activeModalAnimator.loadFrames(firstAnim.frames, firstAnim.fps || 10);
  }

  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function initModalListeners() {
  const modal = document.getElementById('character-modal');
  const closeBtn = document.getElementById('modal-close-btn');

  function closeModal() {
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    if (activeModalAnimator) {
      activeModalAnimator.stop();
    }
  }

  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal && modal.classList.contains('open')) {
      closeModal();
    }
  });
}

/* ----------------------------------------------------
 * 8. 3D Card Hover & Holographic Tilt Effect
 * -------------------------------------------------- */
function initCard3DTilt() {
  const cards = document.querySelectorAll('.character-card');
  cards.forEach(card => {
    card.addEventListener('mousemove', (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const centerX = rect.width / 2;
      const centerY = rect.height / 2;

      const rotateX = ((y - centerY) / centerY) * -9;
      const rotateY = ((x - centerX) / centerX) * 9;

      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-8px) scale3d(1.02, 1.02, 1.02)`;
    });

    card.addEventListener('mouseleave', () => {
      card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0) scale3d(1, 1, 1)';
    });
  });
}

/* ----------------------------------------------------
 * 9. Scrollytelling Progress & Chapter Trigger
 * -------------------------------------------------- */
function initScrollytelling() {
  const chapters = document.querySelectorAll('.chapter-card');
  const progressFill = document.getElementById('scroll-progress-fill');
  const navDots = document.querySelectorAll('.chapter-nav-dot');

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in-view');
        const chapterIdx = entry.target.dataset.chapter;
        navDots.forEach(dot => {
          dot.classList.toggle('active', dot.dataset.targetChapter === chapterIdx);
        });
      }
    });
  }, { threshold: 0.3 });

  chapters.forEach(ch => observer.observe(ch));

  window.addEventListener('scroll', () => {
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const scrolled = window.scrollY;
    const progress = Math.min(100, Math.max(0, (scrolled / docHeight) * 100));
    if (progressFill) progressFill.style.width = `${progress}%`;
  }, { passive: true });

  navDots.forEach(dot => {
    dot.addEventListener('click', () => {
      const targetId = dot.dataset.targetChapter;
      const targetEl = document.querySelector(`[data-chapter="${targetId}"]`);
      if (targetEl) {
        targetEl.scrollIntoView({ behavior: 'smooth' });
        playSfx('whoosh');
      }
    });
  });
}

/* ----------------------------------------------------
 * 10. Dual Endings Interactive Explorer
 * -------------------------------------------------- */
function initEndings() {
  const endingTabs = document.querySelectorAll('.ending-choice-tab');
  const panels = document.querySelectorAll('.ending-panel');
  const showcase = document.querySelector('.endings-showcase');

  endingTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      endingTabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));

      tab.classList.add('active');
      const targetPanel = document.getElementById(tab.dataset.targetPanel);
      if (targetPanel) {
        targetPanel.classList.add('active');
      }

      if (showcase) {
        showcase.dataset.activeEnding = tab.dataset.ending;
      }
      playSfx(tab.dataset.ending === 'purified' ? 'celestial' : 'laugh');
    });
  });
}

/* ----------------------------------------------------
 * 11. Accord Cosmology Interactive Flow
 * -------------------------------------------------- */
function initCosmology() {
  const nodes = document.querySelectorAll('.cosmology-node');
  const infoTitle = document.getElementById('cosmology-info-title');
  const infoDesc = document.getElementById('cosmology-info-desc');

  nodes.forEach(node => {
    node.addEventListener('click', () => {
      nodes.forEach(n => n.classList.remove('active'));
      node.classList.add('active');
      if (infoTitle) infoTitle.textContent = node.dataset.name;
      if (infoDesc) infoDesc.textContent = node.dataset.desc;
      playSfx('whoosh');
    });
  });
}

/* ----------------------------------------------------
 * 12. Smooth Navigation
 * -------------------------------------------------- */
function initNavigation() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth' });
        playSfx('whoosh');
      }
    });
  });
}
