# NxNative — 使用 GitHub Actions 构建 iOS IPA

[English](README.md) | **简体中文**

本项目通过 GitHub Actions 云端 macOS Runner 调用 [NxNative](https://github.com/seedds/nxnative)，将游戏文件构建为未签名 iOS IPA。在上游构建流程基础上，本仓库增加了游戏包预处理、基础游戏 Title ID 识别、磁盘空间管理、Standard/NVN 两阶段 RomFS 中转，以及可选的百度网盘上传功能。

> **状态说明：** 本项目是社区维护的构建工作流。构建成功不代表特定游戏一定能在所有 iPhone 型号或 iOS 版本上正常启动和运行。请自行提供有权使用的游戏文件和密钥。

## 功能概览

工作流可在 GitHub 的 **Actions** 页面手动启动，并提供两种构建路径：

| 设备选项 | 上游源码 | 构建路径 |
| --- | --- | --- |
| iPhone 15 or older (BC fallback) | [mianmuhammadse/nxnative](https://github.com/mianmuhammadse/nxnative)，固定提交 `d158df611bf2f3fa315c4f16585575cdfdb2a1d3` | BC 纹理兼容路径 |
| iPhone 15 Pro/Pro Max or newer (standard) | [seedds/nxnative](https://github.com/seedds/nxnative)，`main` 分支 | 标准纹理路径 |

以上选项只代表构建配置，不是设备或游戏兼容性保证。Standard 路径跟随上游 `main`，上游更新可能影响后续构建；BC fallback 固定在指定 commit。

## 本仓库新增的功能

- **手动启动工作流：** 选择设备/构建路径，填写可选的 16 位游戏本体 Title ID，并选择产物上传位置。
- **通过 Secrets 下载文件：** 使用 GitHub Actions Secrets 中的下载地址获取游戏本体、可选更新/DLC 和 `prod.keys`。
- **游戏包预处理：** 支持直接使用 NSP/XCI，或解压包含 NSP/XCI/NSZ/XCZ 的受支持 RAR 压缩包；校验包签名，并将文件移动到构建输入目录，避免重复复制大文件。
- **Title ID 识别：** 优先使用手动指定值；否则从游戏包内容和文件名中识别唯一的游戏本体 Title ID。
- **磁盘优化 CI 集成：** 对运行时检出的 NxNative 脚本应用经过锚点校验的补丁，监控可用磁盘空间，并在不再需要时释放大型中间文件。
- **Standard/NVN RomFS 中转：** Standard 构建生成独立 `RomFS.img` 时，会在 Shader Split 后、Metal 编译前暂停并上传镜像，然后恢复缓存构建。
- **灵活的产物保存位置：** 将 IPA 和（如果生成）独立 RomFS 镜像上传到 GitHub Actions Artifacts 或百度网盘。
- **百度上传预检：** 选择百度网盘时，在下载大型游戏文件前，使用正式上传相同的 Action 上传一个 1 MiB 测试文件。

## 使用要求

- 拥有可访问本仓库的 GitHub 账户。构建 Job 限制为仅仓库 Owner 执行。
- 仓库已启用 GitHub Actions。
- 提供 `gdown` 可访问且无需交互登录的下载链接。
- 自行合法取得的游戏文件，以及与游戏匹配的 `prod.keys`。
- 如需上传百度网盘，需提供有效的 `BDUSS` 和 `STOKEN`，且账号具备上传权限。
- 了解 GitHub 云端 Runner 的可用性、运行时长限制和 Artifact 保留期限。

**不要将游戏转储文件、`prod.keys`、私有下载地址、Cookie、访问令牌或其他凭据提交到仓库。** 私密信息应放在 Actions Secrets 中。公开仓库的工作流文件、运行记录和日志可能对所有人可见。

工作流使用 `xcode-27` Runner 标签，配置 Python 3.13 和 .NET 10，并安装 `glslang`、`xcodegen`、`zstd`、`spirv-cross`、`unar` 等 Homebrew 依赖。

## 配置与使用

### 1. 添加 Repository Secrets

进入 **Settings → Secrets and variables → Actions → New repository secret**，按下表添加完全一致的名称。

| Secret | 是否必需 | 内容 |
| --- | --- | --- |
| `Game_URL` | 必需 | 游戏本体文件或受支持 RAR 压缩包的下载地址 |
| `Keys_URL` | 必需 | `prod.keys` 的下载地址 |
| `Update_URL` | 可选 | 游戏更新文件或压缩包下载地址 |
| `DLC_URL` | 可选 | 第一个 DLC 文件或压缩包下载地址 |
| `DLC2_URL` | 可选 | 第二个 DLC 文件或压缩包下载地址 |
| `BDUSS` | 仅百度上传时需要 | 百度网盘认证 Cookie |
| `STOKEN` | 仅百度上传时需要 | 与 BDUSS 配套的 STOKEN |

Secret 名称区分大小写。下载步骤使用 `gdown`，请确认 Runner 无需交互登录即可访问这些地址。没有更新或 DLC 时，无需添加对应 Secret。

支持的游戏包扩展名为 `.nsp`、`.xci`、`.nsz` 和 `.xcz`。直接下载的文件必须能识别为 NSP 或 XCI 容器；RAR 压缩包会先解压再校验。工作流会拒绝签名错误的文件、不支持的直接下载内容、重复文件名以及没有任何游戏包的目录。

### 2. 启动构建

1. 打开仓库的 **Actions** 页面。
2. 选择 **NxNative - Generic IPA Builder**。
3. 点击 **Run workflow**。
4. 选择设备/构建路径。
5. Profile ID 可保留默认值 `0100B8A026F14000`，也可以填写其他 16 位十六进制游戏本体 Title ID；清空该字段则启用自动识别。
6. 选择 `artifact` 或 `baidu` 作为产物保存位置。
7. 启动工作流。

Profile ID 指**游戏本体 Title ID**，不是更新或 DLC 的 Title ID。自动识别结果为零个或多个候选值时，工作流会停止并要求手动填写。

构建 Job 会检查 `github.actor == github.repository_owner`。由非仓库 Owner 触发的运行，其构建 Job 会被跳过。该限制不会隐藏公开仓库中的运行记录或日志。

### 3. 获取构建产物

使用 GitHub Actions Artifacts 时，打开已完成运行的 **Summary** 页面，下载可用产物：

- `NxNative-IPA-Standard` 或 `NxNative-IPA-BC-Fallback`：未签名 IPA。
- `NxNative-ROMFS`：独立游戏数据镜像，仅在 Standard/NVN 独立 RomFS 中转流程实际生成时存在。
- `NxNative-Build-Logs`：可用的构建日志、调查输出和磁盘监控日志。

Artifact 保留 7 天。GitHub 下载的 Artifact 通常为 ZIP 压缩包。

**Standard/NVN separate-RomFS 构建特别注意：** 必须同时取得 IPA 和与之匹配的 `RomFS.img`。IPA 不包含单独交付的游戏数据，不能只安装 IPA 就开始游玩。

安装 IPA 后，将镜像放入已安装应用的容器目录：

`<App Container>/Documents/romfs.img`

文件名必须为小写的 `romfs.img`。不要放进 `DmIOS.app`、`Payload` 或 App 内部的 `romfs` 资源目录。上游提供了 [`scripts/push_romfs.sh`](https://github.com/seedds/nxnative/blob/main/scripts/push_romfs.sh)，可将镜像复制到应用的 Documents 目录。具体部署方式参考上游的[打包与部署文档](https://github.com/seedds/nxnative/blob/main/docs/development.md)。镜像必须与构建 IPA 时使用的游戏及版本匹配；游戏版本或提取内容变化后，需要重新传输对应镜像。

`NxNative-ROMFS` 是游戏数据镜像，不是可安装应用。

选择百度网盘时，IPA 和独立 RomFS 镜像（如果生成）会上传到网盘根目录下本次运行专属的目录。构建日志仍会作为 GitHub Actions Artifact 上传。

### 百度网盘上传预检与回退机制

当 `upload_target=baidu` 时：

1. 工作流检查是否同时配置了 `BDUSS` 和 `STOKEN`。
2. 任意一个缺失时，实际上传目标会自动回退到 GitHub Actions Artifacts。
3. 两个值都存在时，工作流通过 BaiduPCS-Go 登录，并创建类似 `/NxNative-Build-<run-id>-<attempt>` 的独立远程目录。
4. 生成一个 1 MiB 随机测试文件，使用正式产物上传所用的同一个百度上传 Action 进行测试。
5. 只有预检上传成功后，才开始下载大型游戏文件。

保留预检是有意设计的：它能在耗时较长的下载和构建开始前验证凭据与上传链路。不要仅为了缩短工作流而删除此步骤。

## 磁盘空间优化

本仓库的主要工程目标是降低 GitHub 云端 macOS Runner 的峰值磁盘占用，尤其是 Metal Shader 编译阶段的空间压力。

1. **移动游戏包，不再复制。** 从 RAR 解压或直接下载得到的游戏包会移动到 `$RUNNER_TEMP/GameFiles`，避免同一大文件同时保留两份完整副本。
2. **删除下载暂存文件。** 游戏包准备完成后，删除残留的 `.download` 文件和 RAR 临时解压目录；NxNative 后续需要的已校验游戏包会保留。
3. **测量真实可用空间。** 游戏包准备完成后使用 `df` 输出根卷可用空间，并在构建过程中持续记录剩余空间。
4. **Metal 编译前上传独立 RomFS。** 支持的 Standard/NVN 路径会在第一轮 Shader Split 完成后暂停，并准备 `RomFS.img` 上传。
5. **Metal 编译前释放本地 RomFS。** 上传完成后，第二轮构建复用已有的解包、重写和 Shader 数据，并在 Metal 编译前释放本地 RomFS 镜像。
6. **在安全时机释放已消耗的数据。** CI 补丁协调 Shader 清理，在上游不再需要原始 NSP/XCI 和 Shader 数据时释放空间。
7. **监控与报告。** 后台监控记录可用空间和指定构建目录大小；即使构建失败，也会尝试收集最终磁盘报告。

工作流不会盲目清理 Xcode 缓存，也不再单独扫描 Xcode 安装目录。不会假设刚启动的 Runner 中存在有价值的项目构建缓存。

## CI 辅助脚本：`.github/scripts/nxnative_ci_guard.py`

该 Python 脚本不是游戏补丁，不会修改游戏内容。它负责协调本仓库的 CI 保护措施：

- **构建前清理：** 只清理本工作流管理的旧 `GameFiles` 和 `nxnative` 临时目录，不删除 Xcode、Homebrew 或 Runner 全局缓存。
- **修改上游构建脚本：** 应用补丁前先检查预期源码锚点。若上游源码结构发生意外变化，脚本会报错停止，而不是应用不确定的补丁。
- **协调 RomFS 两阶段构建：** 支持 Standard 路径在 Shader Split 后暂停并交接 RomFS，在第二轮 Metal 构建前释放本地镜像。
- **保护中间文件生命周期：** 确保上游处理仍需要的 Shader 数据不会被提前删除，并在安全时机释放大型源文件。
- **磁盘监控和报告：** 记录剩余空间、构建进度和指定临时目录大小，负责启动/停止监控并输出最终报告。

工作流会调用该脚本执行构建前清理、上游补丁、磁盘监控和报告。它不代替 NxNative 解包游戏，也不负责 Metal 编译。

## 构建流程

```text
选择 Standard 或 BC fallback 源码
                  |
检出 NxNative 和 CI 辅助脚本
                  |
确定产物上传位置
                  |
选择百度网盘？ ---- 是 ---> 登录、创建远程目录、
      |                     上传 1 MiB 预检文件
      否                            |
      |                             |
      +-----------------------------+
                  |
下载游戏包和 prod.keys
                  |
预处理游戏包、校验签名并移动到 GameFiles
                  |
检查可用空间，清理下载/解压暂存文件
                  |
识别或应用游戏本体 Title ID
                  |
应用 CI Guard 补丁并准备 Shader 工具链
                  |
第一轮 NxNative 构建
       |
       +-- BC fallback：原有内置 RomFS 构建路径
       |
       +-- Standard/NVN separate-RomFS：
              拆分 Shader，在 Metal 前暂停
              上传 RomFS.img
              再次运行构建器并复用缓存
              释放本地 RomFS，编译 Metal
                  |
生成未签名 IPA
                  |
上传 IPA、可用的 RomFS 和构建日志
                  |
停止监控并清理临时文件/密钥
```

RomFS 中转是有条件触发的：只有 Standard 路径实际进入受支持的 NVN + separate-RomFS 流程，并成功生成 handoff 标记和镜像时才会执行。其他路径可能在第一轮就完成 IPA，不会生成独立 RomFS Artifact。BC fallback 保留原有内置 RomFS 流程。

## 仓库结构

- `.github/workflows/build.yml`：主 GitHub Actions 构建工作流。
- `.github/scripts/nxnative_ci_guard.py`：负责上游补丁和磁盘监控的 CI 辅助脚本。
- `README.md`：英文说明（默认显示）。
- `README.zh-CN.md`：简体中文说明。

工作流在运行时动态检出 NxNative 上游源码。本仓库不是上游项目的 Fork，也不是源码镜像。

## 常见问题

| 现象 | 排查方向 |
| --- | --- |
| 构建 Job 被跳过 | 只有仓库 Owner 可以执行构建 Job。请使用 Owner 账户启动。 |
| 百度上传回退到 Artifact | `BDUSS` 或 `STOKEN` 缺失。请同时配置两个 Secrets。 |
| 百度预检上传失败 | 检查凭据有效性、网盘账号上传权限和 Action 网络连接。工作流会有意在下载大型游戏文件前停止。 |
| 必需文件下载失败 | 检查 `Game_URL`、`Keys_URL`、分享权限，以及 `gdown` 是否能够访问链接。 |
| 游戏包签名校验失败 | 下载内容可能是 HTML 页面、不完整文件、不支持的内容，或扩展名与实际文件不符。请检查源文件和下载地址。 |
| 无法唯一识别 Title ID | 在 `profile_id` 中填写正确的 16 位十六进制游戏本体 Title ID。 |
| 构建过程中磁盘空间不足 | 检查可用空间步骤和 `NxNative-Build-Logs`，重点查看 `disk-monitor.log`、`build-console.log`。减少不必要的更新/DLC 输入，或使用存储空间更大的 Runner。 |
| CI 补丁找不到预期源码锚点 | 上游 NxNative 可能已经变化。检查上游修改并更新 CI 辅助脚本；脚本会主动停止，避免错误打补丁。 |
| 没有 RomFS Artifact | 当前构建可能没有使用 Standard/NVN 独立 RomFS 中转。检查第一轮日志和 handoff 标记是否生成。 |
| IPA 已安装但游戏无法运行 | 构建成功不代表兼容。检查游戏版本、更新/DLC、密钥、构建路径、设备和上游兼容性说明。 |

分享日志寻求帮助前，请删除私有下载地址、令牌和其他凭据。不要分享密钥文件或游戏转储文件。

## 上游项目与 Actions

- [seedds/nxnative](https://github.com/seedds/nxnative)：Standard 构建源码。
- [mianmuhammadse/nxnative](https://github.com/mianmuhammadse/nxnative)：固定版本的 BC fallback 源码。
- [CHC383/baidu-netdisk-upload-action](https://github.com/CHC383/baidu-netdisk-upload-action)：百度网盘上传 Action。
- [BaiduPCS-Go](https://github.com/qjfoidnh/BaiduPCS-Go)：用于登录百度网盘并创建每次运行的远程目录。
