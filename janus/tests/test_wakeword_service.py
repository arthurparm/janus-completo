import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.core.senses.audio.wakeword_service import WakeWordService

import sys
from unittest.mock import MagicMock

# Mock module availability before patch attempts to resolve it
mock_oww = MagicMock()
sys.modules["openwakeword"] = mock_oww
sys.modules["openwakeword.model"] = mock_oww
sys.modules["pyaudio"] = MagicMock()

@pytest.mark.asyncio
async def test_wakeword_service_initialization():
    """
    Test initialization with mocked libraries.
    """
    with patch("openwakeword.model.Model") as MockModel:
        service = WakeWordService(models=["test_model"])
        assert service._available is True
        assert service.models == ["test_model"]
        MockModel.assert_called_once_with(["test_model"])

@pytest.mark.asyncio
async def test_wait_for_wake_word():
    """
    Test detection loop (mocked audio stream).
    """
    with patch("openwakeword.model.Model") as MockModel, \
         patch("pyaudio.PyAudio") as MockPyAudio:
        
        # Setup Model Prediction Mock
        model_instance = MockModel.return_value
        # return score 0.0 first call, 0.9 second call
        model_instance.predict.side_effect = [
            {"test_model": 0.0},
            {"test_model": 0.9}
        ]
        
        # Setup Audio Stream Mock
        p_instance = MockPyAudio.return_value
        stream_instance = p_instance.open.return_value
        stream_instance.read.return_value = b'\x00' * 1280
        
        service = WakeWordService(models=["test_model"])
        
        detected = await service.wait_for_wake_word()
        
        assert detected is True
        assert model_instance.predict.call_count == 2
        stream_instance.stop_stream.assert_called_once()
