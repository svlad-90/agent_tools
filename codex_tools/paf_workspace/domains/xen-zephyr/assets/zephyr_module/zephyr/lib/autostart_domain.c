/* SPDX-License-Identifier: Apache-2.0 */

#include <errno.h>
#include <string.h>

#include <zephyr/kernel.h>
#include <zephyr/kernel/mm.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/util.h>
#include <zephyr/xen/dom0/domctl.h>
#include <zephyr/xen/dom0/sysctl.h>
#include <zephyr/xen/hvm.h>

#if __has_include(<xen/public/arch-arm.h>)
#include <xen/public/arch-arm.h>
#include <xen/public/domctl.h>
#include <xen/public/xen.h>
#else
#include <zephyr/xen/public/arch-arm.h>
#include <zephyr/xen/public/domctl.h>
#include <zephyr/xen/public/xen.h>
#endif

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

static void probe_xen_sysctl_physinfo(void)
{
	struct xen_sysctl_physinfo physinfo = {0};
	int ret;

	ret = xen_sysctl_physinfo(&physinfo);
	printk("[xen-harness][dom0] sysctl physinfo: %s ret=%d threads=%u nr_cpus=%u\n",
	       ret == 0 ? "PASS" : "FAIL", ret, physinfo.threads_per_core,
	       physinfo.nr_cpus);
}

static void print_domain_info(uint32_t domid, const char *label)
{
	xen_domctl_getdomaininfo_t info = {0};
	int ret;

	ret = xen_domctl_getdomaininfo(domid, &info);
	if (ret) {
		printk("[xen-harness][dom0] %s dom%u getdomaininfo=%d\n",
		       label, domid, ret);
		return;
	}

	printk("[xen-harness][dom0] %s dom%u info: flags=0x%x pages=%llu max_pages=%llu online_vcpus=%u max_vcpu_id=%u gpaddr_bits=%u\n",
	       label, domid, info.flags, info.tot_pages, info.max_pages,
	       info.nr_online_vcpus, info.max_vcpu_id, info.gpaddr_bits);
}

static void print_console_params(uint32_t domid, const char *label)
{
	uint64_t console_pfn = 0;
	uint64_t console_evtchn = 0;
	int pfn_ret;
	int evtchn_ret;

	pfn_ret = hvm_get_parameter(HVM_PARAM_CONSOLE_PFN, domid, &console_pfn);
	evtchn_ret = hvm_get_parameter(HVM_PARAM_CONSOLE_EVTCHN, domid,
				       &console_evtchn);

	printk("[xen-harness][dom0] %s dom%u console params: pfn_ret=%d pfn=0x%llx evtchn_ret=%d evtchn=%llu\n",
	       label, domid, pfn_ret, console_pfn, evtchn_ret, console_evtchn);
}

static void print_vcpu_state(uint32_t domid, uint32_t vcpu, const char *label)
{
	struct xen_domctl_getvcpuinfo info = {0};
	struct vcpu_guest_context context = {0};
	int ret;

	ret = xen_domctl_getvcpu(domid, vcpu, &info);
	if (ret) {
		printk("[xen-harness][dom0] %s dom%u vcpu%u getvcpu=%d\n",
		       label, domid, vcpu, ret);
	} else {
		printk("[xen-harness][dom0] %s dom%u vcpu%u info: online=%u blocked=%u running=%u cpu_time=%llu cpu=%u\n",
		       label, domid, vcpu, info.online, info.blocked, info.running,
		       info.cpu_time, info.cpu);
	}

	ret = xen_domctl_getvcpucontext(domid, vcpu, &context);
	if (ret) {
		printk("[xen-harness][dom0] %s dom%u vcpu%u getvcpucontext=%d\n",
		       label, domid, vcpu, ret);
		return;
	}

	printk("[xen-harness][dom0] %s dom%u vcpu%u context: pc=0x%llx x0=0x%llx cpsr=0x%llx sp_el0=0x%llx sp_el1=0x%llx elr_el1=0x%llx\n",
	       label, domid, vcpu, context.user_regs.pc64, context.user_regs.x0,
	       context.user_regs.cpsr, context.user_regs.sp_el0,
	       context.user_regs.sp_el1, context.user_regs.elr_el1);
}

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

	probe_xen_sysctl_physinfo();

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
	print_domain_info(ret, "post-create");
	print_console_params(ret, "post-create");
	print_vcpu_state(ret, 0, "post-create");

	k_sleep(K_MSEC(1000));
	print_domain_info(ret, "post-create+1s");
	print_console_params(ret, "post-create+1s");
	print_vcpu_state(ret, 0, "post-create+1s");

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
