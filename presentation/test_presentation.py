import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import ImageFont
from pptx import Presentation
from pptx.enum.text import PP_ALIGN

import build_presentation as deck


class PresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.days = deck.read_days()
        cls.illustrations = deck.read_illustrations()
        cls.pullquotes = deck.read_pullquotes()
        with tempfile.TemporaryDirectory(dir=deck.ROOT / "presentation") as directory:
            output = Path(directory) / "journey.pptx"
            with patch.object(deck, "OUTPUT", output), contextlib.redirect_stdout(io.StringIO()):
                deck.build()
            cls.presentation = Presentation(output)
        cls.daily_slides = [
            slide for slide in cls.presentation.slides
            if any(shape.name.startswith("Diary highlights:") for shape in slide.shapes)
        ]
        cls.illustrated_slides = [
            slide for slide in cls.presentation.slides
            if any(shape.name.startswith("Illustration:") for shape in slide.shapes)
        ]
        cls.checked_slides = (
            cls.daily_slides + cls.illustrated_slides
            + [slide for slide in cls.presentation.slides
               if any(shape.name.startswith(("Rootstalk pullquote:", "Foreword excerpt:"))
                      for shape in slide.shapes)]
            + [cls.presentation.slides[1], cls.presentation.slides[-1]]
        )

    def test_all_days_and_parts_survive_round_trip(self):
        self.assertEqual(
            len(self.presentation.slides),
            10 + len(self.pullquotes) + len(self.illustrations) + sum(len(day.pages) for day in self.days),
        )
        expected = [
            (day, part, page)
            for day in self.days
            for part, page in enumerate(day.pages, start=1)
        ]
        self.assertEqual(len(self.daily_slides), len(expected))
        for slide, (day, part, page) in zip(self.daily_slides, expected):
            with self.subTest(day=day.number, part=part):
                shapes = {shape.name: shape for shape in slide.shapes}
                body = shapes[f"Diary highlights: day {day.number}, part {part}"]
                self.assertEqual(body.text, "\n".join(page.highlights))
                for index, paragraph in enumerate(body.text_frame.paragraphs):
                    self.assertEqual(paragraph.font.size.pt, 22)
                    self.assertAlmostEqual(paragraph.line_spacing, 1.05)
                    self.assertEqual(
                        paragraph.space_after.pt,
                        12 if index < len(page.highlights) - 1 else 0,
                    )
                self.assertNotIn("…", body.text)
                notes = slide.notes_slide.notes_text_frame.text
                self.assertIn(day.transcript, notes)
                self.assertIn(f"PART {part} OF {len(day.pages)}", notes)
                self.assertIn("editorial summary, not a verbatim quotation", notes)

    def test_visible_source_links_on_every_daily_slide(self):
        expected_days = [day for day in self.days for _ in day.pages]
        for slide, day in zip(self.daily_slides, expected_days):
            with self.subTest(day=day.number):
                link = next(
                    shape for shape in slide.shapes if shape.has_text_frame
                    and shape.name == "Footer links"
                )
                self.assertEqual(link.text_frame.paragraphs[0].runs[0].hyperlink.address, day.source_url)
                self.assertIn(day.source_url, slide.notes_slide.notes_text_frame.text)
        day33 = self.days[32]
        self.assertTrue(day33.source_url.endswith("/items/fri-nov-19.html"))
        self.assertIn("033-fri-nov-20", day33.source_path.name)
        matching = [slide for slide in self.daily_slides if "day 33 of 41" in slide.notes_slide.notes_text_frame.text]
        self.assertTrue(all("Date verification needed" in slide.notes_slide.notes_text_frame.text for slide in matching))

    def test_article_links_remain_clickable(self):
        quotes = [
            slide for slide in self.presentation.slides
            if any(shape.has_text_frame and shape.text == "PULL QUOTE  /  ROOTSTALK" for shape in slide.shapes)
        ]
        self.assertEqual(len(quotes), 15)
        for slide, quote in zip(quotes, self.pullquotes):
            link = next(shape for shape in slide.shapes if shape.has_text_frame and shape.text == "Read the Rootstalk article online")
            self.assertEqual(link.text_frame.paragraphs[0].runs[0].hyperlink.address, f"{deck.ROOTSTALK_URL}#{quote.anchor}")

    def test_pullquotes_are_verbatim_and_interleaved_with_their_diary_days(self):
        found = []
        positions = {}
        for position, slide in enumerate(self.presentation.slides):
            for shape in slide.shapes:
                if shape.name.startswith(("Rootstalk pullquote:", "Diary highlights:")):
                    positions[shape.name] = position
                if shape.name.startswith("Rootstalk pullquote:"):
                    quote = self.pullquotes[len(found)]
                    self.assertEqual(shape.text, quote.text)
                    self.assertIn(quote.text, slide.notes_slide.notes_text_frame.text)
                    self.assertIn(f"Diary day: {quote.day}", slide.notes_slide.notes_text_frame.text)
                    self.assertTrue(any(
                        item.has_text_frame and item.text.startswith("Miriam Abia McFate · Rootstalk")
                        for item in slide.shapes
                    ))
                    found.append(quote)
        self.assertEqual(found, self.pullquotes)
        self.assertEqual([quote.day for quote in found], [3, 3, 5, 5, 6, 10, 13, 14, 16, 19, 25, 30, 35, 39, 41])
        for day in self.days:
            quote_names = [
                f"Rootstalk pullquote: {index}"
                for index, quote in enumerate(self.pullquotes, start=1)
                if quote.day == day.number
            ]
            for offset, name in enumerate(quote_names):
                if offset < len(day.pages):
                    self.assertEqual(
                        positions[name] + 1,
                        positions[f"Diary highlights: day {day.number}, part {offset + 1}"],
                    )
                if offset:
                    prior_part = min(offset, len(day.pages))
                    self.assertGreater(
                        positions[name],
                        positions[f"Diary highlights: day {day.number}, part {prior_part}"],
                    )
        self.assertEqual(
            [name for name, position in positions.items() if 11 <= position <= 14],
            ["Rootstalk pullquote: 1", "Diary highlights: day 3, part 1",
             "Rootstalk pullquote: 2", "Diary highlights: day 4, part 1"],
        )
        foreword = [
            shape.text for slide in self.presentation.slides for shape in slide.shapes
            if shape.name.startswith("Foreword excerpt:")
        ]
        self.assertEqual(foreword, [f"“{text}”" for text, _ in deck.FOREWORD_QUOTES])
        self.assertEqual(
            [index + 1 for index, slide in enumerate(self.presentation.slides)
             if any(shape.name.startswith("Foreword excerpt:") for shape in slide.shapes)],
            [9, 21, 43, 60, 96],
        )

    def test_footer_links_are_one_centered_line_with_unlinked_separator(self):
        count = 0
        for slide in self.presentation.slides:
            footers = [shape for shape in slide.shapes if shape.name == "Footer links"]
            self.assertLessEqual(len(footers), 1)
            for shape in footers:
                count += 1
                self.assertLessEqual(abs(2 * shape.left + shape.width - self.presentation.slide_width), 1)
                frame = shape.text_frame
                self.assertFalse(frame.word_wrap)
                self.assertEqual(len(frame.paragraphs), 1)
                paragraph = frame.paragraphs[0]
                self.assertEqual(paragraph.alignment, PP_ALIGN.CENTER)
                self.assertEqual(frame.margin_left, frame.margin_right)
                runs = paragraph.runs
                self.assertIn(len(runs), (1, 3))
                for run in runs[::2]:
                    self.assertTrue(run.hyperlink.address)
                    self.assertTrue(run.font.underline)
                if len(runs) == 3:
                    self.assertEqual(runs[1].text, " · ")
                    self.assertIsNone(runs[1].hyperlink.address)
                    self.assertFalse(runs[1].font.underline)
                else:
                    self.assertNotIn(" · ", shape.text)
        self.assertEqual(count, len(self.daily_slides) + len(self.illustrated_slides) + 20)

    def test_pullquotes_reject_invalid_records_and_article_order(self):
        valid = json.loads(deck.PULLQUOTES.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pullquotes.json"
            for invalid in (
                [], {}, [{"day": 3, "anchor": "section"}],
                [{"day": 42, "anchor": "section", "text": "quote"}],
                [{"day": 3, "anchor": "", "text": "quote"}],
                list(reversed(valid)),
            ):
                with self.subTest(records=invalid):
                    path.write_text(json.dumps(invalid), encoding="utf-8")
                    with patch.object(deck, "PULLQUOTES", path), self.assertRaises(ValueError):
                        deck.read_pullquotes()

    def test_rootstalk_daily_links_only_for_published_entries(self):
        expected_days = [day for day in self.days for _ in day.pages]
        for slide, day in zip(self.daily_slides, expected_days):
            with self.subTest(day=day.number):
                links = [
                    run for shape in slide.shapes if shape.name == "Footer links"
                    for run in shape.text_frame.paragraphs[0].runs
                    if run.text == "Read this day in Rootstalk"
                ]
                published = day.number <= 19 or day.number >= 38
                self.assertEqual(len(links), int(published))
                if published:
                    link = links[0]
                    self.assertEqual(link.hyperlink.address, day.rootstalk_url)
                    self.assertIn(day.rootstalk_url, slide.notes_slide.notes_text_frame.text)
                else:
                    self.assertIsNone(day.rootstalk_url)
        self.assertEqual(
            self.days[38].rootstalk_url,
            f"{deck.ROOTSTALK_URL}#thursday-november-25-1926---thanksgiving-day",
        )

    def test_matching_source_slides_after_cover_and_at_end(self):
        opening = self.presentation.slides[1]
        closing = self.presentation.slides[-1]
        def contents(slide):
            return [shape.text for shape in slide.shapes if shape.has_text_frame]
        self.assertEqual(contents(opening), contents(closing))
        self.assertIn("Two sources behind this journey", contents(opening))
        for slide in (opening, closing):
            contact = next(shape for shape in slide.shapes if shape.name == "Source contact")
            self.assertEqual(
                contact.text,
                "Questions or comments?  Please contact Mark at mark.mcfate@icloud.com.",
            )
            self.assertEqual(contact.text_frame.paragraphs[0].alignment, PP_ALIGN.CENTER)
            self.assertLessEqual(abs(2 * contact.left + contact.width - self.presentation.slide_width), 1)
            self.assertGreater(contact.top / 914400, 6.27)
            links = {
                shape.text: shape.text_frame.paragraphs[0].runs[0].hyperlink.address
                for shape in slide.shapes if shape.has_text_frame
                and shape.text in ("1926.mcfate.family", "rootstalk.grinnell.edu")
            }
            self.assertEqual(links, {
                "1926.mcfate.family": deck.SITE_URL,
                "rootstalk.grinnell.edu": deck.ROOTSTALK_URL,
            })
            self.assertIn("not independent eyewitness accounts", slide.notes_slide.notes_text_frame.text)
        self.assertEqual(opening.notes_slide.notes_text_frame.text, closing.notes_slide.notes_text_frame.text)

    def test_no_audience_note_taking_slide(self):
        text = "\n".join(
            shape.text for slide in self.presentation.slides
            for shape in slide.shapes if shape.has_text_frame
        )
        self.assertNotIn("Leave room for what the room adds", text)
        self.assertNotIn("Add notes here", text)
        self.assertNotIn("OPEN RESEARCH NOTES", text)

    def test_illustrations_keep_complete_images_captions_and_annotations(self):
        self.assertEqual(len(self.illustrated_slides), len(self.illustrations))
        self.assertEqual(len(self.illustrations), 10)
        for illustration in self.illustrations:
            slide = next(
                slide for slide in self.illustrated_slides
                if any(shape.name == f"Illustration: {illustration.id}" for shape in slide.shapes)
            )
            shapes = {shape.name: shape for shape in slide.shapes}
            with self.subTest(illustration=illustration.id):
                picture = shapes[f"Illustration: {illustration.id}"]
                self.assertEqual(picture.image.blob, (deck.ROOT / illustration.image).read_bytes())
                self.assertEqual(
                    (picture.crop_left, picture.crop_right, picture.crop_top, picture.crop_bottom),
                    (0, 0, 0, 0),
                )
                self.assertAlmostEqual(
                    picture.width / picture.height,
                    picture.image.size[0] / picture.image.size[1],
                    places=5,
                )
                self.assertEqual(shapes[f"Caption: {illustration.id}"].text, illustration.caption)
                self.assertEqual(shapes[f"Annotation: {illustration.id}"].text, illustration.annotation)
                image_url = illustration.image_url or f"{deck.SITE_URL}/{illustration.image}"
                self.assertEqual(picture.click_action.hyperlink.address, image_url)
                self.assertEqual(picture._element.nvPicPr.cNvPr.get("descr"), illustration.caption)
                links = [
                    run.hyperlink.address for shape in slide.shapes if shape.has_text_frame
                    for paragraph in shape.text_frame.paragraphs for run in paragraph.runs
                    if run.hyperlink.address
                ]
                self.assertIn(illustration.source_url, links)
                self.assertIn(image_url, links)
                notes = slide.notes_slide.notes_text_frame.text
                for content in (
                    illustration.caption, illustration.annotation,
                    illustration.credit, illustration.source_url, image_url,
                ):
                    self.assertIn(content, notes)
                if illustration.credit.startswith("McFate family"):
                    self.assertIn("handwritten on the verso", notes)
                    self.assertIn(f"{deck.ROOTSTALK_URL}#endnote1", notes)

    def test_photographs_follow_corresponding_diary_entries(self):
        latest_day = None
        for slide in self.presentation.slides:
            for shape in slide.shapes:
                if shape.name.startswith("Diary highlights:"):
                    latest_day = int(shape.name.split("day ")[1].split(",")[0])
                if shape.name.startswith("Illustration:"):
                    illustration = next(
                        item for item in self.illustrations
                        if shape.name == f"Illustration: {item.id}"
                    )
                    if illustration.placement.startswith("day-"):
                        self.assertEqual(latest_day, int(illustration.placement[4:]))
                    else:
                        self.assertIsNone(latest_day)

    def test_daily_shapes_stay_inside_slide(self):
        for slide in self.checked_slides:
            for shape in slide.shapes:
                with self.subTest(shape=shape.name):
                    self.assertGreaterEqual(shape.left, 0)
                    self.assertGreaterEqual(shape.top, 0)
                    self.assertLessEqual(shape.left + shape.width, self.presentation.slide_width)
                    self.assertLessEqual(shape.top + shape.height, self.presentation.slide_height)

    def test_daily_text_fits_with_installed_fonts(self):
        fonts = Path("/System/Library/Fonts/Supplemental")
        if not (fonts / "Arial.ttf").exists() or not (fonts / "Georgia.ttf").exists():
            self.skipTest("Exact Arial/Georgia layout check requires the macOS supplemental fonts.")
        for slide in self.checked_slides:
            for shape in slide.shapes:
                if not shape.has_text_frame or not shape.text:
                    continue
                frame = shape.text_frame
                width = (shape.width - frame.margin_left - frame.margin_right) / 12700
                height = (shape.height - frame.margin_top - frame.margin_bottom) / 12700
                used_height = 0.0
                for index, paragraph in enumerate(frame.paragraphs):
                    font_name = paragraph.font.name or "Arial"
                    # Diary metadata uses the existing Aptos theme; check the Arial fallback.
                    if font_name == "Aptos":
                        font_name = "Arial"
                    suffix = " Bold" if paragraph.font.bold else ""
                    font_path = fonts / f"{font_name}{suffix}.ttf"
                    size = paragraph.font.size.pt
                    font = ImageFont.truetype(str(font_path), round(size * 10))
                    if shape.name == "Footer links":
                        self.assertLessEqual(font.getlength(paragraph.text) / 10, width)
                    lines = 1
                    current = ""
                    for word in paragraph.text.split():
                        self.assertLessEqual(font.getlength(word) / 10, width, shape.name)
                        candidate = f"{current} {word}".strip()
                        if font.getlength(candidate) / 10 > width:
                            lines += 1
                            current = word
                        else:
                            current = candidate
                    spacing = paragraph.line_spacing or 1.2
                    used_height += lines * size * spacing
                    if index < len(frame.paragraphs) - 1:
                        used_height += paragraph.space_after.pt if paragraph.space_after else 0
                with self.subTest(shape=shape.name, text=shape.text[:45]):
                    reserve = 0.4 * 72 if shape.name.startswith("Diary highlights:") else 0
                    self.assertLessEqual(used_height + reserve, height)

    def test_highlights_fail_explicitly_when_incomplete_or_overfull(self):
        valid = json.loads(deck.HIGHLIGHTS.read_text(encoding="utf-8"))
        missing_day = dict(valid)
        missing_day.pop("25")
        overfull = dict(valid)
        overfull["25"] = [{"title": "Too much text", "highlights": ["word " * 116]}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "highlights.json"
            for invalid in (missing_day, overfull):
                path.write_text(json.dumps(invalid), encoding="utf-8")
                with patch.object(deck, "HIGHLIGHTS", path), self.assertRaises(ValueError):
                    deck.read_highlights()


if __name__ == "__main__":
    unittest.main()
