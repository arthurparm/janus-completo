import pytest
import asyncio
from unittest.mock import MagicMock, patch
from app.core.agents.meta_agent import MetaAgent, analyze_performance_trends, get_resource_usage
from app.core.monitoring.health_monitor import _latency_windows
from collections import deque
import json

@pytest.mark.asyncio
async def test_meta_agent_initialization():
    """Test that MetaAgent initializes correctly with tools."""
    # Mock LLM to prevent actual API calls during init
    with patch("app.core.agents.meta_agent.get_llm") as mock_get_llm:
        mock_llm_instance = MagicMock()
        mock_get_llm.return_value = mock_llm_instance
        
        agent = MetaAgent()
        
        assert agent.agent_id == "meta_agent_supervisor"
        assert len(agent.tools) == 4
        tool_names = [t.name for t in agent.tools]
        assert "analyze_memory_for_failures" in tool_names
        assert "get_system_health_metrics" in tool_names
        assert "analyze_performance_trends" in tool_names
        assert "get_resource_usage" in tool_names

def test_get_resource_usage_tool():
    """Test the get_resource_usage tool returns valid structure."""
    result_str = get_resource_usage.invoke({})
    result = json.loads(result_str)
    
    assert "cpu" in result
    assert "memory" in result
    assert "disk" in result
    assert "process" in result
    
    # Verify psutil data structure presence
    assert "percent_total" in result["cpu"]
    assert "percent_used" in result["memory"]

def test_analyze_performance_trends_tool():
    """Test analyze_performance_trends with injected in-memory data."""
    # Inject mock data
    _latency_windows["test_metric"] = deque([0.1, 0.2, 0.1, 0.15, 0.5])
    
    result_str = analyze_performance_trends.invoke({"metric_name": "test_metric_latency"})
    result = json.loads(result_str)
    
    assert result["metric"] == "test_metric_latency"
    assert result["data_points_count"] == 5
    assert result["average"] > 0
    assert "trend" in result

@pytest.mark.asyncio
async def test_meta_agent_run_cycle_structure():
    """Test that run_analysis_cycle executes and handles flow (mocked LLM)."""
    with patch("app.core.agents.meta_agent.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        # Mock LLM response to return a valid JSON report
        report_mock = {
            "overall_status": "healthy",
            "health_score": 95,
            "issues": [],
            "recommendations": [],
            "summary": "System is healthy."
        }
        mock_llm.invoke.return_value = json.dumps(report_mock)
        mock_get_llm.return_value = mock_llm
        
        agent = MetaAgent()
        report = await agent.run_analysis_cycle()
        
        assert report is not None
        assert report.overall_status == "healthy"
        assert report.health_score == 95
        assert len(report.issues_detected) == 0
