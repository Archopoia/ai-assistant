# Steps 08–15 — one-shot after raw.glb exists

```bash
python3 -m pipeline.cli character <name>
# or with an external generator mesh:
python3 -m pipeline.cli character <name> --glb /path/to/model.glb
```

## Manual Claude prompts (if driving step-by-step)

### 08 clean
```
Clean model.glb with a Blender script:
1. Turn it to face the engine's forward axis, feet on 0, height [1.15] m, apply transforms.
2. Merge vertices by distance and print the count of loose parts.
3. Recalculate normals; list flipped faces, holes and zero-length normals.
4. Decimate a copy to [budget] triangles, keep its UVs, and bake the base colour
   and a normal map from the original onto it.
5. Render front, side and back with a 5 cm grid and open them.
```

### 09 split
```
Tag every face as one part: head, torso, arm L/R, hand L/R, leg L/R, [coat, scarf, belt].
Use the texture colour and the position on the body.
Where two parts only touch (hand on coat, coat on leg), split the edge.
Render one flat colour per part, front and back, and open it.
```

### 10 joints
```
Render the model orthographic, front and side, 5 cm grid, labelled axes.
Write hips, spine, chest, neck, head, shoulders, elbows, wrists, knees, ankles
and toes to joints.json in metres. Draw them as dots on the renders and open them.
```

### 11 weights
```
Build the armature on joints.json. Long cloth below the hips gets 2 bones of its own,
front and back, children of Hips. Bind with automatic weights, then fix in code:
- torso and [collar, scarf, coat] get 0 on every arm bone
- the head bone moves only head and hair
- each hand is 100% on its hand bone, the head 100% on Head
- belt, pouches and sash go 100% on Hips
- the coat skirt goes on the cloth bones
- max 4 bones per vertex, then normalize
```

### 12 pose test
```
Pose test: arms up 90 degrees, arms forward 60, a step with each leg, head turned 60.
Render each pose front and side. For each pose print the longest stretched edge
against the rest pose and the 10 worst vertices with their bone.
Fix the weights there and rerun. Max 3 rounds, then show me what's left.
```

### 13–14 clips
```
Store the rest pose of this armature; every clip starts from it.
Write idle.py (2 s loop) and walk.py (1 s, two footsteps), 30 fps.
Then print foot slide, lowest vertex, hips range, first/last loop delta.
```

### 15 export
```
Export character.fbx: mesh, armature and all clips. Apply Transform off,
Add Leaf Bones off, scale 1.
```
