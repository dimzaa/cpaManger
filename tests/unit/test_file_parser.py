"""
Unit tests for FileParser service.

Tests:
- parse_ministry_filename: valid patterns, invalid patterns
- map_hebrew_columns: basic column renaming
"""

import pytest
import pandas as pd

from backend.services.file_parser import FileParser, FileParserException


class TestParseMinistryFilename:
    """Tests for FileParser.parse_ministry_filename()"""

    def test_valid_mucarim_filename(self):
        result = FileParser.parse_ministry_filename("10406544_3_2026MUCARIM.csv")
        assert result["municipality_code"] == 10406544
        assert result["month"] == 3
        assert result["year"] == 2026
        assert result["table"] == "MUCARIM"
        assert result["filename"] == "10406544_3_2026MUCARIM.csv"

    def test_valid_gy033_filename(self):
        result = FileParser.parse_ministry_filename("10406544_3_2026GY033.csv")
        assert result["municipality_code"] == 10406544
        assert result["month"] == 3
        assert result["year"] == 2026
        assert result["table"] == "GY033"

    def test_table_name_is_uppercase(self):
        result = FileParser.parse_ministry_filename("12345_1_2025sometable.csv")
        assert result["table"] == "SOMETABLE"

    def test_single_digit_month(self):
        result = FileParser.parse_ministry_filename("99999999_1_2026TABLE.csv")
        assert result["month"] == 1

    def test_double_digit_month(self):
        result = FileParser.parse_ministry_filename("99999999_12_2026TABLE.csv")
        assert result["month"] == 12

    def test_filename_without_csv_extension(self):
        """parse_ministry_filename should handle stem-only names too."""
        result = FileParser.parse_ministry_filename("10406544_3_2026MUCARIM")
        assert result["municipality_code"] == 10406544

    def test_invalid_filename_raises_exception(self):
        with pytest.raises(FileParserException):
            FileParser.parse_ministry_filename("invalid_filename.csv")

    def test_filename_with_only_two_segments_raises_exception(self):
        """A filename with only two underscore-separated parts should fail."""
        with pytest.raises(FileParserException):
            FileParser.parse_ministry_filename("10406544_3.csv")

    def test_no_underscores_raises_exception(self):
        with pytest.raises(FileParserException):
            FileParser.parse_ministry_filename("nounderscores.csv")

    def test_result_has_all_keys(self):
        result = FileParser.parse_ministry_filename("10406544_3_2026MUCARIM.csv")
        for key in ("municipality_code", "month", "year", "table", "filename"):
            assert key in result


class TestMapHebrewColumns:
    """Tests for FileParser.map_hebrew_columns()"""

    def test_maps_known_hebrew_column(self):
        df = pd.DataFrame({"סמל מוטב": [1, 2], "שם מוטב": ["עיר א", "עיר ב"]})
        result = FileParser.map_hebrew_columns(df)
        assert "municipality_code" in result.columns
        assert "municipality_name" in result.columns

    def test_preserves_unmapped_columns(self):
        df = pd.DataFrame({"עמודה_לא_מוכרת": [1, 2], "סמל מוטב": [10, 20]})
        result = FileParser.map_hebrew_columns(df)
        assert "עמודה_לא_מוכרת" in result.columns
        assert "municipality_code" in result.columns

    def test_maps_amount_column(self):
        df = pd.DataFrame({"סכום מחושב": [50000.0, 60000.0]})
        result = FileParser.map_hebrew_columns(df)
        assert "total" in result.columns

    def test_maps_children_count_column(self):
        df = pd.DataFrame({"מספר ילדים": [30, 40]})
        result = FileParser.map_hebrew_columns(df)
        assert "children_count" in result.columns

    def test_returns_dataframe(self):
        df = pd.DataFrame({"סמל מוטב": [1]})
        result = FileParser.map_hebrew_columns(df)
        assert isinstance(result, pd.DataFrame)

    def test_empty_dataframe_returns_empty(self):
        df = pd.DataFrame()
        result = FileParser.map_hebrew_columns(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result.columns) == 0
