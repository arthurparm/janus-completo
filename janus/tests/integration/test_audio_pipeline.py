import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.senses.audio.manager import VoiceManager


@pytest.mark.asyncio
async def test_audio_pipeline_success_flow():
    """
    Verifies the full audio pipeline flow:
    Wake Word Detected -> Listen (Input) -> Processing (Simulated) -> Speak (Output)
    """
    # 1. Setup Manager with Mocks
    manager = VoiceManager()

    # Mock Services
    mock_wakeword = MagicMock()
    mock_wakeword.wait_for_wake_word = AsyncMock(
        side_effect=[True, False]
    )  # Detect once, then stop loop logic if we were looping

    mock_stt = MagicMock()
    mock_stt.listen = AsyncMock(return_value="Que horas sao?")

    mock_tts = MagicMock()
    mock_tts.speak = AsyncMock()

    # Inject mocks manually (bypassing initialize real hardware init)
    manager.wakeword = mock_wakeword
    manager.stt = mock_stt
    manager.tts = mock_tts
    manager._enabled = True

    # 2. Simulate Daemon Loop Interaction
    # Logic similar to what Daemon does:

    # Step A: Wait for Wake Word
    wake_detected = await manager.wait_for_wake_word()
    assert wake_detected is True, "Wake word should have been detected"

    # Step B: User speaks command
    user_input = await manager.listen()
    assert user_input == "Que horas sao?", "STT should return mocked input"

    # Step C: Simulate LLM Processing (Mocked)
    llm_response = "Sao 14 horas."

    # Step D: System Speaks response
    await manager.speak(llm_response)

    # 3. Verify Calls
    mock_wakeword.wait_for_wake_word.assert_awaited()
    mock_stt.listen.assert_awaited_once()
    mock_tts.speak.assert_awaited_once_with("Sao 14 horas.")


@pytest.mark.asyncio
async def test_audio_pipeline_graceful_failure():
    """
    Verifies that hardware failures are handled gracefully (Circuit Breaker logic).
    """
    manager = VoiceManager()
    manager._recovery_timeout = 0.1  # Fast recovery for test

    # Mock WakeWord to fail repeatedly
    mock_wakeword = MagicMock()
    mock_wakeword.wait_for_wake_word = AsyncMock(side_effect=Exception("Mic Device Error"))

    manager.wakeword = mock_wakeword
    manager._enabled = True
    manager._max_failures = 2  # Trip fast

    # Attempt 1: Fail
    res1 = await manager.wait_for_wake_word()
    assert res1 is False
    assert manager._failure_count == 1

    # Attempt 2: Fail -> Trip
    res2 = await manager.wait_for_wake_word()
    assert res2 is False
    assert manager._failure_count == 2
    assert manager._circuit_open is True

    # Attempt 3: Circuit Open -> Immediate False (no call to wakeword)
    mock_wakeword.wait_for_wake_word.reset_mock()
    res3 = await manager.wait_for_wake_word()
    assert res3 is False
    mock_wakeword.wait_for_wake_word.assert_not_called()

    # Recovery
    await asyncio.sleep(0.15)

    # Attempt 4: Should retry (and fail again in this setup, but call occurs)
    res4 = await manager.wait_for_wake_word()
    assert res4 is False
    mock_wakeword.wait_for_wake_word.assert_called()
