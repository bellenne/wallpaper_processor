from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProcessingResult:
    source_path: Path
    success: bool
    output_paths: list[Path] = field(default_factory=list)
    error_message: str | None = None
