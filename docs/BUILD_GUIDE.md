# NxNative 构建使用说明（Google Drive 版）

本说明对应仓库中的 [`.github/workflows/build.yml`](../.github/workflows/build.yml)。该工作流从 Google Drive 下载游戏文件和 `prod.keys`，在 GitHub Actions 提供的 macOS 构建环境中执行 NxNative 构建。无需在本地安装 macOS、Xcode 或 NxNative 编译环境。

> 请仅使用你依法有权使用的游戏备份和密钥。不要把游戏文件、`prod.keys`、百度网盘凭据或可公开访问的下载链接提交到仓库或公开发布。

## 1. 工作流特点

- 游戏输入来源：Google Drive 分享链接，通过 GitHub Secrets 保存。
- 支持设备构建路径：BC fallback、Standard。
- 游戏文件支持：直接 NSP/XCI/NSZ/XCZ 包；或包含这些包的 RAR 压缩包。
- 可选输入：游戏更新、DLC、第二个 DLC。
- 构建输出：GitHub Actions Artifact，或选择上传到百度网盘。
- Standard 构建采用分阶段流程：先完成 Shader Split，并单独交付 `RomFS.img`，再继续 Metal 编译和 IPA 打包；BC fallback 沿用其 bundled-RomFS 构建路径。
- 工作流会清理下载/解压中间文件，并运行磁盘空间监控和构建后审计。

## 2. 准备文件

准备以下文件：

| 文件 | 必需 | 说明 |
|---|---|---|
| 游戏本体 | 是 | NSP、XCI、NSZ、XCZ，或包含受支持游戏包的 RAR |
| `prod.keys` | 是 | 与游戏文件匹配的密钥文件 |
| 游戏更新 | 否 | 需要使用更新时提供 |
| DLC | 否 | 需要使用 DLC 时提供 |
| 第二个 DLC | 否 | 需要使用第二组 DLC 时提供 |

工作流会尝试自动识别基础游戏 Title ID。请确保输入的游戏包中能够识别出唯一的基础游戏 Title ID；如果自动识别失败，可在运行时填写手动 Profile ID。

## 3. 将文件上传到 Google Drive

1. 登录 [Google Drive](https://drive.google.com/)。
2. 上传游戏本体（或 RAR 压缩包）、`prod.keys`，以及需要使用的更新和 DLC。
3. 对每个需要下载的文件分别设置共享权限：
   - 打开文件的“共享”设置。
   - 将“常规访问权限”设为“知道链接的任何人”。
   - 权限保持为“查看者”。
   - 复制该文件的分享链接。
4. 确认链接对应的是正确文件，且文件已上传完成。

**隐私提醒：**“知道链接的任何人”意味着获得链接的人可能访问文件。不要公开发布这些链接；构建完成后，可按需将文件权限恢复为受限。

## 4. 配置 GitHub Secrets

打开仓库：

**Settings → Secrets and variables → Actions → New repository secret**

按下表创建 Secret。名称必须完全一致，注意大小写和下划线。

| Secret 名称 | 内容 | 必需 |
|---|---|---|
| `Game_URL` | Google Drive 游戏本体或 RAR 文件分享链接 | 是 |
| `Keys_URL` | `prod.keys` 文件分享链接 | 是 |
| `Update_URL` | 更新包分享链接 | 否 |
| `DLC_URL` | DLC 文件分享链接 | 否 |
| `DLC2_URL` | 第二个 DLC 文件分享链接 | 否 |
| `BDUSS` | 百度网盘登录凭据 | 仅选择百度网盘输出时需要 |
| `STOKEN` | 百度网盘登录凭据 | 仅选择百度网盘输出时需要 |

`Game_URL` 和 `Keys_URL` 必须配置。没有对应文件时，更新、DLC 和第二个 DLC 的 Secret 可以不创建。

如果输出目标选择 `baidu`，还需要配置 `BDUSS` 和 `STOKEN`。如果这两个 Secret 未配置，工作流会警告并自动回退到 GitHub Artifact，不会因此改用百度网盘作为输入来源。

不要把 `prod.keys` 文件内容直接粘贴到 Secret；工作流需要的是可下载文件的 Google Drive 分享链接。

## 5. 启动构建

1. 打开仓库的 **Actions** 页面。
2. 在左侧选择 **NxNative - Generic IPA Builder**。
3. 点击 **Run workflow**。
4. 选择要运行的分支（通常为 `main`）。
5. 按需填写以下参数：

| 参数 | 默认值 | 如何选择 |
|---|---|---|
| `device` | `iPhone 15 Pro/Pro Max or newer (standard)` | 根据目标设备和所需构建路径选择 |
| `profile_id` | 空 | 通常留空，使用自动识别；只有自动识别失败或确需指定基础游戏 Title ID 时填写 |
| `upload_target` | `artifact` | `artifact` 下载 GitHub Artifact；`baidu` 上传到百度网盘 |

### device 选项说明

- **iPhone 15 or older (BC fallback)：**选择固定版本的 BC fallback 构建路径。
- **iPhone 15 Pro/Pro Max or newer (standard)：**选择 Standard 上游构建路径。

这两个选项代表不同的构建路径，不代表对所有游戏或设备的兼容性保证。请根据目标设备及游戏实际情况选择。

### Profile ID

通常保持为空。工作流会从 NSP/XCI 等游戏包内容中检测基础游戏 Title ID。手动填写时应使用 **16 位十六进制 Title ID**，不要填写游戏名称、更新包 ID 或 DLC ID。

### 输出位置

- `artifact`：构建完成后，在本次 Actions 运行详情页的 Artifacts 区域下载。
- `baidu`：工作流会先验证百度网盘上传能力，再将 RomFS（Standard 路径需要时）和 IPA 上传到本次运行创建的独立目录，目录名称形如 `/NxNative-Build-运行编号-尝试编号`。

## 6. 查看构建进度

1. 启动后留在 **Actions** 页面。
2. 打开最新的一次 workflow run。
3. 点击 `build` Job 查看步骤日志。
4. 重点关注下载、游戏包识别、Title ID 检测、Shader Split、Metal 编译和 IPA 上传步骤。

工作流仅允许仓库所有者执行构建 Job。若由其他协作者触发，Job 不会执行。

### Standard 路径的两阶段构建

Standard 路径会先进行 Shader 处理和拆分，并在 Metal 编译前交付独立的 `RomFS.img`。之后重新进入缓存构建流程，释放不再需要的 Shader、RomFS 和 NSP 占用，再继续 Metal 编译并生成 IPA。这是为了降低 macOS Runner 在大型游戏构建时的磁盘峰值占用。

BC fallback 路径不使用这套独立 RomFS 交付流程，而使用其原有 bundled-RomFS 构建方式。

## 7. 下载构建结果

### GitHub Artifact

当 `upload_target=artifact`：

1. 打开本次 workflow run 的 Summary 页面。
2. 找到 **Artifacts**。
3. 下载 `NxNative-IPA-Standard` 或 `NxNative-IPA-BC-Fallback`。
4. GitHub 通常会下载 ZIP 文件，解压后取得 `.ipa`。

Standard 路径如果产生独立 RomFS，还会有 `NxNative-ROMFS` Artifact。构建日志会作为 `NxNative-Build-Logs` Artifact 上传。Artifact 默认保留 7 天。

### 百度网盘

当 `upload_target=baidu` 且凭据及上传预检通过时，IPA（以及 Standard 路径的 RomFS）会上传到日志中显示的本次运行专属目录。使用百度网盘客户端或其他方式打开该目录下载文件。

## 8. 常见问题

### Google Drive 下载失败

- 检查对应文件是否设置为“知道链接的任何人 / 查看者”。
- 检查 Secret 中是否粘贴了正确文件的分享链接。
- 确认文件已完整上传。
- 大文件可能受到 Google Drive 下载确认或临时流量限制影响。

工作流对下载执行最多三次尝试；多次失败时应先检查链接和共享权限。

### 缺少或无法读取 prod.keys

确认 `Keys_URL` 指向实际的 `prod.keys` 文件，而不是 Google Drive 文件夹或预览页面；同时确认密钥与游戏文件匹配。

### 无法识别游戏 Title ID

确认基础游戏包已正确下载、文件未损坏，并且包内包含可识别的 Title ID 信息。必要时在 `profile_id` 中填写基础游戏的 16 位十六进制 Title ID。

### 找不到游戏包或格式检查失败

Google Drive 版直接下载支持 NSP/XCI/NSZ/XCZ 包，也支持包含这些包的 RAR。检查文件是否完整、扩展名和实际文件内容是否一致。

### 百度网盘输出没有生效

确认已配置 `BDUSS` 和 `STOKEN`。工作流会先上传 1 MiB 预检文件；预检不通过时构建不会进入后续百度网盘输出流程。若凭据缺失，工作流会回退为 GitHub Artifact。

### 构建失败

打开失败步骤，先定位日志中**最早出现的实际错误**。后续错误可能只是前一个错误引起的连锁结果。可以提供失败步骤名称、设备选项和相关日志上下文进行分析；分享前请删除下载链接、Cookie、Token 等敏感信息。

## 9. 使用前检查清单

- [ ] 游戏本体和匹配的 `prod.keys` 已准备。
- [ ] 需要的更新和 DLC 已准备。
- [ ] Google Drive 文件链接可访问。
- [ ] `Game_URL` 和 `Keys_URL` 已配置。
- [ ] 如需更新/DLC，已配置对应可选 Secret。
- [ ] 如需百度网盘输出，已配置 `BDUSS` 和 `STOKEN`。
- [ ] 已选择正确的设备构建路径。
- [ ] 已确认输出目标。
- [ ] 构建完成后已下载 IPA，并检查构建日志。

---

**兼容性说明：**成功生成 IPA 不等于游戏一定能在目标 iPhone/iPad 上正常运行。实际结果还取决于游戏版本、设备、构建路径和游戏本身的兼容情况。
