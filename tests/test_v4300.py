import tempfile, os
from core.auto_episode import AutoEpisodeDirector

x=AutoEpisodeDirector()
old=x.root
x.root=tempfile.mkdtemp()
r=x.create('中式恐怖短剧：道士进入废弃凶宅，遇到红衣女鬼，结尾留下悬念',duration=60)
assert r['episode_id'].startswith('EP-')
s=x.status(r['episode_id'])
assert s['progress'] >= 0
print('V40.300_AUTO_EPISODE_OK')
x.root=old
