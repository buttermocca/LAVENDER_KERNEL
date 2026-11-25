#!/usr/bin/env python3
"""Port SUSFS v2.3.0 integration hunks onto the pinned SouthWest-NG 4.19 tree.

The upstream reference patch is based on a different Android 4.19 derivative.
NoMount is applied first, so its pagemap metadata hook is preserved and SUSFS
map spoofing is layered after it.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: port_susfs_southwest.py KERNEL_SOURCE_DIR")

root = Path(sys.argv[1])

def replace_once(relpath: str, old: str, new: str, description: str) -> None:
    path = root / relpath
    content = path.read_text()
    if new in content:
        return
    count = content.count(old)
    if count != 1:
        raise SystemExit(
            f"{description}: expected one anchor in {relpath}, found {count}"
        )
    path.write_text(content.replace(old, new, 1))


def replace_once_in_region(relpath: str, start_marker: str, end_marker: str,
                           old: str, new: str, description: str) -> None:
    path = root / relpath
    content = path.read_text()
    start = content.find(start_marker)
    if start < 0:
        raise SystemExit(f"{description}: start marker missing in {relpath}")
    end = content.find(end_marker, start + len(start_marker))
    if end < 0:
        raise SystemExit(f"{description}: end marker missing in {relpath}")
    region = content[start:end]
    if new in region:
        return
    count = region.count(old)
    if count != 1:
        raise SystemExit(
            f"{description}: expected one anchor inside selected function in {relpath}, found {count}"
        )
    region = region.replace(old, new, 1)
    path.write_text(content[:start] + region + content[end:])

# fs/Makefile: this tree's filesystem object list has extra fs_types.o.
replace_once(
    "fs/Makefile",
    "\t\tfs_types.o fs_context.o fs_parser.o\n",
    "\t\tfs_types.o fs_context.o fs_parser.o\n\n"
    "obj-$(CONFIG_KSU_SUSFS) += susfs.o\n",
    "SUSFS fs/Makefile wiring",
)

# cmdline.c: retain the device tree's INITRAMFS_IGNORE_SKIP_FLAG behavior.
replace_once(
    "fs/proc/cmdline.c",
    "#include <linux/seq_file.h>\n",
    "#include <linux/seq_file.h>\n#include <linux/jump_label.h>\n",
    "SUSFS cmdline jump-label include",
)
replace_once(
    "fs/proc/cmdline.c",
    "static int cmdline_proc_show(struct seq_file *m, void *v)\n{\n",
    "static int cmdline_proc_show(struct seq_file *m, void *v)\n{\n"
    "#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG\n"
    "    extern struct static_key_false susfs_is_fake_cmdline_or_bootconfig_buffer_set;\n"
    "    extern void susfs_spoof_cmdline_or_bootconfig(struct seq_file *m);\n"
    "    if (static_branch_likely(&susfs_is_fake_cmdline_or_bootconfig_buffer_set)) {\n"
    "        susfs_spoof_cmdline_or_bootconfig(m);\n"
    "        seq_putc(m, '\\n');\n"
    "        return 0;\n"
    "    }\n"
    "#endif\n",
    "SUSFS cmdline spoof hook",
)

# task_mmu.c: merge SUSFS with NoMount's already-applied metadata override.
replace_once(
    "fs/proc/task_mmu.c",
    "#include <linux/ctype.h>\n",
    "#include <linux/ctype.h>\n"
    "#if defined(CONFIG_KSU_SUSFS_SUS_KSTAT) || defined(CONFIG_KSU_SUSFS_SUS_MAP) || defined(CONFIG_KSU_SUSFS_OPEN_REDIRECT)\n"
    "#include <linux/susfs_def.h>\n"
    "#endif\n"
    "#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n"
    "#include <linux/srcu.h>\n"
    "#endif\n",
    "SUSFS task_mmu includes",
)
replace_once(
    "fs/proc/task_mmu.c",
    "static void\nshow_map_vma(struct seq_file *m, struct vm_area_struct *vma)\n",
    "#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n"
    "extern void susfs_sus_kstat_spoof_show_map_vma(struct inode *inode, dev_t *out_dev, unsigned long *out_ino);\n"
    "#endif\n"
    "#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n"
    "extern struct srcu_struct susfs_srcu_open_redirect;\n"
    "extern int susfs_open_redirect_spoof_show_map_vma_srcu(struct inode *inode, unsigned long *out_ino, dev_t *out_dev, char **out_spoofed_name);\n"
    "#endif\n\n"
    "static void\nshow_map_vma(struct seq_file *m, struct vm_area_struct *vma)\n",
    "SUSFS task_mmu declarations",
)
replace_once(
    "fs/proc/task_mmu.c",
    "\tif (file) {\n\t\tstruct inode *inode = file_inode(vma->vm_file);\n"
    "\t\tdev = inode->i_sb->s_dev;\n",
    "\tif (file) {\n\t\tstruct inode *inode = file_inode(vma->vm_file);\n"
    "#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n"
    "\t\tif (SUSFS_IS_INODE_OPEN_REDIRECT(inode)) {\n"
    "\t\t\tchar *spoofed_redirected_name = NULL;\n"
    "\t\t\tint srcu_idx = srcu_read_lock(&susfs_srcu_open_redirect);\n"
    "\t\t\tint ret = susfs_open_redirect_spoof_show_map_vma_srcu(inode, &ino, &dev, &spoofed_redirected_name);\n"
    "\t\t\tif (!ret) {\n"
    "\t\t\t\tpgoff = ((loff_t)vma->vm_pgoff) << PAGE_SHIFT;\n"
    "\t\t\t\tstart = vma->vm_start;\n"
    "\t\t\t\tend = vma->vm_end;\n"
    "\t\t\t\tshow_vma_header_prefix(m, start, end, flags, pgoff, dev, ino);\n"
    "\t\t\t\tseq_pad(m, ' ');\n"
    "\t\t\t\tif (spoofed_redirected_name)\n"
    "\t\t\t\t\tseq_puts(m, spoofed_redirected_name);\n"
    "\t\t\t\tseq_putc(m, '\\n');\n"
    "\t\t\t\tsrcu_read_unlock(&susfs_srcu_open_redirect, srcu_idx);\n"
    "\t\t\t\treturn;\n"
    "\t\t\t}\n"
    "\t\t\tsrcu_read_unlock(&susfs_srcu_open_redirect, srcu_idx);\n"
    "\t\t}\n"
    "#endif\n"
    "#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n"
    "\t\tif (SUSFS_IS_INODE_SUS_MAP(inode))\n"
    "\t\t\treturn;\n"
    "#endif\n"
    "\t\tdev = inode->i_sb->s_dev;\n",
    "SUSFS show_map_vma open-redirect and map-hide hooks",
)
replace_once(
    "fs/proc/task_mmu.c",
    "\t\t  vfs_map_meta_override(inode, &dev, &ino); }\n"
    "#endif\n"
    "\t\tpgoff = ((loff_t)vma->vm_pgoff) << PAGE_SHIFT;\n",
    "\t\t  vfs_map_meta_override(inode, &dev, &ino); }\n"
    "#endif\n"
    "#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT\n"
    "\t\tsusfs_sus_kstat_spoof_show_map_vma(inode, &dev, &ino);\n"
    "#endif\n"
    "\t\tpgoff = ((loff_t)vma->vm_pgoff) << PAGE_SHIFT;\n",
    "SUSFS map metadata spoof after NoMount override",
)
replace_once(
    "fs/proc/task_mmu.c",
    "static int show_smap(struct seq_file *m, void *v)\n"
    "{\n"
    "\tstruct vm_area_struct *vma = v;\n"
    "\tstruct mem_size_stats mss;\n\n"
    "\tmemset(&mss, 0, sizeof(mss));\n",
    "static int show_smap(struct seq_file *m, void *v)\n"
    "{\n"
    "\tstruct vm_area_struct *vma = v;\n"
    "\tstruct mem_size_stats mss;\n\n"
    "#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n"
    "\tif (vma->vm_file && SUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file)))\n"
    "\t\treturn 0;\n"
    "#endif\n"
    "\tmemset(&mss, 0, sizeof(mss));\n",
    "SUSFS show_smap hide hook",
)
replace_once(
    "fs/proc/task_mmu.c",
    "\tfor (vma = priv->mm->mmap; vma; vma = vma->vm_next) {\n"
    "\t\tsmap_gather_stats(vma, &mss);\n"
    "\t\tlast_vma_end = vma->vm_end;\n"
    "\t}\n",
    "\tfor (vma = priv->mm->mmap; vma; vma = vma->vm_next) {\n"
    "#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n"
    "\t\tif (vma->vm_file && SUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file)))\n"
    "\t\t\tgoto bypass_orig_flow;\n"
    "#endif\n"
    "\t\tsmap_gather_stats(vma, &mss);\n"
    "#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n"
    "bypass_orig_flow:\n"
    "#endif\n"
    "\t\tlast_vma_end = vma->vm_end;\n"
    "\t}\n",
    "SUSFS smaps_rollup hide hook",
)
replace_once(
    "fs/proc/task_mmu.c",
    "\tint ret = 0, copied = 0;\n\n"
    "\tif (!mm || !mmget_not_zero(mm))\n",
    "\tint ret = 0, copied = 0;\n"
    "#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n"
    "\tstruct vm_area_struct *vma;\n"
    "#endif\n\n"
    "\tif (!mm || !mmget_not_zero(mm))\n",
    "SUSFS pagemap VMA declaration",
)
replace_once(
    "fs/proc/task_mmu.c",
    "\t\tret = mmap_read_lock_killable(mm);\n"
    "\t\tif (ret)\n"
    "\t\t\tgoto out_free;\n"
    "\t\tret = walk_page_range(start_vaddr, end, &pagemap_walk);\n"
    "\t\tmmap_read_unlock(mm);\n",
    "\t\tret = mmap_read_lock_killable(mm);\n"
    "\t\tif (ret)\n"
    "\t\t\tgoto out_free;\n"
    "#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n"
    "\t\tvma = find_vma(mm, start_vaddr);\n"
    "\t\tif (vma && vma->vm_file && SUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file)))\n"
    "\t\t\tgoto bypass_orig_flow;\n"
    "#endif\n"
    "\t\tret = walk_page_range(start_vaddr, end, &pagemap_walk);\n"
    "#ifdef CONFIG_KSU_SUSFS_SUS_MAP\n"
    "bypass_orig_flow:\n"
    "#endif\n"
    "\t\tmmap_read_unlock(mm);\n",
    "SUSFS pagemap hide hook",
)

# sys.c: port uname spoofing into this tree's plain newuname implementation.
replace_once(
    "kernel/sys.c",
    "#include <linux/utsname.h>\n",
    "#include <linux/utsname.h>\n#include <linux/jump_label.h>\n",
    "SUSFS sys.c jump-label include",
)
replace_once(
    "kernel/sys.c",
    "\treturn ret;\n}\n\nSYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)\n",
    "\treturn ret;\n}\n\n"
    "#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME\n"
    "extern struct static_key_false susfs_is_uname_spoof_buffer_set;\n"
    "extern void susfs_spoof_uname(struct new_utsname *tmp);\n"
    "#endif\n\n"
    "SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)\n",
    "SUSFS uname declarations",
)
replace_once_in_region(
    "kernel/sys.c",
    "SYSCALL_DEFINE1(newuname, struct new_utsname __user *, name)\n{",
    "\n#ifdef __ARCH_WANT_SYS_OLD_UNAME",
    "\tdown_read(&uts_sem);\n"
    "\tmemcpy(&tmp, utsname(), sizeof(tmp));\n"
    "\tup_read(&uts_sem);\n",
    "\tdown_read(&uts_sem);\n"
    "\tmemcpy(&tmp, utsname(), sizeof(tmp));\n"
    "#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME\n"
    "\tif (static_branch_likely(&susfs_is_uname_spoof_buffer_set))\n"
    "\t\tsusfs_spoof_uname(&tmp);\n"
    "#endif\n"
    "\tup_read(&uts_sem);\n",
    "SUSFS uname spoof call",
)

# Verify the key hooks survived both patch ordering and the target-tree port.
checks = {
    "fs/Makefile": ["obj-$(CONFIG_KSU_SUSFS) += susfs.o"],
    "fs/proc/cmdline.c": ["susfs_spoof_cmdline_or_bootconfig(m)"],
    "fs/proc/task_mmu.c": [
        "susfs_open_redirect_spoof_show_map_vma_srcu",
        "susfs_sus_kstat_spoof_show_map_vma(inode, &dev, &ino)",
        "SUSFS_IS_INODE_SUS_MAP(file_inode(vma->vm_file))",
        "vfs_map_meta_override(inode, &dev, &ino)",
    ],
    "kernel/sys.c": ["susfs_spoof_uname(&tmp)"],
}
for relpath, needles in checks.items():
    content = (root / relpath).read_text()
    for needle in needles:
        if needle not in content:
            raise SystemExit(f"verification failed: {needle!r} missing from {relpath}")

print("SouthWest-NG SUSFS compatibility port completed and verified.")
