"""
Security Tests for Safe Condition Parser

Validates that the safe parser:
1. Correctly evaluates valid conditions
2. Blocks dangerous inputs (code injection attempts)
3. Enforces resource limits (DoS protection)
4. Handles errors gracefully
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.safe_condition_parser import (
    SafeConditionParser,
    safe_evaluate_condition,
    TokenType,
)


# ============================================================================
# VALID CONDITION TESTS
# ============================================================================


class TestValidConditions:
    """Test that valid conditions evaluate correctly."""

    def test_always_keyword(self):
        """Test 'always' keyword returns True."""
        assert safe_evaluate_condition("always", {}) is True

    def test_simple_comparison_greater_than(self):
        """Test simple > comparison."""
        assert safe_evaluate_condition("severity > 0.7", {"severity": 0.8}) is True
        assert safe_evaluate_condition("severity > 0.7", {"severity": 0.5}) is False

    def test_simple_comparison_greater_equal(self):
        """Test >= comparison."""
        assert safe_evaluate_condition("severity >= 0.7", {"severity": 0.8}) is True
        assert safe_evaluate_condition("severity >= 0.7", {"severity": 0.7}) is True
        assert safe_evaluate_condition("severity >= 0.7", {"severity": 0.6}) is False

    def test_simple_comparison_less_than(self):
        """Test < comparison."""
        assert safe_evaluate_condition("severity < 0.7", {"severity": 0.5}) is True
        assert safe_evaluate_condition("severity < 0.7", {"severity": 0.8}) is False

    def test_simple_comparison_less_equal(self):
        """Test <= comparison."""
        assert safe_evaluate_condition("severity <= 0.7", {"severity": 0.6}) is True
        assert safe_evaluate_condition("severity <= 0.7", {"severity": 0.7}) is True
        assert safe_evaluate_condition("severity <= 0.7", {"severity": 0.8}) is False

    def test_simple_comparison_equal(self):
        """Test == comparison."""
        assert safe_evaluate_condition("severity == 0.7", {"severity": 0.7}) is True
        assert safe_evaluate_condition("severity == 0.7", {"severity": 0.8}) is False

    def test_simple_comparison_not_equal(self):
        """Test != comparison."""
        assert safe_evaluate_condition("severity != 0.7", {"severity": 0.8}) is True
        assert safe_evaluate_condition("severity != 0.7", {"severity": 0.7}) is False

    def test_integer_comparison(self):
        """Test integer comparisons."""
        assert safe_evaluate_condition("recurrence_count >= 3", {"recurrence_count": 5}) is True
        assert safe_evaluate_condition("recurrence_count >= 3", {"recurrence_count": 2}) is False

    def test_and_operator(self):
        """Test AND logical operator."""
        ctx = {"severity": 0.8, "recurrence_count": 3}
        assert safe_evaluate_condition("severity >= 0.7 and recurrence_count >= 2", ctx) is True

        ctx = {"severity": 0.6, "recurrence_count": 3}
        assert safe_evaluate_condition("severity >= 0.7 and recurrence_count >= 2", ctx) is False

    def test_or_operator(self):
        """Test OR logical operator."""
        ctx = {"severity": 0.8, "recurrence_count": 1}
        assert safe_evaluate_condition("severity >= 0.9 or recurrence_count >= 3", ctx) is False

        ctx = {"severity": 0.95, "recurrence_count": 1}
        assert safe_evaluate_condition("severity >= 0.9 or recurrence_count >= 3", ctx) is True

    def test_complex_expression(self):
        """Test complex expression with multiple operators."""
        ctx = {"severity": 0.85, "recurrence_count": 2, "confidence": 0.9}
        expr = "severity >= 0.8 and recurrence_count >= 2 or confidence >= 0.95"
        assert safe_evaluate_condition(expr, ctx) is True

    def test_parentheses(self):
        """Test parentheses for grouping."""
        ctx = {"severity": 0.85, "recurrence_count": 1}

        # Without parens: (severity >= 0.8 and recurrence_count >= 2) or severity >= 0.9
        # With low recurrence, only severity >= 0.9 would be True
        assert safe_evaluate_condition("severity >= 0.8 and recurrence_count >= 2 or severity >= 0.9", ctx) is False

        # With parens: severity >= 0.8 and (recurrence_count >= 2 or severity >= 0.9)
        # severity is 0.85 (>= 0.8) and (recurrence < 2 but severity < 0.9) = False
        assert safe_evaluate_condition("severity >= 0.8 and (recurrence_count >= 2 or severity >= 0.9)", ctx) is False

        # But if severity >= 0.9
        ctx["severity"] = 0.95
        assert safe_evaluate_condition("severity >= 0.8 and (recurrence_count >= 2 or severity >= 0.9)", ctx) is True


# ============================================================================
# SECURITY TESTS - CODE INJECTION PREVENTION
# ============================================================================


class TestSecurityCodeInjection:
    """Test that dangerous code injection attempts are blocked."""

    def test_blocks_import_statement(self):
        """Attempt to import modules should fail."""
        with pytest.raises(ValueError):
            safe_evaluate_condition("__import__('os').system('ls')", {"severity": 0.8})

    def test_blocks_builtin_access(self):
        """Attempt to access __builtins__ should fail."""
        with pytest.raises(ValueError):
            safe_evaluate_condition("__builtins__", {})

    def test_blocks_attribute_access(self):
        """Attempt to use attribute access should fail."""
        # The parser doesn't support '.' so this should fail during tokenization
        with pytest.raises(ValueError):
            safe_evaluate_condition("severity.__class__", {"severity": 0.8})

    def test_blocks_function_calls(self):
        """Attempt to call functions should fail."""
        # The parser doesn't support '()' for function calls
        with pytest.raises(ValueError):
            safe_evaluate_condition("eval('1+1')", {})

    def test_blocks_list_comprehension(self):
        """Attempt to use list comprehension should fail."""
        with pytest.raises(ValueError):
            safe_evaluate_condition("[x for x in range(100)]", {})

    def test_blocks_lambda(self):
        """Attempt to use lambda should fail."""
        with pytest.raises(ValueError):
            safe_evaluate_condition("lambda: True", {})

    def test_blocks_exec(self):
        """Attempt to use exec should fail."""
        with pytest.raises(ValueError):
            safe_evaluate_condition("exec('import os')", {})

    def test_blocks_unauthorized_variables(self):
        """Attempt to use non-whitelisted variables should fail."""
        with pytest.raises(ValueError) as exc_info:
            safe_evaluate_condition("malicious_var >= 0", {"malicious_var": 1})

        assert "not allowed" in str(exc_info.value).lower()

    def test_blocks_subclass_introspection(self):
        """Attempt to use __subclasses__() should fail."""
        with pytest.raises(ValueError):
            safe_evaluate_condition("().__class__.__bases__[0].__subclasses__()", {})


# ============================================================================
# SECURITY TESTS - DOS PROTECTION
# ============================================================================


class TestSecurityDoSProtection:
    """Test that DoS attacks via expensive expressions are blocked."""

    def test_blocks_overly_complex_expression(self):
        """Expression with too many tokens should be rejected."""
        parser = SafeConditionParser()

        # Create expression with > MAX_TOKENS (50)
        # Each "severity >= 0.8 and " is 4 tokens
        expr_parts = ["severity >= 0.8"] + [" and severity >= 0.8"] * 20
        long_expr = "".join(expr_parts)

        with pytest.raises(ValueError) as exc_info:
            parser.evaluate(long_expr, {"severity": 0.8})

        assert "too complex" in str(exc_info.value).lower()

    def test_max_token_limit(self):
        """Verify MAX_TOKENS limit is enforced."""
        parser = SafeConditionParser()
        assert parser.MAX_TOKENS == 50


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Test graceful error handling."""

    def test_missing_variable_in_context(self):
        """Missing variable should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            safe_evaluate_condition("severity >= 0.8", {})  # No 'severity' in context

        assert "not provided in context" in str(exc_info.value).lower()

    def test_invalid_operator(self):
        """Invalid operator should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            safe_evaluate_condition("severity = 0.8", {"severity": 0.8})  # Single '='

        assert "invalid operator" in str(exc_info.value).lower() or "unexpected" in str(exc_info.value).lower()

    def test_unterminated_string(self):
        """Unterminated string should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            safe_evaluate_condition('severity >= "0.8', {"severity": 0.8})

        assert "unterminated" in str(exc_info.value).lower()

    def test_unexpected_token(self):
        """Unexpected token should raise ValueError."""
        with pytest.raises(ValueError):
            safe_evaluate_condition("severity >= 0.8 &&", {"severity": 0.8})  # C-style &&

    def test_missing_operator(self):
        """Missing operator should raise ValueError."""
        with pytest.raises(ValueError):
            safe_evaluate_condition("severity 0.8", {"severity": 0.8})

    def test_unmatched_parenthesis(self):
        """Unmatched parenthesis should raise ValueError."""
        with pytest.raises(ValueError):
            safe_evaluate_condition("(severity >= 0.8", {"severity": 0.8})

    def test_safe_default_on_error(self):
        """safe_evaluate_condition should return False on error (safe default)."""
        # Invalid expression should return False instead of raising
        result = safe_evaluate_condition("invalid syntax @#$", {"severity": 0.8})
        assert result is False


# ============================================================================
# TOKENIZATION TESTS
# ============================================================================


class TestTokenization:
    """Test token parsing."""

    def test_tokenize_number_integer(self):
        """Test integer tokenization."""
        parser = SafeConditionParser()
        tokens = parser._tokenize("42")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 42

    def test_tokenize_number_float(self):
        """Test float tokenization."""
        parser = SafeConditionParser()
        tokens = parser._tokenize("3.14")
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 3.14

    def test_tokenize_variable(self):
        """Test variable tokenization."""
        parser = SafeConditionParser()
        tokens = parser._tokenize("severity")
        assert tokens[0].type == TokenType.VARIABLE
        assert tokens[0].value == "severity"

    def test_tokenize_operator(self):
        """Test operator tokenization."""
        parser = SafeConditionParser()
        tokens = parser._tokenize(">=")
        assert tokens[0].type == TokenType.OPERATOR
        assert tokens[0].value == ">="

    def test_tokenize_logical_and(self):
        """Test 'and' tokenization."""
        parser = SafeConditionParser()
        tokens = parser._tokenize("and")
        assert tokens[0].type == TokenType.LOGICAL
        assert tokens[0].value == "and"

    def test_tokenize_logical_or(self):
        """Test 'or' tokenization."""
        parser = SafeConditionParser()
        tokens = parser._tokenize("or")
        assert tokens[0].type == TokenType.LOGICAL
        assert tokens[0].value == "or"

    def test_tokenize_complex_expression(self):
        """Test complex expression tokenization."""
        parser = SafeConditionParser()
        tokens = parser._tokenize("severity >= 0.8 and recurrence_count >= 2")

        # Should have: severity, >=, 0.8, and, recurrence_count, >=, 2, EOF
        assert len(tokens) == 8
        assert tokens[0].value == "severity"
        assert tokens[1].value == ">="
        assert tokens[2].value == 0.8
        assert tokens[3].value == "and"
        assert tokens[4].value == "recurrence_count"
        assert tokens[5].value == ">="
        assert tokens[6].value == 2
        assert tokens[7].type == TokenType.EOF


# ============================================================================
# COMPARISON WITH eval() - DEMONSTRATE SAFETY
# ============================================================================


class TestComparisonWithEval:
    """Demonstrate that safe parser blocks attacks that eval() would allow."""

    def test_eval_vulnerability_subclasses(self):
        """Show that eval() is vulnerable to __subclasses__() attack."""
        # This is what the old eval() approach was vulnerable to:
        # malicious_expr = "().__class__.__bases__[0].__subclasses__()[104].__init__.__globals__['sys'].modules['os'].system('ls')"

        # With eval() (DANGEROUS - don't actually run):
        # result = eval(malicious_expr, {"__builtins__": {}}, {})  # STILL VULNERABLE!

        # With safe parser (SECURE):
        with pytest.raises(ValueError):
            safe_evaluate_condition(
                "().__class__.__bases__[0]",
                {}
            )

    def test_eval_vulnerability_import(self):
        """Show that eval() is vulnerable to __import__ attack."""
        # Old eval() approach was vulnerable to:
        # malicious_expr = "__import__('os').system('rm -rf /')"

        # With safe parser (SECURE):
        with pytest.raises(ValueError):
            safe_evaluate_condition(
                "__import__('os')",
                {}
            )


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestPerformance:
    """Test that parser performs well on valid expressions."""

    def test_parse_speed_simple(self):
        """Simple expression should parse quickly."""
        import time

        start = time.time()
        for _ in range(1000):
            safe_evaluate_condition("severity >= 0.8", {"severity": 0.9})
        duration = time.time() - start

        # Should complete 1000 evaluations in < 1 second
        assert duration < 1.0

    def test_parse_speed_complex(self):
        """Complex expression should parse quickly."""
        import time

        expr = "severity >= 0.8 and recurrence_count >= 2 or confidence >= 0.9"
        ctx = {"severity": 0.85, "recurrence_count": 3, "confidence": 0.95}

        start = time.time()
        for _ in range(1000):
            safe_evaluate_condition(expr, ctx)
        duration = time.time() - start

        # Should complete 1000 evaluations in < 1 second
        assert duration < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
