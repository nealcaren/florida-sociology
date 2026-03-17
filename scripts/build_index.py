"""Build chapters.json master index from per-chapter JSON files."""

import json
from pathlib import Path


def main():
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"

    chapters = []
    total_changes = 0

    for i in range(1, 22):
        path = data_dir / f"ch{i:02d}.json"
        if not path.exists():
            print(f"  WARNING: {path.name} not found, skipping")
            continue

        with open(path) as f:
            ch = json.load(f)

        total_changes += ch.get("change_count", 0)
        chapters.append({
            "chapter": ch["chapter"],
            "title": ch["title"],
            "severity": ch.get("severity", "none"),
            "change_count": ch.get("change_count", 0),
            "summary_short": ch.get("summary", "")[:200],
        })

    index = {
        "title": "What Florida Changed in Your Sociology Textbook",
        "description": "A chapter-by-chapter comparison of the original OpenStax Introduction to Sociology 3e with Florida's state-modified version, highlighting every edit, deletion, and relocation.",
        "total_changes": total_changes,
        "chapters": chapters,
    }

    out_path = data_dir / "chapters.json"
    with open(out_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"Built index: {len(chapters)} chapters, {total_changes} total changes")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
