# S3 v1 资源源文件

此目录是 v0.3.2 发布时使用的 S3 资源源，不是可直接导入的 ZIP。

- `season.json`：S3 赛季精灵编号、名称与属性。
- `spirits/`：与数据逐一对应的透明 PNG 图片。
- 图片命名：`No.编号 精灵名称.png`。

单独构建资源包：

```powershell
.venv\Scripts\python.exe scripts\build_content_pack.py `
  --season-file "content_sources\S3\season.json" `
  --spirits-dir "content_sources\S3\spirits" `
  --version 1 `
  --output "release\content\S3-v1.zip"
```

执行 `scripts/build_release.ps1 -Clean` 时，该资源包会自动生成，并预安装到 portable 成品的 `data/content`。
