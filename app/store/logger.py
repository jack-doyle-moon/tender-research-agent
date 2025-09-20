"""Structured logging setup using structlog."""

import logging
import sys
from pathlib import Path
from typing import Any, Dict

import structlog
from structlog.typing import FilteringBoundLogger

from app.config import settings


def setup_logging() -> None:
    """Configure structured logging."""
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.dev.ConsoleRenderer(colors=True)
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> FilteringBoundLogger:
    """Get a structured logger."""
    return structlog.get_logger(name)


class RunLogger:
    """Logger for tracking run progress and metrics."""
    
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.logger = get_logger("run").bind(run_id=run_id)
        self.metrics: Dict[str, Any] = {}
    
    def log_start(self, rfp_path: str, company_name: str) -> None:
        """Log run start."""
        self.logger.info(
            "Run started",
            rfp_path=rfp_path,
            company_name=company_name
        )
    
    def log_agent_start(self, agent_name: str, iteration: int = 0) -> None:
        """Log agent execution start."""
        self.logger.info(
            "Agent started",
            agent=agent_name,
            iteration=iteration
        )
    
    def log_agent_complete(self, agent_name: str, duration: float, iteration: int = 0) -> None:
        """Log agent execution completion."""
        self.logger.info(
            "Agent completed",
            agent=agent_name,
            duration_seconds=duration,
            iteration=iteration
        )
        
        # Track metrics
        key = f"{agent_name}_duration"
        if key not in self.metrics:
            self.metrics[key] = []
        self.metrics[key].append(duration)
    
    def log_tool_usage(self, tool_name: str, query: str, results_count: int) -> None:
        """Log tool usage."""
        self.logger.info(
            "Tool used",
            tool=tool_name,
            query=query,
            results_count=results_count
        )
    
    def log_requirement_processed(self, requirement_id: str, confidence: float) -> None:
        """Log requirement processing."""
        self.logger.debug(
            "Requirement processed",
            requirement_id=requirement_id,
            confidence=confidence
        )
    
    def log_validation_result(self, coverage_score: float, gaps_count: int, is_sufficient: bool) -> None:
        """Log validation results."""
        self.logger.info(
            "Validation completed",
            coverage_score=coverage_score,
            gaps_count=gaps_count,
            is_sufficient=is_sufficient
        )
        
        self.metrics.update({
            "coverage_score": coverage_score,
            "gaps_count": gaps_count,
            "is_sufficient": is_sufficient
        })
    
    def log_error(self, error: str, agent: str = None, tool: str = None) -> None:
        """Log error."""
        self.logger.error(
            "Error occurred",
            error=error,
            agent=agent,
            tool=tool
        )
    
    def log_run_complete(self, total_duration: float, iterations: int) -> None:
        """Log run completion."""
        self.logger.info(
            "Run completed",
            total_duration_seconds=total_duration,
            iterations=iterations,
            metrics=self.metrics
        )
    
    def save_metrics(self, run_dir: Path) -> None:
        """Save metrics to file."""
        import json
        
        metrics_file = run_dir / "metrics.json"
        with open(metrics_file, "w") as f:
            json.dump(self.metrics, f, indent=2)


# Initialize logging on import
setup_logging()
