"""MCP Prompts: reusable templates for AI agent workflows."""

from __future__ import annotations


def explore_dataset() -> str:
    """Guide an AI agent through exploring the Titanic dataset step by step."""
    return (
        "You are exploring the Titanic passenger dataset through MCP DataBridge.\n\n"
        "Start by understanding the data:\n"
        "1. Use `list_tables` to see the database schema (8 normalized tables)\n"
        "2. Read the `databridge://info` resource for an overview\n"
        "3. Read `databridge://sample` to see example rows\n\n"
        "Then explore:\n"
        "4. Use `describe_column` on key columns: age, fare, sex, class, deck\n"
        "5. Use `query_passengers` with filters to find specific groups\n"
        "6. Use `aggregate_stats` to compute averages, counts, etc.\n"
        "7. Use `get_survival_analysis` to analyze survival by class, sex, "
        "age_group, etc.\n\n"
        "Key facts about this dataset:\n"
        "- 891 passengers, ~38% survived\n"
        "- 20% of age values are missing\n"
        "- 77% of deck values are missing\n"
        "- The database is normalized: use the tools for human-readable results\n"
    )


def survival_analysis() -> str:
    """Step-by-step survival analysis workflow for the Titanic dataset."""
    return (
        "Perform a comprehensive survival analysis of the Titanic dataset:\n\n"
        "1. **Overall survival rate**: Use `aggregate_stats` with "
        "group_by='survived', metric='count', column='survived'\n\n"
        "2. **By class**: Use `get_survival_analysis` with dimension='class'\n"
        "   - First class had the highest survival rate\n\n"
        "3. **By gender**: Use `get_survival_analysis` with dimension='sex'\n"
        "   - 'Women and children first' policy is clearly visible\n\n"
        "4. **By age group**: Use `get_survival_analysis` with "
        "dimension='age_group'\n"
        "   - Children had a notably higher survival rate\n\n"
        "5. **Intersectional analysis**: Use `aggregate_stats` with filters\n"
        "   - Compare survival of 1st class women vs 3rd class men\n"
        '   - Use filters like {"sex": "female", "pclass": 1}\n\n'
        "6. **Fare analysis**: Use `aggregate_stats` to compare average fare "
        "of survivors vs non-survivors\n\n"
        "7. **Family size impact**: Analyze sibsp and parch columns\n"
    )


def data_quality_report() -> str:
    """Analyze data quality issues in the Titanic dataset."""
    return (
        "Generate a data quality report for the Titanic dataset:\n\n"
        "1. **Missing values**: Use `describe_column` for each column\n"
        "   - age: ~20% missing (177 of 891)\n"
        "   - deck: ~77% missing (688 of 891)\n"
        "   - embarked: 2 missing\n\n"
        "2. **Distributions**: Check each column's distribution\n"
        "   - Use `describe_column` on 'fare' — look for outliers\n"
        "   - Use `describe_column` on 'age' — check for reasonable range\n\n"
        "3. **Zero-fare anomaly**: 7 passengers have fare=0.0\n"
        "   - Use `query_passengers` with filters to inspect them\n"
        "   - These may be crew, companions, or data entry errors\n\n"
        "4. **Redundancy**: Note that 'survived' and 'alive' carry the same info\n\n"
        "5. **Encoding**: Missing categorical values are stored as -1 foreign keys\n"
        "   - This affects Deck (77%), Embarked (2 rows), and EmbarkTown (2 rows)\n"
        "   - Use 'missing' filter value to find them: "
        '{"deck": "missing"}\n\n'
        "6. **Summary**: Compile findings into a quality score and recommendations\n"
    )
