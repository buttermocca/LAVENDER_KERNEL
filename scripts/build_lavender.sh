#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="\${GITHUB_WORKSPACE:-$(pwd)}"
WORK="$ROOT/work"; KERNEL="$WORK/kernel"; KSU="$WORK/ksu_next"; OUT="$KERNEL/out"
KERNEL_COMMIT="cff390118b0803a60f332bf0f39ab0289bbb0195"
KSU_COMMIT="0b17f24246db5c80c056b92c15bcad2b77f1276e"
NMS_COMMIT="66f4452ae4fdde2df162af32c38bdb1bd8ebfafd"
CLANG_COMMIT="54220fd601050b350b2af7adc913089ebf0e7aed"
REF_COMMIT="54dbc5ac847872d16fb268cb4072bd37d9ee7d5c"
REF="https://raw.githubusercontent.com/6078HITHEDAY/tb128fu-kernelsu-next-reference/$REF_COMMIT"
NMS="https://raw.githubusercontent.com/Bouteillepleine/NoMount-Suite/$NMS_COMMIT"
mkdir -p "$WORK" "$ROOT/dist" "$ROOT/logs"
exec > >(tee "$ROOT/logs/build.log") 2>&1

fetch() { curl -fL --retry 4 --retry-all-errors --connect-timeout 30 "$1" -o "$2"; }
clone_pin() {
  git clone --filter=blob:none --no-checkout "$1" "$2"
  git -C "$2" fetch --depth=1 origin "$3"
  git -C "$2" checkout --detach FETCH_HEAD
  test "$(git -C "$2" rev-parse HEAD)" = "$3"
}
check_hash() { echo "$2  $1" | sha256sum -c -; }

echo "=== Clone pinned sources ==="
clone_pin https://github.com/pix106/android_kernel_xiaomi_sdm660_southwest-ng.git "$KERNEL" "$KERNEL_COMMIT"
clone_pin https://github.com/KernelSU-Next/KernelSU-Next.git "$KSU" "$KSU_COMMIT"
clone_pin https://github.com/Bouteillepleine/NoMount-Suite.git "$WORK/nomount" "$NMS_COMMIT"
clone_pin https://github.com/LineageOS/android_prebuilts_clang_kernel_linux-x86_clang-r416183b.git "$WORK/clang" "$CLANG_COMMIT"

mkdir -p "$WORK/patches"
fetch "$REF/patches/ksu-next/0001-manual-sucompat-retry-uapi5.diff" "$WORK/patches/ksu1.diff"
fetch "$REF/patches/ksu-next/0002-susfs-v2.3.0-legacy-integration.diff" "$WORK/patches/ksu2.diff"
fetch "$REF/patches/kernel/0001-manual-hook-integration.patch" "$WORK/patches/kernel1.patch"
fetch "$REF/patches/kernel/0002-susfs-v2.3.0-non-gki.patch" "$WORK/patches/kernel2.patch"
fetch "$REF/patches/build-compat/engine.h" "$WORK/patches/engine.h"
fetch "$NMS/hookless/patches/nomount_kernel_integration.patch" "$WORK/patches/nomount.patch"

check_hash "$WORK/patches/ksu1.diff" "186f74f6e647f84b130e03e8bc36c9c952207038f764b86a5e2299d7de51cd43"
check_hash "$WORK/patches/ksu2.diff" "e7f19bfbf414b4cd94e795ecfbaa5f52a464468ecda0e2f3f112bc3dd38b0a80"
check_hash "$WORK/patches/kernel1.patch" "987b02137a5ea4737b34202cf9c801da32873ba8a8962ead8df72b3c8365450e"
check_hash "$WORK/patches/kernel2.patch" "4c146871a895af2f8b375ab88553bd81c4bb623461dcd44138c5402f152559bc"
check_hash "$WORK/patches/engine.h" "de3d8eac3e193da0015b013e45eecc605faa9ec30c07c12b8c"

echo "=== KernelSU Next legacy manual-hook + SUSFS 2.3 integration ==="
git -C "$KSU" apply --check "$WORK/patches/ksu1.diff"
git -C "$KSU" apply "$WORK/patches/ksu1.diff"
git -C "$KSU" apply --check "$WORK/patches/ksu2.diff"
git -C "$KSU" apply "$WORK/patches/ksu2.diff"
grep -q '^#define KERNEL_SU_UAPI_VERSION 5' "$KSU/uapi/supercall.h"

echo "=== SouthWest-NG kernel manual-hook integration ==="
git -C "$KERNEL" apply --check --exclude=arch/arm64/configs/grass-perf_defconfig "$WORK/patches/kernel1.patch"
git -C "$KERNEL" apply --exclude=arch/arm64/configs/grass-perf_defconfig "$WORK/patches/kernel1.patch"

echo "=== NoMount v1.3.217 integration BEFORE SUSFS ==="
sed -n '/^diff --git /,$p' "$WORK/patches/nomount.patch" > "$WORK/patches/nomount-clean.patch"
test -s "$WORK/patches/nomount-clean.patch"
git -C "$KERNEL" apply --check "$WORK/patches/nomount-clean.patch"
git -C "$KERNEL" apply "$WORK/patches/nomount-clean.patch"
fetch "$NMS/hookless/src/nomount.c" "$KERNEL/fs/nomount.c"
fetch "$NMS/hookless/src/nomount.h" "$KERNEL/fs/nomount.h"

echo "=== SUSFS 2.3.0 NON-GKI kernel integration AFTER NoMount ==="
git -C "$KERNEL" apply --check --exclude=arch/arm64/configs/grass-perf_defconfig "$WORK/patches/kernel2.patch"
git -C "$KERNEL" apply --exclude=arch/arm64/configs/grass-perf_defconfig "$WORK/patches/kernel2.patch"

ln -sfn ../../ksu_next/kernel "$KERNEL/drivers/kernelsu"
mkdir -p "$KERNEL/scripts/openssl-stub/openssl"
cp "$WORK/patches/engine.h" "$KERNEL/scripts/openssl-stub/openssl/engine.h"

export PATH="$WORK/clang/bin:$PATH"
clang --version | head -n 1
cd "$KERNEL"
ARGS=(ARCH=arm64 O=out CC=clang LLVM=1 LLVM_IAS=1 CLANG_TRIPLE=aarch64-linux-gnu- CROSS_COMPILE=aarch64-linux-gnu- CROSS_COMPILE_ARM32=arm-linux-gnueabi-)

echo "=== Configure SDM660 + lavender + KSU/SUSFS/NoMount ==="
make "\${ARGS[@]}" vendor/xiaomi/sdm660_defconfig
"$KERNEL/scripts/kconfig/merge_config.sh" -m -O "$OUT" "$OUT/.config" \
  "$KERNEL/arch/arm64/configs/vendor/xiaomi/lavender.config" \
  "$ROOT/configs/lavender-ksu-susfs-nomount.fragment"
make "\${ARGS[@]}" olddefconfig

grep -q '^CONFIG_KSU=y$' "$OUT/.config"
grep -q '^CONFIG_KSU_MANUAL_HOOK=y$' "$OUT/.config"
grep -q '^# CONFIG_KPROBES is not set$' "$OUT/.config"
grep -q '^CONFIG_KSU_SUSFS=y$' "$OUT/.config"
grep -q '^CONFIG_NOMOUNT=y$' "$OUT/.config"
grep -q '^CONFIG_MACH_XIAOMI_LAVENDER=y$' "$OUT/.config"
grep -q '^CONFIG_BUILD_ARM64_APPENDED_DTB_IMAGE=y$' "$OUT/.config"

cp "$OUT/.config" "$ROOT/dist/kernel.config"
grep -E '^(CONFIG_KSU=|CONFIG_KSU_MANUAL_HOOK=|CONFIG_KSU_SUSFS=|CONFIG_NOMOUNT=|CONFIG_MACH_XIAOMI_LAVENDER=|CONFIG_LOCALVERSION=)' "$OUT/.config" > "$ROOT/dist/config-summary.txt"

echo "=== Compile Image-dtb ==="
make "\${ARGS[@]}" -j2 Image-dtb
IMAGE="$OUT/arch/arm64/boot/Image-dtb"
test -s "$IMAGE"
cp "$IMAGE" "$ROOT/dist/Image-dtb"
sha256sum "$ROOT/dist/Image-dtb" | tee "$ROOT/dist/SHA256SUMS"
cat > "$ROOT/dist/build-manifest.txt" <<EOF
Device: Redmi Note 7 (lavender)
ROM target: Lunaris AOSP 3.13 GMS-Official / Android 16
Kernel: 4.19.325-cip136-st20-SouthWest-NG-0.23.0
Kernel source commit: $KERNEL_COMMIT
KernelSU Next legacy base: $KSU_COMMIT (manual hook, UAPI 5)
SUSFS: v2.3.0 NON-GKI in-tree
NoMount: v1.3.217 / $NMS_COMMIT hookless in-tree engine
Clang-r416183b commit: $CLANG_COMMIT
Output: Image-dtb only; no boot.img or flashable ZIP
EOF
echo "Build passed; this is not a device-tested boot image."
