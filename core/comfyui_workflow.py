import random


def build_sd15_txt2img_workflow(prompt, negative_prompt='', checkpoint='v1-5-pruned-emaonly.ckpt', width=512, height=512, steps=15, cfg=7.0, seed=None, filename_prefix='SciCloud_V40'):
    """Build a ComfyUI API-format SD1.5 txt2img workflow."""
    if seed is None or int(seed) < 0:
        seed = random.randint(0, 2**63 - 1)
    return {
        '3': {'class_type': 'KSampler', 'inputs': {
            'seed': int(seed), 'steps': int(steps), 'cfg': float(cfg),
            'sampler_name': 'euler', 'scheduler': 'normal', 'denoise': 1.0,
            'model': ['4', 0], 'positive': ['6', 0], 'negative': ['7', 0], 'latent_image': ['5', 0]
        }},
        '4': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': checkpoint}},
        '5': {'class_type': 'EmptyLatentImage', 'inputs': {'width': int(width), 'height': int(height), 'batch_size': 1}},
        '6': {'class_type': 'CLIPTextEncode', 'inputs': {'text': prompt or '', 'clip': ['4', 1]}},
        '7': {'class_type': 'CLIPTextEncode', 'inputs': {'text': negative_prompt or '', 'clip': ['4', 1]}},
        '8': {'class_type': 'VAEDecode', 'inputs': {'samples': ['3', 0], 'vae': ['4', 2]}},
        '9': {'class_type': 'SaveImage', 'inputs': {'filename_prefix': filename_prefix, 'images': ['8', 0]}},
    }
