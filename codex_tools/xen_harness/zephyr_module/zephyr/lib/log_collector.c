/* SPDX-License-Identifier: Apache-2.0 */

#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

#include <xen_harness/log_collector.h>

static K_THREAD_STACK_DEFINE(collector_stack,
			     CONFIG_XEN_HARNESS_DOMU_CONSOLE_STACK_SIZE);
static struct k_thread collector_thread;
static bool collector_started;

static void collector_main(void *arg1, void *arg2, void *arg3)
{
	ARG_UNUSED(arg1);
	ARG_UNUSED(arg2);
	ARG_UNUSED(arg3);

	printk("[xen-harness][dom0] DomU console collector started\n");

	while (true) {
		/*
		 * TODO: Drain DomU xencons_interface rings here. This module is
		 * intentionally workspace-local so the implementation can use
		 * Dom0-only Xen control ABI without touching upstream samples.
		 */
		k_msleep(CONFIG_XEN_HARNESS_DOMU_CONSOLE_SCAN_INTERVAL_MS);
	}
}

int xen_harness_log_collector_start(void)
{
	if (collector_started) {
		return 0;
	}

	collector_started = true;
	k_thread_create(&collector_thread, collector_stack,
			K_THREAD_STACK_SIZEOF(collector_stack), collector_main,
			NULL, NULL, NULL,
			CONFIG_XEN_HARNESS_DOMU_CONSOLE_PRIORITY, 0, K_NO_WAIT);
	k_thread_name_set(&collector_thread, "xen-log-collector");

	return 0;
}

SYS_INIT(xen_harness_log_collector_start, APPLICATION,
	 CONFIG_APPLICATION_INIT_PRIORITY);
