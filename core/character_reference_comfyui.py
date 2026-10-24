"""Bind local character reference files to explicitly marked ComfyUI LoadImage nodes."""
import json
import mimetypes
import os
import uuid
from urllib import request, parse
from urllib.error import HTTPError


def _endpoint(model, path):
    return str(model.get("endpoint", "http://127.0.0.1:8188")).rstrip("/") + path


def _is_loopback(model):
    parsed = parse.urlparse(str(model.get("endpoint", "http://127.0.0.1:8188")))
    return parsed.scheme in ("http", "https") and parsed.hostname in ("localhost", "127.0.0.1", "::1")


def _upload_image(model, path, timeout=60):
    if not _is_loopback(model):
        raise ValueError("参考图只允许上传到本机 ComfyUI 回环地址")
    if not os.path.isfile(path) or os.path.getsize(path) <= 0:
        raise ValueError(f"参考图不存在或为空：{path}")
    boundary = "----SciCloudReference" + uuid.uuid4().hex
    filename = os.path.basename(path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with open(path, "rb") as stream:
        content = stream.read()
    chunks = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode(),
        content,
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\ninput\r\n".encode(),
        f"--{boundary}--\r\n".encode(),
    ]
    req = request.Request(_endpoint(model, "/upload/image"), data=b"".join(chunks), method="POST",
                          headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"ComfyUI 参考图上传失败：HTTP {exc.code} {detail}") from exc
    name = str(payload.get("name") or "").strip()
    if not name:
        raise RuntimeError("ComfyUI 上传接口没有返回文件名")
    subfolder = str(payload.get("subfolder") or "").strip()
    return "/".join(x for x in (subfolder, name) if x)


def bind_character_references(workflow, references, model, uploader=None):
    """Return a workflow copy and report. Only marked LoadImage nodes are changed.

    Mark a node by setting _meta.title to 'SciCloud Character Ref: <character id>'
    (or character name), or its image input to '__SCICLOUD_CHARACTER_REFERENCE__:<id>'.
    The ComfyUI workflow must be API-format JSON.
    """
    if isinstance(workflow, str):
        workflow = json.loads(workflow)
    if not isinstance(workflow, dict):
        raise ValueError("ComfyUI workflow 必须是 API 格式 JSON 对象")
    result = json.loads(json.dumps(workflow))
    refs = [r for r in (references or []) if isinstance(r, dict) and r.get("path")]
    if not refs:
        return result, {"success": True, "bound": 0, "warnings": []}
    if not _is_loopback(model):
        raise ValueError("角色参考图只允许发往本机 ComfyUI")
    candidates = []
    for node_id, node in result.items():
        if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
            continue
        if node.get("class_type") != "LoadImage":
            continue
        title = str((node.get("_meta") or {}).get("title") or "")
        image_value = str(node["inputs"].get("image") or "")
        marker = image_value.split(":", 1)[1].strip() if image_value.startswith("__SCICLOUD_CHARACTER_REFERENCE__:") else ""
        if title.startswith("SciCloud Character Ref:"):
            marker = title.split(":", 1)[1].strip()
        if marker:
            candidates.append((node_id, marker, node))
    warnings = []
    bound = 0
    upload = uploader or _upload_image
    for ref in refs:
        char_id = str(ref.get("character_id") or "").strip()
        char_name = str(ref.get("character_name") or "").strip()
        match = next((x for x in candidates if x[1] in (char_id, char_name)), None)
        if not match:
            warnings.append({"character_id": char_id, "character_name": char_name,
                             "message": "工作流没有匹配的 LoadImage 参考节点；仅保留文字锚点，图片没有注入模型"})
            continue
        node_id, marker, node = match
        if not os.path.isfile(str(ref.get("path") or "")) or os.path.getsize(ref["path"]) <= 0:
            warnings.append({"character_id": char_id, "character_name": char_name, "message": "角色参考图文件不存在或为空"})
            continue
        uploaded = upload(model, ref["path"])
        node["inputs"]["image"] = uploaded
        candidates.remove(match)
        bound += 1
    return result, {"success": bound == len(refs), "bound": bound, "requested": len(refs), "warnings": warnings}
