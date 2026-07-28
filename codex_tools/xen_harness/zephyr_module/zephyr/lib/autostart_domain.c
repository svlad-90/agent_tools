/* SPDX-License-Identifier: Apache-2.0 */

#include <errno.h>
#include <string.h>

#include <zephyr/kernel.h>
#include <zephyr/kernel/mm.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/util.h>
#include <zephyr/xen/dom0/domctl.h>
#include <zephyr/xen/public/arch-arm.h>
#include <zephyr/xen/public/domctl.h>
#include <zephyr/xen/public/xen.h>
#include <xen_dom_mgmt.h>

static const uint8_t *get_domu_image(void)
{
	static const uint8_t *image;

	if (image == NULL) {
		uint8_t *mapped_base;
		uintptr_t phys = XEN_HARNESS_DOMU_IMAGE_LOAD_ADDR;
		uintptr_t phys_base = ROUND_DOWN(phys, CONFIG_MMU_PAGE_SIZE);
		size_t offset = phys - phys_base;
		size_t mapped_size = ROUND_UP(offset + XEN_HARNESS_DOMU_IMAGE_SIZE,
					      CONFIG_MMU_PAGE_SIZE);

		k_mem_map_phys_bare(&mapped_base, phys_base, mapped_size,
				     K_MEM_CACHE_WB | K_MEM_PERM_RW);
		image = mapped_base + offset;
		printk("[xen-harness][dom0] mapped DomU image phys=0x%lx va=%p size=%u\n",
		       (unsigned long)phys, image, (uint32_t)XEN_HARNESS_DOMU_IMAGE_SIZE);
	}

	return image;
}

static int load_domu_image_bytes(uint8_t *buf, size_t bufsize,
				 uint64_t read_offset, void *image_info)
{
	const uint8_t *image = get_domu_image();

	ARG_UNUSED(image_info);

	if (read_offset > XEN_HARNESS_DOMU_IMAGE_SIZE ||
	    bufsize > (XEN_HARNESS_DOMU_IMAGE_SIZE - read_offset)) {
		return -EINVAL;
	}

	memcpy(buf, &image[read_offset], bufsize);
	return 0;
}

static ssize_t get_domu_image_size(void *image_info, uint64_t *size)
{
	ARG_UNUSED(image_info);

	if (size == NULL) {
		return -EINVAL;
	}

	*size = XEN_HARNESS_DOMU_IMAGE_SIZE;
	return 0;
}

static struct xen_domain_cfg harness_domu_cfg = {
	.name = CONFIG_XEN_HARNESS_DOMU_AUTOSTART_NAME,
	.domain_name = CONFIG_XEN_HARNESS_DOMU_AUTOSTART_NAME,
	.mem_kb = CONFIG_XEN_HARNESS_DOMU_AUTOSTART_MEMORY_KB,
	.flags = XEN_DOMCTL_CDF_hvm | XEN_DOMCTL_CDF_hap,
	.max_vcpus = CONFIG_XEN_HARNESS_DOMU_AUTOSTART_VCPUS,
	.max_evtchns = 1024,
	.gnt_frames = 1,
	.max_maptrack_frames = 1024,
	.ssidref = CONFIG_XEN_HARNESS_DOMU_AUTOSTART_SSIDREF,
	.gic_version = XEN_DOMCTL_CONFIG_GIC_V3,
	.cmdline = CONFIG_XEN_HARNESS_DOMU_AUTOSTART_CMDLINE,
	.load_image_bytes = load_domu_image_bytes,
	.get_image_size = get_domu_image_size,
};

static void autostart_main(void *arg1, void *arg2, void *arg3)
{
	int ret;
	uint32_t domid = CONFIG_XEN_HARNESS_DOMU_AUTOSTART_DOMID;

	ARG_UNUSED(arg1);
	ARG_UNUSED(arg2);
	ARG_UNUSED(arg3);

	k_sleep(K_MSEC(CONFIG_XEN_HARNESS_DOMU_AUTOSTART_DELAY_MS));

	if (domid == 0) {
		domid = DOMID_INVALID;
	}

	if (domid != DOMID_INVALID) {
		ret = xen_domctl_getdomaininfo(domid, &(xen_domctl_getdomaininfo_t){0});
		printk("[xen-harness][dom0] pre-create dom%u getdomaininfo=%d\n", domid, ret);
	}

	printk("[xen-harness][dom0] creating DomU from Dom0: %s domid=%u image=0x%lx size=%u flags=0x%x ssidref=%u\n",
	       harness_domu_cfg.name, domid, (unsigned long)XEN_HARNESS_DOMU_IMAGE_LOAD_ADDR,
	       (uint32_t)XEN_HARNESS_DOMU_IMAGE_SIZE, harness_domu_cfg.flags,
	       harness_domu_cfg.ssidref);

	ret = domain_create(&harness_domu_cfg, domid);
	if (ret < 0) {
		printk("[xen-harness][dom0] failed to create DomU: %d\n", ret);
		return;
	}

	printk("[xen-harness][dom0] created DomU%u from Dom0\n", ret);

	ret = domain_post_create(&harness_domu_cfg, ret);
	if (ret < 0) {
		printk("[xen-harness][dom0] DomU post-create failed: %d\n", ret);
	}
}

K_THREAD_DEFINE(xen_harness_domu_autostart,
		CONFIG_XEN_HARNESS_DOMU_CONSOLE_STACK_SIZE,
		autostart_main,
		NULL, NULL, NULL,
		CONFIG_XEN_HARNESS_DOMU_CONSOLE_PRIORITY,
		0, 0);
