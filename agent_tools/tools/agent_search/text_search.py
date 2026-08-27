from __future__ import annotations

from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
import time
from typing import Iterable

import regex

from .common import TEXT_BYTES_LIMIT, compile_query, normalized_threads
from .discovery import iter_candidate_files
from .models import AgentSearchError, RangeSnippet, TextMatch, TextSearchReport


def text_search(
    *,
    root: Path,
    query: str,
    fixed: bool = False,
    case_sensitive: bool = False,
    ignore_case: bool = False,
    include: Iterable[str] = (),
    exclude: Iterable[str] = (),
    hidden: bool = False,
    use_gitignore: bool = True,
    threads: int | None = None,
    max_matches_scanned: int = 10_000,
    max_file_bytes: int = TEXT_BYTES_LIMIT,
    before: int = 5,
    after: int = 5,
    max_ranges: int = 20,
    max_lines: int = 300,
) -> TextSearchReport:
    if not root.exists():
        raise AgentSearchError(f"root does not exist: {root}")
    root = root.resolve()
    compiled = compile_query(query, fixed=fixed, case_sensitive=case_sensitive, ignore_case=ignore_case)
    start = time.perf_counter()
    matches: list[TextMatch] = []
    skipped = 0
    scanned = 0
    truncated = False
    worker_count = normalized_threads(threads)
    candidate_files = iter_candidate_files(
        root,
        include=include,
        exclude=exclude,
        hidden=hidden,
        use_gitignore=use_gitignore,
    )
    max_pending = max(worker_count * 4, worker_count)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        pending: set[Future[tuple[list[TextMatch], bool]]] = set()
        file_iter = iter(candidate_files)
        exhausted = False
        while pending or not exhausted:
            while not exhausted and len(pending) < max_pending:
                try:
                    path = next(file_iter)
                except StopIteration:
                    exhausted = True
                    break
                scanned += 1
                pending.add(executor.submit(search_text_file, path, compiled, max_file_bytes))
            if not pending:
                continue
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                file_matches, file_skipped = future.result()
                skipped += int(file_skipped)
                if not file_matches:
                    continue
                remaining = max_matches_scanned - len(matches)
                if remaining <= 0:
                    truncated = True
                    exhausted = True
                    pending.clear()
                    break
                matches.extend(file_matches[:remaining])
                if len(file_matches) > remaining:
                    truncated = True
                    exhausted = True
                    pending.clear()
                    break
    if not truncated:
        scanned += sum(1 for _path in file_iter)
    if len(matches) >= max_matches_scanned:
        truncated = True
    matches.sort(key=lambda item: (str(item.path), item.line, item.column))
    ranges = build_ranges(matches, before=before, after=after, max_ranges=max_ranges, max_lines=max_lines)
    return TextSearchReport(
        root=root,
        query=query,
        elapsed_seconds=time.perf_counter() - start,
        files_scanned=scanned,
        files_skipped=skipped,
        matches=tuple(matches),
        ranges=tuple(ranges),
        truncated=truncated,
    )


def search_text_file(path: Path, compiled: regex.Pattern[str], max_file_bytes: int) -> tuple[list[TextMatch], bool]:
    try:
        if path.stat().st_size > max_file_bytes:
            return [], True
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return [], True
    if "\0" in text[:4096]:
        return [], True
    result: list[TextMatch] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in compiled.finditer(line):
            result.append(
                TextMatch(
                    path=path,
                    line=line_no,
                    column=match.start() + 1,
                    text=line,
                    groups={name: values for name, values in match.capturesdict().items() if values},
                )
            )
    return result, False


def build_ranges(
    matches: list[TextMatch],
    *,
    before: int,
    after: int,
    max_ranges: int,
    max_lines: int,
) -> list[RangeSnippet]:
    by_file: dict[Path, list[TextMatch]] = defaultdict(list)
    for match in matches:
        by_file[match.path].append(match)
    snippets: list[RangeSnippet] = []
    total_lines = 0
    for path in sorted(by_file):
        try:
            file_lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        windows: list[tuple[int, int, list[int]]] = []
        for match in by_file[path]:
            start = max(1, match.line - before)
            end = min(len(file_lines), match.line + after)
            if windows and start <= windows[-1][1] + 1:
                old_start, old_end, old_matches = windows[-1]
                windows[-1] = (old_start, max(old_end, end), [*old_matches, match.line])
            else:
                windows.append((start, end, [match.line]))
        for start, end, match_lines in windows:
            if len(snippets) >= max_ranges or total_lines >= max_lines:
                return snippets
            selected = tuple((idx, file_lines[idx - 1]) for idx in range(start, end + 1))
            total_lines += len(selected)
            snippets.append(RangeSnippet(path=path, start=start, end=end, match_lines=tuple(match_lines), lines=selected))
    return snippets
