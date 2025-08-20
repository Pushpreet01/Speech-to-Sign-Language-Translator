#!/usr/bin/env python3
"""
Test script for SignBSL.com integration
This script tests fetching real sign language videos from SignBSL.com
"""

import sys
sys.path.append('.')
from local_demo import fetch_signbsl_video_url, get_sign_url, map_text_to_signs_greedy

def test_signbsl_integration():
    """Test the SignBSL.com integration with various words and phrases"""
    
    print("🌐 Testing SignBSL.com Integration")
    print("=" * 50)
    print()
    
    # Test common words that are likely to be on SignBSL.com
    test_words = [
        'hello',
        'thank you',
        'good morning',
        'please',
        'help',
        'water',
        'food',
        'home',
        'love',
        'happy',
        'family',
        'friend'
    ]
    
    print("🔍 Testing individual word lookup:")
    print("-" * 30)
    
    successful_fetches = 0
    for word in test_words:
        print(f"Testing '{word}'...", end=" ")
        url = fetch_signbsl_video_url(word)
        if url and 'signbsl.com' in url:
            print(f"✅ Found: {url}")
            successful_fetches += 1
        elif url:
            print(f"⚠️ Unexpected URL: {url}")
        else:
            print("❌ Not found")
    
    print()
    print(f"📊 Results: {successful_fetches}/{len(test_words)} words found on SignBSL.com")
    print()
    
    # Test full sentence processing
    print("🎯 Testing full sentence processing:")
    print("-" * 35)
    
    test_sentences = [
        "hello thank you",
        "good morning how are you",
        "please help me"
    ]
    
    for sentence in test_sentences:
        print(f"\nSentence: '{sentence}'")
        sign_sequence = map_text_to_signs_greedy(sentence)
        
        for sign in sign_sequence:
            source = "SignBSL" if sign.get('source') == 'signbsl' else "Placeholder"
            phrase_info = f" ({sign['phrase_length']} words)" if sign['phrase_length'] > 1 else ""
            print(f"  • '{sign['word']}'{phrase_info} → {source}")
    
    print()
    print("🎉 SignBSL.com integration test complete!")
    print("Your system now fetches real sign language videos when available.")

if __name__ == "__main__":
    test_signbsl_integration()
