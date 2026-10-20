# ollies-content

Content for the Ollie's Frozen Custard app. The app downloads these files, so changes show up
without a new app release. Every change is checked by `tools/validate.py` (it runs on GitHub
automatically) before it's merged.

| File | What it holds | Who updates it |
|---|---|---|
| `catalog.json` | Every flavor, with Year-round / Seasonal / Limited and its season | Chris, through Claude |
| `calendar/YYYY-MM.json` | The month's flavor calendar | Claude, from the monthly PDF |
| `dole.json` | Dole soft serve pairs, one per week | Claude |
| `hours.json` | Hours, copied from Ollie's Google listing daily | Automatic. Change hours on Google, not here. |
| `about.json` | The About Ollie's story, contact email, and job listing shown on the Visit screen | Chris, directly on GitHub or through Claude |
| `links.json` | Web addresses the app opens (rewards sign-up, catering form, social pages) | Chris or Claude |
| `menu.json` | The menu: sections, items, descriptions, sizes, prices, and photos | Chris, through Claude |
| `images/` | Photos the app shows (menu items now; flavors later) | Claude, from Chris's photos |

To edit `about.json` on GitHub: open the file, click the pencil icon, change the text between
the quotation marks, and commit to a new branch with a pull request. Each paragraph is one line
in quotes, separated by commas.

## Updating the menu and prices

Prices live in `menu.json`, one per size (for example a Turtle sundae has a Regular and a
Junior price). A price of `null` shows in the app as "Price coming soon".

1. Chris sends Claude the changes in any form: a list, a photo of the price board, or a new menu PDF.
2. Claude updates `menu.json` on a new branch and opens a pull request that lists every change in
   plain English (for example "Turtle sundae, Regular: price coming soon -> $6.25").
3. The automatic check runs. It catches prices that aren't plain numbers (like "$5" or 4.255),
   missing photos, and repeated or blank items and sizes.
4. Chris reads the list and merges. The app shows the new menu the next time it's opened. No app
   update or store review is needed.

New photos go in `images/menu/`, sized to about 800 pixels wide, and are named in the item's
`photos` list.
