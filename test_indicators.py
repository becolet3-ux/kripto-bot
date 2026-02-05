
import sys
import os
import asyncio
import numpy as np
import pandas as pd
from typing import Dict

# Add project root to path
sys.path.append(os.getcwd())

from src.learning.brain import BotBrain
from src.strategies.analyzer import MarketAnalyzer

def test_brain_weights():
    print("🧠 Testing BotBrain Weights...")
    # Use a temp file for testing
    brain = BotBrain(data_file="data/test_brain_data.json")
    
    # Check default weights
    weights = brain.get_indicator_weights()
    print(f"Current Weights: {weights}")
    
    assert "mfi" in weights, "MFI missing from weights"
    assert "patterns" in weights, "Patterns missing from weights"
    
    # Test Update: WIN scenario
    signals = {"mfi": 1, "patterns": 1} 
    pnl_pct = 5.0 # Win
    
    print(f"Testing Update (Win) with signals: {signals}")
    brain.update_indicator_weights(signals, pnl_pct)
    
    new_weights = brain.get_indicator_weights()
    print(f"New Weights: {new_weights}")
    
    assert new_weights["mfi"] > 1.0, "MFI weight should increase"
    assert new_weights["patterns"] > 1.0, "Patterns weight should increase"
    
    print("✅ Brain Weight Update Test Passed!")
    
    # Clean up
    if os.path.exists("data/test_brain_data.json"):
        os.remove("data/test_brain_data.json")

def test_analyzer_calculations():
    print("📊 Testing Analyzer Calculations...")
    analyzer = MarketAnalyzer()
    
    # Create dummy data: Hammer Pattern
    # Open high, Close high, Low very low
    data = []
    # 50 candles (needs > 25 for SMA_Long)
    for i in range(50):
        timestamp = 1000 + i * 3600
        if i == 49: # Last candle is Hammer
            open_p = 100.0
            close_p = 101.0 # Small green body
            high_p = 101.5 # Small upper wick
            low_p = 95.0 # Long lower wick
            volume = 1000.0
        else:
            open_p = 100.0
            close_p = 100.0
            high_p = 100.0
            low_p = 100.0
            volume = 100.0
            
        data.append([timestamp, open_p, high_p, low_p, close_p, volume])
        
    df = analyzer.calculate_indicators(data)
    
    # Check MFI
    assert 'MFI' in df.columns, "MFI column missing"
    
    # Check Patterns
    last_row = df.iloc[-1]
    print(f"Last Row Is Hammer: {last_row['is_hammer']}")
    
    assert last_row['is_hammer'] == True, "Failed to detect Hammer pattern"
    
    print("✅ Analyzer Calculation Test Passed!")

if __name__ == "__main__":
    try:
        test_brain_weights()
        test_analyzer_calculations()
        print("🎉 ALL TESTS PASSED!")
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()
