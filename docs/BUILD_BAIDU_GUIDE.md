# NxNative 构建使用说明（百度网盘版）

本说明对应仓库中的 [`.github/workflows/build-baidu.yml`](../.github/workflows/build-baidu.yml)。该工作流直接从百度网盘下载游戏目录、`prod.keys` 和可选更新/DLC，在 GitHub Actions 提供的 macOS 构建环境中执行 NxNative 构建。

与 Google Drive 版不同，百度网盘版**必须使用百度网盘作为构建输入来源**；即使最终选择将 IPA 上传为 GitHub Artifact，也仍然需要配置百度网盘登录凭据。

> 请仅使用你依法有权使用的游戏备份和密钥。不要把游戏文件、`prod.keys` 或百度网盘登录凭据提交到仓库或公开发布。

## 1. 工作流特点

- 游戏输入来源：百度网盘，通过运行时填写的网盘路径指定。
- 游戏本体输入：填写一个网盘目录，工作流递归下载目录内容，并筛选其中所有 `.nsp` 和 `.xci` 文件。
- 密钥输入：填写单个 `prod.keys` 文件路径。
- 可选输入：单个更新包、DLC、第二个 DLC 文件路径。
- 输出位置：GitHub Artifact 或百度网盘。
- 设备构建路径：BC fallback、Standard。
- Standard 路径采用 Shader Split / RomFS 先行交付，再释放空间并继续 Metal 编译；BC fallback 使用原有 bundled-RomFS 构建方式。

## 2. 准备百度网盘目录

建议先在百度网盘中整理好文件，路径清晰且避免重名。

例如：

```text
/游戏备份/目标游戏/
├── BaseGame.nsp
├── 其他游戏内容.xci
/游戏备份/密钥/prod.keys
/游戏备份/更新/Update.nsp
/游戏备份/DLC/DLC.nsp
```

以上仅为目录组织示例，实际路径以你网盘中的路径为准。

### 游戏目录要求

`game_path` 必须填写**游戏文件所在目录**，而不是某一个 NSP/XCI 文件路径。工作流会递归下载该目录，并从下载内容中筛选所有 `.nsp` 和 `.xci` 文件。

- 可以在同一目录或其子目录中放置基础游戏、更新或其他 NSP/XCI 包。
- 工作流会将找到的所有 NSP/XCI 文件作为游戏包输入进行后续处理。
- 如果目录内没有找到 NSP/XCI，构建会在下载/筛选阶段失败。
- 如果不同子目录存在同名 NSP/XCI 文件，工作流会因文件名重复而停止。
- 该目录筛选步骤只选择 `.nsp` 和 `.xci`；不要把 NSZ/XCZ 或 RAR 压缩包当作游戏目录中的直接游戏包输入。

### prod.keys 和可选文件

- `keys_path`：必须指向一个具体的 `prod.keys` 文件，不能填写文件夹。
- `update_path`：可选，填写一个更新文件路径。
- `dlc_path`：可选，填写一个 DLC 文件路径。
- `dlc2_path`：可选，填写第二个 DLC 文件路径。

这些单文件路径必须分别指向一个文件，不能指向目录或包含多个文件的路径。更新/DLC 文件后续处理支持直接 NSP/XCI/NSZ/XCZ 包或 RAR 压缩包；但基础游戏目录的递归筛选只选择 NSP/XCI。

## 3. 配置百度网盘凭据

打开仓库：

**Settings → Secrets and variables → Actions → New repository secret**

创建以下两个 Repository Secrets：

| Secret 名称 | 内容 | 必需 |
|---|---|---|
| `BDUSS` | 百度网盘登录凭据中的 BDUSS 值 | 是 |
| `STOKEN` | 百度网盘登录凭据中的 STOKEN 值 | 是 |

两个 Secret 名称必须完全一致，区分大小写。

**注意：**
- 不需要把游戏文件或 `prod.keys` 上传到 GitHub 仓库。
- 不要把 BDUSS、STOKEN 写入 YAML、README、Issue 或公开日志。
- 百度网盘版在下载输入文件之前就会检查这两个 Secret；缺少任意一个都会直接终止。
- 即使 `upload_target` 选择 `artifact`，下载游戏和密钥仍需要这两个凭据。

## 4. 启动构建

1. 打开仓库的 **Actions** 页面。
2. 在左侧选择 **NxNative - Generic IPA Builder** 对应的百度网盘工作流（文件为 `.github/workflows/build-baidu.yml`）。
3. 点击 **Run workflow**。
4. 选择工作流所在分支（通常为 `main`）。
5. 填写以下参数：

| 参数 | 必需 | 填写内容 |
|---|---|---|
| `device` | 是 | 选择 BC fallback 或 Standard |
| `profile_id` | 否 | 通常留空，自动识别 Title ID |
| `game_path` | 是 | 百度网盘中的游戏目录路径 |
| `keys_path` | 是 | 百度网盘中 `prod.keys` 的完整文件路径 |
| `update_path` | 否 | 更新包完整文件路径；没有则留空 |
| `dlc_path` | 否 | DLC 完整文件路径；没有则留空 |
| `dlc2_path` | 否 | 第二个 DLC 完整文件路径；没有则留空 |
| `upload_target` | 是 | `artifact` 或 `baidu` |

路径应使用百度网盘中的实际路径，例如：

```text
game_path: /游戏备份/目标游戏
keys_path: /游戏备份/密钥/prod.keys
update_path: /游戏备份/更新/Update.nsp
dlc_path: /游戏备份/DLC/DLC.nsp
dlc2_path:
```

请勿把示例路径原样照抄；替换为你自己的网盘路径。

### device 选项说明

- **iPhone 15 or older (BC fallback)：**选择固定版本的 BC fallback 构建路径。
- **iPhone 15 Pro/Pro Max or newer (standard)：**选择 Standard 上游构建路径。

这两个选项代表不同的构建路径，不是对所有游戏或设备的兼容性保证。

### Profile ID

通常保持为空，让工作流自动识别基础游戏 Title ID。自动识别失败或确需手动指定时，填写基础游戏的 **16 位十六进制 Title ID**。

### 输出目标

- `artifact`：将 IPA 作为 GitHub Actions Artifact 提供下载。
- `baidu`：将 RomFS（Standard 路径需要时）和 IPA 上传到百度网盘。

## 5. 工作流执行过程

工作流主要按以下顺序执行：

1. 检查 `BDUSS` 和 `STOKEN`，并登录百度网盘。
2. 如果输出目标选择百度网盘，则创建本次运行专属输出目录。
3. 当选择百度网盘输出时，先上传一个 1 MiB 预检文件，验证实际上传链路。
4. 递归下载 `game_path` 目录，筛选全部 NSP/XCI 文件。
5. 下载 `keys_path` 指定的密钥文件，以及填写的更新/DLC 文件。
6. 检查包格式，处理 RAR（适用于单文件更新/DLC等输入），准备游戏包。
7. 检测基础游戏 Title ID，准备 Shader 构建配置。
8. 执行 Shader Split；Standard 路径在 Metal 编译前先交付独立 RomFS。
9. 释放不再需要的中间文件和磁盘空间，继续 Metal 编译并生成 IPA。
10. 上传 IPA、构建日志，并清理 Runner 上的下载文件和密钥。

### 磁盘空间优化说明

该工作流并非简单地把所有下载文件长期保留到构建结束。它会在准备游戏包后删除原始下载和 RAR 解压中间目录，并通过仓库内的 CI guard 执行临时文件预清理、Shader/RomFS 空间释放和磁盘监控。

Standard 路径会先生成并交付 `RomFS.img`，然后重新进入缓存构建流程，在继续 Metal 编译前释放 Shader、RomFS 和 NSP 的空间占用。这样做是为了降低大型游戏构建时 Runner 的磁盘峰值需求。

BC fallback 不走独立 RomFS 交付步骤，使用其原本的 bundled-RomFS 构建路径。

## 6. 下载构建结果

### GitHub Artifact

如果 `upload_target=artifact`：

1. 打开本次 Actions 运行详情页。
2. 在 Summary 页面找到 **Artifacts**。
3. 下载 `NxNative-IPA-Standard` 或 `NxNative-IPA-BC-Fallback`。
4. 解压下载的 ZIP，取得 `.ipa` 文件。

Standard 构建如果产生独立 RomFS，还会提供 `NxNative-ROMFS` Artifact。构建日志作为 `NxNative-Build-Logs` Artifact 上传。Artifact 默认保留 7 天。

### 百度网盘

如果 `upload_target=baidu`：

- 工作流会在网盘根目录创建本次运行专属目录。
- 目录名称形如 `/NxNative-Build-运行编号-尝试编号`。
- IPA 会上传到该目录；Standard 路径需要单独交付 RomFS 时，`RomFS.img` 也会上传到同一目录。
- 上传前会先执行 1 MiB 预检。预检失败时，工作流会在正式构建前报错，不会等到构建结束才发现上传不可用。

## 7. 常见问题

### 提示缺少 BDUSS 或 STOKEN

检查仓库的 **Settings → Secrets and variables → Actions**，确认 `BDUSS` 和 `STOKEN` 均已创建，且名称拼写和大小写完全正确。百度网盘版无论输出目标选什么，都要求这两个凭据。

### 游戏目录下载后提示没有 NSP/XCI

确认 `game_path` 是目录路径，并且该目录或子目录中确实包含扩展名为 `.nsp` 或 `.xci` 的文件。该步骤不会把目录中的 NSZ/XCZ 或 RAR 当作游戏包筛选出来。

### 提示路径必须是单个文件

`keys_path`、`update_path`、`dlc_path` 和 `dlc2_path` 应指向单个文件。不要填写文件夹路径；可选路径没有对应文件时直接留空。

### 下载失败

确认网盘路径存在、当前账号有权限访问，并确认没有把文件路径和目录路径填反。工作流对单文件下载执行最多三次尝试；目录下载失败时应先检查目录路径和网盘访问权限。

### Title ID 检测失败

检查游戏目录是否同时包含多个不同游戏的 NSP/XCI，或基础游戏包是否缺少可识别的 Title ID 信息。必要时在 `profile_id` 中手动填写基础游戏的 16 位十六进制 Title ID。

### 百度网盘上传预检失败

检查 `BDUSS`、`STOKEN` 是否有效，以及百度网盘账号是否能够正常上传文件。预检在正式下载/构建前执行，避免构建完成后才发现无法上传。

### 构建失败

打开 Actions run，找到最早出现实际错误的步骤及其上下文。后续错误可能只是前一个错误引起的连锁结果。分享日志前，请删除凭据、Token、私有链接等敏感信息。

## 8. 使用前检查清单

- [ ] 百度网盘中已整理好游戏目录。
- [ ] 游戏目录中包含所需的 NSP/XCI 文件。
- [ ] `prod.keys` 已上传，且路径指向单个文件。
- [ ] 需要的更新和 DLC 已上传，路径指向对应单个文件。
- [ ] 仓库已配置 `BDUSS`。
- [ ] 仓库已配置 `STOKEN`。
- [ ] `game_path` 填写的是目录，不是单个 NSP/XCI 文件。
- [ ] `keys_path` 填写的是 `prod.keys` 文件路径。
- [ ] 已选择正确的设备构建路径和输出目标。
- [ ] 构建完成后已下载 IPA 或从百度网盘输出目录取得文件。

---

**兼容性说明：**构建成功只代表 IPA 已生成，不保证游戏一定能在目标设备上正常运行。实际结果取决于游戏版本、目标设备、构建路径及游戏自身兼容性。
