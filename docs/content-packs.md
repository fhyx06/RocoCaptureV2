# 赛季资源包

RocoCapture V2 使用“内置资源 + 本地覆盖包”的内容架构。应用始终保留内置赛季作为离线兜底，本地包按赛季 ID 补充或覆盖内置数据。

## 用户导入

1. 打开“设置 → 赛季资源”。
2. 点击“导入资源包”并选择 ZIP。
3. 应用会验证格式、文件清单、SHA-256、图片类型和版本兼容性。
4. 重新启动应用，使所有页面和图标统一使用新资源。

资源安装在程序目录下的 `data/content/`。每次激活新包前都会保存资源配置快照，“回滚”可恢复上一次配置；已下载的包不会立即删除。

## 包结构

```text
S3-v1.zip
├── manifest.json
├── season.json
└── spirits/
    ├── NO.030 恶魔叮.png
    └── NO.401 示例精灵.png
```

`season.json` 沿用内置赛季格式：

```json
{
  "season": "S3",
  "label": "S3 赛季异色追踪总览",
  "spirits": [
    {"no": 401, "name": "示例精灵", "elements": ["火"]}
  ]
}
```

`manifest.json` 示例：

```json
{
  "schema_version": 1,
  "pack_id": "S3",
  "pack_version": 1,
  "season": "S3",
  "min_app_version": "0.3.2",
  "files": {
    "season.json": "<sha256>",
    "spirits/NO.401 示例精灵.png": "<sha256>"
  }
}
```

同一赛季导入更高 `pack_version` 后，新版本会成为活动资源。`min_app_version` 高于当前应用版本时，应用会拒绝导入并提示先更新程序。

精灵编号在所有赛季中被视为稳定身份。同一编号可以在覆盖包中修正名称，旧存档的保底会自动迁移到新名称；不同精灵不能重复使用同一编号。

## 构建资源包

在项目根目录运行：

```powershell
.venv\Scripts\python.exe scripts\build_content_pack.py `
  --season-file src\assets\seasons\S3.json `
  --spirits-dir src\assets\spirits\S3 `
  --version 1 `
  --output release\content\S3-v1.zip
```

脚本会验证赛季 JSON 和 PNG，自动生成逐文件 SHA-256 清单并输出可导入 ZIP。

## 安全限制

- 只接受 `manifest.json`、`season.json` 和 `spirits/*.png`。
- 拒绝绝对路径、目录穿越、反斜杠路径、符号链接和加密 ZIP。
- 限制文件数量、单文件大小及总解压大小。
- 所有清单内文件必须通过 SHA-256 校验。
- 安装先进入同磁盘临时目录，验证完成后再原子切换活动索引。
- 资源包不能包含或执行 Python、DLL、脚本等程序代码。
