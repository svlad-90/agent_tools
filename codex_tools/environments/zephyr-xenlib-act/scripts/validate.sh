#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${SCRIPT_DIR}/env.sh"

usage() {
	cat <<EOF
Usage: $(basename "$0") [repo-root] [options] [--] [act arguments...]

Build or reuse the local act runner image and run zephyr-xenlib's Build
workflow.

Options:
  --token-file PATH       File containing a GitHub token. Default:
                          ${CODEX_DEFAULT_ZEPHYR_XENLIB_TOKEN_FILE}
  --rebuild-image         Rebuild the runner image before running act.
  --target TARGET         Restrict the matrix target, for example qemu_cortex_a53.
  --project PROJECT       Restrict the matrix project, for example zephyr-dom0-xt.
  --isolated-parallel     Run each matrix entry in its own copied workspace,
                          with per-target logs under report/runtime.
  --isolated-root PATH    Directory for isolated workspaces.
  --log-dir PATH          Directory for isolated-parallel logs.
  --parallel              Run the workflow as one act invocation and let act
                          schedule matrix jobs.
  -h, --help              Show this help.

Environment:
  ACT_BIN                         Path to act binary.
  CODEX_ZEPHYR_XENLIB_ACT_IMAGE   Docker image tag.
  CODEX_DOCKER_BUILD_NETWORK      Docker build network. Defaults to host.
EOF
}

repo_root="${1:-${CODEX_DEFAULT_ZEPHYR_XENLIB_REPO}}"
if [ "$#" -gt 0 ]; then
	case "$1" in
		--token-file|--rebuild-image|--target|--project|-h|--help|--)
			repo_root="${CODEX_DEFAULT_ZEPHYR_XENLIB_REPO}"
			;;
		*)
			shift
			;;
	esac
fi

token_file="${CODEX_DEFAULT_ZEPHYR_XENLIB_TOKEN_FILE}"
rebuild_image=0
parallel=0
isolated_parallel=0
isolated_root=""
log_dir=""
target_filter=""
project_filter=""

while [ "$#" -gt 0 ]; do
	case "$1" in
		--token-file)
			token_file="${2:?missing value for --token-file}"
			shift 2
			;;
		--rebuild-image)
			rebuild_image=1
			shift
			;;
		--target)
			target_filter="${2:?missing value for --target}"
			shift 2
			;;
		--project)
			project_filter="${2:?missing value for --project}"
			shift 2
			;;
		--isolated-parallel)
			isolated_parallel=1
			shift
			;;
		--isolated-root)
			isolated_root="${2:?missing value for --isolated-root}"
			shift 2
			;;
		--log-dir)
			log_dir="${2:?missing value for --log-dir}"
			shift 2
			;;
		--parallel)
			parallel=1
			shift
			;;
		-h|--help)
			usage
			exit 0
			;;
		--)
			shift
			break
			;;
		*)
			break
			;;
	esac
done

if [ ! -d "${repo_root}" ]; then
	echo "zephyr-xenlib checkout does not exist: ${repo_root}" >&2
	exit 1
fi
repo_root="$(cd "${repo_root}" && pwd)"

if [ ! -s "${token_file}" ]; then
	echo "missing or empty token file: ${token_file}" >&2
	exit 1
fi

act_bin="${ACT_BIN:-}"
if [ -z "${act_bin}" ]; then
	if command -v act >/dev/null 2>&1; then
		act_bin=act
	elif [ -x "${CODEX_WORKSPACE_ROOT}/zephyr-xenlib-builders/tools/act" ]; then
		act_bin="${CODEX_WORKSPACE_ROOT}/zephyr-xenlib-builders/tools/act"
	elif [ -x /tmp/act-bin/act ]; then
		act_bin=/tmp/act-bin/act
	else
		echo "error: act is not installed; set ACT_BIN or put act in PATH" >&2
		exit 1
	fi
fi

if [ "${rebuild_image}" -eq 1 ] || ! docker image inspect "${CODEX_ZEPHYR_XENLIB_ACT_IMAGE}" >/dev/null 2>&1; then
	"${SCRIPT_DIR}/build.sh"
fi

targets=(
	rcar_spider_ca55
	rcar_salvator_xs_m3
	rcar_h3ulcb_ca57
	qemu_cortex_a53
)

if [ -n "${target_filter}" ]; then
	targets=("${target_filter}")
fi

project="${project_filter:-zephyr-dom0-xt}"
if [ "${project}" != "zephyr-dom0-xt" ]; then
	echo "project ${project} is excluded by the workflow matrix; nothing to run" >&2
	exit 1
fi

secret_file="$(mktemp)"
chmod 600 "${secret_file}"
trap 'rm -f "${secret_file}"' EXIT
printf 'GITHUB_TOKEN=%s\n' "$(tr -d '\r\n' < "${token_file}")" >"${secret_file}"

cd "${repo_root}"

run_act() {
	"${act_bin}" push -j build --pull=false --rm \
		--secret-file "${secret_file}" \
		-P "ubuntu-22.04=${CODEX_ZEPHYR_XENLIB_ACT_IMAGE}" \
		"$@"
}

prepare_isolated_workspace() {
	local target="$1"
	local target_root="${isolated_root}/${target}"
	local target_repo="${target_root}/zephyr-xenlib"
	local target_job="build_${target}"

	mkdir -p "${target_root}"
	rsync -a --delete \
		--exclude '.west' \
		--exclude 'build' \
		--exclude 'sdk' \
		--exclude 'zephyr-dom0-xt' \
		--exclude 'zephyr-xenlib' \
		--exclude 'zephyr-xrun' \
		"${repo_root}/" "${target_repo}/"
	sed -i "s/^  build:/  ${target_job}:/" \
		"${target_repo}/.github/workflows/build.yaml"

	printf '%s\n' "${target_repo}"
}

if [ "${isolated_parallel}" -eq 1 ]; then
	if ! command -v rsync >/dev/null 2>&1; then
		echo "error: rsync is required for --isolated-parallel" >&2
		exit 1
	fi

	task_root="$(cd "${repo_root}/../.." && pwd)"
	isolated_root="${isolated_root:-${task_root}/dev/act-isolated}"
	log_dir="${log_dir:-${task_root}/report/runtime}"
	mkdir -p "${isolated_root}" "${log_dir}"

	pids=()
	pid_targets=()
	for target in "${targets[@]}"; do
		target_repo="$(prepare_isolated_workspace "${target}")"
		target_job="build_${target}"
		log_file="${log_dir}/act-${target}.log"
		echo "Running isolated zephyr-xenlib matrix: target=${target}, project=${project}"
		echo "  job: ${target_job}"
		echo "  workspace: ${target_repo}"
		echo "  log: ${log_file}"
		(
			cd "${target_repo}"
			"${act_bin}" push -j "${target_job}" --pull=false --rm \
				--secret-file "${secret_file}" \
				-P "ubuntu-22.04=${CODEX_ZEPHYR_XENLIB_ACT_IMAGE}" \
				--matrix "target:${target}" \
				--matrix "project:${project}" "$@"
		) >"${log_file}" 2>&1 &
		pids+=("$!")
		pid_targets+=("${target}")
	done

	status=0
	for index in "${!pids[@]}"; do
		pid="${pids[${index}]}"
		target="${pid_targets[${index}]}"
		if wait "${pid}"; then
			echo "PASS ${target}: ${log_dir}/act-${target}.log"
		else
			echo "FAIL ${target}: ${log_dir}/act-${target}.log" >&2
			status=1
		fi
	done
	exit "${status}"
fi

if [ "${parallel}" -eq 1 ]; then
	matrix_args=()
	if [ -n "${target_filter}" ]; then
		matrix_args+=(--matrix "target:${target_filter}")
	fi
	if [ -n "${project_filter}" ]; then
		matrix_args+=(--matrix "project:${project_filter}")
	fi
	run_act "${matrix_args[@]}" "$@"
	exit $?
fi

for target in "${targets[@]}"; do
	echo "Running zephyr-xenlib matrix: target=${target}, project=${project}"
	run_act --matrix "target:${target}" --matrix "project:${project}" "$@"
done
