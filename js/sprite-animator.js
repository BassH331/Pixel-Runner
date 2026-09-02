/**
 * High Performance Pixel-Art Sprite Frame Animator
 * Renders frame sequences onto HTML5 Canvas with pixel-perfect smoothing disabled.
 */

class SpriteAnimator {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.options = {
      fps: options.fps || 10,
      loop: options.loop !== false,
      autoPlay: options.autoPlay !== false,
      pixelated: true,
      onFrame: options.onFrame || null,
      ...options
    };

    if (this.options.pixelated) {
      this.ctx.imageSmoothingEnabled = false;
    }

    this.frames = [];
    this.loadedImages = [];
    this.currentFrame = 0;
    this.isPlaying = false;
    this.lastFrameTime = 0;
    this.animationFrameId = null;
    this.scale = 1;
  }

  loadFrames(frameUrls, fps = 10) {
    this.stop();
    this.frames = frameUrls;
    this.options.fps = fps;
    this.currentFrame = 0;
    this.loadedImages = new Array(frameUrls.length).fill(null);

    let loadCount = 0;
    const total = frameUrls.length;

    if (total === 0) {
      this.clear();
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      frameUrls.forEach((url, idx) => {
        const img = new Image();
        img.onload = () => {
          this.loadedImages[idx] = img;
          loadCount++;
          if (idx === 0) {
            this.renderFrame(0);
          }
          if (loadCount === total) {
            if (this.options.autoPlay) {
              this.play();
            }
            resolve();
          }
        };
        img.onerror = () => {
          loadCount++;
          if (loadCount === total) resolve();
        };
        img.src = url;
      });
    });
  }

  renderFrame(index) {
    const img = this.loadedImages[index];
    if (!img) return;

    const cw = this.canvas.width;
    const ch = this.canvas.height;
    this.ctx.clearRect(0, 0, cw, ch);

    // Calculate aspect-preserving scale to center image inside canvas
    const imgAspect = img.width / img.height;
    const canvasAspect = cw / ch;

    let drawW, drawH;
    if (imgAspect > canvasAspect) {
      drawW = cw * 0.9;
      drawH = drawW / imgAspect;
    } else {
      drawH = ch * 0.9;
      drawW = drawH * imgAspect;
    }

    const drawX = (cw - drawW) / 2;
    const drawY = (ch - drawH) / 2;

    this.ctx.imageSmoothingEnabled = false;
    this.ctx.drawImage(img, Math.round(drawX), Math.round(drawY), Math.round(drawW), Math.round(drawH));

    if (this.options.onFrame) {
      this.options.onFrame(index, this.loadedImages.length);
    }
  }

  play() {
    if (this.isPlaying) return;
    this.isPlaying = true;
    this.lastFrameTime = performance.now();
    this.loop();
  }

  stop() {
    this.isPlaying = false;
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
  }

  loop = (timestamp) => {
    if (!this.isPlaying) return;

    const frameInterval = 1000 / this.options.fps;
    const elapsed = timestamp - this.lastFrameTime;

    if (elapsed >= frameInterval) {
      this.lastFrameTime = timestamp - (elapsed % frameInterval);

      if (this.loadedImages.length > 0) {
        this.currentFrame = (this.currentFrame + 1) % this.loadedImages.length;
        this.renderFrame(this.currentFrame);
      }
    }

    this.animationFrameId = requestAnimationFrame(this.loop);
  };

  setFps(fps) {
    this.options.fps = Math.max(1, fps);
  }

  clear() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  destroy() {
    this.stop();
    this.loadedImages = [];
    this.frames = [];
  }
}

window.SpriteAnimator = SpriteAnimator;
