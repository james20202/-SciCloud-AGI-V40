# SciCloud AGI V40.7

## 连续性引擎
- 检查连续镜头的人物、场景、屏幕方向、景别、机位、光线与信息负载。
- 生成 continuity report 并保存到 `projects/continuity_reports/`。
- Prompt Engine 自动注入连续性约束。
- 支持 `screen_direction` 与 `axis_break` 标记，避免无意跳轴。
- 不把“检查通过”伪装成模型生成结果；这是导演/QC层检查。
