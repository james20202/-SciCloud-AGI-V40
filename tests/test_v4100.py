from core.episode_pipeline import EpisodePipeline

def test_pipeline_contract():
    e=EpisodePipeline('/tmp/scicloud_v40_100_test')
    assert e.STAGES == ['plan','shots','media','assemble','qc','publish']
    assert callable(e.create) and callable(e.run) and callable(e.status)
print('V40.100_PIPELINE_CONTRACT_OK')
