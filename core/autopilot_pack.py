"""Resolve the EP final video before building a publish package.

AutopilotCenter.pack() used to call publish_pack_engine.build(ep_id)
with no final_video, and build() rejects a missing final video, so
the button could never succeed. The EP record itself is the real
source: episode_pipeline stores final_video once the media/assemble
stages finish (see episode_pipeline.run_media). This helper reads
that record first and only calls build() when a non-empty final
video file actually exists; otherwise it says exactly what is
missing and where to generate it, instead of failing silently or
pretending success.
"""
import os


def resolve_and_build(episode_id, load_pipeline=None, build=None):
    episode_id = (episode_id or "").strip()
    if not episode_id:
        return {"success": False, "message": "请先输入 EP 编号（例如 EP-…），再打包发布。"}
    if load_pipeline is None:
        from core.episode_pipeline import episode_pipeline

        load_pipeline = episode_pipeline.load
    if build is None:
        from core.publish_pack_engine import publish_pack_engine

        build = publish_pack_engine.build
    try:
        record = load_pipeline(episode_id)
    except Exception as exc:
        return {
            "success": False,
            "message": f"EP {episode_id} 不存在或无法读取（{exc}）。请先在生产页创建并完成一集，再打包发布。",
        }
    final_video = record.get("final_video") if isinstance(record, dict) else None
    if not final_video or not os.path.isfile(final_video) or os.path.getsize(final_video) <= 0:
        return {
            "success": False,
            "message": (
                f"EP {episode_id} 的最终视频尚未生成，无法打包发布。"
                "请先在生产页完成媒体与剪辑阶段（或在工作流页完成一集并生成成片），"
                "生成最终视频后再点打包发布。"
            ),
        }
    return build(episode_id, final_video)
