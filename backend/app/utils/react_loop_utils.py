"""
ReAct Loop Processing Utilities

This module provides shared utilities for processing and formatting ReAct loop
information from LangChain agents. Used by both traditional and streaming
agent services to ensure consistent processing.

Functions:
- Thought extraction from agent logs
- Tool action categorization and description
- SQL query formatting
- Result type detection
- Step processing and summarization
- Execution flow generation
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional, List


def extract_thought_from_log(log_text: str) -> Optional[str]:
    """
    Extract the agent's thought/reasoning from the log text.

    Args:
        log_text: Raw log text from the agent

    Returns:
        Extracted thought or None if not found
    """
    if not log_text:
        return None

    # Common patterns for thoughts in LangChain agents
    thought_patterns = [
        r"Thought:\s*(.*?)(?=\n(?:Action|Final Answer)|$)",
        r"I need to\s*(.*?)(?=\n|$)",
        r"Let me\s*(.*?)(?=\n|$)",
        r"I should\s*(.*?)(?=\n|$)",
        r"First,?\s*(.*?)(?=\n|$)",
        r"Now\s*(.*?)(?=\n|$)",
        r"To answer this\s*(.*?)(?=\n|$)",
        r"I'll\s*(.*?)(?=\n|$)"
    ]

    for pattern in thought_patterns:
        match = re.search(pattern, log_text, re.IGNORECASE | re.DOTALL)
        if match:
            thought = match.group(1).strip()
            if thought and len(thought) > 5:  # Avoid very short matches
                return thought

    # If no specific pattern matches, try to extract the first meaningful sentence
    sentences = log_text.split('.')
    for sentence in sentences:
        clean_sentence = sentence.strip()
        if (len(clean_sentence) > 20 and
                not clean_sentence.startswith(('Action:', 'Final Answer:', 'Observation:'))):
            return clean_sentence

    return None


def categorize_tool_action(tool_name: str) -> Dict[str, str]:
    """
    Categorize and describe the tool action with human-readable information.

    Args:
        tool_name: Name of the tool being used

    Returns:
        Dictionary with category, description, and purpose
    """
    tool_categories = {
        'sql_db_list_tables': {
            'category': 'schema_exploration',
            'description': 'Listing all available tables in the database',
            'purpose': 'Understanding database structure'
        },
        'sql_db_schema': {
            'category': 'schema_exploration',
            'description': 'Examining table schema and structure',
            'purpose': 'Understanding table columns and relationships'
        },
        'sql_db_query': {
            'category': 'data_retrieval',
            'description': 'Executing SQL query to retrieve data',
            'purpose': 'Getting the actual data to answer the question'
        },
        'sql_db_query_checker': {
            'category': 'validation',
            'description': 'Validating SQL query syntax and logic',
            'purpose': 'Ensuring query correctness before execution'
        },
        'list_sql_database': {
            'category': 'schema_exploration',
            'description': 'Listing database tables and structure',
            'purpose': 'Understanding available data sources'
        },
        'info_sql_database': {
            'category': 'schema_exploration',
            'description': 'Getting detailed table information',
            'purpose': 'Understanding table schemas and relationships'
        },
        'query_sql_database': {
            'category': 'data_retrieval',
            'description': 'Executing SQL query against database',
            'purpose': 'Retrieving data to answer the question'
        },
        'query_sql_checker': {
            'category': 'validation',
            'description': 'Checking SQL query for errors',
            'purpose': 'Validating query syntax and logic'
        }
    }

    return tool_categories.get(tool_name, {
        'category': 'unknown',
        'description': f'Using tool: {tool_name}',
        'purpose': 'Performing agent action'
    })


def format_sql_query(query_text: str) -> str:
    """
    Format SQL query for better readability with proper indentation and line breaks.

    Args:
        query_text: Raw SQL query string

    Returns:
        Formatted SQL query
    """
    if not query_text:
        return query_text

    # Basic SQL formatting
    query = query_text.strip()

    # Add line breaks for major keywords
    major_keywords = [
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN',
        'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'UNION', 'UNION ALL'
    ]

    for keyword in major_keywords:
        # Use word boundaries to avoid partial matches
        pattern = f'\\b{re.escape(keyword)}\\b'
        query = re.sub(pattern, f'\n{keyword}', query, flags=re.IGNORECASE)

    # Add proper indentation for sub-clauses
    lines = query.split('\n')
    formatted_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Main clauses start at column 0
        if any(stripped.upper().startswith(kw) for kw in major_keywords):
            formatted_lines.append(stripped)
        else:
            # Sub-clauses get indented
            formatted_lines.append(f"    {stripped}")

    # Clean up extra whitespace and empty lines
    result = '\n'.join(formatted_lines)
    result = re.sub(r'\n\s*\n', '\n', result)
    result = re.sub(r'^\n+', '', result)

    return result


def detect_result_type(result_text: str, tool_name: str) -> str:
    """
    Detect and classify the type of result returned by a tool.

    Args:
        result_text: The result text from the tool
        tool_name: Name of the tool that produced the result

    Returns:
        String describing the result type for UI formatting
    """
    if not result_text or result_text.strip() == "":
        return "empty"

    # Tool-specific result type detection
    if tool_name in ['sql_db_list_tables', 'list_sql_database']:
        return "table_list"
    elif tool_name in ['sql_db_schema', 'info_sql_database']:
        return "schema_info"
    elif tool_name in ['sql_db_query', 'query_sql_database']:
        # Check if it looks like tabular data
        if '|' in result_text and '\n' in result_text:
            return "tabular_data"
        elif result_text.strip().startswith('(') and result_text.strip().endswith(')'):
            return "sql_result_tuple"
        elif result_text.strip().startswith('[') and result_text.strip().endswith(']'):
            return "sql_result_list"
        else:
            return "sql_result"
    elif tool_name in ['sql_db_query_checker', 'query_sql_checker']:
        return "validation_result"
    else:
        # Generic content-based detection
        if result_text.count('\n') > 3 and '|' in result_text:
            return "tabular_data"
        elif result_text.startswith('CREATE TABLE') or result_text.startswith('CREATE'):
            return "schema_definition"
        elif result_text.count(',') > 3 and len(result_text) < 200:
            return "list_data"
        else:
            return "text"


def process_intermediate_steps(steps: List[Any]) -> List[Dict[str, Any]]:
    """
    Enhanced processing of intermediate execution steps to extract ReAct loop information.

    Args:
        steps: Raw intermediate steps from agent execution

    Returns:
        List of formatted ReAct step dictionaries
    """
    processed_steps = []
    step_counter = 0

    for i, step in enumerate(steps):
        try:
            step_counter += 1

            if isinstance(step, tuple) and len(step) >= 2:
                action, observation = step[0], step[1]

                # Extract basic action information
                tool_name = getattr(action, 'tool', 'unknown')
                tool_input = getattr(action, 'tool_input', '')
                action_log = getattr(action, 'log', '')

                # Extract thought from the action log
                thought = extract_thought_from_log(action_log)

                # Get tool categorization
                tool_info = categorize_tool_action(tool_name)

                # Process tool input based on tool type
                formatted_input = tool_input
                if tool_name in ['sql_db_query', 'query_sql_database'] and isinstance(tool_input, str):
                    formatted_input = format_sql_query(tool_input)

                # Process observation
                observation_text = str(observation) if observation else "No result"

                # For SQL query results, try to structure them better
                if tool_name in ['sql_db_query', 'query_sql_database'] and observation_text:
                    # Try to detect if this is tabular data
                    lines = observation_text.strip().split('\n')
                    if len(lines) > 1 and '|' in observation_text:
                        # Looks like formatted table data - keep as is for now
                        pass

                step_info = {
                    "step_number": step_counter,
                    "step_type": "react_cycle",
                    "timestamp": datetime.now().isoformat(),
                    "thought": thought,
                    "action": {
                        "tool": tool_name,
                        "category": tool_info['category'],
                        "description": tool_info['description'],
                        "purpose": tool_info['purpose'],
                        "icon": tool_info.get('icon', '🔧'),
                        "input": formatted_input,
                        "raw_input": tool_input,
                        "full_log": action_log
                    },
                    "observation": {
                        "result": observation_text,
                        "result_type": detect_result_type(observation_text, tool_name),
                        "success": len(observation_text.strip()) > 0,
                        "length": len(observation_text)
                    },
                    "metadata": {
                        "original_step_index": i,
                        "processing_time": datetime.now().isoformat()
                    }
                }

                processed_steps.append(step_info)
            else:
                # Handle malformed steps
                step_info = {
                    "step_number": step_counter,
                    "step_type": "malformed",
                    "timestamp": datetime.now().isoformat(),
                    "error": "Could not parse step structure",
                    "raw_step": str(step)[:500] + "..." if len(str(step)) > 500 else str(step),
                    "metadata": {
                        "original_step_index": i,
                        "processing_time": datetime.now().isoformat()
                    }
                }
                processed_steps.append(step_info)

        except Exception as err:
            processed_steps.append({
                "step_number": step_counter,
                "step_type": "error",
                "timestamp": datetime.now().isoformat(),
                "error": f"Processing error: {err}",
                "raw_step": str(step)[:200] + "..." if len(str(step)) > 200 else str(step),
                "metadata": {
                    "original_step_index": i,
                    "processing_time": datetime.now().isoformat()
                }
            })

    return processed_steps


def generate_step_summary(react_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of the ReAct steps for quick overview.

    Args:
        react_steps: List of processed ReAct steps

    Returns:
        Summary dictionary with counts, categories, and flow information
    """
    if not react_steps:
        return {
            "total_steps": 0,
            "categories": {},
            "tools_used": [],
            "final_action": None,
            "execution_pattern": []
        }

    categories = {}
    tools_used = []
    execution_pattern = []

    for step in react_steps:
        if step.get("step_type") == "react_cycle":
            action = step.get("action", {})
            category = action.get("category", "unknown")
            tool = action.get("tool", "unknown")

            categories[category] = categories.get(category, 0) + 1
            tools_used.append(tool)
            execution_pattern.append(category)

    return {
        "total_steps": len(react_steps),
        "categories": categories,
        "tools_used": list(set(tools_used)),  # Remove duplicates
        "execution_pattern": execution_pattern,
        "final_action": react_steps[-1].get("action", {}).get("description") if react_steps else None,
        "complexity_score": _calculate_complexity_score(react_steps)
    }


def generate_execution_flow(react_steps: List[Dict[str, Any]]) -> List[str]:
    """
    Generate a high-level execution flow description for user understanding.

    Args:
        react_steps: List of processed ReAct steps

    Returns:
        List of human-readable flow descriptions
    """
    flow = []

    for step in react_steps:
        if step.get("step_type") == "react_cycle":
            action = step.get("action", {})
            purpose = action.get("purpose", "Unknown action")
            icon = action.get("icon", "🔧")
            flow.append(f"{icon} {purpose}")

    return flow


def format_step_for_display(step: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a ReAct step for optimal frontend display with UI-friendly formatting.

    Args:
        step: Processed ReAct step dictionary

    Returns:
        Display-formatted step dictionary
    """
    if step.get("step_type") != "react_cycle":
        return step

    action = step.get("action", {})
    observation = step.get("observation", {})

    # Create display-friendly version
    display_step = {
        **step,  # Copy all original data
        "display": {
            "title": f"Step {step.get('step_number')}: {action.get('description', 'Unknown Action')}",
            "category_label": _get_category_label(action.get('category')),
            "category_color": _get_category_color(action.get('category')),
            "thought_summary": _summarize_thought(step.get('thought')),
            "result_summary": _summarize_result(observation.get('result', ''), observation.get('result_type')),
            "sql_formatted": action.get('input') if action.get('tool') in ['sql_db_query',
                                                                           'query_sql_database'] else None,
            "execution_time_estimate": _estimate_execution_time(action.get('category'))
        }
    }

    return display_step


def _calculate_complexity_score(react_steps: List[Dict[str, Any]]) -> int:
    """Calculate a complexity score based on the execution pattern."""
    score = 0

    for step in react_steps:
        if step.get("step_type") == "react_cycle":
            action = step.get("action", {})
            category = action.get("category", "")

            # Weight different categories
            if category == "schema_exploration":
                score += 1
            elif category == "data_retrieval":
                score += 3
            elif category == "validation":
                score += 2

            # Bonus for SQL complexity
            if action.get("tool") in ["sql_db_query", "query_sql_database"]:
                sql_input = action.get("input", "")
                if "JOIN" in sql_input.upper():
                    score += 2
                if "GROUP BY" in sql_input.upper():
                    score += 1
                if "ORDER BY" in sql_input.upper():
                    score += 1

    return min(score, 10)  # Cap at 10


def _get_category_label(category: str) -> str:
    """Get human-readable label for category."""
    labels = {
        'schema_exploration': 'Database Exploration',
        'data_retrieval': 'Data Query',
        'validation': 'Query Validation',
        'unknown': 'Other Action'
    }
    return labels.get(category, category.title())


def _get_category_color(category: str) -> str:
    """Get color code for category visualization."""
    colors = {
        'schema_exploration': '#3498db',  # Blue
        'data_retrieval': '#2ecc71',  # Green
        'validation': '#f39c12',  # Orange
        'unknown': '#95a5a6'  # Gray
    }
    return colors.get(category, '#95a5a6')


def _summarize_thought(thought: Optional[str]) -> Optional[str]:
    """Create a shortened version of the thought for display."""
    if not thought:
        return None

    if len(thought) <= 80:
        return thought

    # Try to end at a sentence boundary
    for i in range(75, min(len(thought), 120)):
        if thought[i] in '.!?':
            return thought[:i + 1]

    # Fallback to simple truncation
    return thought[:80] + "..."


def _summarize_result(result: str, result_type: str) -> str:
    """Create a summary of the result for display."""
    if not result:
        return "No result"

    if result_type == "table_list":
        tables = result.split(',')
        count = len(tables)
        return f"Found {count} tables: {', '.join(tables[:3])}{'...' if count > 3 else ''}"

    elif result_type in ["sql_result", "tabular_data"]:
        lines = result.split('\n')
        if len(lines) > 1:
            return f"Retrieved {len(lines) - 1} rows of data"
        else:
            return "Query executed successfully"

    elif result_type == "schema_info":
        return "Retrieved table schema information"

    else:
        if len(result) <= 100:
            return result
        return result[:100] + "..."


def _estimate_execution_time(category: str) -> str:
    """Estimate execution time for different categories."""
    estimates = {
        'schema_exploration': '~1s',
        'data_retrieval': '~2-3s',
        'validation': '~1s',
        'unknown': '~1-2s'
    }
    return estimates.get(category, '~1-2s')


# Export all public functions
__all__ = [
    'extract_thought_from_log',
    'categorize_tool_action',
    'format_sql_query',
    'detect_result_type',
    'process_intermediate_steps',
    'generate_step_summary',
    'generate_execution_flow',
    'format_step_for_display'
]
