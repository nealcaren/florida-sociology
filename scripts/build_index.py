"""Build chapters.json master index from per-chapter JSON files.

Reads all ch*.json and ch*_removed.json files from data/ and builds
the master index. Files may use Florida chapter numbering or original
chapter numbering — the script reads the 'chapter' field from each.
"""

import json
from pathlib import Path


def main():
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"

    chapters = []
    total_changes = 0
    seen_chapters = set()

    # Read all chapter JSON files (both comparison and removed)
    for path in sorted(data_dir.glob("ch*.json")):
        if path.name == "chapters.json":
            continue

        with open(path) as f:
            ch = json.load(f)

        chapter_num = ch["chapter"]

        # Skip duplicates (prefer _removed files over old sample data)
        if chapter_num in seen_chapters:
            # If this is a _removed file, replace the existing entry
            if "_removed" in path.name:
                chapters = [c for c in chapters if c["chapter"] != chapter_num]
                total_changes -= sum(
                    c["change_count"] for c in [c for c in chapters if c["chapter"] == chapter_num]
                )
            else:
                continue

        seen_chapters.add(chapter_num)
        change_count = ch.get("change_count", 0)
        total_changes += change_count

        florida_title = ch.get("florida_title")
        status = "removed" if florida_title is None else "modified" if change_count > 0 else "unchanged"

        chapters.append({
            "chapter": chapter_num,
            "title": ch["title"],
            "florida_title": florida_title,
            "severity": ch.get("severity", "none"),
            "change_count": change_count,
            "status": status,
            "summary_short": ch.get("summary", "")[:200],
            "data_file": path.name,
        })

    # Sort by original chapter number
    chapters.sort(key=lambda c: c["chapter"])

    removed_count = sum(1 for c in chapters if c["status"] == "removed")
    major_count = sum(1 for c in chapters if c["severity"] == "major")

    index = {
        "title": "What Florida Changed in Your Sociology Textbook",
        "description": "A chapter-by-chapter comparison of the original OpenStax Introduction to Sociology 3e with Florida's state-modified version, highlighting every edit, deletion, and relocation.",
        "total_changes": total_changes,
        "chapters_removed": removed_count,
        "chapters_major": major_count,
        "original_chapter_count": 21,
        "florida_chapter_count": 12,
        "chapters": chapters,
    }

    out_path = data_dir / "chapters.json"
    with open(out_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"Built index: {len(chapters)} chapters, {total_changes} total changes")
    print(f"  {removed_count} chapters removed entirely")
    print(f"  {major_count} chapters with major changes")
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
