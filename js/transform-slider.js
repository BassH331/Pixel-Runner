/**
 * Interactive Transformation & Debt Engine
 * Enhanced with screen rumble, sound triggers, and punchy dopamine feedback.
 */

class TransformEngine {
  constructor() {
    this.slider = document.getElementById('curse-range');
    this.stageDisplay = document.querySelector('.stage-display');
    this.humanCanvas = document.getElementById('human-canvas');
    this.demonCanvas = document.getElementById('demon-canvas');
    this.percentLabel = document.getElementById('corruption-pct');
    this.memoryText = document.getElementById('memory-fragment');
    this.costDetails = document.getElementById('cost-details');
    this.stateLabel = document.getElementById('state-label');
    this.auraElement = document.getElementById('trans-aura');

    this.humanAnimator = null;
    this.demonAnimator = null;
    this.lastTier = 0;

    this.memories = [
      { max: 20, state: "100% Mortal Hero", quote: "“I remember her laugh like cool river water. We were walking home. I will bring her back!”", cost: "Your human soul is intact. The shadow demon inside you is resting." },
      { max: 45, state: "Slightly Corrupted", quote: "“My hands are freezing... I remember holding her wrist, but what color was her favorite scarf?”", cost: "You gain shadow speed! But your fingers turn pale and you forget small memories." },
      { max: 70, state: "Half Demon Beast", quote: "“Were her eyes blue or green? Why is her voice fading? All I hear is the scratching of the Broker's pen!”", cost: "Huge demon strength! But your reflection in the water starts showing a monster with glowing eyes." },
      { max: 95, state: "Nearly Lost Forever", quote: "“I know I am running for someone... but what was her name? The power feels so good... why stop now?”", cost: "Giant razor claws and shadow wings! Almost everything you loved has been burned away." },
      { max: 100, state: "Full Demon God (Ending B)", quote: "“I am no longer a man. I am the new Collector of the Forest! All debts belong to ME!”", cost: "You are an immortal god! But the brother who loved Elysia is completely gone." }
    ];

    this.init();
  }

  init() {
    if (!this.humanCanvas || !this.demonCanvas) return;

    this.humanAnimator = new SpriteAnimator(this.humanCanvas, { fps: 9 });
    this.demonAnimator = new SpriteAnimator(this.demonCanvas, { fps: 11 });

    const charData = window.CHARACTER_DATA.find(c => c.id === 'protagonist');
    if (charData) {
      this.humanAnimator.loadFrames(charData.animations.mortal_idle.frames, 9);
      this.demonAnimator.loadFrames(charData.animations.cursed_idle.frames, 11);
    }

    if (this.slider) {
      this.slider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        this.updateState(val);
      });
      this.updateState(parseInt(this.slider.value, 10));
    }
  }

  updateState(val) {
    if (this.percentLabel) {
      this.percentLabel.textContent = `${val}%`;
    }

    // Top HUD update if present
    const hudCurse = document.getElementById('hud-curse-val');
    if (hudCurse) {
      hudCurse.textContent = `${val}%`;
    }

    // Canvas blending
    const humanAlpha = Math.max(0, 1 - (val / 85));
    const demonAlpha = Math.min(1, val / 70);

    if (this.humanCanvas) {
      this.humanCanvas.style.opacity = humanAlpha;
      this.humanCanvas.style.filter = `grayscale(${val * 0.9}%) blur(${val * 0.015}px)`;
    }
    if (this.demonCanvas) {
      this.demonCanvas.style.opacity = demonAlpha;
      this.demonCanvas.style.filter = `drop-shadow(0 0 ${val * 0.35}px rgba(220, 20, 45, ${val / 90}))`;
    }

    // Aura update
    if (this.auraElement) {
      const red = Math.round(val * 2.4);
      const alpha = (val / 100) * 0.75;
      this.auraElement.style.background = `radial-gradient(circle, rgba(${red}, 10, 40, ${alpha}) 0%, rgba(5, 5, 10, 0) 70%)`;
      this.auraElement.style.transform = `scale(${1 + val * 0.007})`;
    }

    // Screen Shake effect when corruption is high (75%+)
    if (this.stageDisplay) {
      if (val >= 80) {
        this.stageDisplay.classList.add('rumble-active');
      } else {
        this.stageDisplay.classList.remove('rumble-active');
      }
    }

    // Tier sound trigger
    const currentTierIndex = this.memories.findIndex(m => val <= m.max);
    if (currentTierIndex !== -1 && currentTierIndex !== this.lastTier) {
      this.lastTier = currentTierIndex;
      if (typeof window.playSfx === 'function') {
        if (val >= 90) {
          window.playSfx('laugh');
        } else if (val >= 50) {
          window.playSfx('whoosh');
        } else {
          window.playSfx('magic');
        }
      }
    }

    // Find current memory stage
    const currentStage = this.memories[currentTierIndex] || this.memories[this.memories.length - 1];

    if (this.stateLabel) {
      this.stateLabel.textContent = currentStage.state;
      this.stateLabel.className = val > 75 ? 'state-badge state-danger' : (val > 35 ? 'state-badge state-warning' : 'state-badge state-normal');
    }
    if (this.memoryText) {
      this.memoryText.textContent = currentStage.quote;
    }
    if (this.costDetails) {
      this.costDetails.textContent = currentStage.cost;
    }
  }
}

window.TransformEngine = TransformEngine;
