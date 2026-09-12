from typing import Optional

from app.agents.base_agent import BaseAgent
from app.core.errors import LLMBadOutput, NoDocumentsIndexed
from app.services import llm_service
from app.services.context_builder import build_overview_context

MAX_CONTEXT_CHARS = 5000

PROMPT_TEMPLATE = """
You are an Academic Copilot creating a quiz to help a student deeply understand their study material.

Generate exactly {num_questions} open-ended quiz questions based on the study material below.

Rules:
- Each question should test understanding of a key concept, NOT just recall of a fact.
- The answer must be thorough and conceptual — explain the idea, why it matters, and any
  related context so the student truly understands it.
- Do NOT generate multiple-choice questions.
- Vary the questions across different topics covered in the material.

Respond ONLY with a valid JSON array. No extra text before or after. Format:
[
  {{
    "question": "...",
    "answer": "..."
  }}
]

Study Material:
{context}

JSON:
"""

GRADING_TEMPLATE = """
You are an Academic Copilot grading a student's answer to a study question.

Question:
{question}

Model answer:
{expected_answer}

Student's answer:
{student_answer}

Grade the student's answer against the model answer. Be encouraging but honest.

Respond ONLY with a valid JSON object in this exact format:
{{
  "score": <integer from 0 to 100>,
  "verdict": "<one of: correct, partially correct, incorrect>",
  "feedback": "<2-4 sentences explaining what the student got right, what they
                missed, and how to improve>"
}}

JSON:
"""

VALID_VERDICTS = {"correct", "partially correct", "incorrect"}


class QuizAgent(BaseAgent):
    """Generates and grades open-ended quiz questions."""

    def run(self, num_questions: int = 5, doc_id: Optional[str] = None) -> dict:
        """Returns {questions: list[{question, answer}]}."""
        context = build_overview_context(doc_id=doc_id, max_chars=MAX_CONTEXT_CHARS)
        if not context:
            raise NoDocumentsIndexed(
                "No readable content was found for the selected document."
            )

        prompt = PROMPT_TEMPLATE.format(num_questions=num_questions, context=context)
        parsed = llm_service.ask_llm_json(prompt)

        if not isinstance(parsed, list):
            raise LLMBadOutput("The model did not return a list of questions.")

        questions = [
            {"question": item["question"].strip(), "answer": item["answer"].strip()}
            for item in parsed
            if isinstance(item, dict)
            and isinstance(item.get("question"), str)
            and isinstance(item.get("answer"), str)
            and item["question"].strip()
            and item["answer"].strip()
        ]

        if not questions:
            raise LLMBadOutput(
                "The model did not produce any usable questions. Please try again."
            )

        return {"questions": questions}

    def grade(self, question: str, expected_answer: str, student_answer: str) -> dict:
        """Returns {score: int, verdict: str, feedback: str}."""
        prompt = GRADING_TEMPLATE.format(
            question=question,
            expected_answer=expected_answer,
            student_answer=student_answer,
        )
        parsed = llm_service.ask_llm_json(prompt)

        if not isinstance(parsed, dict):
            raise LLMBadOutput("The model did not return a grading result.")

        try:
            score = int(parsed.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(100, score))

        verdict = str(parsed.get("verdict", "")).strip().lower()
        if verdict not in VALID_VERDICTS:
            # Fall back to deriving the verdict from the score.
            verdict = (
                "correct" if score >= 80
                else "partially correct" if score >= 40
                else "incorrect"
            )

        feedback = str(parsed.get("feedback", "")).strip()
        if not feedback:
            feedback = "No feedback was returned for this answer."

        return {"score": score, "verdict": verdict, "feedback": feedback}
