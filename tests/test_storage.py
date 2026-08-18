"""Notes have to survive a restart -- and a corrupted file."""

from __future__ import annotations

import tempfile
import unittest
import unittest.mock
from pathlib import Path

from ajeeb.storage import Note, NoteBook, data_dir


class NoteBookTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "nested" / "notes.json"
        self.book = NoteBook(self.path)

    def test_a_new_notebook_is_empty(self):
        self.assertEqual(self.book.all(), [])

    def test_notes_survive_a_reopen(self):
        self.book.add("buy milk")
        self.book.add("call mum")
        self.assertEqual([n.text for n in NoteBook(self.path).all()], ["buy milk", "call mum"])

    def test_missing_directories_are_created(self):
        self.book.add("first")
        self.assertTrue(self.path.exists())

    def test_remove_uses_the_number_people_hear(self):
        self.book.add("one")
        self.book.add("two")
        self.assertEqual(self.book.remove(1).text, "one")
        self.assertEqual([n.text for n in self.book.all()], ["two"])

    def test_removing_a_number_that_is_not_there(self):
        self.book.add("only")
        for index in (0, 2, -1):
            with self.subTest(index=index), self.assertRaises(IndexError):
                self.book.remove(index)

    def test_clear_reports_how_many_went(self):
        self.book.add("a")
        self.book.add("b")
        self.assertEqual(self.book.clear(), 2)
        self.assertEqual(self.book.all(), [])

    def test_a_corrupted_file_does_not_take_the_assistant_down(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("{not json at all", encoding="utf-8")
        with self.assertLogs("ajeeb.storage", level="WARNING"):
            self.assertEqual(self.book.all(), [])

    def test_unexpected_entries_are_skipped(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text('[{"text": "keep", "created": "x"}, {"nope": 1}, 5]', encoding="utf-8")
        self.assertEqual([n.text for n in self.book.all()], ["keep"])

    def test_a_note_reports_when_it_was_written(self):
        note = Note.new("something")
        self.assertTrue(note.when)
        self.assertEqual(Note(text="x", created="not-a-date").when, "not-a-date")


class DataDirTests(unittest.TestCase):
    def test_ajeeb_home_overrides_the_default(self):
        with unittest.mock.patch.dict("os.environ", {"AJEEB_HOME": "/tmp/ajeeb-test"}):
            self.assertEqual(data_dir(), Path("/tmp/ajeeb-test"))

    def test_the_default_lives_under_the_home_directory(self):
        with unittest.mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(data_dir().name, ".ajeeb")


if __name__ == "__main__":
    unittest.main()
