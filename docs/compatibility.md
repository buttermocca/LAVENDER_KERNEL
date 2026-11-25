# Compatibility and integration record

Investigation date: 2026-11-26. This document records source-derived facts separately from build/runtime status.

## 1. Exact device target

| Item | Value |
|---|---|
| Device | Xiaomi Redmi Note 7 / `lavender` |
| Android | 16 |
| ROM | Lunaris AOSP 3.13 GMS-Official |
| Security patch | 2026-11-01 |
| Baseband | `3.1-00777-SDM660_GEN_PACK-1.381998.1.399979.1` |
| Running kernel | `4.19.325-cip136-st20-SouthWest-NG-0.23.0` |
| Running root state | `su` was absent; Manager installation alone had not enabled root |

## 2. Source pins

| Component | Pin | Purpose |
|---|---|---|
| SouthWest-NG kernel | `pix106/android_kernel_xiaomi_sdm660_southwest-ng` @ `cff390118b0803a60f332bf0f39ab0289bbb0195` | Exact 0.23.0 source base |
| KernelSU Next driver | `KernelSU-Next/KernelSU-Next` @ `0b17f24246db5c80c056b92c15bcad2b77f1276e` | Non-GKI 4.19 legacy/manual-hook driver base |
| KSU 4.19 compatibility + SUSFS integration | `6078HITHEDAY/tb128fu-kernelsu-next-reference` @ `54dbc5ac847872d16fb268cb4072bd37d9ee7d5c` | Pinned known-good patch set |
| NoMount Suite | `Bouteillepleine/NoMount-Suite` v1.3.217 @ `66f4452ae4fdde2df162af32c38bdb1bd8ebfafd` | 4.19 in-tree hookless engine |
| Clang toolchain | `LineageOS/android_prebuilts_clang_kernel_linux-x86_clang-r416183b` @ `54220fd601050b350b2af7adc913089ebf0e7aed` | Reproducible compiler |

## 3. KernelSU Next integration choice

The selected source is the KernelSU Next **legacy/manual-hook** line, not the upstream v3.4.2 kernel driver tree. The reference project pins commit `0b17f242`, adds a manual sucompat entry and retries a userspace filename read in process context, then integrates SUSFS v2.3.0 into the legacy supercall path.

The selected integration reports UAPI version 5 to match the released official v3.4.2 Manager. It uses:
- `CONFIG_KSU=y`
- `CONFIG_KSU_MANUAL_HOOK=y`
- `CONFIG_KPROBES=n`
- no syscall-table hook
- explicit call-site hooks in the 4.19 source tree

The upstream v3.4.2 KSU kernel release uses a different source organization and its official prebuilt kernel/SUSFS LKM assets are GKI/KMI variants for Android 5.10 and newer. Those binaries must not be renamed or loaded on this 4.19 CIP kernel.

**Version distinction:** the Manager is v3.4.2; the kernel driver is based on the v3.4.0-legacy source snapshot at the pinned commit above, with compatibility patches. This is the tested compatibility choice, not a claim that the v3.4.2 upstream kernel driver has been ported.

Sources:
- https://github.com/KernelSU-Next/KernelSU-Next/releases/tag/v3.4.2
- https://github.com/6078HITHEDAY/tb128fu-kernelsu-next-reference

## 4. SUSFS v2.3.0 NON-GKI

The selected reference integrates SUSFS v2.3.0 directly into the non-GKI kernel and wires its command handling through KernelSU Next's legacy supercall path. This differs from the current official KernelSU Next SUSFS guard LKM, whose downloadable assets are GKI KMI-specific for 5.10 and newer.

The user-space helper is separate from the kernel implementation. The current sidex15 module release is Revision 28 (`v1.5.2+_R28`), which communicates with patched SUSFS kernels; install it only after the matching patched kernel has booted.

Sources:
- https://github.com/KernelSU-Next/KernelSU-Next/releases/tag/v3.4.2
- https://github.com/sidex15/susfs4ksu-module/releases/tag/v1.5.2%2B_R28
- https://github.com/6078HITHEDAY/tb128fu-kernelsu-next-reference/blob/main/docs/pitfalls.md

## 5. NoMount v1.3.217

The selected NoMount path is the hookless/in-tree engine, not the LKM variant. The NoMount integration patch is supported by its project for Linux 4.19, and requires:
- its kernel integration patch,
- `hookless/src/nomount.c` and `nomount.h` copied into `fs/`,
- `CONFIG_NOMOUNT=y`,
- the matching `00_NoMount-Module` metamodule after the kernel is installed.

The NoMount integration is applied **before** the SUSFS patch because both modify `fs/proc/task_mmu.c`. The build uses the exact NoMount v1.3.217 tag commit above.

Scope limitation: this hookless integration provides path redirection, maps dev/inode rewriting and the xattr guard. It does not include all optional `_ghost` / `_pathhide` call-site cloaks present in the fuller forks. The build must not advertise those optional cloaks as enabled.

Sources:
- https://github.com/Bouteillepleine/NoMount-Suite/releases/tag/v1.3.217
- https://github.com/Bouteillepleine/NoMount-Suite/tree/main/hookless

## 6. Adaptation to SouthWest-NG CIP136-ST20

The reference patch set was validated against a different Linux 4.19.325 CIP135-ST19 tree. Lunaris currently runs SouthWest-NG 0.23.0, CIP136-ST20. Linux version equivalence alone does not prove source compatibility.

The committed build script therefore:
1. checks out the exact SouthWest-NG commit,
2. checks out pinned KSU Next, NoMount and clang commits,
3. verifies the four reference patch SHA-256 values,
4. applies KSU patches with `git apply --check`,
5. applies the manual-hook, NoMount, and SUSFS kernel patches in that order with no fuzz,
6. merges the original SDM660 base config, lavender device config and feature fragment,
7. asserts KSU manual-hook, SUSFS, NoMount and lavender options are enabled,
8. builds `Image-dtb`.

The manual-hook patch's reference-only `grass-perf_defconfig` hunk is excluded; the actual target uses `vendor/xiaomi/sdm660_defconfig` plus `vendor/xiaomi/lavender.config`.

Any context mismatch is a hard stop. A mismatch requires a reviewed port to the CIP136-ST20 files; it must not be bypassed with fuzz or by deleting failing hunks.

## 7. Current execution status

Initial CI runs `#1` and `#2` both failed during the manual-hook kernel patch application, before Kconfig generation or C compilation. The exact mismatched hunks were:
- `drivers/Kconfig`: the reference patch anchors to `drivers/gud/Kconfig`, which is absent in SouthWest-NG.
- `drivers/Makefile`: the reference patch anchors to a OnePlus/OPlus driver tail not present in this SDM660 tree.
- `include/linux/compiler-clang.h`: the reference patch expects a newer `__diagnose_as` block which this tree does not contain; the reference/KSU source search did not find a caller requiring it.

The build script was changed to apply the remaining manual-hook call-site hunks without fuzz, then add the KSU Kconfig source at this tree's actual final `endmenu` and the KSU Makefile object at the actual end of `drivers/Makefile`. The unused clang-attribute hunk is skipped rather than inserted into a file whose source layout does not contain it. The follow-up CI runs are now checking that adaptation and the subsequent NoMount/SUSFS patches.

## 8. Post-build modules

After the new kernel boots and KernelSU Next reports Working, install:
- official KernelSU Next v3.4.2 Manager, not a repackaged Manager,
- SUSFS-for-KernelSU Revision 28 user-space module,
- NoMount `00_NoMount-Module-v1.3.217.zip`.

Do not install `01_NoMount-Module-LKM`; it is intended for stock GKI 5.10–6.18, not this in-tree 4.19 build.

Links:
- https://github.com/KernelSU-Next/KernelSU-Next/releases/tag/v3.4.2
- https://github.com/sidex15/susfs4ksu-module/releases/tag/v1.5.2%2B_R28
- https://github.com/Bouteillepleine/NoMount-Suite/releases/download/v1.3.217/00_NoMount-Module-v1.3.217.zip
