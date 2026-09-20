import pytest
import pygame as pg
from src.game.entities.skeleton import Skeleton, SkeletonState
from src.game.entities.fire_wizard import FireWizard, FireWizardState
from src.game.entities.bloo_zombie import BloodZombie, BloodZombieState
from src.game.entities.green_monster import GreenMonster, GatekeeperState
from src.game.entities.player import Player, PlayerState

@pytest.fixture(scope="module", autouse=True)
def setup_pg():
    pg.init()
    pg.display.set_mode((1, 1), pg.NOFRAME)

def test_skeleton_hit_frame_resets_on_state_change():
    player = Player(100, 100, None)
    skel = Skeleton(200, 100, player)
    
    # Init state should be IDLE/CHASE and not in hit frame
    skel.set_state(SkeletonState.IDLE, force=True)
    assert not skel.is_in_hit_frame()
    assert not skel.should_deal_damage()
    
    # Enter attack state
    skel._begin_attack()
    assert skel.state == SkeletonState.ATTACK
    
    # Move to hit frame index 6
    skel.animation_index = 6.0
    skel.update(16)
    assert skel.is_in_hit_frame()
    assert skel.should_deal_damage()
    
    # Force transition to CHASE state (e.g. state finish or hurt interrupt)
    skel.set_state(SkeletonState.CHASE, force=True)
    assert skel.state == SkeletonState.CHASE
    
    # Even at frame index 6 in CHASE, it MUST NOT be in hit frame or deal damage
    skel.animation_index = 6.0
    skel.update(16)
    assert not skel.is_in_hit_frame()
    assert not skel.should_deal_damage()

def test_fire_wizard_hit_frame_resets_on_state_change():
    player = Player(100, 100, None)
    fw = FireWizard(200, 100, player)
    
    fw.set_state(FireWizardState.IDLE, force=True)
    assert not fw.is_in_hit_frame()
    assert not fw.should_deal_damage()
    
    fw.set_state(FireWizardState.ATTACK, force=True)
    fw.animation_index = 6.0
    fw.update(16)
    assert fw.is_in_hit_frame()
    
    fw.set_state(FireWizardState.CHASE, force=True)
    fw.animation_index = 6.0
    fw.update(16)
    assert not fw.is_in_hit_frame()
    assert not fw.should_deal_damage()

def test_blood_zombie_hit_frame_resets_on_state_change():
    player = Player(100, 100, None)
    bz = BloodZombie(200, 100, player)
    
    bz.set_state(BloodZombieState.IDLE, force=True)
    assert not bz.is_in_hit_frame()
    assert not bz.should_deal_damage()
    
    bz._begin_attack()
    bz.animation_index = 6.0
    bz.update(16)
    assert bz.is_in_hit_frame()
    
    bz.set_state(BloodZombieState.CHASE, force=True)
    bz.animation_index = 6.0
    bz.update(16)
    assert not bz.is_in_hit_frame()
    assert not bz.should_deal_damage()

def test_player_hit_frame_resets_on_state_change():
    pl = Player(100, 100, None)
    
    pl.set_state(PlayerState.IDLE, force=True)
    assert not pl.is_in_hit_frame()
    assert not pl.should_deal_damage()
    
    pl.attack_thrust()
    pl.animation_index = 2.0
    pl.update(16)
    assert pl.is_in_hit_frame()
    
    pl.set_state(PlayerState.RUN, force=True)
    pl.animation_index = 2.0
    pl.update(16)
    assert not pl.is_in_hit_frame()
    assert not pl.should_deal_damage()
