"""Tests for LLM conversation history management in src/rag/llm.py."""

import sys
import unittest
from unittest.mock import MagicMock, patch

import src.rag.llm as llm_mod

_SLM = ("slm", "test-model", "")
_ANTHROPIC = ("anthropic", "test-model", "test-key")
_GROQ = ("groq", "test-model", "test-key")
_CONTEXT = "Income tax slab rates as per Finance Act 2024."
_QUESTION = "What is the 30% slab threshold?"


class _ChatHelper(unittest.TestCase):
    """Base with a helper that runs chat() and captures the messages list."""

    def _run_chat(self, question=_QUESTION, context=_CONTEXT, history=None, provider=_SLM):
        captured = {}

        def fake_ollama(base, model, messages, max_tokens):
            captured["messages"] = list(messages)
            return "answer"

        def fake_openai(base, api_key, model, messages, max_tokens):
            captured["messages"] = list(messages)
            return "answer"

        def fake_anthropic(api_key, model, messages, max_tokens):
            captured["messages"] = list(messages)
            return "answer"

        with (
            patch.object(llm_mod, "llm", return_value=provider),
            patch.object(llm_mod, "_ollama_native", side_effect=fake_ollama),
            patch.object(llm_mod, "_openai_compatible", side_effect=fake_openai),
            patch.object(llm_mod, "_anthropic", side_effect=fake_anthropic),
        ):
            llm_mod.chat(question, context, history)

        return captured.get("messages", [])


class TestSystemPromptPosition(_ChatHelper):

    def test_system_prompt_is_first_message(self):
        msgs = self._run_chat()
        self.assertEqual(msgs[0]["role"], "system")

    def test_system_prompt_contains_expected_text(self):
        msgs = self._run_chat()
        self.assertIn("Income Tax", msgs[0]["content"])

    def test_system_prompt_exactly_once_no_history(self):
        msgs = self._run_chat(history=None)
        system_msgs = [m for m in msgs if m["role"] == "system"]
        self.assertEqual(len(system_msgs), 1)

    def test_system_prompt_exactly_once_with_history(self):
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]
        msgs = self._run_chat(history=history)
        system_msgs = [m for m in msgs if m["role"] == "system"]
        self.assertEqual(len(system_msgs), 1)


class TestCurrentQuestionPlacement(_ChatHelper):

    def test_current_question_is_last_message(self):
        msgs = self._run_chat()
        self.assertEqual(msgs[-1]["role"], "user")

    def test_current_question_content_includes_question(self):
        msgs = self._run_chat()
        self.assertIn(_QUESTION, msgs[-1]["content"])

    def test_current_question_content_includes_context(self):
        msgs = self._run_chat()
        self.assertIn(_CONTEXT, msgs[-1]["content"])


class TestHistoryPreservation(_ChatHelper):

    def test_no_history_produces_two_messages(self):
        msgs = self._run_chat(history=None)
        self.assertEqual(len(msgs), 2)

    def test_empty_list_history_produces_two_messages(self):
        msgs = self._run_chat(history=[])
        self.assertEqual(len(msgs), 2)

    def test_history_appears_between_system_and_current(self):
        history = [
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "first answer"},
        ]
        msgs = self._run_chat(history=history)
        # system, user_hist, assistant_hist, current_user
        self.assertEqual(len(msgs), 4)
        self.assertEqual(msgs[1], history[0])
        self.assertEqual(msgs[2], history[1])

    def test_history_order_is_preserved(self):
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]
        msgs = self._run_chat(history=history)
        inner = msgs[1:-1]
        self.assertEqual(inner, history)


class TestHistoryMutationGuard(_ChatHelper):

    def test_caller_history_not_mutated_empty(self):
        history = []
        self._run_chat(history=history)
        self.assertEqual(history, [])

    def test_caller_history_not_mutated_with_items(self):
        history = [
            {"role": "user", "content": "old question"},
            {"role": "assistant", "content": "old answer"},
        ]
        before = [dict(m) for m in history]
        self._run_chat(history=history)
        self.assertEqual(len(history), 2, "history list length must not change")
        self.assertEqual(history, before, "history items must not change")

    def test_history_not_mutated_after_multiple_calls(self):
        history = []
        for i in range(3):
            self._run_chat(history=history)
        self.assertEqual(history, [], "repeated calls must not accumulate into history")


class TestMultiTurnBehavior(_ChatHelper):

    def test_growing_history_never_adds_second_system_prompt(self):
        history = []
        for _ in range(4):
            msgs = self._run_chat(history=history)
            system_count = sum(1 for m in msgs if m["role"] == "system")
            self.assertEqual(system_count, 1)
            history.append({"role": "user", "content": _QUESTION})
            history.append({"role": "assistant", "content": "some answer"})


class TestProviderRouting(_ChatHelper):

    def test_anthropic_provider_messages_built_correctly(self):
        msgs = self._run_chat(provider=_ANTHROPIC)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[-1]["role"], "user")

    def test_groq_provider_messages_built_correctly(self):
        msgs = self._run_chat(provider=_GROQ)
        self.assertEqual(msgs[0]["role"], "system")
        self.assertEqual(msgs[-1]["role"], "user")


if __name__ == "__main__":
    unittest.main()
