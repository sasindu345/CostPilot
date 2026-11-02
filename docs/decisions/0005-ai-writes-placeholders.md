# 0005: The AI writes placeholders, not numbers

**Status:** Accepted, 2 Nov 2026

**Situation.** Telling an AI not to invent numbers does not guarantee that it will not. Wrong money figures would destroy trust in the product.

**Decision.** Code creates facts with IDs. The AI writes `{{F1}}`, and our code fills in the real value. A checker rejects any money or percentage that is not linked to a fact. After one retry, a plain template answer is used.

**Why.** The AI never handles the numbers it displays, so errors are prevented, not just detected.

**Trade-offs.** The writing is a little less free-flowing, and answers need one extra checking step. Template answers are plainer.
