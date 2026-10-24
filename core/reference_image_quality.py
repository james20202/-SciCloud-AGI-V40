"""Advisory visual similarity checks for generated frames and character references.

Adapted from MIT-licensed tccnnd/Comic-drama/backend/consistency_validator.py:
normalized RGB histograms, average-hash structural comparison, and weighted scoring.
This is not face recognition and must not be treated as proof of identity.
"""
from pathlib import Path


def _compute_color_histogram(image_path, image_loader=None):
    try:
        if image_loader is None:
            from PIL import Image
        else:
            Image = image_loader
        image = Image.open(image_path).convert("RGB").resize((128, 128))
        bins = [0.0] * 24
        total = 128 * 128
        for red, green, blue in image.getdata():
            bins[red // 32] += 1
            bins[8 + green // 32] += 1
            bins[16 + blue // 32] += 1
        return [value / total for value in bins]
    except Exception:
        return None


def _histogram_similarity(hist_a, hist_b):
    if not hist_a or not hist_b or len(hist_a) != len(hist_b):
        return 0.0
    return min(1.0, sum(min(a, b) for a, b in zip(hist_a, hist_b)))


def _compute_structural_hash(image_path, hash_size=16, image_loader=None):
    try:
        if image_loader is None:
            from PIL import Image
        else:
            Image = image_loader
        image = Image.open(image_path).convert("L").resize((hash_size, hash_size))
        pixels = list(image.getdata())
        average = sum(pixels) / len(pixels)
        return "".join("1" if pixel > average else "0" for pixel in pixels)
    except Exception:
        return None


def _hamming_similarity(hash_a, hash_b):
    if not hash_a or not hash_b or len(hash_a) != len(hash_b):
        return 0.0
    return sum(a == b for a, b in zip(hash_a, hash_b)) / len(hash_a)


class ReferenceImageQualityEngine:
    def compare(self, generated_image, reference_image, character_name=""):
        generated = Path(str(generated_image or ""))
        reference = Path(str(reference_image or ""))
        if not generated.is_file() or generated.stat().st_size <= 0:
            return {"success": False, "character_name": character_name, "score": None,
                    "message": "生成图片不存在或为空", "status": "not_evaluated"}
        if not reference.is_file() or reference.stat().st_size <= 0:
            return {"success": False, "character_name": character_name, "score": None,
                    "message": "角色参考图不存在或为空", "status": "not_evaluated"}
        hist_gen = _compute_color_histogram(generated)
        hist_ref = _compute_color_histogram(reference)
        hash_gen = _compute_structural_hash(generated)
        hash_ref = _compute_structural_hash(reference)
        if not all((hist_gen, hist_ref, hash_gen, hash_ref)):
            return {"success": False, "character_name": character_name, "score": None,
                    "message": "图片相似度检查不可用；请确认 Pillow 已安装且图片可解码",
                    "status": "not_evaluated"}
        color_score = _histogram_similarity(hist_gen, hist_ref)
        structure_score = _hamming_similarity(hash_gen, hash_ref)
        score = round(0.55 * color_score + 0.45 * structure_score, 3)
        return {
            "success": True, "character_name": character_name, "score": score,
            "color_score": round(color_score, 3), "structure_score": round(structure_score, 3),
            "status": "review" if score < 0.60 else "informational",
            "message": "相似度启发式评分偏低，建议复核人物外观" if score < 0.60 else "相似度启发式评分已记录",
            "limitations": "颜色/整体结构启发式，不是人脸识别；姿势、背景、光线变化会影响分数。",
        }


reference_image_quality_engine = ReferenceImageQualityEngine()
