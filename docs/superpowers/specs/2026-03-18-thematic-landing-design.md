# Thematic Landing Page — Design Spec

## Problem

The current landing page shows changes chapter-by-chapter, which mirrors the textbook structure but obscures the patterns. Readers can't easily see that the same kinds of content were targeted across multiple chapters.

## Solution

Add a tabbed landing page with "By Theme" (default) and "By Chapter" views. The thematic view organizes changes into four categories with prose introductions and highlighted example cards.

## Components

### 1. Tab Bar

Two tabs below the hero section (title, subtitle, PDF links, stats). Clicking toggles visibility of the theme view vs. the chapter grid. No page reload. Stats remain visible in both views. Default is "By Theme."

### 2. Theme Sections

Four sections, each containing:

**Title** — displayed as an h2-level heading.

**Prose introduction** — 1-2 paragraphs framing the pattern. Written with the prose-craft skill. Stored in `data/themes.json`.

**Eliminated chapters callout** — where relevant, a highlighted note listing entire chapters that were removed (e.g., "Entire chapters eliminated: Race & Ethnicity (Ch. 11), Gender, Sex, and Sexuality (Ch. 12)").

**3-4 example cards** — each showing:
- Chapter and section label (e.g., "Chapter 7, Section 7.3")
- Description text (~1-3 sentences from the change's `context` field, possibly edited for the landing page)
- "See in context →" link navigating to `#chapter-N` with the relevant change scrolled into view

### 3. The Four Themes

**Race & Racism**
- Eliminated: Ch. 11 (Race and Ethnicity)
- Examples: Eric Garner/Floyd/Taylor names scrubbed (ch07/13), environmental racism section deleted (ch20/16), anti-Mexican marijuana history removed (ch07/3), racial profiling language hedged (ch07/12)

**Gender & Sexuality**
- Eliminated: Ch. 12 (Gender, Sex, and Sexuality)
- Examples: Noel's they/them pronouns replaced with she/her (ch05/0), LGBTQ seniors sidebar removed (ch13/24), same-sex parenting research deleted (ch14/1), LGBTQ criminalization history removed (ch07/4)

**Economic Inequality**
- Eliminated: Ch. 9 (Social Stratification), Ch. 10 (Global Inequality)
- Examples: minimum wage sidebar deleted (ch01/10), CEO pay statistics removed (ch21/3), "faults with the free enterprise system" softened (ch01/7), feminization of aging poor removed (ch13/15)

**Political Content & Critical Theory**
- Examples: critical theory/CRT/feminist theory deleted (ch01/11), Biden minimum wage reference removed (ch01/10), judicial system section deleted (ch15/4), public sociology concept erased (ch01/12), Sociological Theory Today rewritten (ch01/12)

### 4. Data Format (`data/themes.json`)

```json
{
  "themes": [
    {
      "id": "race",
      "title": "Race & Racism",
      "prose": "Paragraph 1.\n\nParagraph 2.",
      "eliminated_chapters": [11],
      "examples": [
        {
          "chapter": 7,
          "change_index": 13,
          "description": "The passage naming Eric Garner, Breonna Taylor, and George Floyd..."
        }
      ]
    }
  ]
}
```

The `prose` field will be written using the prose-craft skill. The `description` may be taken directly from the change's `context` field or edited for the landing page.

### 5. Frontend Changes

**`index.html`** — add tab bar markup after the stats div, add theme view container.

**`js/app.js`** — load `themes.json`, render theme sections, handle tab switching. Tab state is not URL-driven (no hash change). Link clicks in example cards navigate to `#chapter-N` which triggers the existing routing.

**`css/style.css`** — tab bar styles, theme section styles, example card styles, eliminated-chapter callout styles.

## What This Does NOT Include

- Auto-categorization of changes by theme (future work — requires tagging each change)
- Filtering within chapter views by theme
- URL-driven tab state
