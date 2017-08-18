from seekers_types import *

import random
import copy
import utils


def tick(players, camps, goals, animations, world):
  seekers = [s for p in players for s in p.seekers]
  # move and recover seekers
  for s in seekers:
    s.move(world)
    if s.disabled():
      s.disabled_counter -= 1
  # compute magnetic forces and move goals
  for g in goals:
    force = Vector(0,0)
    for s in seekers:
      force += s.magnetic_force(world,g.position)
    g.acceleration = force
    g.move(world)
  # handle seeker collisions
  for i in range(0, len(seekers)):
    s = seekers[i]
    for j in range(i+1, len(seekers)):
      t = seekers[j]
      d = world.torus_distance(t.position,s.position)
      min_dist = s.radius + t.radius
      if d < min_dist: Seeker.collision(s,t,world,min_dist)
  # handle goals and scoring
  for i,g in enumerate(goals):
    for camp in camps:
      scored = g.camp_tick(camp)
    if scored: 
      goal_scored(g.owner, i, goals, animations, world) 
  # advance animations
  for _, animation_list in animations.items():
    for (i, a) in enumerate(animation_list):
      a.age += 1
      if a.age > a.duration:
        animation_list.pop(i)


def goal_scored(player, goal_index, goals, animations, world):
  player.score += 1
  g = goals[goal_index]
  goals[goal_index] = Goal(world.random_position())
  animations["score"].append(ScoreAnimation(g.position, player.color))



