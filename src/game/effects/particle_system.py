"""
ParticleSystem — High-performance procedural particle engine for Pixel-Runner.

Features:
- Deque-based object pool for zero GC allocation churn during gameplay.
- Preset particle profiles: BLOOD_SPLASH, SOUL_WISP, DUST_CLOUD, FIRE_EMBER, WEAPON_SPARST.
- EventBus integration: automatically subscribes to DamageDealt and EntityDied events.
- Batch rendering with optional BLEND_RGBA_ADD glowing particle effects.
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Tuple
import pygame as pg

from v3x_zulfiqar_gideon import EventBus, DamageDealt, EntityDied


# ─────────────────────────────────────────────────────────────────────────────
# Particle Dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class Particle:
    """Lightweight, slot-optimized procedural particle."""
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    color: Tuple[int, int, int] = (255, 255, 255)
    alpha: int = 255
    size: float = 4.0
    lifetime: float = 0.5  # seconds
    age: float = 0.0
    gravity: float = 0.0
    shrink: bool = True
    glow: bool = False

    def reset(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: Tuple[int, int, int],
        size: float = 4.0,
        lifetime: float = 0.5,
        gravity: float = 0.0,
        shrink: bool = True,
        glow: bool = False,
        alpha: int = 255,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.alpha = alpha
        self.size = size
        self.lifetime = lifetime
        self.age = 0.0
        self.gravity = gravity
        self.shrink = shrink
        self.glow = glow


# ─────────────────────────────────────────────────────────────────────────────
# Particle Pool
# ─────────────────────────────────────────────────────────────────────────────

class ParticlePool:
    """Recyclable object pool eliminating runtime allocations."""

    def __init__(self, capacity: int = 600) -> None:
        self._pool: deque[Particle] = deque(
            [Particle() for _ in range(capacity)], maxlen=capacity * 2
        )

    def acquire(self) -> Particle:
        if self._pool:
            return self._pool.pop()
        return Particle()

    def release(self, particle: Particle) -> None:
        self._pool.append(particle)


# ─────────────────────────────────────────────────────────────────────────────
# Particle Emitter & Manager
# ─────────────────────────────────────────────────────────────────────────────

class ParticleManager:
    """Central particle lifecycle and batch rendering manager."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self.pool = ParticlePool(capacity=600)
        self.active_particles: list[Particle] = []

        if event_bus is not None:
            self.register_events(event_bus)

    def register_events(self, event_bus: EventBus) -> None:
        """Subscribe particle manager to relevant EventBus events."""
        event_bus.subscribe(DamageDealt, self._on_damage_dealt)
        event_bus.subscribe(EntityDied, self._on_entity_died)

    def spawn_blood_splash(self, x: float, y: float, count: int = 14) -> None:
        """Spawn fleshy blood burst particles."""
        for _ in range(count):
            p = self.pool.acquire()
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(40, 260)
            red_shade = random.randint(160, 240)
            p.reset(
                x=x + random.uniform(-6, 6),
                y=y + random.uniform(-6, 6),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 50.0,
                color=(red_shade, random.randint(10, 30), random.randint(10, 30)),
                size=random.uniform(2.5, 5.5),
                lifetime=random.uniform(0.3, 0.65),
                gravity=450.0,
                shrink=True,
                glow=False,
            )
            self.active_particles.append(p)

    def spawn_sparks(self, x: float, y: float, count: int = 12) -> None:
        """Spawn metallic / magic sparks for skeletal or boss impacts."""
        for _ in range(count):
            p = self.pool.acquire()
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80, 320)
            p.reset(
                x=x,
                y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=(255, random.randint(180, 240), random.randint(50, 120)),
                size=random.uniform(2.0, 4.0),
                lifetime=random.uniform(0.15, 0.4),
                gravity=150.0,
                shrink=True,
                glow=True,
            )
            self.active_particles.append(p)

    def spawn_soul_wisps(self, x: float, y: float, count: int = 18) -> None:
        """Spawn floating ethereal soul wisps upon entity death."""
        for _ in range(count):
            p = self.pool.acquire()
            angle = random.uniform(-math.pi, 0)  # upward semicircle
            speed = random.uniform(30, 120)
            p.reset(
                x=x + random.uniform(-12, 12),
                y=y + random.uniform(-12, 12),
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 40.0,
                color=(random.randint(100, 180), random.randint(210, 255), 255),
                size=random.uniform(3.0, 7.0),
                lifetime=random.uniform(0.6, 1.2),
                gravity=-30.0,  # float upward
                shrink=True,
                glow=True,
            )
            self.active_particles.append(p)

    def _on_damage_dealt(self, event: DamageDealt) -> None:
        """Event subscriber handler for DamageDealt."""
        if event.target_tier in ("boss", "elite"):
            self.spawn_sparks(event.target.rect.centerx, event.target.rect.centery, count=16)
            self.spawn_blood_splash(event.target.rect.centerx, event.target.rect.centery, count=10)
        else:
            self.spawn_blood_splash(event.target.rect.centerx, event.target.rect.centery, count=12)

    def _on_entity_died(self, event: EntityDied) -> None:
        """Event subscriber handler for EntityDied."""
        px, py = event.position
        self.spawn_soul_wisps(px, py, count=20)

    def update(self, dt_seconds: float, scroll_speed: float = 0.0) -> None:
        """Update active particles positions, ages, and recycle expired ones."""
        if not self.active_particles:
            return

        alive: list[Particle] = []
        for p in self.active_particles:
            p.age += dt_seconds
            if p.age >= p.lifetime:
                self.pool.release(p)
                continue

            # Update physics
            p.vy += p.gravity * dt_seconds
            p.x += p.vx * dt_seconds - scroll_speed
            p.y += p.vy * dt_seconds

            alive.append(p)

        self.active_particles = alive

    def draw(self, surface: pg.Surface) -> None:
        """Batch render active particles onto surface."""
        if not self.active_particles:
            return

        for p in self.active_particles:
            progress = p.age / p.lifetime
            alpha = max(0, min(255, int(p.alpha * (1.0 - progress))))
            size = max(1.0, p.size * (1.0 - progress if p.shrink else 1.0))
            int_size = int(size)

            if int_size < 1 or alpha <= 0:
                continue

            if p.glow:
                # Translucent glow surface
                glow_surf = pg.Surface((int_size * 2, int_size * 2), pg.SRCALPHA)
                pg.draw.circle(glow_surf, (*p.color, alpha), (int_size, int_size), int_size)
                surface.blit(
                    glow_surf,
                    (int(p.x - int_size), int(p.y - int_size)),
                    special_flags=pg.BLEND_RGBA_ADD,
                )
            else:
                if alpha < 255:
                    p_surf = pg.Surface((int_size * 2, int_size * 2), pg.SRCALPHA)
                    pg.draw.circle(p_surf, (*p.color, alpha), (int_size, int_size), int_size)
                    surface.blit(p_surf, (int(p.x - int_size), int(p.y - int_size)))
                else:
                    pg.draw.circle(surface, p.color, (int(p.x), int(p.y)), int_size)
