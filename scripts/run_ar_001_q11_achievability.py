from pathlib import Path

from src.analysis.q11_achievability import COMPONENT_ROOT, write_outputs


def main() -> None:
    output_dir = (
        COMPONENT_ROOT
        / "artifacts"
        / "ar_001"
    )
    result = write_outputs(Path(output_dir))
    print(
        f"{result['status']}: "
        f"{result['exact_optimum']['serialized_chars']} chars"
    )


if __name__ == "__main__":
    main()
