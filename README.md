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

To edit `about.json` on GitHub: open the file, click the pencil icon, change the text between
the quotation marks, and commit to a new branch with a pull request. Each paragraph is one line
in quotes, separated by commas.
