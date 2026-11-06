import unittest

from evaluation.run_evaluation import compare, evaluate, validate_dataset


def issue(category="price", verdict="violation", quote="₹799"):
    return dict(category=category,verdict=verdict,quote=quote)


class EvaluationTests(unittest.TestCase):
    def test_exact_match_has_no_missed_or_extra_warning(self):
        scored=compare([issue()],[issue()])
        self.assertEqual((scored["tp"],scored["fp"],scored["fn"]),(1,0,0))

    def test_wrong_verdict_counts_as_missed_and_extra(self):
        scored=compare([issue()],[issue(verdict="needs_review")])
        self.assertEqual((scored["tp"],scored["fp"],scored["fn"]),(0,1,1))

    def test_duplicates_are_not_hidden_by_set_comparison(self):
        scored=compare([issue()],[issue(),issue()])
        self.assertEqual((scored["tp"],scored["fp"],scored["fn"]),(1,1,0))

    def test_invalid_quote_and_duplicate_case_ids_rejected(self):
        case=dict(id="a",group="baseline",draft="Text",expected=[issue()])
        with self.assertRaises(ValueError):validate_dataset(dict(schema_version=1,cases=[case]))
        case["expected"]=[]
        with self.assertRaises(ValueError):validate_dataset(dict(schema_version=1,cases=[case,case]))

    def test_clean_case_has_undefined_precision_not_invented_perfect_score(self):
        data=dict(schema_version=1,cases=[dict(id="clean",group="baseline",draft="Explore Veyra Audio.",expected=[])])
        report=evaluate(data)
        self.assertEqual(report["summary"]["exact_cases"],1)
        self.assertIsNone(report["summary"]["precision"])
        self.assertIsNone(report["summary"]["recall"])
        self.assertFalse(report["live_ai_tested"])

    def test_missed_labels_are_reported_not_rewritten(self):
        expected=[issue(category="claims",verdict="unsupported",quote="outperforms every competitor")]
        data=dict(schema_version=1,cases=[dict(id="semantic",group="challenge",
            draft="Beat 200 outperforms every competitor.",expected=expected)])
        report=evaluate(data)
        self.assertEqual(report["summary"]["fn"],1)
        self.assertEqual(data["cases"][0]["expected"],expected)


if __name__=="__main__":unittest.main()
