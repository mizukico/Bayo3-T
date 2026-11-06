# NxNative Build Guide (Google Drive)

[简体中文](BUILD_GUIDE.md) | **English**

This guide covers [`.github/workflows/build.yml`](../.github/workflows/build.yml). The workflow downloads game files and `prod.keys` from Google Drive, then builds NxNative in the macOS environment provided by GitHub Actions. You do not need to install macOS, Xcode, or the NxNative build toolchain locally.

> Use only game backups and keys that you are legally entitled to use. Do not commit game files, `prod.keys`, Baidu Netdisk credentials, or publicly accessible download links to the repository.

## 1. Workflow overview

- **Input source:** Google Drive share links stored in GitHub Secrets.
- **Build paths:** BC fallback and Standard.
- **Supported game inputs:** NSP/XCI/NSZ/XCZ packages, or RAR archives containing supported packages.
- **Optional inputs:** game update, DLC, and a second DLC package.
- **Output:** GitHub Actions Artifacts or Baidu Netdisk.
- **Standard build:** performs Shader Split and delivers `RomFS.img` separately before continuing with Metal compilation and IPA packaging. BC fallback uses its bundled-RomFS build path.
- The workflow removes download/extraction intermediates and runs disk monitoring and a post-build disk audit.

## 2. Prepare your files

| File | Required | Notes |
|---|---|---|
| Base game | Yes | NSP, XCI, NSZ, XCZ, or a RAR archive containing supported packages |
| `prod.keys` | Yes | Must match the game files |
| Game update | No | Provide if needed |
| DLC | No | Provide if needed |
| Second DLC | No | Provide if needed |

The workflow attempts to detect the base game's Title ID automatically. Make sure the supplied game packages contain enough information to identify the base game. If automatic detection fails, you can enter a Profile ID when starting the workflow.

## 3. Upload files to Google Drive

1. Sign in to [Google Drive](https://drive.google.com/).
2. Upload the base game (or its RAR archive), `prod.keys`, and any update/DLC files.
3. For each file the workflow needs to download, open **Share**:
   - Under General access, select **Anyone with the link**.
   - Set the role to **Viewer**.
   - Copy the file's sharing link.
4. Verify that each link points to the intended file and that the upload has completed.

**Privacy:** Anyone who obtains an “Anyone with the link” URL may be able to access that file. Do not publish these links. You can restore restricted access after the build if appropriate.

## 4. Configure GitHub Secrets

In the repository, open:

**Settings → Secrets and variables → Actions → New repository secret**

Create the following repository secrets. Names are case-sensitive and must match exactly.

| Secret | Value | Required |
|---|---|---|
| `Game_URL` | Google Drive share link for the base game or RAR archive | Yes |
| `Keys_URL` | Google Drive share link for `prod.keys` | Yes |
| `Update_URL` | Google Drive share link for the update package | No |
| `DLC_URL` | Google Drive share link for the DLC package | No |
| `DLC2_URL` | Google Drive share link for the second DLC package | No |
| `BDUSS` | Baidu Netdisk login credential | Only when Baidu output is selected |
| `STOKEN` | Baidu Netdisk login credential | Only when Baidu output is selected |

`Game_URL` and `Keys_URL` are required. Leave optional update/DLC secrets unset if those files are not needed.

If you select `baidu` as the output target, configure both `BDUSS` and `STOKEN`. If either is missing, the workflow falls back to GitHub Artifact output; this does not change Google Drive as the input source.

Do not paste the contents of `prod.keys` into a Secret. The workflow expects a downloadable Google Drive file-sharing URL.

## 5. Start a build

1. Open the repository's **Actions** tab.
2. Select **NxNative - Generic IPA Builder**.
3. Click **Run workflow**.
4. Select the branch to run (normally `main`).
5. Set the inputs:

| Input | Default | Guidance |
|---|---|---|
| `device` | `iPhone 15 Pro/Pro Max or newer (standard)` | Choose the build path for your target device |
| `profile_id` | Empty | Leave empty for automatic detection; fill only if detection fails or you need to specify the base game's Title ID |
| `upload_target` | `artifact` | `artifact` downloads from GitHub Actions; `baidu` uploads to Baidu Netdisk |

### Device options

- **iPhone 15 or older (BC fallback):** selects the pinned BC fallback build path.
- **iPhone 15 Pro/Pro Max or newer (standard):** selects the Standard upstream build path.

These options select different build paths; they are not a compatibility guarantee for every game or device. Choose based on the target device and the game's actual requirements.

### Profile ID

Normally leave this field empty. The workflow detects the base game's Title ID from the supplied game package contents. If you enter it manually, use the base game's **16-character hexadecimal Title ID**—not the game name, update Title ID, or DLC Title ID.

### Output destination

- `artifact`: download the output from the Artifacts section of the workflow run.
- `baidu`: after validating upload capability, the workflow uploads RomFS (when required by the Standard path) and the IPA to a unique folder for that run. The folder name resembles `/NxNative-Build-RUN_ID-ATTEMPT`.

## 6. Monitor the build

1. Stay on the **Actions** page after starting the workflow.
2. Open the latest workflow run.
3. Select the `build` job to view its logs.
4. Check the download, package validation, Title ID detection, Shader Split, Metal compilation, and IPA upload steps.

Only the repository owner is allowed to execute the build job. If another collaborator triggers the workflow, the job will not run.

### Two-stage Standard build

The Standard path processes and splits shaders first, then delivers a standalone `RomFS.img` before Metal compilation. It then resumes the cached build flow and releases Shader, RomFS, and NSP space that is no longer needed before continuing Metal compilation and generating the IPA. This reduces peak disk usage on the macOS runner, especially for large games.

The BC fallback path does not use this separate RomFS delivery flow; it follows its bundled-RomFS build path.

## 7. Download the build outputs

### GitHub Actions Artifacts

When `upload_target=artifact`:

1. Open the workflow run's Summary page.
2. Find the **Artifacts** section.
3. Download `NxNative-IPA-Standard` or `NxNative-IPA-BC-Fallback`.
4. Extract the downloaded ZIP to obtain the `.ipa` file.

If the Standard path generates a separate RomFS output, an `NxNative-ROMFS` Artifact is also provided. Build logs are uploaded as `NxNative-Build-Logs`. The workflow configures a 7-day Artifact retention period.

### Baidu Netdisk

When `upload_target=baidu` and the credentials and upload preflight succeed, the IPA (and RomFS when required by the Standard path) is uploaded to the unique folder shown in the workflow logs. Open that folder in a Baidu Netdisk client to retrieve the files.

## 8. Troubleshooting

### Google Drive download fails

- Make sure the file is shared as **Anyone with the link / Viewer**.
- Check that the Secret contains the correct file-sharing URL.
- Confirm the upload has completed.
- Large files may encounter Google Drive confirmation or temporary traffic limits.

The workflow makes up to three download attempts. If all attempts fail, verify the link and sharing permissions first.

### Missing or unreadable prod.keys

Make sure `Keys_URL` points to the actual `prod.keys` file, not a Drive folder or preview page. The keys must match the game files.

### Title ID detection fails

Verify that the base game package downloaded correctly and is not corrupted. If needed, enter the base game's 16-character hexadecimal Title ID in `profile_id`.

### No game package found or package validation fails

The Google Drive workflow accepts NSP/XCI/NSZ/XCZ packages directly, or RAR archives containing supported packages. Check that the file is complete and that its extension matches its actual contents.

### Baidu output is not used

Verify that both `BDUSS` and `STOKEN` are configured. Before the build, the workflow uploads a 1 MiB preflight file. If the credentials are missing, it falls back to GitHub Artifact output.

### Build fails

Open the failed step and locate the **first actual error** in the logs. Later errors may be consequences of the first failure. Before sharing logs, remove download URLs, cookies, tokens, and other sensitive information.

## 9. Pre-build checklist

- [ ] The base game and matching `prod.keys` are ready.
- [ ] Required update and DLC files are ready.
- [ ] Google Drive file links are accessible.
- [ ] `Game_URL` and `Keys_URL` are configured.
- [ ] Optional update/DLC secrets are configured if needed.
- [ ] `BDUSS` and `STOKEN` are configured if Baidu output is required.
- [ ] The correct device build path is selected.
- [ ] The output destination is selected.
- [ ] The IPA and build logs are checked after completion.

---

**Compatibility note:** Successful IPA generation does not guarantee that the game will run correctly on the target iPhone or iPad. Actual results depend on the game version, device, build path, and the game's own compatibility.
