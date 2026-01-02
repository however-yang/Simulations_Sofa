# SOFA 肝脏牵拉与切割

这是一个可交互的 SOFA 场景：肝脏可形变，支持鼠标牵拉/固定，并提供可键盘控制的小棍切割工具。运行入口为 `liver_traction.py`。

## 功能

- 可形变肝脏（四面体 FEM），从 `liver3-HD.msh` 加载
- 鼠标牵拉与固定点
- 启用切割时，小棍会移除碰到的四面体
- 表面纹理贴图（使用 `liver2.png`，平面投影生成 UV）

## 环境要求

- SOFA v23.06（或兼容版本，需 GUI）
- SofaPython3 插件
- Linux 环境（已在 Ubuntu 22.04 测试）

## 快速运行

```bash
# 先激活你的 SOFA/conda 环境
LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH" \
runSofa -g qglviewer -l SofaPython3 liver_traction.py
```

如果 SofaPython3 无法加载，请确保 SOFA 构建与 Python 版本匹配，并确认
`LD_LIBRARY_PATH` 已包含环境的 `lib` 目录。

## 操作说明

- 鼠标：
  - 左键：牵拉（吸附）表面
  - 右键：固定点
- 小棍移动（数字小键盘 / 方向键）：
  - 8 / 2：Z+ / Z-
  - 4 / 6：X- / X+
  - 9 / 3：Y+ / Y-
- 切割：
  - P：切割开关
  - R：重置小棍位置

提示：使用键盘前先点击 3D 视窗确保焦点在场景中。

## 纹理说明

当前纹理是用平面投影生成 UV，再直接贴到表面上：

- 投影轴默认是 XZ（`axis_u=0, axis_v=2`）
- 如需改成 XY 或 YZ，在 `liver_traction.py` 里修改 `SurfaceUVProjector` 的参数即可
  - XY：`axis_u=0, axis_v=1`
  - YZ：`axis_u=1, axis_v=2`

## 文件说明

- `liver_traction.py`：主场景文件
- `liver3-HD.msh`：肝脏四面体网格（物理）
- `liver2.png`：肝脏表面纹理
- `liver3-HD.obj` / `liver3-HD.mtl`：备用表面网格与材质（当前场景未使用）
