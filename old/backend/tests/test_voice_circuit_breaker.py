import time
from unittest.mock import AsyncMock, patch

import pytest

from app.core.senses.audio.manager import VoiceManager


@pytest.mark.asyncio
async def test_circuit_breaker_trip():
    with patch("app.core.senses.audio.manager.STTService") as MockSTT, \
         patch("app.core.senses.audio.manager.TTSService"):

        vm = VoiceManager()
        vm.initialize()

        stt = MockSTT.return_value
        # Fail 5 times
        stt.listen = AsyncMock(side_effect=Exception("Mic Error"))

        # 1. Failures accumulate
        for i in range(5):
             await vm.listen()
             assert vm._failure_count == i + 1

        assert vm._circuit_open is True

        # 2. Circuit is Open (Fast Fail)
        # Should not call stt.listen()
        stt.listen.reset_mock()
        await vm.listen()
        stt.listen.assert_not_called()

@pytest.mark.asyncio
async def test_circuit_breaker_recovery():
    with patch("app.core.senses.audio.manager.STTService") as MockSTT, \
         patch("app.core.senses.audio.manager.TTSService"):

        vm = VoiceManager()
        vm.initialize()
        vm._circuit_open = True
        vm._max_failures = 5
        vm._failure_count = 5
        vm._last_failure_time = time.time() - 61 # 61s ago (Limit 60)

        stt = MockSTT.return_value
        stt.listen = AsyncMock(return_value="Recovered")

        # Circuit should close and allow call
        result = await vm.listen()

        assert vm._circuit_open is False
        assert vm._failure_count == 0
        assert result == "Recovered"
        stt.listen.assert_called_once()
