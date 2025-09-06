#!/usr/bin/env python3
"""
Simple test script to verify the retry logic works correctly.
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

from backend.db import init_db
from backend.logic import build_retry_batch, session_summary, build_quiz_batch, create_session_items, start_or_resume_session, save_attempt
from backend.auth import create_user

def test_retry_logic():
    print("Testing retry logic...")
    
    # Initialize database
    init_db()
    
    # Test build_retry_batch with some word IDs
    word_ids = [1, 2, 3]
    retry_batch = build_retry_batch(word_ids)
    
    print(f"✓ build_retry_batch created {len(retry_batch)} items")
    assert len(retry_batch) == len(word_ids), f"Expected {len(word_ids)} items, got {len(retry_batch)}"
    
    # Verify each item has required fields
    for item in retry_batch:
        assert "word_id" in item
        assert "question" in item
        assert "answer" in item
        assert "options" in item
        assert len(item["options"]) == 5  # 1 correct + 4 distractors
        print(f"✓ Item for word_id {item['word_id']}: {item['question'][:30]}... -> {item['answer']}")
    
    print("✓ All tests passed!")

if __name__ == "__main__":
    test_retry_logic()