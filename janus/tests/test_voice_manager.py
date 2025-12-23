import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.senses.audio.manager import VoiceManager

@pytest.mark.asyncio
async def test_voice_manager_initialization():
    """
    Test that VoiceManager instantiates services correctly.
    We mock the underlying service imports to avoid missing dependency errors.
    """
    with patch("app.core.senses.audio.manager.STTService") as MockSTT, \
         patch("app.core.senses.audio.manager.TTSService") as MockTTS:
        
        vm = VoiceManager()
        vm.initialize()
        
        assert vm._enabled is True
        MockSTT.assert_called_once()
        MockTTS.assert_called_once()
        
@pytest.mark.asyncio
async def test_voice_manager_speak():
    with patch("app.core.senses.audio.manager.STTService"), \
         patch("app.core.senses.audio.manager.TTSService") as MockTTS:
        
        vm = VoiceManager()
        vm.initialize()
        
        # Configure the mock instance
        tts_instance = MockTTS.return_value
        tts_instance.speak = AsyncMock()
        
        await vm.speak("Hello")
        tts_instance.speak.assert_awaited_with("Hello")

@pytest.mark.asyncio
async def test_voice_manager_listen():
    with patch("app.core.senses.audio.manager.STTService") as MockSTT, \
         patch("app.core.senses.audio.manager.TTSService"):
        
        vm = VoiceManager()
        vm.initialize()
        
        stt_instance = MockSTT.return_value
        stt_instance.listen = AsyncMock(return_value="test command")
        
        result = await vm.listen()
        assert result == "test command"
        stt_instance.listen.assert_awaited_once()

@pytest.mark.asyncio
async def test_voice_manager_wake_word():
    with patch("app.core.senses.audio.manager.WakeWordService") as MockWW:
        vm = VoiceManager()
        vm.initialize()
        
        ww_instance = MockWW.return_value
        ww_instance.wait_for_wake_word = AsyncMock(return_value=True)
        
        result = await vm.wait_for_wake_word()
        assert result is True
        ww_instance.wait_for_wake_word.assert_awaited_once()
