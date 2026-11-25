# Compatibility report: Lunaris 3.13 GMS / lavender / Linux 4.19.325

Investigation date: 2026-11-26.

## 1. Exact target recorded from the supplied Android Version screen

- Device: Xiaomi Redmi Note 7 | `lavender`
- Android: 16
- ROM package type: `GMS-OFFICIAL`
- ROM: Lunaris AOSP 3.13 GMS-Official
- Android security patch: 2026-11-01
- Baseband: `3.1-00777-SDM660_GEN_PACK-1.381998.1.399979.1`
- Kernel: `4.19.325-cip136-st20-SouthWest-NG-0.23.0`
- Kernel build: `#1 Mon Nov 23 19:35:43 UTC 2026`

ADB checks supplied by the owner show:

```text
adb shell su -c id
/system/bin/sh: su: inaccessible or not found

adb shell uname -r
4.19.325-cip136-st20-SouthWest-NG-0.23.0
```

The installed KernelSU Next Manager v3.4.2-spoofed reports that the non-GKI kernel has no KernelSU Next driver integrated. The APK is only the manager; it does not install the required in-kernel driver.

## 2. Source pins inspected

| Component | Source / pin | Finding |
|---|---|---|
| SouthWest-NG kernel | `pix106/android_kernel_xiaomi_sdm660_southwest-ng` / `cff390118b0803a60f332bf0f39ab0289bbb0195` | Exact 0.23.0 generation; contains lavender config and SDM660 base defconfig |
| KernelSU Next | `KernelSU-Next/KernelSU-Next` current `dev` snapshot inspected at `3660779ea2e2fe1adb27616d8aad9ffaad717501` | Current driver code; non-GKI 4.19 requires the driver built into the kernel |
| KernelSU Next release | `v3.4.2` | Official release published 2026-10-13; its downloadable SUSFS guard LKM assets are KMI-specific GKI assets |
| NoMount Suite | `Bouteillepleine/NoMount-Suite` latest release inspected: `v1.3.217` | Built-in / hookless integration supports Linux 4.19; LKM zip is for GKI 5.10–6.18 |
| SUSFS upstream 4.19 | `simonpunk/susfs4ksu`, `kernel-4.19`, commit `001e69919c6271f690fd00b17e4c721c9e599152` | SUSFS v1.5.5, last update 2025-02-23 |

## 3. KernelSU Next: feasible on this kernel

KernelSU Next's published compatibility notes state that 4.19–5.4 requires the driver built into the kernel. The current upstream has a `legacy` integration path and a syscall-table hook option for ARM64 kernels >=4.17. Therefore a built-in KernelSU Next driver is a feasible route for this 4.19.325 ARM64 kernel.

The actual defconfig still needs deliberate integration. In the SouthWest-NG source, the base `sdm660_defconfig` has `CONFIG_KPROBES` disabled and `CONFIG_MODULES` disabled. The correct hook mode and all required kernel options must be selected before building; do not simply flash the Manager APK again.

References:
- https://github.com/KernelSU-Next/KernelSU-Next
- https://github.com/KernelSU-Next/KernelSU-Next/tree/legacy
- https://github.com/KernelSU-Next/KernelSU-Next/releases/tag/v3.4.2

## 4. NoMount: a 4.19 in-tree integration exists

The NoMount Suite's `hookless` integration explicitly lists Linux 4.19. It requires:
- the 4.19-compatible `nomount_kernel_integration.patch`,
- `hookless/src/nomount.c` and `hookless/src/nomount.h` copied into `fs/`,
- `CONFIG_NOMOUNT=y`,
- and the matching `00_NoMount-Module` metamodule installed from the KernelSU Next manager.

The `01_NoMount-Module-LKM` package is not for this 4.19 kernel; the project documents that LKM package for GKI 5.10–6.18.

There is a scope caveat: the documented `hookless` integration does not implement every optional cloak/path-hide call-site feature that exists in the fuller in-tree forks. It is not accurate to call that subset a fully verified implementation of every NoMount hiding feature. Kernel patch application and runtime behavior still need testing on the exact SouthWest-NG tree.

References:
- https://github.com/Bouteillepleine/NoMount-Suite
- https://github.com/Bouteillepleine/NoMount-Suite/tree/main/hookless

## 5. SUSFS: this is the blocking compatibility issue

There are two different SUSFS paths; neither currently gives a verified drop-in solution for this exact kernel plus the latest KernelSU Next:

### 5.1 Current KernelSU Next SUSFS guard LKM

The current KernelSU Next release publishes SUSFS guard modules by GKI KMI name (for example `android16-6.12_susfs_guard_lkm.ko`). Its userspace `ksud susfs load` selects an embedded module asset by KMI. There is no official `4.19.325-cip136-st20-SouthWest-NG-0.23.0` asset.

The current source labels this LKM `2.3.0-gki`. Its BTF-layout code resolves `btf_vmlinux` and BTF type functions. This makes it a GKI-oriented path, not a known-compatible 4.19 CIP module. Reusing a random GKI `.ko` or only renaming its KMI asset would be unsafe.

Reference:
- https://github.com/KernelSU-Next/KernelSU-Next/blob/dev/kernel/susfs/susfs_core.h
- https://github.com/KernelSU-Next/KernelSU-Next/blob/dev/kernel/susfs/btf_layout.c
- https://github.com/KernelSU-Next/KernelSU-Next/releases/tag/v3.4.2

### 5.2 Upstream non-GKI SUSFS 4.19 patch

The available upstream `kernel-4.19` branch is SUSFS v1.5.5, commit `001e6991`, dated 2025-02-23. Its KernelSU-side integration patch was written for the older flat KernelSU source layout. Current KernelSU Next is substantially refactored. A build script that blindly applies that old patch to current KernelSU Next should be expected to fail or require a real port.

A community KernelSU build guide explicitly notes that non-GKI SUSFS branches have not been updated since early 2025 and their KernelSU-side patch can fail against restructured forks.

References:
- https://gitlab.com/simonpunk/susfs4ksu/-/tree/kernel-4.19
- https://github.com/Albanel22/xiaoleGun-KernelSU_Action

## 6. Why this repository does not publish a kernel image yet

The kernel source and device config are known, but a complete source-level integration has not been demonstrated for:

```text
KernelSU Next v3.4.x
+ SUSFS (a 4.19-compatible implementation)
+ NoMount
+ SouthWest-NG 0.23.0 / lavender
```

A KSU Next + NoMount kernel without working SUSFS would not meet the owner's request. Likewise, an old SUSFS patch that merely applies with fuzz, a GKI-only SUSFS module renamed to look like a 4.19 module, or an image that has not been built and boot-tested must not be advertised as a completed kernel.

No boot image, flashable ZIP, or prebuilt binary has been generated by this repository at this stage. The next engineering milestone is to port and compile-test a SUSFS implementation against the exact 4.19.325 SouthWest-NG source while preserving the current Lunaris GMS userspace, then run the full kernel build and static artifact checks. Only after those gates pass should a reversible boot test be prepared.
