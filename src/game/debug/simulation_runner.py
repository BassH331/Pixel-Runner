"""
SimulationRunner — Decoupled automated level and wave simulation report runner.

Handles frame tracking, position logging, physical/proximity collision checks,
exit condition detection, and JSON/Markdown report generation in scratch/.
"""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING, Any
import pygame as pg

if TYPE_CHECKING:
    from src.game.states.game_state import GameState


class SimulationRunner:
    """Manages head-less or automated simulation test runs and report generation."""

    def __init__(self, game_state: GameState) -> None:
        self.game = game_state

    def update_simulation(self, dt: float) -> None:
        """Track entities and check exit conditions during a simulation run."""
        if not getattr(self.game, "_is_simulating", False):
            return

        self.game._sim_log_counter += 1
        player_sprite = self.game.player.sprite
        if not player_sprite:
            return

        if getattr(self.game, "_sim_type", "level") == "wave":
            for obstacle in self.game.obstacle_group:
                from src.game.entities.skeleton import Skeleton
                if isinstance(obstacle, Skeleton):
                    enemy_id = getattr(obstacle, "_sim_id", None)
                    if enemy_id is None:
                        counter = getattr(self.game, "_sim_enemy_id_counter", 0) + 1
                        setattr(self.game, "_sim_enemy_id_counter", counter)
                        enemy_id = counter
                        setattr(obstacle, "_sim_id", enemy_id)
                        setattr(obstacle, "_sim_tracked", True)

                        enemy_data = {
                            "id": enemy_id,
                            "type": "skeleton",
                            "spawn_distance": float(self.game.world_distance),
                            "initial_x": obstacle.rect.x,
                            "initial_y": obstacle.rect.y,
                            "first_physical_collision": None,
                            "positions": [],
                        }
                        self.game._simulation_wave_enemies.append(enemy_data)
                        print(f"[SIM] Dynamic enemy #{enemy_id} (Skeleton) SPAWNED at world_dist={self.game.world_distance:.0f} screen=({obstacle.rect.x},{obstacle.rect.y})")
                    else:
                        enemy_data = next(
                            (e for e in self.game._simulation_wave_enemies if e["id"] == enemy_id),
                            None,
                        )
                        if enemy_data is not None:
                            if enemy_data["first_physical_collision"] is None:
                                if player_sprite.rect.colliderect(obstacle.rect):
                                    enemy_data["first_physical_collision"] = {
                                        "world_distance": float(self.game.world_distance),
                                        "screen_x": obstacle.rect.x,
                                        "screen_y": obstacle.rect.y,
                                    }
                                    print(f"[SIM] Dynamic enemy #{enemy_id} (Skeleton) PHYSICAL COLLISION at world_dist={self.game.world_distance:.0f}")

                            enemy_data["positions"].append((obstacle.rect.x, obstacle.rect.y))

            active_enemies = [
                f"#{getattr(s, '_sim_id')}@({s.rect.x},{s.rect.y})"
                for s in self.game.obstacle_group
                if getattr(s, "_sim_tracked", False)
            ]
            print(f"[SIM] frame={self.game._sim_log_counter} dist={self.game.world_distance:.0f} player@({player_sprite.rect.x},{player_sprite.rect.y}) | {' '.join(active_enemies)}")

        else:
            sim_targets = []
            for npc in self.game.npc_group:
                eid = getattr(npc, "event_id", None)
                if eid is not None:
                    sim_targets.append((npc, "npc"))
            for obstacle in self.game.obstacle_group:
                if getattr(obstacle, "is_boss", False):
                    eid = getattr(obstacle, "event_id", None)
                    if eid is not None:
                        sim_targets.append((obstacle, "boss"))

            for target, ttype in sim_targets:
                eid = getattr(target, "event_id")
                if eid not in self.game._simulation_npcs:
                    self.game._simulation_npcs[eid] = {
                        "id": eid,
                        "type": ttype if ttype == "boss" else ("wizard" if target.__class__.__name__ == "WizardNPC" else "generic"),
                        "title": getattr(target, "title" if ttype == "npc" else "boss_title", "Entity"),
                        "spawn_distance": self.game.world_distance,
                        "actual_scale": float(getattr(target, "scale", 1.0)),
                        "actual_radius": float(getattr(target, "proximity_radius", 160.0)),
                        "actual_width": target.image.get_width() if target.image else 0,
                        "actual_height": target.image.get_height() if target.image else 0,
                        "initial_x": target.rect.x,
                        "initial_y": target.rect.y,
                        "world_x": getattr(target, "world_x", None),
                        "positions": [],
                        "first_physical_collision": None,
                        "first_proximity_collision": None,
                    }
                    print(f"[SIM] NPC #{eid} '{self.game._simulation_npcs[eid]['title']}' SPAWNED at world_dist={self.game.world_distance:.0f} screen=({target.rect.x},{target.rect.y})")

                sim_npc = self.game._simulation_npcs[eid]
                if sim_npc["first_physical_collision"] is None:
                    if player_sprite.rect.colliderect(target.rect):
                        event_dist = float(getattr(target, "event_distance", 0.0))
                        sim_npc["first_physical_collision"] = {
                            "world_distance": float(self.game.world_distance),
                            "trigger_distance": event_dist,
                            "delta": float(self.game.world_distance - event_dist),
                        }
                        print(f"[SIM] NPC #{eid} '{sim_npc['title']}' PHYSICAL COLLISION at world_dist={self.game.world_distance:.0f}")

                if sim_npc["first_proximity_collision"] is None:
                    if ttype == "npc" and getattr(target, "_in_range", False):
                        event_dist = float(getattr(target, "event_distance", 0.0))
                        sim_npc["first_proximity_collision"] = {
                            "world_distance": float(self.game.world_distance),
                            "trigger_distance": event_dist,
                            "delta": float(self.game.world_distance - event_dist),
                        }
                        print(f"[SIM] NPC #{eid} '{sim_npc['title']}' PROXIMITY COLLISION at world_dist={self.game.world_distance:.0f}")

                self.game._simulation_npcs[eid]["positions"].append((target.rect.x, target.rect.y))

            npc_info = [f"#{getattr(t, 'event_id')}@({t.rect.x},{t.rect.y})" for t, _ in sim_targets]
            print(f"[SIM] frame={self.game._sim_log_counter} dist={self.game.world_distance:.0f} player@({player_sprite.rect.x},{player_sprite.rect.y}) | {' '.join(npc_info)}")

            triggered_expected_eids = [
                eid for eid, exp in self.game._simulation_expected_npcs.items()
                if exp["distance"] <= self.game.world_distance
            ]
            if triggered_expected_eids:
                all_spawned = all(eid in self.game._simulation_npcs for eid in triggered_expected_eids)
                all_offscreen = False
                if all_spawned:
                    all_offscreen = True
                    for npc in self.game.npc_group:
                        eid = getattr(npc, "event_id", None)
                        if eid in triggered_expected_eids and npc.rect.right >= 0:
                            all_offscreen = False
                            break
                    if all_offscreen:
                        for obstacle in self.game.obstacle_group:
                            eid = getattr(obstacle, "event_id", None)
                            if eid in triggered_expected_eids and getattr(obstacle, "is_boss", False):
                                from src.game.entities.skeleton import SkeletonState
                                if getattr(obstacle, "state", None) != SkeletonState.DEATH and getattr(obstacle, "_health", 0) > 0:
                                    all_offscreen = False
                                    break
                if all_spawned and all_offscreen:
                    self.write_simulation_report()
                    pg.quit()
                    sys.exit(0)

        self.game._simulation_timer += dt
        if self.game._simulation_timer >= self.game._simulation_duration * 1000:
            self.write_simulation_report()
            pg.quit()
            sys.exit(0)

    def write_simulation_report(self) -> None:
        """Write JSON and Markdown simulation reports to scratch/."""
        from src.game.entities.hitbox_registry import HitboxRegistry

        if getattr(self.game, "_sim_type", "level") == "wave":
            overall_passed = len(self.game._simulation_wave_enemies) > 0

            report_data = {
                "status": "PASSED" if overall_passed else "FAILED",
                "timestamp": pg.time.get_ticks(),
                "duration_ms": self.game._simulation_timer,
                "start_distance": getattr(self.game, "_sim_start_distance", 0.0),
                "final_distance": self.game.world_distance,
                "scroll_speed": self.game.max_bg_scroll_speed,
                "type": "wave",
                "enemies": self.game._simulation_wave_enemies,
            }

            markdown_lines = [
                "# Pixel-Runner Wave Simulation Report",
                "",
                f"**Overall Status:** {'PASSED ✅' if overall_passed else 'FAILED ❌'}",
                f"**Final Distance:** {self.game.world_distance:.1f}",
                f"**Simulation Duration:** {self.game._simulation_timer:.1f}ms",
                f"**Dynamic Enemies Spawned:** {len(self.game._simulation_wave_enemies)}",
                "",
            ]

            if not overall_passed:
                markdown_lines.append("## Issues Found")
                markdown_lines.append("1. No dynamic enemies spawned from configured spawn zones during the simulation.")
                markdown_lines.append("")

            for enemy in self.game._simulation_wave_enemies:
                eid = enemy["id"]
                markdown_lines.append(f"### Enemy #{eid} ({enemy['type'].capitalize()})")
                markdown_lines.append(f"- **Spawned at world_distance:** {enemy['spawn_distance']:.1f}m")
                markdown_lines.append(f"- **Initial Screen Position:** ({enemy['initial_x']}, {enemy['initial_y']})")

                phy = enemy.get("first_physical_collision")
                if phy:
                    markdown_lines.append(f"- **Physical Collision:** reached at world_distance={phy['world_distance']:.1f}m (Screen: ({phy['screen_x']}, {phy['screen_y']}))")
                else:
                    markdown_lines.append(f"- **Physical Collision:** None (no player collision detected)")

                positions = enemy.get("positions", [])
                if positions:
                    markdown_lines.append(f"- **Frames Tracked:** {len(positions)}")
                    samples = []
                    sample_indices = [0, len(positions) // 2, len(positions) - 1]
                    for si in sample_indices:
                        if 0 <= si < len(positions):
                            samples.append(f"Frame {si}: ({positions[si][0]}, {positions[si][1]})")
                    markdown_lines.append(f"- **Position Samples:** {', '.join(samples)}")
                markdown_lines.append("")

            os.makedirs("scratch", exist_ok=True)
            with open("scratch/simulation_report.json", "w") as f:
                json.dump(report_data, f, indent=4)

            with open("scratch/simulation_report.md", "w") as f:
                f.write("\n".join(markdown_lines))

            print(f"\n{'='*60}")
            print(f"[WAVE SIMULATION REPORT] Status: {report_data['status']}")
            print(f"  Distance: {report_data.get('start_distance', 0):.0f} → {self.game.world_distance:.0f}")
            print(f"  Duration: {self.game._simulation_timer:.0f}ms")
            print(f"  Dynamic Enemies Spawned: {len(self.game._simulation_wave_enemies)}")
            print(f"{'='*60}")
            return

        report_data = {
            "status": "PASSED",
            "timestamp": pg.time.get_ticks(),
            "duration_ms": self.game._simulation_timer,
            "start_distance": getattr(self.game, "_sim_start_distance", 0.0),
            "final_distance": self.game.world_distance,
            "scroll_speed": self.game.max_bg_scroll_speed,
            "npcs": [],
        }

        markdown_lines = [
            "# Pixel-Runner Simulation Report",
            "",
            f"**Final Distance:** {self.game.world_distance:.1f}",
            f"**Simulation Duration:** {self.game._simulation_timer:.1f}ms",
            f"**Scroll Speed:** {self.game.max_bg_scroll_speed} px/frame",
            "",
        ]

        overall_passed = True
        issues: list[str] = []

        for eid, exp in self.game._simulation_expected_npcs.items():
            ntype = exp["type"]
            reg_key = exp.get("registry_key", "generic_npc_")
            reg_margins = HitboxRegistry.get_margins(reg_key)

            npc_res: dict = {
                "id": eid,
                "type": ntype,
                "title": exp["title"],
                "registry_key": reg_key,
                "json_distance": exp["distance"],
                "json_scale": exp["scale"],
                "json_radius": exp["radius"],
                "registry_scale": reg_margins.scale,
                "registry_ground_offset": reg_margins.ground_offset,
                "spawned": False,
                "status": "NOT SPAWNED",
                "issues": [],
            }

            if abs(exp["scale"] - reg_margins.scale) > 0.01:
                npc_res["issues"].append(
                    f"Scale mismatch: level JSON has {exp['scale']}, "
                    f"entity_dimensions.json has {reg_margins.scale} for '{reg_key}'"
                )

            spawned_data = self.game._simulation_npcs.get(eid)
            if spawned_data:
                npc_res["spawned"] = True
                npc_res["actual_spawn_distance"] = spawned_data["spawn_distance"]
                npc_res["actual_scale"] = spawned_data["actual_scale"]
                npc_res["actual_radius"] = spawned_data["actual_radius"]
                npc_res["actual_width"] = spawned_data["actual_width"]
                npc_res["actual_height"] = spawned_data["actual_height"]
                npc_res["initial_screen_x"] = spawned_data["initial_x"]
                npc_res["initial_screen_y"] = spawned_data["initial_y"]
                npc_res["first_physical_collision"] = spawned_data.get("first_physical_collision")
                npc_res["first_proximity_collision"] = spawned_data.get("first_proximity_collision")

                positions = spawned_data["positions"]
                npc_res["total_frames_tracked"] = len(positions)

                dist_delta = abs(spawned_data["spawn_distance"] - exp["distance"])
                if dist_delta > 20:
                    npc_res["issues"].append(
                        f"Spawn distance mismatch: expected trigger at {exp['distance']}, "
                        f"but first detected at world_distance={spawned_data['spawn_distance']:.1f} "
                        f"(delta={dist_delta:.1f})"
                    )

                if abs(spawned_data["actual_scale"] - exp["scale"]) > 0.01:
                    npc_res["issues"].append(
                        f"Runtime scale mismatch: JSON says {exp['scale']}, "
                        f"but NPC spawned with scale={spawned_data['actual_scale']}"
                    )

                if abs(spawned_data["actual_radius"] - exp["radius"]) > 0.01:
                    npc_res["issues"].append(
                        f"Runtime radius mismatch: JSON says {exp['radius']}, "
                        f"but NPC spawned with radius={spawned_data['actual_radius']}"
                    )

                if len(positions) >= 5:
                    moved_left = positions[-1][0] < positions[0][0]
                    if not moved_left:
                        npc_res["issues"].append(
                            f"NPC did not scroll left: start_x={positions[0][0]}, end_x={positions[-1][0]}"
                        )
                    x_delta = positions[0][0] - positions[-1][0]
                    npc_res["total_x_scrolled"] = x_delta
                    npc_res["avg_scroll_per_frame"] = x_delta / len(positions) if positions else 0
                else:
                    npc_res["insufficient_data"] = True

                if "world_x" in spawned_data and spawned_data["world_x"] is not None:
                    last_x = positions[-1][0]
                    expected_x = spawned_data["world_x"] - self.game.world_distance
                    x_error = abs(last_x - expected_x)
                    npc_res["expected_screen_x"] = expected_x
                    npc_res["actual_screen_x"] = last_x
                    npc_res["screen_x_error"] = x_error
                    if x_error > 5:
                        npc_res["issues"].append(
                            f"Screen position mismatch: expected x={expected_x:.1f}, "
                            f"actual x={last_x:.1f}, error={x_error:.1f}"
                        )

                samples = []
                sample_indices = [0, len(positions) // 2, len(positions) - 1]
                for si in sample_indices:
                    if 0 <= si < len(positions):
                        samples.append({"frame": si, "x": positions[si][0], "y": positions[si][1]})
                npc_res["position_samples"] = samples

                if npc_res["issues"]:
                    npc_res["status"] = "FAILED"
                    overall_passed = False
                elif npc_res.get("insufficient_data"):
                    npc_res["status"] = "INCONCLUSIVE (too few frames)"
                else:
                    npc_res["status"] = "PASSED"
            else:
                if self.game.world_distance < exp["distance"]:
                    npc_res["status"] = "SKIPPED (not reached)"
                else:
                    npc_res["status"] = "FAILED"
                    npc_res["issues"].append(
                        f"NPC should have spawned at distance {exp['distance']}, "
                        f"world reached {self.game.world_distance:.1f} but NPC never appeared"
                    )
                    overall_passed = False

            issues.extend(npc_res["issues"])
            report_data["npcs"].append(npc_res)

            status_emoji = "✅" if npc_res["status"] == "PASSED" else "❌" if "FAILED" in npc_res["status"] else "⚠️"
            markdown_lines.append(f"### NPC #{eid}: {exp['title']} ({status_emoji} {npc_res['status']})")
            markdown_lines.append(f"- **Registry Key:** `{reg_key}`")
            markdown_lines.append(f"- **Trigger Distance:** JSON={exp['distance']}m | Spawned at={npc_res.get('actual_spawn_distance', 'N/A')}m")
            markdown_lines.append(f"- **Scale:** JSON={exp['scale']} | Registry={reg_margins.scale} | Runtime={npc_res.get('actual_scale', 'N/A')}")
            markdown_lines.append(f"- **Proximity Radius:** JSON={exp['radius']} | Runtime={npc_res.get('actual_radius', 'N/A')}")
            if spawned_data:
                markdown_lines.append(f"- **Image Dimensions:** {npc_res['actual_width']}×{npc_res['actual_height']}")
                markdown_lines.append(f"- **Initial Screen Pos:** ({npc_res['initial_screen_x']}, {npc_res['initial_screen_y']})")
                markdown_lines.append(f"- **Frames Tracked:** {npc_res['total_frames_tracked']}")
                markdown_lines.append(f"- **Total X Scrolled:** {npc_res.get('total_x_scrolled', 'N/A')}px")
                if npc_res.get("first_physical_collision"):
                    phy = npc_res["first_physical_collision"]
                    markdown_lines.append(f"- **Physical Collision:** reached at world_distance={phy['world_distance']:.1f}m (level editor trigger={phy['trigger_distance']}m, delta={phy['delta']:.1f}m)")
                else:
                    markdown_lines.append(f"- **Physical Collision:** None (no bounding box overlap)")

                if npc_res.get("first_proximity_collision"):
                    prox = npc_res["first_proximity_collision"]
                    markdown_lines.append(f"- **Proximity Collision:** reached at world_distance={prox['world_distance']:.1f}m (level editor trigger={prox['trigger_distance']}m, delta={prox['delta']:.1f}m)")
                else:
                    markdown_lines.append(f"- **Proximity Collision:** None (no interaction radius overlap)")
                if npc_res.get("position_samples"):
                    markdown_lines.append(f"- **Position Samples:**")
                    for s in npc_res["position_samples"]:
                        markdown_lines.append(f"  - Frame {s['frame']}: ({s['x']}, {s['y']})")
            else:
                markdown_lines.append(f"- **Spawned:** No")

            if npc_res["issues"]:
                markdown_lines.append(f"- **⚠ Issues:**")
                for issue in npc_res["issues"]:
                    markdown_lines.append(f"  - {issue}")
            markdown_lines.append("")

        if not overall_passed:
            report_data["status"] = "FAILED"

        if issues:
            markdown_lines.insert(2, f"**Overall Status:** FAILED ❌")
            markdown_lines.insert(3, "")
            markdown_lines.insert(4, "## Issues Found")
            for i, issue in enumerate(issues):
                markdown_lines.insert(5 + i, f"{i+1}. {issue}")
            markdown_lines.insert(5 + len(issues), "")
        else:
            markdown_lines.insert(2, f"**Overall Status:** PASSED ✅")

        os.makedirs("scratch", exist_ok=True)
        with open("scratch/simulation_report.json", "w") as f:
            json.dump(report_data, f, indent=4)

        with open("scratch/simulation_report.md", "w") as f:
            f.write("\n".join(markdown_lines))

        print(f"\n{'='*60}")
        print(f"[SIMULATION REPORT] Status: {report_data['status']}")
        print(f"  Distance: {report_data.get('start_distance', 0):.0f} → {self.game.world_distance:.0f}")
        print(f"  Duration: {self.game._simulation_timer:.0f}ms")
        for npc in report_data["npcs"]:
            status = npc['status']
            print(f"  NPC #{npc['id']} ({npc['title']}): {status}")
        print(f"{'='*60}")
