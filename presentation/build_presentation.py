#!/usr/bin/env python3
"""Build an editable 1926 McFate journey presentation from repository sources."""

from __future__ import annotations

import csv
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "presentation" / "mcfate-1926-journey.pptx"
DIARY_DIR = ROOT / "objects" / "markdown"
TRIP_DATA = ROOT / "_data" / "McFate-Travel-Diary-Trip-Data.csv"
METADATA = ROOT / "_data" / "McFate-Travel-Diary-Export.csv"
HIGHLIGHTS = ROOT / "presentation" / "diary_highlights.json"
ILLUSTRATIONS = ROOT / "presentation" / "illustrations.json"
PULLQUOTES = ROOT / "presentation" / "pullquotes.json"
SITE_URL = "https://1926.mcfate.family"
ROOTSTALK_URL = "https://rootstalk.grinnell.edu/issues/volume-xi-issue-1/mcfate/"

SLIDE_W = 13.333
SLIDE_H = 7.5
PAPER = RGBColor(246, 242, 232)
INK = RGBColor(31, 47, 44)
GREEN = RGBColor(66, 94, 82)
GOLD = RGBColor(180, 119, 54)
RUST = RGBColor(154, 82, 54)
MUTED = RGBColor(105, 108, 99)
CARD = RGBColor(255, 253, 247)
RULE = RGBColor(218, 210, 194)
WHITE = RGBColor(255, 255, 255)


@dataclass
class HighlightPage:
    title: str
    highlights: list[str]


@dataclass
class Illustration:
    id: str
    title: str
    placement: str
    image: str
    source_url: str
    caption: str
    annotation: str
    credit: str
    image_url: str | None = None
    credit_url: str | None = None


@dataclass
class Day:
    number: int
    date: datetime
    heading: str
    source_path: Path
    transcript: str
    pages: list[HighlightPage]
    source_url: str
    places: list[str]
    miles: float
    events: list[str]

    @property
    def rootstalk_url(self) -> str | None:
        if not (1 <= self.number <= 19 or 38 <= self.number <= 41):
            return None
        anchor = self.date.strftime("%A-%B-").lower() + f"{self.date.day}-{self.date.year}"
        if self.number == 39:
            anchor += "---thanksgiving-day"
        return f"{ROOTSTALK_URL}#{anchor}"


FOREWORD_QUOTES = [
    (
        "I remember my father as the consumate DIYer, a genuine Jack-of-All-Trades, "
        "and master of many! Having read grandma’s journal many times I see his skills "
        "and spirit were inherited, and passed on to me – albeit with less mastery. "
        "Whether that’s a good thing or bad in my case, and in these complex times, "
        "I’m still uncertain.",
        "The author's father, and the resourcefulness behind the story",
    ),
    (
        "The McFate family, like so many others “back in the day”, was resourceful. "
        "Perhaps a testament to a simpilier time? Certainly a quality that served them "
        "well in both daily life, and as they ventured forth.",
        "Resourcefulness on the road",
    ),
    (
        "When compiling this text, and preparing content for https://1926.mcfate.family, "
        "I counted 53 entries mentioning breakdowns – and subsequent repairs – related "
        "to tires, wheels, oil, electrical systems, and the engine of their Ford. They "
        "overcame all these things without significant assistance from others.",
        "Fifty-three breakdown and repair entries",
    ),
    (
        "They were clearly perseverant, averaging 75 miles per day over 35 days of "
        "travel - a 9.4 MPH moving average - while managing to feed themselves (and "
        "others), shooting game near the roadside when it was acceptable to do so. "
        "They prepared most of their own meals, setup and broke camp 34 times, and "
        "even crafted simple toys for the kids to keep them occupied. Grandma had a "
        "hand in all of this while observing and recording innumerable details as "
        "you will see in her writing.",
        "A moving household: the author's research summary",
    ),
    (
        "They were remarkably resourceful and perseverant, necessities of a simpiler "
        "life in a simplier time, and I envy that.",
        "A closing reflection",
    ),
]


@dataclass
class PullQuote:
    day: int
    anchor: str
    text: str


def read_pullquotes() -> list[PullQuote]:
    records = json.loads(PULLQUOTES.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("Rootstalk pullquotes must be a nonempty list.")
    quotes = []
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != {"day", "anchor", "text"}
            or type(record["day"]) is not int
            or not 1 <= record["day"] <= 41
            or any(not isinstance(record[key], str) or not record[key].strip()
                   for key in ("anchor", "text"))
        ):
            raise ValueError("Each Rootstalk pullquote needs a day, anchor, and verbatim text.")
        quotes.append(PullQuote(**record))
    if [quote.day for quote in quotes] != sorted(quote.day for quote in quotes):
        raise ValueError("Rootstalk pullquotes must retain article order.")
    return quotes


def parse_date(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%a, %b, %d, %Y")


def clean_markdown(value: str) -> str:
    value = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[\d+\]\(#[^)]+\)", "", value)
    value = re.sub(r"[*_`#]", "", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def read_diary_files() -> list[tuple[Path, str, str]]:
    entries = []
    for path in sorted(DIARY_DIR.glob("[0-9][0-9][0-9]-*.md")):
        if path.name.startswith("000-"):
            continue
        raw = path.read_text(encoding="utf-8")
        heading = next(
            (line[3:].strip() for line in raw.splitlines() if line.startswith("## ")),
            "",
        )
        body = re.split(r"^## .+$", raw, maxsplit=1, flags=re.MULTILINE)
        transcript = clean_markdown(body[1]) if len(body) > 1 else ""
        entries.append((path, heading, transcript))
    if len(entries) != 41:
        raise ValueError(f"Expected 41 dated diary entries, found {len(entries)}.")
    return entries


def read_highlights() -> dict[int, list[HighlightPage]]:
    raw = json.loads(HIGHLIGHTS.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != {str(number) for number in range(1, 42)}:
        raise ValueError("Diary highlights must contain exactly days 1 through 41.")
    result: dict[int, list[HighlightPage]] = {}
    for number, pages in raw.items():
        if not isinstance(pages, list) or not pages:
            raise ValueError(f"Day {number} needs at least one highlight page.")
        result[int(number)] = []
        for page in pages:
            if not isinstance(page, dict):
                raise ValueError(f"Day {number}: each highlight page must be an object.")
            title = page.get("title")
            highlights = page.get("highlights")
            if not isinstance(title, str) or not title.strip():
                raise ValueError(f"Day {number}: each highlight page needs a title.")
            if (
                not isinstance(highlights, list)
                or not 1 <= len(highlights) <= 3
                or any(not isinstance(text, str) or not text.strip() for text in highlights)
            ):
                raise ValueError(f"Day {number}: use one to three nonempty highlight paragraphs.")
            if len(title) > 65 or sum(len(text.split()) for text in highlights) > 115:
                raise ValueError(
                    f"Day {number}, {title!r}: shorten the summary or split it into more pages "
                    "(maximum 65 title characters and 115 words per page)."
                )
            result[int(number)].append(HighlightPage(title, highlights))
    return result


def read_days() -> list[Day]:
    highlights = read_highlights()
    source_urls: dict[str, str] = {}
    with METADATA.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            if row["display_template"] == "markdown" and not row["parentid"]:
                source_urls[row["date"]] = f"{SITE_URL}/items/{row['objectid']}.html"

    records: dict[int, list[dict[str, str]]] = {}
    with TRIP_DATA.open(newline="", encoding="utf-8-sig") as file:
        for row in csv.DictReader(file):
            number = row.get("Day Number", "").strip()
            if number.isdigit() and int(number) > 0:
                records.setdefault(int(number), []).append(row)

    diary = read_diary_files()
    days: list[Day] = []
    for number, (path, heading, transcript) in enumerate(diary, start=1):
        rows = records.get(number)
        if not rows:
            raise ValueError(f"No trip-data rows found for diary day {number}.")
        dated = next((row["Date"].strip() for row in rows if row.get("Date", "").strip()), "")
        date = parse_date(dated)
        date_key = date.strftime("%Y-%m-%d")
        if date_key not in source_urls:
            raise ValueError(f"No website item found in collection metadata for {date_key}.")
        places = list(dict.fromkeys(row["Where"].strip() for row in rows if row.get("Where", "").strip()))
        miles_text = next(
            (row["Daily Mileage"].strip() for row in reversed(rows) if row.get("Daily Mileage", "").strip()),
            "0",
        )
        events = []
        for row in rows:
            event = row.get("What", "").strip()
            event = re.sub(
                r"\s*,?\s*\d{1,2}\.\d+°?\s*[NS],?\s*\d{1,3}\.\d+°?\s*[EW]",
                "",
                event,
            ).strip(" ,;")
            if event and event not in events:
                events.append(event)
        days.append(
            Day(
                number=number,
                date=date,
                heading=heading,
                source_path=path,
                transcript=transcript,
                pages=highlights[number],
                source_url=source_urls[date_key],
                places=places,
                miles=float(miles_text),
                events=events,
            )
        )
    return days


def read_illustrations() -> list[Illustration]:
    records = json.loads(ILLUSTRATIONS.read_text(encoding="utf-8"))
    illustrations = [Illustration(**record) for record in records]
    ids = set()
    placements = {"family", "route"} | {f"day-{day}" for day in range(1, 42)}
    for illustration in illustrations:
        if illustration.id in ids:
            raise ValueError(f"Duplicate illustration ID: {illustration.id}")
        ids.add(illustration.id)
        if illustration.placement not in placements:
            raise ValueError(f"Invalid illustration placement: {illustration.placement}")
        if not (ROOT / illustration.image).is_file():
            raise FileNotFoundError(f"Missing illustration: {illustration.image}")
    return illustrations


def add_background(slide, color=PAPER):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, Inches(SLIDE_W), Inches(SLIDE_H)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def add_box(slide, x, y, w, h, color=CARD, radius=True):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def add_link(slide, label, url, x, y, w, h, *, size=12):
    shape = add_text(slide, label, x, y, w, h, size=size, color=GREEN, font="Arial")
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            run.hyperlink.address = url
            run.font.underline = True
    return shape


def add_footer_links(slide, links: list[tuple[str, str]], *, size=12, y=6.76, h=0.26):
    shape = add_text(
        slide, "", 0.65, y, SLIDE_W - 1.3, h,
        size=size, color=GREEN, font="Arial", align=PP_ALIGN.CENTER,
    )
    shape.name = "Footer links"
    shape.text_frame.word_wrap = False
    paragraph = shape.text_frame.paragraphs[0]
    for index, (label, url) in enumerate(links):
        if index:
            separator = paragraph.add_run()
            separator.text = " · "
        run = paragraph.add_run()
        run.text = label
        run.hyperlink.address = url
        run.font.underline = True
    return shape


def add_text(
    slide,
    text,
    x,
    y,
    w,
    h,
    *,
    size=18,
    color=INK,
    font="Aptos",
    bold=False,
    italic=False,
    align=PP_ALIGN.LEFT,
    valign=MSO_ANCHOR.TOP,
    margin=0,
):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = shape.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(margin)
    frame.margin_right = Inches(margin)
    frame.margin_top = Inches(margin)
    frame.margin_bottom = Inches(margin)
    frame.vertical_anchor = valign
    for index, line in enumerate(text.split("\n")):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.alignment = align
        paragraph.font.name = font
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.italic = italic
        paragraph.font.color.rgb = color
    return shape


def add_footer(slide, page_label):
    add_text(
        slide,
        "MIRIAM ABIA McFATE  ·  1926",
        0.62,
        7.08,
        5.7,
        0.2,
        size=9,
        color=MUTED,
        bold=True,
    )
    add_text(
        slide,
        page_label,
        7.1,
        7.08,
        5.55,
        0.2,
        size=9,
        color=MUTED,
        align=PP_ALIGN.RIGHT,
    )


def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def blank_slide(prs, label):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide)
    add_footer(slide, label)
    return slide


def add_veterans_slide(prs):
    navy = RGBColor(20, 43, 76)
    red = RGBColor(174, 42, 52)
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(slide, navy)
    for y, color in ((0, red), (0.18, WHITE), (7.14, WHITE), (7.32, red)):
        add_box(slide, 0, y, SLIDE_W, 0.18, color, radius=False)
    for x in (4.72, 5.57, 6.42, 7.27, 8.12):
        star = slide.shapes.add_shape(
            MSO_SHAPE.STAR_5_POINT, Inches(x), Inches(0.78),
            Inches(0.48), Inches(0.48),
        )
        star.fill.solid()
        star.fill.fore_color.rgb = WHITE
        star.line.fill.background()
    for side, x in (("left", 0.6), ("right", SLIDE_W - 1.85)):
        flag = slide.shapes.add_group_shape()
        flag.name = f"US flag: {side}"
        for stripe in range(13):
            add_box(
                flag, x, 1.65 + stripe * 0.66 / 13, 1.25, 0.66 / 13,
                red if stripe % 2 == 0 else WHITE, radius=False,
            )
        add_box(flag, x, 1.65, 0.5, 0.66 * 7 / 13, navy, radius=False)
        for row in range(9):
            for column in range(6 if row % 2 == 0 else 5):
                star = flag.shapes.add_shape(
                    MSO_SHAPE.STAR_5_POINT,
                    Inches(x + 0.025 + column * 0.079 + (0.0395 if row % 2 else 0)),
                    Inches(1.67 + row * 0.037), Inches(0.047), Inches(0.03),
                )
                star.fill.solid()
                star.fill.fore_color.rgb = WHITE
                star.line.fill.background()
    add_text(
        slide, "HONORING OUR VETERANS", 2.0, 1.65, SLIDE_W - 4.0, 0.75,
        size=38, font="Georgia", bold=True, color=WHITE, align=PP_ALIGN.CENTER,
    )
    add_text(
        slide, "Veterans Day  ·  November 11, 2026",
        0.65, 2.65, SLIDE_W - 1.3, 0.45,
        size=22, font="Arial", color=WHITE, align=PP_ALIGN.CENTER,
    )
    add_text(
        slide, "To all who have served: thank you for your service,\n"
        "your sacrifice, and your dedication to our country.",
        0.95, 3.5, SLIDE_W - 1.9, 1.0,
        size=25, font="Arial", color=WHITE, align=PP_ALIGN.CENTER,
    )
    add_box(slide, 0.85, 5.15, SLIDE_W - 1.7, 1.6, WHITE)
    for side, x in (("left", 1.0), ("right", SLIDE_W - 2.0)):
        balloons = slide.shapes.add_group_shape()
        balloons.name = f"Birthday balloons: {side}"
        for offset, y, color in ((0, 5.5, red), (0.3, 5.26, RGBColor(40, 105, 181)),
                                 (0.6, 5.55, GOLD)):
            center = x + offset + 0.19
            add_box(balloons, center, y + 0.47, 0.012, 6.55 - y - 0.47, MUTED, radius=False)
            knot = balloons.shapes.add_shape(
                MSO_SHAPE.ISOSCELES_TRIANGLE, Inches(center - 0.045),
                Inches(y + 0.45), Inches(0.09), Inches(0.1),
            )
            knot.fill.solid()
            knot.fill.fore_color.rgb = color
            knot.line.fill.background()
            balloon = balloons.shapes.add_shape(
                MSO_SHAPE.OVAL, Inches(x + offset), Inches(y), Inches(0.38), Inches(0.5),
            )
            balloon.fill.solid()
            balloon.fill.fore_color.rgb = color
            balloon.line.fill.background()
    add_text(
        slide, "Happy birthday to my sister-in-law, Lucy!",
        2.15, 5.4, SLIDE_W - 4.3, 0.4,
        size=23, font="Arial", bold=True, color=navy, align=PP_ALIGN.CENTER,
    )
    add_text(
        slide, "An early happy birthday to my brother Ron for November 12!\n"
        "And a special thank-you to Ron for his service as a Navy veteran.",
        2.15, 5.98, SLIDE_W - 4.3, 0.62,
        size=18, font="Arial", color=navy, align=PP_ALIGN.CENTER,
    )
    add_notes(slide, "Opening recognition for Veterans Day, November 11, 2026. "
              "Birthday wishes and recognition of Ron's Navy service supplied by the presenter.")
    return slide


def add_cover(prs):
    slide = blank_slide(prs, "100 YEARS")
    add_text(slide, "A FAMILY ROAD WEST", 0.7, 0.35, 11.93, 0.3, size=14, color=RUST, bold=True)
    add_text(
        slide,
        "Miriam McFate’s 1926 journey",
        0.7,
        0.85,
        11.93,
        0.65,
        size=34,
        color=INK,
        font="Georgia",
        bold=True,
    )
    banner_url = "https://rootstalk.blob.core.windows.net/rootstalk-2025-spring/1926-header-image.png"
    picture = slide.shapes.add_picture(
        str(ROOT / "presentation" / "images" / "1926-header-image.png"),
        Inches(0.65), Inches(1.7), width=Inches(SLIDE_W - 1.3),
    )
    picture.name = "Rootstalk cover banner"
    picture._element.nvPicPr.cNvPr.set(
        "descr", "Rootstalk article header: 1926 highway map, Miriam's portrait, "
        "and the published journal title and subtitle.",
    )
    picture.click_action.hyperlink.address = ROOTSTALK_URL
    add_text(
        slide,
        "Iowa to California in a Ford—one day, one mile, one repair at a time.",
        0.7,
        5.98,
        11.93,
        0.4,
        size=18,
        color=GREEN,
    )
    add_text(
        slide,
        "A century later · November 11, 2026",
        0.7,
        6.5,
        11.93,
        0.38,
        size=16,
        color=RUST,
        bold=True,
    )
    add_notes(
        slide,
        "Presentation date: November 11, 2026. The diary covers October 18 through "
        "November 27, 1926. The title does not claim November 11 was the exact "
        "midpoint; see the route overview. The complete Rootstalk header image "
        "is reproduced without cropping or retouching; its embedded wording is "
        "part of the published artwork. The Sheridan Township map remains on "
        "its dedicated illustrated slide.\n"
        f"Banner image: {banner_url}\n"
        f"Source: {ROOTSTALK_URL}",
    )
    return slide


def add_sources_slide(prs):
    slide = blank_slide(prs, "INFORMATION SOURCES")
    add_text(
        slide, "Two sources behind this journey", 0.8, 0.7, 11.7, 0.65,
        size=32, font="Georgia", bold=True,
    )
    sources = [
        (
            "1926.mcfate.family",
            SITE_URL,
            "THE FULL JOURNAL & ONGOING RESEARCH",
            "All 41 dated diary entries, with maps, photographs, supporting "
            "material, and continuing research by Mark McFate. Use this site "
            "to explore a particular day beyond the slide summary.",
        ),
        (
            "rootstalk.grinnell.edu",
            ROOTSTALK_URL,
            "THE PUBLISHED STORY & FAMILY REFLECTION",
            "An abridged journal edition in Volume XI, Issue 1 (Spring 2025), "
            "with Mark McFate's foreword on the family's resourcefulness "
            "and perseverance. The deck includes all 15 journal pullquotes "
            "and five separate foreword excerpts.",
        ),
    ]
    for index, (label, url, caption, description) in enumerate(sources):
        y = 1.75 + index * 2.4
        add_box(slide, 0.8, y, 11.73, 2.12)
        add_text(slide, caption, 1.1, y + 0.18, 11.1, 0.25, size=11, color=RUST, bold=True)
        add_link(slide, label, url, 1.1, y + 0.55, 11.1, 0.42, size=25)
        add_text(
            slide, description, 1.1, y + 1.02, 11.1, 1.0,
            size=19, font="Arial",
        )
    contact = add_text(
        slide,
        "Questions or comments?  Please contact Mark at mark.mcfate@icloud.com.",
        0.65, 6.55, SLIDE_W - 1.3, 0.35,
        size=16, font="Arial", color=GREEN, align=PP_ALIGN.CENTER,
    )
    contact.name = "Source contact"
    add_notes(
        slide,
        "Two complementary presentations of Miriam's journal, not independent "
        "eyewitness accounts. The website provides the full transcript and "
        "ongoing supporting research; Rootstalk publishes an abridged edition "
        "with Mark McFate's contextual foreword.\n"
        f"Full journal and research: {SITE_URL}\n"
        f"Rootstalk article and foreword: {ROOTSTALK_URL}\n"
        "The Rootstalk edition skips from November 5 to November 24. Consult "
        "the full-journal website for the intervening entries. Click either "
        "domain on the slide to open its source; the Rootstalk link goes "
        "directly to the journal article.",
    )
    return slide


def add_people_slide(prs):
    slide = blank_slide(prs, "THE FAMILY")
    add_text(slide, "A traveling household", 0.8, 0.72, 7.5, 0.62, size=32, font="Georgia", bold=True)
    add_text(
        slide,
        "Eight people, two dogs, and a Ford fitted for camp life",
        0.83,
        1.45,
        7.6,
        0.38,
        size=17,
        color=GREEN,
    )
    add_box(slide, 0.8, 2.15, 7.15, 4.3)
    add_text(
        slide,
        "Miriam Abia McFate  ·  journal keeper, 29\n"
        "Clarence McFate  ·  driver and mechanic\n"
        "Grover Tahash  ·  Miriam’s brother\n"
        "Mildred  ·  14     Kenneth  ·  12\n"
        "Velma  ·  8     Delmar  ·  6     Beulah  ·  4\n"
        "Jimmie the dog; Dallas, a terrier puppy found in Texas",
        1.18,
        2.55,
        6.45,
        3.2,
        size=19,
        color=INK,
    )
    add_box(slide, 8.45, 2.15, 3.9, 4.3, RGBColor(237, 228, 209))
    add_text(slide, "“", 8.82, 2.32, 0.6, 0.5, size=48, color=GOLD, font="Georgia")
    add_text(
        slide,
        "Our house is built on a Ford, with all modern convenience of camp life.",
        8.92,
        3.0,
        3.0,
        1.55,
        size=22,
        color=INK,
        font="Georgia",
        italic=True,
    )
    add_text(slide, "— Miriam’s opening journal entry", 8.92, 5.15, 3.0, 0.46, size=12, color=MUTED)
    add_notes(
        slide,
        "Family names and ages are listed in the Rootstalk article and the opening "
        "journal context. Miriam describes a gasoline stove, small wood heater, "
        "medicine cabinet, folding table and chairs, day bed, cupboard, pressure "
        "cooker, tent, and camp cots. The quote is from her October 18, 1926 entry.\n"
        f"Source: {ROOTSTALK_URL}\n"
        "Primary repository source: objects/markdown/000-intro.md",
    )
    return slide


def add_route_slide(prs):
    slide = blank_slide(prs, "ROUTE AT A GLANCE")
    add_text(slide, "A road west, day by day", 0.8, 0.72, 8.2, 0.62, size=32, font="Georgia", bold=True)
    add_text(
        slide,
        "October 18 – November 27, 1926  ·  41 dated diary entries",
        0.83,
        1.45,
        8.4,
        0.36,
        size=16,
        color=GREEN,
    )
    states = ["IOWA", "ILLINOIS", "MISSOURI", "ARKANSAS", "TEXAS", "NEW MEXICO", "ARIZONA", "CALIFORNIA"]
    x0, y, w = 0.95, 2.3, 11.45
    add_box(slide, x0, y + 0.23, w, 0.08, RULE, radius=False)
    step = w / (len(states) - 1)
    for idx, state in enumerate(states):
        x = x0 + idx * step
        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL, Inches(x - 0.08), Inches(y + 0.13), Inches(0.25), Inches(0.25)
        )
        dot.fill.solid()
        dot.fill.fore_color.rgb = GOLD if idx in (0, len(states) - 1) else GREEN
        dot.line.fill.background()
        label_x = min(x - 0.4, SLIDE_W - 1.45)
        add_text(slide, state, label_x, y + 0.6, 1.35, 0.25, size=9, color=INK, bold=True, align=PP_ALIGN.CENTER)
    add_box(slide, 0.8, 3.65, 3.55, 1.55, GREEN)
    add_text(slide, "2,809", 1.08, 3.88, 2.95, 0.68, size=36, color=WHITE, font="Georgia", bold=True)
    add_text(slide, "miles in Miriam’s final entry", 1.08, 4.62, 3.0, 0.28, size=12, color=WHITE)
    add_box(slide, 4.88, 3.65, 3.55, 1.55, RGBColor(237, 228, 209))
    add_text(slide, "35", 5.17, 3.88, 2.95, 0.68, size=36, color=INK, font="Georgia", bold=True)
    add_text(slide, "travel days, per the author’s research", 5.17, 4.62, 3.0, 0.28, size=12, color=INK)
    add_box(slide, 8.96, 3.65, 3.55, 1.55, RGBColor(237, 228, 209))
    add_text(slide, "34", 9.25, 3.88, 2.95, 0.68, size=36, color=INK, font="Georgia", bold=True)
    add_text(slide, "times they set up and broke camp", 9.25, 4.62, 3.0, 0.28, size=12, color=INK)
    add_text(
        slide,
        "November 11 is day 25 of the 41 entries—just after the calendar midpoint "
        "(around November 7–8). On that day the family crossed North Texas, from "
        "the Dallas area toward Fort Worth.",
        0.88,
        5.62,
        11.55,
        0.8,
        size=15,
        color=INK,
    )
    add_text(
        slide,
        "Mileage sources differ: Miriam’s final entry says 2,809 miles; the reconstructed route CSV totals 2,574.6.",
        0.9,
        6.53,
        11.6,
        0.24,
        size=9,
        color=MUTED,
    )
    add_notes(
        slide,
        "The final journal entry states that the trip covered 2,809 miles. The "
        "Rootstalk foreword reports 35 travel days and 34 camp set-ups/breakdowns. "
        "The reconstructed route CSV totals 2,574.6 miles and has 34 day-number "
        "groups with positive recorded mileage. These are distinct source measures; "
        "the deck does not reconcile them. The 75-mile/day and 35-day figures are "
        "reproduced from the article as published. "
        "November 11, 1926, is day 25 of the 41 dated entries. Counting inclusive "
        "dates from October 18 to November 27, the calendar midpoint is around "
        "November 7–8, so the presentation describes November 11 as just after the "
        "midpoint rather than the exact midpoint.\n"
        f"Research source and statistics: {ROOTSTALK_URL}\n"
        "Final diary entry: objects/markdown/041-sat-nov-27-1926.md",
    )
    return slide


def add_quote_slide(prs, quote, caption, index, *, pullquote: PullQuote | None = None):
    kind = "PULL QUOTE" if pullquote else "FOREWORD EXCERPT"
    source_url = f"{ROOTSTALK_URL}#{pullquote.anchor if pullquote else 'foreword-resourceful-and-perseverant'}"
    slide = blank_slide(prs, f"ROOTSTALK · {kind} {index}")
    add_text(slide, f"{kind}  /  ROOTSTALK", 0.9, 0.75, 5.2, 0.35, size=12, color=RUST, bold=True)
    add_box(slide, 0.88, 1.42, 0.12, 4.95, GOLD, radius=False)
    body = add_text(
        slide,
        quote if pullquote else f"“{quote}”",
        1.38,
        1.55,
        10.35,
        4.35,
        size=24 if len(quote) < 500 else 20,
        color=INK,
        font="Georgia",
        italic=True,
        valign=MSO_ANCHOR.MIDDLE,
    )
    body.name = f"Rootstalk pullquote: {index}" if pullquote else f"Foreword excerpt: {index}"
    add_text(slide, caption, 1.42, 6.12, 8.9, 0.35, size=13, color=GREEN, bold=True)
    author = "Miriam Abia McFate" if pullquote else "Mark McFate"
    add_text(slide, f"{author} · Rootstalk, Volume XI, Issue 1 · Spring 2025", 1.42, 6.48, 9.5, 0.26, size=10, color=MUTED)
    add_footer_links(slide, [("Read the Rootstalk article online", source_url)], size=10, y=6.8, h=0.22)
    add_notes(
        slide,
        ("Verbatim div.pullquote from the Rootstalk article. "
         if pullquote else "Verbatim excerpt from the Rootstalk article's italicized foreword. ") +
        "The original spelling and punctuation are retained.\n"
        f"Source: {source_url}\n"
        f"Context: {caption}\n"
        f"Quote: {quote}" +
        (f"\nDiary day: {pullquote.day}" if pullquote else ""),
    )
    return slide


def add_day_slide(prs, day: Day, page: HighlightPage, part: int):
    date_label = day.date.strftime("%A, %B %-d, %Y")
    part_label = f"PART {part} OF {len(day.pages)}"
    slide = blank_slide(prs, f"DAY {day.number:02d} / 41 · {part_label}")
    add_text(
        slide,
        f"DAY {day.number:02d} / 41  ·  {part_label}  ·  DIARY SUMMARY",
        0.65, 0.3, 8.4, 0.24, size=11, color=RUST, bold=True,
    )
    add_text(slide, date_label, 0.65, 0.68, 11.9, 0.55, size=30, color=INK, font="Georgia", bold=True)
    if day.number == 25:
        add_box(slide, 9.52, 0.25, 3.16, 0.34, GOLD)
        add_text(
            slide,
            "100 YEARS AGO TODAY",
            9.62,
            0.31,
            2.96,
            0.22,
            size=10,
            color=WHITE,
            bold=True,
            align=PP_ALIGN.CENTER,
        )

    route = "  ·  ".join(day.places) if day.places else "Route not recorded in trip data"
    endpoints = list(dict.fromkeys(day.places[:1] + day.places[-1:]))
    route_label = " to ".join(endpoints) if endpoints else "Route not recorded in trip data"
    add_text(slide, route_label, 0.68, 1.3, 9.5, 0.28, size=12, color=GREEN, bold=True)
    add_text(
        slide, f"{day.miles:,.1f} miles logged", 10.1, 1.3, 2.55, 0.28,
        size=12, color=MUTED, align=PP_ALIGN.RIGHT,
    )

    add_box(slide, 0.65, 1.74, 12.03, 4.88)
    add_text(
        slide, page.title, 0.95, 1.96, 11.43, 0.53,
        size=26, font="Georgia", color=GREEN, bold=True,
    )
    body = add_text(
        slide,
        "\n".join(page.highlights),
        0.98,
        2.66,
        11.37,
        3.74,
        size=22,
        color=INK,
        font="Arial",
    )
    body.name = f"Diary highlights: day {day.number}, part {part}"
    for index, paragraph in enumerate(body.text_frame.paragraphs):
        paragraph.line_spacing = 1.05
        paragraph.space_after = Pt(12 if index < len(page.highlights) - 1 else 0)
    links = [("Open this day's full journal on the source website", day.source_url)]
    if day.rootstalk_url:
        links.append(("Read this day in Rootstalk", day.rootstalk_url))
    add_footer_links(slide, links)

    notes = [
        f"{date_label} · day {day.number} of 41",
        f"{part_label}: {page.title}",
        "Slide text is an editorial summary, not a verbatim quotation.",
        f"Route data: {route}",
        f"Recorded daily mileage: {day.miles:g}",
        f"Trip-data events: {' | '.join(day.events)}",
        f"Read this entry online: {day.source_url}",
        *([f"Rootstalk entry: {day.rootstalk_url}"] if day.rootstalk_url else []),
        "",
        "Full transcript:",
        day.transcript,
        "",
        f"Transcript source: {day.source_path.relative_to(ROOT)}",
        f"Trip-data source: {TRIP_DATA.relative_to(ROOT)}",
    ]
    if day.number == 25:
        notes.extend(
            [
                "",
                "The journal recounts finding a terrier puppy in a gunny sack near "
                "Dallas and naming the pup Dallas.",
            ]
        )
    if day.number == 33:
        notes.extend(
            [
                "",
                "Date verification needed: the trip-data CSV dates this entry Friday, "
                "November 19, while its transcript heading says Friday, November 20. "
                "The following entry is Saturday, November 20. The slide follows the "
                "route CSV pending primary-journal verification.",
            ]
        )
    add_notes(slide, "\n".join(notes))
    return slide


def add_illustration_slide(prs, illustration: Illustration):
    slide = blank_slide(prs, "PHOTOGRAPHS & MAPS")
    add_text(
        slide, illustration.title, 0.65, 0.55, 12.0, 0.65,
        size=30, font="Georgia", bold=True,
    )
    wide = illustration.id in {"representative-camper", "1926-route-map"}
    x, y, width, height = (0.65, 1.4, 12.03, 3.8) if wide else (0.65, 1.4, 7.25, 5.15)
    picture = slide.shapes.add_picture(str(ROOT / illustration.image), Inches(x), Inches(y))
    scale = min(Inches(width) / picture.width, Inches(height) / picture.height)
    picture.width = round(picture.width * scale)
    picture.height = round(picture.height * scale)
    picture.left = Inches(x) + (Inches(width) - picture.width) // 2
    picture.top = Inches(y) + (Inches(height) - picture.height) // 2
    picture.name = f"Illustration: {illustration.id}"
    picture._element.nvPicPr.cNvPr.set("descr", illustration.caption)
    image_url = illustration.image_url or f"{SITE_URL}/{illustration.image}"
    picture.click_action.hyperlink.address = image_url

    caption_x, caption_y, caption_w, caption_h = (
        (0.7, 5.35, 11.9, 0.83) if wide else (8.2, 1.82, 4.4, 3.15)
    )
    if not wide:
        add_text(
            slide, "PUBLISHED CAPTION", 8.2, 1.45, 4.4, 0.24,
            size=10, color=RUST, bold=True,
        )
    caption = add_text(
        slide, illustration.caption, caption_x, caption_y, caption_w, caption_h,
        size=17 if len(illustration.caption) > 320 else 18, font="Arial",
    )
    caption.name = f"Caption: {illustration.id}"
    annotation = add_text(
        slide, illustration.annotation,
        0.7 if wide else 8.2, 6.25 if wide else 5.12,
        11.9 if wide else 4.4, 0.35 if wide else 0.84,
        size=12, color=GREEN, font="Arial",
    )
    annotation.name = f"Annotation: {illustration.id}"
    if not wide:
        add_text(
            slide, illustration.credit, 8.2, 6.05, 4.4, 0.45,
            size=10, color=MUTED, font="Arial",
        )
    source_label = (
        "Read caption and context in Rootstalk"
        if illustration.source_url.startswith(ROOTSTALK_URL)
        else "Read the source website's introduction"
    )
    add_footer_links(slide, [
        (source_label, illustration.source_url),
        ("Open full-size image", image_url),
    ])
    notes = [
        illustration.title,
        f"Illustration ID: {illustration.id}",
        f"Presentation placement: {illustration.placement} (not proof of the photo's date)",
        "",
        "Published caption (verbatim):",
        illustration.caption,
        "",
        "Editorial annotation:",
        illustration.annotation,
        f"Credit: {illustration.credit}",
        f"Caption/context source: {illustration.source_url}",
        f"Full-size image: {image_url}",
        f"Local image: {illustration.image}",
        "The complete image is aspect-fit without cropping; original marks are retained.",
    ]
    if illustration.credit_url:
        notes.append(f"Original credited website: {illustration.credit_url}")
    if illustration.credit.startswith("McFate family"):
        notes.extend([
            "",
            "Rootstalk endnote 1: Photos were provided to Mark in 2025 by Rachel's "
            "oldest daughter, Debra. Mark believes they were largely taken by Mildred, "
            "the eldest child traveling west. Mildred also contributed many captions, "
            "handwritten on the verso sometime shortly after the 1991 transcript "
            "was created. These are source-qualified attributions, not confirmed "
            "photographer or caption-author identifications for each image.",
            f"Photo provenance: {ROOTSTALK_URL}#endnote1",
        ])
    add_notes(slide, "\n".join(notes))
    return slide


def build():
    days = read_days()
    illustrations = read_illustrations()
    pullquotes = read_pullquotes()
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    prs.core_properties.title = "A Family Road West: Miriam McFate’s 1926 Journey"
    prs.core_properties.subject = "Historical society presentation for November 11, 2026"
    prs.core_properties.author = "Mark McFate"
    prs.core_properties.keywords = "Miriam McFate, 1926, road trip, family history"

    add_veterans_slide(prs)
    add_cover(prs)
    add_sources_slide(prs)
    add_people_slide(prs)
    for illustration in illustrations:
        if illustration.placement == "family":
            add_illustration_slide(prs, illustration)
    add_route_slide(prs)
    for illustration in illustrations:
        if illustration.placement == "route":
            add_illustration_slide(prs, illustration)
    add_quote_slide(prs, *FOREWORD_QUOTES[0], 1)

    insertion_points = {5: 1, 15: 2, 25: 3, 41: 4}
    for day in days:
        day_quotes = [
            (index, quote) for index, quote in enumerate(pullquotes, start=1)
            if quote.day == day.number
        ]
        for offset in range(max(len(day_quotes), len(day.pages))):
            if offset < len(day_quotes):
                index, quote = day_quotes[offset]
                add_quote_slide(
                    prs, quote.text, day.date.strftime("%A, %B %-d, %Y"),
                    index, pullquote=quote,
                )
            if offset < len(day.pages):
                add_day_slide(prs, day, day.pages[offset], offset + 1)
        for illustration in illustrations:
            if illustration.placement == f"day-{day.number}":
                add_illustration_slide(prs, illustration)
        quote_index = insertion_points.get(day.number)
        if quote_index is not None:
            add_quote_slide(prs, *FOREWORD_QUOTES[quote_index], quote_index + 1)

    add_sources_slide(prs)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUTPUT)
    print(f"Created {OUTPUT.relative_to(ROOT)} with {len(prs.slides)} slides.")


if __name__ == "__main__":
    build()
