# tests/test_data_loader.py
"""
Tests for data_loader.py — Excel/JSON/GSheet data parsing.
"""
import os
import pytest
from models import Job, Operation, Machine
from data_loader import (
    _parse_operations,
    _parse_unavailable_periods,
    load_data_from_json,
    load_data_from_excel,
)

# Path to test data files (relative to project root)
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_JSON = os.path.join(PROJECT_ROOT, "data.json")
DATA_XLSX = os.path.join(PROJECT_ROOT, "data.xlsx")


class TestParseOperations:
    def test_single_operation(self):
        ops = _parse_operations("1(15)", row_index=1)
        assert len(ops) == 1
        assert ops[0].machine_id == 1
        assert ops[0].processing_time == 15

    def test_multiple_operations(self):
        ops = _parse_operations("1(15); 2(20); 3(10)", row_index=1)
        assert len(ops) == 3
        assert ops[1].machine_id == 2
        assert ops[1].processing_time == 20

    def test_whitespace_handling(self):
        ops = _parse_operations("  1 ( 15 ) ;  2( 20 )  ", row_index=1)
        assert len(ops) == 2
        assert ops[0].machine_id == 1

    def test_empty_returns_empty(self):
        assert _parse_operations(None, row_index=1) == []
        assert _parse_operations("", row_index=1) == []

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid 'operations' format"):
            _parse_operations("invalid_no_parens", row_index=1)


class TestParseUnavailablePeriods:
    def test_single_period(self):
        periods = _parse_unavailable_periods("10-20", row_index=1)
        assert periods == [(10, 20)]

    def test_multiple_periods(self):
        periods = _parse_unavailable_periods("10-20;50-60", row_index=1)
        assert periods == [(10, 20), (50, 60)]

    def test_empty_returns_empty(self):
        assert _parse_unavailable_periods(None, row_index=1) == []
        assert _parse_unavailable_periods("", row_index=1) == []

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid 'unavailable_periods' format"):
            _parse_unavailable_periods("no_dash_here", row_index=1)


class TestLoadJSON:
    @pytest.mark.skipif(not os.path.exists(DATA_JSON), reason="data.json not found")
    def test_load_from_json(self):
        """Load the real data.json file and verify structure."""
        machines, jobs = load_data_from_json(DATA_JSON)
        assert len(machines) == 3
        assert len(jobs) == 5

        # Spot-check first machine and job
        assert machines[0].machine_id == 0
        assert machines[1].unavailable_periods == [(7, 12)]

        assert jobs[0].job_id == 0
        assert jobs[0].due_date == 15
        assert len(jobs[0].operations) == 3


class TestLoadExcel:
    @pytest.mark.skipif(not os.path.exists(DATA_XLSX), reason="data.xlsx not found")
    def test_load_from_excel(self):
        """Load the real data.xlsx file and verify structure."""
        machines, jobs = load_data_from_excel(DATA_XLSX)
        assert len(machines) > 0
        assert len(jobs) > 0

        # All machines should have valid IDs
        for m in machines:
            assert isinstance(m.machine_id, int)

        # All jobs should have operations, due_date, priority
        for j in jobs:
            assert isinstance(j.job_id, int)
            assert len(j.operations) > 0
            assert j.due_date >= 0
            assert j.priority >= 1
