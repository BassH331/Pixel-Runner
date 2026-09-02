/**
 * Multi-layer Parallax Controller
 * Supports scroll-based and subtle cursor-driven depth for layered atmospheric pixel art.
 */

class ParallaxController {
  constructor() {
    this.hero = document.querySelector('.hero-section');
    this.layers = document.querySelectorAll('[data-parallax-speed]');
    this.isReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.mouseX = 0;
    this.mouseY = 0;
    this.targetMouseX = 0;
    this.targetMouseY = 0;
    this.ticking = false;

    if (!this.isReducedMotion) {
      this.init();
    }
  }

  init() {
    window.addEventListener('scroll', () => this.onScroll(), { passive: true });

    if (this.hero) {
      this.hero.addEventListener('mousemove', (e) => {
        const rect = this.hero.getBoundingClientRect();
        this.targetMouseX = (e.clientX - rect.left) / rect.width - 0.5;
        this.targetMouseY = (e.clientY - rect.top) / rect.height - 0.5;
        this.requestTick();
      }, { passive: true });

      this.hero.addEventListener('mouseleave', () => {
        this.targetMouseX = 0;
        this.targetMouseY = 0;
        this.requestTick();
      });
    }

    this.onScroll();
  }

  requestTick() {
    if (!this.ticking) {
      requestAnimationFrame(() => {
        this.updateMouseParallax();
        this.ticking = false;
      });
      this.ticking = true;
    }
  }

  updateMouseParallax() {
    this.mouseX += (this.targetMouseX - this.mouseX) * 0.08;
    this.mouseY += (this.targetMouseY - this.mouseY) * 0.08;

    this.layers.forEach((layer) => {
      const speed = parseFloat(layer.getAttribute('data-parallax-speed')) || 0.1;
      const mouseFactor = parseFloat(layer.getAttribute('data-mouse-factor')) || speed * 25;
      const scrollSpeed = parseFloat(layer.getAttribute('data-scroll-speed')) || speed;
      const scrollY = window.scrollY;

      const tx = Math.round(this.mouseX * mouseFactor);
      const ty = Math.round(scrollY * scrollSpeed + this.mouseY * mouseFactor);

      layer.style.transform = `translate3d(${tx}px, ${ty}px, 0)`;
    });

    if (Math.abs(this.targetMouseX - this.mouseX) > 0.001 || Math.abs(this.targetMouseY - this.mouseY) > 0.001) {
      requestAnimationFrame(() => this.updateMouseParallax());
    }
  }

  onScroll() {
    const scrollY = window.scrollY;
    this.layers.forEach((layer) => {
      const scrollSpeed = parseFloat(layer.getAttribute('data-scroll-speed')) || 0.1;
      const mouseFactor = parseFloat(layer.getAttribute('data-mouse-factor')) || 10;
      const tx = Math.round(this.mouseX * mouseFactor);
      const ty = Math.round(scrollY * scrollSpeed);
      layer.style.transform = `translate3d(${tx}px, ${ty}px, 0)`;
    });
  }
}

window.ParallaxController = ParallaxController;
