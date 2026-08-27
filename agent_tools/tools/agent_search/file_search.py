from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from pathlib import Path
import time
from typing import Iterable

import regex

from .common import compile_query, normalize_extension, normalized_threads
from .discovery import iter_candidate_files
from .models import AgentSearchError, FileMatch, FileSearchReport


def file_search(
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
    max_files_scanned: int = 10_000,
    extensions: Iterable[str] = (),
    scope: str = "path",
) -> FileSearchReport:
    if not root.exists():
        raise AgentSearchError(f"root does not exist: {root}")
    root = root.resolve()
    compiled = compile_query(query, fixed=fixed, case_sensitive=case_sensitive, ignore_case=ignore_case)
    if scope not in {"path", "name"}:
        raise AgentSearchError(f"unsupported file search scope: {scope}")
    start = time.perf_counter()
    extension_set = {normalize_extension(ext) for ext in extensions if ext}
    matches: list[FileMatch] = []
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
        pending: set[Future[FileMatch | None]] = set()
        file_iter = iter(candidate_files)
        exhausted = False
        while pending or not exhausted:
            while not exhausted and len(pending) < max_pending and scanned < max_files_scanned:
                try:
                    path = next(file_iter)
                except StopIteration:
                    exhausted = True
                    break
                scanned += 1
                pending.add(executor.submit(match_file_path, root, path, compiled, extension_set, scope))
            if scanned >= max_files_scanned and not exhausted:
                truncated = any(True for _path in file_iter)
                exhausted = True
            if not pending:
                continue
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                match = future.result()
                if match is not None:
                    matches.append(match)
    matches.sort(key=lambda item: (-item.score, str(item.path.relative_to(root))))
    return FileSearchReport(
        root=root,
        query=query,
        elapsed_seconds=time.perf_counter() - start,
        files_scanned=scanned,
        matches=tuple(matches),
        truncated=truncated,
    )


def match_file_path(
    root: Path,
    path: Path,
    compiled: regex.Pattern[str],
    extensions: set[str],
    scope: str,
) -> FileMatch | None:
    if extensions and path.suffix.lower() not in extensions:
        return None
    rel = path.relative_to(root)
    rel_text = rel.as_posix()
    name = path.name
    score = 0
    reasons: list[str] = []
    if compiled.search(name):
        score += 5
        reasons.append("name")
    if scope == "path" and compiled.search(rel_text):
        score += 2
        reasons.append("path")
    if not reasons:
        return None
    score += max(0, 5 - len(rel.parts))
    return FileMatch(path=path, score=score, reason="+".join(reasons))
