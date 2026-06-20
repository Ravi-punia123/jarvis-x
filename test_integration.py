#!/usr/bin/env python3
"""
Integration test for JARVIS modernization
Tests all major components work without blocking/crashing
"""
import sys
import os
import time
import threading
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Verify all modules import without errors"""
    print("[TEST] Importing all modules...")
    try:
        import config
        import ai
        import memory
        import planner
        import executor
        import speech
        import vision
        import ui_theme
        import ui_components
        import ui_file_manager
        import ui_history
        from ui import JarvisApp
        print("[OK] All imports successful")
        return True
    except Exception as e:
        print(f"[ERR] Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_backend_services():
    """Verify backend services initialize"""
    print("\n[TEST] Initializing backend services...")
    try:
        from ai import OllamaAssistant
        from memory import MemoryManager
        from planner import Planner
        from executor import Executor
        from speech import SpeechManager
        from vision import VisionManager
        
        ai_svc = OllamaAssistant()
        mem_svc = MemoryManager()
        planner_svc = Planner()
        executor_svc = Executor()
        speech_svc = SpeechManager()
        vision_svc = VisionManager()
        
        print("[OK] All backend services initialized")
        return True
    except Exception as e:
        print(f"[ERR] Backend init failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ui_components():
    """Verify UI components work"""
    print("\n[TEST] Testing UI components...")
    try:
        import tkinter as tk
        import ui_theme
        from ui_components import RoundedButton, MessageBubble, LoadingIndicator, StatusIndicator
        
        root = tk.Tk()
        root.geometry("400x300")
        
        # Test theme
        assert ui_theme.BG_PRIMARY == '#090d16', "Theme color mismatch"
        
        # Test button
        btn = RoundedButton(root, "Test", command=lambda: None)
        btn.pack()
        
        # Test message bubble
        bubble = MessageBubble(root, "Test message", is_user=True)
        bubble.pack()
        
        # Test loading indicator
        loader = LoadingIndicator(root)
        loader.pack()
        loader.start()
        
        # Test status
        status = StatusIndicator(root, "thinking")
        status.pack()
        
        root.update()
        root.after(100, root.destroy)
        root.mainloop()
        
        print("[OK] All UI components functional")
        return True
    except Exception as e:
        print(f"[ERR] UI component test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_manager():
    """Verify file manager works"""
    print("\n[TEST] Testing file manager...")
    try:
        from ui_file_manager import FileManager
        import tempfile
        
        fm = FileManager()
        
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = f.name
        
        try:
            fm.add_file(temp_path)
            files = fm.list_files()
            assert len(files) > 0, "File not added"
            
            fm.clear_files()
            files = fm.list_files()
            assert len(files) == 0, "Files not cleared"
            
            print("[OK] File manager functional")
            return True
        finally:
            os.unlink(temp_path)
    except Exception as e:
        print(f"[ERR] File manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_history_manager():
    """Verify history manager works"""
    print("\n[TEST] Testing history manager...")
    try:
        from ui_history import HistoryManager
        import tempfile
        import json
        import os
        
        hm = HistoryManager()
        
        # Test session operations
        hm.new_session("Test Session 1")
        hm.add_message("user", "Hello", {})
        hm.add_message("assistant", "Hi", {})
        hm.save_session("Test Session 1")
        
        sessions = hm.get_sessions()
        assert len(sessions) > 0, "Session not created"
        
        print("[OK] History manager functional")
        return True
    except Exception as e:
        print(f"[ERR] History manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_persistence():
    """Verify memory persists"""
    print("\n[TEST] Testing memory persistence...")
    try:
        from memory import MemoryManager
        
        mem = MemoryManager()
        mem.add_user_message("Test user message")
        mem.add_assistant_message("Test assistant response")
        mem.add_action("test_action", {"data": "value"})
        
        history = mem.get_recent_history(limit=10)
        assert len(history) >= 2, "Messages not recorded"
        
        print("[OK] Memory persistence functional")
        return True
    except Exception as e:
        print(f"[ERR] Memory persistence test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("JARVIS Integration Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Backend Services", test_backend_services()))
    results.append(("UI Components", test_ui_components()))
    results.append(("File Manager", test_file_manager()))
    results.append(("History Manager", test_history_manager()))
    results.append(("Memory Persistence", test_memory_persistence()))
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
