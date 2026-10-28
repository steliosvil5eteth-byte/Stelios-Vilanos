"""Offline narration-safe scene segmentation; no rendering or publishing."""
import re

def sentence_chunks(script):
    ends = [m.end() for m in re.finditer(r'[.!?;…»](?=\s|$)', script)]
    ends = sorted(set([0] + ends + [len(script)]))
    return [script[a:b] for a, b in zip(ends, ends[1:]) if b > a]

def split_into_scenes(script, count=16):
    chunks = sentence_chunks(script)
    if len(chunks) < count:
        raise ValueError('Not enough sentence units for requested scenes')
    scenes, pos = [], 0
    for i in range(count):
        remaining_scenes = count - i
        max_take = len(chunks) - pos - (remaining_scenes - 1)
        target = len(script) / count
        take, size = (max_take if remaining_scenes == 1 else 1), len(chunks[pos])
        while take < max_take and abs(size + len(chunks[pos + take]) - target) < abs(size - target):
            size += len(chunks[pos + take]); take += 1
        scenes.append(''.join(chunks[pos:pos + take]))
        pos += take
    assert pos == len(chunks) and ''.join(scenes) == script
    return scenes
