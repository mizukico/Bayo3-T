# NxNative – Generic iOS IPA Builder

Build an unsigned iOS IPA from locally supplied Nintendo Switch game packages with the NxNative toolchain, using GitHub Actions. The workflow also supports exporting the standalone `RomFS.img` and final IPA to either GitHub Actions Artifacts or a Baidu Netdisk folder.

**Language:** English (default) · [简体中文](#简体中文)

> This repository contains the workflow and CI helper scripts. It does **not** include game files, title keys, a signed IPA, or any copyrighted game data. You must provide files that you are legally entitled to use.

## Contents

- [Overview](#overview)
- [Workflow inputs](#workflow-inputs)
- [Requirements and repository setup](#requirements-and-repository-setup)
- [Configure Actions secrets](#configure-actions-secrets)
- [Run a build](#run-a-build)
- [Build pipeline](#build-pipeline)
- [Outputs](#outputs)
- [Disk-space management](#disk-space-management)
- [Access control and security](#access-control-and-security)
- [Troubleshooting](#troubleshooting)
- [Implementation notes](#implementation-notes)

## Overview

The workflow is manually started with **Actions → NxNative - Generic IPA Builder → Run workflow**. It checks out an upstream NxNative source tree, applies CI-specific compatibility and disk-management patches, prepares the game packages, and builds an unsigned IPA on the configured `xcode-27` runner.

Two source paths are available:

| Build path | Source | Intended target |
| --- | --- | --- |
| Standard | [seedds/nxnative](https://github.com/seedds/nxnative), `main` | iPhone 15 Pro / Pro Max or newer; uses the standard path and separate RomFS handoff when supported |
| BC fallback | [mianmuhammadse/nxnative](https://github.com/mianmuhammadse/nxnative), pinned revision `d158df611bf2f3fa315c4f16585575cdfdb2a1d3` | iPhone 15 or older; uses the BC fallback path |

The standard source is currently checked out from the upstream `main` branch, so upstream changes can affect later builds. The BC fallback source is pinned to a specific commit.

## Workflow inputs

| Input | Choices / default | Description |
| --- | --- | --- |
| `device` | `iPhone 15 or older (BC fallback)` or `iPhone 15 Pro/Pro Max or newer (standard)`; default: Standard | Selects the NxNative source and build path. |
| `profile_id` | Default: `0100B8A026F14000`; may be left blank | Base-game title ID, exactly 16 hexadecimal characters. A non-empty value overrides automatic detection. If blank, the workflow attempts to detect the base title ID from the supplied package contents and filenames. |
| `upload_target` | `artifact` or `baidu`; default: `artifact` | Selects GitHub Actions Artifacts or Baidu Netdisk for build outputs. |

The profile ID is a **base game title ID**, not an update or DLC title ID. If automatic detection finds zero or multiple candidates, the workflow stops and asks for a valid manual override.

## Requirements and repository setup

1. A GitHub account with permission to run Actions in this repository. The build job additionally checks that the workflow actor is the repository owner.
2. The repository's Actions workflow enabled.
3. The required download URLs and title keys configured as repository Actions secrets (see below).
4. For Baidu upload, valid `BDUSS` and `STOKEN` secrets with permission to write to the target Netdisk account.
5. Game package files and keys that match the selected game and NxNative's supported input formats.

The workflow uses the `xcode-27` runner label and installs its required command-line dependencies during the run, including Python 3.13, .NET 10, and Homebrew packages such as `glslang`, `xcodegen`, `zstd`, `spirv-cross`, and `unar`.

### Supported package inputs

The preparation step accepts direct package downloads or RAR archives containing supported packages:

- Base game: required.
- Update: optional.
- DLC: optional.
- Second DLC package: optional.
- Package extensions: `.nsp`, `.xci`, `.nsz`, and `.xcz`.

Direct downloads must be recognized as NSP or XCI containers by their file signatures. RAR archives are extracted before the contained packages are validated. The workflow rejects unrecognized archives, invalid package signatures, duplicate output filenames, and an empty prepared-game directory.

The title keys file is downloaded separately as `prod.keys`. It is stored with restrictive file permissions during the run and removed during final cleanup.

## Configure Actions secrets

Open **Repository → Settings → Secrets and variables → Actions → New repository secret**. Secret names must match the names below exactly.

| Secret | Required? | Purpose |
| --- | --- | --- |
| `Game_URL` | Yes | Download URL for the base game package or RAR archive. |
| `Keys_URL` | Yes | Download URL for the `prod.keys` file. |
| `Update_URL` | No | Download URL for the update package or archive. |
| `DLC_URL` | No | Download URL for the first DLC package or archive. |
| `DLC2_URL` | No | Download URL for the second DLC package or archive. |
| `BDUSS` | Only for Baidu upload | Baidu Netdisk authentication cookie value. |
| `STOKEN` | Only for Baidu upload | Baidu Netdisk STOKEN value paired with BDUSS. |

The download step uses `gdown`; configure URLs that `gdown` can access. Keep these URLs in Actions secrets rather than hard-coding them in the workflow or README.

### Baidu upload behavior

When `upload_target=baidu`:

1. The workflow checks that both `BDUSS` and `STOKEN` are configured.
2. If either secret is missing, it emits a warning and switches the effective destination to GitHub Actions Artifacts.
3. If both are present, it installs BaiduPCS-Go, logs in, and creates a unique remote directory for the current run.
4. Before downloading the game files, it creates a 1 MiB random test file and uploads it with the same Baidu upload Action used for the real outputs.
5. The build proceeds only after the preflight upload step succeeds.

The preflight is intentional: it validates the configured Baidu credentials and upload path before the time-consuming game download and build stages. Do not remove it merely to shorten the workflow.

Each Baidu run uses a directory similar to `/NxNative-Build-<run-id>-<attempt>` in the Netdisk root. The RomFS image (when produced) and final IPA are uploaded to that directory.

## Run a build

1. Open the repository's **Actions** tab.
2. Select **NxNative - Generic IPA Builder**.
3. Click **Run workflow**.
4. Select the target device path.
5. Keep the default profile ID, enter a different 16-character hexadecimal base title ID, or clear the field to request automatic detection.
6. Choose `artifact` or `baidu` as the output destination.
7. Start the workflow and follow the run summary and step logs.

The build job contains an owner check: `github.actor == github.repository_owner`. A run started by a different actor will have its build job skipped.

## Build pipeline

The workflow is organized to validate upload capability early and reduce unnecessary disk duplication.

1. **Select the build path.** Check out the selected upstream NxNative source and this repository's CI helper script.
2. **Resolve the upload destination.** Determine whether to use GitHub Artifacts or Baidu Netdisk.
3. **Preflight Baidu, when selected.** Authenticate, create the unique remote folder, and upload a 1 MiB test file before downloading large inputs.
4. **Prepare the toolchain.** Set up Python and .NET, install dependencies, and remove only stale workflow-owned temporary directories.
5. **Download inputs.** Download the base game, keys, and any configured update/DLC packages. Download command output is suppressed so secret URLs are not deliberately echoed by `gdown`.
6. **Prepare game packages.** Extract RAR archives when needed, validate NSP/XCI container signatures, and move the prepared packages into `$RUNNER_TEMP/GameFiles`. Moving avoids retaining a second full copy of each package.
7. **Check and reclaim space.** Print available root-volume space, remove leftover download files and extracted archive directories, and keep the prepared packages for the build.
8. **Detect the profile.** Use the manual title ID if supplied; otherwise scan package contents and filenames for a unique base-game title ID.
9. **Patch the upstream build scripts for CI.** Apply guarded changes for shader processing, IoStore detection, RomFS handoff, and temporary-file lifetime.
10. **First build pass.** Run the upstream builder. On the standard separate-RomFS path, stop after shader splitting and stage the standalone `RomFS.img` for upload.
11. **Upload RomFS, when produced.** Upload it to the selected destination before the Metal compilation stage. The BC fallback path may use its original bundled-RomFS flow and may not produce a separate RomFS artifact.
12. **Second build pass.** Re-enter the build to reuse prepared extraction/rewrite/shader data, release no-longer-needed source data at safe points, and finish Metal compilation and IPA packaging. If the first pass already completed the IPA, the second build is skipped.
13. **Upload the IPA and diagnostics.** Upload the IPA to the selected destination and retain build logs as a GitHub Actions Artifact.
14. **Clean up.** Stop the disk monitor and remove temporary downloads, prepared game packages, keys, and temporary BaiduPCS-Go configuration from the runner.

## Outputs

### GitHub Actions Artifacts

When the effective destination is `artifact`, the workflow can produce:

| Artifact name | Contents | Retention |
| --- | --- | --- |
| `NxNative-ROMFS` | Standalone `RomFS.img`, only when the selected build path produces the separate image | 7 days |
| `NxNative-IPA-Standard` or `NxNative-IPA-BC-Fallback` | Final unsigned IPA | 7 days |
| `NxNative-Build-Logs` | Available build logs, survey output, disk-monitor log, and build console log | 7 days |

The ROMFS artifact is conditional. Do not assume it will exist for every game or build path. The final IPA artifact is required for a successful Artifact-target build.

### Baidu Netdisk

When Baidu upload is active, the workflow uploads the standalone RomFS image when available and the final IPA to the unique run directory created at the beginning of the run. GitHub build logs are still uploaded as the `NxNative-Build-Logs` artifact.

## Disk-space management

The workflow is designed around actual free-space measurements and the lifetime of large build intermediates.

- Before build processing, stale `GameFiles` and `nxnative` directories from a prior run are removed from the runner temporary directory. The pre-clean step does not delete Xcode, Homebrew, runner diagnostics, or user-wide caches.
- Downloaded game packages are moved, not copied, into `GameFiles`.
- After package preparation, the workflow reports available space using `df`, then deletes leftover download files and extracted RAR staging directories.
- A background monitor records root-volume free space periodically, build progress, and selected temporary-directory sizes. It also reserves a small emergency file so it can release space if free space becomes critically low.
- CI patches defer deletion of shader translator intermediates until upstream processing no longer needs them. They also release the original NSP/XCI packages after extraction, standalone RomFS after the upload handoff on the supported standard path, and consumed shader data after Metal compilation.
- A final disk report is collected even if the build fails.

The workflow no longer runs a separate pre-build Xcode installation/cache audit or a blanket Xcode cache-cleaning step. It does not assume that a fresh runner contains useful project build caches.

## Access control and security

- **Owner-only build job:** the job-level condition compares the triggering actor with the repository owner. A non-owner-triggered run is skipped; this condition does not hide the workflow run itself.
- **Public repository visibility:** on a public repository, workflow files, run metadata, and Actions logs may be visible to the public. The owner check is not a log-privacy mechanism. Use a private repository and appropriately restricted repository access if run logs must not be public.
- **Secrets:** never put download URLs, cookies, title keys, or other credentials directly in workflow YAML, README files, issue reports, or commits. Configure them as Actions secrets.
- **Download logging:** the `gdown` command's standard output and error output are suppressed during secret-URL downloads. This reduces accidental URL disclosure, but it is not a substitute for keeping the repository and its logs appropriately access-controlled.
- **Artifacts:** build logs may contain filenames, paths, tool output, and diagnostic information. Review repository visibility and artifact access permissions before sharing a run.
- **Local cleanup:** temporary game files and keys are removed from the ephemeral runner at the end of the job. This does not remove copies stored in the original download provider or Baidu Netdisk.

## Troubleshooting

| Symptom | Likely cause / action |
| --- | --- |
| Build job is skipped | The triggering actor is not the repository owner. Start the workflow using the owner account. |
| Baidu target falls back to Artifact | One or both of `BDUSS` and `STOKEN` are missing. Configure both secrets and rerun. |
| Baidu preflight upload fails | Check that both credentials are current, the account can upload, and the Baidu upload Action can reach the service. The workflow intentionally stops before downloading the game files. |
| Required download URL is empty | Configure `Game_URL` and `Keys_URL`; configure optional URLs only when the corresponding package is intended to be included. |
| Download fails after retries | Check the secret URL, sharing permissions, file availability, and whether `gdown` can access the link. |
| Package signature is invalid | The download may be an HTML confirmation page, an incomplete file, an unsupported format, or a mislabeled package. Verify the original file and URL. |
| No unique title ID is detected | Enter the correct 16-character hexadecimal base-game title ID in `profile_id`. |
| Disk-space check fails or the build runs out of space | Inspect the available-space check and `NxNative-Build-Logs` artifact, especially `disk-monitor.log` and `build-console.log`. Reduce unnecessary game/update/DLC inputs or use a runner with more available storage. |
| Upstream patch step cannot find an expected code anchor | The upstream source may have changed. The patch script deliberately fails rather than applying a partial or ambiguous edit. Review the upstream changes and update the CI patch before retrying. |
| RomFS artifact is absent | The selected path or game may not use the separate image-backed RomFS handoff. Check the first-pass log; the BC fallback path retains its original bundled-RomFS behavior. |

## Implementation notes

- Main workflow: [`.github/workflows/build.yml`](.github/workflows/build.yml)
- CI helper: [`.github/scripts/nxnative_ci_guard.py`](.github/scripts/nxnative_ci_guard.py)
- Standard upstream: [`seedds/nxnative`](https://github.com/seedds/nxnative)
- BC fallback upstream: [`mianmuhammadse/nxnative`](https://github.com/mianmuhammadse/nxnative)
- Baidu upload Action: [`CHC383/baidu-netdisk-upload-action`](https://github.com/CHC383/baidu-netdisk-upload-action)

The CI helper validates expected upstream code anchors before patching. If upstream code changes, the workflow may stop at the patch stage; this is intentional and safer than silently applying a patch to an unexpected source layout.

---

## 简体中文

# NxNative – 通用 iOS IPA 构建器

本项目通过 GitHub Actions 调用 NxNative 工具链，将用户自行提供的 Nintendo Switch 游戏文件构建为未签名 iOS IPA。工作流也支持将独立的 `RomFS.img`（如果构建路径会生成）和最终 IPA 上传到 GitHub Actions Artifacts 或百度网盘。

> 本仓库只包含工作流和 CI 辅助脚本，**不包含**游戏文件、title keys、已签名 IPA 或任何受版权保护的游戏数据。请自行提供有权使用的文件。

## 目录

- [项目概览](#项目概览)
- [工作流输入项](#工作流输入项)
- [运行要求与仓库设置](#运行要求与仓库设置)
- [配置 Actions Secrets](#配置-actions-secrets)
- [启动构建](#启动构建)
- [构建流程](#构建流程)
- [构建产物](#构建产物)
- [磁盘空间管理](#磁盘空间管理)
- [访问控制与安全](#访问控制与安全)
- [故障排查](#故障排查)
- [实现说明](#实现说明)

## 项目概览

在仓库的 **Actions → NxNative - Generic IPA Builder → Run workflow** 中手动启动构建。工作流会检出上游 NxNative 源码，应用 CI 专用兼容性和磁盘管理补丁，准备游戏文件，并在配置为 `xcode-27` 的 Runner 上构建未签名 IPA。

当前提供两条源码路径：

| 构建路径 | 源码 | 目标设备 |
| --- | --- | --- |
| Standard 标准路径 | [seedds/nxnative](https://github.com/seedds/nxnative)，`main` 分支 | iPhone 15 Pro / Pro Max 或更新机型；支持时使用独立 RomFS 交接流程 |
| BC fallback 兼容路径 | [mianmuhammadse/nxnative](https://github.com/mianmuhammadse/nxnative)，固定版本 `d158df611bf2f3fa315c4f16585575cdfdb2a1d3` | iPhone 15 或更旧机型；使用 BC fallback 构建路径 |

Standard 当前检出上游 `main` 分支，因此上游更新可能影响后续构建。BC fallback 固定在指定 commit。

## 工作流输入项

| 输入项 | 选项 / 默认值 | 说明 |
| --- | --- | --- |
| `device` | `iPhone 15 or older (BC fallback)` 或 `iPhone 15 Pro/Pro Max or newer (standard)`；默认 Standard | 选择 NxNative 源码和构建路径。 |
| `profile_id` | 默认 `0100B8A026F14000`；允许留空 | 游戏本体 Title ID，必须为 16 位十六进制字符。填写后覆盖自动识别；留空时尝试从游戏包内容和文件名中识别。 |
| `upload_target` | `artifact` 或 `baidu`；默认 `artifact` | 选择 GitHub Actions Artifacts 或百度网盘作为构建产物保存位置。 |

这里的 Profile ID 指**游戏本体 Title ID**，不是更新或 DLC 的 Title ID。如果自动识别结果为零个或多个候选值，工作流会停止，需要手动填写正确的 ID。

## 运行要求与仓库设置

1. 拥有可在本仓库运行 Actions 的 GitHub 账户。构建 Job 还会检查触发者是否为仓库 Owner。
2. 仓库已启用 GitHub Actions。
3. 已配置下文列出的下载地址和 keys Secrets。
4. 如需上传百度网盘，必须配置有效的 `BDUSS` 和 `STOKEN`，且账号具备网盘写入权限。
5. 准备与所选游戏匹配、且属于 NxNative 支持范围的游戏文件和 keys。

工作流使用 `xcode-27` Runner 标签，并在运行时安装所需命令行依赖，包括 Python 3.13、.NET 10，以及 `glslang`、`xcodegen`、`zstd`、`spirv-cross`、`unar` 等 Homebrew 软件包。

### 支持的游戏文件

准备步骤支持直接下载游戏包，也支持下载包含游戏包的 RAR 压缩档：

- 游戏本体：必需。
- 游戏更新：可选。
- DLC：可选。
- 第二个 DLC 包：可选。
- 支持的包扩展名：`.nsp`、`.xci`、`.nsz`、`.xcz`。

直接下载的文件必须通过文件签名识别为 NSP 或 XCI 容器。RAR 会先解压，再检查其中的游戏包。对于无法识别的压缩档、签名错误的游戏包、重复的输出文件名或空的游戏包目录，工作流会报错停止。

Title keys 文件会单独下载并保存为 `prod.keys`。构建期间会限制其文件权限，并在工作流最终清理阶段删除。

## 配置 Actions Secrets

进入 **Repository → Settings → Secrets and variables → Actions → New repository secret**。Secret 名称必须与下表完全一致。

| Secret | 是否必需 | 用途 |
| --- | --- | --- |
| `Game_URL` | 必需 | 游戏本体文件或 RAR 压缩档的下载地址。 |
| `Keys_URL` | 必需 | `prod.keys` 文件的下载地址。 |
| `Update_URL` | 可选 | 游戏更新文件或压缩档的下载地址。 |
| `DLC_URL` | 可选 | 第一个 DLC 文件或压缩档的下载地址。 |
| `DLC2_URL` | 可选 | 第二个 DLC 文件或压缩档的下载地址。 |
| `BDUSS` | 仅百度上传时需要 | 百度网盘认证 Cookie 值。 |
| `STOKEN` | 仅百度上传时需要 | 与 BDUSS 配套的百度网盘 STOKEN 值。 |

下载步骤使用 `gdown`，请配置 `gdown` 能够访问的下载地址。不要将这些地址硬编码进工作流、README、Issue 或提交记录中，应放入 Actions Secrets。

### 百度网盘上传机制

当 `upload_target=baidu` 时：

1. 工作流先检查 `BDUSS` 和 `STOKEN` 是否都已配置。
2. 如果任意一个缺失，会输出警告并自动切换为 GitHub Actions Artifacts。
3. 如果两个值都存在，则安装 BaiduPCS-Go、登录网盘，并为本次运行创建独立远程目录。
4. 在下载游戏文件之前，生成一个 1 MiB 随机测试文件，并使用正式构建相同的百度上传 Action 进行上传测试。
5. 只有预检上传成功，才会继续下载游戏文件和构建。

这个预检是有意保留的：它能在耗时较长的游戏文件下载和构建开始之前，验证百度网盘凭据和上传链路。不要为了缩短工作流而删除此步骤。

每次百度网盘构建会在网盘根目录创建类似 `/NxNative-Build-<run-id>-<attempt>` 的独立目录。RomFS 镜像（如果生成）和最终 IPA 都会上传到该目录。

## 启动构建

1. 打开仓库的 **Actions** 页面。
2. 选择 **NxNative - Generic IPA Builder**。
3. 点击 **Run workflow**。
4. 选择目标设备构建路径。
5. 保留默认 Profile ID、填写其他 16 位十六进制游戏本体 Title ID，或清空该字段以启用自动识别。
6. 选择 `artifact` 或 `baidu` 作为输出位置。
7. 启动工作流，并查看运行摘要和各步骤日志。

构建 Job 包含 Owner 检查：`github.actor == github.repository_owner`。由其他用户触发的运行，其构建 Job 会被跳过。

## 构建流程

工作流优先验证上传能力，并尽量减少大文件在磁盘上的重复占用。

1. **选择构建路径。** 检出对应的上游 NxNative 源码，以及本仓库的 CI 辅助脚本。
2. **确定上传目标。** 选择 GitHub Artifacts 或百度网盘。
3. **百度上传预检（仅百度模式）。** 登录、创建独立远程目录，并在下载大文件前上传 1 MiB 测试文件。
4. **准备工具链。** 配置 Python 和 .NET、安装依赖，并清理 Runner 临时目录中由本工作流管理的残留目录。
5. **下载输入文件。** 下载游戏本体、keys，以及已配置的更新和 DLC。下载命令的输出会被屏蔽，避免 `gdown` 主动将 Secret 下载地址打印到日志。
6. **准备游戏包。** 必要时解压 RAR，校验 NSP/XCI 容器签名，然后将游戏包移动到 `$RUNNER_TEMP/GameFiles`。使用移动而不是复制，避免同一份游戏包占用两份完整空间。
7. **检查并回收空间。** 使用 `df` 输出根卷可用空间，删除残留下载文件和 RAR 解压目录，保留后续构建所需的游戏包。
8. **识别 Profile。** 优先使用手动填写的 Title ID；否则扫描游戏包内容和文件名，识别唯一的游戏本体 Title ID。
9. **应用上游 CI 补丁。** 对 Shader 处理、IoStore 识别、RomFS 交接和临时文件生命周期应用带校验的补丁。
10. **第一轮构建。** 运行上游构建器。对于支持独立 RomFS 的 Standard 路径，在 Shader 拆分完成后暂停，并准备独立的 `RomFS.img` 上传。
11. **上传 RomFS（如果生成）。** 在 Metal 编译阶段之前，将其上传到选定位置。BC fallback 路径可能沿用原始内置 RomFS 流程，不一定生成独立 RomFS 产物。
12. **第二轮构建。** 重新进入构建流程，复用已准备的解包、重写和 Shader 数据，在安全时机释放不再需要的源文件，完成 Metal 编译和 IPA 打包。如果第一轮已经生成完整 IPA，则跳过第二轮。
13. **上传 IPA 和诊断日志。** 将 IPA 上传到所选位置，并将构建日志保存为 GitHub Actions Artifact。
14. **清理。** 停止磁盘监控，并从 Runner 中删除临时下载文件、准备好的游戏包、keys 和 BaiduPCS-Go 临时配置。

## 构建产物

### GitHub Actions Artifacts

当最终上传目标为 `artifact` 时，工作流可能生成以下产物：

| Artifact 名称 | 内容 | 保留时间 |
| --- | --- | --- |
| `NxNative-ROMFS` | 独立的 `RomFS.img`，仅在所选构建路径生成独立镜像时存在 | 7 天 |
| `NxNative-IPA-Standard` 或 `NxNative-IPA-BC-Fallback` | 最终未签名 IPA | 7 天 |
| `NxNative-Build-Logs` | 可用的构建日志、survey 输出、磁盘监控日志和构建控制台日志 | 7 天 |

RomFS Artifact 是有条件生成的，并非每个游戏或构建路径都会有。对于 Artifact 上传模式，最终 IPA Artifact 是成功构建所需的产物。

### 百度网盘

百度上传模式启用时，工作流会将独立 RomFS 镜像（如果生成）和最终 IPA 上传到本次运行创建的独立目录。GitHub 构建日志仍会作为 `NxNative-Build-Logs` Artifact 上传。

## 磁盘空间管理

工作流围绕实际可用空间和大型中间文件的生命周期进行管理。

- 构建前会清理 Runner 临时目录中上一次运行残留的 `GameFiles` 和 `nxnative`。预清理不会删除 Xcode、Homebrew、Runner 诊断文件或用户级缓存。
- 下载的游戏包会移动到 `GameFiles`，而不是复制。
- 游戏包准备完成后，工作流会通过 `df` 检查可用空间，再删除残留下载文件和 RAR 解压暂存目录。
- 后台监控会定期记录根卷可用空间、构建进度和部分临时目录大小。它还会预留一小块应急空间，在可用空间降至危险阈值时释放。
- CI 补丁会确保 Shader 转换中间文件在上游处理不再需要之前不会被提前删除；同时在提取完成后释放原始 NSP/XCI，在支持的 Standard 路径完成上传交接后释放独立 RomFS，并在 Metal 编译后删除已消耗的 Shader 数据。
- 即使构建失败，也会尝试收集最终磁盘报告。

工作流已不再单独执行 Xcode 安装目录/缓存盘点，也不再盲目清理 Xcode 缓存。它不会假定刚启动的 Runner 中存在有价值的项目构建缓存。

## 访问控制与安全

- **仅 Owner 执行构建 Job：** Job 条件会比较触发者与仓库 Owner。非 Owner 触发的运行会被跳过，但这并不会隐藏工作流运行记录本身。
- **公开仓库可见性：** 对于公开仓库，工作流文件、运行元数据和 Actions 日志可能对公众可见。Owner 检查不是日志隐私机制。如果日志不能公开，应使用 Private 仓库，并限制仓库成员访问权限。
- **Secrets：** 不要将下载地址、Cookie、title keys 或其他凭据直接写入 YAML、README、Issue 或提交记录。应使用 Actions Secrets。
- **下载日志：** 下载 Secret URL 时会屏蔽 `gdown` 的标准输出和错误输出，以降低意外泄露地址的风险；但这不能替代适当的仓库和日志访问控制。
- **Artifacts：** 构建日志可能包含文件名、路径、工具输出和诊断信息。分享运行记录前，请检查仓库可见性和 Artifact 访问权限。
- **本地清理：** 工作流结束时会删除临时 Runner 中的游戏文件和 keys，但不会删除原始下载服务或百度网盘中保存的副本。

## 故障排查

| 现象 | 可能原因 / 处理方法 |
| --- | --- |
| 构建 Job 被跳过 | 触发者不是仓库 Owner。请使用 Owner 账户启动工作流。 |
| 百度目标自动回退到 Artifact | `BDUSS` 或 `STOKEN` 缺失。配置两个 Secrets 后重新运行。 |
| 百度预检上传失败 | 检查两个凭据是否有效、网盘账号是否允许上传，以及百度上传 Action 是否能够连接服务。工作流会有意在下载游戏文件前停止。 |
| 必需下载地址为空 | 配置 `Game_URL` 和 `Keys_URL`；只有需要对应更新或 DLC 时才配置可选地址。 |
| 下载重试后仍失败 | 检查 Secret 地址、分享权限、文件是否仍然存在，以及 `gdown` 能否访问该链接。 |
| 游戏包签名校验失败 | 下载内容可能是 HTML 确认页面、不完整文件、不支持的格式，或文件扩展名与实际内容不符。请检查源文件和下载地址。 |
| 无法唯一识别 Title ID | 在 `profile_id` 中填写正确的 16 位十六进制游戏本体 Title ID。 |
| 磁盘空间检查失败或构建空间不足 | 查看可用空间检查步骤和 `NxNative-Build-Logs` Artifact，重点检查 `disk-monitor.log` 与 `build-console.log`。减少不必要的游戏更新/DLC 输入，或使用可用存储空间更大的 Runner。 |
| 上游补丁无法找到预期代码锚点 | 上游源码可能已变化。补丁脚本会主动失败，而不是应用不完整或不确定的修改。检查上游变更后再更新 CI 补丁。 |
| 没有 RomFS Artifact | 当前游戏或构建路径可能不使用独立镜像 RomFS 交接。检查第一轮构建日志；BC fallback 会保留原始内置 RomFS 流程。 |

## 实现说明

- 主工作流：[`.github/workflows/build.yml`](.github/workflows/build.yml)
- CI 辅助脚本：[`.github/scripts/nxnative_ci_guard.py`](.github/scripts/nxnative_ci_guard.py)
- Standard 上游：[ `seedds/nxnative`](https://github.com/seedds/nxnative)
- BC fallback 上游：[ `mianmuhammadse/nxnative`](https://github.com/mianmuhammadse/nxnative)
- 百度上传 Action：[`CHC383/baidu-netdisk-upload-action`](https://github.com/CHC383/baidu-netdisk-upload-action)

CI 辅助脚本在修改上游文件前会验证预期代码锚点。如果上游代码结构发生变化，工作流可能在补丁阶段停止。这是有意设计的保护机制，避免将补丁静默应用到不匹配的源码版本。

