"""Tests for Context Rot Needle Auditor."""
import unittest
from context_rot_needle_auditor.core import PromptSegment, audit_prompt_assembly, u_curve_salience


class TestContextRotAuditor(unittest.TestCase):
    def test_detects_middle_buried_needle_and_high_dilution(self):
        segs = [
            PromptSegment("head_noise", "a " * 2000, is_needle=False),
            PromptSegment("critical_rule", "Must validate JWT issuer.", is_needle=True),
            PromptSegment("tail_noise", "b " * 2000, is_needle=False),
        ]
        rep = audit_prompt_assembly(segs)
        self.assertEqual(rep.buried_needles, ["critical_rule"])
        self.assertEqual(rep.needle_audits[0].zone, "middle")
        self.assertGreater(rep.rot_risk_score, 0.5)
        self.assertGreaterEqual(len(rep.recommendations), 2)

    def test_edge_pinned_needles_have_low_risk(self):
        segs = [
            PromptSegment("sys", "Strict JSON schema.", is_needle=True),
            PromptSegment("docs", "helper text " * 20, is_needle=False),
            PromptSegment("recency_rule", "Confirm tests pass.", is_needle=True),
        ]
        rep = audit_prompt_assembly(segs)
        self.assertEqual(rep.buried_needles, [])
        self.assertEqual(rep.needle_audits[0].zone, "primacy")
        self.assertEqual(rep.needle_audits[1].zone, "recency")

    def test_u_curve_symmetry_and_edges(self):
        self.assertEqual(u_curve_salience(0.0), 1.0)
        self.assertEqual(u_curve_salience(1.0), 1.0)
        self.assertEqual(u_curve_salience(0.5), 0.25)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            audit_prompt_assembly([])
        with self.assertRaises(ValueError):
            audit_prompt_assembly([PromptSegment("x", "hi")], middle_low=0.8, middle_high=0.2)
