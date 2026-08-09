/* SPDX-License-Identifier: Apache-2.0 */

#include <errno.h>

#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/util.h>
#include <zephyr/xen/generic.h>

#include <domain.h>
#include <xen_console.h>

#include <xen_harness/log_collector.h>

#ifndef CONFIG_XEN_HARNESS_DOMU_CONSOLE_MAX_DOMAINS
#define CONFIG_XEN_HARNESS_DOMU_CONSOLE_MAX_DOMAINS 8
#endif

#define DOMU_FIRST_DOMID 1
#define DOMU_MAX_DOMID CONFIG_XEN_HARNESS_DOMU_CONSOLE_MAX_DOMAINS
#define DOMU_COUNT (DOMU_MAX_DOMID - DOMU_FIRST_DOMID + 1)
#define LOG_LINE_BUFFER_SIZE 256

BUILD_ASSERT(DOMU_MAX_DOMID >= DOMU_FIRST_DOMID);

struct domu_console {
	domid_t domid;
	struct xencons_interface *intf;
	char line[LOG_LINE_BUFFER_SIZE];
	size_t line_len;
	bool attached;
};

static K_THREAD_STACK_DEFINE(collector_stack,
			     CONFIG_XEN_HARNESS_DOMU_CONSOLE_STACK_SIZE);
static struct k_thread collector_thread;
static struct xen_harness_console_sink active_sink;
static bool collector_started;
static struct domu_console domu_consoles[DOMU_COUNT];

static int printk_sink_write_line(xen_harness_domid_t domid, const char *line,
				  size_t len, void *user_data)
{
	ARG_UNUSED(user_data);

	printk("[xen-harness][domu%u] %.*s\n", domid, (int)len, line);
	return 0;
}

static void ensure_default_sink(void)
{
	if (active_sink.write_line == NULL) {
		active_sink.write_line = printk_sink_write_line;
	}
}

static struct domu_console *domu_console_for_id(domid_t domid)
{
	if (domid < DOMU_FIRST_DOMID || domid > DOMU_MAX_DOMID) {
		return NULL;
	}

	return &domu_consoles[domid - DOMU_FIRST_DOMID];
}

static void flush_line(struct domu_console *console)
{
	if (console->line_len == 0) {
		return;
	}

	console->line[console->line_len] = '\0';
	ensure_default_sink();
	(void)active_sink.write_line((xen_harness_domid_t)console->domid,
				     console->line, console->line_len,
				     active_sink.user_data);
	console->line_len = 0;
}

static void append_char(struct domu_console *console, char ch)
{
	if (ch == '\r') {
		return;
	}

	if (ch == '\n') {
		flush_line(console);
		return;
	}

	if (console->line_len == (sizeof(console->line) - 1)) {
		flush_line(console);
	}

	console->line[console->line_len++] = ch;
}

static void console_feed_cb(char ch, void *cb_data)
{
	struct domu_console *console = cb_data;

	append_char(console, ch);
}

static void attach_console(domid_t domid)
{
	struct domu_console *console = domu_console_for_id(domid);
	struct xen_domain *domain;
	int ret;

	if (console == NULL || console->attached) {
		return;
	}

	domain = get_domain(domid);
	if (domain == NULL) {
		return;
	}

	if (domain->console.ext_tid == NULL) {
		put_domain(domain);
		return;
	}

	console->domid = domid;
	if (domain->f_dom0less) {
		put_domain(domain);
		return;
	}

	ret = set_console_feed_cb(domain, console_feed_cb, console);
	if (ret < 0) {
		printk("[xen-harness][dom0] failed to attach DomU%u console: %d\n",
		       domid, ret);
		put_domain(domain);
		return;
	}

	console->attached = true;
	printk("[xen-harness][dom0] attached DomU%u console\n", domid);
	put_domain(domain);
}

void domain_pre_unpause(struct xen_domain *domain)
{
	struct domu_console *console;
	int ret;

	if (!collector_started || domain == NULL || domain->f_dom0less) {
		return;
	}

	console = domu_console_for_id(domain->domid);
	if (console == NULL || console->attached ||
	    domain->console.ext_tid == NULL) {
		return;
	}

	console->domid = domain->domid;
	ret = set_console_feed_cb(domain, console_feed_cb, console);
	if (ret < 0) {
		printk("[xen-harness][dom0] failed to attach DomU%u console: %d\n",
		       domain->domid, ret);
		return;
	}

	console->attached = true;
	printk("[xen-harness][dom0] attached DomU%u console before unpause\n",
	       domain->domid);
}

static void collector_main(void *arg1, void *arg2, void *arg3)
{
	ARG_UNUSED(arg1);
	ARG_UNUSED(arg2);
	ARG_UNUSED(arg3);

	printk("[xen-harness][dom0] DomU console collector started\n");

	while (true) {
		for (domid_t domid = DOMU_FIRST_DOMID; domid <= DOMU_MAX_DOMID; domid++) {
			attach_console(domid);
		}

		k_msleep(CONFIG_XEN_HARNESS_DOMU_CONSOLE_SCAN_INTERVAL_MS);
	}
}

int xen_harness_log_collector_start(void)
{
	if (collector_started) {
		return 0;
	}

	ensure_default_sink();
	collector_started = true;
	k_thread_create(&collector_thread, collector_stack,
			K_THREAD_STACK_SIZEOF(collector_stack), collector_main,
			NULL, NULL, NULL,
			CONFIG_XEN_HARNESS_DOMU_CONSOLE_PRIORITY, 0, K_NO_WAIT);
	k_thread_name_set(&collector_thread, "xen-log-collector");

	return 0;
}

int xen_harness_log_collector_set_sink(const struct xen_harness_console_sink *sink)
{
	if (collector_started) {
		return -EALREADY;
	}

	if (sink == NULL) {
		active_sink.write_line = printk_sink_write_line;
		active_sink.user_data = NULL;
		return 0;
	}

	if (sink->write_line == NULL) {
		return -EINVAL;
	}

	active_sink = *sink;
	return 0;
}

#if defined(CONFIG_XEN_HARNESS_DOMU_CONSOLE_COLLECTOR_AUTOSTART)
SYS_INIT(xen_harness_log_collector_start, APPLICATION,
	 CONFIG_APPLICATION_INIT_PRIORITY);
#endif
