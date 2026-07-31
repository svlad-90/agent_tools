#!/bin/sh
set -eu

domids="${XEN_HARNESS_CONSOLE_DOMIDS:-1}"
output="${XEN_HARNESS_CONSOLE_OUTPUT:-console}"
log_dir="${XEN_HARNESS_CONSOLE_LOG_DIR:-/run/xen-harness/console}"
xenconsole="${XEN_HARNESS_XENCONSOLE:-/usr/lib/xen/bin/xenconsole}"
backend="${XEN_HARNESS_CONSOLE_BACKEND:-auto}"
xl="${XEN_HARNESS_XL:-/usr/sbin/xl}"
oneshot="${XEN_HARNESS_CONSOLE_ONESHOT:-0}"

pids=""

printf '[xen-harness][dom0] Linux Dom0 console collector started domids=%s output=%s backend=%s\n' \
	"${domids}" "${output}" "${backend}"

cleanup() {
	for pid in ${pids}; do
		kill "${pid}" 2>/dev/null || true
	done
}

trap cleanup EXIT INT TERM

emit_line() {
	domid="$1"
	line="$2"

	case "${output}" in
	console)
		printf '[xen-harness][domu%s] %s\n' "${domid}" "${line}"
		;;
	file)
		mkdir -p "${log_dir}"
		printf '%s\n' "${line}" >> "${log_dir}/domu${domid}.log"
		;;
	*)
		printf '[xen-harness][dom0] unsupported console output: %s\n' "${output}" >&2
		return 1
		;;
	esac
}

collect_one() {
	domid="$1"

	while true; do
		"${xenconsole}" "${domid}" 2>&1 | while IFS= read -r line; do
			case "${line}" in
			xenconsole:*)
				printf '[xen-harness][dom0] xenconsole dom%u: %s\n' \
					"${domid}" "${line}" >&2
				;;
			*)
				emit_line "${domid}" "${line}"
				;;
			esac
		done
		sleep 1
	done
}

emit_xen_dmesg_line() {
	line="$1"

	for domid in ${domids}; do
		prefix="(XEN) DOM${domid}: "
		case "${line}" in
		"${prefix}"*)
			emit_line "${domid}" "${line#"${prefix}"}"
			return 0
			;;
		esac
	done
}

collect_xen_dmesg() {
	"${xl}" dmesg 2>&1 | while IFS= read -r line; do
		emit_xen_dmesg_line "${line}"
	done

	if [ "${oneshot}" = "1" ]; then
		return 0
	fi

	"${xl}" dmesg -f 2>&1 | while IFS= read -r line; do
		emit_xen_dmesg_line "${line}"
	done
}

case "${backend}" in
auto|xenconsole)
	for domid in ${domids}; do
		collect_one "${domid}" &
		pids="${pids} $!"
	done
	;;
xen-dmesg)
	collect_xen_dmesg &
	pids="${pids} $!"
	;;
*)
	printf '[xen-harness][dom0] unsupported console backend: %s\n' "${backend}" >&2
	exit 1
	;;
esac

if [ "${backend}" = "auto" ]; then
	collect_xen_dmesg &
	pids="${pids} $!"
fi

wait
