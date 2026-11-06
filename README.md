# NxNative — Build Nintendo Switch Game Ports for iOS

**English** | [简体中文](README.zh-CN.md)

Build an unsigned iOS IPA with [NxNative](https://github.com/seedds/nxnative) through GitHub Actions on a cloud macOS runner. This repository extends the upstream build workflow with package preparation, base-game Title ID detection, disk-space management, a two-pass Standard/NVN RomFS handoff, and optional Baidu Netdisk uploads.

> **Status:** Community-maintained workflow. A successful build does not guarantee that a particular game will boot or run correctly on every iPhone or iOS version. You must provide game files and keys that you are legally entitled to use.

## Overview

The workflow is manually started from the **Actions** tab and offers two build paths:

| Device selection | Build source | Intended path |
| --- | --- | --- |
| iPhone 15 or older (BC fallback) | [mianmuhammadse/nxnative](https://github.com/mianmuhammadse/nxnative) at pinned commit `d158df611bf2f3fa315c4f16585575cdfdb2a1d3` | BC-texture fallback |
| iPhone 15 Pro/Pro Max or newer (standard) | [seedds/nxnative](https://github.com/seedds/nxnative) at `main` | Standard texture path |

These labels select build configurations; they are not compatibility guarantees. The Standard source follows upstream `main`, so upstream changes may affect later builds. The BC fallback source is pinned to a specific commit.

## What this repository adds

- **Major disk-space optimization:** reduce the upstream extraction preflight's extra reserve from 6 GiB to 0.5 GiB while retaining the extracted-size estimate and real free-space check; move rather than copy packages; release original NSP/XCI after extraction; upload and release standalone RomFS before Metal; and clean consumed shader data after Metal.

- **Manual workflow dispatch:** select the device/build path, provide an optional 16-character base-game Title ID override, and choose the output destination.
- **Secret-based downloads:** download the base game package, optional update/DLC packages, and `prod.keys` using URLs stored in GitHub Actions secrets.
- **Package preparation:** accept direct NSP/XCI packages or supported RAR archives containing NSP/XCI/NSZ/XCZ packages; validate package signatures and move files into the build input directory instead of making duplicate copies.
- **Title ID selection:** use the configured override or detect a unique base-game Title ID from package contents and filenames.
- **Disk-conscious CI integration:** apply guarded patches to the checked-out NxNative scripts, monitor available disk space, and release large intermediates when they are no longer needed.
- **Standard/NVN RomFS handoff:** when the Standard build produces a separate `RomFS.img`, pause after shader splitting and before Metal compilation, upload the image, then resume the cached build.
- **Flexible output delivery:** upload the IPA and, when generated, the standalone RomFS image to GitHub Actions Artifacts or Baidu Netdisk.
- **Early Baidu upload validation:** when Baidu is selected, upload a 1 MiB probe using the same Action as the production outputs before downloading large game files.

## Requirements

- A GitHub account with access to this repository. The build job is restricted to the repository owner.
- GitHub Actions enabled for the repository.
- Download links that `gdown` can access without interactive sign-in.
- Your own legally obtained game package(s) and a matching `prod.keys` file.
- For Baidu Netdisk output, valid `BDUSS` and `STOKEN` credentials with upload permission.
- Awareness of GitHub-hosted runner availability, execution limits, and Artifact retention.

**Never commit game dumps, `prod.keys`, private download URLs, cookies, access tokens, or other credentials to this repository.** Use Actions secrets for private values. A public repository's workflow files, run metadata, and logs may be visible to everyone.

The workflow uses the `xcode-27` runner label. It sets up Python 3.13 and .NET 10 and installs Homebrew dependencies including `glslang`, `xcodegen`, `zstd`, `spirv-cross`, and `unar`.

## Setup

### 1. Add repository secrets

Open **Settings → Secrets and variables → Actions → New repository secret** and add the exact names below.

| Secret | Required | Value |
| --- | --- | --- |
| `Game_URL` | Yes | Download URL for the base game package or supported RAR archive |
| `Keys_URL` | Yes | Download URL for `prod.keys` |
| `Update_URL` | No | Download URL for the update package or archive |
| `DLC_URL` | No | Download URL for the first DLC package or archive |
| `DLC2_URL` | No | Download URL for the second DLC package or archive |
| `BDUSS` | Baidu output only | Baidu Netdisk authentication cookie |
| `STOKEN` | Baidu output only | STOKEN paired with the BDUSS value |

Secret names are case-sensitive. The download step uses `gdown`; verify that each URL is accessible to the runner and points to the intended file. Add update/DLC secrets only when you want those packages included.

Supported package extensions are `.nsp`, `.xci`, `.nsz`, and `.xcz`. Direct downloads must be recognizable NSP or XCI containers. RAR archives are extracted before package validation. The workflow rejects invalid signatures, unsupported direct-download content, duplicate package filenames, and an empty prepared-game directory.

### 2. Start a build

1. Open the repository's **Actions** tab.
2. Select **NxNative - Generic IPA Builder**.
3. Click **Run workflow**.
4. Select the device/build path.
5. Keep the default profile ID `0100B8A026F14000`, enter another 16-character hexadecimal base-game Title ID, or clear the field to request automatic detection.
6. Choose `artifact` or `baidu` as the output destination.
7. Start the workflow.

The profile ID is the **base game's Title ID**, not an update or DLC Title ID. If automatic detection finds zero or multiple candidates, the workflow stops and asks for a manual override.

The build job checks `github.actor == github.repository_owner`. A run triggered by another actor will have its build job skipped. This check does not hide the run record or logs in a public repository.

### 3. Retrieve the outputs

When using GitHub Actions Artifacts, open the completed run's **Summary** and download the available artifacts:

- `NxNative-IPA-Standard` or `NxNative-IPA-BC-Fallback` — the unsigned IPA.
- `NxNative-ROMFS` — the separate game-data image, only when the Standard/NVN separate-RomFS handoff is produced.
- `NxNative-Build-Logs` — available build logs, survey output, and disk-monitor logs.

Artifacts are retained for 7 days. GitHub downloads them as ZIP files.

**Important for Standard/NVN separate-RomFS builds:** you need BOTH the IPA and its matching `RomFS.img`. The IPA does not contain the separate game data and is not sufficient on its own.

After installing the IPA, place the image in the installed app's container at:

`<App Container>/Documents/romfs.img`

Use the exact lowercase filename `romfs.img`. Do not put it inside `DmIOS.app`, `Payload`, or the app's `romfs` resource folder. The upstream project provides [`scripts/push_romfs.sh`](https://github.com/seedds/nxnative/blob/main/scripts/push_romfs.sh) to copy the image into the app's Documents directory. See the upstream [packing/deployment documentation](https://github.com/seedds/nxnative/blob/main/docs/development.md) for details. The image must match the game/version used to build the IPA; transfer the matching image again whenever the game version or extracted content changes.

The `NxNative-ROMFS` artifact is a game-data image, not an installable app.

When Baidu Netdisk is selected, the IPA and separate RomFS image (if produced) are uploaded to a unique run folder in the Netdisk root. The build logs are still uploaded as a GitHub Actions Artifact.

### Baidu upload preflight and fallback

When `upload_target=baidu`:

1. The workflow checks that both `BDUSS` and `STOKEN` are configured.
2. If either secret is missing, the effective destination automatically falls back to GitHub Actions Artifacts.
3. If both are present, the workflow logs in with BaiduPCS-Go and creates a unique remote directory named like `/NxNative-Build-<run-id>-<attempt>`.
4. It generates a 1 MiB random probe file and uploads it with the same Baidu upload Action used for the actual outputs.
5. Large game-file downloads begin only after the preflight upload succeeds.

This preflight is intentional: it checks the credentials and upload route before the time-consuming download and build stages. Do not remove it simply to shorten the workflow.

## Disk-space optimizations

Disk-space reduction is a core feature of this repository, not just diagnostic logging. The workflow changes both the upstream extraction preflight threshold and the lifetime of large build inputs/intermediates so the runner does not need to hold every large file at the same time.

### 1. Reduce the extraction preflight reserve: 6 GiB → 0.5 GiB

The upstream `build_ipa_from_nsp.py` estimates the space required for extraction from the source data/tree size, then adds a fixed **6 GiB safety reserve**. The guard patch changes only that extra reserve to **0.5 GiB**.

- The extracted-size estimate is still calculated.
- The real available-space comparison (`free_gb(work) < gb`) is still performed.
- The separate check for insufficient IPA output space (the upstream **5 GB** check) is not removed.
- This is a reduction of the conservative reserve, **not removal or bypass of the extraction-space preflight**.

Why this is reasonable for this workflow: the later build no longer needs to keep the original NSP/XCI packages, standalone RomFS image, and consumed shader intermediates occupying disk through the Metal stage. Those files are released at defined safe points below. Reserving the later peak in full during the initial extraction check would therefore be unnecessarily conservative. The trade-off is that a runner with genuinely insufficient space can still run out of disk later; the live monitor and cleanup steps do not guarantee capacity.

### 2. Move packages instead of duplicating them

- Packages extracted from RAR archives are moved into `$RUNNER_TEMP/GameFiles`.
- Directly downloaded NSP/XCI packages are also moved from the download staging directory into `GameFiles`.
- The workflow removes leftover `.download` files and temporary extracted-RAR directories after package preparation.

This avoids keeping a second full-size copy of each game package. The validated package files remain available to NxNative until extraction has consumed them.

### 3. Release original NSP/XCI after game and DLC extraction

On the second build pass, the CI patch removes the original `.nsp`, `.xci`, `.nsz`, and `.xcz` inputs after `extract_aoc()` has completed. It reports the number and total size of removed packages and the resulting free disk space.

The deletion is deliberately delayed until extraction has finished; the source packages are not deleted before NxNative has consumed them.

### 4. Split the Standard/NVN build around the RomFS upload

For the Standard path that supports image-backed `--romfs separate`, the workflow uses two passes:

1. The first pass extracts game data, rewrites and splits shaders, then stops before Metal compilation.
2. The workflow uploads the standalone `RomFS.img` before continuing.
3. The temporary upload staging hard link is removed.
4. The second pass re-enters the builder and reuses the existing extraction/rewrite/shader-split work.
5. During this second pass, after NxNative has completed game and DLC extraction (`extract_aoc()`), the CI patch deletes the original `.nsp`, `.xci`, `.nsz`, and `.xcz` package files. It reports the number and total size removed, plus the resulting free disk space. This happens before the later Metal stage; the packages are retained until NxNative has finished consuming them.
6. At the post-split handoff point, the original local RomFS image is deleted after the upload has succeeded and before Metal compilation.

The handoff uses a hard link for the staging file, rather than creating another full copy of the large image. The separate image remains available as the uploaded artifact/Netdisk output; the runner does not need to retain its local copy during the later Metal build. Thus, the second pass frees two different classes of large input: the original game packages after extraction, and the local standalone RomFS image after upload.

The BC fallback path does not support this separate-image handoff and keeps its upstream bundled-RomFS behavior.

### 5. Release consumed shader data after Metal

After the iOS Metal shader build succeeds, the workflow removes the consumed `shader/pkg` and `shader/cache` directories while retaining `shader/ios` for IPA packaging.

The CI patch also disables shader cache publication for these ephemeral CI builds. It intentionally does **not** delete translator `.bin`, `.spv`, reflection, or job files early: upstream `fin()` tasks may still read them. The upstream translator temporary-directory cleanup remains responsible for deleting those files after all finishing tasks complete. This avoids a race that could break shader output.

### 6. Live disk monitoring and emergency reserve

- The workflow reports actual free space with `df` after game-package preparation and at key build stages.
- The progress display adds current root-volume free space to the iOS shader progress line.
- A background monitor records free space periodically and takes deeper snapshots of selected build directories.
- The monitor allocates a real **256 MiB emergency reserve**. If free space falls to **8 GiB or less**, it removes that reserve file to leave some room for the runner and log-writing operations.
- The final monitor report is collected when the build stops.

These measures improve visibility and reclaim space at known safe points; they do not create extra runner storage or guarantee that every game fits.

## CI helper: `.github/scripts/nxnative_ci_guard.py`

This Python script is not a game patch and does not modify game content. It coordinates repository-specific CI safeguards:

- **Pre-clean:** removes stale workflow-owned `GameFiles` and `nxnative` temporary directories without deleting Xcode, Homebrew, or runner-wide caches.
- **Patch upstream build scripts:** validates expected source anchors before applying disk-safe shader and RomFS workflow changes. If upstream changes unexpectedly, the helper fails rather than applying an ambiguous patch.
- **Coordinate the two-pass RomFS build:** supports the Standard path's stop-after-split handoff and releases the local RomFS image before the second-pass Metal build.
- **Protect intermediate-file lifetimes:** delays deletion of shader data until upstream processing no longer needs it, then releases large source data at safe points.
- **Monitor and report disk use:** records free space, build progress, and selected temporary-directory sizes; starts and stops the monitor and prints a final report.

The workflow invokes this helper for pre-cleaning, patching, disk monitoring, and reporting. It does not replace NxNative's package extraction or Metal compilation.

## Build flow

```text
Select Standard or BC fallback source
                  |
Checkout NxNative and CI helper
                  |
Resolve output destination
                  |
Baidu selected? ---- yes ---> Login, create remote folder,
      |                       upload 1 MiB preflight probe
      no                              |
      |                               |
      +-------------------------------+
                  |
Download game package(s) and prod.keys
                  |
Prepare packages, validate signatures, move into GameFiles
                  |
Check free space and remove download/extraction staging
                  |
Detect or apply base-game Title ID
                  |
Apply CI guard patches and prepare shader toolchain
                  |
First NxNative build pass
       |
       +-- BC fallback: original bundled-RomFS build path
       |
       +-- Standard/NVN separate-RomFS:
              split shaders and pause before Metal
              upload RomFS.img
              rerun builder and reuse cached work
              delete original NSP/XCI packages after extraction
              release local RomFS after upload
              compile Metal
                  |
Create unsigned IPA
                  |
Upload IPA, available RomFS, and build logs
                  |
Stop monitor and clean temporary files/keys
```

The RomFS handoff is conditional. It occurs only when the Standard path reaches the supported NVN + separate-RomFS flow and produces the handoff marker and image. Other paths may finish the IPA in the first pass and do not produce a separate RomFS artifact. The BC fallback path retains its bundled-RomFS behavior.

## Repository layout

- `.github/workflows/build.yml` — main GitHub Actions build workflow.
- `.github/scripts/nxnative_ci_guard.py` — CI helper for guarded upstream patches and disk monitoring.
- `README.md` — English documentation (default).
- `README.zh-CN.md` — Simplified Chinese documentation.

NxNative source is checked out at workflow runtime. This repository is not a fork or mirror of either upstream source repository.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Build job is skipped | Only the repository owner can execute the build job. Start the workflow with the owner account. |
| Baidu output falls back to Artifact | One or both of `BDUSS` and `STOKEN` are missing. Configure both secrets. |
| Baidu preflight upload fails | Check credential validity, account upload permission, and Action connectivity. The workflow intentionally stops before downloading large game files. |
| Required download fails | Verify `Game_URL` and `Keys_URL`, sharing permissions, and that `gdown` can access the links. |
| Package signature validation fails | The download may be an HTML page, incomplete file, unsupported content, or mislabeled package. Verify the source file and URL. |
| Title ID cannot be uniquely detected | Enter the correct 16-character hexadecimal base-game Title ID in `profile_id`. |
| Disk space runs out | Inspect the available-space check and `NxNative-Build-Logs`, especially `disk-monitor.log` and `build-console.log`. Reduce unnecessary update/DLC inputs or use a runner with more storage. |
| CI patch cannot find an expected source anchor | Upstream NxNative may have changed. Review the upstream change and update the CI helper; it intentionally fails closed. |
| RomFS artifact is absent | The selected build may not use the Standard/NVN separate-RomFS handoff. Check the first-pass log and whether the handoff marker was created. |
| IPA installs but the game does not run | Build success is not a compatibility guarantee. Check the game version, update/DLC, keys, selected build path, device, and upstream compatibility notes. |

When sharing logs for help, remove private URLs, tokens, and other credentials. Never share your keys file or game dump.

## Upstream projects and actions

- [seedds/nxnative](https://github.com/seedds/nxnative) — Standard build source.
- [mianmuhammadse/nxnative](https://github.com/mianmuhammadse/nxnative) — pinned BC fallback source.
- [CHC383/baidu-netdisk-upload-action](https://github.com/CHC383/baidu-netdisk-upload-action) — Baidu Netdisk upload Action.
- [BaiduPCS-Go](https://github.com/qjfoidnh/BaiduPCS-Go) — used to authenticate and create the per-run remote folder.
