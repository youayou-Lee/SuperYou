"""
Legal RAG Benchmark Test Runner

This module provides a test framework for evaluating RAG systems on legal documents.
It supports three question types: fact_exact, evidence_set, and conflict_gap.
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class TestResult:
    """Result of a single benchmark test"""
    question_id: str
    question_type: str
    question: str
    passed: bool
    score: float
    max_score: float
    details: Dict[str, Any]
    error_message: Optional[str] = None


class BenchmarkRunner:
    """Main benchmark runner for legal RAG testing"""
    
    def __init__(self, benchmark_dir: Path):
        self.benchmark_dir = Path(benchmark_dir)
        self.questions_dir = self.benchmark_dir / "questions"
        self.results: List[TestResult] = []
        
    def load_questions(self, question_type: Optional[str] = None) -> List[Dict]:
        """Load questions from JSON files"""
        questions = []
        
        if question_type:
            file_path = self.questions_dir / f"{question_type}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'questions' in data:
                        questions.extend(data['questions'])
        else:
            for json_file in self.questions_dir.glob("*.json"):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'questions' in data:
                        questions.extend(data['questions'])
        
        return questions
    
    def evaluate_fact_exact(self, question: Dict, predicted_answer: Dict) -> TestResult:
        """Evaluate fact-exact type question"""
        qid = question['id']
        q_text = question['question']
        expected = question['expected']
        scoring = question['scoring']
        
        score = 0.0
        max_score = 1.0
        details = {}
        
        # Numeric exact match
        if scoring.get('numeric_exact') and 'amount_total' in expected:
            predicted_amount = predicted_answer.get('amount')
            if predicted_amount == expected['amount_total']:
                score += 0.7
                details['amount_match'] = True
            else:
                details['amount_match'] = False
                details['expected'] = expected['amount_total']
                details['predicted'] = predicted_amount
        
        # Date exact match
        if scoring.get('date_exact') and 'date' in expected:
            predicted_date = predicted_answer.get('date')
            if predicted_date == expected['date']:
                score += 0.7
                details['date_match'] = True
            else:
                details['date_match'] = False
                details['expected_date'] = expected['date']
                details['predicted_date'] = predicted_date
        
        # Boolean/Text answer match
        if 'boolean_answer' in expected:
            predicted_bool = predicted_answer.get('boolean')
            if predicted_bool == expected['boolean_answer']:
                score += 0.7
                details['boolean_match'] = True
            else:
                details['boolean_match'] = False
        
        if 'text_answer' in expected:
            predicted_text = predicted_answer.get('text')
            if predicted_text and predicted_text == expected['text_answer']:
                score += 0.7
                details['text_match'] = True
            else:
                details['text_match'] = False
        
        # Citation check
        if scoring.get('citation_required'):
            has_citation = predicted_answer.get('citation') is not None
            if has_citation:
                score += 0.3
                details['citation_provided'] = True
            else:
                details['citation_provided'] = False
        
        # Normalize score
        passed = score >= max_score * 0.7  # 70% to pass
        
        return TestResult(
            question_id=qid,
            question_type='fact_exact',
            question=q_text,
            passed=passed,
            score=score,
            max_score=max_score,
            details=details
        )
    
    def evaluate_evidence_set(self, question: Dict, predicted_answer: Dict) -> TestResult:
        """Evaluate evidence_set type question"""
        qid = question['id']
        q_text = question['question']
        expected = question['expected']
        scoring = question['scoring']
        
        score = 0.0
        max_score = 1.0
        details = {}
        
        key_points = expected.get('key_points', [])
        required_evidence = question.get('required_evidence', [])
        retrieved_evidence = predicted_answer.get('evidence', [])
        
        # Calculate recall
        key_evidence_count = len([e for e in required_evidence if e.get('is_critical', True)])
        retrieved_key_count = 0
        
        for evidence in retrieved_evidence:
            for req_evidence in required_evidence:
                if req_evidence.get('is_critical', True):
                    if 'must_include' in req_evidence:
                        if req_evidence['must_include'] in str(evidence):
                            retrieved_key_count += 1
                            break
        
        recall = retrieved_key_count / max(key_evidence_count, 1) if key_evidence_count > 0 else 1.0
        details['evidence_recall'] = recall
        
        # Calculate precision
        relevant_count = len([e for e in retrieved_evidence 
                          if any(req['must_include'] in str(e) for req in required_evidence)])
        precision = relevant_count / max(len(retrieved_evidence), 1) if retrieved_evidence else 0.0
        details['evidence_precision'] = precision
        
        # Score based on thresholds
        min_recall = scoring.get('evidence_recall_min', 0.8)
        min_precision = scoring.get('evidence_precision_min', 0.7)
        
        if recall >= min_recall:
            score += 0.5
        if precision >= min_precision:
            score += 0.3
            
        # Citation check
        if scoring.get('citation_required'):
            has_citation = predicted_answer.get('citation') is not None
            if has_citation:
                score += 0.2
                details['citation_provided'] = True
            else:
                details['citation_provided'] = False
        
        passed = score >= max_score * 0.7
        
        return TestResult(
            question_id=qid,
            question_type='evidence_set',
            question=q_text,
            passed=passed,
            score=score,
            max_score=max_score,
            details=details
        )
    
    def evaluate_conflict_gap(self, question: Dict, predicted_answer: Dict) -> TestResult:
        """Evaluate conflict_gap type question"""
        qid = question['id']
        q_text = question['question']
        expected = question.get('expected', {})
        
        score = 0.0
        max_score = 1.0
        details = {}
        
        should_abstain = question.get('should_abstain', True)
        required_quote = question.get('required_quote', '')
        
        # Check abstention
        did_abstain = predicted_answer.get('abstained', False) or \
                      '不详' in str(predicted_answer.get('answer', '')) or \
                      '忘记' in str(predicted_answer.get('answer', '')) or \
                      '不知道' in str(predicted_answer.get('answer', ''))
        
        if should_abstain:
            if did_abstain:
                score += 0.4
                details['correct_abstention'] = True
            else:
                details['correct_abstention'] = False
                details['should_have_abstained'] = True
        
        # Check for hallucination
        has_hallucination = False
        predicted_text = str(predicted_answer.get('answer', ''))
        
        # Check if invented specific details not in evidence
        if not did_abstain and should_abstain:
            has_hallucination = True
            details['hallucination_detected'] = True
        else:
            has_hallucination = False
            details['hallucination_detected'] = False
            score += 0.4
        
        # Quote check
        if required_quote:
            quote_included = required_quote in predicted_text or \
                          any(q in predicted_text for q in question.get('additional_quotes', []))
            if quote_included:
                score += 0.2
                details['quote_included'] = True
            else:
                details['quote_included'] = False
        
        passed = score >= max_score * 0.7
        
        return TestResult(
            question_id=qid,
            question_type='conflict_gap',
            question=q_text,
            passed=passed,
            score=score,
            max_score=max_score,
            details=details
        )
    
    def run_test(self, question: Dict, rag_system: Any) -> TestResult:
        """Run a single test question against the RAG system"""
        q_type = question.get('type', question.get('benchmark_type', 'unknown'))
        
        try:
            # Call the RAG system (mock interface)
            predicted_answer = rag_system.query(question['question'])
            
            # Route to appropriate evaluator
            if q_type == 'fact_exact':
                return self.evaluate_fact_exact(question, predicted_answer)
            elif q_type == 'evidence_set':
                return self.evaluate_evidence_set(question, predicted_answer)
            elif q_type == 'conflict_gap':
                return self.evaluate_conflict_gap(question, predicted_answer)
            else:
                return TestResult(
                    question_id=question.get('id', 'unknown'),
                    question_type=q_type,
                    question=question['question'],
                    passed=False,
                    score=0.0,
                    max_score=1.0,
                    details={},
                    error_message=f"Unknown question type: {q_type}"
                )
        except Exception as e:
            return TestResult(
                question_id=question.get('id', 'unknown'),
                question_type=q_type,
                question=question['question'],
                passed=False,
                score=0.0,
                max_score=1.0,
                details={},
                error_message=str(e)
            )
    
    def run_benchmark(self, rag_system: Any, question_type: Optional[str] = None) -> Dict:
        """Run full benchmark and return summary"""
        questions = self.load_questions(question_type)
        self.results = []
        
        for question in questions:
            result = self.run_test(question, rag_system)
            self.results.append(result)
        
        return self.generate_summary()
    
    def generate_summary(self) -> Dict:
        """Generate summary report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        total_score = sum(r.score for r in self.results)
        max_total_score = sum(r.max_score for r in self.results)
        
        # Breakdown by type
        by_type = {}
        for result in self.results:
            qtype = result.question_type
            if qtype not in by_type:
                by_type[qtype] = {'count': 0, 'passed': 0, 'total_score': 0, 'max_score': 0}
            by_type[qtype]['count'] += 1
            if result.passed:
                by_type[qtype]['passed'] += 1
            by_type[qtype]['total_score'] += result.score
            by_type[qtype]['max_score'] += result.max_score
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'pass_rate': passed_tests / total_tests if total_tests > 0 else 0,
            'overall_score': total_score,
            'max_score': max_total_score,
            'overall_percentage': (total_score / max_total_score * 100) if max_total_score > 0 else 0,
            'by_type': by_type,
            'individual_results': [
                {
                    'id': r.question_id,
                    'type': r.question_type,
                    'question': r.question,
                    'passed': r.passed,
                    'score': r.score,
                    'max_score': r.max_score,
                    'details': r.details,
                    'error': r.error_message
                }
                for r in self.results
            ]
        }
        
        return summary
    
    def save_results(self, output_path: Path):
        """Save results to JSON file"""
        summary = self.generate_summary()
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        return summary


class MockRAGSystem:
    """Mock RAG system for testing purposes"""
    
    def query(self, question: str) -> Dict:
        """
        Mock query method.
        Replace this with actual RAG system integration.
        """
        # This is a placeholder - actual implementation would call your RAG system
        return {
            'answer': 'Mock answer',
            'evidence': [],
            'citation': None
        }


def main():
    """Main entry point for running benchmarks"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Legal RAG Benchmark')
    parser.add_argument('--benchmark-dir', type=Path, 
                      default=Path(__file__).parent,
                      help='Path to benchmark directory')
    parser.add_argument('--type', type=str, choices=['fact_exact', 'evidence_set', 'conflict_gap'],
                      help='Question type to run (default: all)')
    parser.add_argument('--output', type=Path, 
                      default=Path('benchmark_results.json'),
                      help='Output file for results')
    
    args = parser.parse_args()
    
    # Create runner
    runner = BenchmarkRunner(args.benchmark_dir)
    
    # Use mock RAG system (replace with actual implementation)
    rag_system = MockRAGSystem()
    
    # Run benchmark
    print(f"Running benchmark on {args.benchmark_dir}...")
    summary = runner.run_benchmark(rag_system, args.type)
    
    # Print summary
    print("\n=== Benchmark Summary ===")
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed_tests']}")
    print(f"Pass Rate: {summary['pass_rate']*100:.1f}%")
    print(f"Overall Score: {summary['overall_percentage']:.1f}%")
    
    print("\n=== Results by Type ===")
    for qtype, stats in summary['by_type'].items():
        print(f"\n{qtype}:")
        print(f"  Passed: {stats['passed']}/{stats['count']}")
        print(f"  Score: {stats['total_score']}/{stats['max_score']} "
              f"({stats['total_score']/stats['max_score']*100:.1f}%)")
    
    # Save results
    runner.save_results(args.output)
    print(f"\nResults saved to: {args.output}")
    
    # Return exit code based on pass rate
    return 0 if summary['pass_rate'] >= 0.7 else 1


if __name__ == '__main__':
    exit(main())
