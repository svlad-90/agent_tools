/* SPDX-License-Identifier: Apache-2.0 */

#ifndef XEN_HARNESS_LOG_COLLECTOR_H_
#define XEN_HARNESS_LOG_COLLECTOR_H_

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Start the Dom0-side Xen console collector.
 *
 * The collector prints domain-tagged records to the Dom0 console so the host
 * harness can split them into per-domain log files. It is safe to call this
 * more than once; repeated calls return success after the first start.
 */
int xen_harness_log_collector_start(void);

#ifdef __cplusplus
}
#endif

#endif /* XEN_HARNESS_LOG_COLLECTOR_H_ */
