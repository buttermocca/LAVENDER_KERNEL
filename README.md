# LAVENDER_KERNEL

Compatibility investigation for the Redmi Note 7 (lavender) running Lunaris AOSP 3.13 GMS-Official.

## Device/build target

| Item | Observed value |
|---|---|
| Device | Xiaomi Redmi Note 7 / lavender |
| RAM | 4 GB |
| ROM | Lunaris AOSP 3.13 GMS-Official |
| Android | 16 |
| Security patch | 2026-11-01 |
| Kernel | 4.19.325-cip136-st20-SouthWest-NG-0.23.0 |
| Kernel build timestamp | 2026-11-23 19:35:43 UTC |
| Current root state | Not rooted; `su` is absent |
| Current Manager | KernelSU Next 3.4.2-spoofed |

## Requested result

Keep the existing Lunaris GMS ROM and provide:

1. KernelSU Next (current 3.4.x manager line), built into the non-GKI 4.19 kernel.
2. SUSFS support.
3. NoMount support.

## Current compatibility decision

**No flashable kernel is published by this repository yet.** The integration is intentionally blocked until the SUSFS implementation is proven against this exact 4.19.325 CIP kernel. A kernel image that only boots but does not actually load SUSFS is not considered a completed result.

- KernelSU Next: the current project supports non-GKI kernels when its driver is built into the kernel. The 4.19 branch requires a legacy/in-tree integration; installing the Manager APK alone does not root the phone.
- NoMount: the current NoMount Suite provides a hookless in-tree integration for Linux 4.19. Its kernel engine requires `CONFIG_NOMOUNT=y`, the integration patch and source files, plus the matching `00_NoMount-Module` metamodule.
- SUSFS: the latest KernelSU Next SUSFS guard LKM is marked GKI-oriented and the official v3.4.2 release only publishes KMI-specific LKM assets for 5.10 and newer. The current 4.19 CIP kernel has no matching published KMI asset. The older upstream `kernel-4.19` SUSFS branch is v1.5.5 (last updated 2025-02-23); its KernelSU-side patch targets the older flat KernelSU layout and is not a drop-in patch for the current refactored KernelSU Next source.

See [the compatibility report](docs/compatibility.md) for exact source pins and the integration boundary.

## Kernel source baseline

- Source: [pix106/android_kernel_xiaomi_sdm660_southwest-ng](https://github.com/pix106/android_kernel_xiaomi_sdm660_southwest-ng)
- Baseline commit: `cff390118b0803a60f332bf0f39ab0289bbb0195` (SouthWest-NG 0.23.0)
- Lavender device config: `arch/arm64/configs/vendor/xiaomi/lavender.config`
- Base defconfig: `arch/arm64/configs/vendor/xiaomi/sdm660_defconfig`

The observed base defconfig has `CONFIG_KPROBES` disabled and `CONFIG_MODULES` disabled. Both settings must be reconsidered explicitly for the requested KSU/SUSFS/NoMount configuration. No generic kernel ZIP should be flashed over the current ROM without a verified matching build and a tested recovery path.

## Safety

This repository currently contains compatibility notes only. It does not contain a boot image, flashable ZIP, or a completed kernel build. Do not flash a file merely because its filename contains `lavender`, `SouthWest-NG`, or `legacy`.
