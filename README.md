# LAVENDER_KERNEL

Redmi Note 7 (**lavender**) kernel integration for the existing Lunaris AOSP 3.13 GMS-Official ROM. The ROM is not replaced.

## Target captured from the phone

| Item | Value |
|---|---|
| Device | Xiaomi Redmi Note 7 / `lavender` |
| Android | 16 |
| ROM | Lunaris AOSP 3.13 GMS-Official |
| Security patch | 2026-11-01 |
| Kernel | `4.19.325-cip136-st20-SouthWest-NG-0.23.0` |
| Current state | KernelSU Manager is installed, but the running kernel has no KSU driver and `su` is absent |

## Integration plan now committed

- **Kernel base:** `pix106/android_kernel_xiaomi_sdm660_southwest-ng` at `cff390118b0803a60f332bf0f39ab0289bbb0195`.
- **KernelSU Next:** legacy/manual-hook source at `0b17f24246db5c80c056b92c15bcad2b77f1276e`, with the 4.19 compatibility and SUSFS supercall patches from the pinned reference project. This is the v3.4.0-legacy driver line with UAPI 5, paired with the official v3.4.2 Manager. It is **not** the upstream v3.4.2 kernel driver; that driver has no equivalent verified manual-hook + SUSFS 2.3 integration for this non-GKI 4.19 target.
- **SUSFS:** v2.3.0 NON-GKI, built into the kernel. It is not the GKI 5.10+ SUSFS guard LKM.
- **NoMount:** v1.3.217 hookless/in-tree engine. Its kernel patch is applied before SUSFS because both touch `fs/proc/task_mmu.c`.
- **Toolchain:** LineageOS clang-r416183b at `54220fd601050b350b2af7adc913089ebf0e7aed`.

The reference kernel that supplied the 4.19.325 manual-hook/SUSFS port is CIP135-ST19. The Lunaris kernel is CIP136-ST20. The build deliberately applies patches without fuzz and stops if any source hunk does not match. This source-port gate is essential; matching only the Linux version number is not proof of compatibility.

## Build

A pinned GitHub Actions build recipe is included:

- Workflow: [Build Redmi Note 7 lavender kernel](.github/workflows/build-lavender.yml)
- Script: [scripts/build_lavender.sh](scripts/build_lavender.sh)
- Config: [configs/lavender-ksu-susfs-nomount.fragment](configs/lavender-ksu-susfs-nomount.fragment)

To run it, open the repository's **Actions** tab, choose **Build Redmi Note 7 lavender kernel**, then select **Run workflow**. The job first checks every pinned patch with `git apply --check`, merges SDM660 + lavender device configs, verifies the required Kconfig options, and only then compiles `Image-dtb`.

**Current build status: not yet compiled or boot-tested.** The workflow and reproducible build recipe are committed, but no Actions run/artifact is visible yet. The first CI run must pass before an image is treated as usable.

## Expected post-build packages

Install these only after a kernel with all three integrations has been successfully built and booted:

1. KernelSU Next official v3.4.2 Manager (not a repackaged/spoofed Manager).
2. SUSFS-for-KernelSU userspace helper, Revision 28: [sidex15 release](https://github.com/sidex15/susfs4ksu-module/releases/tag/v1.5.2%2B_R28).
3. NoMount **in-tree** metamodule: [00_NoMount-Module v1.3.217](https://github.com/Bouteillepleine/NoMount-Suite/releases/download/v1.3.217/00_NoMount-Module-v1.3.217.zip). Do not use the LKM package for this 4.19 build.

NoMount's hookless in-tree engine provides path redirection, maps dev/inode rewriting and the xattr guard. It does **not** include every optional `_ghost` / `_pathhide` cloak available in the fuller forked kernels; do not expect `nomount check` to report those optional cloaks as available.

## Safety / output boundary

The pipeline produces `Image-dtb`, the final `.config`, and logs. It does not produce an AnyKernel ZIP or a boot image because the actual Lunaris `boot.img` header/ramdisk have not been supplied for a matching repack. Do not flash the kernel image as though it were a complete boot image. Back up the current boot image and verify a recovery path before any hardware test.

Detailed rationale and exact pins: [docs/compatibility.md](docs/compatibility.md).
