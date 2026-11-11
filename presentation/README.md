# McFate 1926 Journey Presentation

`mcfate-1926-journey.pptx` is an editable widescreen presentation that opens in
Keynote and can be imported into Google Slides without a PowerPoint license.
The current deck has 98 slides: a Veterans Day splash slide, three opening slides, 62 diary-summary slides
covering all 41 dated entries, all 15 Rootstalk journal pullquotes, five
separately labeled foreword excerpts, ten illustrated
slides, and matching information-source slides immediately after the cover
and at the very end. There is no audience note-taking slide.
Both source slides briefly describe
the full-journal website and the abridged Rootstalk article, with clickable links.
Both also show the requested contact sentence beneath the sources, centered
horizontally.

The illustrated edition was also uploaded as a separate
[Google Slides deck](https://docs.google.com/presentation/d/1WAjGrFXx17NM6UXau86mzpvkqQ3tt1GF1RyYPK55ppM/edit),
leaving the earlier deck unchanged. This cloud copy does not automatically
refresh when the local deck is rebuilt. This is the corrected 22-point edition
with all 15 journal pullquotes, centered footer links, day-specific Rootstalk
links, captioned photographs and maps,
and information-source slides at positions 3 and 98.

The opening splash uses editable red, white, and blue shapes and stars to thank
veterans for their service. Centered birthday wishes appear at the bottom,
including the presenter's requested recognition of Ron's Navy service.
Editable U.S. flags flank the heading, and colorful balloon clusters frame the
birthday message without covering the text.
The original journey cover follows this splash; all later slides retain their
relative order.

## Rootstalk pullquotes

`pullquotes.json` preserves all 15 rendered `div.pullquote` entries in article
order. These are Miriam's direct words, not editorial summaries. Each receives
its own slide, with the first quote immediately before the corresponding day's
first summary and additional quotes interleaved with that day's summaries.
Each has a link to the
article section where it appears. The three quotes in the November 5-23
overview follow their explicitly cited dates: November 11, 16, and 21.
The original date lines, spelling, and punctuation are retained, including
the mismatched quotation marks in the November 16 road sign.
Only HTML formatting whitespace is normalized.

The five pre-existing excerpts from Mark's foreword remain separately labeled
**Foreword excerpt**, rather than being mistaken for the article's pullquotes.
Their positions remain unchanged. Multiple pullquotes for one day keep their
article order, alternating quote then daily summary where possible. If there
are more quotes than summaries, the remaining quotes follow that day's last
summary rather than being assigned to another date.
Both types are reproduced verbatim and attributed to their respective authors.
Footer links share one horizontally centered line. When two links are present,
they are separated by ` · `; only the labels are clickable, not the separator.
Single links are centered too, including on quote and illustration slides.

## Photographs, maps, and captions

The illustrated slides include all seven historical family photographs in
the Rootstalk article, its representative period camper image, its highlighted
1926 highway map, and the repository's 1927 Sheridan Township parcel map.
The article's decorative header and author portraits are not included.

Each illustration has a complete, editable published caption, a separate
editorial annotation, source and full-size-image links, and credit/provenance
in the speaker notes. The original image files are embedded without cropping
or retouching, preserving borders and marks such as the Mississippi photograph's
hand-drawn arrow. Tentative dates, locations, and identifications remain
explicitly tentative. The camper illustration is **not** the McFate party.

Rootstalk endnote 1 explains that Debra supplied the family photographs in 2025;
Mark believes Mildred took most of them and added many handwritten verso captions
after the 1991 transcription. This is recorded as qualified provenance, not a
confirmed photographer/caption-author attribution for every picture.

The family photos appear alongside the relevant park, river, puppy, and Texas
entries. The undated group photo is in the family introduction to avoid assigning
it a false date. The two maps follow the route overview. The small township scan
has limited original resolution; its highlighted parcel is a possible starting
point, not a verified departure location.

`illustrations.json` records captions, annotations, placement, credits, and
original image URLs. Downloaded article figures are retained in `images/`;
the township map remains in `../objects/`. Rebuilds use these local assets
and do not need to download the images again.

Daily slides use a nearly full-width, 22-point primary text area instead of
the former clipped opening excerpt and statistics sidebar. Human-edited
summaries emphasize experiences, humor, family life, encounters, and memorable
sights. Richer entries span two or three themed slides with part numbers.
They are explicitly labeled as summaries, not quotations.
Diary paragraphs use 1.05 line spacing and 12-point gaps, with no trailing
paragraph gap. Font-fit tests reserve an additional 0.4 inches of vertical
space to accommodate Google Slides import differences.

The deck uses the dated trip data in `_data/McFate-Travel-Diary-Trip-Data.csv`
for its date, day number, locations, and mileage. Each day's speaker notes
retain the corresponding transcript from `objects/markdown/` and its source
path, including on continuation slides. Every daily slide has an underlined,
clickable link to that day's item page at <https://1926.mcfate.family>.
For October 18 through November 5 and November 24 through 27, a second
link on the same line opens the corresponding dated section in Rootstalk.
The intervening days are omitted from that abridged edition, so their slides
have no Rootstalk link. November 25 uses the article's Thanksgiving heading.
Destinations come from the collection metadata's date and object ID, rather
than guessing a URL from a transcript filename. Quote slides also have a
visible link to the Rootstalk article.
Miriam's final entry reports 2,809 miles, while the reconstructed route CSV
totals 2,574.6 miles; the presentation identifies these as separate source
figures rather than silently reconciling them.

## Rebuild

From the repository root:

```sh
python3 -m pip install -r presentation/requirements.txt
python3 presentation/build_presentation.py
```

The output is written to `presentation/mcfate-1926-journey.pptx`.

## Future additions and edits

- Edit `diary_highlights.json` to change a day's wording or add a continuation
  page. Each day contains an ordered list of pages, each with a `title` and
  one to three `highlights` paragraphs.
- Keep each page to at most 115 words and each title to at most 65 characters.
  Split longer material into another themed page; the builder rejects
  over-budget pages instead of silently cutting off text. Recheck layout
  after editing, especially if changing fonts.
- Summarize from the matching transcript in `../objects/markdown/`. Retain
  attribution and avoid presenting a paraphrase as Miriam's exact words.
- Change `build_presentation.py` for layout or other slide types, then rebuild.
  No online AI service or Microsoft account is needed to run the builder.
- In future prompts, identify the day, date, or slide title you want changed.
  The editable summaries and generator preserve those changes on rebuild.
- Edit `illustrations.json` to adjust image placement or editorial annotations.
  Keep published captions distinct from new commentary and preserve uncertainty.
- Keep `pullquotes.json` synchronized with every `div.pullquote` in the article,
  preserving article order, verbatim wording, date lines, and source anchors.
  Do not summarize or silently correct direct quotations.

Check the generated deck with:

```sh
python3 -m unittest discover -s presentation -p 'test_*.py' -v
```

Tests check all days and continuation pages, full speaker-note transcripts,
saved hyperlinks, slide bounds, and invalid summary inputs. On macOS they
also measure daily text wrapping against the installed Arial and Georgia
fonts, including illustration captions. Tests also check image bytes, aspect
ratios, zero cropping, caption/annotation preservation, placement, and removal
of the former note-taking slide. This is a layout check, not a guarantee of
identical Google Slides rendering.
Tests also verify all 15 pullquotes survive unchanged, alternate with the correct
day's summaries where possible, retain section links, and remain distinct from the five foreword
excerpts, whose positions are unchanged.
Footer checks verify a single centered paragraph, an unlinked dot separator
when needed, independently clickable labels, and sufficient width for one line.

## Google Slides and source-page navigation

1. Upload the rebuilt `.pptx` to your signed-in Google Drive.
2. Open it with Google Slides. To make a native Slides copy, choose
   **File > Save as Google Slides**.
3. Check text, speaker notes, and links after import. A rebuilt local file
   does **not** automatically update a previously imported Google Slides deck;
   import the new file to use these revisions. Edits made only in Slides do
   not flow back into the generator.
4. In slideshow mode, click **Open this day's full journal on the source
   website**. External links normally open another browser tab; switch back
   to the slideshow tab to continue from the same slide.
5. Rehearse this on the presenting Mac. Browser full-screen behavior can vary;
   presenting in a regular browser window makes tab switching simpler.
   The source website requires an internet connection.

## Source note to resolve

The route CSV dates day 33 as Friday, November 19, 1926. The matching
transcription file `objects/markdown/033-fri-nov-20-1926.md` is headed
"Fri, Nov 20, 1926," while the next file is headed Saturday, November 20.
The deck follows the route CSV for the slide date and marks this discrepancy
in the November 19 slide notes for verification against the primary journal.
