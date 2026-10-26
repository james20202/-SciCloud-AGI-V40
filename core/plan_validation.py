"""Plan / storyboard validation, run before any render.

Plain Python only, no new dependency. This module deliberately does NOT
import the persistent bible store: a plan's own ``characters`` / ``scenes``
lists are the bible for that plan (DirectorPlanEngine builds them in the
plan itself, with ids such as CHAR-00001 / SCENE-00001, which are not
entries in data/bibles). Validating against the persistent store would
reject every normally generated plan, so refs are checked against the
plan that the shots belong to.

Rules (fail at plan time, with a shot-identified reason):
- plan / storyboard must be an object with a non-empty shots list
- every shot id must be present and unique
- every shot duration must be a finite number in (0, 3600]
- every shot scene ref must exist in the plan's scenes. A plan shot with
  no scene_id is an error: DirectorPlanEngine always sets one, and
  StoryboardDirector fills one in before this check runs on derived shots.
- every shot character ref must exist in the plan's characters. A shot
  with no character_ids falls back to the plan's first character (the
  StoryboardDirector behaviour), so it is only an error when the plan
  has no characters at all.
- every shot must have a non-empty prompt after expansion
  (visual_prompt or prompt).
- shot durations must sum to the episode target duration, within the
  same tolerance StoryboardDirector uses: max(0.1s, 0.5% of target).
"""

import math


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _ids(items):
    out = set()
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                out.add(str(item["id"]))
    return out


def _character_ids_of_shot(shot):
    raw = shot.get("character_ids")
    if raw is None:
        return None
    if isinstance(raw, list):
        ids = []
        for item in raw:
            if isinstance(item, dict):
                if item.get("id"):
                    ids.append(str(item["id"]))
            elif isinstance(item, str) and item:
                ids.append(item)
        return ids
    if isinstance(raw, str) and raw:
        return [raw]
    return []


def _prompt_of_shot(shot):
    for key in ("visual_prompt", "prompt"):
        value = shot.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _target_duration(plan, target_duration):
    if target_duration is not None:
        return target_duration
    if not isinstance(plan, dict):
        return None
    intent = plan.get("intent")
    if isinstance(intent, dict):
        for key in ("duration_seconds", "target_duration_seconds"):
            if intent.get(key) is not None:
                return intent[key]
    if plan.get("target_duration_seconds") is not None:
        return plan["target_duration_seconds"]
    return None


def _check_shots(shots, character_ids, scene_ids, errors):
    seen = set()
    for index, shot in enumerate(shots):
        label = "第 %d 个镜头" % (index + 1)
        if not isinstance(shot, dict):
            errors.append("%s 必须是对象" % label)
            continue
        shot_id = shot.get("id")
        if not isinstance(shot_id, str) or not shot_id.strip():
            errors.append("%s 缺少有效镜头 ID" % label)
        else:
            label = "镜头 %s" % shot_id
            if shot_id in seen:
                errors.append("镜头 ID 重复：%s" % shot_id)
            seen.add(shot_id)
        duration = shot.get("duration")
        if not _is_number(duration):
            errors.append("%s 时长必须是有限数字" % label)
        elif not 0 < float(duration) <= 3600:
            errors.append("%s 时长必须大于 0 且不超过 3600 秒" % label)
        scene_id = shot.get("scene_id")
        if not scene_id:
            errors.append("%s 缺少场景引用 scene_id" % label)
        elif str(scene_id) not in scene_ids:
            errors.append("%s 的场景引用 %s 在本计划场景中不存在" % (label, scene_id))
        char_ids = _character_ids_of_shot(shot)
        if char_ids is None:
            if not character_ids:
                errors.append("%s 没有人物指派，且本计划没有任何人物" % label)
        else:
            for char_id in char_ids:
                if char_id not in character_ids:
                    errors.append("%s 的人物引用 %s 在本计划人物中不存在" % (label, char_id))
        if not _prompt_of_shot(shot):
            errors.append("%s 缺少可用于生成的提示词（visual_prompt / prompt 为空）" % label)


def validate_plan(plan, target_duration=None):
    """Return a list of validation errors (empty list = valid)."""
    errors = []
    if not isinstance(plan, dict):
        return ["导演计划必须是对象"]
    shots = plan.get("shots")
    if not isinstance(shots, list) or not shots:
        return ["导演计划没有镜头，拒绝进入渲染"]
    character_ids = _ids(plan.get("characters"))
    scene_ids = _ids(plan.get("scenes"))
    _check_shots(shots, character_ids, scene_ids, errors)
    target = _target_duration(plan, target_duration)
    if target is not None:
        try:
            target_value = float(target)
        except (TypeError, ValueError):
            errors.append("导演计划目标时长无效")
            return errors
        if not math.isfinite(target_value) or target_value <= 0:
            errors.append("导演计划目标时长必须是有限正数")
        else:
            actual = 0.0
            ok = True
            for shot in shots:
                if isinstance(shot, dict) and _is_number(shot.get("duration")):
                    actual += float(shot["duration"])
                else:
                    ok = False
            if ok:
                tolerance = max(0.1, target_value * 0.005)
                if abs(actual - target_value) > tolerance:
                    errors.append(
                        "镜头总时长 %.3fs 与目标 %.3fs 不匹配，允许误差 ±%.3fs"
                        % (actual, target_value, tolerance)
                    )
    return errors


def validate_plan_or_raise(plan, target_duration=None):
    errors = validate_plan(plan, target_duration=target_duration)
    if errors:
        raise ValueError("导演计划校验失败：" + "；".join(errors))
    return True


def validate_storyboard(storyboard, plan=None):
    """Validate storyboard shots against the source plan's refs.

    When no plan is given, only shot shape, duration and prompt are
    checked; ref existence needs the plan. The per-shot duration-sum
    check against the plan target stays in StoryboardDirector, which
    already raises on mismatch, so it is not duplicated here.
    """
    errors = []
    if not isinstance(storyboard, dict):
        return ["分镜必须是对象"]
    shots = storyboard.get("shots")
    if not isinstance(shots, list) or not shots:
        return ["分镜没有镜头，拒绝进入渲染"]
    if plan is None:
        # Without a plan, ref existence cannot be judged, so only shot
        # shape, duration and prompt are checked here.
        for index, shot in enumerate(shots):
            if not isinstance(shot, dict):
                errors.append("第 %d 个镜头必须是对象" % (index + 1))
                continue
            if not _is_number(shot.get("duration")) or not 0 < float(shot.get("duration", 0)) <= 3600:
                errors.append("镜头 %s 时长必须是大于 0 且不超过 3600 秒的有限数字" % (shot.get("id") or (index + 1)))
            if not _prompt_of_shot(shot):
                errors.append("镜头 %s 缺少可用于生成的提示词" % (shot.get("id") or (index + 1)))
        return errors
    if not isinstance(plan, dict):
        return ["分镜来源导演计划必须是对象"]
    _check_shots(shots, _ids(plan.get("characters")), _ids(plan.get("scenes")), errors)
    return errors


def validate_storyboard_or_raise(storyboard, plan=None):
    errors = validate_storyboard(storyboard, plan=plan)
    if errors:
        raise ValueError("分镜校验失败：" + "；".join(errors))
    return True
