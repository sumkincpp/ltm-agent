import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


def has_content_parts(event) -> bool:
    """Check if event has content with parts.

    Args:
        event: Event object to check

    Returns:
        True if event has content with parts, False otherwise
    """
    return hasattr(event, "content") and event.content is not None and hasattr(event.content, "parts") and event.content.parts is not None


class PipelineOutputFormatter:
    """Extract and format pipeline execution results."""

    @staticmethod
    def extract_result_text(events: List) -> Optional[str]:
        """Extract final result from event list.

        Args:
            events: List of events from pipeline execution

        Returns:
            Extracted result text or None
        """
        if not events:
            logger.debug("No events to extract result from")
            return None

        for event in reversed(events):
            if not has_content_parts(event):
                continue

            for part in event.content.parts or []:
                text = getattr(part, "text", None)
                if not text:
                    continue

                text = text.strip()
                if not text:
                    continue

                if "Status: SOLVED" in text:
                    if "FINAL RESULTS" in text:
                        result_text = text.split("FINAL RESULTS")[0].strip()
                        if result_text:
                            logger.debug("Extracted result from SOLVED status with FINAL RESULTS marker")
                            return result_text
                    else:
                        logger.debug("Found SOLVED status without FINAL RESULTS marker, using full text")
                        return text

                elif not text.startswith("FINAL"):
                    logger.debug("Extracted result from non-FINAL text")
                    return text

        logger.warning("No suitable result text found in pipeline output")
        return None

    @staticmethod
    def display_result(result: Optional[str], verbose: bool = False) -> None:
        """Display formatted result to user.

        Args:
            result: Result text to display
            verbose: Whether verbose mode is enabled
        """
        if verbose:
            return

        if result:
            print(f"\n{result}\n")
        else:
            logger.debug("No result to display")
