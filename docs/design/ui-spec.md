# UI specification

The target design is [overview-mockup.png](overview-mockup.png). Colours are stored in `apps/web/src/styles/tokens.css`.

## Layout

- **Sidebar** (dark green): logo, then Overview, Documents, Analytics and AI Assistant. Settings sits at the bottom. The active item has a light green gradient.
- **Top bar** (white): notifications bell and user menu.
- **Main area**: page title and date filter, then cards.
- **AI side panel**: on the right of Overview, on wide screens only.

## Overview page

| Row | Content |
|---|---|
| 1 | Four cards: Total Expenditure (highlighted), This Month, Last Month, Change |
| 2 | Monthly Cloud Spending chart; Top Services list |
| 3 | Recent Documents; AI Recommendations |

## Changes from the design image

The image is the visual target, but these details are corrected on purpose.

| In the image | What we build |
|---|---|
| "This Month" shows +8.2% in red and "Change" shows −8.2%. The real value is −8.1% ($248.60 vs $270.40) | One calculated value. A drop is not a red warning |
| "Last 6 Months" filter with 5 months on the chart | The chart always matches the filter |
| September is about $262 on the chart but "Last Month" is $270.40 | Both use the same data |
| Top Services total $203.60 of $248.60 | Add an "Other" row |
| Chart axis starts at $100 | Start at $0, so changes are not exaggerated |
| Savings like "~$32/month" | Show only provable savings; otherwise "Needs usage data" |
| AI Assistant is a side panel and a full page | Same conversation in both |
| A half-finished month against a full month | Compare the same number of days, labelled "so far" |

## States every screen needs

- **Empty:** explain what to do next, with a button
- **Loading:** a skeleton of the content
- **Error:** a plain message and a retry button

## Accessibility

- Text meets WCAG AA contrast
- Everything works with a keyboard
- Colour is never the only signal, so changes also use an arrow or a word
