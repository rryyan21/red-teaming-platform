"""
Unit tests for attack generators.

These tests verify that:
- Attack generators return the expected structure
- All attacks have required fields
- Attack types are valid
"""

import pytest
from app.attacks import (
    generate_jailbreak_attacks,
    generate_injection_attacks,
    generate_obfuscation_attacks,
    generate_benign_prompts,
    generate_all_attacks,
    Attack
)


def test_jailbreak_attacks_structure():
    """Test that jailbreak attacks have correct structure."""
    attacks = generate_jailbreak_attacks()
    assert len(attacks) > 0
    
    for attack in attacks:
        assert isinstance(attack, Attack)
        assert attack.id.startswith("jailbreak_")
        assert attack.type == "jailbreak"
        assert len(attack.prompt) > 0
        assert attack.severity in ["low", "medium", "high"]


def test_injection_attacks_structure():
    """Test that injection attacks have correct structure."""
    attacks = generate_injection_attacks()
    assert len(attacks) > 0
    
    for attack in attacks:
        assert isinstance(attack, Attack)
        assert attack.id.startswith("injection_")
        assert attack.type == "injection"


def test_benign_prompts_structure():
    """Test that benign prompts have correct structure."""
    attacks = generate_benign_prompts()
    assert len(attacks) > 0
    
    for attack in attacks:
        assert isinstance(attack, Attack)
        assert attack.id.startswith("benign_")
        assert attack.type == "benign"
        assert attack.severity == "low"


def test_generate_all_attacks():
    """Test that generate_all_attacks returns all attack types."""
    all_attacks = generate_all_attacks()
    assert len(all_attacks) > 0
    
    # Check that we have attacks from multiple categories
    types = set(attack.type for attack in all_attacks)
    assert "jailbreak" in types
    assert "injection" in types
    assert "benign" in types
    
    # Check all attacks have unique IDs
    ids = [attack.id for attack in all_attacks]
    assert len(ids) == len(set(ids)), "All attack IDs should be unique"

