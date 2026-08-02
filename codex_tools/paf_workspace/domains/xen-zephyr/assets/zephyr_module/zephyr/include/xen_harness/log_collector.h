/* SPDX-License-Identifier: Apache-2.0 */

#ifndef XEN_HARNESS_LOG_COLLECTOR_H_
#define XEN_HARNESS_LOG_COLLECTOR_H_

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef uint16_t xen_harness_domid_t;

struct xen_harness_console_sink {
	int (*write_line)(xen_harness_domid_t domid, const char *line, size_t len,
			  void *user_data);
	void *user_data;
};

/*
 * Start the Dom0-side Xen console collector.
 *
 * By default the collector writes domain-tagged records to the Dom0 console so
 * the host harness can split them into per-domain sources. Products with a
 * separate host-visible transport may install another sink before starting the
 * collector. It is safe to call this more than once; repeated calls return
 * success after the first start.
 */
int xen_harness_log_collector_start(void);

/*
 * Replace the collector output sink.
 *
 * Must be called before xen_harness_log_collector_start(). Passing NULL
 * restores the default Dom0 printk sink.
 */
int xen_harness_log_collector_set_sink(const struct xen_harness_console_sink *sink);

#ifdef __cplusplus
}
#endif

#endif /* XEN_HARNESS_LOG_COLLECTOR_H_ */
