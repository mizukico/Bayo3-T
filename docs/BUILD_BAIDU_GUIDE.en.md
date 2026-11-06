# NxNative Build Guide (Baidu Netdisk)

[简体中文](BUILD_BAIDU_GUIDE.md) | **English**

This guide covers [`.github/workflows/build-baidu.yml`](../.github/workflows/build-baidu.yml). The workflow downloads the game directory, `prod.keys`, and optional update/DLC files directly from Baidu Netdisk, then builds NxNative in the macOS environment provided by GitHub Actions.

Unlike the Google Drive workflow, this workflow **requires Baidu Netdisk as its input source**. You must configure Baidu credentials even if you choose GitHub Actions Artifacts as the final output destination.

> Use only game backups and keys that you are legally entitled to use. Do not commit game files, `prod.keys`, or Baidu Netdisk credentials to the repository.

## 1. Workflow overview

- **Input source:** Baidu Netdisk paths supplied when starting the workflow.
- **Game input:** a Baidu Netdisk directory. The workflow downloads it recursively and selects all `.nsp` and `.xci` files found inside.
- **Keys input:** the path to one `prod.keys` file.
- **Optional inputs:** one update package, one DLC package, and a second DLC package.
- **Output:** GitHub Actions Artifacts or Baidu Netdisk.
- **Build paths:** BC fallback and Standard.
- **Standard path:** performs Shader Split and delivers RomFS separately before freeing disk space and continuing Metal compilation. BC fallback uses its bundled-RomFS build path.

## 2. Prepare your Baidu Netdisk folders

Organize your files in advance and use clear paths. Avoid duplicate package filenames.

Example layout:

```text
/GameBackups/TargetGame/
├── BaseGame.nsp
├── AdditionalContent.xci
/GameBackups/Keys/prod.keys
/GameBackups/Updates/Update.nsp
/GameBackups/DLC/DLC.nsp
```

This is only an example. Use the actual paths in your Baidu Netdisk account.

### Game directory requirements

`game_path` must be a **directory containing game files**, not the path to an individual NSP/XCI file. The workflow downloads the directory recursively and selects all `.nsp` and `.xci` files found in it.

- The base game and other NSP/XCI packages may be in the directory or its subdirectories.
- Every discovered NSP/XCI file is passed into the subsequent package preparation process.
- If no NSP/XCI files are found, the workflow fails during download/filtering.
- If different subdirectories contain packages with the same filename, the workflow stops because of the duplicate filename.
- This directory scan selects only `.nsp` and `.xci`. Do not use NSZ/XCZ files or RAR archives as direct game-directory inputs.

### prod.keys and optional files

- `keys_path`: required; must point to one specific `prod.keys` file, not a folder.
- `update_path`: optional; path to one update file.
- `dlc_path`: optional; path to one DLC file.
- `dlc2_path`: optional; path to a second DLC file.

Each single-file path must point to exactly one file, not a directory or a path containing multiple files. If an optional file is not needed, leave its input empty.

The subsequent preparation step supports direct NSP/XCI/NSZ/XCZ packages or RAR archives for these single-file update/DLC inputs. However, the base game directory scan itself selects only NSP/XCI files.

## 3. Configure Baidu Netdisk credentials

In the repository, open:

**Settings → Secrets and variables → Actions → New repository secret**

Create both repository secrets:

| Secret | Value | Required |
|---|---|---|
| `BDUSS` | The BDUSS value from your Baidu Netdisk login credentials | Yes |
| `STOKEN` | The STOKEN value from your Baidu Netdisk login credentials | Yes |

The names are case-sensitive and must match exactly.

**Important:**
- You do not need to upload game files or `prod.keys` to the GitHub repository.
- Never put BDUSS or STOKEN in YAML, README files, Issues, or public logs.
- The workflow checks both secrets before downloading input files. If either is missing, the run stops.
- Both credentials are required even when `upload_target` is set to `artifact`.

## 4. Start a build

1. Open the repository's **Actions** tab.
2. Select the workflow associated with `.github/workflows/build-baidu.yml` (displayed as **NxNative - Generic IPA Builder**).
3. Click **Run workflow**.
4. Select the branch (normally `main`).
5. Fill in the inputs:

| Input | Required | Value |
|---|---|---|
| `device` | Yes | Select BC fallback or Standard |
| `profile_id` | No | Usually leave empty for automatic Title ID detection |
| `game_path` | Yes | Baidu Netdisk directory containing the game packages |
| `keys_path` | Yes | Full path to the `prod.keys` file |
| `update_path` | No | Full path to the update package, or leave empty |
| `dlc_path` | No | Full path to the DLC package, or leave empty |
| `dlc2_path` | No | Full path to the second DLC package, or leave empty |
| `upload_target` | Yes | `artifact` or `baidu` |

Example values:

```text
game_path: /GameBackups/TargetGame
keys_path: /GameBackups/Keys/prod.keys
update_path: /GameBackups/Updates/Update.nsp
dlc_path: /GameBackups/DLC/DLC.nsp
dlc2_path:
```

Replace these example paths with the actual paths in your account.

### Device options

- **iPhone 15 or older (BC fallback):** selects the pinned BC fallback build path.
- **iPhone 15 Pro/Pro Max or newer (standard):** selects the Standard upstream build path.

These are different build paths, not a compatibility guarantee for every game or device.

### Profile ID

Normally leave this field empty so the workflow can detect the base game's Title ID. If automatic detection fails or you need to specify it manually, enter the base game's **16-character hexadecimal Title ID**.

### Output destination

- `artifact`: upload the IPA as a GitHub Actions Artifact.
- `baidu`: upload RomFS (when required by the Standard path) and the IPA to Baidu Netdisk.

## 5. What the workflow does

The workflow generally performs these steps:

1. Checks `BDUSS` and `STOKEN`, then logs in to Baidu Netdisk.
2. If Baidu output is selected, creates a unique output folder for this run.
3. If Baidu output is selected, uploads a 1 MiB preflight file to verify the upload path.
4. Recursively downloads the `game_path` directory and selects all NSP/XCI files.
5. Downloads the specified keys file and any update/DLC files.
6. Validates package signatures and prepares the game packages. RAR extraction is available for supported single-file update/DLC inputs.
7. Detects the base game's Title ID and prepares the shader build configuration.
8. Runs Shader Split; the Standard path delivers standalone RomFS before Metal compilation.
9. Releases unneeded intermediate files and disk space, then continues Metal compilation and generates the IPA.
10. Uploads the IPA and build logs, then cleans downloaded files and keys from the runner.

### Disk-space optimization

The workflow does not keep every downloaded and extracted intermediate file until the end. After preparing the game packages, it removes original download and RAR extraction intermediates. The repository's CI guard also performs temporary-file pre-cleaning, Shader/RomFS space management, disk monitoring, and a post-build audit.

For the Standard path, the workflow generates and delivers `RomFS.img` first. It then resumes the cached build flow and frees space used by Shader, RomFS, and NSP data before continuing Metal compilation. This is designed to reduce peak disk usage when building large games on the runner.

BC fallback does not use the separate RomFS delivery step; it follows its bundled-RomFS build path.

## 6. Retrieve the build outputs

### GitHub Actions Artifacts

If `upload_target=artifact`:

1. Open the workflow run details.
2. Find **Artifacts** on the Summary page.
3. Download `NxNative-IPA-Standard` or `NxNative-IPA-BC-Fallback`.
4. Extract the ZIP to obtain the `.ipa` file.

If the Standard build produces a separate RomFS output, an `NxNative-ROMFS` Artifact is also provided. Build logs are uploaded as `NxNative-Build-Logs`. The configured Artifact retention period is 7 days.

### Baidu Netdisk

If `upload_target=baidu`:

- The workflow creates a unique folder in the Baidu Netdisk root directory.
- The folder name resembles `/NxNative-Build-RUN_ID-ATTEMPT`.
- The IPA is uploaded to this folder. If the Standard path requires separate RomFS delivery, `RomFS.img` is uploaded to the same folder.
- A 1 MiB upload preflight runs before the main build, so upload problems are detected early.

## 7. Troubleshooting

### BDUSS or STOKEN is missing

Open **Settings → Secrets and variables → Actions** and verify that both `BDUSS` and `STOKEN` exist with the exact spelling and capitalization. The Baidu workflow requires both regardless of the output destination.

### No NSP/XCI files found in the game directory

Make sure `game_path` points to a directory and that it or its subdirectories contain files with the `.nsp` or `.xci` extension. The directory scan does not select NSZ/XCZ or RAR files as game packages.

### The workflow says a path must point to one file

`keys_path`, `update_path`, `dlc_path`, and `dlc2_path` must point to individual files. Do not enter a folder path. Leave optional inputs empty when the corresponding file is not needed.

### Download fails

Check that the Baidu Netdisk path exists and that the account has permission to access it. Also verify that directory and file paths have not been swapped. The single-file downloader makes up to three attempts; for directory download failures, check the directory path and access permissions.

### Title ID detection fails

Check whether the game directory contains multiple different games or whether the base game package lacks recognizable Title ID information. If necessary, enter the base game's 16-character hexadecimal Title ID in `profile_id`.

### Baidu upload preflight fails

Check that `BDUSS` and `STOKEN` are valid and that the Baidu Netdisk account can upload files. The preflight runs before the main download/build process to avoid discovering an upload problem only after a long build.

### Build fails

Open the Actions run and locate the first step containing an actual error. Later failures may be consequences of the earlier one. Remove credentials, tokens, and private links before sharing logs.

## 8. Pre-build checklist

- [ ] The Baidu Netdisk game directory is prepared.
- [ ] The game directory contains the required NSP/XCI files.
- [ ] `prod.keys` is uploaded and `keys_path` points to that file.
- [ ] Required update/DLC files are uploaded and their paths point to individual files.
- [ ] The repository has a `BDUSS` secret.
- [ ] The repository has an `STOKEN` secret.
- [ ] `game_path` is a directory, not an individual NSP/XCI file.
- [ ] `keys_path` points to the `prod.keys` file.
- [ ] The device build path and output destination are selected.
- [ ] After completion, the IPA is retrieved from Artifacts or the Baidu output folder.

---

**Compatibility note:** A successful build means that an IPA was generated; it does not guarantee that the game will run correctly on the target device. Results depend on the game version, target device, build path, and the game's own compatibility.
